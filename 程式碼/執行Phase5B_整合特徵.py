"""
Phase 5B Stage 2.6 — 整合三支柱特徵 → feature_store_final.parquet
=================================================================

Stage 2.2/2.3/(2.4) 都寫到各自的輸出，這支 runner 把他們合併回主 feature_store：

  入：
    outputs/feature_store.parquet              (Phase 1：7 支柱 + labels)
    outputs/text_features.parquet              (Stage 2.2：txt_keyword_* / txt_volume_*)
    outputs/feature_store_with_sent.parquet    (Stage 2.3：已 merge sent_* 的完整表)
    outputs/topic_features.parquet            (Stage 2.4 選配：topic_*)

  出：
    outputs/feature_store_final.parquet        ← 整合後，供 Phase 2 訓練用
    outputs/feature_store.parquet              ← 若 --inplace，則備份原檔後覆寫

執行：
    python 程式碼/執行Phase5B_整合特徵.py [--inplace]
"""
from __future__ import annotations

import sys
import io
import argparse
import time
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import pandas as pd
from loguru import logger

PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def _pillar_of(col: str) -> str:
    for prefix in ("trend_", "fund_", "val_", "event_", "risk_", "chip_",
                   "ind_", "sent_", "txt_", "topic_", "mg_"):
        if col.startswith(prefix):
            return prefix.rstrip("_")
    if col.startswith(("fwd_ret_", "label_")):
        return "label"
    return "other"


def main():
    parser = argparse.ArgumentParser(description="Phase 5B Stage 2.6 — 整合三支柱特徵")
    parser.add_argument("--sent-fs", default="outputs/feature_store_with_sent.parquet")
    parser.add_argument("--txt-features", default="outputs/text_features.parquet")
    parser.add_argument("--topic-features", default="outputs/topic_features.parquet")
    parser.add_argument("--output", default="outputs/feature_store_final.parquet")
    parser.add_argument("--inplace", action="store_true",
                        help="覆寫 outputs/feature_store.parquet（備份為 .bak）")
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = PROJECT_ROOT / "logs" / f"phase5b_s26_merge_{run_id}.log"
    logger.remove()
    logger.add(sys.stdout, format="{time:HH:mm:ss} | {level:<7} | {message}", level="INFO")
    logger.add(str(log_path), level="DEBUG", encoding="utf-8")

    logger.info("=" * 70)
    logger.info("Phase 5B Stage 2.6 — 整合三支柱特徵")
    logger.info(f"Run ID: {run_id}")
    logger.info("=" * 70)

    t0 = time.time()

    # ─── 以 sent_fs 為主幹（因為它已經是 feature_store + sent_） ───
    sent_path = PROJECT_ROOT / args.sent_fs
    if not sent_path.exists():
        logger.error(f"Sent FS 不存在：{sent_path}")
        sys.exit(1)

    logger.info(f"\n[1/3] Loading main base: {sent_path.name}")
    df = pd.read_parquet(sent_path)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["company_id"] = df["company_id"].astype(str)
    logger.info(f"  shape: {df.shape}")

    # ─── merge txt_ ───
    txt_path = PROJECT_ROOT / args.txt_features
    if txt_path.exists():
        logger.info(f"\n[2/3] Merging txt: {txt_path.name}")
        txt_df = pd.read_parquet(txt_path)
        txt_df["trade_date"] = pd.to_datetime(txt_df["trade_date"])
        txt_df["company_id"] = txt_df["company_id"].astype(str)
        txt_cols = [c for c in txt_df.columns if c.startswith("txt_")]
        logger.info(f"  adding {len(txt_cols)} txt_ cols")
        df = df.merge(txt_df[["company_id", "trade_date"] + txt_cols],
                      on=["company_id", "trade_date"], how="left")
        for c in txt_cols:
            df[c] = df[c].fillna(0.0)
        logger.info(f"  shape: {df.shape}")
    else:
        logger.warning(f"  txt_features 不存在：{txt_path}")

    # ─── merge topic_ (optional) ───
    topic_path = PROJECT_ROOT / args.topic_features
    if topic_path.exists():
        logger.info(f"\n[3/3] Merging topic: {topic_path.name}")
        topic_df = pd.read_parquet(topic_path)
        topic_df["trade_date"] = pd.to_datetime(topic_df["trade_date"])
        topic_df["company_id"] = topic_df["company_id"].astype(str)
        topic_cols = [c for c in topic_df.columns if c.startswith("topic_")]
        logger.info(f"  adding {len(topic_cols)} topic_ cols")
        df = df.merge(topic_df[["company_id", "trade_date"] + topic_cols],
                      on=["company_id", "trade_date"], how="left")
        for c in topic_cols:
            df[c] = df[c].fillna(0.0)
        logger.info(f"  shape: {df.shape}")
    else:
        logger.info(f"  topic_features 略過（Stage 2.4 為選配）")

    # ─── 統計 pillar ───
    by_pillar = {}
    for c in df.columns:
        by_pillar.setdefault(_pillar_of(c), []).append(c)
    logger.info("\n--- Final pillar summary ---")
    for p, cols in sorted(by_pillar.items()):
        logger.info(f"  {p:<8} : {len(cols):>4} cols")
    logger.info(f"  TOTAL    : {df.shape[1]:>4} cols × {df.shape[0]:,} rows")

    # ─── 輸出 ───
    out_main = PROJECT_ROOT / args.output
    df.to_parquet(out_main, index=False)
    mb = out_main.stat().st_size / 1024**2
    logger.info(f"\n  Saved final: {out_main} ({mb:.1f} MB)")

    if args.inplace:
        orig = PROJECT_ROOT / "outputs" / "feature_store.parquet"
        if orig.exists():
            bak = orig.with_suffix(f".bak_{run_id}.parquet")
            orig.rename(bak)
            logger.info(f"  Backed up: {bak.name}")
        df.to_parquet(orig, index=False)
        logger.info(f"  Overwrote: {orig}")

    elapsed = time.time() - t0
    logger.info("=" * 70)
    logger.info(f"✅ Stage 2.6 完成 — {elapsed/60:.1f} 分鐘")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
