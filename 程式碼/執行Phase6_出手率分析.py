"""Phase 6 Stage 1 — 出手率 / 閾值敏感度分析
=================================================

動機：G10 範例（台泥）在投影片呈現了 predict_threshold 掃描表：
  threshold 0.40 → 41.7% 出手率 / 100% 準確率
  threshold 0.25 → 65.2% 出手率 / 95.2% 準確率
本專案缺此分析，補件。

本腳本以 xgboost_D20 OOF predictions 為基礎，掃描 threshold ∈ [0.30, 0.50]：
  - 出手率        = P(up_prob >= t)
  - 命中率（hit） = P(label == 2 | up_prob >= t)
  - 基準上漲率    = P(label == 2)
  - 邊際優勢 edge = hit - base
  - Precision@TopK（模型 top-K 預測的命中率）

輸出：
  outputs/figures/threshold_sweep_xgb_D20.png
  outputs/reports/threshold_sweep_xgb_D20.json

執行方式：
  python 程式碼/執行Phase6_出手率分析.py
"""
from __future__ import annotations

import sys
import io
import json
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"
FIG_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

FONT_PATH = "C:/Windows/Fonts/mingliu.ttc"
prop = fm.FontProperties(fname=FONT_PATH)
plt.rcParams["font.sans-serif"] = [prop.get_name()]
plt.rcParams["axes.unicode_minus"] = False


