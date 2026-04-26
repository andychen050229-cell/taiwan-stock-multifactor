#!/usr/bin/env python3
"""
Phase 3 Extended Analytics（搭配治理監控一起跑）

本腳本負責產出 Phase 4 報告會用到的進階分析：
  A. 成本敏感度熱力圖（Cost Sensitivity Heatmap）
  B. 跨 horizon × model 指標熱力圖（AUC / IC / Sharpe）
  C. 支柱貢獻度分析（Pillar Contribution，基於 feature importance 聚合）
  D. 個股 Case Study（3-5 檔代表性股票：預測信號 vs 實際報酬）

輸入：
  outputs/reports/phase2_report_*.json（最新）
  outputs/models/{eng}_D{h}_model.joblib
  outputs/feature_store_final.parquet

輸出：
  outputs/figures/phase3_*.png
  outputs/reports/phase3_analytics_{timestamp}.json
"""

import sys
import os
import json
import io
import ctypes
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick


# ============================================================
# Windows Job Object 記憶體硬限制（避免整機停住）
# ============================================================
def _set_memory_cap_windows(limit_gb: float = 6.0) -> None:
    if sys.platform != "win32":
        return
    try:
        kernel32 = ctypes.windll.kernel32

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [("ReadOperationCount", ctypes.c_ulonglong),
                        ("WriteOperationCount", ctypes.c_ulonglong),
                        ("OtherOperationCount", ctypes.c_ulonglong),
                        ("ReadTransferCount", ctypes.c_ulonglong),
                        ("WriteTransferCount", ctypes.c_ulonglong),
                        ("OtherTransferCount", ctypes.c_ulonglong)]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                        ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", ctypes.c_uint32),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", ctypes.c_uint32),
                        ("Affinity", ctypes.c_size_t),
                        ("PriorityClass", ctypes.c_uint32),
                        ("SchedulingClass", ctypes.c_uint32)]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                        ("IoInfo", IO_COUNTERS),
                        ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
        JobObjectExtendedLimitInformation = 9

        hJob = kernel32.CreateJobObjectW(None, None)
        if not hJob:
            return
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = (
            JOB_OBJECT_LIMIT_PROCESS_MEMORY | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        info.ProcessMemoryLimit = int(limit_gb * 1024 * 1024 * 1024)
        ok = kernel32.SetInformationJobObject(
            hJob, JobObjectExtendedLimitInformation,
            ctypes.byref(info), ctypes.sizeof(info)
        )
        if not ok:
            return
        kernel32.AssignProcessToJobObject(hJob, kernel32.GetCurrentProcess())
        print(f"[memory-cap] analytics Job Object limit set to {limit_gb:.1f} GB", flush=True)
    except Exception as e:
        print(f"[memory-cap] WARN: {e}", flush=True)


_MEMCAP_GB = float(os.environ.get("PHASE3_MEM_CAP_GB", "6.0"))
_set_memory_cap_windows(_MEMCAP_GB)


sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config_loader import load_config
from src.utils.logger import get_logger


# ============================================================
# 工具函式
# ============================================================
def _latest_p2_report(report_dir: Path) -> Path:
    cands = sorted(report_dir.glob("phase2_report_*.json"), reverse=True)
    if not cands:
        raise FileNotFoundError(f"No phase2_report_*.json in {report_dir}")
    return cands[0]


def _setup_matplotlib_cjk():
    """讓中文在 matplotlib 不變成方塊。"""
    try:
        plt.rcParams["font.family"] = ["Microsoft JhengHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
    except Exception:
        pass


# ============================================================
# A. 成本敏感度熱力圖
# ============================================================
def build_cost_sensitivity(p2_report: dict, fig_dir: Path, log) -> dict:
    """3 cost scenarios × 9 models → Return / Sharpe / MDD 熱力圖。"""
    log.info("\n[A] Cost Sensitivity Heatmap...")
    res = p2_report["results"]
    horizons = [1, 5, 20]
    engines = ["lightgbm", "xgboost", "ensemble"]
    costs = ["standard", "discount", "conservative"]

    # 建立 Return / Sharpe / MDD 三個矩陣（row = model-horizon, col = cost）
    models = [f"{eng}_D{h}" for h in horizons for eng in engines]
    metrics = {"total_return": {}, "sharpe_ratio": {}, "max_drawdown": {}}

    for h in horizons:
        bt = res.get(f"backtest_horizon_{h}", {})
        for eng in engines:
            m = bt.get(eng, {}).get("cost_scenarios", {})
            key = f"{eng}_D{h}"
            for metric in metrics:
                metrics[metric][key] = [m.get(c, {}).get(metric, np.nan) for c in costs]

    data = {m: pd.DataFrame(v, index=costs).T for m, v in metrics.items()}

    # 繪圖：1×3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(18, 7))
    titles = {
        "total_return": "Total Return (%)",
        "sharpe_ratio": "Sharpe Ratio",
        "max_drawdown": "Max Drawdown (%)",
    }
    cmaps = {"total_return": "RdYlGn", "sharpe_ratio": "RdYlGn", "max_drawdown": "RdYlGn"}
    formatters = {
        "total_return": lambda v: f"{v*100:+.1f}%" if not pd.isna(v) else "—",
        "sharpe_ratio": lambda v: f"{v:+.2f}" if not pd.isna(v) else "—",
        "max_drawdown": lambda v: f"{v*100:.1f}%" if not pd.isna(v) else "—",
    }

    for i, metric in enumerate(["total_return", "sharpe_ratio", "max_drawdown"]):
        df = data[metric]
        df_display = df.copy()
        if metric == "total_return":
            df_display = df_display * 100
        elif metric == "max_drawdown":
            df_display = df_display * 100

        vmin, vmax = df_display.min().min(), df_display.max().max()
        if metric == "max_drawdown":
            # MDD 是負值，顏色反向（越接近 0 越好）
            im = axes[i].imshow(df_display.values, aspect="auto", cmap=cmaps[metric], vmin=vmin, vmax=0)
        else:
            # 對稱置中 0
            abs_max = max(abs(vmin), abs(vmax), 1e-6)
            im = axes[i].imshow(df_display.values, aspect="auto", cmap=cmaps[metric], vmin=-abs_max, vmax=abs_max)

        axes[i].set_xticks(range(len(costs)))
        axes[i].set_xticklabels([c.capitalize() for c in costs])
        axes[i].set_yticks(range(len(models)))
        axes[i].set_yticklabels(models, fontsize=9)
        axes[i].set_title(titles[metric], fontsize=12, fontweight="bold")
        axes[i].set_xlabel("Cost Scenario")

        # 加數值標註
        for y in range(len(models)):
            for x in range(len(costs)):
                v = df.iloc[y, x]
                axes[i].text(x, y, formatters[metric](v), ha="center", va="center",
                             fontsize=8, color="black", fontweight="bold")

        plt.colorbar(im, ax=axes[i], fraction=0.046, pad=0.04)

    fig.suptitle("Cost Sensitivity Analysis (9 models × 3 cost scenarios)",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    out = fig_dir / "phase3_cost_sensitivity_heatmap.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {out.name}")

    return {
        "models": models,
        "costs": costs,
        "return_matrix": {m: v.values.tolist() for m, v in [(m, data["total_return"].loc[[m]]) for m in models]},
    }


# ============================================================
# B. 跨 horizon × model 指標熱力圖
# ============================================================
def build_cross_horizon_heatmap(p2_report: dict, fig_dir: Path, log) -> dict:
    """AUC / IC / Sharpe 在 model × horizon 上的全景比較。"""
    log.info("\n[B] Cross-Horizon Comparison Heatmap...")
    res = p2_report["results"]
    horizons = [1, 5, 20]
    engines = ["lightgbm", "xgboost", "ensemble"]

    # 取 AUC
    auc_mat = np.full((len(engines), len(horizons)), np.nan)
    ic_mat = np.full((len(engines), len(horizons)), np.nan)
    sharpe_mat = np.full((len(engines), len(horizons)), np.nan)

    for j, h in enumerate(horizons):
        model_key = f"model_horizon_{h}"
        m_h = res.get(model_key, {})
        bt_h = res.get(f"backtest_horizon_{h}", {})

        for i, eng in enumerate(engines):
            # AUC
            eng_metrics = m_h.get(eng, {})
            if "metrics" in eng_metrics:
                auc = eng_metrics["metrics"].get("auc", np.nan)
            else:
                auc = eng_metrics.get("auc", np.nan)
            auc_mat[i, j] = auc

            # IC (rank_ic in backtest)
            bt_eng = bt_h.get(eng, {})
            ic_mat[i, j] = bt_eng.get("rank_ic", np.nan)

            # Sharpe (from discount cost scenario)
            cs = bt_eng.get("cost_scenarios", {}).get("discount", {})
            sharpe_mat[i, j] = cs.get("sharpe_ratio", np.nan)

    # 繪圖
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    configs = [
        ("AUC", auc_mat, "RdYlGn", 0.5, 0.70, ".4f"),
        ("Rank IC", ic_mat, "RdYlGn", -0.03, 0.03, "+.4f"),
        ("Sharpe (discount)", sharpe_mat, "RdYlGn", -3.0, 1.0, "+.2f"),
    ]

    for ax, (title, mat, cmap, vmin, vmax, fmt) in zip(axes, configs):
        im = ax.imshow(mat, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_xticks(range(len(horizons)))
        ax.set_xticklabels([f"D+{h}" for h in horizons])
        ax.set_yticks(range(len(engines)))
        ax.set_yticklabels(engines)
        ax.set_title(title, fontsize=12, fontweight="bold")

        for i in range(len(engines)):
            for j in range(len(horizons)):
                v = mat[i, j]
                txt = f"{v:{fmt}}" if not np.isnan(v) else "—"
                ax.text(j, i, txt, ha="center", va="center", fontsize=11,
                        color="black", fontweight="bold")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle("Cross-Horizon Performance Matrix", fontsize=14, fontweight="bold")
    plt.tight_layout()
    out = fig_dir / "phase3_cross_horizon_heatmap.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {out.name}")

    return {
        "engines": engines,
        "horizons": horizons,
        "auc": auc_mat.tolist(),
        "rank_ic": ic_mat.tolist(),
        "sharpe": sharpe_mat.tolist(),
    }


# ============================================================
# C. 支柱貢獻度分析
# ============================================================
def build_pillar_contribution(p2_report: dict, model_dir: Path, fig_dir: Path, log) -> dict:
    """
    從 Phase 2 report 中每個模型的 top_features 聚合成支柱貢獻度。
    優先用 p2_report JSON（無需載入 joblib，避免記憶體/版本衝突）。
    """
    log.info("\n[C] Pillar Contribution Analysis (from p2_report top_features)...")

    selected = p2_report["results"]["feature_selection"].get("selected", [])
    log.info(f"  Total selected features: {len(selected)}")

    # 支柱前綴
    pillars = ["trend_", "fund_", "val_", "event_", "risk_", "chip_", "ind_", "txt_", "sent_"]

    # 取支柱標籤
    def pillar_of(fname):
        for p in pillars:
            if fname.startswith(p):
                return p.rstrip("_")
        return "other"

    engines = ["lightgbm", "xgboost"]
    horizons = [1, 5, 20]

    pillar_importance = {}
    feature_count_by_pillar = Counter(pillar_of(f) for f in selected)

    for eng in engines:
        for h in horizons:
            model_name = f"{eng}_D{h}"
            try:
                tf = p2_report["results"][f"model_horizon_{h}"][eng].get("top_features", {})
            except Exception:
                tf = {}
            if not tf:
                log.warning(f"  {model_name}: no top_features in report")
                continue

            # 正規化
            total = sum(tf.values()) or 1e-12
            imp_norm = {k: v / total for k, v in tf.items()}

            # 聚合到支柱
            by_pillar = defaultdict(float)
            for f, v in imp_norm.items():
                by_pillar[pillar_of(f)] += float(v)

            pillar_importance[model_name] = dict(by_pillar)
            log.info(f"  {model_name}: {len(tf)} top features aggregated")

    if not pillar_importance:
        log.warning("  No pillar importance data — skipping")
        return {}

    # 組成 DataFrame：row = model, col = pillar
    all_pillars = sorted(set().union(*(d.keys() for d in pillar_importance.values())))
    df = pd.DataFrame(0.0, index=list(pillar_importance.keys()), columns=all_pillars)
    for m, d in pillar_importance.items():
        for p, v in d.items():
            df.loc[m, p] = v

    # 繪圖 1: stacked bar per model
    fig, ax = plt.subplots(figsize=(12, 6))
    pillar_colors = {
        "trend": "#1f77b4", "fund": "#2ca02c", "val": "#9467bd",
        "event": "#ff7f0e", "risk": "#d62728", "chip": "#8c564b",
        "ind": "#e377c2", "txt": "#7f7f7f", "sent": "#bcbd22",
        "other": "#17becf",
    }
    df_ordered = df[all_pillars]
    bottom = np.zeros(len(df))
    for p in all_pillars:
        vals = df_ordered[p].values
        ax.bar(df.index, vals, bottom=bottom, label=p, color=pillar_colors.get(p, "gray"))
        bottom += vals

    ax.set_ylabel("Normalized Importance Share")
    ax.set_title("Pillar Contribution by Model (Sum of Normalized Feature Importance)",
                 fontsize=13, fontweight="bold")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    out1 = fig_dir / "phase3_pillar_contribution.png"
    plt.savefig(out1, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {out1.name}")

    # 繪圖 2: average across models
    avg = df.mean(axis=0).sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [pillar_colors.get(p, "gray") for p in avg.index]
    ax.barh(avg.index, avg.values, color=colors)
    for i, (p, v) in enumerate(avg.items()):
        ax.text(v + 0.005, i, f"{v:.1%} ({feature_count_by_pillar[p]} feat)",
                va="center", fontsize=10)
    ax.set_xlabel("Average Importance Share (across all models)")
    ax.set_title("Pillar Contribution — Grand Average", fontsize=13, fontweight="bold")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_xlim(0, avg.max() * 1.25)
    plt.tight_layout()
    out2 = fig_dir / "phase3_pillar_average.png"
    plt.savefig(out2, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {out2.name}")

    return {
        "pillar_by_model": {m: d for m, d in pillar_importance.items()},
        "pillar_average": avg.to_dict(),
        "feature_count_by_pillar": dict(feature_count_by_pillar),
    }


# ============================================================
# D. Case Study：用 OOF 預測 + 特徵商店 ID/Date 對照
# ============================================================
def build_case_study(id_date_df: pd.DataFrame, oof_dir: Path,
                     fig_dir: Path, log, n_cases: int = 4) -> dict:
    """
    從 Phase 2 已產出的 OOF 預測 (_temp_oof_xgboost_D20.npz)
    + feature store 的 (stock_id, trade_date) 索引對照，
    畫出幾檔代表性股票的「預測 UP 機率 vs 實際 D+20 類別」時序圖。

    好處：
      - 不需要載入 model joblib（避免舊版本欄位不對）
      - 不需要重跑 predict_proba
      - 完全用 OOF，符合 walk-forward 無洩漏原則
    """
    log.info("\n[D] Individual Stock Case Study (from OOF)...")

    # 載入 xgboost_D20 OOF
    oof_path = oof_dir / "_temp_oof_xgboost_D20.npz"
    if not oof_path.exists():
        log.warning(f"  Missing OOF: {oof_path.name}")
        return {}

    data = np.load(str(oof_path))
    pred = data["predictions"]  # shape (N, 3) — [DOWN, FLAT, UP]
    labels = data["labels"]      # shape (N,)

    # 對齊 id/date 的列數
    if len(id_date_df) != len(pred):
        log.warning(f"  Shape mismatch: FS {len(id_date_df)} vs OOF {len(pred)}")
        return {}

    # 把 OOF 合併回 id/date
    id_date_df = id_date_df.reset_index(drop=True).copy()
    id_date_df["up_prob"] = pred[:, 2]
    id_date_df["oof_label"] = labels

    valid_mask = ~np.isnan(pred[:, 2]) & ~np.isnan(labels)
    valid_df = id_date_df[valid_mask].copy()
    log.info(f"  Valid OOF rows: {len(valid_df):,} / {len(id_date_df):,}")

    if valid_df.empty:
        log.warning("  No valid OOF — skipping")
        return {}

    # 挑選股票
    stock_stats = valid_df.groupby("company_id").size().reset_index(name="n_valid")
    stock_stats = stock_stats[stock_stats["n_valid"] >= 100]

    # 偏好台股大型股（嘗試多種 id 格式）
    preferred = ["2330", "2317", "2454", "2303", "2382", "1301", "2891", "2881", "2412"]
    stock_ids_str = stock_stats["company_id"].astype(str)
    avail_preferred = [s for s in preferred if s in stock_ids_str.values]
    chosen = avail_preferred[:n_cases]

    if len(chosen) < n_cases:
        remaining_stats = stock_stats[~stock_ids_str.isin(chosen)]
        extra = remaining_stats.nlargest(n_cases - len(chosen), "n_valid")["company_id"].astype(str).tolist()
        chosen.extend(extra)

    log.info(f"  Selected stocks: {chosen}")

    case_results = {}
    fig, axes = plt.subplots(len(chosen), 1, figsize=(14, 3.0 * len(chosen)), sharex=False)
    if len(chosen) == 1:
        axes = [axes]

    for idx, sid in enumerate(chosen):
        sub = valid_df[valid_df["company_id"].astype(str) == sid].sort_values("trade_date")
        if sub.empty:
            continue

        ax = axes[idx]
        ax2 = ax.twinx()

        ax.plot(sub["trade_date"], sub["up_prob"], color="tab:blue",
                label="OOF UP prob (xgboost_D20)", linewidth=1.2, alpha=0.85)
        ax.axhline(0.40, color="blue", linestyle=":", alpha=0.3)
        ax.axhline(0.50, color="red", linestyle=":", alpha=0.3)

        ret_class = sub["oof_label"].map({0.0: -1, 1.0: 0, 2.0: 1})
        ax2.scatter(sub["trade_date"], ret_class, color="tab:orange", s=6,
                    alpha=0.4, label="Actual D+20 class (-1/0/+1)")

        ax.set_ylabel("UP Prob", color="tab:blue")
        ax2.set_ylabel("Actual class", color="tab:orange")
        ax.set_ylim(0, 1)
        ax2.set_ylim(-1.5, 1.5)
        ax.grid(alpha=0.3)

        # 統計
        avg_prob = float(sub["up_prob"].mean())
        pred_up_mask = sub["up_prob"] > 0.40
        hits = int(((pred_up_mask) & (sub["oof_label"] == 2.0)).sum())
        total_up_calls = int(pred_up_mask.sum())
        hit_rate = hits / max(total_up_calls, 1)
        base_up_rate = float((sub["oof_label"] == 2.0).mean())

        title = (f"Stock {sid}  (n={len(sub)} valid, avg UP prob={avg_prob:.2%}, "
                 f"hit-rate when prob>0.40: {hit_rate:.1%} vs base {base_up_rate:.1%})")
        ax.set_title(title, fontsize=10)

        case_results[sid] = {
            "n_valid_days": int(len(sub)),
            "avg_up_prob": avg_prob,
            "hit_rate_when_up_called": hit_rate,
            "n_up_calls": total_up_calls,
            "n_hits": hits,
            "base_up_rate": base_up_rate,
        }

    fig.suptitle("Case Study — Individual Stock OOF Predictions (xgboost_D20)",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    out = fig_dir / "phase3_case_study.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {out.name}")

    return case_results


# ============================================================
# Main
# ============================================================
def main():
    _setup_matplotlib_cjk()
    config = load_config()
    log = get_logger("phase3_analytics", config)
    root = Path(config.get("_project_root", "."))

    log.info("=" * 70)
    log.info("Phase 3 Extended Analytics")
    log.info("=" * 70)

    report_dir = root / config["paths"]["reports"]
    fig_dir = root / config["paths"]["figures"]
    model_dir = root / config["paths"]["outputs"] / "models"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # 載入 Phase 2 最新報告
    p2_path = _latest_p2_report(report_dir)
    log.info(f"  P2 report: {p2_path.name}")
    with io.open(p2_path, "r", encoding="utf-8") as f:
        p2_report = json.load(f)

    # Feature store 路徑（延後載入，只在 case study 需要時才讀）
    fs_path = root / config["paths"]["outputs"] / "feature_store_final.parquet"
    if not fs_path.exists():
        fs_path = root / config["paths"]["outputs"] / "feature_store.parquet"
    log.info(f"  Feature store (lazy): {fs_path.name}")

    selected = p2_report["results"]["feature_selection"].get("selected", [])

    results = {}

    # A. Cost sensitivity（僅用 Phase 2 JSON，不需 FS）
    try:
        results["cost_sensitivity"] = build_cost_sensitivity(p2_report, fig_dir, log)
    except Exception as e:
        log.error(f"[A] FAILED: {e}")
        results["cost_sensitivity"] = {"error": str(e)}

    # B. Cross-horizon（僅用 Phase 2 JSON）
    try:
        results["cross_horizon"] = build_cross_horizon_heatmap(p2_report, fig_dir, log)
    except Exception as e:
        log.error(f"[B] FAILED: {e}")
        results["cross_horizon"] = {"error": str(e)}

    # C. Pillar contribution（只需要模型）
    try:
        results["pillar_contribution"] = build_pillar_contribution(p2_report, model_dir, fig_dir, log)
    except Exception as e:
        log.error(f"[C] FAILED: {e}")
        results["pillar_contribution"] = {"error": str(e)}

    # D. Case study（用 OOF 預測；只需要 stock_id + trade_date 兩欄）
    try:
        import pyarrow.parquet as pq
        log.info(f"  [D] Loading only (stock_id, trade_date) from feature store...")
        table = pq.read_table(str(fs_path), columns=["company_id", "trade_date"])
        id_date_df = table.to_pandas()
        log.info(f"  [D] id/date shape: {id_date_df.shape}")
        oof_dir = root / config["paths"]["outputs"]
        results["case_study"] = build_case_study(id_date_df, oof_dir, fig_dir, log)
        del id_date_df, table
        import gc; gc.collect()
    except Exception as e:
        log.error(f"[D] FAILED: {e}")
        import traceback
        log.error(traceback.format_exc())
        results["case_study"] = {"error": str(e)}

    # 儲存 JSON 摘要
    out_json = report_dir / f"phase3_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with io.open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "source_p2_report": p2_path.name,
            "results": results,
        }, f, ensure_ascii=False, indent=2, default=str)
    log.info(f"\n  Analytics summary: {out_json.name}")

    log.info("\n" + "=" * 70)
    log.info("Phase 3 Analytics DONE")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
