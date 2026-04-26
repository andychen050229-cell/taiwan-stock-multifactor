"""
Phase 5B Stage 2.3 — 情緒特徵（sent_*）
========================================

流程：
  1. 載入 text_tokens_lite.parquet（Stage 2.1 產出，已做 PIT 對齊）
  2. 以 SnowNLP + engineer_phase5a 關鍵字 lexicon 混合打分（w=0.6/0.4）
  3. 用 industry.stock_name regex 掃描 title 展開成 (company_id, date, sent)
  4. 依 (company, trade_date) 聚合 + rolling 1d/5d/20d + PIT shift(1)
  5. merge 進 outputs/feature_store.parquet（7 支柱 → 8 支柱，新增 sent_）

執行：
    python 程式碼/執行Phase5B_情緒特徵.py
    python 程式碼/執行Phase5B_情緒特徵.py --sample-n 20000  # 快速驗證

預估時間：
  - 全量 583k 文章：SnowNLP 打分約 8~15 分鐘，aggregation ~2 分鐘
"""
from __future__ import annotations

import sys
import io
import gc
import argparse
import time
from pathlib import Path
from datetime import datetime

# UTF-8 stdout for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
from loguru import logger

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "程式碼"))

from src.features.sent_scorer import (
    score_sentiment,
    explode_mentions,
    aggregate_sent_features,
)


