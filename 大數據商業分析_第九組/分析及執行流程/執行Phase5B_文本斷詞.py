"""
Phase 5B Stage 2.1 — 文本預處理與斷詞 + PIT 對齊
=================================================
流程（對應過往範例 G1/G10/G20 的文本預處理步驟）：
  1. 載入 stock_text（教授 A4，1.12M 篇）
  2. Four-layer filter：content_type / 長度語言 / MinHash LSH 去重 / 清洗
  3. jieba 斷詞（財經詞典 + 停用詞）+ multiprocessing
  4. PIT 對齊：post_time → trade_date（cutoff_hour=8 前算當日，之後算下一交易日）
  5. 輸出 outputs/text_tokens.parquet（供 Stage 2.2/2.3/2.4 使用）

執行方式：
    python 程式碼/執行Phase5B_文本斷詞.py [--use-full-content] [--dry-run]

預估時間：
  - 使用 title（預設）：~1-2 小時（1.12M × avg 30 chars）
  - 使用 content：~4-6 小時（1.12M × avg 150 chars）
"""
from __future__ import annotations

import sys
import io
import gc
import argparse
import time
from pathlib import Path
from datetime import datetime

# UTF-8 stdout for Chinese output on Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import pandas as pd
import yaml
from loguru import logger

# 設定路徑
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "程式碼"))

from src.data.loader import DataLoader
from src.data.text_processor import run_text_pipeline
from src.data.text_tokenizer import run_tokenize_and_align


def setup_logger(log_path: Path):
    """配置 loguru 同時輸出到檔案與 console"""
    logger.remove()
    logger.add(sys.stdout, format="{time:HH:mm:ss} | {level:<7} | {message}", level="INFO")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(log_path),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {module}:{function}:{line} | {message}",
        level="DEBUG",
        rotation="50 MB",
        retention="30 days",
        encoding="utf-8",
    )


def load_config(config_path: Path) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_trading_dates(loader: DataLoader) -> pd.DatetimeIndex:
    """從 stock_prices 取出所有交易日（全市場 union）"""
    prices = loader.load_stock_prices()
    date_col = "trade_date" if "trade_date" in prices.columns else "date"
    dates = pd.to_datetime(prices[date_col].unique())
    trading_dates = pd.DatetimeIndex(sorted(dates))
    logger.info(
        f"Trading dates: {len(trading_dates):,} unique days "
        f"({trading_dates.min()} ~ {trading_dates.max()})"
    )
    del prices
    gc.collect()
    return trading_dates


def main():
    parser = argparse.ArgumentParser(description="Phase 5B Stage 2.1 — 文本斷詞與 PIT 對齊")
    parser.add_argument(
        "--use-full-content",
        action="store_true",
        help="使用 stock_text (full content) 而非 stock_text_lite (title only)。預設使用 lite。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run：只跑前 10,000 篇驗證 pipeline 可運作，不寫出正式檔。",
    )
    parser.add_argument(
        "--sample-n",
        type=int,
        default=None,
        help="只處理前 N 篇（配合除錯）。",
    )
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = PROJECT_ROOT / "logs" / f"phase5b_s21_tokenize_{run_id}.log"
    setup_logger(log_path)

    logger.info("=" * 70)
    logger.info("Phase 5B Stage 2.1 — 文本斷詞與 PIT 對齊")
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Log:    {log_path}")
    logger.info(f"Mode:   {'FULL CONTENT' if args.use_full_content else 'TITLE ONLY (lite)'}")
    if args.dry_run:
        logger.warning("!! DRY RUN !! — 只處理前 10,000 篇")
    if args.sample_n:
        logger.warning(f"!! SAMPLE !! — 只處理前 {args.sample_n:,} 篇")
    logger.info("=" * 70)

    t0 = time.time()

    # ===== 1. 載入設定與資料 =====
    config = load_config(PROJECT_ROOT / "程式碼" / "src" / "config" / "base.yaml")
    config["_project_root"] = str(PROJECT_ROOT)  # DataLoader 用這把 key 解析 parquet_dir
    loader = DataLoader(config=config)

    logger.info("\n[Step 1/4] 載入 stock_text ...")
    text_df = loader.load_stock_text(lite=not args.use_full_content)
    logger.info(f"  載入: {len(text_df):,} 筆")

    # 可選：取樣
    n_limit = 10_000 if args.dry_run else args.sample_n
    if n_limit and n_limit < len(text_df):
        text_df = text_df.head(n_limit).copy()
        logger.warning(f"  截斷為前 {n_limit:,} 筆")

    # 載入交易日曆
    trading_dates = load_trading_dates(loader)

    # ===== 2. Four-Layer 文本前處理 =====
    logger.info("\n[Step 2/4] Four-layer 文本前處理 (content_type / 長度語言 / MinHash / 清洗) ...")
    text_df_clean = run_text_pipeline(text_df, config)
    logger.info(
        f"  通過: {len(text_df_clean):,} / {len(text_df):,} "
        f"({len(text_df_clean)/len(text_df)*100:.1f}%)"
    )
    del text_df
    gc.collect()

    # ===== 3. jieba 斷詞 + PIT 對齊 =====
    logger.info("\n[Step 3/4] jieba 斷詞 + PIT 對齊 (multiprocessing) ...")
    if args.dry_run:
        out_path = None  # dry run 不寫出
    else:
        out_dir = PROJECT_ROOT / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = "full" if args.use_full_content else "lite"
        out_path = out_dir / f"text_tokens_{suffix}.parquet"

    result = run_tokenize_and_align(
        df_cleaned=text_df_clean,
        trading_dates=trading_dates,
        config=config,
        out_path=out_path,
    )

    # ===== 4. Summary =====
    logger.info("\n[Step 4/4] Summary")
    elapsed = time.time() - t0
    logger.info(f"  總時間: {elapsed/60:.1f} 分鐘")
    logger.info(f"  結果筆數: {len(result):,}")
    logger.info(f"  欄位: {result.columns.tolist()}")
    if "trade_date" in result.columns:
        logger.info(
            f"  trade_date 範圍: {result['trade_date'].min()} ~ {result['trade_date'].max()}"
        )
        n_na = result["trade_date"].isna().sum()
        logger.info(f"  trade_date 缺失: {n_na:,} ({n_na/len(result)*100:.2f}%)")
    if out_path:
        mb = out_path.stat().st_size / 1024**2
        logger.info(f"  輸出: {out_path} ({mb:.1f} MB)")

    logger.info("=" * 70)
    logger.info("✅ Stage 2.1 完成")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
