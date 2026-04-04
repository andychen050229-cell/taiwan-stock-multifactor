"""
前瞻偏差偵測模組（§3.5）

四重偵測機制：
  1. 未來欄位名稱掃描 — 搜尋含 "future_", "_forward" 等可疑欄位
  2. 時間戳驗證 — 確認特徵日期 ≤ 預測日期
  3. Train/Test 分佈比較 — PSI (Population Stability Index)
  4. 標籤相關性篩查 — 特徵與標籤相關 > 0.95 可能是洩漏
"""
import re
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger
from ..utils.helpers import timer


@timer
def scan_future_columns(df: pd.DataFrame, config: dict) -> dict:
    """
    Check 1: 掃描欄位名稱中是否包含暗示未來資訊的關鍵字。

    Args:
        df: 任意 DataFrame
        config: 設定字典

    Returns:
        掃描結果字典
    """
    patterns = config.get("preprocessing", {}).get("leakage_detection", {}).get(
        "future_keyword_patterns", ["future_", "_forward", "_next", "_tomorrow"]
    )

    suspicious = []
    for col in df.columns:
        col_lower = col.lower()
        for pattern in patterns:
            if pattern.lower() in col_lower:
                suspicious.append({"column": col, "matched_pattern": pattern})

    result = {
        "check": "future_column_scan",
        "pass": len(suspicious) == 0,
        "suspicious_columns": suspicious,
        "total_columns_scanned": len(df.columns),
    }

    if suspicious:
        logger.warning(f"Check 1 FAIL: {len(suspicious)} suspicious column names found:")
        for s in suspicious:
            logger.warning(f"  '{s['column']}' matches pattern '{s['matched_pattern']}'")
    else:
        logger.info(f"Check 1 PASS: No suspicious column names in {len(df.columns)} columns")

    return result


@timer
def verify_timestamps(
    features_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    feature_date_col: str,
    label_date_col: str,
) -> dict:
    """
    Check 2: 確認特徵的時間戳 ≤ 標籤的時間戳。

    每一筆特徵的日期必須在對應標籤日期之前或同一天，
    否則代表特徵「偷看了未來的資料」。
    """
    f_dates = pd.to_datetime(features_df[feature_date_col])
    l_dates = pd.to_datetime(labels_df[label_date_col])

    # 需要對齊 index
    if len(f_dates) != len(l_dates):
        logger.warning(f"Feature/label length mismatch: {len(f_dates)} vs {len(l_dates)}")
        min_len = min(len(f_dates), len(l_dates))
        f_dates = f_dates.iloc[:min_len]
        l_dates = l_dates.iloc[:min_len]

    violations = (f_dates.values > l_dates.values).sum()

    result = {
        "check": "timestamp_verification",
        "pass": violations == 0,
        "violations": int(violations),
        "total_checked": len(f_dates),
    }

    if violations > 0:
        logger.error(f"Check 2 FAIL: {violations} records have feature_date > label_date")
    else:
        logger.info(f"Check 2 PASS: All {len(f_dates):,} feature timestamps ≤ label timestamps")

    return result


@timer
def compute_psi(
    train_series: pd.Series,
    test_series: pd.Series,
    bins: int = 10,
) -> float:
    """
    計算 Population Stability Index (PSI)。

    PSI < 0.10 → 穩定
    PSI 0.10-0.25 → 需關注
    PSI > 0.25 → 顯著飄移
    """
    # 用訓練集的分位數做分箱
    breakpoints = np.percentile(train_series.dropna(), np.linspace(0, 100, bins + 1))
    breakpoints = np.unique(breakpoints)

    if len(breakpoints) < 3:
        return 0.0  # 分箱不足

    train_counts = np.histogram(train_series.dropna(), bins=breakpoints)[0]
    test_counts = np.histogram(test_series.dropna(), bins=breakpoints)[0]

    # 轉為比例（加小量避免 log(0)）
    eps = 1e-8
    train_pct = train_counts / train_counts.sum() + eps
    test_pct = test_counts / test_counts.sum() + eps

    psi = np.sum((test_pct - train_pct) * np.log(test_pct / train_pct))

    return float(psi)


