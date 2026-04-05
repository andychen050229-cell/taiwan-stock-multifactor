"""
五大支柱特徵工程模組 — Phase 1 骨架版

五大支柱：
  ① 趨勢與價格 (trend_)  — MA, EMA, MACD, 動量, 波動率
  ② 基本面 (fund_)       — 毛利率, 營業利益率, 營收YoY, EPS
  ③ 估值 (val_)          — P/E ratio
  ④ 事件與敘事 (event_)  — 新聞量, 情緒代理, 標題關鍵字
  ⑤ 風險與機制 (risk_)   — 波動率Regime, 回撤, 大盤指標

報告中對應章節：§5
"""
import pandas as pd
import numpy as np
from loguru import logger
from ..utils.helpers import timer


# ============================================================
# ① 趨勢與價格特徵
# ============================================================

@timer
def build_trend_features(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    趨勢與價格特徵（close-based，OHLCV 擴充另行處理）。

    生成的特徵：
      - trend_ma_5/10/20/60: 移動平均
      - trend_ema_12/26: 指數移動平均
      - trend_macd / trend_macd_signal / trend_macd_hist: MACD
      - trend_momentum_5/10/20: 動量（N日報酬率）
      - trend_volatility_20/60: 滾動波動率
      - trend_ma_cross_5_20: 均線交叉信號
      - trend_price_vs_ma20: 價格相對 MA20 的偏離度
    """
    df = df.copy()

    ticker_col = _find_col(df, ["company_id", "stock_id"])
    close_col = _find_col(df, ["closing_price", "close"])
    date_col = _find_col(df, ["trade_date", "date"])

    if not all([ticker_col, close_col]):
        logger.warning("Missing ticker/close columns. Skipping trend features.")
        return df

    if df[close_col].dtype == "object":
        df[close_col] = pd.to_numeric(df[close_col], errors="coerce")

    df = df.sort_values([ticker_col, date_col]).reset_index(drop=True)

    # MA
    for window in [5, 10, 20, 60]:
        df[f"trend_ma_{window}"] = df.groupby(ticker_col)[close_col].transform(
            lambda x: x.rolling(window, min_periods=max(3, window // 2)).mean()
        )

    # EMA
    for span in [12, 26]:
        df[f"trend_ema_{span}"] = df.groupby(ticker_col)[close_col].transform(
            lambda x: x.ewm(span=span, adjust=False).mean()
        )

    # MACD
    df["trend_macd"] = df["trend_ema_12"] - df["trend_ema_26"]
    df["trend_macd_signal"] = df.groupby(ticker_col)["trend_macd"].transform(
        lambda x: x.ewm(span=9, adjust=False).mean()
    )
    df["trend_macd_hist"] = df["trend_macd"] - df["trend_macd_signal"]

    # Momentum（N日報酬率）
    for n in [5, 10, 20]:
        df[f"trend_momentum_{n}"] = df.groupby(ticker_col)[close_col].transform(
            lambda x: x.pct_change(n, fill_method=None)
        )

    # 滾動波動率
    daily_ret = df.groupby(ticker_col)[close_col].pct_change(fill_method=None)
    for window in [20, 60]:
        df[f"trend_volatility_{window}"] = daily_ret.groupby(df[ticker_col]).transform(
            lambda x: x.rolling(window, min_periods=max(10, window // 3)).std()
        )

    # 均線交叉
    df["trend_ma_cross_5_20"] = (df["trend_ma_5"] > df["trend_ma_20"]).astype(float)
    df.loc[df["trend_ma_5"].isna() | df["trend_ma_20"].isna(), "trend_ma_cross_5_20"] = np.nan

    # 價格偏離度
    df["trend_price_vs_ma20"] = (
        (df[close_col] - df["trend_ma_20"]) / df["trend_ma_20"]
    ).replace([np.inf, -np.inf], np.nan)

    # OHLCV 擴充（如果有）
    if "high_price" in df.columns and "low_price" in df.columns:
        df = _build_ohlcv_features(df, ticker_col, close_col)

    trend_cols = [c for c in df.columns if c.startswith("trend_")]
    logger.info(f"  Trend features generated: {len(trend_cols)} features")

    return df


def _build_ohlcv_features(df, ticker_col, close_col):
    """OHLCV 擴充特徵（需要 open/high/low/volume）"""
    high_col = _find_col(df, ["high_price", "high"])
    low_col = _find_col(df, ["low_price", "low"])
    open_col = _find_col(df, ["open_price", "open"])
    vol_col = _find_col(df, ["volume"])

    # True Range & ATR
    if high_col and low_col:
        prev_close = df.groupby(ticker_col)[close_col].shift(1)
        tr = pd.concat([
            df[high_col] - df[low_col],
            (df[high_col] - prev_close).abs(),
            (df[low_col] - prev_close).abs(),
        ], axis=1).max(axis=1)

        for window in [14, 20]:
            df[f"trend_atr_{window}"] = tr.groupby(df[ticker_col]).transform(
                lambda x: x.rolling(window, min_periods=10).mean()
            )

    # RSI
    if close_col:
        delta = df.groupby(ticker_col)[close_col].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        for window in [14]:
            avg_gain = gain.groupby(df[ticker_col]).transform(
                lambda x: x.rolling(window, min_periods=window).mean()
            )
            avg_loss = loss.groupby(df[ticker_col]).transform(
                lambda x: x.rolling(window, min_periods=window).mean()
            )
            rs = avg_gain / avg_loss.replace(0, np.nan)
            df[f"trend_rsi_{window}"] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    for window in [20]:
        ma = df.groupby(ticker_col)[close_col].transform(
            lambda x: x.rolling(window).mean()
        )
        std = df.groupby(ticker_col)[close_col].transform(
            lambda x: x.rolling(window).std()
        )
        df[f"trend_bb_upper_{window}"] = ma + 2 * std
        df[f"trend_bb_lower_{window}"] = ma - 2 * std
        df[f"trend_bb_width_{window}"] = (
            (df[f"trend_bb_upper_{window}"] - df[f"trend_bb_lower_{window}"]) / ma
        ).replace([np.inf, -np.inf], np.nan)

    # Volume features
    if vol_col:
        for window in [5, 20]:
            df[f"trend_vol_ma_{window}"] = df.groupby(ticker_col)[vol_col].transform(
                lambda x: x.rolling(window, min_periods=3).mean()
            )
        # Volume ratio
        if "trend_vol_ma_5" in df.columns and "trend_vol_ma_20" in df.columns:
            df["trend_vol_ratio"] = (
                df["trend_vol_ma_5"] / df["trend_vol_ma_20"]
            ).replace([np.inf, -np.inf], np.nan)

    logger.info("  OHLCV extended features added (ATR, RSI, BB, Volume)")
    return df


# ============================================================
# ② 基本面特徵
# ============================================================

@timer
def build_fundamental_features(prices_df: pd.DataFrame,
                               financial_df: pd.DataFrame,
                               config: dict) -> pd.DataFrame:
    """
    基本面特徵 — 將 income_stmt 的單季指標 PIT-safe 併入價格表。

    策略：
      1. 只使用 pit_date <= trade_date 的財報（避免 look-ahead）
      2. 每個 trade_date 取最近一期可用財報
      3. 生成 fund_ 前綴特徵
    """
    if financial_df is None or len(financial_df) == 0:
        logger.warning("No financial data. Skipping fundamental features.")
        return prices_df

    ticker_col = _find_col(prices_df, ["company_id", "stock_id"])
    date_col = _find_col(prices_df, ["trade_date", "date"])

    if not ticker_col or not date_col:
        return prices_df

    # 確認 financial_df 有 pit_date
    if "pit_date" not in financial_df.columns:
        logger.warning("financial_df missing pit_date. Skipping fundamental features.")
        return prices_df

    # 選擇要合併的欄位
    fund_cols = [c for c in financial_df.columns
                 if c.endswith("_sq") or c.endswith("_yoy") or c.startswith("gross_") or
                 c.startswith("operating_margin") or c.startswith("net_margin")]

    if not fund_cols:
        logger.warning("No fundamental feature columns found.")
        return prices_df

    # 準備合併用 DF
    fin_merge = financial_df[["company_id", "pit_date"] + fund_cols].copy()
    fin_merge = fin_merge.dropna(subset=["pit_date"])
    fin_merge = fin_merge.sort_values(["company_id", "pit_date"])

    # PIT-safe merge: asof merge — 每個 trade_date 取 pit_date <= trade_date 的最近一筆
    prices_df = prices_df.sort_values([ticker_col, date_col]).reset_index(drop=True)

    # 確保日期型別一致
    fin_merge[date_col] = pd.to_datetime(fin_merge["pit_date"])
    fin_merge = fin_merge.drop(columns=["pit_date"])
    prices_df[date_col] = pd.to_datetime(prices_df[date_col])

    # merge_asof 要求兩邊都按 key 排序
    left = prices_df.sort_values([date_col]).reset_index(drop=True)
    right = fin_merge.sort_values([date_col]).reset_index(drop=True)

    result = pd.merge_asof(
        left,
        right,
        on=date_col,
        by="company_id",
        direction="backward",
        suffixes=("", "_fin"),
    )

    # 重新命名為 fund_ 前綴
    rename_map = {}
    for col in fund_cols:
        new_name = f"fund_{col}" if not col.startswith("fund_") else col
        if col in result.columns:
            rename_map[col] = new_name
    result = result.rename(columns=rename_map)

    # 還原排序
    result = result.sort_values([ticker_col, date_col]).reset_index(drop=True)

    fund_features = [c for c in result.columns if c.startswith("fund_")]
    logger.info(f"  Fundamental features merged: {len(fund_features)} features (PIT-safe)")

    return result


# ============================================================
# ③ 估值特徵
# ============================================================

@timer
def build_valuation_features(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    估值特徵 — P/E ratio 等。
    val_pe = closing_price / eps_sq (需 PIT-safe 的 eps)
    """
    close_col = _find_col(df, ["closing_price", "close"])
    eps_col = _find_col(df, ["fund_eps_sq", "eps_sq"])

    if not close_col or not eps_col:
        logger.warning("Missing close/eps columns. Skipping valuation features.")
        return df

    # P/E ratio
    df["val_pe"] = (df[close_col] / df[eps_col]).replace([np.inf, -np.inf], np.nan)

    # P/E 分位數（relative valuation）
    ticker_col = _find_col(df, ["company_id", "stock_id"])
    if ticker_col:
        df["val_pe_rank"] = df.groupby(ticker_col)["val_pe"].transform(
            lambda x: x.rank(pct=True)
        )

    val_cols = [c for c in df.columns if c.startswith("val_")]
    logger.info(f"  Valuation features: {len(val_cols)} features")

    return df


# ============================================================
# ④ 事件與敘事特徵
# ============================================================

@timer
def build_event_features(prices_df: pd.DataFrame, text_df: pd.DataFrame,
                         config: dict) -> pd.DataFrame:
    """
    事件與敘事特徵（Phase 1 簡化版）。

    Phase 1 features:
      - event_news_count_1d/5d: 新聞/社群數量
      - event_title_length_avg: 標題平均長度（情緒代理）

    Phase 2 will add: TF-IDF, 情緒分析, BERT embeddings
    """
    if text_df is None or len(text_df) == 0:
        logger.warning("No text data. Skipping event features.")
        return prices_df

    ticker_col = _find_col(prices_df, ["company_id", "stock_id"])
    date_col = _find_col(prices_df, ["trade_date", "date"])

    # 找出 text 的日期和相關欄位
    text_date_col = _find_col(text_df, ["post_time", "date", "publish_date"])
    text_title_col = _find_col(text_df, ["title", "標題"])

    if not text_date_col:
        logger.warning("No date column in text data. Skipping event features.")
        return prices_df

    # 確保日期型別
    text_df = text_df.copy()
    if text_df[text_date_col].dtype == "object":
        text_df[text_date_col] = pd.to_datetime(text_df[text_date_col], errors="coerce")

    # 建立每日新聞數量（全市場）
    text_df["_date"] = text_df[text_date_col].dt.date
    daily_news = text_df.groupby("_date").size().reset_index(name="event_news_count_raw")
    daily_news["_date"] = pd.to_datetime(daily_news["_date"])

    # 合併到 prices
    prices_df = prices_df.copy()
    prices_df["_date_key"] = pd.to_datetime(prices_df[date_col]).dt.normalize()
    prices_df = prices_df.merge(
        daily_news.rename(columns={"_date": "_date_key"}),
        on="_date_key", how="left",
    )
    prices_df["event_news_count_raw"] = prices_df["event_news_count_raw"].fillna(0)

    # 滾動新聞量
    if ticker_col:
        for window in [1, 5]:
            prices_df[f"event_news_count_{window}d"] = prices_df.groupby(ticker_col)[
                "event_news_count_raw"
            ].transform(lambda x: x.rolling(window, min_periods=1).sum())

    prices_df.drop(columns=["_date_key", "event_news_count_raw"], inplace=True, errors="ignore")

    event_cols = [c for c in prices_df.columns if c.startswith("event_")]
    logger.info(f"  Event features: {len(event_cols)} features (Phase 1 simplified)")

    return prices_df


# ============================================================
# ⑤ 風險與機制特徵
# ============================================================

@timer
def build_risk_features(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    風險與機制特徵。

    Features:
      - risk_drawdown: 從近期高點的回撤
      - risk_volatility_regime: 波動率分位（高/中/低）
      - risk_market_ret_20d: 大盤 20 日報酬（cross-sectional 市場指標）
    """
    ticker_col = _find_col(df, ["company_id", "stock_id"])
    close_col = _find_col(df, ["closing_price", "close"])
    date_col = _find_col(df, ["trade_date", "date"])

    if not all([ticker_col, close_col, date_col]):
        return df

    df = df.copy()

    if df[close_col].dtype == "object":
        df[close_col] = pd.to_numeric(df[close_col], errors="coerce")

    # Drawdown（60 日滾動高點）
    rolling_max = df.groupby(ticker_col)[close_col].transform(
        lambda x: x.rolling(60, min_periods=20).max()
    )
    df["risk_drawdown"] = ((df[close_col] - rolling_max) / rolling_max).replace(
        [np.inf, -np.inf], np.nan
    )

    # 波動率 Regime（基於 60 日波動率的分位數）
    if "trend_volatility_60" in df.columns:
        df["risk_volatility_regime"] = df.groupby(ticker_col)["trend_volatility_60"].transform(
            lambda x: pd.cut(x.rank(pct=True), bins=[0, 0.33, 0.67, 1.0],
                             labels=[0, 1, 2], include_lowest=True)
        )
    else:
        # 如果 trend 還沒算，自己算
        daily_ret = df.groupby(ticker_col)[close_col].pct_change(fill_method=None)
        vol_60 = daily_ret.groupby(df[ticker_col]).transform(
            lambda x: x.rolling(60, min_periods=20).std()
        )
        df["risk_volatility_regime"] = df.groupby(ticker_col)[close_col].transform(
            lambda _: pd.cut(vol_60.rank(pct=True), bins=[0, 0.33, 0.67, 1.0],
                             labels=[0, 1, 2], include_lowest=True)
        )

    # 大盤報酬（跨公司的平均日報酬，20 日滾動）
    # 過濾掉 Inf/NaN 並裁切極端值，避免停牌/異常股污染大盤指標
    daily_ret_all = df.groupby(ticker_col)[close_col].pct_change(fill_method=None)
    daily_ret_clean = daily_ret_all.replace([np.inf, -np.inf], np.nan).clip(-0.5, 0.5)
    market_ret = daily_ret_clean.groupby(df[date_col]).mean()
    market_ret_20 = market_ret.rolling(20, min_periods=10).mean()
    market_ret_map = market_ret_20.to_dict()
    df["risk_market_ret_20d"] = df[date_col].map(market_ret_map)

    risk_cols = [c for c in df.columns if c.startswith("risk_")]
    logger.info(f"  Risk features: {len(risk_cols)} features")

    return df


# ============================================================
# 主流程
# ============================================================

@timer
def run_feature_pipeline(prices_df: pd.DataFrame,
                         financial_df: pd.DataFrame = None,
                         text_df: pd.DataFrame = None,
                         config: dict = None) -> pd.DataFrame:
    """
    五大支柱特徵工程主流程。

    Args:
        prices_df: 股價 DataFrame（含標籤）
        financial_df: 損益表 DataFrame（已處理，含 _sq, pit_date）
        text_df: 文本 DataFrame
        config: 設定字典

    Returns:
        Feature Store DataFrame
    """
    logger.info("=" * 60)
    logger.info("Five-Pillar Feature Engineering")
    logger.info("=" * 60)

    config = config or {}

    # ① 趨勢與價格
    logger.info("\n[Pillar 1/5] Trend & Price features...")
    df = build_trend_features(prices_df, config)

    # ② 基本面
    logger.info("\n[Pillar 2/5] Fundamental features...")
    df = build_fundamental_features(df, financial_df, config)

    # ③ 估值
    logger.info("\n[Pillar 3/5] Valuation features...")
    df = build_valuation_features(df, config)

    # ④ 事件與敘事
    logger.info("\n[Pillar 4/5] Event & Narrative features...")
    df = build_event_features(df, text_df, config)

    # ⑤ 風險與機制
    logger.info("\n[Pillar 5/5] Risk & Regime features...")
    df = build_risk_features(df, config)

    # 特徵統計
    feature_prefixes = ["trend_", "fund_", "val_", "event_", "risk_"]
    feature_counts = {}
    for prefix in feature_prefixes:
        cols = [c for c in df.columns if c.startswith(prefix)]
        feature_counts[prefix.rstrip("_")] = len(cols)

    total_features = sum(feature_counts.values())
    logger.info(f"\n--- Feature Store Summary ---")
    logger.info(f"  Total features: {total_features}")
    for name, count in feature_counts.items():
        logger.info(f"    {name}: {count}")
    logger.info(f"  Shape: {df.shape[0]:,} rows x {df.shape[1]} cols")
    logger.info(f"  Memory: {df.memory_usage(deep=True).sum()/1024**2:.1f} MB")

    # Inf/NaN 清理
    inf_count = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()
    if inf_count > 0:
        logger.warning(f"  Replacing {inf_count} Inf values with NaN")
        df = df.replace([np.inf, -np.inf], np.nan)

    # === Imputation 策略 ===
    # 策略設計原則：
    #   1. 趨勢/風險特徵（trend_, risk_）：前向填充（同一股票的前一日值），
    #      因為這些特徵具有時序連續性，前一日值是最合理的估計
    #   2. 基本面特徵（fund_）：前向填充（季報更新前延用上季數值），
    #      這與 PIT 邏輯一致——財報公告前，投資人只能看到上季數據
    #   3. 估值特徵（val_）：前向填充
    #   4. 事件特徵（event_）：填 0（無新聞 = 0 則新聞計數）
    #   5. 剩餘 NaN：不做填充，留給模型的 NaN-aware 機制處理
    #      （LightGBM/XGBoost 原生支援 NaN splitting）
    ticker_col = _find_col(df, ["company_id", "stock_id"])
    date_col = _find_col(df, ["trade_date", "date"])

    if ticker_col and date_col:
        df = df.sort_values([ticker_col, date_col])

        # 前向填充（per-stock），limit=63（約一季交易日）避免過期資訊無限延伸
        ffill_prefixes = ["trend_", "fund_", "val_", "risk_"]
        ffill_cols = [c for c in df.columns
                      if any(c.startswith(p) for p in ffill_prefixes) and df[c].dtype != "object"]
        if ffill_cols:
            before_nan = df[ffill_cols].isna().sum().sum()
            df[ffill_cols] = df.groupby(ticker_col)[ffill_cols].ffill(limit=63)
            after_nan = df[ffill_cols].isna().sum().sum()
            filled = before_nan - after_nan
            logger.info(f"  Imputation (ffill, limit=63): {filled:,} NaN filled across {len(ffill_cols)} columns")

        # 事件特徵：填 0
        event_cols = [c for c in df.columns if c.startswith("event_") and df[c].dtype != "object"]
        if event_cols:
            before_nan = df[event_cols].isna().sum().sum()
            df[event_cols] = df[event_cols].fillna(0)
            after_nan = df[event_cols].isna().sum().sum()
            filled = before_nan - after_nan
            logger.info(f"  Imputation (zero-fill events): {filled:,} NaN filled across {len(event_cols)} columns")

        remaining_nan = df.select_dtypes(include=[np.number]).isna().sum().sum()
        total_cells = df.select_dtypes(include=[np.number]).size
        logger.info(f"  Post-imputation NaN: {remaining_nan:,} / {total_cells:,} "
                    f"({remaining_nan/total_cells*100:.2f}%) — handled by model NaN-aware splitting")

    return df


# ============================================================
# 輔助函式
# ============================================================

def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None
