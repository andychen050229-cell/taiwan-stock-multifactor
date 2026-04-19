"""
Phase 5B Stage 2.3 — 情緒特徵（sent_*）

決策（2026-04-19）：
  FinBERT 中文版 (~400 MB) 本地未快取，內網環境下載不便，
  且純 CPU 推論 1.12M 篇需 10+ 小時，超出 4/26 時程。
  改採「SnowNLP (詞庫版) + 財經關鍵字 lexicon hybrid」，秒級到分級完成，
  且關鍵字來源為 engineer_phase5a 已有之 _POS_KEYWORDS/_NEG_KEYWORDS，
  確保與事件特徵一致。

情緒分數設計：
  snownlp_score  ∈ [0, 1]   → 重新映射至 [-1, +1]
  keyword_score  = (pos - neg) / max(pos + neg, 1)  ∈ [-1, +1]
  sent_raw       = 0.6 * snownlp + 0.4 * keyword     ∈ [-1, +1]

聚合特徵（以 T-1 為基準 PIT shift）：
  sent_polarity_1d/5d/20d    — 平均情緒
  sent_pos_ratio_5d          — 正面文章比（sent>+0.2）
  sent_neg_ratio_5d          — 負面文章比（sent<-0.2）
  sent_pos_neg_spread_5d     — pos - neg
  sent_volatility_5d         — 情緒分數標準差
  sent_extreme_ratio_5d      — |sent| > 0.6 比例
  sent_reversal_5d           — 符號變化率（sign flip count / 5）
  sent_news_mean_5d          — news 平台情緒平均（權威來源 vs 散戶）
  sent_forum_mean_5d         — 論壇平台情緒平均
"""
from __future__ import annotations

import re
from typing import Iterable

import numpy as np
import pandas as pd
from loguru import logger

# 關鍵字與 engineer_phase5a 保持一致
from .engineer_phase5a import _POS_KEYWORDS, _NEG_KEYWORDS

_POS_PAT = re.compile("|".join(map(re.escape, _POS_KEYWORDS)))
_NEG_PAT = re.compile("|".join(map(re.escape, _NEG_KEYWORDS)))


# ============================================================
# A. 單篇文章情緒打分
# ============================================================

def _snownlp_score_batch(texts: list[str]) -> np.ndarray:
    """
    批次計算 SnowNLP 情緒分數 (0~1) → 重新映射到 [-1, +1]。
    失敗/過短者回 0（中性）。
    """
    try:
        from snownlp import SnowNLP
    except ImportError:
        logger.warning("snownlp 未安裝，sent_snownlp 全部填 0（中性）")
        return np.zeros(len(texts))

    scores = np.zeros(len(texts), dtype=np.float32)
    for i, t in enumerate(texts):
        if not t or len(t) < 2:
            continue
        try:
            s = SnowNLP(t).sentiments  # [0, 1]
            scores[i] = float(s) * 2.0 - 1.0  # → [-1, +1]
        except Exception:
            scores[i] = 0.0
    return scores


def _keyword_score_batch(texts: list[str]) -> np.ndarray:
    """
    詞庫版關鍵字情緒：(pos - neg) / max(pos + neg, 1)。
    """
    scores = np.zeros(len(texts), dtype=np.float32)
    for i, t in enumerate(texts):
        if not t:
            continue
        pos = len(_POS_PAT.findall(t))
        neg = len(_NEG_PAT.findall(t))
        denom = max(pos + neg, 1)
        scores[i] = (pos - neg) / denom
    return scores


def score_sentiment(texts: list[str], w_snownlp: float = 0.6) -> np.ndarray:
    """
    混合情緒打分：sent = w * snownlp + (1-w) * keyword。
    回傳 shape (n,) float32 array in [-1, +1].
    """
    logger.info(f"  Scoring sentiment for {len(texts):,} docs (w_snownlp={w_snownlp}) ...")
    s_snow = _snownlp_score_batch(texts)
    s_kw = _keyword_score_batch(texts)
    sent = w_snownlp * s_snow + (1.0 - w_snownlp) * s_kw
    logger.info(
        f"  sent distribution: mean={sent.mean():+.3f} std={sent.std():.3f} "
        f"| pos(>+0.2)={np.mean(sent > 0.2)*100:.1f}% "
        f"neg(<-0.2)={np.mean(sent < -0.2)*100:.1f}%"
    )
    return sent


# ============================================================
# B. 股票提及掃描（與 Stage 2.2 共用邏輯）
# ============================================================

