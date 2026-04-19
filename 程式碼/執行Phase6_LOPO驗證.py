"""Phase 6 Stage 3 — LOPO (Leave-One-Pillar-Out) Validation
=================================================

動機：Phase 5B 投入 1,125,134 篇文章、540 個 txt_/sent_ 特徵入 feature_store，
但「文本到底貢獻多少」過去只以 Phase 3 permutation importance 推估
（txt_ 支柱 ~6% 平均貢獻）。對嚴肅的量化評審而言，
LOPO (Leave-One-Pillar-Out) 是更直接的証據：
  baseline (all 91 features)                             → AUC_0
  remove pillar P, retrain, predict same OOS window      → AUC_P
  marginal contribution ΔAUC = AUC_0 − AUC_P

本腳本以 xgboost_D20 為基準（Phase 5B 選用的主力模型），
跑 9 個支柱的 LOPO 各一次，輸出表格 + 條狀圖。

為速度：僅用最後一個 walk-forward fold（匹配 feature selection 的時間區間）。
train/val/test split 與 train_single_engine 相同（均有 stratified subsample 200k）。

Outputs:
  outputs/figures/lopo_pillar_contribution_D20.png
  outputs/reports/lopo_pillar_contribution_D20.json

執行方式：
  python 程式碼/執行Phase6_LOPO驗證.py
"""
from __future__ import annotations

import sys
import io
import json
import re
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from sklearn.metrics import roc_auc_score, log_loss

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"
FIG_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

FONT_PATH = "C:/Windows/Fonts/mingliu.ttc"
prop = fm.FontProperties(fname=FONT_PATH)
plt.rcParams["font.sans-serif"] = [prop.get_name()]
plt.rcParams["axes.unicode_minus"] = False

PILLAR_ZH = {
    "trend": "趨勢 (trend)",
    "fund":  "基本面 (fund)",
    "val":   "估值 (val)",
    "event": "事件 (event)",
    "risk":  "風險 (risk)",
    "chip":  "籌碼 (chip)",
    "ind":   "產業 (ind)",
    "txt":   "文本 (txt)",
    "sent":  "情緒 (sent)",
}

PILLAR_COLOR = {
    "trend": "#3b82f6",
    "fund":  "#10b981",
    "val":   "#f59e0b",
    "event": "#ef4444",
    "risk":  "#8b5cf6",
    "chip":  "#ec4899",
    "ind":   "#06b6d4",
    "txt":   "#f97316",
    "sent":  "#84cc16",
}


def pillar_of(name: str) -> str:
    m = re.match(r"^([a-z]+)_", name)
    return m.group(1) if m else "other"


def train_xgboost(X_train, y_train, X_val, y_val, X_test, y_test, seed=42):
    """Minimal XGBoost classifier matching trainer.py config."""
    from xgboost import XGBClassifier
    model = XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        tree_method="hist",
        early_stopping_rounds=30,
        eval_metric="mlogloss",
        random_state=seed,
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(X_train, y_train,
              eval_set=[(X_val, y_val)],
              verbose=False)
    proba = model.predict_proba(X_test)

    # Compute metrics (macro AUC + per-class AUC + log loss)
    try:
        auc_macro = roc_auc_score(y_test, proba, multi_class="ovr", average="macro")
    except Exception:
        auc_macro = np.nan
    try:
        logloss = log_loss(y_test, proba, labels=[0, 1, 2])
    except Exception:
        logloss = np.nan

    per_class_auc = {}
    for cls in [0, 1, 2]:
        try:
            y_bin = (y_test == cls).astype(int)
            per_class_auc[f"auc_c{cls}"] = float(roc_auc_score(y_bin, proba[:, cls]))
        except Exception:
            per_class_auc[f"auc_c{cls}"] = None

    # IC (spearman rank correlation of up_prob vs actual y)
    try:
        from scipy.stats import spearmanr
        ic_up, _ = spearmanr(proba[:, 2], y_test)
        ic_up = float(ic_up)
    except Exception:
        ic_up = None

    return {
        "auc_macro": float(auc_macro),
        "logloss": float(logloss),
        "auc_up": per_class_auc["auc_c2"],
        "auc_flat": per_class_auc["auc_c1"],
        "auc_down": per_class_auc["auc_c0"],
        "ic_up": ic_up,
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
    }


def _map_labels(y: np.ndarray) -> np.ndarray:
    """Map {-1, 0, +1} → {0, 1, 2} for xgboost multi:softprob."""
    return (y.astype(int) + 1).astype(int)


