"""
中文斷詞與 PIT 對齊模組（Phase 5B Stage 2.1）

擴充 text_processor.py 的 Layer 1-4 管線，新增：
  Layer 5: jieba 斷詞 + 停用詞移除 + 金融詞典
  Layer 6: PIT 對齊（post_time → trade_date，D 日僅可用 D-1 08:00 之前文章）

使用方式：
    from src.data.text_tokenizer import run_tokenize_pipeline
    df_tokens = run_tokenize_pipeline(df_cleaned, config)
    df_pit = align_to_trade_date(df_tokens, trading_calendar, cutoff_hour=8)
"""
from __future__ import annotations

import re
from datetime import time
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
from loguru import logger

from ..utils.helpers import timer


# ============================================================
# 停用詞管理（內建台灣財經語境）
# ============================================================

# 最小停用詞集（財經/論壇/新聞常見虛詞）。可以在外部擴充。
_DEFAULT_STOPWORDS = set("""
的 了 是 在 和 有 就 不 也 都 及 與 或 並 而 還 把 被 比 讓 跟 對 所 從 到 由 於 以 為 更 很 再 又 只
這 那 其 此 本 該 他 她 它 我 你 妳 您 我們 你們 妳們 您們 他們 她們 它們 之 於 了 吧 呢 喔 啊
啥 甚 怎 啥 哦 哇 啦 嘛 啦啦 呵呵 哈哈 哈哈哈 呵 哈哈哈哈 ㄏㄏ XD XDD XDDD orz ORZ QQ lol LOL
請問 想請教 請益 大家 各位 各位大大 板友 版友 推文 回文 原文 回覆 如題 感謝 謝謝 先謝 謝謝您 謝 感恩
如下 以下 以上 如上 如題 圖1 圖2 文1 文2 Fig Figure Table 標題 內文 來源 出處 新聞 報導 記者
今天 昨天 明天 上週 下週 上個月 下個月 今年 明年 去年 早上 晚上 中午 下午 凌晨 剛剛 剛才 最近 最近 目前 現在 之前 之後
一 二 三 四 五 六 七 八 九 十 兩 百 千 萬 億 元 塊 塊錢 台幣 新台幣 NT NT$ NTD $ % 一些 一點 一下
哪 哪裡 哪些 哪個 多少 怎樣 如何 為何 為什麼 怎麼 怎麼樣 什麼 這樣 那樣
可以 不行 不能 能 會 不會 應該 可能 也許 大概 大約 好像 似乎 確實 當然 當然是
然後 因此 所以 但是 可是 不過 然而 然而後 另外 此外 接著 再來 總之 總而言之 換句話說
比如 例如 譬如 好比 就像 像是 如同
要 不要 需要 想 想要 覺得 認為 以為 發現 看到 聽到 想到 知道 了解 理解 明白
等 等等 什麼的 之類 之類的 諸如此類
""".split())


def _load_financial_lexicon() -> list[str]:
    """
    載入金融領域詞典。
    目前內建；未來可改從外部檔案載入以支援擴充。

    詞典涵蓋：台股公司簡稱、技術指標、基本面詞、財報科目、市場術語。
    """
    return [
        # 市場術語
        "大盤", "權值股", "指數", "成交量", "成交金額", "漲停", "跌停", "漲停板", "跌停板",
        "除權息", "除權", "除息", "填權", "填息", "貼權", "貼息", "現金股利", "股票股利",
        "法人", "外資", "投信", "自營商", "買超", "賣超", "淨買超", "淨賣超",
        "融資", "融券", "資券", "融資餘額", "融券餘額", "融資使用率", "券資比",
        # 技術面
        "K線", "週K", "月K", "日K", "均線", "月線", "季線", "年線", "MACD", "RSI", "KD",
        "布林通道", "黃金交叉", "死亡交叉", "多頭", "空頭", "多頭排列", "空頭排列",
        "壓力位", "支撐位", "突破", "跌破", "回測", "回踩", "頸線",
        # 基本面
        "毛利", "毛利率", "營益率", "淨利率", "EPS", "ROE", "ROA", "本益比", "股價淨值比",
        "殖利率", "配息", "配股", "股利政策",
        # 熱門產業／族群關鍵字
        "半導體", "晶圓代工", "封測", "IC設計", "記憶體", "矽晶圓",
        "AI", "AI晶片", "人工智慧", "伺服器", "高速傳輸", "PCB", "散熱", "重電",
        "電動車", "EV", "儲能", "再生能源", "綠能", "風電", "光電", "太陽能",
        "金融股", "銀行股", "壽險", "產險", "金控",
        "航運", "貨櫃", "散裝", "紅海", "運價",
        "生技", "疫苗", "新藥", "醫材",
        "元宇宙", "加密貨幣", "區塊鏈", "比特幣",
    ]


# ============================================================
# jieba 斷詞器（延遲初始化，多進程友善）
# ============================================================

_JIEBA_INITIALIZED = False


