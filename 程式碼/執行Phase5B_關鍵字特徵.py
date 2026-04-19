"""
Phase 5B Stage 2.2 — 關鍵字特徵 (txt_*)
=========================================
對應過往範例：
  - G1 (聯發科)：關鍵字萃取 + 重要性排序
  - G10 (台泥) ：TF-IDF + Chi² + SVM → 95.2% accuracy @ threshold=0.25
  - G20 (174 半導體)：TF-IDF top 1500 + 多模型

本 runner 產出兩組特徵：
  - txt_keyword_{kw}_{win}d: 關鍵字 win 日內累計出現次數 (PIT-safe rolling)
  - txt_volume_*:            文本量 / 平均長度 / 平台分布

輸入：
  outputs/text_tokens_lite.parquet   ← Stage 2.1 輸出
  outputs/feature_store.parquet      ← Phase 1 輸出（取 label_horizon_5 作為訓練信號）

輸出：
  outputs/text_keywords.parquet      ← 關鍵字清單 + Chi²/MI/Lift 分數
  outputs/text_features.parquet      ← txt_* 特徵矩陣（company_id × trade_date）

執行方式：
  python 程式碼/執行Phase5B_關鍵字特徵.py [--top-n 500] [--horizon 5]
"""
from __future__ import annotations

import sys
import io
import gc
import argparse
import time
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
import yaml
from loguru import logger

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "程式碼"))

from src.features.text_features import (
    select_keywords,
    build_keyword_features,
    build_volume_features,
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
        retention="30 days",
        encoding="utf-8",
    )


