"""
五大支柱特徵工程模組 — Phase 4 增強版

五大支柱：
  ① 趨勢與價格 (trend_)  — MA, EMA, MACD, 動量, 波動率, ATR, RSI, BB, Volume
  ② 基本面 (fund_)       — 毛利率, 營業利益率, 營收YoY, EPS
                          + Phase 4: ROE, ROA, ROIC, EBITDA, D/E, 流動比率
  ③ 估值 (val_)          — P/E ratio
                          + Phase 4: P/B, P/S, EV/EBITDA
  ④ 事件與敘事 (event_)  — 新聞量, 情緒代理, 標題關鍵字
  ⑤ 風險與機制 (risk_)   — 波動率Regime, 回撤, 大盤指標
                          + Phase 4: 複合機制指標, 市場寬度, 波動率期限結構

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
    # 注意：不做 copy()，直接在原 DataFrame 上操作以節省記憶體（pipeline 模式）

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
            lambda x: x.pct_change(n)
        )

    # 滾動波動率
    daily_ret = df.groupby(ticker_col)[close_col].pct_change()
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
                               config: dict,
                               bs_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    基本面特徵 — 將 income_stmt + balance_sheet 的指標 PIT-safe 併入價格表。

    策略：
      1. 只使用 pit_date <= trade_date 的財報（避免 look-ahead）
      2. 每個 trade_date 取最近一期可用財報
      3. 生成 fund_ 前綴特徵

    Phase 4 新增：bs_df 參數，合併 ROE/ROA/ROIC/EBITDA/D_E 等衍生指標
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
                 c.startswith("operating_margin") or c.startswith("net_margin") or
                 c == "eps"]  # eps 用於估值因子 (val_ps, val_ev_ebitda) 的 implied_shares 計算

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

    # merge_asof 要求兩邊都按 key 排序 — 使用 inplace 排序節省記憶體
    import gc as _gc
    prices_df.sort_values([date_col], inplace=True)
    prices_df.reset_index(drop=True, inplace=True)
    fin_merge.sort_values([date_col], inplace=True)
    fin_merge.reset_index(drop=True, inplace=True)

    result = pd.merge_asof(
        prices_df,
        fin_merge,
        on=date_col,
        by="company_id",
        direction="backward",
        suffixes=("", "_fin"),
    )
    # 立即釋放 merge 輸入
    del prices_df, fin_merge
    _gc.collect()

    # 重新命名為 fund_ 前綴
    rename_map = {}
    for col in fund_cols:
        new_name = f"fund_{col}" if not col.startswith("fund_") else col
        if col in result.columns:
            rename_map[col] = new_name
    result.rename(columns=rename_map, inplace=True)

    # 還原排序
    result.sort_values([ticker_col, date_col], inplace=True)
    result.reset_index(drop=True, inplace=True)

    fund_features = [c for c in result.columns if c.startswith("fund_")]
    logger.info(f"  Fundamental features merged: {len(fund_features)} features (PIT-safe)")

    # ---- Phase 4: 合併資產負債表衍生指標 ----
    if bs_df is not None and len(bs_df) > 0:
        result = _merge_bs_features(result, bs_df, ticker_col, date_col)

    return result


def _merge_bs_features(prices_df: pd.DataFrame, bs_df: pd.DataFrame,
                       ticker_col: str, date_col: str) -> pd.DataFrame:
    """
    Phase 4: PIT-safe 合併資產負債表衍生指標到價格表。

    合併欄位（若存在）：roe, roa, roic, ebitda, ebitda_margin,
    debt_equity, current_ratio, nopat, stockholders_equity, total_assets,
    revenue_sq (用於估值特徵計算)
    """
    bs_feature_cols = [
        "roe", "roa", "roic", "ebitda", "ebitda_margin",
        "debt_equity", "current_ratio", "nopat",
        "stockholders_equity", "total_assets", "revenue_sq",
    ]

    # 檢查 bs_df 有哪些可用欄位
    available_cols = [c for c in bs_feature_cols if c in bs_df.columns]
    if not available_cols:
        logger.warning("BS DataFrame has no usable feature columns. Skipping BS merge.")
        return prices_df

    if "pit_date" not in bs_df.columns:
        logger.warning("BS DataFrame missing pit_date. Skipping BS merge.")
        return prices_df

    # 準備合併
    bs_id_col = "company_id" if "company_id" in bs_df.columns else None
    if not bs_id_col:
        logger.warning("BS DataFrame missing company_id. Skipping BS merge.")
        return prices_df

    bs_merge = bs_df[[bs_id_col, "pit_date"] + available_cols].copy()
    bs_merge = bs_merge.dropna(subset=["pit_date"])
    bs_merge = bs_merge.sort_values([bs_id_col, "pit_date"])

    # 重命名 pit_date → date_col 以供 merge_asof
    bs_merge[date_col] = pd.to_datetime(bs_merge["pit_date"])
    bs_merge = bs_merge.drop(columns=["pit_date"])

    prices_df[date_col] = pd.to_datetime(prices_df[date_col])

    import gc as _gc

    # 避免重複欄位：先移除 prices_df 中已有的同名欄
    overlap = [c for c in available_cols if c in prices_df.columns]
    if overlap:
        logger.info(f"  Dropping overlapping columns before BS merge: {overlap}")
        prices_df.drop(columns=overlap, inplace=True)

    # inplace 排序節省記憶體
    prices_df.sort_values([date_col], inplace=True)
    prices_df.reset_index(drop=True, inplace=True)
    bs_merge.sort_values([date_col], inplace=True)
    bs_merge.reset_index(drop=True, inplace=True)

    result = pd.merge_asof(
        prices_df, bs_merge,
        on=date_col,
        by=bs_id_col,
        direction="backward",
        suffixes=("", "_bs"),
    )
    del prices_df, bs_merge
    _gc.collect()

    # 重命名為 fund_ 前綴（roe → fund_roe 等），保留 raw 欄位供估值用
    rename_map = {}
    for col in available_cols:
        if col in result.columns:
            # stockholders_equity / total_assets / revenue_sq 保留原名供估值計算
            if col not in ("stockholders_equity", "total_assets", "revenue_sq"):
                rename_map[col] = f"fund_{col}"
    result.rename(columns=rename_map, inplace=True)

    result.sort_values([ticker_col, date_col], inplace=True)
    result.reset_index(drop=True, inplace=True)

    bs_added = [c for c in result.columns if c.startswith("fund_") and
                c.replace("fund_", "") in bs_feature_cols]
    logger.info(f"  Phase 4 BS features merged: {len(bs_added)} features "
                f"({', '.join(bs_added)})")

    return result


# ============================================================
# ③ 估值特徵
# ============================================================

@timer
def build_valuation_features(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    估值特徵 — P/E, P/B, P/S, EV/EBITDA。

    Phase 1: val_pe = closing_price / eps_sq
    Phase 4 新增:
      - val_pb = closing_price * shares_outstanding / stockholders_equity
               （若無 shares_outstanding，用 market_cap proxy：市值 / 權益）
      - val_ps = market_cap / revenue_sq（或 price / revenue_per_share proxy）
      - val_ev_ebitda = (market_cap + debt - cash_proxy) / ebitda
    """
    close_col = _find_col(df, ["closing_price", "close"])
    eps_col = _find_col(df, ["fund_eps", "fund_eps_sq", "eps_sq", "eps"])
    ticker_col = _find_col(df, ["company_id", "stock_id"])

    if not close_col:
        logger.warning("Missing close column. Skipping valuation features.")
        return df

    # P/E ratio
    if eps_col:
        df["val_pe"] = (df[close_col] / df[eps_col]).replace([np.inf, -np.inf], np.nan)
        # 限制合理範圍 (負值保留但截斷極端值)
        df["val_pe"] = df["val_pe"].clip(-200, 500)
    else:
        logger.warning("Missing eps column. Skipping P/E.")

    # [C2] P/E 分位數 — 修正為截面排名（per date across all stocks）
    date_col_val = _find_col(df, ["trade_date", "date"])
    if date_col_val and "val_pe" in df.columns:
        df["val_pe_rank"] = df.groupby(date_col_val)["val_pe"].transform(
            lambda x: x.rank(pct=True, na_option="keep")
        )
        logger.info(f"  val_pe_rank: cross-sectional rank (per date), mean={df['val_pe_rank'].mean():.3f}")

    # [C1] Helper: 推算 implied shares — 加入單位校驗 + 診斷
    def _calc_implied_shares(df_ref, net_inc_col_ref, eps_col_ref):
        safe_eps = df_ref[eps_col_ref].replace(0, np.nan)
        raw_shares = df_ref[net_inc_col_ref] / safe_eps
        # shares 必須為正數
        implied = raw_shares.where(raw_shares > 0, np.nan)

        # [C1] 單位校驗：若 median shares < 1000，可能 NI(千元) / EPS(元) 單位不匹配
        median_shares = implied.median()
        if pd.notna(median_shares) and median_shares < 1000:
            logger.warning(f"  implied_shares: median={median_shares:.0f} (suspiciously low → trying ×1000 unit correction)")
            implied = implied * 1000
        elif pd.notna(median_shares):
            logger.info(f"  implied_shares: median={median_shares:.0f} shares")

        # 🔴2 fix: 異號強制 NaN — NI>0 但 EPS<0（或反之）代表資料異常
        sign_mismatch = (
            ((df_ref[net_inc_col_ref] > 0) & (df_ref[eps_col_ref] < 0)) |
            ((df_ref[net_inc_col_ref] < 0) & (df_ref[eps_col_ref] > 0))
        )
        n_mismatch = sign_mismatch.sum()
        if n_mismatch > 0:
            logger.warning(f"  implied_shares: {n_mismatch} rows with NI/EPS sign mismatch → forced NaN")
            implied = implied.where(~sign_mismatch, np.nan)

        return implied

    # [C1] P/B ratio — 改善 clip + 診斷
    if "stockholders_equity" in df.columns:
        net_inc_col = _find_col(df, ["fund_net_income_sq", "net_income_sq"])
        if eps_col and net_inc_col:
            implied_shares = _calc_implied_shares(df, net_inc_col, eps_col)
            safe_shares = implied_shares.replace(0, np.nan)
            bvps = df["stockholders_equity"] / safe_shares
            safe_bvps = bvps.where(bvps > 0, np.nan)  # BVPS 應為正（正常公司）
            df["val_pb"] = (df[close_col] / safe_bvps).replace([np.inf, -np.inf], np.nan)
            df["val_pb"] = df["val_pb"].clip(0, 30)
            # [C1] 診斷：clip 命中率
            at_clip_max = (df["val_pb"] >= 29.9).sum()
            valid_pb = df["val_pb"].notna().sum()
            clip_pct = at_clip_max / max(valid_pb, 1) * 100
            if clip_pct > 50:
                logger.error(f"  val_pb: {clip_pct:.0f}% at clip max — implied_shares may have unit issues!")
            logger.info(f"  val_pb: mean={df['val_pb'].mean():.2f}, valid={valid_pb}, at_clip_max={clip_pct:.1f}%")
        else:
            if ticker_col:
                df["val_pb"] = df.groupby(ticker_col)["stockholders_equity"].transform(
                    lambda x: x.rank(pct=True, ascending=False)
                )
                logger.info("  val_pb: fallback to equity rank (no EPS/net_income for shares)")
    else:
        logger.info("  val_pb: skipped (no stockholders_equity)")

    # ---- Phase 4: P/S ratio (Price-to-Sales) ----
    if "revenue_sq" in df.columns:
        net_inc_col = _find_col(df, ["fund_net_income_sq", "net_income_sq"])
        if eps_col and net_inc_col:
            implied_shares = _calc_implied_shares(df, net_inc_col, eps_col)
            safe_shares = implied_shares.replace(0, np.nan)
            rev_per_share = df["revenue_sq"] / safe_shares
            safe_rps = rev_per_share.replace(0, np.nan)
            df["val_ps"] = (df[close_col] / safe_rps).replace([np.inf, -np.inf], np.nan)
            df["val_ps"] = df["val_ps"].clip(-10, 100)
            logger.info(f"  val_ps: mean={df['val_ps'].mean():.2f}")
        else:
            logger.info("  val_ps: skipped (no EPS/net_income for shares estimation)")
    else:
        logger.info("  val_ps: skipped (no revenue_sq)")

    # ---- Phase 4: EV/EBITDA ----
    ebitda_col = _find_col(df, ["fund_ebitda", "ebitda"])
    if ebitda_col:
        # Bug #3 fix: 用修正版 implied_shares
        # Bug #4 fix: EV = market_cap + total_debt - cash_proxy
        net_inc_col = _find_col(df, ["fund_net_income_sq", "net_income_sq"])
        has_components = (eps_col and net_inc_col and
                          "total_assets" in df.columns)
        if has_components:
            implied_shares = _calc_implied_shares(df, net_inc_col, eps_col)
            market_cap = df[close_col] * implied_shares

            # EV = market_cap + total_debt - cash_proxy
            # 🟡8 fix: total_debt = D/E × equity，需防護 equity≤0 和 D/E 缺失
            debt_col = _find_col(df, ["fund_debt_equity"])
            if "stockholders_equity" in df.columns and debt_col:
                de_ratio = df[debt_col].fillna(0).clip(lower=0)  # D/E < 0 不合理 → 0
                safe_equity = df["stockholders_equity"].clip(lower=0)  # 負 equity → 0（無法推算 debt）
                total_debt = (de_ratio * safe_equity).clip(lower=0)
            else:
                total_debt = pd.Series(0, index=df.index)

            # C3 fix: current_assets 包含存貨/應收帳款，作為 cash proxy 過度膨脹
            # 無獨立 cash_and_equivalents 欄位，保守處理：cash_proxy=0
            # EV = market_cap + total_debt (不扣除現金，避免低估 EV)
            cash_proxy = pd.Series(0, index=df.index)
            if "cash_and_equivalents" in df.columns:
                cash_proxy = df["cash_and_equivalents"].fillna(0)
                logger.info("  val_ev_ebitda: using cash_and_equivalents as cash proxy for EV")
            else:
                logger.info("  val_ev_ebitda: no cash column available, using cash_proxy=0 (conservative)")

            ev = market_cap + total_debt - cash_proxy

            safe_ebitda = df[ebitda_col].replace(0, np.nan)
            df["val_ev_ebitda"] = (ev / safe_ebitda).replace([np.inf, -np.inf], np.nan)
            df["val_ev_ebitda"] = df["val_ev_ebitda"].clip(-50, 200)
            logger.info(f"  val_ev_ebitda: mean={df['val_ev_ebitda'].mean():.2f}")
        else:
            logger.info("  val_ev_ebitda: skipped (missing components)")
    else:
        logger.info("  val_ev_ebitda: skipped (no EBITDA)")

    # 清理暫存欄位（stockholders_equity, total_assets, revenue_sq 可選性保留或移除）
    temp_cols_to_drop = [c for c in ["stockholders_equity", "total_assets", "revenue_sq"]
                         if c in df.columns]
    if temp_cols_to_drop:
        df = df.drop(columns=temp_cols_to_drop)
        logger.info(f"  Dropped temp columns: {temp_cols_to_drop}")

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

    # 合併到 prices（不做 copy，pipeline 模式）
    prices_df["_date_key"] = pd.to_datetime(prices_df[date_col]).dt.normalize()
    prices_df = prices_df.merge(
        daily_news.rename(columns={"_date": "_date_key"}),
        on="_date_key", how="left",
    )
    prices_df["event_news_count_raw"] = prices_df["event_news_count_raw"].fillna(0)

    # M1 fix: 滾動新聞量 — shift(1) 避免 lookahead bias（用前一日新聞預測當日）
    if ticker_col:
        for window in [1, 5]:
            prices_df[f"event_news_count_{window}d"] = prices_df.groupby(ticker_col)[
                "event_news_count_raw"
            ].transform(lambda x: x.shift(1).rolling(window, min_periods=1).sum())

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

    # 不做 copy，pipeline 模式直接操作

    if df[close_col].dtype == "object":
        df[close_col] = pd.to_numeric(df[close_col], errors="coerce")

    # Drawdown（60 日滾動高點）
    rolling_max = df.groupby(ticker_col)[close_col].transform(
        lambda x: x.rolling(60, min_periods=20).max()
    )
    df["risk_drawdown"] = ((df[close_col] - rolling_max) / rolling_max).replace(
        [np.inf, -np.inf], np.nan
    )

    # 波動率 Regime（基於 60 日波動率的分位數）→ 轉為 float 避免 Categorical 問題
    if "trend_volatility_60" in df.columns:
        df["risk_volatility_regime"] = df.groupby(ticker_col)["trend_volatility_60"].transform(
            lambda x: pd.cut(x.rank(pct=True), bins=[0, 0.33, 0.67, 1.0],
                             labels=[0, 1, 2], include_lowest=True)
        ).astype(float)
    else:
        # 如果 trend 還沒算，自己算 60 日波動率再分位
        daily_ret = df.groupby(ticker_col)[close_col].pct_change()
        vol_60 = daily_ret.groupby(df[ticker_col]).transform(
            lambda x: x.rolling(60, min_periods=20).std()
        )
        df["_vol_60_tmp"] = vol_60
        df["risk_volatility_regime"] = df.groupby(ticker_col)["_vol_60_tmp"].transform(
            lambda x: pd.cut(x.rank(pct=True), bins=[0, 0.33, 0.67, 1.0],
                             labels=[0, 1, 2], include_lowest=True)
        ).astype(float)
        df.drop(columns=["_vol_60_tmp"], inplace=True)

    # 大盤報酬（跨公司的平均日報酬，20 日滾動）
    # 過濾掉 Inf/NaN 並裁切極端值，避免停牌/異常股污染大盤指標
    daily_ret_all = df.groupby(ticker_col)[close_col].pct_change()
    daily_ret_clean = daily_ret_all.replace([np.inf, -np.inf], np.nan).clip(-0.5, 0.5)
    market_ret = daily_ret_clean.groupby(df[date_col]).mean()
    # 🔴1 fix: shift(1) 避免前視偏差 — 用前一日及更早的大盤報酬預測當日
    market_ret_20 = market_ret.rolling(20, min_periods=10).mean().shift(1)
    market_ret_map = market_ret_20.to_dict()
    df["risk_market_ret_20d"] = df[date_col].map(market_ret_map)

    # ================================================================
    # Phase 4 新增：複合機制特徵（設計避免與 trend_volatility_60 共線）
    # ================================================================

    # --- Market Breadth（市場寬度）---
    # 定義：當日上漲股票佔比（advance-decline ratio 的簡化）
    # 與個股 volatility 正交（衡量市場整體參與度，非個股波動）
    daily_ret_binary = (daily_ret_clean > 0).astype(float)
    daily_ret_binary[daily_ret_clean.isna()] = np.nan
    breadth_daily = daily_ret_binary.groupby(df[date_col]).mean()  # 上漲比率 [0,1]

    # 🔴1 fix: 20日平滑 + shift(1) 避免前視偏差
    breadth_20 = breadth_daily.rolling(20, min_periods=10).mean().shift(1)
    breadth_map = breadth_20.to_dict()
    df["risk_market_breadth"] = df[date_col].map(breadth_map)
    logger.info(f"  risk_market_breadth: mean={df['risk_market_breadth'].mean():.4f}")

    # --- Volatility Term Structure（波動率期限結構）---
    # 定義：短期波動率 / 長期波動率 的比值
    # 獨立維度：不是波動率本身，而是波動率的 shape（backwardation/contango）
    # > 1 表示短期波動高於長期（壓力狀態），< 1 表示正常
    if "trend_volatility_20" in df.columns and "trend_volatility_60" in df.columns:
        safe_vol60 = df["trend_volatility_60"].replace(0, np.nan)
        df["risk_vol_term_structure"] = (
            df["trend_volatility_20"] / safe_vol60
        ).replace([np.inf, -np.inf], np.nan).clip(0.2, 5.0)
        logger.info(f"  risk_vol_term_structure: mean={df['risk_vol_term_structure'].mean():.4f}")
    else:
        # 自己計算
        ret_for_vol = df.groupby(ticker_col)[close_col].pct_change()
        vol_20 = ret_for_vol.groupby(df[ticker_col]).transform(
            lambda x: x.rolling(20, min_periods=10).std()
        )
        vol_60 = ret_for_vol.groupby(df[ticker_col]).transform(
            lambda x: x.rolling(60, min_periods=20).std()
        )
        safe_vol60 = vol_60.replace(0, np.nan)
        df["risk_vol_term_structure"] = (vol_20 / safe_vol60).replace(
            [np.inf, -np.inf], np.nan
        ).clip(0.2, 5.0)
        logger.info(f"  risk_vol_term_structure: mean={df['risk_vol_term_structure'].mean():.4f}")

    # --- Regime Composite（複合機制指標）---
    # 設計原則：用正交維度（market breadth + vol term structure + market return）
    # 組合成單一 regime 信號，避免與 trend_volatility_60 共線
    # composite = z-score(market_breadth) + z-score(market_ret_20d) - z-score(vol_term_structure)
    # 高值 = 牛市機制（寬度高、報酬正、波動率 contango）
    # 低值 = 熊市機制
    composite_cols = []
    if "risk_market_breadth" in df.columns:
        composite_cols.append("risk_market_breadth")
    if "risk_market_ret_20d" in df.columns:
        composite_cols.append("risk_market_ret_20d")
    if "risk_vol_term_structure" in df.columns:
        composite_cols.append("risk_vol_term_structure")

    if len(composite_cols) >= 2:
        # [A fix] Z-score 標準化 — expanding 需區分市場指標 vs 個股指標
        # 市場指標（每日一值，map 到所有股票）：先 deduplicate 再 expanding
        # 個股指標（vol_term_structure）：需 groupby(ticker) expanding
        market_level_cols = {"risk_market_breadth", "risk_market_ret_20d"}
        z_parts = []
        for col in composite_cols:
            if col in market_level_cols and date_col:
                # 市場指標：按日 deduplicate → expanding → map back
                daily_vals = df.groupby(date_col)[col].first().sort_index()
                exp_mean = daily_vals.expanding(min_periods=20).mean()
                exp_std = daily_vals.expanding(min_periods=20).std().replace(0, np.nan)
                daily_z = (daily_vals - exp_mean) / exp_std
                z = df[date_col].map(daily_z)
            elif ticker_col:
                # 個股指標：per-stock expanding
                z = df.groupby(ticker_col)[col].transform(
                    lambda x: (x - x.expanding(min_periods=20).mean()) /
                              x.expanding(min_periods=20).std().replace(0, np.nan)
                )
            else:
                # Fallback
                expanding_mean = df[col].expanding(min_periods=20).mean()
                expanding_std = df[col].expanding(min_periods=20).std().replace(0, np.nan)
                z = (df[col] - expanding_mean) / expanding_std
            # vol_term_structure 取負號（高值=壓力→低 regime）
            if col == "risk_vol_term_structure":
                z = -z
            z_parts.append(z)

        df["risk_regime_composite"] = sum(z_parts) / len(z_parts)
        df["risk_regime_composite"] = df["risk_regime_composite"].clip(-3, 3)
        logger.info(f"  risk_regime_composite: mean={df['risk_regime_composite'].mean():.4f}")
    else:
        logger.warning("  Insufficient components for regime_composite. Skipping.")

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
                         config: dict = None,
                         bs_df: pd.DataFrame = None,
                         industry_df: pd.DataFrame = None,
                         inst_df: pd.DataFrame = None,
                         mg_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    特徵工程主流程。Phase 5A 由五大支柱擴增為九類：

      五大支柱：trend_ / fund_ / val_ / event_ / risk_
      Phase 5A 新增：chip_ / mg_ / ind_ （event_ 增強由 industry_df 提供 stock_name）

    Args:
        prices_df: 股價 DataFrame（含標籤）
        financial_df: 損益表 DataFrame（已處理，含 _sq, pit_date）
        text_df: 文本 DataFrame（full 版建議含 content 欄位）
        config: 設定字典
        bs_df: Phase 4 資產負債表 DataFrame
        industry_df: Phase 5A 產業分類（company_id, stock_name, industry_category）
        inst_df: Phase 5A 三大法人（company_id, trade_date, foreign/trust/dealer_net）
        mg_df: Phase 5A 融資融券（company_id, trade_date, margin_*, short_*）

    Returns:
        Feature Store DataFrame
    """
    import gc as _gc
    logger.info("=" * 60)
    logger.info("Feature Engineering Pipeline (Phase 5A)")
    logger.info("=" * 60)

    config = config or {}

    # ① 趨勢與價格
    logger.info("\n[Pillar 1/5] Trend & Price features...")
    df = build_trend_features(prices_df, config)
    del prices_df; _gc.collect()

    # ② 基本面（Phase 4: 含 BS 衍生指標）
    logger.info("\n[Pillar 2/5] Fundamental features...")
    df = build_fundamental_features(df, financial_df, config, bs_df=bs_df)
    del financial_df, bs_df; _gc.collect()

    # ③ 估值（Phase 4: 含 P/B, P/S, EV/EBITDA）
    logger.info("\n[Pillar 3/5] Valuation features...")
    df = build_valuation_features(df, config)
    _gc.collect()

    # ④ 事件與敘事
    # Phase 5A：若有 industry_df，改用 phase5a 強化版（per-stock mention）
    if industry_df is not None and not industry_df.empty and text_df is not None and len(text_df) > 0:
        logger.info("\n[Pillar 4/5] Event & Narrative features (Phase 5A per-stock)...")
        from .engineer_phase5a import build_event_features_phase5a
        df = build_event_features_phase5a(df, text_df, industry_df, config)
    else:
        logger.info("\n[Pillar 4/5] Event & Narrative features (legacy global-count)...")
        df = build_event_features(df, text_df, config)
    del text_df; _gc.collect()

    # ⑤ 風險與機制
    logger.info("\n[Pillar 5/5] Risk & Regime features...")
    df = build_risk_features(df, config)

    # === Phase 5A 新增支柱 ===
    if industry_df is not None and not industry_df.empty:
        logger.info("\n[Phase 5A] Industry relative strength features...")
        from .engineer_phase5a import build_industry_features
        df = build_industry_features(df, industry_df, config)
        del industry_df; _gc.collect()

    if inst_df is not None and not inst_df.empty:
        logger.info("\n[Phase 5A] Chip (institutional investors) features...")
        from .engineer_phase5a import build_chip_features
        df = build_chip_features(df, inst_df, config)
        del inst_df; _gc.collect()

    if mg_df is not None and not mg_df.empty:
        logger.info("\n[Phase 5A] Margin trading features...")
        from .engineer_phase5a import build_margin_features
        df = build_margin_features(df, mg_df, config)
        del mg_df; _gc.collect()

    # 特徵統計（Phase 5A 擴充 prefix 列表）
    feature_prefixes = [
        "trend_", "fund_", "val_", "event_", "risk_",
        "chip_", "mg_", "ind_",
    ]
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
        # Phase 5A: ind_ 屬於 cross-sectional，不適合 ffill；chip_/mg_ 為每日籌碼，可 ffill
        ffill_prefixes = ["trend_", "fund_", "val_", "risk_", "chip_", "mg_"]
        ffill_cols = [c for c in df.columns
                      if any(c.startswith(p) for p in ffill_prefixes) and df[c].dtype != "object"]
        if ffill_cols:
            before_nan = df[ffill_cols].isna().sum().sum()
            df[ffill_cols] = df.groupby(ticker_col)[ffill_cols].ffill(limit=63)
            after_nan = df[ffill_cols].isna().sum().sum()
            filled = before_nan - after_nan
            logger.info(f"  Imputation (ffill, limit=63): {filled:,} NaN filled across {len(ffill_cols)} columns")

        # 事件特徵：填 0（Phase 5A 新增 ind_ 也填 0 — 無產業 peer 時退化為 neutral）
        zero_fill_prefixes = ["event_", "ind_"]
        zero_fill_cols = [
            c for c in df.columns
            if any(c.startswith(p) for p in zero_fill_prefixes) and df[c].dtype != "object"
        ]
        if zero_fill_cols:
            before_nan = df[zero_fill_cols].isna().sum().sum()
            df[zero_fill_cols] = df[zero_fill_cols].fillna(0)
            after_nan = df[zero_fill_cols].isna().sum().sum()
            filled = before_nan - after_nan
            logger.info(f"  Imputation (zero-fill event/ind): {filled:,} NaN filled across {len(zero_fill_cols)} columns")

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