def _init_jieba(financial_lexicon: Optional[list[str]] = None) -> None:
    """初始化 jieba：載入繁體模式與金融詞典。多進程安全。"""
    global _JIEBA_INITIALIZED
    if _JIEBA_INITIALIZED:
        return

    import jieba

    # 繁中模式（若有 paddle 模型可切換，這裡保守用內建）
    jieba.initialize()

    # 金融詞典
    lex = financial_lexicon or _load_financial_lexicon()
    for word in lex:
        jieba.add_word(word, freq=1000, tag="n")

    _JIEBA_INITIALIZED = True


def _tokenize_single(text: str, stopwords: frozenset[str]) -> list[str]:
    """斷詞單一文本。移除停用詞、純數字、單字（除非是金融詞）。"""
    if not isinstance(text, str) or len(text.strip()) == 0:
        return []

    import jieba

    tokens = jieba.lcut(text, cut_all=False, HMM=True)

    # 過濾規則
    filtered = []
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if tok in stopwords:
            continue
        if len(tok) == 1 and not re.search(r'[\u4e00-\u9fff]', tok):
            continue  # 單一非中文字元略過
        if re.fullmatch(r'\d+(\.\d+)?', tok):
            continue  # 純數字略過
        if re.fullmatch(r'[^\w\u4e00-\u9fff]+', tok):
            continue  # 純符號略過
        filtered.append(tok)

    return filtered


def _tokenize_chunk(args: tuple) -> list[list[str]]:
    """多進程 worker：對一個 chunk 的文本執行斷詞。"""
    texts, stopwords, financial_lexicon = args
    _init_jieba(financial_lexicon)
    return [_tokenize_single(t, stopwords) for t in texts]


# ============================================================
# 公開 API
# ============================================================

@timer
def tokenize_texts(
    texts: Iterable[str],
    stopwords: Optional[set[str]] = None,
    financial_lexicon: Optional[list[str]] = None,
    n_jobs: int = -1,
    chunk_size: int = 5000,
) -> list[list[str]]:
    """
    批次斷詞。

    Args:
        texts: 文本 iterable
        stopwords: 停用詞集合（None 用內建）
        financial_lexicon: 金融詞典（None 用內建）
        n_jobs: 進程數（-1 = all cores，1 = single process 便於 debug）
        chunk_size: 每個進程一次處理幾筆

    Returns:
        每筆文本的 token list
    """
    texts_list = list(texts)
    total = len(texts_list)
    logger.info(f"Tokenize {total:,} texts | n_jobs={n_jobs} | chunk={chunk_size}")

    stopwords_frozen = frozenset(stopwords or _DEFAULT_STOPWORDS)

    if n_jobs == 1 or total <= chunk_size:
        # 單進程快速路徑
        _init_jieba(financial_lexicon)
        result = [_tokenize_single(t, stopwords_frozen) for t in texts_list]
        avg_tokens = sum(len(r) for r in result) / max(len(result), 1)
        logger.info(f"  done | avg {avg_tokens:.1f} tokens/doc")
        return result

    # 多進程
    if n_jobs < 0:
        n_jobs = cpu_count()

    chunks = [
        (texts_list[i:i + chunk_size], stopwords_frozen, financial_lexicon)
        for i in range(0, total, chunk_size)
    ]

    logger.info(f"  dispatching {len(chunks):,} chunks to {n_jobs} workers")

    with Pool(processes=n_jobs) as pool:
        chunk_results = pool.map(_tokenize_chunk, chunks)

    # 展平
    result = [tok for chunk in chunk_results for tok in chunk]
    avg_tokens = sum(len(r) for r in result) / max(len(result), 1)
    logger.info(f"  done | avg {avg_tokens:.1f} tokens/doc")
    return result


@timer
def add_tokens_column(
    df: pd.DataFrame,
    text_col: Optional[str] = None,
    out_col: str = "tokens",
    n_jobs: int = -1,
) -> pd.DataFrame:
    """對 DataFrame 新增 tokens 欄位。"""
    if text_col is None:
        for cand in ["content", "text", "title", "body", "內容"]:
            if cand in df.columns:
                text_col = cand
                break

    if text_col is None or text_col not in df.columns:
        logger.error(f"No suitable text column found in {df.columns.tolist()}")
        return df

    logger.info(f"Tokenizing column '{text_col}' ({len(df):,} rows)")
    df = df.copy()
    df[out_col] = tokenize_texts(df[text_col].fillna("").tolist(), n_jobs=n_jobs)
    return df


# ============================================================
# PIT 對齊
# ============================================================