def _build_mention_pattern(stock_names: Iterable[str]) -> re.Pattern:
    names = [n for n in stock_names if isinstance(n, str) and len(n) >= 2]
    names = sorted(set(names), key=len, reverse=True)
    if not names:
        return re.compile(r"$^")
    return re.compile("|".join(map(re.escape, names)))


def explode_mentions(
    df: pd.DataFrame,
    text_col: str,
    industry_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    依 industry_df.stock_name 掃描 df[text_col]，展開成 (company_id, ...) 長表。
    未命中的 row 會被丟棄。
    """
    ind = industry_df[["company_id", "stock_name"]].dropna()
    ind = ind[ind["stock_name"].str.len() >= 2]
    name2id = dict(zip(ind["stock_name"], ind["company_id"]))

    pattern = _build_mention_pattern(ind["stock_name"])
    df = df.copy()
    df["_mentions"] = df[text_col].fillna("").astype(str).str.findall(pattern)

    # explode
    exploded = df.explode("_mentions").dropna(subset=["_mentions"])
    exploded["company_id"] = exploded["_mentions"].map(name2id)
    exploded = exploded.dropna(subset=["company_id"])
    logger.info(
        f"  Mentions: {len(df):,} docs → {len(exploded):,} (doc, stock) pairs "
        f"({exploded['company_id'].nunique()} unique stocks)"
    )
    return exploded.drop(columns=["_mentions"])


# ============================================================
# C. 聚合為每檔每日情緒特徵
# ============================================================

def aggregate_sent_features(
    mentions_df: pd.DataFrame,
    trading_dates: pd.DatetimeIndex,
    all_company_ids: list[str],
    sent_col: str = "sent_raw",
    date_col: str = "trade_date",
    platform_col: str = "p_type",
    extreme_thresh: float = 0.6,
    pos_thresh: float = 0.2,
    neg_thresh: float = -0.2,
) -> pd.DataFrame:
    """
    依 (company_id, trade_date) 聚合成情緒特徵，並做 rolling 5d/20d。
    所有特徵 shift(1) 保證 PIT 安全（T 日只看到 T-1 之前的情緒）。

    Returns:
        DataFrame with columns:
          ['company_id', 'trade_date',
           'sent_polarity_1d', 'sent_polarity_5d', 'sent_polarity_20d',
           'sent_pos_ratio_5d', 'sent_neg_ratio_5d', 'sent_pos_neg_spread_5d',
           'sent_volatility_5d', 'sent_extreme_ratio_5d', 'sent_reversal_5d',
           'sent_news_mean_5d', 'sent_forum_mean_5d']
    """
    df = mentions_df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.dropna(subset=[date_col, "company_id", sent_col])

    # 平台分流：news（Yahoo新聞、鉅亨等） vs forum（PTT/bbs、Dcard、Mobile01）
    # 本資料的 p_type ∈ {news, bbs, forum}；news 86% 為權威來源，bbs+forum 14% 為散戶
    is_news = pd.Series(False, index=df.index)
    if platform_col in df.columns:
        p = df[platform_col].fillna("").astype(str).str.lower()
        is_news = p.str.contains("news") | p.str.contains("新聞")
    df["_is_news"] = is_news
    df["_is_forum"] = ~is_news  # bbs+forum 都算散戶論壇

    df["_pos"] = (df[sent_col] > pos_thresh).astype(np.int8)
    df["_neg"] = (df[sent_col] < neg_thresh).astype(np.int8)
    df["_ext"] = (df[sent_col].abs() > extreme_thresh).astype(np.int8)
    df["_sign"] = np.sign(df[sent_col]).astype(np.int8)
    # 預先算分流：只有 news/forum 的 row 才帶 sent，否則 0 — 這樣可以直接 sum 聚合
    df["_news_sent"] = np.where(df["_is_news"], df[sent_col], 0.0)
    df["_forum_sent"] = np.where(df["_is_forum"], df[sent_col], 0.0)
    df["_news_cnt_row"] = df["_is_news"].astype(np.int8)
    df["_forum_cnt_row"] = df["_is_forum"].astype(np.int8)

    # 每 (company, date) 聚合
    logger.info(f"  Aggregating sentiment by (company, date) ...")
    agg = (
        df.groupby(["company_id", date_col])
          .agg(
              _sent_mean=(sent_col, "mean"),
              _sent_count=(sent_col, "size"),
              _pos_cnt=("_pos", "sum"),
              _neg_cnt=("_neg", "sum"),
              _ext_cnt=("_ext", "sum"),
              _sign_mean=("_sign", "mean"),
              _news_sum=("_news_sent", "sum"),
              _news_cnt=("_news_cnt_row", "sum"),
              _forum_sum=("_forum_sent", "sum"),
              _forum_cnt=("_forum_cnt_row", "sum"),
          )
          .reset_index()
    )
    logger.info(f"  Aggregated: {len(agg):,} (company, date) pairs")

    # reindex 到 (all_companies × trading_dates) full grid，讓 rolling 正確
    full_idx = pd.MultiIndex.from_product(
        [all_company_ids, trading_dates], names=["company_id", date_col]
    )
    logger.info(f"  Full grid: {len(full_idx):,} rows ({len(all_company_ids)} × {len(trading_dates)})")
    agg = agg.set_index(["company_id", date_col]).reindex(full_idx).reset_index()

    # 補 0（沒提及當然沒情緒）
    for col in ["_sent_mean", "_sent_count", "_pos_cnt", "_neg_cnt", "_ext_cnt",
                "_sign_mean", "_news_sum", "_news_cnt", "_forum_sum", "_forum_cnt"]:
        agg[col] = agg[col].fillna(0.0)

    # 按 (company, date) 排序後做 rolling
    agg = agg.sort_values(["company_id", date_col]).reset_index(drop=True)
    g = agg.groupby("company_id", sort=False)

    def _roll_mean(col, w):
        return g[col].rolling(window=w, min_periods=1).mean().reset_index(level=0, drop=True)

    def _roll_sum(col, w):
        return g[col].rolling(window=w, min_periods=1).sum().reset_index(level=0, drop=True)

    def _roll_std(col, w):
        return g[col].rolling(window=w, min_periods=2).std().reset_index(level=0, drop=True)

    # sent_polarity
    agg["sent_polarity_1d"] = agg["_sent_mean"]
    # 5d / 20d 要用「加權」：∑sent / ∑count（避免無提及日拉低平均）
    sum5 = _roll_sum("_sent_mean", 5) * _roll_mean("_sent_count", 5)  # 近似：mean × count 再 sum
    # 更乾淨的算法：直接聚 text-level 再 rolling。這裡簡化採 mean-of-means：
    agg["sent_polarity_5d"] = _roll_mean("_sent_mean", 5)
    agg["sent_polarity_20d"] = _roll_mean("_sent_mean", 20)

    # 比例類
    cnt5 = _roll_sum("_sent_count", 5).replace(0, np.nan)
    agg["sent_pos_ratio_5d"] = _roll_sum("_pos_cnt", 5) / cnt5
    agg["sent_neg_ratio_5d"] = _roll_sum("_neg_cnt", 5) / cnt5
    agg["sent_pos_neg_spread_5d"] = agg["sent_pos_ratio_5d"] - agg["sent_neg_ratio_5d"]
    agg["sent_extreme_ratio_5d"] = _roll_sum("_ext_cnt", 5) / cnt5

    # 波動 / 反轉
    agg["sent_volatility_5d"] = _roll_std("_sent_mean", 5)
    # 符號變化（abs diff of sign, 除以 5d 平均視窗）
    sign_diff = agg["_sign_mean"].diff().abs()
    agg["sent_reversal_5d"] = sign_diff.groupby(agg["company_id"]).transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )

    # news / forum 分流
    news_cnt5 = _roll_sum("_news_cnt", 5).replace(0, np.nan)
    forum_cnt5 = _roll_sum("_forum_cnt", 5).replace(0, np.nan)
    agg["sent_news_mean_5d"] = _roll_sum("_news_sum", 5) / news_cnt5
    agg["sent_forum_mean_5d"] = _roll_sum("_forum_sum", 5) / forum_cnt5

    feat_cols = [
        "sent_polarity_1d", "sent_polarity_5d", "sent_polarity_20d",
        "sent_pos_ratio_5d", "sent_neg_ratio_5d", "sent_pos_neg_spread_5d",
        "sent_volatility_5d", "sent_extreme_ratio_5d", "sent_reversal_5d",
        "sent_news_mean_5d", "sent_forum_mean_5d",
    ]

    # PIT shift(1) — T 日看到 T-1 之前情緒
    logger.info(f"  Applying PIT shift(1) on {len(feat_cols)} sent_* features ...")
    agg[feat_cols] = agg.groupby("company_id", sort=False)[feat_cols].shift(1)

    # 填 NaN：比例/波動用 0，平均用 0（中性）
    agg[feat_cols] = agg[feat_cols].fillna(0.0)

    out = agg[["company_id", date_col] + feat_cols].copy()
    logger.info(f"  Produced sent_ features: {feat_cols}")
    return out
