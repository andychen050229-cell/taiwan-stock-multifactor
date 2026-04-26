"""
資料漂移偵測模組 — Phase 3

使用 PSI（Population Stability Index）和 KS Test 偵測特徵分佈偏移。
"""

import numpy as np
import pandas as pd
from scipy import stats
from loguru import logger


def _compute_psi(reference: np.ndarray, current: np.ndarray, n_bins: int = 10) -> float:
    """
    計算 Population Stability Index (PSI)。

    PSI < 0.1:  無顯著偏移
    PSI 0.1~0.2: 輕微偏移
    PSI > 0.2:  顯著偏移
    """
    ref = reference[~np.isnan(reference)]
    cur = current[~np.isnan(current)]

    if len(ref) < 50 or len(cur) < 50:
        logger.debug(f"  PSI skipped: ref={len(ref)}, cur={len(cur)} (need ≥ 50)")
        return 0.0

    # 用 reference 的分位數作為 bin 邊界
    breakpoints = np.percentile(ref, np.linspace(0, 100, n_bins + 1))
    breakpoints = np.unique(breakpoints)

    if len(breakpoints) < 3:
        return 0.0

    ref_counts = np.histogram(ref, bins=breakpoints)[0]
    cur_counts = np.histogram(cur, bins=breakpoints)[0]

    # 轉為比例，避免除以零
    ref_pct = (ref_counts + 1) / (len(ref) + n_bins)
    cur_pct = (cur_counts + 1) / (len(cur) + n_bins)

    psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return float(psi)


def _compute_ks(reference: np.ndarray, current: np.ndarray) -> dict:
    """
    計算 Kolmogorov-Smirnov 檢定。

    Returns:
        dict with ks_stat, p_value, significant (p < 0.01)
    """
    ref = reference[~np.isnan(reference)]
    cur = current[~np.isnan(current)]

    if len(ref) < 30 or len(cur) < 30:
        return {"ks_stat": 0, "p_value": 1.0, "significant": False}

    stat, p_val = stats.ks_2samp(ref, cur)
    return {
        "ks_stat": float(stat),
        "p_value": float(p_val),
        "significant": p_val < 0.01,
    }


def _compute_label_drift(ref_labels: pd.Series, cur_labels: pd.Series) -> dict:
    """計算標籤分佈偏移。"""
    ref_dist = ref_labels.value_counts(normalize=True).sort_index()
    cur_dist = cur_labels.value_counts(normalize=True).sort_index()

    all_labels = sorted(set(ref_dist.index) | set(cur_dist.index))
    drift = {}
    max_shift = 0

    for label in all_labels:
        ref_pct = ref_dist.get(label, 0)
        cur_pct = cur_dist.get(label, 0)
        shift = abs(cur_pct - ref_pct)
        max_shift = max(max_shift, shift)
        drift[str(label)] = {
            "reference_pct": round(float(ref_pct), 4),
            "current_pct": round(float(cur_pct), 4),
            "shift": round(float(shift), 4),
        }

    return {
        "distribution": drift,
        "max_shift": round(float(max_shift), 4),
        "significant": max_shift > 0.10,
    }