@timer
def check_distribution_shift(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    config: dict,
    numeric_only: bool = True,
) -> dict:
    """
    Check 3: 比較 Train/Test 特徵分佈（PSI）。

    PSI > max_train_test_psi 表示分佈飄移嚴重，可能有洩漏或非穩態問題。
    """
    max_psi = config.get("preprocessing", {}).get("leakage_detection", {}).get("max_train_test_psi", 0.25)

    if numeric_only:
        cols = train_df.select_dtypes(include=[np.number]).columns
    else:
        cols = train_df.columns

    # 只檢查兩者共有的欄位
    common_cols = [c for c in cols if c in test_df.columns]

    psi_results = {}
    flagged = []

    for col in common_cols:
        psi = compute_psi(train_df[col], test_df[col])
        psi_results[col] = round(psi, 4)
        if psi > max_psi:
            flagged.append({"column": col, "psi": round(psi, 4)})

    result = {
        "check": "distribution_shift",
        "pass": len(flagged) == 0,
        "flagged_columns": flagged,
        "total_checked": len(common_cols),
        "max_psi_threshold": max_psi,
        "psi_values": psi_results,
    }

    if flagged:
        logger.warning(f"Check 3 WARNING: {len(flagged)} columns exceed PSI threshold {max_psi}:")
        for f in flagged[:5]:
            logger.warning(f"  {f['column']}: PSI={f['psi']}")
    else:
        logger.info(f"Check 3 PASS: All {len(common_cols)} columns within PSI threshold")

    return result


@timer
def check_label_correlation(
    df: pd.DataFrame,
    label_col: str,
    threshold: float = 0.95,
) -> dict:
    """
    Check 4: 篩查與標籤相關係數 > threshold 的特徵。

    若某特徵與標籤幾乎完美相關，可能是「標籤本身的變形」（洩漏）。
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if label_col in numeric_cols:
        numeric_cols.remove(label_col)

    correlations = {}
    suspicious = []

    for col in numeric_cols:
        try:
            corr = abs(df[col].corr(df[label_col]))
            correlations[col] = round(corr, 4)
            if corr > threshold:
                suspicious.append({"column": col, "correlation": round(corr, 4)})
        except Exception:
            pass

    result = {
        "check": "label_correlation",
        "pass": len(suspicious) == 0,
        "suspicious_features": suspicious,
        "threshold": threshold,
        "total_checked": len(numeric_cols),
    }

    if suspicious:
        logger.error(f"Check 4 FAIL: {len(suspicious)} features have |corr| > {threshold} with label:")
        for s in suspicious:
            logger.error(f"  {s['column']}: corr={s['correlation']}")
    else:
        logger.info(f"Check 4 PASS: No features with |corr| > {threshold} in {len(numeric_cols)} features")

    return result


@timer
def run_leakage_detection(
    df: pd.DataFrame,
    config: dict,
    label_col: Optional[str] = None,
    train_df: Optional[pd.DataFrame] = None,
    test_df: Optional[pd.DataFrame] = None,
) -> dict:
    """
    執行完整四重洩漏偵測。

    Args:
        df: 完整 DataFrame（用於 Check 1, 4）
        config: 設定字典
        label_col: 標籤欄位名（用於 Check 4）
        train_df: 訓練集（用於 Check 3）
        test_df: 測試集（用於 Check 3）

    Returns:
        完整偵測結果字典
    """
    logger.info("=" * 50)
    logger.info("Running 4-layer leakage detection...")
    logger.info("=" * 50)

    results = {}

    # Check 1: 未來欄位名稱掃描
    results["check1"] = scan_future_columns(df, config)

    # Check 2: 時間戳驗證（需要 feature + label 的日期，此階段暫跳過）
    results["check2"] = {"check": "timestamp_verification", "status": "deferred",
                         "note": "Will run after feature engineering with label alignment"}
    logger.info("Check 2 DEFERRED: Requires feature-label date alignment (Phase 2)")

    # Check 3: 分佈比較
    if train_df is not None and test_df is not None:
        results["check3"] = check_distribution_shift(train_df, test_df, config)
    else:
        results["check3"] = {"check": "distribution_shift", "status": "deferred",
                             "note": "Will run after train/test split"}
        logger.info("Check 3 DEFERRED: Requires train/test split (Phase 2)")

    # Check 4: 標籤相關性
    if label_col and label_col in df.columns:
        results["check4"] = check_label_correlation(df, label_col)
    else:
        results["check4"] = {"check": "label_correlation", "status": "deferred",
                             "note": "Will run after label engineering (Phase 2)"}
        logger.info("Check 4 DEFERRED: Requires label column (Phase 2)")

    # 總結
    active_checks = [r for r in results.values() if isinstance(r, dict) and "pass" in r]
    all_pass = all(r["pass"] for r in active_checks)
    n_warnings = sum(1 for r in results.values() if isinstance(r, dict) and r.get("status") == "deferred")

    results["summary"] = {
        "overall_pass": all_pass,
        "checks_run": len(active_checks),
        "checks_deferred": n_warnings,
        "total_checks": 4,
    }

    status = "ALL PASS ✓" if all_pass else "ISSUES FOUND ⚠"
    logger.info(f"Leakage detection: {status} ({len(active_checks)} run, {n_warnings} deferred)")

    return results
