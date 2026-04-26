"""
Phase 5A 特徵擴充模組
=====================
在既有五大支柱之上新增三類特徵（mg_ 已於 2026-04-19 下架）：

  A. 籌碼特徵 (chip_*)       — 三大法人動向（foreign/trust/dealer）
  B. [DEPRECATED 2026-04-19] 融資融券特徵 (mg_*) — 已下架，見下方說明
  C. 產業相對強弱 (ind_*)    — 個股 vs 產業 peer 的超額報酬
  D. 事件質性特徵 (event_*)  — stock_text 內文套用、per-stock 計數與語氣代理

── mg_ 支柱下架說明（2026-04-19）──────────────────────────────────
決策：SCOPE.md v1.0 決議下架 mg_ 支柱，理由如下：
  1. FinMind margin 覆蓋僅 1,136 / 1,932 = 58.8%，其中約 100 支是結構性
     不可下載（KY 股、創業板、新上市、ETF 非信用交易標的）。
  2. 過往範例（G1 聯發科、G10 台泥、G20 174 半導體、G2 華城）均未使用
     融資融券特徵，價值有限。
  3. margin_trading.parquet 檔案仍保留於 選用資料集/parquet/ 作為資料透明
     之證明，但不進入模型訓練管線。詳見 資料來源宣告.md 的 B6 欄位說明。
  4. build_margin_features() 函式保留以供日後查詢，但 執行Phase1_資料工程.py
     已設定 mg_df=None，此函式不再被呼叫。

設計原則（Phase 5A 約束）：
  1. PIT-safe：所有聚合都以 shift(1) 避免 look-ahead（籌碼/融資是當日收盤後公布，
     模型在 T 日可用的是 T-1 日數據）。
  2. 群組 shift：rolling 計算一律在 groupby(company_id) 內做，避免跨股票洩漏。
  3. 缺失 graceful：若某類資料缺失（例如 chip 還沒抓完），該類特徵自動跳過。
"""
from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..utils.helpers import timer


# ============================================================
# A. 籌碼特徵 (chip_*)
# ============================================================