def prepare_fold_data(fs: pd.DataFrame, feats: list[str], label_col: str,
                      test_n_days: int = 63, val_n_days: int = 63,
                      subsample_n: int = 200_000, seed: int = 42):
    """Prepare last-fold train/val/test split, with stratified subsample on train."""
    fs = fs.dropna(subset=[label_col]).copy()
    fs["trade_date"] = pd.to_datetime(fs["trade_date"])
    fs = fs.sort_values("trade_date").reset_index(drop=True)

    unique_dates = np.sort(fs["trade_date"].unique())
    n_dates = len(unique_dates)
    test_start_date = unique_dates[n_dates - test_n_days]
    val_start_date = unique_dates[n_dates - test_n_days - val_n_days]

    train_df = fs[fs["trade_date"] < val_start_date]
    val_df = fs[(fs["trade_date"] >= val_start_date) & (fs["trade_date"] < test_start_date)]
    test_df = fs[fs["trade_date"] >= test_start_date]

    # Stratified subsample on train to match trainer protocol
    if len(train_df) > subsample_n:
        train_df = (train_df.groupby(label_col, group_keys=False)
                    [train_df.columns]
                    .apply(lambda g: g.sample(
                        n=max(1, int(subsample_n * len(g) / len(train_df))),
                        random_state=seed,
                    )))

    X_train = train_df[feats].fillna(0).values.astype(np.float32)
    y_train = _map_labels(train_df[label_col].values)
    X_val = val_df[feats].fillna(0).values.astype(np.float32)
    y_val = _map_labels(val_df[label_col].values)
    X_test = test_df[feats].fillna(0).values.astype(np.float32)
    y_test = _map_labels(test_df[label_col].values)
    return X_train, y_train, X_val, y_val, X_test, y_test