@timer
def align_to_trade_date(
    df_text: pd.DataFrame,
    trading_dates: pd.DatetimeIndex,
    post_time_col: str = "post_time",
    out_col: str = "trade_date",
    cutoff_hour: int = 8,
) -> pd.DataFrame:
    """
    將文章的 post_time 對齊到實際影響的 trade_date。

    規則（Point-in-Time 安全）：
      - 若 post_time < 當日 cutoff_hour（如 08:00）→ 當日 trade_date
      - 若 post_time >= cutoff_hour 且當日為交易日 → 次一個交易日
      - 週末、假日的文章 → 下一個交易日

    範例（cutoff_hour=8）：
      - 2024-06-03 (週一) 07:30 → trade_date = 2024-06-03
      - 2024-06-03 (週一) 09:30 → trade_date = 2024-06-04
      - 2024-06-01 (週六) 任意時間 → trade_date = 2024-06-03

    Args:
        df_text: 需有 post_time 欄
        trading_dates: 交易日索引（由 stock_prices.trade_date unique 取得）
        post_time_col: DataFrame 中的時間欄位
        out_col: 輸出欄位名
        cutoff_hour: 盤前截止時間（小時，24h 制）

    Returns:
        新增 out_col 欄位的 DataFrame
    """
    df = df_text.copy()
    df[post_time_col] = pd.to_datetime(df[post_time_col])

    # 排序並去重 trading dates
    td_sorted = pd.DatetimeIndex(sorted(set(trading_dates.normalize())))
    td_array = td_sorted.values.astype("datetime64[ns]")

    # 用 searchsorted 找每篇文章所屬的下一個交易日
    cutoff = time(cutoff_hour, 0)

    def _assign(ts: pd.Timestamp) -> Optional[pd.Timestamp]:
        if pd.isna(ts):
            return pd.NaT
        ts_norm = ts.normalize()
        # 若當日為交易日且 ts 時間 < cutoff → 當日
        if ts_norm in td_sorted and ts.time() < cutoff:
            return ts_norm
        # 否則：找「嚴格大於 ts_norm」的第一個交易日
        idx = td_sorted.searchsorted(ts_norm, side="right")
        if idx >= len(td_sorted):
            return pd.NaT
        return td_sorted[idx]

    # 為效能以 pandas vectorized 先粗分類，再對邊界情形做回退
    # 快速路徑：把 ts >= cutoff 的部分整日 +1，再 map 到下一交易日
    ts_norm = df[post_time_col].dt.normalize()
    ts_is_before_cut = df[post_time_col].dt.time < cutoff

    # 對每篇文章決定「參考日」：若盤前 → 當日；否則 → 明日
    reference_day = ts_norm.where(ts_is_before_cut, ts_norm + pd.Timedelta(days=1))

    # 用 searchsorted 批次對 reference_day 找下一個交易日（含當日）
    ref_values = reference_day.values.astype("datetime64[ns]")
    idx = td_sorted.searchsorted(ref_values, side="left")
    idx_clipped = pd.Series(idx, index=df.index).clip(upper=len(td_sorted) - 1)

    aligned = pd.Series(td_sorted[idx_clipped.to_numpy()], index=df.index)
    # 超出最後一個交易日的設為 NaT
    out_of_range = (idx >= len(td_sorted))
    if out_of_range.any():
        aligned.loc[out_of_range] = pd.NaT

    df[out_col] = aligned

    dropped_count = df[out_col].isna().sum()
    logger.info(
        f"PIT align: {len(df):,} rows | cutoff={cutoff_hour}:00 | "
        f"dropped {dropped_count:,} (out of trading range)"
    )
    return df


# ============================================================
# Stage 2.1 完整管線
# ============================================================

@timer
def run_tokenize_and_align(
    df_cleaned: pd.DataFrame,
    trading_dates: pd.DatetimeIndex,
    config: dict,
    out_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Stage 2.1 完整管線：
      1. 對 content 欄位斷詞（多進程）
      2. 對 title 欄位斷詞（多進程）
      3. PIT 對齊 post_time → trade_date
      4. 若 out_path 有值，輸出 parquet

    Args:
        df_cleaned: 已經過 text_processor.run_text_pipeline 清洗後的 DataFrame
        trading_dates: 交易日 DatetimeIndex（stock_prices.trade_date.unique()）
        config: 設定檔
        out_path: 選配；若給則輸出到此檔案

    Returns:
        含 tokens_content, tokens_title, trade_date 欄位的 DataFrame
    """
    n_jobs = config.get("preprocessing", {}).get("text", {}).get("n_jobs", -1)
    cutoff_hour = config.get("preprocessing", {}).get("text", {}).get("pit_cutoff_hour", 8)

    logger.info("=" * 60)
    logger.info(f"Stage 2.1 tokenize + PIT align | n_jobs={n_jobs}")
    logger.info("=" * 60)

    df = df_cleaned.copy()

    # 內容斷詞
    if "content" in df.columns:
        df = add_tokens_column(df, text_col="content", out_col="tokens_content", n_jobs=n_jobs)
    # 標題斷詞（通常更乾淨，下游情緒模型優先用）
    if "title" in df.columns:
        df = add_tokens_column(df, text_col="title", out_col="tokens_title", n_jobs=n_jobs)

    # PIT 對齊
    if "post_time" in df.columns and len(trading_dates) > 0:
        df = align_to_trade_date(
            df, trading_dates,
            post_time_col="post_time",
            out_col="trade_date",
            cutoff_hour=cutoff_hour,
        )

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_path, index=False)
        logger.info(f"Saved tokenized corpus to {out_path} ({len(df):,} rows)")

    return df