def main():
    print("=" * 70, flush=True)
    print("Phase 6 Stage 1 — 出手率 / 閾值敏感度分析", flush=True)
    print("=" * 70, flush=True)

    # 1. 載入 OOF xgb_D20
    oof_path = PROJECT_ROOT / "outputs" / "_temp_oof_xgboost_D20.npz"
    if not oof_path.exists():
        print(f"找不到 OOF：{oof_path}", flush=True)
        sys.exit(1)
    d = np.load(str(oof_path), allow_pickle=True)
    preds = d["predictions"]   # (N, 3) — 0=down, 1=flat, 2=up
    labels = d["labels"]

    valid = ~np.isnan(labels)
    up_prob = preds[:, 2][valid]
    y = labels[valid].astype(int)
    n_total = len(y)
    base_up = (y == 2).mean()
    print(f"OOS rows: {n_total:,}    base P(up)={base_up:.3%}", flush=True)

    # 2. Threshold sweep（對應 G10 的 table）
    thresholds = np.arange(0.30, 0.51, 0.01)
    rows = []
    for t in thresholds:
        mask = up_prob >= t
        n_call = int(mask.sum())
        call_rate = n_call / n_total
        if n_call == 0:
            hit_rate = np.nan
            edge = np.nan
        else:
            hit_rate = (y[mask] == 2).mean()
            edge = hit_rate - base_up
        rows.append({
            "threshold": round(float(t), 3),
            "n_calls": n_call,
            "call_rate": call_rate,
            "hit_rate": hit_rate,
            "base_up_rate": base_up,
            "edge": edge,
        })
    sweep = pd.DataFrame(rows)
    print("\n=== 閾值掃描表（up_prob 分類為 class-2） ===", flush=True)
    print(sweep.to_string(index=False), flush=True)

    # 3. Precision@TopK（對應「每日挑 K 支」實戰思路）
    ks = [1, 3, 5, 10, 20, 50, 100]
    topk_rows = []
    df_pred = pd.DataFrame({"up_prob": up_prob, "y": y})
    # 單一 OOS 期間的 top-K（全域排序，不分日期）
    for k_pct in [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10]:
        k = max(1, int(n_total * k_pct))
        top = df_pred.nlargest(k, "up_prob")
        hit = (top["y"] == 2).mean()
        edge = hit - base_up
        topk_rows.append({
            "top_pct": k_pct,
            "n_picks": k,
            "hit_rate": hit,
            "edge": edge,
        })
    topk = pd.DataFrame(topk_rows)
    print("\n=== Top-K Precision（全域排序） ===", flush=True)
    print(topk.to_string(index=False), flush=True)

    # 4. 繪圖
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))

    # (a) 出手率 vs 命中率
    ax = axes[0, 0]
    ax2 = ax.twinx()
    ax.plot(sweep["threshold"], sweep["call_rate"], "b-o", markersize=5,
            label="出手率 (call rate)")
    ax2.plot(sweep["threshold"], sweep["hit_rate"], "r-s", markersize=5,
             label="命中率 (P(label=up | call))")
    ax2.axhline(base_up, color="gray", linestyle="--", alpha=0.6,
                label=f"基準上漲率 {base_up:.2%}")
    ax.set_xlabel("predict_threshold", fontproperties=prop)
    ax.set_ylabel("出手率", color="b", fontproperties=prop)
    ax2.set_ylabel("命中率", color="r", fontproperties=prop)
    ax.set_title("(a) 出手率 × 命中率 vs 閾值",
                 fontproperties=prop, fontsize=13)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", prop=prop, fontsize=9)
    ax2.legend(loc="lower right", prop=prop, fontsize=9)

    # (b) Edge over base
    ax = axes[0, 1]
    ax.bar(sweep["threshold"], sweep["edge"] * 100,
           color=["#10b981" if v > 0 else "#ef4444" for v in sweep["edge"]], alpha=0.85,
           width=0.008)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("predict_threshold", fontproperties=prop)
    ax.set_ylabel("邊際優勢 (hit − base) [pp]", fontproperties=prop)
    ax.set_title("(b) 相對基準的命中率優勢",
                 fontproperties=prop, fontsize=13)
    ax.grid(alpha=0.3, axis="y")

    # (c) Top-K precision
    ax = axes[1, 0]
    ax.plot(topk["top_pct"] * 100, topk["hit_rate"] * 100, "b-o", markersize=7)
    ax.axhline(base_up * 100, color="gray", linestyle="--", alpha=0.6,
               label=f"基準上漲率 {base_up:.2%}")
    ax.set_xlabel("取樣百分比 (%)", fontproperties=prop)
    ax.set_ylabel("命中率 (%)", fontproperties=prop)
    ax.set_title("(c) Top-K% Precision（全域排序）",
                 fontproperties=prop, fontsize=13)
    ax.set_xscale("log")
    for _, r in topk.iterrows():
        ax.annotate(f"{r['hit_rate']:.1%}",
                    (r["top_pct"] * 100, r["hit_rate"] * 100),
                    textcoords="offset points", xytext=(5, 5), fontsize=8)
    ax.legend(prop=prop, fontsize=9)
    ax.grid(alpha=0.3, which="both")

    # (d) up_prob distribution with thresholds highlighted
    ax = axes[1, 1]
    ax.hist(up_prob, bins=60, color="#636EFA", alpha=0.7)
    for t, c in [(0.35, "#f59e0b"), (0.40, "#ef4444"), (0.45, "#8b5cf6")]:
        ax.axvline(t, linestyle="--", color=c, linewidth=2,
                   label=f"t={t}  call_rate={((up_prob >= t).mean()):.1%}")
    ax.set_xlabel("up_prob (class-2 probability)", fontproperties=prop)
    ax.set_ylabel("count", fontproperties=prop)
    ax.set_title("(d) OOS 預測機率分布 + 代表性閾值",
                 fontproperties=prop, fontsize=13)
    ax.legend(prop=prop, fontsize=9)
    ax.grid(alpha=0.3, axis="y")

    fig.suptitle(f"xgboost_D20 閾值敏感度｜OOS n={n_total:,}, base P(up)={base_up:.2%}",
                 fontproperties=prop, fontsize=15, y=0.995)
    fig.tight_layout()

    out_png = FIG_DIR / "threshold_sweep_xgb_D20.png"
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n→ {out_png.name}", flush=True)

    # 5. JSON 報告
    report = {
        "model": "xgboost_D20",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "oos_n": int(n_total),
        "base_up_rate": float(base_up),
        "threshold_sweep": sweep.to_dict(orient="records"),
        "top_k_precision": topk.to_dict(orient="records"),
        "highlighted_thresholds": {
            "conservative_0.40": _fmt(sweep[sweep["threshold"] == 0.40]),
            "balanced_0.35":      _fmt(sweep[sweep["threshold"] == 0.35]),
            "aggressive_0.30":    _fmt(sweep[sweep["threshold"] == 0.30]),
        },
    }
    out_json = REPORT_DIR / "threshold_sweep_xgb_D20.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"→ {out_json.name}", flush=True)
    print("=" * 70, flush=True)


def _fmt(row):
    if row.empty:
        return None
    r = row.iloc[0]
    return {
        "threshold": float(r["threshold"]),
        "call_rate": float(r["call_rate"]),
        "hit_rate": float(r["hit_rate"]) if pd.notna(r["hit_rate"]) else None,
        "edge": float(r["edge"]) if pd.notna(r["edge"]) else None,
    }


if __name__ == "__main__":
    main()
