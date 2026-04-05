"""
股價資料前處理與除權息驗證模組

處理流程：
  1. 缺值處理：forward-fill ≤ 5 日
  2. 除權息 5 步驗證
  3. 漲跌停偵測與標記
  4. 基本品質檢查

報告中對應章節：§3.1, §3.3, §11.1
"""
import pandas as pd
import numpy as np
from loguru import logger
from ..utils.helpers import timer


# ============================================================
# 1. 缺值處理
# ============================================================

@timer
def handle_missing_prices(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    處理股價缺值。

    策略：
      - 連續缺值 ≤ ffill_max_days 日 → forward fill
      - 超過 → 保留 NaN（後續分析時排除）
      - 記錄每支股票的缺值統計

    Args:
        df: stock_prices DataFrame，需包含 date 和 ticker 欄位
        config: 設定字典

    Returns:
        處理後的 DataFrame
    """
    max_days = config.get("preprocessing", {}).get("stock_prices", {}).get("ffill_max_days", 5)

    # 自動偵測欄位名
    date_col = _find_col(df, ["date", "日期", "trade_date"])
    ticker_col = _find_col(df, ["stock_id", "ticker", "symbol", "代號", "company_id"])

    if not date_col or not ticker_col:
        logger.warning("Cannot identify date/ticker columns. Skipping missing value handling.")
        return df

    # 型別轉換：Parquet 可能將數值存為 string
    price_candidates = ["closing_price", "close", "收盤價", "close_price", "adj_close",
                        "open", "high", "low", "volume"]
    for col in price_candidates:
        if col in df.columns and df[col].dtype == "object":
            df[col] = pd.to_numeric(df[col], errors="coerce")
            logger.debug(f"  Converted {col} from string to numeric")

    # 確保日期欄位是 datetime
    if df[date_col].dtype == "object":
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    original_nulls = df.isnull().sum().sum()

    # 確保排序
    df = df.sort_values([ticker_col, date_col]).reset_index(drop=True)

    # 數值欄位 forward fill（限制 max_days）
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    price_cols = [c for c in numeric_cols if c != ticker_col]

    if not price_cols:
        logger.warning("No numeric price columns found after type conversion. Skipping ffill.")
        return df

    df[price_cols] = df.groupby(ticker_col)[price_cols].transform(
        lambda x: x.ffill(limit=max_days)
    )

    filled_nulls = original_nulls - df.isnull().sum().sum()
    remaining_nulls = df.isnull().sum().sum()

    logger.info(f"Missing value handling: filled {filled_nulls:,} | remaining {remaining_nulls:,} | limit={max_days} days")

    return df


# ============================================================
# 1.5 暫停交易日過濾
# ============================================================

@timer
def filter_suspended_days(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    移除或修正暫停交易日（OHLC 全為零的行）。

    策略：
      - 完全暫停（OHLC 皆為 0）：移除該列
      - 異常情況（僅收盤價為 0，其他非零）：設收盤價為 NaN（e.g., IPO 首日）
      - 記錄詳細統計：移除列數、受影響公司數

    Args:
        df: stock_prices DataFrame
        config: 設定字典

    Returns:
        過濾後的 DataFrame
    """
    # 自動偵測欄位名
    ticker_col = _find_col(df, ["stock_id", "ticker", "symbol", "代號", "company_id"])
    open_col = _find_col(df, ["open", "opening_price", "open_price", "開盤價"])
    high_col = _find_col(df, ["high", "high_price", "最高價"])
    low_col = _find_col(df, ["low", "low_price", "最低價"])
    close_col = _find_col(df, ["closing_price", "close", "收盤價", "close_price", "adj_close"])

    if not all([open_col, high_col, low_col, close_col]):
        logger.warning("Cannot identify OHLC columns. Skipping suspended day filtering.")
        return df

    initial_len = len(df)
    initial_tickers = df[ticker_col].nunique() if ticker_col else 0

    # 型別安全：確保 OHLC 欄位為數值
    for col in [open_col, high_col, low_col, close_col]:
        if df[col].dtype == "object":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 條件 1：完全暫停（OHLC 皆為 0）→ 移除
    fully_suspended = (
        (df[open_col] == 0) &
        (df[high_col] == 0) &
        (df[low_col] == 0) &
        (df[close_col] == 0)
    )
    fully_suspended_count = fully_suspended.sum()

    # 統計受影響公司
    if ticker_col:
        affected_tickers_suspended = df.loc[fully_suspended, ticker_col].nunique()
    else:
        affected_tickers_suspended = 0

    # 移除完全暫停的列
    df = df[~fully_suspended].reset_index(drop=True)

    # 條件 2：異常（僅收盤價為 0，其他非零）→ 設 NaN（在過濾後的 df 上重新計算）
    abnormal_zero_close = (
        (df[close_col] == 0) &
        ((df[open_col] != 0) | (df[high_col] != 0) | (df[low_col] != 0))
    )
    abnormal_close_count = abnormal_zero_close.sum()

    if ticker_col:
        affected_tickers_abnormal = df.loc[abnormal_zero_close, ticker_col].nunique() if abnormal_close_count > 0 else 0
    else:
        affected_tickers_abnormal = 0

    # 修正異常情況：設收盤價為 NaN
    if abnormal_close_count > 0:
        df.loc[abnormal_zero_close, close_col] = np.nan

    final_len = len(df)
    final_tickers = df[ticker_col].nunique() if ticker_col else 0

    removed_count = initial_len - final_len
    logger.info(
        f"Suspended day filtering: "
        f"removed {removed_count:,} rows (fully suspended) | "
        f"nullified {abnormal_close_count:,} close prices (abnormal) | "
        f"affected tickers: {affected_tickers_suspended + affected_tickers_abnormal} | "
        f"total records: {final_len:,} (was {initial_len:,})"
    )

    return df


# ============================================================
# 2. 除權息 5 步驗證
# ============================================================

@timer
def verify_ex_dividend(df: pd.DataFrame, config: dict) -> dict:
    """
    除權息 5 步驗證。

    Step 1: 跳空缺口偵測 — 單日漲跌幅 > 9.5% 但非漲跌停
    Step 2: Yahoo 比對 — (需外部資料，此處產出待比對清單)
    Step 3: RSI 異常偵測 — RSI 單日變化 > 閾值
    Step 4: 連續性檢查 — 還原後價格應連續
    Step 5: 手動抽驗清單 — 產出隨機 50 支股票抽驗報告

    Args:
        df: stock_prices DataFrame
        config: 設定字典

    Returns:
        驗證結果字典
    """
    date_col = _find_col(df, ["date", "日期", "trade_date"])
    ticker_col = _find_col(df, ["stock_id", "ticker", "symbol", "代號", "company_id"])
    close_col = _find_col(df, ["closing_price", "close", "收盤價", "close_price", "adj_close"])

    if not all([date_col, ticker_col, close_col]):
        logger.error("Cannot identify required columns for ex-dividend verification")
        return {"status": "error", "message": "Missing required columns"}

    ex_div_config = config.get("preprocessing", {}).get("ex_dividend", {})
    gap_tolerance = ex_div_config.get("max_gap_tolerance_pct", 0.5)
    rsi_window = ex_div_config.get("rsi_anomaly_window", 14)
    rsi_threshold = ex_div_config.get("rsi_anomaly_threshold", 30)

    results = {"steps": {}, "suspicious_records": [], "summary": {}}

    # 型別安全：確保 close 是數值、date 是 datetime
    if df[close_col].dtype == "object":
        df[close_col] = pd.to_numeric(df[close_col], errors="coerce")
    if df[date_col].dtype == "object":
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # 確保排序
    df = df.sort_values([ticker_col, date_col]).reset_index(drop=True)

    # 計算日報酬率
    df["_daily_return"] = df.groupby(ticker_col)[close_col].pct_change()

    # --- Step 1: 跳空缺口偵測 ---
    logger.info("Step 1/5: 跳空缺口偵測...")
    price_alert_pct = config.get("preprocessing", {}).get("stock_prices", {}).get("price_change_alert_pct", 9.5) / 100

    big_gaps = df[df["_daily_return"].abs() > price_alert_pct].copy()
    # 真正的漲跌停（剛好 ±10%）排除
    limit_up_down = df[df["_daily_return"].abs().between(0.095, 0.105)]
    suspicious_gaps = big_gaps[~big_gaps.index.isin(limit_up_down.index)]

    results["steps"]["step1_gap_detection"] = {
        "total_big_gaps": len(big_gaps),
        "likely_limit_moves": len(limit_up_down),
        "suspicious_gaps": len(suspicious_gaps),
        "pass": len(suspicious_gaps) == 0,
    }
    logger.info(f"  Big gaps (>{price_alert_pct*100:.1f}%): {len(big_gaps)} | Suspicious (non-limit): {len(suspicious_gaps)}")

    if len(suspicious_gaps) > 0:
        results["suspicious_records"].extend(
            suspicious_gaps[[ticker_col, date_col, close_col, "_daily_return"]]
            .head(20).to_dict("records")
        )

    # --- Step 2: Yahoo 比對清單 ---
    logger.info("Step 2/5: 產出 Yahoo 比對清單...")
    # 抽取有可疑跳空的股票，產出待比對清單
    if len(suspicious_gaps) > 0:
        yahoo_check_list = suspicious_gaps[ticker_col].unique().tolist()[:20]
    else:
        # 隨機抽 10 支做抽樣比對
        all_tickers = df[ticker_col].unique()
        yahoo_check_list = list(np.random.choice(all_tickers, min(10, len(all_tickers)), replace=False))

    results["steps"]["step2_yahoo_checklist"] = {
        "tickers_to_verify": yahoo_check_list,
        "count": len(yahoo_check_list),
        "note": "需手動比對 Yahoo Finance 收盤價",
    }
    logger.info(f"  Yahoo check list: {len(yahoo_check_list)} tickers")

    # --- Step 3: RSI 異常偵測 ---
    logger.info("Step 3/5: RSI 異常偵測...")
    rsi_anomalies = _detect_rsi_anomalies(df, ticker_col, close_col, rsi_window, rsi_threshold)
    results["steps"]["step3_rsi_anomaly"] = {
        "anomaly_count": len(rsi_anomalies),
        "pass": len(rsi_anomalies) == 0,
    }
    logger.info(f"  RSI anomalies (delta > {rsi_threshold}): {len(rsi_anomalies)}")

    # --- Step 4: 連續性檢查 ---
    logger.info("Step 4/5: 價格連續性檢查...")
    continuity = _check_price_continuity(df, ticker_col, date_col, close_col)
    results["steps"]["step4_continuity"] = continuity
    logger.info(f"  Tickers with gaps > 5 trading days: {continuity['tickers_with_gaps']}")

    # --- Step 5: 手動抽驗清單 ---
    logger.info("Step 5/5: 產出抽驗清單...")
    all_tickers = df[ticker_col].unique()
    sample_size = min(50, len(all_tickers))
    sample_tickers = list(np.random.choice(all_tickers, sample_size, replace=False))
    results["steps"]["step5_manual_sample"] = {
        "sample_tickers": sample_tickers,
        "count": sample_size,
        "note": f"從 {len(all_tickers)} 支股票中隨機抽 {sample_size} 支，需人工抽驗除權息日還原",
    }

    # --- 總結 ---
    all_pass = all(
        step.get("pass", True)
        for step in results["steps"].values()
        if isinstance(step, dict) and "pass" in step
    )
    results["summary"] = {
        "overall_pass": all_pass,
        "total_tickers": len(all_tickers),
        "total_records": len(df),
        "suspicious_count": len(suspicious_gaps) + len(rsi_anomalies),
    }

    status = "PASS ✓" if all_pass else "NEEDS REVIEW ⚠"
    logger.info(f"Ex-dividend verification: {status}")

    # 清理暫存欄位
    df.drop(columns=["_daily_return"], inplace=True, errors="ignore")

    return results


# ============================================================
# 3. 漲跌停偵測
# ============================================================

@timer
def detect_limit_moves(df: pd.DataFrame) -> pd.DataFrame:
    """
    偵測並標記漲跌停日。

    台股漲跌停規則：±10%（以前一日收盤價計算）

    新增欄位：
      - _is_limit_up: 漲停
      - _is_limit_down: 跌停
      - _limit_type: "limit_up" / "limit_down" / "normal"

    注意：此函式的 pct_change() 計算依賴於上游 filter_suspended_days
          已移除或修正了 OHLC 全為零的暫停交易日。零價格會導致 pct_change()
          產生 -1.0 或 Inf，影響漲跌停判定的準確性。
    """
    date_col = _find_col(df, ["date", "日期", "trade_date"])
    ticker_col = _find_col(df, ["stock_id", "ticker", "symbol", "代號", "company_id"])
    close_col = _find_col(df, ["closing_price", "close", "收盤價", "close_price", "adj_close"])

    # 型別安全
    if df[close_col].dtype == "object":
        df[close_col] = pd.to_numeric(df[close_col], errors="coerce")

    df = df.sort_values([ticker_col, date_col]).reset_index(drop=True)
    daily_ret = df.groupby(ticker_col)[close_col].pct_change()

    # 漲跌停判定：±9.5% ~ ±10.5%（含四捨五入容差）
    df["_is_limit_up"] = daily_ret >= 0.095
    df["_is_limit_down"] = daily_ret <= -0.095
    df["_limit_type"] = "normal"
    df.loc[df["_is_limit_up"], "_limit_type"] = "limit_up"
    df.loc[df["_is_limit_down"], "_limit_type"] = "limit_down"

    n_up = df["_is_limit_up"].sum()
    n_down = df["_is_limit_down"].sum()
    logger.info(f"Limit moves detected: {n_up:,} limit-up | {n_down:,} limit-down | total {len(df):,}")

    return df


# ============================================================
# 4. 品質檢查總表
# ============================================================

@timer
def quality_check_prices(df: pd.DataFrame, config: dict) -> dict:
    """
    股價資料品質綜合檢查。

    Returns:
        品質報告字典
    """
    date_col = _find_col(df, ["date", "日期", "trade_date"])
    ticker_col = _find_col(df, ["stock_id", "ticker", "symbol", "代號", "company_id"])
    close_col = _find_col(df, ["closing_price", "close", "收盤價", "close_price", "adj_close"])
    volume_col = _find_col(df, ["volume", "成交量", "trade_volume"])

    min_days = config.get("preprocessing", {}).get("stock_prices", {}).get("min_trading_days", 60)

    report = {}

    # 基本統計
    report["total_records"] = len(df)
    report["total_tickers"] = df[ticker_col].nunique() if ticker_col else None

    if date_col:
        report["date_range"] = f"{df[date_col].min()} ~ {df[date_col].max()}"

    # 缺值率
    report["null_pct"] = {col: f"{df[col].isnull().mean()*100:.2f}%"
                          for col in df.columns if df[col].isnull().any()}

    # 交易日過少的股票
    if ticker_col and date_col:
        days_per_ticker = df.groupby(ticker_col)[date_col].count()
        low_data = days_per_ticker[days_per_ticker < min_days]
        report["tickers_below_min_days"] = len(low_data)
        report["min_trading_days_threshold"] = min_days
        if len(low_data) > 0:
            logger.warning(f"  {len(low_data)} tickers have < {min_days} trading days")

    # 零成交量（可能是停牌）
    if volume_col:
        zero_vol = (df[volume_col] == 0).sum()
        report["zero_volume_records"] = int(zero_vol)
        report["zero_volume_pct"] = f"{zero_vol / len(df) * 100:.2f}%"

    # 負價格（資料錯誤）
    if close_col:
        neg_price = (df[close_col] < 0).sum()
        report["negative_prices"] = int(neg_price)
        if neg_price > 0:
            logger.error(f"  Found {neg_price} records with negative prices!")

    # 完全重複列
    dup_rows = df.duplicated().sum()
    report["duplicate_rows"] = int(dup_rows)

    logger.info(f"Quality check completed: {len(report)} metrics")

    return report


# ============================================================
# 輔助函式
# ============================================================

def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    """從候選欄位名中找出存在於 DataFrame 的第一個"""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _detect_rsi_anomalies(df, ticker_col, close_col, window=14, threshold=10):
    """偵測 RSI 單日大幅跳動（可能是除權息未還原）"""
    anomalies = []

    for ticker, group in df.groupby(ticker_col):
        if len(group) < window + 5:
            continue

        close = group[close_col].values

        # 計算 RSI
        delta = pd.Series(close).diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window, min_periods=window).mean()
        avg_loss = loss.rolling(window, min_periods=window).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        # RSI 單日變化
        rsi_delta = rsi.diff().abs()
        anomaly_mask = rsi_delta > threshold

        if anomaly_mask.any():
            anomaly_indices = group.index[anomaly_mask.values]
            for idx in anomaly_indices:
                if idx in df.index:
                    anomalies.append(idx)

    return anomalies


def _check_price_continuity(df, ticker_col, date_col, close_col):
    """檢查每支股票的交易日是否有大段缺失"""
    results = {"tickers_with_gaps": 0, "max_gap_days": 0, "details": []}

    for ticker, group in df.groupby(ticker_col):
        if len(group) < 2:
            continue

        dates = pd.to_datetime(group[date_col]).sort_values()
        gaps = dates.diff().dt.days
        max_gap = gaps.max()

        if max_gap and max_gap > 15:  # 超過 15 個日曆天（含 CNY）
            results["tickers_with_gaps"] += 1
            results["max_gap_days"] = max(results["max_gap_days"], int(max_gap))
            if len(results["details"]) < 10:
                results["details"].append({
                    "ticker": ticker,
                    "max_gap_days": int(max_gap),
                    "n_records": len(group),
                })

    total_tickers = df[ticker_col].nunique() if ticker_col else 1
    results["pass"] = results["tickers_with_gaps"] / total_tickers < 0.05
    return results