def setup_logger(log_path: Path):
    logger.remove()
    logger.add(sys.stdout, format="{time:HH:mm:ss} | {level:<7} | {message}", level="INFO")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(log_path),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {module}:{function}:{line} | {message}",
        level="DEBUG",
        rotation="50 MB",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description="Phase 5B Stage 2.3 — 情緒特徵 sent_*")
    parser.add_argument(
        "--tokens-file",
        type=str,
        default="outputs/text_tokens_lite.parquet",
        help="Stage 2.1 的輸出（PIT 對齊後的文本 tokens）",
    )
    parser.add_argument(
        "--feature-store",
        type=str,
        default="outputs/feature_store.parquet",
        help="Phase 1 產出的特徵存檔，將 merge sent_ 回去",
    )
    parser.add_argument(
        "--industry-file",
        type=str,
        default="選用資料集/parquet/industry.parquet",
        help="industry parquet（含 company_id/stock_name）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/feature_store_with_sent.parquet",
        help="輸出檔（若 --inplace 則覆寫 feature-store）",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="直接覆寫 feature-store（慎用，會備份）",
    )
    parser.add_argument(
        "--sample-n",
        type=int,
        default=None,
        help="只處理前 N 篇（配合除錯）",
    )
    parser.add_argument(
        "--w-snownlp",
        type=float,
        default=0.6,
        help="SnowNLP 分數權重（其餘 1-w 給關鍵字 lexicon）",
    )
    parser.add_argument(
        "--text-col",
        type=str,
        default="title",
        help="用哪個欄位打分（title 快，content 慢但更精準）",
    )
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = PROJECT_ROOT / "logs" / f"phase5b_s23_sentiment_{run_id}.log"
    setup_logger(log_path)

    logger.info("=" * 70)
    logger.info("Phase 5B Stage 2.3 — 情緒特徵 (SnowNLP + lexicon hybrid)")
    logger.info(f"Run ID:   {run_id}")
    logger.info(f"Log:      {log_path}")
    logger.info(f"Tokens:   {args.tokens_file}")
    logger.info(f"FS:       {args.feature_store}")
    logger.info(f"Industry: {args.industry_file}")
    logger.info(f"Text col: {args.text_col}")
    logger.info(f"w_snownlp={args.w_snownlp}")
    if args.sample_n:
        logger.warning(f"!! SAMPLE !! 只處理前 {args.sample_n:,} 篇")
    logger.info("=" * 70)

    t0 = time.time()

    # ─── Step 1: 載入 tokens ───
    tokens_path = PROJECT_ROOT / args.tokens_file
    if not tokens_path.exists():
        logger.error(f"Tokens file 不存在: {tokens_path}")
        sys.exit(1)

    logger.info(f"\n[1/5] Loading tokens {tokens_path} ...")
    df = pd.read_parquet(tokens_path)
    logger.info(f"  shape={df.shape}, cols={df.columns.tolist()}")

    if args.sample_n and args.sample_n < len(df):
        df = df.head(args.sample_n).copy()
        logger.warning(f"  截斷為前 {args.sample_n:,} 筆")

    # ─── Step 2: 打情緒分 ───
    logger.info(f"\n[2/5] Scoring sentiment on '{args.text_col}' ...")
    if args.text_col not in df.columns:
        logger.error(f"  text_col '{args.text_col}' 不在 tokens；可用欄位：{df.columns.tolist()}")
        sys.exit(1)
    texts = df[args.text_col].fillna("").astype(str).tolist()
    t1 = time.time()
    df["sent_raw"] = score_sentiment(texts, w_snownlp=args.w_snownlp)
    logger.info(f"  scoring done in {time.time()-t1:.1f}s")

    # ─── Step 3: stock mention 展開 ───
    logger.info(f"\n[3/5] Exploding by stock mention (regex over stock_name) ...")
    ind_path = PROJECT_ROOT / args.industry_file
    if not ind_path.exists():
        logger.error(f"Industry file 不存在: {ind_path}")
        sys.exit(1)
    ind_df = pd.read_parquet(ind_path, columns=["company_id", "stock_name"])
    exploded = explode_mentions(df, text_col=args.text_col, industry_df=ind_df)

    # 確保 trade_date 存在
    if "trade_date" not in exploded.columns:
        logger.error(f"  exploded 缺 trade_date 欄：{exploded.columns.tolist()}")
        sys.exit(1)

    # ─── Step 4: 聚合 + rolling + PIT shift ───
    logger.info(f"\n[4/5] Aggregating + rolling + PIT shift(1) ...")

    # 交易日曆：從 feature_store 取出
    fs_path = PROJECT_ROOT / args.feature_store
    if not fs_path.exists():
        logger.error(f"Feature store 不存在: {fs_path}")
        sys.exit(1)
    fs = pd.read_parquet(fs_path, columns=["company_id", "trade_date"])
    trading_dates = pd.DatetimeIndex(sorted(pd.to_datetime(fs["trade_date"]).unique()))
    all_company_ids = sorted(fs["company_id"].astype(str).unique().tolist())
    logger.info(f"  trading_dates={len(trading_dates)}, companies={len(all_company_ids)}")

    # 確保 company_id 型別與 fs 一致
    exploded["company_id"] = exploded["company_id"].astype(str)

    sent_feats = aggregate_sent_features(
        mentions_df=exploded,
        trading_dates=trading_dates,
        all_company_ids=all_company_ids,
        sent_col="sent_raw",
        date_col="trade_date",
        platform_col="p_type",
    )
    logger.info(f"  sent_feats shape={sent_feats.shape}")
    logger.info(f"  sample stats:")
    for c in sent_feats.columns:
        if c in ("company_id", "trade_date"):
            continue
        logger.info(
            f"    {c}: mean={sent_feats[c].mean():+.4f} "
            f"std={sent_feats[c].std():.4f} "
            f"nonzero={(sent_feats[c] != 0).sum():,}"
        )

    # ─── Step 5: merge 進 feature_store ───
    logger.info(f"\n[5/5] Merging sent_ features into feature_store ...")
    fs_full = pd.read_parquet(fs_path)
    logger.info(f"  feature_store pre-merge: {fs_full.shape}")
    fs_full["company_id"] = fs_full["company_id"].astype(str)
    fs_full["trade_date"] = pd.to_datetime(fs_full["trade_date"])
    sent_feats["trade_date"] = pd.to_datetime(sent_feats["trade_date"])

    # 清掉原本可能殘留的 sent_ 欄
    drop_cols = [c for c in fs_full.columns if c.startswith("sent_")]
    if drop_cols:
        logger.warning(f"  Dropping existing sent_ cols: {drop_cols}")
        fs_full = fs_full.drop(columns=drop_cols)

    merged = fs_full.merge(sent_feats, on=["company_id", "trade_date"], how="left")
    sent_cols_added = [c for c in merged.columns if c.startswith("sent_")]
    logger.info(f"  Added sent_ cols: {sent_cols_added}")
    # fill NaN（merge 沒命中的日子）
    merged[sent_cols_added] = merged[sent_cols_added].fillna(0.0)
    logger.info(f"  feature_store post-merge: {merged.shape}")

    # ─── 輸出 ───
    if args.inplace:
        backup_path = fs_path.with_suffix(f".bak_{run_id}.parquet")
        fs_path.rename(backup_path)
        logger.info(f"  Backup feature_store → {backup_path.name}")
        out_path = fs_path
    else:
        out_path = PROJECT_ROOT / args.output

    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(out_path, index=False)
    mb = out_path.stat().st_size / 1024**2
    logger.info(f"  Saved: {out_path} ({mb:.1f} MB)")

    elapsed = time.time() - t0
    logger.info("=" * 70)
    logger.info(f"✅ Stage 2.3 完成 — {elapsed/60:.1f} 分鐘")
    logger.info(f"   新增 sent_ 特徵數: {len(sent_cols_added)}")
    logger.info(f"   輸出: {out_path}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
