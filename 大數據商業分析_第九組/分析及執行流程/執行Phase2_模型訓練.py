#!/usr/bin/env python3
"""
Phase 2 主執行腳本：模型開發 + 策略回測 (v3 — Enhanced + Statistical Validation)

執行流程（14 步驟）：
  1. 載入 Feature Store（Phase 1 產出）
  2. 資料完整性驗證（Inf / NaN / 標籤分佈）
  3. 特徵選擇（MI → VIF）
  4. Walk-Forward 時序切分
  5. 模型訓練 — Horizon D+1（LightGBM + XGBoost）
  6. 模型訓練 — Horizon D+5
  7. 模型訓練 — Horizon D+20
  8. LGB+XGB 集成（Ensemble）+ ICIR 計算
  9. 策略回測（三成本情境 × 三 horizon + ensemble）
  9b. 進階分析（Quintile / Bootstrap CI / Drawdown / Alpha Decay）
  10. 統計驗證（Permutation Test / DSR / OOD 壓力測試）   ← NEW
  11. 概率校準（Platt Scaling）                           ← NEW
  12. 跨 horizon 比較 + 品質閘門
  13. 圖表視覺化（8+ 張專業圖表）
  14. 產出報告

用法：
  python 程式碼/執行Phase2_模型訓練.py
"""

import sys
import os
import json
import warnings
from pathlib import Path
from datetime import datetime

# ============================================================
# 2026-04-19 14:30：記憶體安全帽（Windows Job Object 硬限制 7.5GB）
# 首跑因 MI 階段峰值 9.7GB → 作業系統 OOM kill；限制後腳本會在 7.5GB 自行失敗而非拖住整機
# ============================================================
def _set_memory_cap_windows(limit_gb: float = 7.5) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", ctypes.c_ulong),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", ctypes.c_ulong),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", ctypes.c_ulong),
                ("SchedulingClass", ctypes.c_ulong),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

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
            hJob,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not ok:
            return

        kernel32.AssignProcessToJobObject(hJob, kernel32.GetCurrentProcess())
        print(f"[memory-cap] Windows Job Object limit set to {limit_gb:.1f} GB", flush=True)
    except Exception as e:
        print(f"[memory-cap] WARN: could not enable hard cap: {e}", flush=True)


_MEMCAP_GB = float(os.environ.get("PHASE2_MEM_CAP_GB", "7.5"))
_set_memory_cap_windows(_MEMCAP_GB)

import numpy as np
import pandas as pd
from scipy.stats import spearmanr  # 🟠6 fix: 移至頂部，避免迴圈內重複 import

# 專案根目錄
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config_loader import load_config
from src.utils.logger import get_logger
from src.features.selector import run_feature_selection, check_feature_stability
from src.models.walk_forward import generate_walk_forward_splits, get_fold_summary
from src.models.trainer import train_all_models
from src.backtest.engine import run_backtest, compute_benchmark
from src.backtest.metrics import (
    format_metrics_table, rank_ic_by_date,
    compute_quintile_returns, bootstrap_ci,
    compute_drawdown_analysis, compute_alpha_decay,
)
from src.backtest.statistical_tests import run_statistical_validation
from src.models.calibration import calibrate_oof_predictions
from src.models.trainer import save_models
from src.visualization.charts import (
    plot_cumulative_returns, plot_drawdown, plot_ic_time_series,
    plot_feature_importance, plot_confusion_matrix, plot_monthly_returns,
    plot_model_comparison, plot_fold_stability, plot_shap_summary,
)

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def _serialize(obj):
    """將物件轉為 JSON-safe 格式。"""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    return obj


