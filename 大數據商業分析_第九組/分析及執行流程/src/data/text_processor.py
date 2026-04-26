"""
文本資料前處理模組

處理流程（§3.4 四層文本過濾）：
  Layer 1: content_type 推斷（新聞/社群/公告/研究報告）
  Layer 2: 長度與語言過濾（過短/非中文）
  Layer 3: MinHash LSH 去重（Jaccard > 0.8 視為重複）
  Layer 4: 基本清洗（移除 HTML tags、特殊符號等）
"""
import re
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger
from ..utils.helpers import timer


# ============================================================
# Layer 1: Content Type 推斷
# ============================================================

# 各類型的關鍵字特徵
_CONTENT_PATTERNS = {
    "news": {
        "keywords": ["記者", "報導", "據了解", "本報訊", "中央社", "路透", "外電"],
        "min_length": 50,
    },
    "social": {
        "keywords": ["PTT", "Dcard", "版友", "大大", "請益", "幫QQ", "懶人包", "心得"],
        "min_length": 10,
    },
    "announcement": {
        "keywords": ["公告", "董事會", "股東會", "決議", "重大訊息", "證交所"],
        "min_length": 30,
    },
    "research": {
        "keywords": ["目標價", "投資評等", "研究報告", "買進", "持有", "賣出", "合理價"],
        "min_length": 100,
    },
}


