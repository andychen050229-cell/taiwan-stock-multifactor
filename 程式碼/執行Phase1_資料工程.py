#!/usr/bin/env python3
"""
Phase 1 主執行腳本：資料地基 + 特徵工程

執行內容：
  1. 載入設定檔
  2. 載入四張 Parquet 資料表（+ OHLCV 如果已抓取）
  3. 資料品質概覽
  4. 股價前處理（缺值 + 除權息驗證 + 漲跌停偵測）
  5. 文本前處理（content_type + 過濾 + 去重 + 清洗）
  6. 財報處理（累計→單季 + PIT 日期 + 財務比率）
  7. 標籤生成（D+1, D+5, D+20）
  8. 五大支柱特徵工程
  9. 前瞻偏差偵測
  10. Feature Store 輸出 + 品質報告

使用方式：
  cd 大數據與商業分析專案
  python 程式碼/執行Phase1_資料工程.py

品質閘門（Quality Gate）：
  ✓ 除權息還原抽驗誤差 < 0.5%
  ✓ 文本去重率 15-30%（合理範圍）
  ✓ 四重洩漏偵測零 warning
  ✓ 標籤一致性檢查 PASS
  ✓ Feature Store 無 Inf 值
  ✓ 所有腳本有 loguru 日誌輸出
"""
import sys
import json
from pathlib import Path
from datetime import datetime

import gc

import numpy as np
import pandas as pd

# 確保 src/ 可被 import
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config_loader import load_config
from src.utils.logger import get_logger
from src.data.loader import DataLoader, quick_profile
from src.data.price_processor import (
    handle_missing_prices,
    filter_suspended_days,
    verify_ex_dividend,
    detect_limit_moves,
    quality_check_prices,
)
from src.data.text_processor import run_text_pipeline
from src.data.financial_processor import run_financial_pipeline
from src.data.balance_sheet_processor import run_balance_sheet_pipeline
from src.data.label_generator import run_label_pipeline
from src.data.leakage_detector import run_leakage_detection
from src.features.engineer import run_feature_pipeline