def run_drift_detection(
    fs: pd.DataFrame,
    folds: list,
    selected_features: list,
    config: dict,
) -> dict:
    """
    執行完整的資料漂移偵測。

    使用最後一折的訓練集 vs 測試集作為 reference vs current。

    Returns:
        dict with per-feature PSI/KS, overall severity, label drift
    """
    logger.info("  Running drift detection...")

    # 取最後兩折：倒數第二折訓練集 = reference，最後一折測試集 = current
    if len(folds) >= 2:
        ref_idx = folds[-2].train_idx
        cur_idx = folds[-1].test_idx
    else:
        # 只有一折，用前 70% vs 後 30%
        n = len(fs)
        ref_idx = np.arange(int(n * 0.7))
        cur_idx = np.arange(int(n * 0.7), n)

    ref_data = fs.iloc[ref_idx]
    cur_data = fs.iloc[cur_idx]

    logger.info(f"  Reference: {len(ref_data):,} rows | Current: {len(cur_data):,} rows")

    # 特徵漂移分析
    feature_drift = {}
    n_psi_high = 0
    n_ks_sig = 0

    for feat in selected_features:
        if feat not in fs.columns:
            continue

        ref_vals = ref_data[feat].values.astype(float)
        cur_vals = cur_data[feat].values.astype(float)

        psi = _compute_psi(ref_vals, cur_vals)
        ks = _compute_ks(ref_vals, cur_vals)

        if psi > 0.2:
            n_psi_high += 1
        if ks["significant"]:
            n_ks_sig += 1

        # Per-feature actionable insight
        if psi > 0.2:
            psi_level = "high"
            action = "建議檢查此特徵的數據源是否異常，考慮重新計算或降權"
        elif psi > 0.1:
            psi_level = "medium"
            action = "持續監控，若持續偏移則需調整"
        else:
            psi_level = "low"
            action = "穩定，無需處理"

        # 統計量變化描述
        ref_mean = float(np.nanmean(ref_vals))
        cur_mean = float(np.nanmean(cur_vals))
        ref_std = float(np.nanstd(ref_vals))
        cur_std = float(np.nanstd(cur_vals))
        mean_shift = (cur_mean - ref_mean) / max(abs(ref_mean), 1e-8)

        feature_drift[feat] = {
            "psi": round(psi, 4),
            "ks_stat": round(ks["ks_stat"], 4),
            "ks_p_value": round(ks["p_value"], 6),
            "ks_significant": ks["significant"],
            "psi_level": psi_level,
            "ref_mean": round(ref_mean, 6),
            "cur_mean": round(cur_mean, 6),
            "ref_std": round(ref_std, 6),
            "cur_std": round(cur_std, 6),
            "mean_shift_pct": round(mean_shift * 100, 2),
            "action": action,
        }

    # 標籤漂移
    label_drifts = {}
    for h in [5, 20]:
        label_col = f"label_{h}"
        if label_col in fs.columns:
            ref_l = ref_data[label_col].dropna()
            cur_l = cur_data[label_col].dropna()
            label_drifts[label_col] = _compute_label_drift(ref_l, cur_l)

    # 整體嚴重度
    psi_ratio = n_psi_high / max(len(selected_features), 1)
    if psi_ratio > 0.3:
        severity = "high"
    elif psi_ratio > 0.1:
        severity = "medium"
    else:
        severity = "low"

    # Top drifted features
    sorted_drift = sorted(
        feature_drift.items(),
        key=lambda x: x[1]["psi"],
        reverse=True,
    )
    top_drifted = [
        {
            "feature": name,
            "psi": d["psi"],
            "ks_sig": d["ks_significant"],
            "mean_shift_pct": d.get("mean_shift_pct", 0),
            "action": d.get("action", ""),
        }
        for name, d in sorted_drift[:5]
    ]

    result = {
        "analysis_date": pd.Timestamp.now().isoformat(),
        "reference_period": {
            "n_rows": len(ref_data),
            "date_range": f"{ref_data['trade_date'].min()} ~ {ref_data['trade_date'].max()}"
            if "trade_date" in ref_data.columns else "unknown",
        },
        "current_period": {
            "n_rows": len(cur_data),
            "date_range": f"{cur_data['trade_date'].min()} ~ {cur_data['trade_date'].max()}"
            if "trade_date" in cur_data.columns else "unknown",
        },
        "feature_drift": feature_drift,
        "label_drift": label_drifts,
        "n_features_analyzed": len(feature_drift),
        "n_drifted_features": n_psi_high,
        "n_ks_significant": n_ks_sig,
        "overall_severity": severity,
        "top_drifted": top_drifted,
        "recommendation": (
            "建議盡快重新訓練模型" if severity == "high"
            else "持續監控，暫不需重新訓練" if severity == "medium"
            else "特徵分佈穩定，模型可繼續使用"
        ),
    }

    return result