@timer
def build_chip_features(
    prices_df: pd.DataFrame,
    inst_df: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """
    三大法人籌碼特徵。

    Args:
        prices_df: 股價 DataFrame（含 company_id, trade_date）
        inst_df:   institutional_investors.parquet 載入結果
                    欄位：company_id, trade_date, foreign_net, trust_net, dealer_net, all_inst_net
        config: 設定字典

    Features:
      - chip_foreign_net_1d/5d/20d: 外資買超（T-1 日）/ 5 日累計 / 20 日累計
      - chip_trust_net_5d/20d:      投信買超 5/20 日累計
      - chip_dealer_net_5d:         自營商買超 5 日累計
      - chip_all_inst_net_5d/20d:   三大法人合計 5/20 日累計
      - chip_foreign_trend_20d:     foreign 累計的 20 日斜率（動量）
      - chip_consensus_5d:          三方向一致性 (-1/0/+1)
      - chip_foreign_intensity:     外資買超相對股票流通量（需 volume）

    PIT 安全：以 shift(1) 確保 T 日可看的是 T-1 日（收盤後公布當日）。
    """
    if inst_df is None or inst_df.empty:
        logger.warning("No institutional data. Skipping chip features.")
        return prices_df

    ticker_col = _find_col(prices_df, ["company_id", "stock_id"])
    date_col = _find_col(prices_df, ["trade_date", "date"])
    if not (ticker_col and date_col):
        logger.warning("Missing ticker/date in prices_df. Skipping chip features.")
        return prices_df

    # 對齊欄位名
    inst = inst_df.rename(
        columns={"stock_id": "company_id", "date": "trade_date"}
    ).copy()
    inst["trade_date"] = pd.to_datetime(inst["trade_date"])
    prices_df["_td"] = pd.to_datetime(prices_df[date_col])

    # 先挑要的欄位避免記憶體膨脹
    chip_cols = [
        c for c in ["foreign_net", "trust_net", "dealer_net", "all_inst_net"]
        if c in inst.columns
    ]
    if not chip_cols:
        logger.warning("inst_df has no net columns. Skipping chip features.")
        prices_df.drop(columns="_td", inplace=True, errors="ignore")
        return prices_df

    inst = inst[["company_id", "trade_date"] + chip_cols]

    # 合併進 prices_df
    prices_df = prices_df.merge(
        inst,
        left_on=[ticker_col, "_td"],
        right_on=["company_id", "trade_date"],
        how="left",
        suffixes=("", "_inst"),
    )

    # 若 prices 本身 ticker_col != "company_id"，inst 的 company_id 會變重複欄位
    if "company_id_inst" in prices_df.columns:
        prices_df.drop(columns=["company_id_inst"], inplace=True)
    if "trade_date_inst" in prices_df.columns:
        prices_df.drop(columns=["trade_date_inst"], inplace=True)
    # merge 後 inst 的 trade_date 會覆蓋 _td；以防萬一
    # 實務上 merge 不會替換原欄位；但若有 trade_date 衝突則補上
    if date_col != "trade_date" and "trade_date" in prices_df.columns:
        prices_df.drop(columns=["trade_date"], inplace=True, errors="ignore")

    # Sort for rolling
    prices_df = prices_df.sort_values([ticker_col, "_td"])

    # === PIT-safe rolling ===
    # shift(1) = T-1 日（昨日已公布）
    for base, windows in [
        ("foreign_net", [1, 5, 20]),
        ("trust_net",   [5, 20]),
        ("dealer_net",  [5]),
        ("all_inst_net", [5, 20]),
    ]:
        if base not in prices_df.columns:
            continue

        # 先對每個 ticker 的 base 欄位做 shift(1)
        shifted = prices_df.groupby(ticker_col)[base].shift(1)

        for w in windows:
            if w == 1:
                prices_df[f"chip_{base}_1d"] = shifted
            else:
                prices_df[f"chip_{base}_{w}d"] = (
                    shifted.groupby(prices_df[ticker_col])
                    .rolling(w, min_periods=max(2, w // 3))
                    .sum()
                    .reset_index(level=0, drop=True)
                )

    # 外資 20 日累計的 slope（動量）：用 cumsum 差分代理
    if "chip_foreign_net_20d" in prices_df.columns:
        prices_df["chip_foreign_trend_20d"] = prices_df.groupby(ticker_col)[
            "chip_foreign_net_20d"
        ].transform(lambda s: s.diff(5))

    # 三方向一致性：foreign/trust/dealer 5 日都同號為 +1/-1，否則 0
    signed_cols = [f"chip_{x}_net_5d" for x in ["foreign", "trust", "dealer"]]
    have = [c for c in signed_cols if c in prices_df.columns]
    if len(have) == 3:
        signs = np.sign(prices_df[have].fillna(0))
        all_pos = (signs == 1).all(axis=1)
        all_neg = (signs == -1).all(axis=1)
        prices_df["chip_consensus_5d"] = 0
        prices_df.loc[all_pos, "chip_consensus_5d"] = 1
        prices_df.loc[all_neg, "chip_consensus_5d"] = -1

    # 清理暫存欄位
    for c in chip_cols + ["_td"]:
        if c in prices_df.columns:
            prices_df.drop(columns=c, inplace=True, errors="ignore")

    chip_feats = [c for c in prices_df.columns if c.startswith("chip_")]
    logger.info(f"  Chip features: {len(chip_feats)}")
    return prices_df


# ============================================================
# B. 融資融券特徵 (mg_*)
# ============================================================

@timer
def build_margin_features(
    prices_df: pd.DataFrame,
    mg_df: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """
    融資融券特徵。

    Args:
        prices_df: 股價 DataFrame（含 company_id, trade_date）
        mg_df:   margin_trading.parquet 載入結果
                  欄位：company_id, trade_date, margin_*, short_*
        config: 設定字典

    Features:
      - mg_margin_balance_1d:       昨日融資餘額（張）
      - mg_margin_change_5d:        5 日融資餘額變化
      - mg_short_change_5d:         5 日融券餘額變化
      - mg_margin_short_ratio:      融資/融券餘額比（代表多空力道）
      - mg_margin_use_rate:         融資使用率（融資餘額/上限）
      - mg_retail_sentiment_5d:     散戶情緒代理（融資增 & 股價漲 = 貪婪）

    PIT 安全：shift(1)。
    """
    if mg_df is None or mg_df.empty:
        logger.warning("No margin data. Skipping margin features.")
        return prices_df

    ticker_col = _find_col(prices_df, ["company_id", "stock_id"])
    date_col = _find_col(prices_df, ["trade_date", "date"])
    if not (ticker_col and date_col):
        logger.warning("Missing ticker/date in prices_df. Skipping margin features.")
        return prices_df

    mg = mg_df.copy()
    mg["trade_date"] = pd.to_datetime(mg["trade_date"])
    prices_df["_td"] = pd.to_datetime(prices_df[date_col])

    take_cols = [
        c for c in [
            "margin_balance", "margin_change",
            "short_balance", "short_change",
            "margin_short_ratio", "margin_use_rate",
        ] if c in mg.columns
    ]
    if not take_cols:
        logger.warning("mg_df has no margin_* columns. Skipping margin features.")
        prices_df.drop(columns="_td", inplace=True, errors="ignore")
        return prices_df

    mg = mg[["company_id", "trade_date"] + take_cols]

    prices_df = prices_df.merge(
        mg,
        left_on=[ticker_col, "_td"],
        right_on=["company_id", "trade_date"],
        how="left",
        suffixes=("", "_mg"),
    )
    if "company_id_mg" in prices_df.columns:
        prices_df.drop(columns=["company_id_mg"], inplace=True)
    if "trade_date_mg" in prices_df.columns:
        prices_df.drop(columns=["trade_date_mg"], inplace=True)
    if date_col != "trade_date" and "trade_date" in prices_df.columns:
        prices_df.drop(columns=["trade_date"], inplace=True, errors="ignore")

    prices_df = prices_df.sort_values([ticker_col, "_td"])

    # shift(1) = 昨日
    for col in take_cols:
        if col in prices_df.columns:
            prices_df[f"mg_{col}_1d"] = prices_df.groupby(ticker_col)[col].shift(1)

    # 5 日變化（mg_margin_change_5d 等）
    for col in ["margin_balance", "short_balance"]:
        shifted = f"mg_{col}_1d"
        if shifted in prices_df.columns:
            prices_df[f"mg_{col}_chg_5d"] = prices_df.groupby(ticker_col)[shifted].transform(
                lambda s: s - s.shift(5)
            )

    # 散戶情緒代理：margin 增 & 價格同方向 5 日 momentum
    if "mg_margin_balance_chg_5d" in prices_df.columns:
        close_col = _find_col(prices_df, ["closing_price", "close"])
        if close_col:
            ret5 = prices_df.groupby(ticker_col)[close_col].transform(
                lambda s: s.pct_change(5)
            )
            prices_df["mg_retail_sentiment_5d"] = np.sign(
                prices_df["mg_margin_balance_chg_5d"].fillna(0)
            ) * np.sign(ret5.fillna(0))

    # 清理暫存欄位
    for c in take_cols + ["_td"]:
        if c in prices_df.columns:
            prices_df.drop(columns=c, inplace=True, errors="ignore")

    mg_feats = [c for c in prices_df.columns if c.startswith("mg_")]
    logger.info(f"  Margin features: {len(mg_feats)}")
    return prices_df


# ============================================================
# C. 產業相對強弱 (ind_*)
# ============================================================

@timer
def build_industry_features(
    prices_df: pd.DataFrame,
    industry_df: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """
    產業相對強弱特徵。

    Args:
        prices_df: 股價 DataFrame（含 close, volume 可選）
        industry_df: industry.parquet 載入結果（company_id, industry_category）
        config: 設定字典

    Features:
      - ind_return_rel_20d:    個股 20D 報酬 - 同產業 median
      - ind_momentum_rank_20d: 在產業內 20D 報酬 rank（0~1, percent rank）
      - ind_volatility_rel_60d:個股 60D 波動率 / 產業 median
      - ind_member_count:      產業成員數（越多越穩定）
    """
    if industry_df is None or industry_df.empty:
        logger.warning("No industry data. Skipping industry features.")
        return prices_df

    ticker_col = _find_col(prices_df, ["company_id", "stock_id"])
    date_col = _find_col(prices_df, ["trade_date", "date"])
    close_col = _find_col(prices_df, ["closing_price", "close"])

    if not all([ticker_col, date_col, close_col]):
        logger.warning("Missing cols in prices_df. Skipping industry features.")
        return prices_df

    # 合併產業分類
    ind_map = industry_df[["company_id", "industry_category"]].drop_duplicates(
        subset="company_id"
    )
    prices_df = prices_df.merge(
        ind_map,
        left_on=ticker_col,
        right_on="company_id",
        how="left",
        suffixes=("", "_ind"),
    )
    if "company_id_ind" in prices_df.columns:
        prices_df.drop(columns="company_id_ind", inplace=True)

    # 若 prices_df 本身沒 company_id 欄位（而是 stock_id），merge 會加一個 company_id
    # 保險起見：merge 後要留住原 ticker_col
    if ticker_col != "company_id" and "company_id" in prices_df.columns:
        prices_df.drop(columns="company_id", inplace=True, errors="ignore")

    # 產業成員數
    counts = prices_df.groupby("industry_category")[ticker_col].transform("nunique")
    prices_df["ind_member_count"] = counts

    # === 個股 20 日報酬 ===
    if prices_df[close_col].dtype == "object":
        prices_df[close_col] = pd.to_numeric(prices_df[close_col], errors="coerce")

    prices_df = prices_df.sort_values([ticker_col, date_col])
    prices_df["_ret_20d"] = prices_df.groupby(ticker_col)[close_col].pct_change(20)
    prices_df["_vol_60d"] = prices_df.groupby(ticker_col)[close_col].transform(
        lambda s: s.pct_change().rolling(60, min_periods=20).std()
    )

    # 以 (trade_date, industry_category) 分組計算 median/rank — cross-sectional
    # ind_return_rel_20d = 個股 ret - 產業 median
    grp = prices_df.groupby([date_col, "industry_category"])
    prices_df["ind_return_rel_20d"] = (
        prices_df["_ret_20d"] - grp["_ret_20d"].transform("median")
    )
    # ind_momentum_rank_20d = 個股 ret 在產業的 percentile rank（0~1）
    prices_df["ind_momentum_rank_20d"] = grp["_ret_20d"].rank(pct=True)

    # ind_volatility_rel_60d = 個股 vol / 產業 median vol
    median_vol = grp["_vol_60d"].transform("median")
    prices_df["ind_volatility_rel_60d"] = prices_df["_vol_60d"] / median_vol.replace(
        0, np.nan
    )

    # 清理暫存
    prices_df.drop(
        columns=["_ret_20d", "_vol_60d", "industry_category"],
        inplace=True,
        errors="ignore",
    )

    ind_feats = [c for c in prices_df.columns if c.startswith("ind_")]
    logger.info(f"  Industry features: {len(ind_feats)}")
    return prices_df


# ============================================================
# D. 事件質性特徵（強化版 event_*）
# ============================================================

# 台股文本情緒關鍵字（粗略，後續 Phase 5B 會用 ANTUSD/FinBERT 完整取代）
_POS_KEYWORDS = [
    "大漲", "飆漲", "突破", "創高", "新高", "買進", "推薦", "利多", "獲利",
    "受惠", "看多", "看好", "強勢", "漲停", "熱銷", "旺季", "訂單", "擴產",
    "超標", "成長", "營收增", "EPS 創", "法說利多", "目標價上調", "獎勵",
]
_NEG_KEYWORDS = [
    "大跌", "崩", "跌停", "重挫", "殺盤", "套牢", "利空", "虧損", "衰退",
    "減資", "減產", "下修", "警示", "違約", "淘汰", "裁員", "併購破局",
    "看空", "賣超", "賣出", "目標價下調", "調降", "不佳", "疲弱", "過剩",
    "減損", "倒閉",
]


def _ngram_regex(names: list[str]) -> re.Pattern:
    """將一堆股票名編成一個大正則，避免 O(n*m) 掃描"""
    # 過濾過短名稱（<=1 字）避免誤命中
    names = [re.escape(n) for n in names if isinstance(n, str) and len(n) >= 2]
    if not names:
        return re.compile(r"$^")  # 永不匹配
    # 用長度降冪排序，讓「台積電」優先於「台」
    names = sorted(names, key=len, reverse=True)
    return re.compile("|".join(names))


@timer
def build_event_features_phase5a(
    prices_df: pd.DataFrame,
    text_df: pd.DataFrame,
    industry_df: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """
    事件質性特徵（強化版）。

    與舊 build_event_features 差異：
      - 舊版只算「全市場」每日新聞量，每檔股票都拿到相同值（0 information）。
      - 新版用 stock_name（來自 industry_df）去比對 text 的 title/content，
        得到**每檔股票** 的提及量。

    Features（每檔每日）：
      - event_mention_cnt_1d:        T-1 日提及量
      - event_mention_cnt_5d/20d:    近 5/20 日累計
      - event_mention_surge:         1d / (5d/5) 速率（突發新聞偵測）
      - event_sent_score_5d:         近 5 日語氣分數（正向-負向關鍵字）
      - event_news_ratio_5d:         news 佔比（news + forum + bbs）
      - event_post_main_ratio_5d:    主文佔比（main / (main+reply+r_reply)）

    PIT 安全：shift(1)，確保 T 日看到 T-1 日的提及。
    """
    if text_df is None or text_df.empty or industry_df is None or industry_df.empty:
        logger.warning("Text or industry df missing. Skipping phase5a event features.")
        return prices_df

    ticker_col = _find_col(prices_df, ["company_id", "stock_id"])
    date_col = _find_col(prices_df, ["trade_date", "date"])
    if not (ticker_col and date_col):
        logger.warning("Missing ticker/date. Skipping phase5a event features.")
        return prices_df

    text_date_col = _find_col(text_df, ["post_time", "date", "publish_date"])
    if not text_date_col:
        logger.warning("No date column in text_df. Skipping.")
        return prices_df

    # === 1) 建立 stock_name -> company_id 映射 ===
    name_map = industry_df[["company_id", "stock_name"]].dropna()
    name_map = name_map[name_map["stock_name"].str.len() >= 2]
    id2name = dict(zip(name_map["company_id"], name_map["stock_name"]))
    name2id = dict(zip(name_map["stock_name"], name_map["company_id"]))
    logger.info(f"  Built name2id map: {len(name2id)} stocks")

    # === 2) 每條 text 找提及的股票 ===
    pattern = _ngram_regex(list(name_map["stock_name"]))
    # 以 title 為主（速度快）；若有 content 則優先用 content
    text_col = _find_col(text_df, ["content", "title"])
    if not text_col:
        logger.warning("No text column. Skipping.")
        return prices_df

    tdf = text_df[[text_date_col, text_col] + [
        c for c in ["p_type", "content_type"] if c in text_df.columns
    ]].copy()
    tdf[text_date_col] = pd.to_datetime(tdf[text_date_col], errors="coerce")
    tdf["_date"] = tdf[text_date_col].dt.normalize()
    tdf = tdf.dropna(subset=["_date", text_col])

    # 在每篇 text 上找所有 mention（一篇可能命中多個）
    logger.info(f"  Scanning {len(tdf):,} text records for mentions...")
    tdf["_mentions"] = tdf[text_col].str.findall(pattern)
    tdf["_mention_cnt"] = tdf["_mentions"].str.len()

    # 預先算情緒代理（對 title 即可）
    pos_pat = re.compile("|".join(map(re.escape, _POS_KEYWORDS)))
    neg_pat = re.compile("|".join(map(re.escape, _NEG_KEYWORDS)))
    tdf["_pos"] = tdf[text_col].str.count(pos_pat)
    tdf["_neg"] = tdf[text_col].str.count(neg_pat)
    tdf["_sent"] = tdf["_pos"] - tdf["_neg"]

    # 展開 mentions → (date, stock_name, sent, is_news, is_main)
    exploded = tdf.explode("_mentions").dropna(subset=["_mentions"])
    exploded = exploded.rename(columns={"_mentions": "stock_name"})
    exploded["_is_news"] = (exploded.get("p_type") == "news").astype(int)
    exploded["_is_main"] = (exploded.get("content_type") == "main").astype(int)
    # 合併回 company_id
    exploded["company_id"] = exploded["stock_name"].map(name2id)

    # Aggregate per (date, company_id)
    daily = exploded.groupby(["_date", "company_id"]).agg(
        mention_cnt=("stock_name", "size"),
        sent_sum=("_sent", "sum"),
        news_cnt=("_is_news", "sum"),
        main_cnt=("_is_main", "sum"),
    ).reset_index()
    logger.info(f"  Aggregated mentions: {len(daily):,} (date, stock) pairs")

    # === 3) 合併到 prices_df ===
    prices_df["_td"] = pd.to_datetime(prices_df[date_col]).dt.normalize()
    prices_df = prices_df.merge(
        daily,
        left_on=[ticker_col, "_td"],
        right_on=["company_id", "_date"],
        how="left",
        suffixes=("", "_ev"),
    )
    # 清理重複欄位
    for c in ["company_id_ev", "_date"]:
        if c in prices_df.columns:
            prices_df.drop(columns=c, inplace=True, errors="ignore")
    # 若 ticker_col != company_id，merge 後會多出 company_id 欄
    if ticker_col != "company_id" and "company_id" in prices_df.columns:
        prices_df.drop(columns="company_id", inplace=True, errors="ignore")

    for c in ["mention_cnt", "sent_sum", "news_cnt", "main_cnt"]:
        if c in prices_df.columns:
            prices_df[c] = prices_df[c].fillna(0)

    # === 4) Rolling aggregations（PIT-safe shift(1)）===
    prices_df = prices_df.sort_values([ticker_col, "_td"])

    if "mention_cnt" in prices_df.columns:
        shifted = prices_df.groupby(ticker_col)["mention_cnt"].shift(1)
        prices_df["event_mention_cnt_1d"] = shifted
        for w in [5, 20]:
            prices_df[f"event_mention_cnt_{w}d"] = (
                shifted.groupby(prices_df[ticker_col])
                .rolling(w, min_periods=1)
                .sum()
                .reset_index(level=0, drop=True)
            )
        # surge：1d / (5d/5)
        mean_5d = prices_df["event_mention_cnt_5d"] / 5
        prices_df["event_mention_surge"] = (
            prices_df["event_mention_cnt_1d"] / mean_5d.replace(0, np.nan)
        )

    if "sent_sum" in prices_df.columns and "mention_cnt" in prices_df.columns:
        # sent_score_5d = 5 日情緒分數總和 / 5 日提及量
        sent_shift = prices_df.groupby(ticker_col)["sent_sum"].shift(1)
        ment_shift = prices_df.groupby(ticker_col)["mention_cnt"].shift(1)
        sent_5d = (
            sent_shift.groupby(prices_df[ticker_col])
            .rolling(5, min_periods=1)
            .sum()
            .reset_index(level=0, drop=True)
        )
        ment_5d = (
            ment_shift.groupby(prices_df[ticker_col])
            .rolling(5, min_periods=1)
            .sum()
            .reset_index(level=0, drop=True)
        )
        prices_df["event_sent_score_5d"] = sent_5d / ment_5d.replace(0, np.nan)

    if "news_cnt" in prices_df.columns and "mention_cnt" in prices_df.columns:
        news_shift = prices_df.groupby(ticker_col)["news_cnt"].shift(1)
        news_5d = (
            news_shift.groupby(prices_df[ticker_col])
            .rolling(5, min_periods=1)
            .sum()
            .reset_index(level=0, drop=True)
        )
        ment_shift = prices_df.groupby(ticker_col)["mention_cnt"].shift(1)
        ment_5d = (
            ment_shift.groupby(prices_df[ticker_col])
            .rolling(5, min_periods=1)
            .sum()
            .reset_index(level=0, drop=True)
        )
        prices_df["event_news_ratio_5d"] = news_5d / ment_5d.replace(0, np.nan)

    if "main_cnt" in prices_df.columns:
        main_shift = prices_df.groupby(ticker_col)["main_cnt"].shift(1)
        ment_shift = prices_df.groupby(ticker_col)["mention_cnt"].shift(1)
        main_5d = (
            main_shift.groupby(prices_df[ticker_col])
            .rolling(5, min_periods=1)
            .sum()
            .reset_index(level=0, drop=True)
        )
        ment_5d = (
            ment_shift.groupby(prices_df[ticker_col])
            .rolling(5, min_periods=1)
            .sum()
            .reset_index(level=0, drop=True)
        )
        prices_df["event_post_main_ratio_5d"] = main_5d / ment_5d.replace(0, np.nan)

    # 清理
    for c in ["mention_cnt", "sent_sum", "news_cnt", "main_cnt", "_td"]:
        if c in prices_df.columns:
            prices_df.drop(columns=c, inplace=True, errors="ignore")

    ev_feats = [c for c in prices_df.columns if c.startswith("event_")]
    logger.info(f"  Event features (phase5a): {len(ev_feats)}")
    return prices_df


# ============================================================
# Helpers
# ============================================================

def _find_col(df: pd.DataFrame, candidates: list) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None