def load_config(config_path: Path) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Phase 5B Stage 2.2 — 關鍵字特徵")
    parser.add_argument("--tokens-file", default="outputs/text_tokens_lite.parquet",
                        help="Stage 2.1 輸出路徑")
    parser.add_argument("--feature-store", default="outputs/feature_store.parquet",
                        help="Phase 1 feature_store 路徑（取 label）")
    parser.add_argument("--horizon", type=int, default=5,
                        choices=[1, 5, 20], help="用哪個 D+H 的 label（預設 5）")
    parser.add_argument("--top-n", type=int, default=500,
                        help="保留的關鍵字數量")
    parser.add_argument("--min-df", type=int, default=10,
                        help="TF-IDF min_df（至少出現在 N 篇）")
    parser.add_argument("--max-df", type=float, default=0.5,
                        help="TF-IDF max_df（最多出現在 N% 篇）")
    parser.add_argument("--rolling-windows", default="1,5,20",
                        help="rolling 視窗（逗號分隔）")
    parser.add_argument("--resume-from-keywords", action="store_true",
                        help="從已存檔的 text_keywords.parquet 讀回 selected=True，"
                             "跳過 Chi²+MI+Lift 三重篩選（12 分鐘），直接進 Step 4")
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = PROJECT_ROOT / "logs" / f"phase5b_s22_keywords_{run_id}.log"
    setup_logger(log_path)

    logger.info("=" * 70)
    logger.info("Phase 5B Stage 2.2 — 關鍵字特徵 (txt_*)")
    logger.info(f"Run ID:     {run_id}")
    logger.info(f"Horizon:    D+{args.horizon}")
    logger.info(f"Top N KW:   {args.top_n}")
    logger.info(f"min_df:     {args.min_df}")
    logger.info(f"max_df:     {args.max_df}")
    logger.info(f"Windows:    {args.rolling_windows}")
    logger.info("=" * 70)

    t0 = time.time()
    config = load_config(PROJECT_ROOT / "程式碼" / "src" / "config" / "base.yaml")
    rolling_windows = tuple(int(w) for w in args.rolling_windows.split(","))

    # ===== 1. 載入 Stage 2.1 tokens =====
    logger.info("\n[Step 1/5] 載入 Stage 2.1 tokens ...")
    tokens_path = PROJECT_ROOT / args.tokens_file
    if not tokens_path.exists():
        logger.error(f"找不到 tokens 檔：{tokens_path}。先跑 Stage 2.1。")
        return
    df_tokens = pd.read_parquet(tokens_path)
    logger.info(f"  載入: {len(df_tokens):,} 筆 × {df_tokens.shape[1]} 欄")

    # 去除無 trade_date 的 row（超出交易日範圍）
    before = len(df_tokens)
    df_tokens = df_tokens.dropna(subset=["trade_date"])
    logger.info(f"  去除 NaN trade_date: {before - len(df_tokens):,}")

    # 找 tokens 欄（tokens_title 或 tokens_content）
    token_col = None
    for cand in ["tokens_content", "tokens_title", "tokens"]:
        if cand in df_tokens.columns:
            token_col = cand
            break
    if token_col is None:
        raise ValueError(f"找不到 tokens 欄；現有欄位：{df_tokens.columns.tolist()}")
    logger.info(f"  使用 tokens 欄位：{token_col}")

    # ===== 1b. stock_text 沒有 company_id — 用 regex 掃 title 找提及的股票 =====
    # stock_text 的 s_name 是「平台名」不是股票代號；需用 industry.stock_name 掃文中 mention
    if "company_id" not in df_tokens.columns:
        import re
        logger.info("\n[Step 1b] stock_text 無 company_id，用 stock_name regex 掃 title ...")
        industry_path = PROJECT_ROOT / "選用資料集" / "parquet" / "industry.parquet"
        ind_df = pd.read_parquet(industry_path, columns=["company_id", "stock_name"])
        ind_df = ind_df.dropna().drop_duplicates(subset="stock_name")
        ind_df = ind_df[ind_df["stock_name"].str.len() >= 2]
        name2id = dict(zip(ind_df["stock_name"], ind_df["company_id"]))
        logger.info(f"  name2id 映射：{len(name2id):,} 家")

        # 建 regex（長名優先以避免「台」吃掉「台積電」）
        names_sorted = sorted(ind_df["stock_name"].tolist(), key=len, reverse=True)
        pattern = re.compile("|".join(re.escape(n) for n in names_sorted))

        # 以 title 為對象掃 mention
        title_col = "title" if "title" in df_tokens.columns else None
        if title_col is None:
            raise ValueError("沒 title 欄可做 mention 掃描")

        logger.info(f"  掃描 {len(df_tokens):,} 篇 title ...")
        df_tokens["_mentions"] = df_tokens[title_col].fillna("").str.findall(pattern)
        df_tokens["_n_mentions"] = df_tokens["_mentions"].str.len()
        logger.info(f"  平均每篇提及 {df_tokens['_n_mentions'].mean():.2f} 檔；無提及 {(df_tokens['_n_mentions']==0).sum():,} 篇")

        # 展開 article × mentioned_stock
        exploded = df_tokens.explode("_mentions").dropna(subset=["_mentions"])
        exploded = exploded.rename(columns={"_mentions": "stock_name"})
        exploded["company_id"] = exploded["stock_name"].map(name2id)
        exploded = exploded.dropna(subset=["company_id"])
        exploded["company_id"] = exploded["company_id"].astype(str)
        logger.info(f"  展開後 article × stock：{len(exploded):,} 對")
        df_tokens = exploded
        del exploded; gc.collect()

    # 清理暫存欄位
    for c in ["_mentions", "_n_mentions"]:
        if c in df_tokens.columns:
            df_tokens = df_tokens.drop(columns=c)

    # ===== 2. 載入 feature_store 取 labels =====
    logger.info("\n[Step 2/5] 載入 feature_store 取 label ...")
    fs_path = PROJECT_ROOT / args.feature_store
    if not fs_path.exists():
        logger.error(f"找不到 feature_store：{fs_path}。先跑 Phase 1。")
        return

    label_col = f"label_{args.horizon}"
    fs = pd.read_parquet(fs_path, columns=["company_id", "trade_date", label_col])
    logger.info(f"  載入 feature_store: {fs.shape}")
    logger.info(f"  {label_col} 分布：\n{fs[label_col].value_counts(dropna=False)}")

    # merge 文本 × label（article-level）
    df_tokens["trade_date"] = pd.to_datetime(df_tokens["trade_date"])
    fs["trade_date"] = pd.to_datetime(fs["trade_date"])
    df_art = df_tokens.merge(fs, on=["company_id", "trade_date"], how="inner")
    del fs
    gc.collect()
    logger.info(f"  article × label 成對資料：{len(df_art):,} 筆")

    # 丟掉 label 為 NaN 的 row
    df_art = df_art.dropna(subset=[label_col])
    logger.info(f"  丟除 NaN label 後：{len(df_art):,} 筆")

    # 為 select_keywords 準備 corpus + labels
    corpus = df_art[token_col].tolist()
    labels = df_art[label_col].astype(int).values

    # ===== 3. 關鍵字三重篩選（可 resume） =====
    kw_out = PROJECT_ROOT / "outputs" / "text_keywords.parquet"
    if args.resume_from_keywords and kw_out.exists():
        logger.info("\n[Step 3/5] RESUME — 從 text_keywords.parquet 讀回關鍵字 ...")
        scores_df = pd.read_parquet(kw_out)
        selected_mask = scores_df["selected"].astype(bool) if "selected" in scores_df.columns else \
            pd.Series(True, index=scores_df.index)
        keywords = scores_df.loc[selected_mask, "term"].astype(str).tolist()
        # 依 rank_combined 排序
        if "rank_combined" in scores_df.columns:
            keywords = scores_df[selected_mask].sort_values("rank_combined")["term"].astype(str).tolist()
        logger.info(f"  載入 {len(keywords)} 個 selected keywords")
        logger.info(f"  前 10 名：{keywords[:10]}")
    else:
        logger.info("\n[Step 3/5] TF-IDF + Chi² + MI + Lift 三重篩選 ...")
        keywords, scores_df = select_keywords(
            corpus=corpus,
            labels=labels,
            top_n=args.top_n,
            min_df=args.min_df,
            max_df=args.max_df,
            intersection_ratio=0.5,
        )
        logger.info(f"  選出 {len(keywords)} 個關鍵字")
        logger.info(f"  前 10 名：{keywords[:10]}")

        scores_df.to_parquet(kw_out, index=False)
        logger.info(f"  關鍵字分數表：{kw_out}")

    # 解除語料記憶體
    del corpus, labels, df_art
    gc.collect()

    # ===== 4. 建立 txt_keyword_* 特徵矩陣 =====
    logger.info("\n[Step 4/5] 建立 txt_keyword_{kw}_{win}d 特徵矩陣 ...")
    kw_ckpt = PROJECT_ROOT / "outputs" / "_kw_features_ckpt.parquet"
    if args.resume_from_keywords and kw_ckpt.exists():
        logger.info(f"  RESUME — 從 {kw_ckpt.name} 讀回 keyword 特徵")
        kw_features = pd.read_parquet(kw_ckpt)
    else:
        kw_features = build_keyword_features(
            df_tokens=df_tokens,
            keywords=keywords,
            group_cols=("company_id", "trade_date"),
            token_col=token_col,
            rolling_windows=rolling_windows,
        )
        # checkpoint，Step 5 失敗時可 resume
        kw_features.to_parquet(kw_ckpt, index=False)
        logger.info(f"  checkpoint saved: {kw_ckpt.name}")
    logger.info(f"  keyword 特徵：{kw_features.shape}")

    # ===== 5. 建立 txt_volume_* 特徵 =====
    logger.info("\n[Step 5/5] 建立 txt_volume_* 特徵 ...")
    vol_features = build_volume_features(
        df_tokens=df_tokens,
        group_cols=("company_id", "trade_date"),
        rolling_windows=rolling_windows,
        token_col=token_col,  # 用 Stage 2.1 實際產出的 tokens 欄名
    )
    logger.info(f"  volume 特徵：{vol_features.shape}")

    # ===== 合併 + 輸出 =====
    logger.info("\n合併 keyword + volume 特徵 ...")
    txt_features = kw_features.merge(
        vol_features, on=["company_id", "trade_date"], how="outer"
    )
    logger.info(f"  最終 txt_ 特徵：{txt_features.shape}")

    out_path = PROJECT_ROOT / "outputs" / "text_features.parquet"
    txt_features.to_parquet(out_path, index=False)
    mb = out_path.stat().st_size / 1024**2
    logger.info(f"  輸出：{out_path} ({mb:.1f} MB)")

    # Summary
    elapsed = time.time() - t0
    txt_kw_cols = [c for c in txt_features.columns if c.startswith("txt_keyword_")]
    txt_vol_cols = [c for c in txt_features.columns if c.startswith("txt_volume_")]
    logger.info("=" * 70)
    logger.info(f"✅ Stage 2.2 完成 | 總時間 {elapsed/60:.1f} 分鐘")
    logger.info(f"   txt_keyword_*: {len(txt_kw_cols)} 欄")
    logger.info(f"   txt_volume_*:  {len(txt_vol_cols)} 欄")
    logger.info(f"   合計 {len(txt_features.columns)} 欄 × {len(txt_features):,} rows")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
