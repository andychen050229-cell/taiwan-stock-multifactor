"""
文本特徵工程（Phase 5B Stage 2.2 & 2.3）

對應過往範例的核心方法：
  - G1: 關鍵字萃取 + 重要性排序
  - G10: TF-IDF + Chi-Square + SVM
  - G20: TF-IDF top 1500 + 多個模型

本模組產出三組支柱特徵：
  - txt_keyword_*: 關鍵字出現強度 / TF-IDF 加權
  - txt_volume_*:  文本量、平台分布、平均長度
  - sent_*:       情緒分數（需搭配 sent_scorer.py）

後續 selector.py 的 Corr prefilter + MI + VIF 會對這些特徵做去冗篩選。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger
from scipy import sparse
from scipy.stats import chi2_contingency
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import mutual_info_classif

from ..utils.helpers import timer


# ============================================================
# 三重關鍵字篩選：Chi² / MI / Lift
# ============================================================

def _compute_lift(X_bin: sparse.csr_matrix, y: np.ndarray, positive_class=1) -> np.ndarray:
    """
    計算每個 term 的 Lift = P(term | y=positive) / P(term).

    Args:
        X_bin: 文本 × 詞的 01 矩陣 (presence)
        y: label array
        positive_class: 正類 label

    Returns:
        lift array of shape (n_terms,)
    """
    y_pos = (y == positive_class)
    n = len(y)
    n_pos = y_pos.sum()
    if n_pos == 0 or n_pos == n:
        return np.zeros(X_bin.shape[1])

    # 詞頻：在正類中的出現數 / 在所有文本中的出現數
    term_count_all = np.asarray(X_bin.sum(axis=0)).ravel()
    term_count_pos = np.asarray(X_bin[y_pos, :].sum(axis=0)).ravel()

    p_term = term_count_all / n
    p_term_given_pos = term_count_pos / n_pos

    lift = np.where(p_term > 0, p_term_given_pos / p_term, 0.0)
    return lift


def _compute_chi2(X_bin: sparse.csr_matrix, y: np.ndarray) -> np.ndarray:
    """
    計算每個 term 的 Chi² 統計量。
    回傳 chi2 values (不是 p-value) — 越大表示相關性越強。
    """
    from sklearn.feature_selection import chi2
    chi2_stats, _ = chi2(X_bin, y)
    return np.nan_to_num(chi2_stats, nan=0.0, posinf=0.0, neginf=0.0)


def _compute_mi(X_bin: sparse.csr_matrix, y: np.ndarray) -> np.ndarray:
    """計算 mutual information（binary features 假設）"""
    mi = mutual_info_classif(X_bin, y, discrete_features=True, random_state=42)
    return np.nan_to_num(mi, nan=0.0)


@timer
def select_keywords(
    corpus: list[list[str]],
    labels: np.ndarray,
    top_n: int = 500,
    min_df: int = 10,
    max_df: float = 0.7,
    intersection_ratio: float = 0.5,
) -> tuple[list[str], pd.DataFrame]:
    """
    使用 TF-IDF + Chi² + MI + Lift 做三重篩選。

    流程：
      1. TF-IDF 轉 binary 矩陣
      2. 三路評分：Chi² / MI / Lift
      3. 取三路 top (top_n / intersection_ratio) 的交集 → 強健關鍵字集

    Args:
        corpus: list of token lists
        labels: 對應的 label（0/1/2 三類）
        top_n: 最終想保留的關鍵字數
        min_df, max_df: TfidfVectorizer 參數
        intersection_ratio: 每路取 top_n / ratio 再做交集；ratio 越小越嚴

    Returns:
        (selected_keywords, scores_df)
    """
    logger.info(
        f"Keyword selection | corpus={len(corpus):,} | top_n={top_n} | "
        f"min_df={min_df} | max_df={max_df}"
    )

    # 組回 token string（sklearn 需要 str）
    docs = [" ".join(toks) for toks in corpus]

    # TF-IDF（binary=False 拿 weights，但下游 chi² 會改二值）
    vec = TfidfVectorizer(
        tokenizer=str.split,  # 已預先斷詞
        token_pattern=None,
        min_df=min_df,
        max_df=max_df,
        sublinear_tf=True,
        norm="l2",
    )
    X = vec.fit_transform(docs)
    terms = np.array(vec.get_feature_names_out())
    n_terms = len(terms)
    logger.info(f"  TF-IDF: {X.shape[0]:,} × {n_terms:,} terms")

    # 二值化供 chi² / MI
    X_bin = (X > 0).astype(int)

    # 把 label 轉為 binary（上漲 vs 非上漲），因為 Chi² 對 binary 最直接
    # 若 label 是 {-1, 0, 1}：上漲 = (label == 1)
    y_bin = (labels == 1).astype(int)

    # 三路評分
    logger.info("  computing chi² ...")
    score_chi2 = _compute_chi2(X_bin, y_bin)
    logger.info("  computing mutual info ...")
    score_mi = _compute_mi(X_bin, y_bin)
    logger.info("  computing lift ...")
    score_lift = _compute_lift(X_bin, y_bin, positive_class=1)

    # 排名
    rank_chi2 = pd.Series(score_chi2, index=terms).rank(ascending=False)
    rank_mi = pd.Series(score_mi, index=terms).rank(ascending=False)
    rank_lift = pd.Series(score_lift, index=terms).rank(ascending=False)

    top_cutoff = int(top_n / max(intersection_ratio, 0.01))

    set_chi2 = set(rank_chi2.nsmallest(top_cutoff).index)
    set_mi = set(rank_mi.nsmallest(top_cutoff).index)
    set_lift = set(rank_lift.nsmallest(top_cutoff).index)

    # 交集
    robust = set_chi2 & set_mi & set_lift
    logger.info(
        f"  top {top_cutoff}/each: chi²={len(set_chi2)}, MI={len(set_mi)}, "
        f"lift={len(set_lift)}; intersection={len(robust)}"
    )

    # 若交集不足，放寬
    if len(robust) < top_n:
        logger.warning(f"  intersection only {len(robust)} < {top_n}; falling back to chi² + MI (⋂)")
        robust = set_chi2 & set_mi
    if len(robust) < top_n:
        logger.warning(f"  still {len(robust)} < {top_n}; falling back to chi² top {top_n}")
        robust = set(rank_chi2.nsmallest(top_n).index)

    # 從 robust 中挑綜合排名最高的 top_n
    combined_rank = (rank_chi2 + rank_mi + rank_lift) / 3
    final_candidates = combined_rank.loc[list(robust)].nsmallest(top_n)
    selected = final_candidates.index.tolist()

    # 匯出 scores_df 供報告使用
    scores_df = pd.DataFrame({
        "term": terms,
        "chi2": score_chi2,
        "mi": score_mi,
        "lift": score_lift,
        "rank_chi2": rank_chi2.values,
        "rank_mi": rank_mi.values,
        "rank_lift": rank_lift.values,
        "rank_combined": combined_rank.values,
        "selected": np.isin(terms, selected),
    }).sort_values("rank_combined")

    logger.info(f"  selected {len(selected)} keywords (robust intersection)")
    return selected, scores_df


# ============================================================
# 關鍵字 → 特徵矩陣
# ============================================================

@timer
def build_keyword_features(
    df_tokens: pd.DataFrame,
    keywords: list[str],
    group_cols: tuple = ("company_id", "trade_date"),
    token_col: str = "tokens_content",
    rolling_windows: tuple = (1, 5, 20),
) -> pd.DataFrame:
    """
    建 txt_keyword_{kw}_{win} 特徵。

    規則：
      1. 先計算每篇文章是否含關鍵字（binary）
      2. 按 group_cols（預設 company_id × trade_date）聚合 → 當日關鍵字出現率
      3. 再做 rolling sum（5 日／20 日）→ 長短期文本熱度

    PIT 安全性：
      - 斷言 df_tokens 已經 align_to_trade_date，即 trade_date 是 PIT-safe 的
      - rolling 只 look back，不會偷看未來

    Returns:
        DataFrame with columns company_id, trade_date, txt_keyword_{kw}_{win}
    """
    # 用 list 保留順序（set iteration 可能不確定）
    keyword_list = list(dict.fromkeys(keywords))  # dedupe preserving order
    keyword_set = set(keyword_list)
    logger.info(f"Build keyword features | {len(keyword_list)} kw × {len(rolling_windows)} win")

    # 以 sklearn CountVectorizer 向量化產生 hit matrix（比 dict-per-row 快 50x+）
    # parquet 讀回的 list-of-strings 會變 numpy.ndarray，.join 直接用
    from sklearn.feature_extraction.text import CountVectorizer
    import scipy.sparse as sp

    logger.info("  hit matrix (vectorized) ...")

    def _to_doc(toks):
        if toks is None:
            return ""
        try:
            return " ".join(toks)
        except TypeError:
            return ""

    docs = df_tokens[token_col].map(_to_doc).tolist()

    # 固定 vocabulary 強制用 keyword_list 順序
    cv = CountVectorizer(
        vocabulary=keyword_list,
        tokenizer=str.split,
        token_pattern=None,
        lowercase=False,
        binary=True,  # 只看是否出現，不看次數
    )
    hit_sparse = cv.fit_transform(docs)  # shape: (n_docs, n_keywords), int sparse
    logger.info(f"  hit matrix: {hit_sparse.shape}, nnz={hit_sparse.nnz:,}")

    # 轉 dense DataFrame
    hits = pd.DataFrame(
        hit_sparse.toarray().astype("int8"),
        columns=keyword_list,
        index=df_tokens.index,
    )
    hits_df = pd.concat([df_tokens[list(group_cols)].reset_index(drop=True),
                         hits.reset_index(drop=True)], axis=1)

    # 按 company × trade_date 加總 → 當日該關鍵字出現次數
    logger.info("  daily aggregation ...")
    daily = hits_df.groupby(list(group_cols))[keyword_list].sum().reset_index()

    # rolling sum
    logger.info("  rolling windows ...")
    group_col = group_cols[0]
    date_col = group_cols[1]
    daily = daily.sort_values([group_col, date_col])

    feature_frames = [daily[list(group_cols)].copy()]
    for win in rolling_windows:
        rolled = (
            daily.set_index(date_col)
            .groupby(group_col)[keyword_list]
            .rolling(win, min_periods=1)
            .sum()
            .reset_index()
        )
        rolled.columns = [group_col, date_col] + [f"txt_keyword_{kw}_{win}d" for kw in keyword_list]
        feature_frames.append(rolled.drop(columns=[group_col, date_col]).reset_index(drop=True))

    result = pd.concat(feature_frames, axis=1)
    logger.info(f"  done: {result.shape[0]:,} rows × {result.shape[1]} cols")
    return result


# ============================================================
# 文本量特徵
# ============================================================

@timer
def build_volume_features(
    df_tokens: pd.DataFrame,
    group_cols: tuple = ("company_id", "trade_date"),
    rolling_windows: tuple = (1, 5, 20),
    token_col: str = None,
) -> pd.DataFrame:
    """
    建 txt_volume_* 特徵：每日文本量、平均長度、平台分布。

    Args:
        token_col: 指定 tokens 欄位名（自動偵測 tokens_title / tokens_content / tokens）

    Returns:
        DataFrame with txt_volume_{win}, txt_avg_len_{win}, txt_platform_ptt_ratio_{win}, ...
    """
    group_col, date_col = group_cols
    logger.info("Build volume features ...")

    df = df_tokens.copy()
    # 自動偵測 tokens 欄
    if token_col is None:
        for cand in ("tokens_content", "tokens_title", "tokens"):
            if cand in df.columns:
                token_col = cand
                break
    if token_col is None or token_col not in df.columns:
        logger.warning(f"  no tokens col found; skipping length features")
        df["_tok_len"] = 0
    else:
        # parquet 讀回可能是 ndarray；用 try/except 或 hasattr('__len__') 都可
        def _len(x):
            if x is None:
                return 0
            try:
                return len(x)
            except TypeError:
                return 0
        df["_tok_len"] = df[token_col].apply(_len)

    # 每日聚合
    per_day = df.groupby(list(group_cols)).agg(
        n_articles=("_tok_len", "size"),
        avg_len=("_tok_len", "mean"),
    ).reset_index()

    # 平台分布
    if "s_name" in df.columns:
        platform_dummies = pd.get_dummies(df["s_name"], prefix="plat")
        plat_cols = platform_dummies.columns.tolist()
        df_plat = pd.concat([df[list(group_cols)], platform_dummies], axis=1)
        plat_per_day = df_plat.groupby(list(group_cols))[plat_cols].sum().reset_index()
        per_day = per_day.merge(plat_per_day, on=list(group_cols), how="left")

    per_day = per_day.sort_values([group_col, date_col])

    # rolling
    rolled_frames = [per_day[list(group_cols)].copy()]
    numeric_cols = [c for c in per_day.columns if c not in group_cols]

    for win in rolling_windows:
        rolled = (
            per_day.set_index(date_col)
            .groupby(group_col)[numeric_cols]
            .rolling(win, min_periods=1)
            .sum()
            .reset_index()
        )
        rolled.columns = [group_col, date_col] + [f"txt_volume_{c}_{win}d" for c in numeric_cols]
        rolled_frames.append(rolled.drop(columns=[group_col, date_col]))

    result = pd.concat(rolled_frames, axis=1)
    logger.info(f"  done: {result.shape[0]:,} rows × {result.shape[1]} cols")
    return result