def infer_content_type(text: str) -> str:
    """
    推斷文本類型。

    Args:
        text: 文本內容

    Returns:
        content_type: "news" / "social" / "announcement" / "research" / "unknown"
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        return "unknown"

    scores = {}
    for ctype, pattern in _CONTENT_PATTERNS.items():
        score = sum(1 for kw in pattern["keywords"] if kw in text)
        if len(text) >= pattern["min_length"]:
            score += 0.5  # 長度加分
        scores[ctype] = score

    best_type = max(scores, key=scores.get)
    return best_type if scores[best_type] > 0 else "unknown"


@timer
def add_content_type(df: pd.DataFrame, text_col: str = None) -> pd.DataFrame:
    """
    為文本資料新增 content_type 欄位。

    Args:
        df: stock_text DataFrame
        text_col: 文本欄位名稱（自動偵測）
    """
    # 若已有 content_type 欄位且非全空（如 stock_text_lite），直接統計
    if "content_type" in df.columns and df["content_type"].notna().any():
        type_counts = df["content_type"].value_counts()
        logger.info("Content type (existing column) distribution:")
        for ctype, count in type_counts.items():
            logger.info(f"  {ctype}: {count:,} ({count/len(df)*100:.1f}%)")
        return df

    if text_col is None:
        text_col = _find_text_col(df)

    if text_col is None:
        logger.error("Cannot find text column")
        return df

    df["content_type"] = df[text_col].apply(infer_content_type)

    type_counts = df["content_type"].value_counts()
    logger.info("Content type distribution:")
    for ctype, count in type_counts.items():
        logger.info(f"  {ctype}: {count:,} ({count/len(df)*100:.1f}%)")

    return df


# ============================================================
# Layer 2: 長度與語言過濾
# ============================================================

@timer
def filter_by_length(df: pd.DataFrame, config: dict, text_col: str = None) -> pd.DataFrame:
    """
    過濾過短的文本。

    Args:
        df: stock_text DataFrame
        config: 設定字典
        text_col: 文本欄位名稱

    Returns:
        過濾後的 DataFrame
    """
    min_length = config.get("preprocessing", {}).get("text", {}).get("min_length", 10)

    if text_col is None:
        text_col = _find_text_col(df)

    if text_col is None:
        logger.warning("Cannot find text column for length filtering")
        return df

    original_count = len(df)

    # 過濾空值和過短文本
    mask = df[text_col].notna() & (df[text_col].str.len() >= min_length)
    df_filtered = df[mask].copy()

    removed = original_count - len(df_filtered)
    logger.info(f"Length filter: {original_count:,} → {len(df_filtered):,} (removed {removed:,}, min_length={min_length})")

    return df_filtered


def _is_chinese_dominant(text: str, threshold: float = 0.3) -> bool:
    """判斷文本是否以中文為主（中文字元佔比 > threshold）"""
    if not isinstance(text, str) or len(text) == 0:
        return False

    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    return chinese_chars / len(text) > threshold


@timer
def filter_by_language(df: pd.DataFrame, text_col: str = None, threshold: float = 0.3) -> pd.DataFrame:
    """過濾非中文為主的文本"""
    if text_col is None:
        text_col = _find_text_col(df)

    if text_col is None:
        return df

    original_count = len(df)
    mask = df[text_col].apply(lambda x: _is_chinese_dominant(x, threshold))
    df_filtered = df[mask].copy()

    removed = original_count - len(df_filtered)
    logger.info(f"Language filter: {original_count:,} → {len(df_filtered):,} (removed {removed:,} non-Chinese)")

    return df_filtered


# ============================================================
# Layer 3: MinHash LSH 去重
# ============================================================

@timer
def deduplicate_minhash(
    df: pd.DataFrame,
    config: dict,
    text_col: str = None,
) -> pd.DataFrame:
    """
    MinHash LSH 近似去重。

    使用 datasketch 的 MinHash + LSH 找出 Jaccard 相似度 > threshold 的文本對，
    每組重複只保留最早的一篇。

    Args:
        df: stock_text DataFrame
        config: 設定字典
        text_col: 文本欄位名稱

    Returns:
        去重後的 DataFrame
    """
    try:
        from datasketch import MinHash, MinHashLSH
    except ImportError:
        logger.warning("datasketch not installed. Skipping MinHash deduplication.")
        logger.warning("Install with: pip install datasketch")
        return df

    text_cfg = config.get("preprocessing", {}).get("text", {})
    num_perm = text_cfg.get("minhash_num_perm", 128)
    threshold = text_cfg.get("minhash_threshold", 0.8)
    max_dup_rate = text_cfg.get("max_duplicate_rate", 0.30)

    if text_col is None:
        text_col = _find_text_col(df)

    if text_col is None:
        return df

    # 偵測日期欄位（用於保留最早的文本）
    date_col = _find_col(df, ["date", "日期", "publish_date", "created_at", "post_date"])

    logger.info(f"MinHash LSH dedup: num_perm={num_perm}, threshold={threshold}")

    original_count = len(df)

    # 短文本（如只有 title，avg < 50 chars）用精確去重更快更有效
    avg_len = df[text_col].dropna().str.len().mean()
    if avg_len < 50:
        logger.info(f"  Avg text length ({avg_len:.0f}) < 50 chars → using exact dedup instead of MinHash")
        before = len(df)

        # 偵測股票標識欄位
        stock_col = _find_col(df, ["s_name", "stock_id", "company_id", "ticker", "symbol", "代號"])

        # 決定去重欄位：如果有股票欄位，則用 text_col + stock_col；否則只用 text_col
        if stock_col:
            dedup_cols = [text_col, stock_col]
            logger.info(f"  Detected stock column '{stock_col}' → dedup by [{text_col}, {stock_col}]")
        else:
            dedup_cols = [text_col]
            logger.info(f"  No stock column detected → dedup by [{text_col}] only")

        df = df.drop_duplicates(subset=dedup_cols, keep="first")
        removed = before - len(df)
        dup_rate = removed / before if before > 0 else 0
        logger.info(f"Exact dedup: {before:,} → {len(df):,} (removed {removed:,}, rate={dup_rate:.1%})")
        if dup_rate > max_dup_rate:
            logger.warning(f"  Duplicate rate {dup_rate:.1%} exceeds max threshold {max_dup_rate:.0%}")
        return df

    # ── 大型語料安全閘（2026-04-19 新增）────────────────────────
    # 過往曾在 1.12M rows × avg 500 chars × num_perm=128 掛死電腦。
    # 若資料量超過 50 萬筆且平均長度 > 50，改用 exact dedup（title+平台）
    # 避免 O(n × num_perm × text_len) 單執行緒爆炸。
    if len(df) > 500_000 and avg_len > 50:
        logger.warning(
            f"  Large corpus ({len(df):,} rows × avg {avg_len:.0f} chars) — "
            f"falling back to exact dedup to avoid MinHash O(n × num_perm × L) bottleneck"
        )
        before = len(df)
        stock_col = _find_col(df, ["s_name", "stock_id", "company_id", "ticker", "symbol", "代號"])
        dedup_cols = [text_col, stock_col] if stock_col else [text_col]
        df = df.drop_duplicates(subset=dedup_cols, keep="first")
        removed = before - len(df)
        dup_rate = removed / before if before > 0 else 0
        logger.info(f"Exact dedup (large-corpus safe path): {before:,} → {len(df):,} (removed {removed:,}, rate={dup_rate:.1%})")
        if dup_rate > max_dup_rate:
            logger.warning(f"  Duplicate rate {dup_rate:.1%} exceeds max threshold {max_dup_rate:.0%}")
        return df

    # 建立 MinHash
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    minhashes = {}
    duplicates = set()

    for idx, text in df[text_col].items():
        if not isinstance(text, str) or len(text.strip()) == 0:
            continue

        # 建立 MinHash（以字元 n-gram 為 shingle）
        m = MinHash(num_perm=num_perm)
        # 使用 3-gram
        text_clean = text.strip()
        for i in range(max(len(text_clean) - 2, 1)):
            shingle = text_clean[i:i+3]
            m.update(shingle.encode("utf-8"))

        # 查詢是否有相似的已存在文本
        result = lsh.query(m)
        if result:
            duplicates.add(idx)
        else:
            try:
                lsh.insert(str(idx), m)
                minhashes[idx] = m
            except ValueError:
                # key 已存在
                pass

    # 移除重複
    df_deduped = df[~df.index.isin(duplicates)].copy()

    dup_count = len(duplicates)
    dup_rate = dup_count / original_count if original_count > 0 else 0

    logger.info(f"MinHash dedup: {original_count:,} → {len(df_deduped):,} (removed {dup_count:,}, rate={dup_rate:.1%})")

    if dup_rate > max_dup_rate:
        logger.warning(f"  Duplicate rate {dup_rate:.1%} exceeds max threshold {max_dup_rate:.0%}")

    return df_deduped


# ============================================================
# Layer 4: 基本清洗
# ============================================================

@timer
def clean_text(df: pd.DataFrame, text_col: str = None) -> pd.DataFrame:
    """
    基本文本清洗。

    - 移除 HTML tags
    - 移除 URL
    - 移除多餘空白
    - 統一全半形
    """
    if text_col is None:
        text_col = _find_text_col(df)

    if text_col is None:
        return df

    original_avg_len = df[text_col].dropna().str.len().mean()

    df[text_col] = df[text_col].apply(_clean_single_text)

    new_avg_len = df[text_col].dropna().str.len().mean()
    logger.info(f"Text cleaning: avg length {original_avg_len:.0f} → {new_avg_len:.0f} chars")

    return df


def _clean_single_text(text: str) -> str:
    """清洗單筆文本"""
    if not isinstance(text, str):
        return text

    # 移除 HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # 移除 URL
    text = re.sub(r'https?://\S+', '', text)

    # 移除多餘空白
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# ============================================================
# 完整管線
# ============================================================

@timer
def run_text_pipeline(df: pd.DataFrame, config: dict, text_col: str = None) -> pd.DataFrame:
    """
    執行完整四層文本前處理管線。

    Args:
        df: stock_text DataFrame
        config: 設定字典
        text_col: 文本欄位名稱

    Returns:
        處理後的 DataFrame
    """
    original = len(df)
    logger.info(f"{'='*50}")
    logger.info(f"Text preprocessing pipeline: {original:,} records")
    logger.info(f"{'='*50}")

    if text_col is None:
        text_col = _find_text_col(df)

    # Layer 1: Content type
    df = add_content_type(df, text_col)

    # Layer 2: Length & language filter
    df = filter_by_length(df, config, text_col)
    df = filter_by_language(df, text_col)

    # Layer 3: MinHash dedup
    df = deduplicate_minhash(df, config, text_col)

    # Layer 4: Clean text
    df = clean_text(df, text_col)

    final = len(df)
    logger.info(f"{'='*50}")
    logger.info(f"Pipeline complete: {original:,} → {final:,} ({final/original*100:.1f}% retained)")
    logger.info(f"{'='*50}")

    return df


# ============================================================
# 輔助函式
# ============================================================

def _find_text_col(df: pd.DataFrame) -> Optional[str]:
    """自動偵測文本欄位"""
    candidates = ["text", "content", "body", "title", "內容", "文本", "article"]
    for c in candidates:
        if c in df.columns:
            return c
    # 找最長的字串欄位
    str_cols = df.select_dtypes(include=["object", "string"]).columns
    if len(str_cols) > 0:
        avg_lens = {c: df[c].dropna().str.len().mean() for c in str_cols}
        return max(avg_lens, key=avg_lens.get)
    return None


def _find_col(df: pd.DataFrame, candidates: list) -> Optional[str]:
    """從候選欄位名中找出存在於 DataFrame 的第一個"""
    for c in candidates:
        if c in df.columns:
            return c
    return None
