"""
標籤生成模組 — D+1, D+5, D+20 報酬率分類

功能：
  1. 計算前瞻報酬率（forward return）
  2. 三元分類：上漲(1) / 持平(0) / 下跌(-1)
  3. 支援固定閾值與動態閾值（基於歷史波動率）
  4. 標籤分布統計與品質驗證

報告中對應章節：§4.1, §11.2
"""
import pandas as pd
import numpy as np
from loguru import logger
from ..utils.helpers import timer


# ============================================================
# 1. 前瞻報酬率計算
# ============================================================

@timer
def compute_forward_returns(df: pd.DataFrame, horizons: list = None,
                            config: dict = None) -> pd.DataFrame:
    """
    計算多時間軸前瞻報酬率。
    fwd_ret_N = (close[t+N] - close[t]) / close[t]
    """
    df = df.copy()

    if horizons is None:
        if config:
            horizons = config.get("model", {}).get("horizons", [1, 5, 20])
        else:
            horizons = [1, 5, 20]

    ticker_col = _find_col(df, ["company_id", "stock_id", "ticker", "symbol"])
    date_col = _find_col(df, ["trade_date", "date"])
    close_col = _find_col(df, ["closing_price", "close"])

    if not all([ticker_col, date_col, close_col]):
        logger.error("Cannot identify required columns for forward return calculation")
        return df

    if df[close_col].dtype == "object":
        df[close_col] = pd.to_numeric(df[close_col], errors="coerce")
    if df[date_col].dtype == "object":
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    df = df.sort_values([ticker_col, date_col]).reset_index(drop=True)

    for h in horizons:
        col_name = f"fwd_ret_{h}"
        future_close = df.groupby(ticker_col)[close_col].shift(-h)
        # 安全除法：close=0 或 NaN 時結果為 NaN，避免 Inf
        safe_close = df[close_col].replace(0, np.nan)
        df[col_name] = (future_close - df[close_col]) / safe_close

        non_null = df[col_name].notna().sum()
        logger.info(
            f"  fwd_ret_{h}: {non_null:,} valid "
            f"({non_null/len(df)*100:.1f}%) | "
            f"mean={df[col_name].mean():.6f} | "
            f"std={df[col_name].std():.6f}"
        )

    return df


# ============================================================
# 2. 固定閾值分類
# ============================================================

@timer
def classify_fixed_threshold(df: pd.DataFrame, config: dict = None) -> pd.DataFrame:
    """
    使用固定閾值將報酬率分為三類。
      fwd_ret > +threshold  → label = 1  (上漲)
      fwd_ret < -threshold  → label = -1 (下跌)
      else                  → label = 0  (持平)
    """
    df = df.copy()

    default_thresholds = {1: 0.005, 5: 0.015, 20: 0.040}
    if config:
        thresholds = config.get("labeling", {}).get("thresholds", default_thresholds)
    else:
        thresholds = default_thresholds

    for horizon, threshold in thresholds.items():
        horizon = int(horizon)
        threshold = float(threshold)
        ret_col = f"fwd_ret_{horizon}"
        label_col = f"label_{horizon}"

        if ret_col not in df.columns:
            logger.warning(f"  {ret_col} not found, skipping D+{horizon}")
            continue

        df[label_col] = 0
        df.loc[df[ret_col] > threshold, label_col] = 1
        df.loc[df[ret_col] < -threshold, label_col] = -1
        df.loc[df[ret_col].isna(), label_col] = np.nan

        logger.info(
            f"  label_{horizon} (threshold=+/-{threshold*100:.1f}%): "
            f"UP={int((df[label_col]==1).sum())} | "
            f"FLAT={int((df[label_col]==0).sum())} | "
            f"DOWN={int((df[label_col]==-1).sum())} | "
            f"NaN={int(df[label_col].isna().sum())}"
        )

    return df


# ============================================================
# 3. 動態閾值分類（基於歷史波動率）
# ============================================================