def main():
    print("=" * 70, flush=True)
    print("Phase 6 Stage 3 — LOPO (Leave-One-Pillar-Out) Validation", flush=True)
    print("=" * 70, flush=True)

    # 1. Load Phase 2 report → selected features
    ph2_path = sorted((PROJECT_ROOT / "outputs" / "reports").glob("phase2_report_*.json"))[-1]
    print(f"Phase 2 report: {ph2_path.name}", flush=True)
    ph2 = json.load(open(ph2_path, encoding="utf-8"))
    selected = ph2["results"]["feature_selection"]["selected"]
    print(f"  selected features: {len(selected)}", flush=True)

    # 2. Pillar distribution
    by_pillar = defaultdict(list)
    for f in selected:
        by_pillar[pillar_of(f)].append(f)
    print("\n  Pillar distribution:")
    for p, fs_list in sorted(by_pillar.items(), key=lambda x: -len(x[1])):
        print(f"    {p:6s}: {len(fs_list):3d}  ({', '.join(fs_list[:3])}...)", flush=True)

    # 3. Load feature_store (just columns we need)
    label_col = "label_20"
    cols = list(set(selected + [label_col, "trade_date", "company_id"]))
    fs_path = PROJECT_ROOT / "outputs" / "feature_store_final.parquet"
    fs = pd.read_parquet(fs_path, columns=cols)
    print(f"\n  Feature store loaded: {fs.shape}", flush=True)

    # 4. Prepare baseline data split (fixed split for fair comparison)
    print("\n  Preparing train/val/test split (last-fold style)...", flush=True)
    X_tr0, y_tr0, X_v0, y_v0, X_te0, y_te0 = prepare_fold_data(
        fs, selected, label_col,
    )
    print(f"    train={len(y_tr0):,}  val={len(y_v0):,}  test={len(y_te0):,}", flush=True)

    # 5. Baseline: all 91 features
    print("\n  [baseline] Training xgboost with all 91 features...", flush=True)
    t0 = time.time()
    baseline = train_xgboost(X_tr0, y_tr0, X_v0, y_v0, X_te0, y_te0)
    t_baseline = time.time() - t0
    print(f"    AUC={baseline['auc_macro']:.4f}  LogLoss={baseline['logloss']:.4f}  "
          f"AUC_up={baseline['auc_up']:.4f}  IC_up={baseline['ic_up']:.4f}  "
          f"({t_baseline:.1f}s)", flush=True)

    # 6. LOPO loops
    print("\n  === LOPO sweep ===", flush=True)
    lopo_results = {}
    for pillar, pillar_feats in sorted(by_pillar.items(), key=lambda x: -len(x[1])):
        if len(pillar_feats) == 0:
            continue
        remaining = [f for f in selected if f not in pillar_feats]
        print(f"\n  [skip {pillar:6s}] {len(pillar_feats):3d} features removed, "
              f"{len(remaining)} remain. Training...", flush=True)
        t0 = time.time()
        X_tr, y_tr, X_v, y_v, X_te, y_te = prepare_fold_data(
            fs, remaining, label_col,
        )
        res = train_xgboost(X_tr, y_tr, X_v, y_v, X_te, y_te)
        elapsed = time.time() - t0
        delta_auc = baseline["auc_macro"] - res["auc_macro"]
        delta_auc_up = baseline["auc_up"] - res["auc_up"]
        delta_ic = baseline["ic_up"] - res["ic_up"]
        print(f"    AUC={res['auc_macro']:.4f}  (Δ={delta_auc:+.4f})  "
              f"AUC_up={res['auc_up']:.4f} (Δ={delta_auc_up:+.4f})  "
              f"IC_up={res['ic_up']:.4f} (Δ={delta_ic:+.4f})  "
              f"({elapsed:.1f}s)", flush=True)
        lopo_results[pillar] = {
            **res,
            "n_features_removed": len(pillar_feats),
            "n_features_remain": len(remaining),
            "delta_auc_macro": delta_auc,
            "delta_auc_up": delta_auc_up,
            "delta_ic_up": delta_ic if delta_ic is not None else None,
            "elapsed_sec": round(elapsed, 2),
        }

    # 7. Plot
    print("\n  Plotting...", flush=True)
    df = pd.DataFrame([
        {"pillar": p, "zh": PILLAR_ZH.get(p, p), "n_feats": r["n_features_removed"],
         "delta_auc": r["delta_auc_macro"], "delta_auc_up": r["delta_auc_up"],
         "delta_ic": r["delta_ic_up"] if r["delta_ic_up"] is not None else 0.0}
        for p, r in lopo_results.items()
    ])
    df = df.sort_values("delta_auc", ascending=False).reset_index(drop=True)

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # (a) ΔAUC macro
    ax = axes[0]
    colors = [PILLAR_COLOR.get(p, "#888") for p in df["pillar"]]
    y_pos = np.arange(len(df))
    ax.barh(y_pos, df["delta_auc"] * 100, color=colors, alpha=0.85,
            edgecolor="#333", linewidth=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([f"{z}  (n={n})" for z, n in zip(df["zh"], df["n_feats"])],
                        fontproperties=prop, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel("ΔAUC macro [pp] = baseline − LOPO", fontproperties=prop, fontsize=11)
    ax.set_title(f"(a) 支柱邊際貢獻（xgboost_D20, baseline AUC={baseline['auc_macro']:.4f}）",
                 fontproperties=prop, fontsize=12)
    ax.grid(alpha=0.3, axis="x")
    for i, v in enumerate(df["delta_auc"]):
        ax.text(v * 100 + 0.01, i, f"{v*100:+.2f}", va="center", fontsize=9,
                color="#111")

    # (b) ΔAUC_up + ΔIC
    ax = axes[1]
    width = 0.38
    x = np.arange(len(df))
    ax.bar(x - width / 2, df["delta_auc_up"] * 100, width,
           color="#10b981", alpha=0.85, label="ΔAUC (up 類)")
    ax.bar(x + width / 2, df["delta_ic"] * 100, width,
           color="#636EFA", alpha=0.85, label="ΔIC (rank corr up_prob vs y)")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(df["zh"], rotation=30, ha="right",
                       fontproperties=prop, fontsize=10)
    ax.set_ylabel("Δ (pp)", fontproperties=prop, fontsize=11)
    ax.set_title("(b) 對上漲判別力的邊際貢獻",
                 fontproperties=prop, fontsize=12)
    ax.legend(prop=prop, fontsize=10)
    ax.grid(alpha=0.3, axis="y")

    fig.suptitle(
        f"LOPO Pillar Contribution — xgboost_D20 | OOS test n={baseline['n_test']:,} days "
        f"| baseline AUC={baseline['auc_macro']:.4f}  LogLoss={baseline['logloss']:.4f}  "
        f"IC_up={baseline['ic_up']:.4f}",
        fontproperties=prop, fontsize=13, y=0.995,
    )
    fig.tight_layout()
    out_png = FIG_DIR / "lopo_pillar_contribution_D20.png"
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {out_png.name}", flush=True)

    # 8. JSON report
    report = {
        "model": "xgboost_D20",
        "method": "Leave-One-Pillar-Out (LOPO)",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "note": ("Last-fold split, xgboost_D20, 200k stratified train subsample. "
                 "ΔAUC = baseline_AUC − LOPO_AUC (higher ΔAUC = pillar contributes more)."),
        "baseline": baseline,
        "baseline_elapsed_sec": round(t_baseline, 2),
        "n_selected_features": len(selected),
        "pillar_counts": {p: len(v) for p, v in by_pillar.items()},
        "lopo_results": lopo_results,
        "ranking_by_delta_auc": df.to_dict(orient="records"),
    }
    out_json = REPORT_DIR / "lopo_pillar_contribution_D20.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"  → {out_json.name}", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
