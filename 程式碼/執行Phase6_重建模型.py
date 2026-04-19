"""Phase 6 Stage 0 — Joblib 模型重建（修復 stale bug）
==========================================================

背景：Phase 2 於 2026-04-19 重跑時，outputs/models/*.joblib 未被正確覆寫，
仍停留在 4/8 的舊版（28 features，含已下架的 event_news_count_1d/5d 欄名）。
這導致 Phase 3 prediction_pipeline_valid 閘門 FAIL。

本腳本：
  1. 讀取最新 phase2_report_*.json 取 selected_features（91 個）
  2. 載入 feature_store_final.parquet（1,623 columns）
  3. 用 walk-forward 最後一折訓練 6 個模型（LGB/XGB × D1/D5/D20）
  4. 以新的 save_models（含 backup 機制）覆寫 outputs/models/*.joblib

執行方式：
  python 程式碼/執行Phase6_重建模型.py
"""
from __future__ import annotations

import sys
import io
import json
import gc
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import pandas as pd
import joblib
from loguru import logger

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "程式碼"))

from src.utils.config_loader import load_config
from src.models.walk_forward import generate_walk_forward_splits
from src.models.trainer import train_all_models, save_models


def main():
    t0 = time.time()
    logger.info("=" * 70)
    logger.info("Phase 6 Stage 0 — Joblib 模型重建")
    logger.info("=" * 70)

    # 1. 載入 config（load_config 需要 config 目錄路徑）
    config = load_config(str(PROJECT_ROOT / "程式碼" / "src" / "config"))

    # 2. 取最新 P2 report
    reports_dir = PROJECT_ROOT / "outputs" / "reports"
    p2_files = sorted(reports_dir.glob("phase2_report_*.json"), reverse=True)
    if not p2_files:
        logger.error("找不到 phase2_report_*.json，請先跑 Phase 2。")
        sys.exit(1)
    p2_path = p2_files[0]
    logger.info(f"使用 P2 報告：{p2_path.name}")
    with open(p2_path, encoding="utf-8") as f:
        p2 = json.load(f)
    selected_features = p2["results"]["feature_selection"]["selected"]
    viable_horizons = [1, 5, 20]
    engines = config.get("model", {}).get("engines", ["lightgbm", "xgboost"])
    logger.info(f"Selected features: {len(selected_features)}")
    logger.info(f"Horizons: {viable_horizons}")
    logger.info(f"Engines:  {engines}")

    # 3. 先把舊 joblib 移到 archive
    model_dir = PROJECT_ROOT / "outputs" / "models"
    archive_dir = model_dir / f"archive_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    old_files = list(model_dir.glob("*.joblib"))
    if old_files:
        archive_dir.mkdir(parents=True, exist_ok=True)
        for f in old_files:
            f.rename(archive_dir / f.name)
        logger.info(f"已備份 {len(old_files)} 個舊 joblib 到 {archive_dir.name}")

    # 4. 載入 feature_store
    fs_path = PROJECT_ROOT / "outputs" / "feature_store_final.parquet"
    if not fs_path.exists():
        fs_path = PROJECT_ROOT / "outputs" / "feature_store.parquet"
    logger.info(f"載入 feature_store：{fs_path.name}")
    # 只讀必要欄位
    need_cols = ["company_id", "trade_date"] + selected_features + [
        f"label_{h}" for h in viable_horizons
    ]
    all_cols = pd.read_parquet(fs_path, columns=None).columns.tolist()  # peek
    need_cols = [c for c in need_cols if c in all_cols]
    fs = pd.read_parquet(fs_path, columns=need_cols)
    logger.info(f"載入完成：{fs.shape}")

    # 5. 產生 walk-forward splits → 只用最後一折
    folds = generate_walk_forward_splits(fs, date_col="trade_date", config=config)
    last_fold_only = [folds[-1]]
    logger.info(f"WF folds total={len(folds)}，取最後一折重建")

    # 6. 每個 horizon 訓練 + 存檔
    for h in viable_horizons:
        label_col = f"label_{h}"
        if label_col not in fs.columns:
            logger.warning(f"  {label_col} 不在 feature_store，跳過 D+{h}")
            continue
        logger.info(f"\n=== Training D+{h} ({label_col}) ===")

        h_results = train_all_models(
            df=fs,
            feature_cols=selected_features,
            label_col=label_col,
            folds=last_fold_only,
            config=config,
        )

        for eng, res in h_results.items():
            if "error" in res:
                logger.warning(f"  {eng}_D{h}: training error — {res['error']}")
                continue
            save_models(
                {f"{eng}_D{h}": res},
                feature_cols=selected_features,
                label_col=label_col,
                output_dir=str(model_dir),
            )
        gc.collect()

    # 7. 驗證：每個 joblib 都要有正確 feature_cols
    logger.info("\n=== Verifying joblib files ===")
    saved = sorted(model_dir.glob("*.joblib"))
    ok = fail = 0
    for p in saved:
        try:
            d = joblib.load(str(p))
            stored = d.get("feature_cols", [])
            if set(stored) == set(selected_features):
                logger.info(f"  ✅ {p.name}: {len(stored)} features, label={d.get('label_col')}")
                ok += 1
            else:
                logger.error(f"  ❌ {p.name}: feature_cols 不符 ({len(stored)} vs {len(selected_features)})")
                fail += 1
        except Exception as e:
            logger.error(f"  ❌ {p.name}: load failed ({e})")
            fail += 1

    dur = time.time() - t0
    logger.info("=" * 70)
    logger.info(f"完成：{ok} OK，{fail} FAIL ｜ 耗時 {dur/60:.1f} 分鐘")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