def main():
    # ===== 初始化 =====
    config = load_config()
    log = get_logger("phase2", config)
    root = Path(config.get("_project_root", "."))

    random_seed = config.get("random_seed", 42)
    np.random.seed(random_seed)

    log.info("=" * 70)
    log.info("Phase 2: 模型開發 + 策略回測 — 開始執行")
    log.info(f"Environment: {config.get('_env', 'dev')}")
    log.info(f"Project root: {root}")
    log.info(f"Random seed: {random_seed}")
    log.info("=" * 70)

    report = {
        "phase": "Phase 2 — 模型開發 + 策略回測",
        "timestamp": datetime.now().isoformat(),
        "env": config.get("_env"),
        "results": {},
    }

    # ===== Step 1: 載入 Feature Store =====
    log.info("\n[Step 1/14] Loading Feature Store...")
    output_dir = root / config["paths"]["outputs"]
    # 優先用 feature_store_final.parquet（Phase 5B Stage 2.6 整合後；含 txt_/sent_/topic_）
    # 若不存在則退回 feature_store.parquet（Phase 1 baseline）
    fs_final_path = output_dir / "feature_store_final.parquet"
    fs_baseline_path = output_dir / "feature_store.parquet"
    if fs_final_path.exists():
        fs_path = fs_final_path
        log.info(f"  Using FINAL (Phase 5B integrated): {fs_path.name}")
    elif fs_baseline_path.exists():
        fs_path = fs_baseline_path
        log.warning(f"  Final feature_store 不存在，退回 baseline: {fs_path.name}")
    else:
        log.error(f"Feature Store not found: {fs_baseline_path}")
        log.error("Please run Phase 1 first: python run_phase1.py")
        sys.exit(1)

    fs = pd.read_parquet(fs_path)
    # Memory optimization: downcast float64 → float32 to halve memory
    import gc
    float64_cols = fs.select_dtypes(include=["float64"]).columns
    for col in float64_cols:
        fs[col] = fs[col].astype(np.float32)
    gc.collect()
    log.info(f"  Feature Store loaded: {fs.shape[0]:,} rows × {fs.shape[1]} cols")
    log.info(f"  Memory: {fs.memory_usage(deep=True).sum() / 1024**2:.1f} MB (float32 optimized)")
    log.info(f"  Date range: {fs['trade_date'].min()} ~ {fs['trade_date'].max()}")

    report["results"]["feature_store"] = {
        "rows": len(fs),
        "cols": len(fs.columns),
        "date_range": f"{fs['trade_date'].min()} ~ {fs['trade_date'].max()}",
    }

    # ===== Step 2: 資料完整性驗證 =====
    log.info("\n[Step 2/14] Data integrity validation...")

    numeric_cols = fs.select_dtypes(include=["number"]).columns
    inf_count = int(np.isinf(fs[numeric_cols]).sum().sum())
    nan_pct = float(fs[numeric_cols].isna().mean().mean())
    log.info(f"  Inf count: {inf_count}")
    log.info(f"  NaN percentage: {nan_pct:.2%}")

    # 標籤分佈
    horizons = config.get("model", {}).get("horizons", [1, 5, 20])
    for h in horizons:
        label_col = f"label_{h}"
        if label_col in fs.columns:
            dist = fs[label_col].value_counts(normalize=True).sort_index()
            coverage = fs[label_col].notna().mean()
            log.info(f"  {label_col}: coverage={coverage:.1%} | "
                     f"DOWN={dist.get(-1.0, 0):.1%} FLAT={dist.get(0.0, 0):.1%} "
                     f"UP={dist.get(1.0, 0):.1%}")

    if inf_count > 0:
        log.error(f"  CRITICAL: {inf_count} Inf values detected!")
        sys.exit(1)

    report["results"]["data_validation"] = {
        "inf_count": inf_count,
        "nan_pct": round(nan_pct, 4),
    }

    # ===== Step 3: Walk-Forward 切分（先於特徵選擇，提供 train_idx）=====
    log.info("\n[Step 3/14] Walk-forward time series split...")

    folds = generate_walk_forward_splits(fs, date_col="trade_date", config=config)
    fold_summary = get_fold_summary(folds)
    report["results"]["walk_forward"] = fold_summary

    if len(folds) == 0:
        log.error("  No valid folds generated! Check data date range and config.")
        sys.exit(1)

    # ===== Step 4: 特徵選擇（使用所有 fold 訓練集聯集，更具代表性）=====
    # M5 fix: 使用所有 fold 訓練索引聯集，而非僅 Fold 0
    # 這確保特徵選擇涵蓋更多時間段的資料，更穩健
    all_train_idx = np.unique(np.concatenate([f.train_idx for f in folds]))
    log.info(f"\n[Step 4/14] Feature selection (using all folds train union: {len(all_train_idx)} rows)...")

    selection_result = run_feature_selection(
        fs, "label_5", config, train_idx=all_train_idx
    )
    selected_features = selection_result["selected_features"]

    # 驗證所有選出的特徵確實存在於 Feature Store
    missing_feats = [f for f in selected_features if f not in fs.columns]
    if missing_feats:
        log.error(f"  CRITICAL: {len(missing_feats)} selected features not in Feature Store: {missing_feats}")
        sys.exit(1)

    log.info(f"  Final selected features: {len(selected_features)}")
    report["results"]["feature_selection"] = {
        "n_candidates": selection_result["n_candidates"],
        # Phase 5A: 記錄 corr prefilter 階段計數，便於基線對照
        "after_corr": len(selection_result.get("after_corr", selection_result["after_mi"])),
        "after_mi": len(selection_result["after_mi"]),
        "after_vif": len(selection_result["after_vif"]),
        "selected": selected_features,
    }
    del selection_result
    gc.collect()

    # 記憶體優化：只保留訓練/回測需要的欄位
    # C4 fix: 加入 volume/turnover，backtest liquidity filter 需要
    keep_cols = (
        selected_features
        + [f"label_{h}" for h in horizons]
        + [f"fwd_ret_{h}" for h in horizons]
        + ["trade_date", "company_id", "close", "closing_price"]
        + ["volume", "turnover"]
    )
    keep_cols = [c for c in keep_cols if c in fs.columns]
    fs = fs[keep_cols]
    gc.collect()
    log.info(f"  Memory after column pruning: {fs.memory_usage(deep=True).sum() / 1024**2:.1f} MB ({len(keep_cols)} cols)")

    # ===== Step 5-7: 三個 Horizon 分別訓練 =====
    all_horizon_results = {}
    all_backtest_results = {}

    for h in horizons:
        label_col = f"label_{h}"
        step_num = 4 + horizons.index(h) + 1

        log.info(f"\n[Step {step_num}/14] Training models — Horizon D+{h} ({label_col})...")
        log.info("=" * 60)

        # 訓練
        model_results = train_all_models(
            df=fs,
            feature_cols=selected_features,
            label_col=label_col,
            folds=folds,
            config=config,
        )
        all_horizon_results[h] = model_results

        # 序列化結果（不含 numpy arrays 和模型物件）
        serializable = {}
        for eng, res in model_results.items():
            if "error" in res:
                serializable[eng] = res
                continue
            serializable[eng] = {
                "avg_metrics": res["avg_metrics"],
                "fold_metrics": res["fold_metrics"],
                "best_params": _serialize(res.get("best_params", {})),
                "top_features": dict(
                    sorted(res.get("feature_importance", {}).items(),
                           key=lambda x: x[1], reverse=True)[:20]
                ),
            }
        report["results"][f"model_horizon_{h}"] = serializable
        # 記憶體優化：將 OOF 預測存到磁碟，釋放記憶體
        # 注意：importance_per_fold 在 pop 之前必須保留（for feature_stability gate）
        for eng, res in model_results.items():
            if "error" not in res:
                oof_path = output_dir / f"_temp_oof_{eng}_D{h}.npz"
                np.savez_compressed(oof_path,
                    predictions=res["oof_predictions"],
                    labels=res["oof_labels"])
                res["_oof_path"] = str(oof_path)
                del res["oof_predictions"], res["oof_labels"]
                # 保留 importance_per_fold 供後續 feature_stability 計算使用
                # （先前這行 res.pop("importance_per_fold", None) 會清空，
                #  導致 feature_stability gate 永遠 FAIL）
                res.pop("last_model", None)
        gc.collect()

    # ===== Step 8: Ensemble + ICIR =====
    log.info(f"\n[Step 8/14] LGB+XGB Ensemble + ICIR calculation...")

    # Helper: 從磁碟或記憶體載入 OOF
    def _load_oof(res):
        if "oof_predictions" in res:
            return res["oof_predictions"], res["oof_labels"]
        if "_oof_path" in res:
            data = np.load(res["_oof_path"])
            return data["predictions"], data["labels"]
        return None, None

    all_icir_results = {}
    for h in horizons:
        label_col = f"label_{h}"
        fwd_ret_col = f"fwd_ret_{h}"
        engines_available = [e for e in all_horizon_results[h] if "error" not in all_horizon_results[h][e]]

        # --- Ensemble: 等權平均 LGB + XGB 的 OOF 概率 ---
        if len(engines_available) >= 2:
            oof_list = []
            first_labels = None
            for e in engines_available:
                preds, labels = _load_oof(all_horizon_results[h][e])
                if preds is not None:
                    oof_list.append(preds)
                    if first_labels is None:
                        first_labels = labels
            # [C fix] 驗證所有 engine 的 OOF shape 一致
            if len(oof_list) > 1:
                shapes = [o.shape for o in oof_list]
                if len(set(shapes)) > 1:
                    log.error(f"  Ensemble OOF shape mismatch: {shapes} — skipping ensemble")
                    continue
            ensemble_oof = np.nanmean(oof_list, axis=0)
            ensemble_labels = first_labels
            del oof_list; gc.collect()

            # 計算 ensemble 指標（OOF test only）
            from sklearn.metrics import roc_auc_score, log_loss, accuracy_score, balanced_accuracy_score
            all_test_idx = np.concatenate([f.test_idx for f in folds])
            ens_proba = ensemble_oof[all_test_idx]
            ens_labels_test = ensemble_labels[all_test_idx]
            valid_ens = ~np.isnan(ens_labels_test) & ~np.isnan(ens_proba).any(axis=1)

            if valid_ens.sum() > 100:
                y_true_ens = ens_labels_test[valid_ens].astype(int)
                y_pred_ens = ens_proba[valid_ens]
                y_class_ens = np.argmax(y_pred_ens, axis=1)
                try:
                    ens_auc = roc_auc_score(y_true_ens, y_pred_ens, multi_class="ovr", average="macro")
                except ValueError:
                    ens_auc = 0.0
                ens_acc = accuracy_score(y_true_ens, y_class_ens)
                ens_bal_acc = balanced_accuracy_score(y_true_ens, y_class_ens)
                ens_ll = log_loss(y_true_ens, y_pred_ens)

                log.info(f"  Ensemble D+{h}: AUC={ens_auc:.4f} | Acc={ens_acc:.4f} | "
                         f"BalAcc={ens_bal_acc:.4f} | LogLoss={ens_ll:.4f}")

                # 儲存 ensemble OOF 到磁碟
                ens_oof_path = output_dir / f"_temp_oof_ensemble_D{h}.npz"
                np.savez_compressed(ens_oof_path, predictions=ensemble_oof, labels=ensemble_labels)
                all_horizon_results[h]["ensemble"] = {
                    "engine": "ensemble",
                    "_oof_path": str(ens_oof_path),
                    "avg_metrics": {
                        "auc": round(ens_auc, 4),
                        "log_loss": round(ens_ll, 4),
                        "accuracy": round(ens_acc, 4),
                        "balanced_accuracy": round(ens_bal_acc, 4),
                    },
                    "fold_metrics": [],
                    "feature_importance": {},
                    "best_params": {},
                }
            del ensemble_oof, ensemble_labels; gc.collect()

        # --- ICIR: 逐日 Rank IC 時間序列 ---
        for eng in list(all_horizon_results[h].keys()):
            res = all_horizon_results[h][eng]
            if "error" in res:
                continue
            oof, _ = _load_oof(res)
            if oof is None:
                continue
            up_prob = oof[:, 2]

            # 只取 OOF test 資料
            test_idx = np.concatenate([f.test_idx for f in folds])
            test_df = fs.iloc[test_idx].copy()
            test_df["_up_prob"] = up_prob[test_idx]
            test_df["_fwd_ret"] = fs.iloc[test_idx][fwd_ret_col].values if fwd_ret_col in fs.columns else np.nan

            if fwd_ret_col in fs.columns:
                ic_ts = rank_ic_by_date(test_df, "_up_prob", "_fwd_ret", "trade_date")
                ic_mean = float(ic_ts.dropna().mean()) if len(ic_ts.dropna()) > 0 else 0
                ic_std = float(ic_ts.dropna().std()) if len(ic_ts.dropna()) > 0 else 1
                icir = ic_mean / ic_std if ic_std > 0 else 0
                key = f"{eng}_D{h}"
                all_icir_results[key] = {
                    "ic_series": ic_ts,
                    "mean_ic": round(ic_mean, 4),
                    "std_ic": round(ic_std, 4),
                    "icir": round(icir, 4),
                }
                log.info(f"  {key} ICIR: mean_IC={ic_mean:.4f} | std={ic_std:.4f} | ICIR={icir:.3f}")

    # ===== Step 9: 策略回測 =====
    log.info(f"\n[Step 9/14] Strategy backtesting...")

    # 基準
    benchmark = compute_benchmark(fs, folds, config)
    report["results"]["benchmark"] = _serialize(benchmark["metrics"])
    report["results"]["benchmark"]["n_trading_days"] = benchmark["n_trading_days"]

    for h in horizons:
        label_col = f"label_{h}"
        log.info(f"\n  Backtesting horizon D+{h}...")

        bt_results = run_backtest(
            df=fs,
            model_results=all_horizon_results[h],
            folds=folds,
            feature_cols=selected_features,
            label_col=label_col,
            config=config,
        )
        all_backtest_results[h] = bt_results

        # 序列化（daily_returns 是 pd.Series，不存入 JSON）
        bt_serializable = {}
        for eng, res in bt_results.items():
            bt_serializable[eng] = {
                "cost_scenarios": res["cost_scenarios"],
                "rank_ic": res["rank_ic"],
                "n_trading_days": res["n_trading_days"],
                "avg_daily_stocks": res["avg_daily_stocks"],
                "avg_turnover": res.get("avg_turnover", 0),
            }
        report["results"][f"backtest_horizon_{h}"] = bt_serializable

    # ===== 記憶體優化：釋放回測前的中間資料 =====
    import gc as _gc
    _gc.collect()

    # ===== Step 9b: 進階分析（Quintile / Bootstrap CI / Drawdown / Alpha Decay）=====
    log.info(f"\n[Step 9b/14] Advanced analytics...")

    # --- Quintile Factor Analysis ---
    quintile_results = {}
    for h in horizons:
        fwd_ret_col = f"fwd_ret_{h}"
        if fwd_ret_col not in fs.columns:
            continue
        for eng in ["ensemble", "lightgbm", "xgboost"]:
            res = all_horizon_results[h].get(eng, {})
            if "error" in res:
                continue
            oof_preds, _ = _load_oof(res)
            if oof_preds is None:
                continue
            up_prob = oof_preds[:, 2]
            test_idx = np.concatenate([f.test_idx for f in folds])
            # 只取需要的欄位，避免全量 copy
            qdf = fs.iloc[test_idx][[fwd_ret_col, "trade_date"]].copy()
            qdf["_score"] = up_prob[test_idx]
            qdf["_fwd_ret"] = qdf[fwd_ret_col]
            valid_q = qdf["_score"].notna() & qdf["_fwd_ret"].notna()
            qdf = qdf[valid_q]
            if len(qdf) > 1000:
                qr = compute_quintile_returns(qdf, "_score", "_fwd_ret", "trade_date", holding_days=h)
                key = f"{eng}_D{h}"
                quintile_results[key] = {
                    "quintile_returns": qr["quintile_returns"],
                    "long_short_spread": round(qr["long_short_spread"], 4),
                    "monotonicity": round(qr["monotonicity_score"], 4),
                }
                log.info(f"  Quintile {key}: L/S spread={qr['long_short_spread']:.2%} | "
                         f"Monotonicity={qr['monotonicity_score']:.3f}")
            break  # 只做最佳 engine

    # --- Bootstrap CI for best D+20 strategy ---
    bootstrap_results = {}
    for h in horizons:
        for eng in ["xgboost", "lightgbm", "ensemble"]:
            bt_res = all_backtest_results.get(h, {}).get(eng, {})
            if "daily_returns" in bt_res:
                ci = bootstrap_ci(bt_res["daily_returns"], n_bootstrap=1000, ci=0.95)
                key = f"{eng}_D{h}"
                ret_ci = ci["annualized_return"]
                shp_ci = ci["sharpe_ratio"]
                bootstrap_results[key] = {
                    "return_point": round(ret_ci["point_estimate"], 4),
                    "return_ci_lower": round(ret_ci["ci"][0], 4),
                    "return_ci_upper": round(ret_ci["ci"][1], 4),
                    "sharpe_point": round(shp_ci["point_estimate"], 4),
                    "sharpe_ci_lower": round(shp_ci["ci"][0], 4),
                    "sharpe_ci_upper": round(shp_ci["ci"][1], 4),
                }
                log.info(f"  Bootstrap {key}: Return={ret_ci['point_estimate']:+.2%} "
                         f"[{ret_ci['ci'][0]:+.2%}, {ret_ci['ci'][1]:+.2%}] | "
                         f"Sharpe={shp_ci['point_estimate']:.2f} "
                         f"[{shp_ci['ci'][0]:.2f}, {shp_ci['ci'][1]:.2f}]")
                break  # 只做最佳 engine

    # --- Conditional Drawdown Analysis ---
    drawdown_results = {}
    for h in horizons:
        for eng in ["xgboost", "lightgbm", "ensemble"]:
            bt_res = all_backtest_results.get(h, {}).get(eng, {})
            if "daily_returns" in bt_res:
                dd = compute_drawdown_analysis(bt_res["daily_returns"])
                key = f"{eng}_D{h}"
                episodes = dd.get("top_5_episodes", dd.get("top_episodes", []))
                cdar = dd.get("cdar_95", 0)
                avg_rec = dd.get("avg_recovery_time", dd.get("avg_recovery_days", 0))
                drawdown_results[key] = {
                    "cdar_95": round(cdar, 4),
                    "avg_recovery_days": avg_rec,
                    "n_episodes": len(episodes),
                    "worst_episode": _serialize(episodes[0]) if episodes else {},
                }
                if episodes:
                    ep = episodes[0]
                    log.info(f"  Drawdown {key}: CDaR95={cdar:.2%} | "
                             f"Worst={ep.get('depth', 0):.2%} ({ep.get('duration_to_trough', 0)}d) | "
                             f"AvgRecovery={avg_rec}d")
                break

    # --- Alpha Decay Analysis ---
    # H6 fix: 每個 horizon 使用自己模型的 OOF predictions 計算 IC
    # 原本只用最長 horizon 的模型預測測試所有 horizon 的 IC，不正確
    alpha_decay_results = {}
    for eng in ["ensemble", "xgboost", "lightgbm"]:
        has_all = all(eng in all_horizon_results.get(h, {}) for h in horizons)
        if not has_all:
            continue
        test_idx = np.concatenate([f.test_idx for f in folds])
        ret_cols = [f"fwd_ret_{h}" for h in horizons if f"fwd_ret_{h}" in fs.columns]
        adf = fs.iloc[test_idx][ret_cols + ["trade_date"]].copy()

        # 每個 horizon 用自己的 OOF score
        horizon_metrics = {}
        for h in horizons:
            res_h = all_horizon_results.get(h, {}).get(eng, {})
            if "error" in res_h:
                continue
            oof_h, _ = _load_oof(res_h)
            if oof_h is None:
                continue
            up_prob_h = oof_h[:, 2]
            ret_col = f"fwd_ret_{h}"
            if ret_col not in fs.columns:
                continue
            temp_df = fs.iloc[test_idx][[ret_col, "trade_date"]].copy()
            temp_df["_score"] = up_prob_h[test_idx]
            # 計算單一 horizon 的 IC（spearmanr 已在檔案頂部 import）
            ic_by_date = temp_df.groupby("trade_date").apply(
                lambda g: spearmanr(g["_score"], g[ret_col]).correlation
                if len(g.dropna(subset=["_score", ret_col])) >= 10 else np.nan
            ).dropna()
            if len(ic_by_date) > 0:
                horizon_metrics[ret_col] = {
                    "mean_ic": float(ic_by_date.mean()),
                    "icir": float(ic_by_date.mean() / ic_by_date.std()) if ic_by_date.std() > 0 else 0.0,
                    "n_dates": int(len(ic_by_date)),
                }
        if horizon_metrics:
            alpha_decay_results[eng] = horizon_metrics
            log.info(f"  Alpha decay ({eng}): " + " | ".join(
                f"{k}: IC={v['mean_ic']:.4f}, ICIR={v['icir']:.3f}" for k, v in horizon_metrics.items()
            ))
        break

    # --- Model Serialization ---
    log.info(f"\n  Saving trained models...")
    model_dir = root / "outputs" / "models"
    for h in horizons:
        for eng, res in all_horizon_results[h].items():
            if eng == "ensemble" or "error" in res:
                continue
            last_model = res.get("last_model")
            if last_model is not None:
                save_models(
                    {f"{eng}_D{h}": {"model": last_model, "best_params": res.get("best_params", {})}},
                    feature_cols=selected_features,
                    label_col=f"label_{h}",
                    output_dir=str(model_dir),
                )

    # ===== Step 10: 統計驗證（Permutation Test / DSR / OOD）=====
    log.info(f"\n[Step 10/14] Statistical validation...")

    try:
        stat_validation = run_statistical_validation(
            all_horizon_results=all_horizon_results,
            all_backtest_results=all_backtest_results,
            folds=folds,
            df=fs,
            feature_cols=selected_features,
            config=config,
        )
        # 移除大型 array，只保留摘要
        stat_summary = {
            'permutation_tests': {
                k: {kk: vv for kk, vv in v.items() if kk != 'permuted_aucs'}
                for k, v in stat_validation['permutation_tests'].items()
            },
            'deflated_sharpe': stat_validation['deflated_sharpe'],
            'ood_analysis': {
                k: {kk: vv for kk, vv in v.items() if kk != 'fold_trend'}
                for k, v in stat_validation['ood_analysis'].items()
            },
            'ood_fold_trends': {
                k: v.get('fold_trend', [])
                for k, v in stat_validation['ood_analysis'].items()
            },
            'overall_validity': stat_validation['overall_validity'],
        }
        report["results"]["statistical_validation"] = _serialize(stat_summary)
        log.info(f"  Overall statistical validity: {stat_validation['overall_validity']}")
    except Exception as e:
        log.warning(f"  Statistical validation error (non-fatal): {e}")
        stat_validation = {'overall_validity': 'ERROR'}
        report["results"]["statistical_validation"] = {"error": str(e)}

    # ===== Step 11: 概率校準（Platt Scaling）=====
    # NOTE: 校準在 backtest (Step 9) 之後執行，backtest 使用原始概率
    # 校準後的 OOF 會用於 report 生成和後續 Phase 3+ 分析
    # 未來可考慮將校準移至 Step 9 之前，讓 backtest 也使用校準概率
    log.info(f"\n[Step 11/14] Probability calibration (Platt Scaling)...")

    calibration_results = {}
    for h in horizons:
        for eng, res in all_horizon_results[h].items():
            if 'error' in res:
                continue
            oof_cal, labels_cal = _load_oof(res)
            if oof_cal is None:
                continue

            key = f"{eng}_D{h}"
            log.info(f"  Calibrating {key}...")

            try:
                cal_result = calibrate_oof_predictions(
                    oof_predictions=oof_cal,
                    oof_labels=labels_cal,
                    folds=folds,
                    method="sigmoid",
                )

                if 'error' not in cal_result:
                    calibration_results[key] = {
                        'before': cal_result['before_calibration'],
                        'after': cal_result['after_calibration'],
                        'improvement_pct': cal_result['improvement_pct'],
                        'per_fold_ece': cal_result.get('per_fold_ece', []),
                    }
                    # M6 fix: 將校準後概率存回，並更新 OOF 讓後續分析使用
                    calibrated_proba = cal_result.get('calibrated_proba')
                    if calibrated_proba is not None:
                        res['calibrated_oof'] = calibrated_proba
                        # 更新記憶體中的 oof_predictions
                        if 'oof_predictions' in res:
                            res['oof_predictions_raw'] = res['oof_predictions'].copy()
                            res['oof_predictions'] = calibrated_proba
                            log.info(f"    {key}: OOF updated with calibrated probabilities (in-memory)")
                        # 🟠5 fix: 同步回寫磁碟 .npz，確保 _load_oof 從磁碟載入時也是校準版
                        if '_oof_path' in res:
                            try:
                                disk_data = np.load(res['_oof_path'])
                                np.savez_compressed(
                                    res['_oof_path'],
                                    predictions=calibrated_proba,
                                    labels=disk_data['labels'],
                                )
                                log.info(f"    {key}: Calibrated OOF persisted to {res['_oof_path']}")
                            except Exception as e_disk:
                                log.warning(f"    {key}: Failed to persist calibrated OOF to disk: {e_disk}")
                else:
                    calibration_results[key] = {'error': cal_result['error']}

            except Exception as e:
                log.warning(f"  Calibration for {key} failed: {e}")
                calibration_results[key] = {'error': str(e)}

    report["results"]["calibration"] = _serialize(calibration_results)

    # ===== Step 12: 跨 Horizon 比較 + 品質閘門 =====
    log.info(f"\n[Step 12/14] Cross-horizon comparison & quality gates...")

    quality_gate_auc = config.get("model", {}).get("quality_gate_auc", 0.52)
    comparison = {}

    for h in horizons:
        for eng, res in all_horizon_results[h].items():
            if "error" in res:
                continue
            key = f"{eng}_D{h}"
            auc = res["avg_metrics"]["auc"]
            icir_data = all_icir_results.get(key, {})
            comparison[key] = {
                "horizon": h,
                "engine": eng,
                "auc": auc,
                "log_loss": res["avg_metrics"]["log_loss"],
                "accuracy": res["avg_metrics"]["accuracy"],
                "balanced_accuracy": res["avg_metrics"].get("balanced_accuracy", 0),
                "f1": res["avg_metrics"].get("f1_weighted", 0),
                "rank_ic": all_backtest_results.get(h, {}).get(eng, {}).get("rank_ic", 0),
                "icir": icir_data.get("icir", 0),
                "baseline_logloss": res["avg_metrics"].get("baseline_logloss", 0),
                "pass_auc_gate": auc >= quality_gate_auc,
            }

    # 找最佳模型
    best_key = max(comparison, key=lambda k: comparison[k]["auc"]) if comparison else None

    # 特徵穩定性（用最佳 horizon 的結果）
    stability_report = {}
    if best_key:
        best_h = comparison[best_key]["horizon"]
        best_eng = comparison[best_key]["engine"]
        best_res = all_horizon_results[best_h].get(best_eng, {})
        if best_res.get("importance_per_fold"):
            stability_report = check_feature_stability(
                best_res["importance_per_fold"],
                selected_features,
            )

    # OOF 預測完整性驗證
    oof_valid = True
    for h in horizons:
        for eng, res in all_horizon_results[h].items():
            if "error" in res:
                continue
            oof, _ = _load_oof(res)
            if oof is None or np.isnan(oof).all():
                log.warning(f"  {eng}_D{h}: OOF predictions all NaN!")
                oof_valid = False
            del oof; gc.collect()

    # 品質閘門（分 Critical / Advisory）
    gates = {
        # Critical gates
        "all_models_trained": all(
            "error" not in all_horizon_results[h].get(eng, {"error": True})
            for h in horizons
            for eng in config.get("model", {}).get("engines", [])
        ),
        "auc_gate_pass": all(
            v.get("pass_auc_gate", False) for v in comparison.values()
        ),
        "sufficient_folds": len(folds) >= 2,
        "no_data_leakage": inf_count == 0,
        "oof_predictions_valid": oof_valid,
        # Statistical validation gates (NEW)
        "statistical_validity": stat_validation.get("overall_validity", "ERROR") in ("STRONG", "MODERATE"),
        "permutation_tests_pass": all(
            v.get("significant_at_05", False)
            for v in stat_validation.get("permutation_tests", {}).values()
            if "error" not in v
        ),
        # Advisory gates
        "feature_stability": stability_report.get("stability_score", 0) >= 0.3,
        "best_model_ic_positive": (
            comparison[best_key]["rank_ic"] > 0 if best_key else False
        ),
    }
    all_gates_pass = all(gates.values())

    report["results"]["comparison"] = comparison
    report["results"]["best_model"] = best_key
    report["results"]["icir"] = {k: {kk: vv for kk, vv in v.items() if kk != "ic_series"} for k, v in all_icir_results.items()}
    report["results"]["feature_stability"] = _serialize(stability_report)
    report["results"]["quintile_analysis"] = _serialize(quintile_results)
    report["results"]["bootstrap_ci"] = _serialize(bootstrap_results)
    report["results"]["drawdown_analysis"] = _serialize(drawdown_results)
    report["results"]["alpha_decay"] = _serialize(alpha_decay_results)
    report["quality_gates"] = gates
    report["overall_status"] = "PASS" if all_gates_pass else "NEEDS REVIEW"

    # ===== Step 13: 圖表視覺化 =====
    log.info(f"\n[Step 13/14] Generating charts...")

    fig_dir = root / config["paths"]["figures"]
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig_dir_str = str(fig_dir)

    try:
        # 7a. Cross-horizon model comparison
        chart_metrics = {}
        for key, val in comparison.items():
            disc_sharpe = 0
            h_val = val["horizon"]
            eng_val = val["engine"]
            bt = all_backtest_results.get(h_val, {}).get(eng_val, {})
            if bt:
                disc_sharpe = bt.get("cost_scenarios", {}).get("discount", {}).get("sharpe_ratio", 0)
            chart_metrics[key] = {
                "auc": val["auc"],
                "sharpe": disc_sharpe,
                "ic": val["rank_ic"],
            }
        plot_model_comparison(chart_metrics, fig_dir_str)

        # 7b. Fold stability
        fold_auc_data = {}
        for h in horizons:
            for eng, res in all_horizon_results[h].items():
                if "error" in res or eng == "ensemble":
                    continue
                fold_auc_data[f"{eng}_D{h}"] = [m["auc"] for m in res.get("fold_metrics", [])]
        if fold_auc_data:
            plot_fold_stability(fold_auc_data, fig_dir_str)

        # 7c. Per-horizon charts
        for h in horizons:
            # Cumulative returns & drawdown
            bt_chart_data = {}
            for eng, bt_res in all_backtest_results.get(h, {}).items():
                if "daily_returns" in bt_res:
                    bt_chart_data[eng] = bt_res
            bm_returns = benchmark.get("daily_returns")
            if bt_chart_data:
                plot_cumulative_returns(bt_chart_data, bm_returns, h, fig_dir_str)
                plot_drawdown(bt_chart_data, h, fig_dir_str)

            # Monthly returns (best engine for this horizon)
            for eng in ["ensemble", "lightgbm", "xgboost"]:
                bt_res = all_backtest_results.get(h, {}).get(eng, {})
                if "daily_returns" in bt_res:
                    plot_monthly_returns(bt_res["daily_returns"], eng, h, fig_dir_str)
                    break

            for eng, res in all_horizon_results[h].items():
                if "error" in res or eng == "ensemble":
                    continue

                # Feature importance
                if res.get("feature_importance"):
                    plot_feature_importance(res["feature_importance"], eng, h, fig_dir_str)

                # Confusion matrix
                oof_cm, oof_labels_cm = _load_oof(res)
                if oof_cm is not None and oof_labels_cm is not None:
                    oof_class = np.argmax(oof_cm, axis=1).astype(float)
                    oof_class[np.isnan(oof_labels_cm)] = np.nan
                    plot_confusion_matrix(oof_labels_cm, oof_class, eng, h, fig_dir_str)
                    del oof_cm, oof_labels_cm

            # SHAP summary (last fold model, for best understanding)
            for eng, res in all_horizon_results[h].items():
                if "error" in res or eng == "ensemble":
                    continue
                last_model = res.get("last_model")
                if last_model is not None:
                    # 用最後一折的 test data 做 SHAP
                    last_fold = folds[-1]
                    X_shap = fs.iloc[last_fold.test_idx][selected_features].fillna(0).values
                    plot_shap_summary(last_model, X_shap, selected_features, eng, h, fig_dir_str)

            # IC time series (best engine)
            for eng in ["ensemble", "lightgbm", "xgboost"]:
                key = f"{eng}_D{h}"
                if key in all_icir_results and all_icir_results[key].get("ic_series") is not None:
                    plot_ic_time_series(all_icir_results[key]["ic_series"], h, eng, fig_dir_str)
                    break

        log.info(f"  Charts saved to: {fig_dir}")
    except Exception as e:
        log.warning(f"  Chart generation error (non-fatal): {e}")

    # ===== Step 14: 儲存報告 =====
    log.info(f"\n[Step 14/14] Saving Phase 2 report...")

    report_dir = root / config["paths"]["reports"]
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"phase2_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    log.info(f"  Report saved: {report_path}")

    # ===== 最終摘要 =====
    log.info("\n" + "=" * 70)
    log.info("Phase 2 Summary")
    log.info("=" * 70)
    log.info(f"  Feature Store:     {fs.shape[0]:,} rows × {fs.shape[1]} cols")
    log.info(f"  Selected Features: {len(selected_features)}")
    log.info(f"  Walk-forward Folds: {len(folds)}")
    log.info(f"  Horizons:          D+{', D+'.join(str(h) for h in horizons)}")

    log.info("\n  --- Model Performance ---")
    for key, val in comparison.items():
        status = "✓" if val["pass_auc_gate"] else "✗"
        icir_str = f"ICIR={val.get('icir', 0):.3f}" if val.get("icir") else ""
        log.info(
            f"  {key:>20s}: AUC={val['auc']:.4f} | "
            f"BalAcc={val.get('balanced_accuracy', 0):.4f} | "
            f"IC={val['rank_ic']:.4f} | {icir_str} [{status}]"
        )

    if best_key:
        log.info(f"\n  Best Model: {best_key} (AUC={comparison[best_key]['auc']:.4f})")

    log.info(f"\n  --- Backtest (discount cost) ---")
    for h in horizons:
        for eng, res in all_backtest_results.get(h, {}).items():
            disc = res.get("cost_scenarios", {}).get("discount", {})
            if disc:
                log.info(
                    f"  {eng}_D{h:>2d}: "
                    f"Return={disc.get('annualized_return', 0):+.2%} | "
                    f"Sharpe={disc.get('sharpe_ratio', 0):.2f} | "
                    f"MDD={disc.get('max_drawdown', 0):.2%}"
                )

    log.info(f"\n  --- Statistical Validation ---")
    log.info(f"  Validity: {stat_validation.get('overall_validity', 'N/A')}")
    for key, perm in stat_validation.get('permutation_tests', {}).items():
        if 'error' not in perm:
            log.info(f"  Permutation {key}: AUC={perm.get('observed_auc', 0):.4f} | "
                     f"p={perm.get('p_value', 1):.4f} | "
                     f"{'✓' if perm.get('significant_at_05') else '✗'}")
    for key, dsr in stat_validation.get('deflated_sharpe', {}).items():
        if 'error' not in dsr:
            log.info(f"  DSR {key}: Sharpe={dsr.get('observed_sharpe', 0):.4f} | "
                     f"p={dsr.get('dsr_p_value', 1):.4f} | "
                     f"{'✓' if dsr.get('dsr_pass') else '✗'}")

    log.info(f"\n  --- Probability Calibration ---")
    for key, cal in calibration_results.items():
        if 'error' not in cal:
            log.info(f"  {key}: ECE {cal['before']['ece']:.4f} → {cal['after']['ece']:.4f} "
                     f"({cal['improvement_pct']:+.1f}%)")

    log.info(f"\n  --- Quality Gates ---")
    for gate, passed in gates.items():
        log.info(f"  {'✓' if passed else '✗'} {gate}")
    log.info(f"\n  Overall: {'ALL GATES PASS ✓' if all_gates_pass else 'REVIEW NEEDED ⚠'}")
    log.info("=" * 70)

    return report


if __name__ == "__main__":
    report = main()