@timer
def classify_dynamic_threshold(df: pd.DataFrame, config: dict = None) -> pd.DataFrame:
    """
    使用動態閾值（歷史波動率 x 係數）分類。
    閾值 = sqrt(h) x rolling_std(daily_ret, window) x 0.5
    """
    df = df.copy()

    ticker_col = _find_col(df, ["company_id", "stock_id", "ticker", "symbol"])
    close_col = _find_col(df, ["closing_price", "close"])

    if not ticker_col or not close_col:
        logger.warning("Cannot compute dynamic threshold without ticker/close columns")
        return df

    vol_window = 60
    if config:
        vol_window = config.get("labeling", {}).get("vol_window", 60)

    horizons = [1, 5, 20]
    if config:
        horizons = config.get("model", {}).get("horizons", horizons)

    if df[close_col].dtype == "object":
        df[close_col] = pd.to_numeric(df[close_col], errors="coerce")

    df["_daily_ret"] = df.groupby(ticker_col)[close_col].pct_change()
    df["_vol"] = df.groupby(ticker_col)["_daily_ret"].transform(
        lambda x: x.rolling(vol_window, min_periods=max(20, vol_window // 3)).std()
    )

    for h in horizons:
        ret_col = f"fwd_ret_{h}"
        label_col = f"label_dyn_{h}"

        if ret_col not in df.columns:
            continue

        dynamic_threshold = np.sqrt(h) * df["_vol"] * 0.5

        df[label_col] = 0
        df.loc[df[ret_col] > dynamic_threshold, label_col] = 1
        df.loc[df[ret_col] < -dynamic_threshold, label_col] = -1
        df.loc[df[ret_col].isna() | dynamic_threshold.isna(), label_col] = np.nan

        logger.info(
            f"  label_dyn_{h}: "
            f"UP={int((df[label_col]==1).sum())} | "
            f"FLAT={int((df[label_col]==0).sum())} | "
            f"DOWN={int((df[label_col]==-1).sum())} | "
            f"threshold_median={dynamic_threshold.median():.6f}"
        )

    df.drop(columns=["_daily_ret", "_vol"], inplace=True, errors="ignore")
    return df


# ============================================================
# 4. 標籤品質驗證
# ============================================================

@timer
def validate_labels(df: pd.DataFrame, config: dict = None) -> dict:
    """
    標籤品質綜合驗證。
    檢查：類別平衡度、NaN 覆蓋率、分布統計
    """
    report = {"checks": {}, "distributions": {}, "warnings": []}

    label_cols = [c for c in df.columns if c.startswith("label_") and not c.startswith("label_dyn_")]
    label_dyn_cols = [c for c in df.columns if c.startswith("label_dyn_")]
    all_label_cols = label_cols + label_dyn_cols

    for col in all_label_cols:
        valid = df[col].notna()
        total_valid = valid.sum()

        if total_valid == 0:
            report["warnings"].append(f"{col}: all NaN!")
            continue

        dist = df.loc[valid, col].value_counts(normalize=True).sort_index()
        report["distributions"][col] = {str(k): round(v, 4) for k, v in dist.to_dict().items()}

        min_pct = dist.min()
        is_balanced = min_pct >= 0.15
        report["checks"][f"{col}_balance"] = {
            "min_class_pct": f"{min_pct*100:.1f}%",
            "balanced": is_balanced,
        }

        if not is_balanced:
            report["warnings"].append(
                f"{col}: imbalanced! min class = {min_pct*100:.1f}% (threshold: 15%)"
            )

        coverage = total_valid / len(df)
        report["checks"][f"{col}_coverage"] = f"{coverage*100:.1f}%"

        logger.info(
            f"  {col}: coverage={coverage*100:.1f}% | "
            f"dist={dist.to_dict()} | "
            f"balanced={'PASS' if is_balanced else 'FAIL'}"
        )

    n_warnings = len(report["warnings"])
    if n_warnings > 0:
        for w in report["warnings"]:
            logger.warning(f"  {w}")
    else:
        logger.info("  All label checks passed")

    report["overall_pass"] = len(report["warnings"]) == 0
    return report


# ============================================================
# 主流程
# ============================================================

@timer
def run_label_pipeline(df: pd.DataFrame, config: dict) -> tuple:
    """
    標籤生成完整流程。
    Returns: (新增標籤的 DataFrame, 驗證報告 dict)
    """
    logger.info("=" * 60)
    logger.info("Label Generation Pipeline")
    logger.info("=" * 60)

    logger.info("\n[Step 1/4] Computing forward returns...")
    df = compute_forward_returns(df, config=config)

    logger.info("\n[Step 2/4] Fixed threshold classification...")
    df = classify_fixed_threshold(df, config=config)

    use_dynamic = config.get("labeling", {}).get("use_dynamic_threshold", False)
    if use_dynamic:
        logger.info("\n[Step 3/4] Dynamic threshold classification...")
        df = classify_dynamic_threshold(df, config=config)
    else:
        logger.info("\n[Step 3/4] Dynamic threshold: SKIPPED (disabled in config)")

    logger.info("\n[Step 4/4] Label validation...")
    report = validate_labels(df, config=config)

    logger.info(f"\nLabel pipeline complete: {df.shape[0]:,} rows x {df.shape[1]} cols")
    return df, report


# ============================================================
# 輔助函式
# ============================================================

def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None