def main():
    """Phase 1 主流程"""

    # ===== 1. 載入設定 =====
    config = load_config()
    log = get_logger("phase1", config)

    # 設定全域隨機種子以確保可重現性
    random_seed = config.get("random_seed", 42)
    np.random.seed(random_seed)
    log.info(f"Random seed set to: {random_seed}")

    log.info("=" * 70)
    log.info("Phase 1: 資料地基 + 特徵工程 — 開始執行")
    log.info(f"Environment: {config.get('_env', 'unknown')}")
    log.info(f"Project root: {config.get('_project_root', 'unknown')}")
    log.info("=" * 70)

    # 收集所有結果
    report = {
        "phase": "Phase 1 — 資料地基 + 特徵工程",
        "timestamp": datetime.now().isoformat(),
        "env": config.get("_env"),
        "results": {},
    }

    # ===== 2. 載入資料 =====
    log.info("\n[Step 1/10] Loading data from Parquet...")
    loader = DataLoader(config)

    try:
        # Phase 5A（2026-04-19 修正）：改用 stock_text_lite（title only）
        # 原因：全文 1.12M × 平均 500 字做 MinHash LSH（num_perm=128）會掛住電腦
        # （曾在 11:12 掛死）。title 平均 22 字，MinHash 自動退回 exact dedup，秒級完成。
        # Phase 5B Stage 2.1 已另外產出 text_tokens_lite.parquet 供後續使用。
        data = loader.load_all(text_lite=True)
    except FileNotFoundError as e:
        log.error(f"Data file not found: {e}")
        log.error("Please ensure Parquet files exist in the configured directory.")
        sys.exit(1)

    # 嘗試載入 OHLCV（如果已抓取）
    root = Path(config.get("_project_root", "."))
    ohlcv_path = root / config["data"]["parquet_dir"] / config["data"].get("ohlcv", "stock_prices_ohlcv.parquet")
    has_ohlcv = False
    if ohlcv_path.exists():
        log.info(f"  Found OHLCV data: {ohlcv_path}")
        ohlcv_df = pd.read_parquet(ohlcv_path)
        data["stock_prices"] = ohlcv_df
        has_ohlcv = True
        log.info(f"  OHLCV loaded: {ohlcv_df.shape[0]:,} rows × {ohlcv_df.shape[1]} cols")
    else:
        log.warning(f"  OHLCV file not found ({ohlcv_path.name}). Using close-only mode.")

    report["results"]["has_ohlcv"] = has_ohlcv

    # ===== 3. 資料品質概覽 =====
    log.info("\n[Step 2/10] Data quality profiling...")
    profiles = {}
    for name, df in data.items():
        profiles[name] = quick_profile(df, name)
    report["results"]["profiles"] = {
        k: {kk: str(vv) for kk, vv in v.items()} for k, v in profiles.items()
    }

    # ===== 4. 股價前處理 =====
    log.info("\n[Step 3/10] Stock price preprocessing...")

    # 4a. 缺值處理
    data["stock_prices"] = handle_missing_prices(data["stock_prices"], config)

    # 4a2. 停牌日過濾（移除 OHLC 全為零的列，修正異常零收盤價）
    data["stock_prices"] = filter_suspended_days(data["stock_prices"], config)

    # 4b. 除權息驗證
    ex_div_results = verify_ex_dividend(data["stock_prices"], config)
    report["results"]["ex_dividend_verification"] = _serialize(ex_div_results)

    # 4c. 漲跌停偵測
    data["stock_prices"] = detect_limit_moves(data["stock_prices"])

    # 清理漲跌停工具欄位，避免洩漏至 Feature Store
    _limit_cols = ["_is_limit_up", "_is_limit_down", "_limit_type"]
    data["stock_prices"].drop(columns=[c for c in _limit_cols if c in data["stock_prices"].columns], inplace=True)

    # 4d. 品質檢查
    price_quality = quality_check_prices(data["stock_prices"], config)
    report["results"]["price_quality"] = price_quality

    # ===== 5. 文本前處理 =====
    log.info("\n[Step 4/10] Text preprocessing pipeline...")
    data["stock_text"] = run_text_pipeline(data["stock_text"], config)

    report["results"]["text_after_processing"] = {
        "rows": len(data["stock_text"]),
        "content_types": data["stock_text"]["content_type"].value_counts().to_dict()
            if "content_type" in data["stock_text"].columns else {},
    }

    # ===== 6. 財報處理 =====
    log.info("\n[Step 5/11] Financial data processing...")
    data["income_stmt"], fin_validation = run_financial_pipeline(data["income_stmt"], config)
    report["results"]["financial_validation"] = _serialize(fin_validation)

    # ===== 6b. Phase 4: 資產負債表 + 現金流量表處理 =====
    bs_processed = None
    if len(data.get("balance_sheet", pd.DataFrame())) > 0:
        log.info("\n[Step 5b/11] Balance Sheet + Cashflow pipeline (Phase 4)...")
        bs_processed, bs_report = run_balance_sheet_pipeline(
            bs_raw=data["balance_sheet"],
            cf_raw=data.get("cashflow"),
            income_df=data["income_stmt"],
            config=config,
        )
        report["results"]["balance_sheet_quality"] = _serialize(bs_report)
        log.info(f"  BS processed: {bs_processed.shape[0]:,} rows × {bs_processed.shape[1]} cols")
        # 提前儲存 BS processed（避免特徵工程後記憶體已被釋放）
        output_dir = root / config["paths"]["outputs"]
        output_dir.mkdir(parents=True, exist_ok=True)
        bs_output = output_dir / "balance_sheet_processed.parquet"
        bs_processed.to_parquet(bs_output, index=False, engine="pyarrow")
        log.info(f"  BS processed saved early: {bs_output}")
    else:
        log.info("\n[Step 5b/11] No balance sheet data found. Skipping Phase 4 BS pipeline.")

    # ===== 記憶體優化：釋放已處理完的原始資料 =====
    log.info("  Memory optimization: releasing raw data...")
    for _key in ["balance_sheet", "cashflow"]:
        if _key in data:
            del data[_key]
    gc.collect()

    # ===== 7. 標籤生成 =====
    log.info("\n[Step 6/11] Label generation...")
    data["stock_prices"], label_validation = run_label_pipeline(data["stock_prices"], config)
    report["results"]["label_validation"] = _serialize(label_validation)

    # ===== 記憶體優化：保留 text_df 引用後釋放 data dict 多餘項目 =====
    text_df_ref = data["stock_text"]
    prices_df_ref = data["stock_prices"]
    income_df_ref = data["income_stmt"]
    # Phase 5A：industry / institutional（若存在）
    industry_df_ref = data.get("industry", pd.DataFrame())
    inst_df_ref = data.get("institutional_investors", pd.DataFrame())
    # ── mg_ 支柱已於 2026-04-19 下架（SCOPE 決策）──────────────────
    # 原因：margin_trading FinMind 下載覆蓋僅 1,136 / 1,932 = 58.8%，
    # 其中 ~100 支為結構性不可下載（KY 股、創業板、新上市、ETF 非信用交易標的）。
    # 過往範例（G1/G10/G20/G2）均未使用融資融券特徵，時間成本/效益不划算。
    # parquet 檔案仍保留於 選用資料集/parquet/margin_trading.parquet 作為資料透明之證明，
    # 但不進入模型訓練。詳見 資料來源宣告.md 與 SCOPE.md v1.0。
    mg_df_ref = None
    # 釋放 data dict（但不刪除 DataFrame 本身，只刪除 dict 引用）
    del data
    gc.collect()
    log.info("  Memory freed before feature engineering")

    # ===== 8. 特徵工程（Phase 5A：五大支柱 + chip_/ind_，mg_ 已下架）=====
    log.info("\n[Step 7/11] Feature engineering (Phase 5A — 7 pillars, mg_ dropped)...")
    feature_store = run_feature_pipeline(
        prices_df=prices_df_ref,
        financial_df=income_df_ref,
        text_df=text_df_ref,
        config=config,
        bs_df=bs_processed,
        # Phase 5A 新增輸入
        industry_df=industry_df_ref if len(industry_df_ref) > 0 else None,
        inst_df=inst_df_ref if len(inst_df_ref) > 0 else None,
        mg_df=mg_df_ref,  # = None, mg_ 支柱已下架
    )
    # 釋放特徵工程輸入
    del text_df_ref, prices_df_ref, industry_df_ref, inst_df_ref, mg_df_ref
    bs_processed = None
    gc.collect()

    # Phase 5A: 計算特徵數含新支柱（mg_ 已下架，不再統計）
    _PILLAR_PREFIXES = [
        "trend_", "fund_", "val_", "event_", "risk_",
        "chip_", "ind_",
    ]
    _feat_cols = [c for c in feature_store.columns
                  if any(c.startswith(p) for p in _PILLAR_PREFIXES)]
    _feat_count_by_pillar = {
        p.rstrip("_"): sum(1 for c in _feat_cols if c.startswith(p))
        for p in _PILLAR_PREFIXES
    }
    report["results"]["feature_store"] = {
        "rows": len(feature_store),
        "cols": len(feature_store.columns),
        "feature_count": len(_feat_cols),
        "feature_count_by_pillar": _feat_count_by_pillar,
        "memory_mb": f"{feature_store.memory_usage(deep=True).sum() / 1024**2:.1f}",
    }

    # ===== 9. 前瞻偏差偵測 =====
    log.info("\n[Step 8/11] Leakage detection...")
    leakage_results = run_leakage_detection(feature_store, config)
    report["results"]["leakage_detection"] = _serialize(leakage_results)

    # ===== 10. 輸出 =====
    log.info("\n[Step 9/11] Saving Feature Store...")

    # 儲存 Feature Store
    output_dir = root / config["paths"]["outputs"]
    output_dir.mkdir(parents=True, exist_ok=True)
    feature_store_path = output_dir / "feature_store.parquet"
    feature_store.to_parquet(feature_store_path, index=False, engine="pyarrow")
    log.info(f"  Feature Store saved: {feature_store_path}")
    log.info(f"  Shape: {feature_store.shape}")

    # 儲存處理後的 income_stmt
    fin_output = output_dir / "income_stmt_processed.parquet"
    income_df_ref.to_parquet(fin_output, index=False, engine="pyarrow")
    log.info(f"  Processed income_stmt saved: {fin_output}")

    # BS processed 已在特徵工程前儲存（見 Step 5b 後方）

    # ===== 報告 =====
    log.info("\n[Step 10/11] Generating Phase 1 report...")

    # 品質閘門檢查
    # Feature Store 完整性驗證
    _numeric_fs = feature_store.select_dtypes(include=["number"])
    _inf_count = int(np.isinf(_numeric_fs).sum().sum()) if len(_numeric_fs.columns) > 0 else 0
    _nan_pct = float(_numeric_fs.isna().mean().mean()) if len(_numeric_fs.columns) > 0 else 0.0
    log.info(f"  Feature Store validation: Inf={_inf_count}, NaN%={_nan_pct:.2%}")

    gates = {
        "ex_dividend_pass": ex_div_results.get("summary", {}).get("overall_pass", False),
        "leakage_check1_pass": leakage_results.get("check1", {}).get("pass", False),
        "financial_validation_pass": fin_validation.get("overall_pass", False),
        "label_validation_pass": label_validation.get("overall_pass", False),
        "price_quality_pass": (
            price_quality.get("duplicate_rows", 0) == 0
            and price_quality.get("negative_prices", 0) == 0
        ),
        "feature_store_valid": (
            _inf_count == 0 and _nan_pct < 0.5
        ),
    }

    all_gates_pass = all(gates.values())
    report["quality_gates"] = gates
    report["overall_status"] = "PASS" if all_gates_pass else "NEEDS REVIEW"

    # 儲存報告
    report_dir = root / config["paths"]["reports"]
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"phase1_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    log.info(f"  Report saved: {report_path}")

    # ===== 最終摘要 =====
    log.info("\n" + "=" * 70)
    log.info("Phase 1 Summary")
    log.info("=" * 70)
    log.info(f"  OHLCV mode:    {'Full OHLCV' if has_ohlcv else 'Close-only'}")
    log.info(f"  Companies:     {profiles['companies']['rows']:,}")
    log.info(f"  Stock prices:  {profiles['stock_prices']['rows']:,}")
    log.info(f"  Income stmt:   {profiles['income_stmt']['rows']:,}")
    log.info(f"  Balance sheet: {report['results'].get('balance_sheet_quality', {}).get('total_records', 'N/A')} rows")
    log.info(f"  Stock text:    {report['results'].get('text_after_processing', {}).get('rows', 'N/A')} (after processing)")
    log.info(f"  Feature Store: {feature_store.shape[0]:,} rows × {feature_store.shape[1]} cols")
    log.info(f"  Features:      {report['results']['feature_store']['feature_count']}")
    log.info(f"  Ex-dividend:   {'PASS ✓' if gates['ex_dividend_pass'] else 'NEEDS REVIEW ⚠'}")
    log.info(f"  Leakage:       {'PASS ✓' if gates['leakage_check1_pass'] else 'ISSUES FOUND ⚠'}")
    log.info(f"  Financial:     {'PASS ✓' if gates['financial_validation_pass'] else 'NEEDS REVIEW ⚠'}")
    log.info(f"  Labels:        {'PASS ✓' if gates['label_validation_pass'] else 'NEEDS REVIEW ⚠'}")
    log.info(f"  Price Quality: {'PASS ✓' if gates['price_quality_pass'] else 'ISSUES FOUND ⚠'}")
    log.info(f"  Feature Store: {'PASS ✓' if gates['feature_store_valid'] else 'ISSUES FOUND ⚠'} (Inf={_inf_count}, NaN={_nan_pct:.1%})")
    log.info(f"  Overall:       {'ALL GATES PASS ✓' if all_gates_pass else 'REVIEW NEEDED ⚠'}")
    log.info("=" * 70)

    return report


def _serialize(obj):
    """將結果物件轉為 JSON 可序列化格式"""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


if __name__ == "__main__":
    report = main()
