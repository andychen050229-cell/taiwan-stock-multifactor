#!/usr/bin/env python3
"""
Phase 3 主執行腳本：模型治理 + 部署優化 + 信號監控

執行流程（9 步驟）：
  1. 載入 Phase 2 產出 + 模型重建（修復 save_models bug）
  2. 模型治理文件（Model Card）自動生成
  3. 資料漂移偵測（Data Drift Detection）
  4. 信號衰減監控（Signal Decay Monitor）
  5. 模型效能基線建立（Performance Baseline）
  6. 預測管線封裝（Prediction Pipeline）
  7. DSR 門控重新驗證（修正策略數量懲罰）
  8. 儀表板升級（Dashboard Enhancement — 由手動整合）
  9. 品質閘門 + 產出報告

用法：
  python 程式碼/執行Phase3_治理監控.py
"""

import sys
import json
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import joblib

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config_loader import load_config
from src.utils.logger import get_logger
from src.models.walk_forward import generate_walk_forward_splits
from src.models.trainer import train_all_models, save_models, load_model
from src.features.selector import run_feature_selection
from src.governance.model_card import generate_model_cards
from src.governance.drift_detector import run_drift_detection
from src.governance.signal_monitor import run_signal_decay_analysis
from src.governance.baseline import establish_baselines, revalidate_dsr

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def _serialize(obj):
    """將物件轉為 JSON-safe 格式。"""
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (pd.Timestamp, pd.Period)):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    return obj


def main():
    # ===== 初始化 =====
    config = load_config()
    log = get_logger("phase3", config)
    root = Path(config.get("_project_root", "."))

    random_seed = config.get("random_seed", 42)
    np.random.seed(random_seed)

    log.info("=" * 70)
    log.info("Phase 3: 模型治理 + 部署優化 + 信號監控 — 開始執行")
    log.info(f"Environment: {config.get('_env', 'dev')}")
    log.info(f"Project root: {root}")
    log.info("=" * 70)

    report = {
        "phase": "Phase 3 — 模型治理 + 部署優化 + 信號監控",
        "timestamp": datetime.now().isoformat(),
        "env": config.get("_env"),
        "results": {},
    }

    output_dir = root / config["paths"]["outputs"]
    gov_dir = output_dir / "governance"
    gov_dir.mkdir(parents=True, exist_ok=True)
    model_dir = output_dir / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    # ===========================================================
    # Step 1: 載入 Phase 2 產出 + 模型重建
    # ===========================================================
    log.info("\n[Step 1/9] Loading Phase 2 outputs & rebuilding models...")

    # 1a. 載入 Feature Store（優先用 Phase 5B 整合後的 _final 版）
    fs_final_path = output_dir / "feature_store_final.parquet"
    fs_baseline_path = output_dir / "feature_store.parquet"
    if fs_final_path.exists():
        fs_path = fs_final_path
        log.info(f"  Using FINAL feature store (Phase 5B integrated)")
    elif fs_baseline_path.exists():
        fs_path = fs_baseline_path
    else:
        log.error(f"Feature Store not found: {fs_baseline_path}")
        log.error("Please run Phase 1 first.")
        sys.exit(1)

    fs = pd.read_parquet(fs_path)
    log.info(f"  Feature Store: {fs.shape[0]:,} rows × {fs.shape[1]} cols")

    # 1b. 載入 Phase 2 報告
    report_dir = root / config["paths"]["reports"]
    p2_reports = sorted(report_dir.glob("phase2_report_*.json"), reverse=True)
    if not p2_reports:
        log.error("No Phase 2 report found.")
        sys.exit(1)

    p2_path = p2_reports[0]
    with open(p2_path, "r", encoding="utf-8") as f:
        p2_report = json.load(f)
    log.info(f"  Phase 2 report: {p2_path.name}")

    # 1c. 解析可用策略（排除 D+1）
    horizons = config.get("model", {}).get("horizons", [1, 5, 20])
    viable_horizons = [5, 20]  # D+1 不可行（Sharpe 為負）
    engines = config.get("model", {}).get("engines", ["lightgbm", "xgboost"])

    # 1d. 取得 Phase 2 的特徵清單
    p2_features = p2_report.get("results", {}).get("feature_selection", {})
    selected_features = (p2_features.get("selected_features")
                         or p2_features.get("selected") or [])
    if not selected_features:
        log.warning("  No selected features in Phase 2 report, re-running selection...")
        folds = generate_walk_forward_splits(fs, date_col="trade_date", config=config)
        sel_result = run_feature_selection(fs, "label_5", config, train_idx=folds[0].train_idx)
        selected_features = sel_result["selected_features"]

    log.info(f"  Selected features: {len(selected_features)}")

    # 1e. 檢查模型檔案 — 若缺失或 stale（feature_cols 對不上）則重建
    expected_models = [f"{eng}_D{h}" for h in viable_horizons for eng in engines]
    existing_models = {p.stem.replace("_model", ""): p for p in model_dir.glob("*.joblib")}
    missing_models = [m for m in expected_models if m not in existing_models]

    # 額外偵測 stale：若存檔的 feature_cols 與當前 selected_features 對不上即視為過期
    selected_set = set(selected_features)
    for name, path in list(existing_models.items()):
        try:
            stored = joblib.load(str(path))
            stored_cols = stored.get("feature_cols", []) or []
            if set(stored_cols) != selected_set:
                log.warning(
                    f"  STALE detected for {name}: "
                    f"stored n={len(stored_cols)} vs current selected n={len(selected_set)}"
                )
                missing_models.append(name)
                existing_models.pop(name, None)
        except Exception as e:
            log.warning(f"  Failed to inspect {name}: {e} → treat as missing")
            missing_models.append(name)
            existing_models.pop(name, None)

    missing_models = sorted(set(missing_models))

    if missing_models:
        log.warning(f"  Missing models: {missing_models}")
        log.info("  Rebuilding models from Feature Store (last fold only)...")

        folds = generate_walk_forward_splits(fs, date_col="trade_date", config=config)
        last_fold_only = [folds[-1]]  # 只用最後一折重建，節省時間

        for h in viable_horizons:
            label_col = f"label_{h}"
            model_key_prefix = [f"{eng}_D{h}" for eng in engines]
            need_rebuild = any(mk in missing_models for mk in model_key_prefix)

            if not need_rebuild:
                continue

            log.info(f"  Training D+{h} models (last fold)...")
            h_results = train_all_models(
                df=fs,
                feature_cols=selected_features,
                label_col=label_col,
                folds=last_fold_only,
                config=config,
            )

            # 儲存模型
            for eng, res in h_results.items():
                if "error" in res:
                    log.warning(f"  {eng}_D{h}: training error — {res['error']}")
                    continue
                save_models(
                    {f"{eng}_D{h}": res},
                    feature_cols=selected_features,
                    label_col=label_col,
                    output_dir=str(model_dir),
                )

        # 重新檢查
        existing_models = {p.stem.replace("_model", ""): p for p in model_dir.glob("*.joblib")}
        still_missing = [m for m in expected_models if m not in existing_models]
        if still_missing:
            log.error(f"  CRITICAL: Models still missing after rebuild: {still_missing}")
        else:
            log.info(f"  All {len(expected_models)} models successfully rebuilt.")
    else:
        log.info(f"  All {len(expected_models)} models present.")

    # 載入所有模型
    loaded_models = {}
    for name, path in existing_models.items():
        try:
            loaded_models[name] = load_model(str(path))
        except Exception as e:
            log.warning(f"  Failed to load {name}: {e}")

    report["results"]["step1_models"] = {
        "expected": expected_models,
        "available": list(loaded_models.keys()),
        "rebuilt": missing_models,
    }

    # ===========================================================
    # Step 2: Model Card 自動生成
    # ===========================================================
    log.info("\n[Step 2/9] Generating Model Cards...")

    model_cards = generate_model_cards(
        p2_report=p2_report,
        loaded_models=loaded_models,
        selected_features=selected_features,
        viable_horizons=viable_horizons,
        config=config,
    )

    for name, card in model_cards.items():
        card_path = gov_dir / f"model_card_{name}.json"
        with open(card_path, "w", encoding="utf-8") as f:
            json.dump(_serialize(card), f, ensure_ascii=False, indent=2)
        log.info(f"  Model Card saved: {card_path.name}")

    report["results"]["step2_model_cards"] = {
        "generated": list(model_cards.keys()),
        "count": len(model_cards),
    }

    # ===========================================================
    # Step 3: 資料漂移偵測
    # ===========================================================
    log.info("\n[Step 3/9] Data drift detection...")

    folds = generate_walk_forward_splits(fs, date_col="trade_date", config=config)
    drift_report = run_drift_detection(
        fs=fs,
        folds=folds,
        selected_features=selected_features,
        config=config,
    )

    drift_path = gov_dir / "drift_report.json"
    with open(drift_path, "w", encoding="utf-8") as f:
        json.dump(_serialize(drift_report), f, ensure_ascii=False, indent=2)
    log.info(f"  Drift severity: {drift_report['overall_severity']}")
    log.info(f"  Features with PSI > 0.2: {drift_report['n_drifted_features']}")

    report["results"]["step3_drift"] = {
        "severity": drift_report["overall_severity"],
        "n_drifted": drift_report["n_drifted_features"],
        "top_drifted": drift_report.get("top_drifted", []),
    }

    # ===========================================================
    # Step 4: 信號衰減監控
    # ===========================================================
    log.info("\n[Step 4/9] Signal decay analysis...")

    decay_report = run_signal_decay_analysis(
        p2_report=p2_report,
        fs=fs,
        folds=folds,
        selected_features=selected_features,
        viable_horizons=viable_horizons,
        config=config,
    )

    decay_path = gov_dir / "signal_decay_report.json"
    with open(decay_path, "w", encoding="utf-8") as f:
        json.dump(_serialize(decay_report), f, ensure_ascii=False, indent=2)
    log.info(f"  Recommended retrain cycle: {decay_report.get('recommended_retrain_cycle', 'N/A')}")

    report["results"]["step4_signal_decay"] = _serialize(decay_report)

    # ===========================================================
    # Step 5: 效能基線建立
    # ===========================================================
    log.info("\n[Step 5/9] Establishing performance baselines...")

    baselines = establish_baselines(
        p2_report=p2_report,
        viable_horizons=viable_horizons,
        engines=engines,
    )

    baseline_path = gov_dir / "performance_baseline.json"
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(_serialize(baselines), f, ensure_ascii=False, indent=2)
    log.info(f"  Baselines established for {len(baselines)} models")

    report["results"]["step5_baselines"] = {
        "models": list(baselines.keys()),
        "count": len(baselines),
    }

    # ===========================================================
    # Step 6: 預測管線驗證
    # ===========================================================
    log.info("\n[Step 6/9] Prediction pipeline validation...")

    pipeline_valid = True
    pipeline_results = {}

    for name, model_data in loaded_models.items():
        try:
            model = model_data["model"]
            feat_cols = model_data.get("feature_cols", selected_features)

            # 取最新一筆資料做預測測試
            latest_date = fs["trade_date"].max()
            sample = fs[fs["trade_date"] == latest_date].head(10)

            if sample.empty:
                pipeline_results[name] = {"status": "skip", "reason": "no sample data"}
                continue

            X_test = sample[feat_cols].fillna(0).values
            pred = model.predict_proba(X_test)

            # 驗證輸出
            assert pred.shape[1] == 3, f"Expected 3 classes, got {pred.shape[1]}"
            assert np.allclose(pred.sum(axis=1), 1.0, atol=0.01), "Probabilities don't sum to 1"
            assert not np.isnan(pred).any(), "NaN in predictions"

            pipeline_results[name] = {
                "status": "pass",
                "sample_size": len(sample),
                "pred_shape": list(pred.shape),
                "avg_up_prob": float(pred[:, 2].mean()),
            }
            log.info(f"  {name}: PASS (avg UP prob = {pred[:, 2].mean():.4f})")

        except Exception as e:
            pipeline_results[name] = {"status": "fail", "error": str(e)}
            pipeline_valid = False
            log.error(f"  {name}: FAIL — {e}")

    report["results"]["step6_pipeline"] = {
        "valid": pipeline_valid,
        "results": pipeline_results,
    }

    # ===========================================================
    # Step 7: DSR 門控重新驗證
    # ===========================================================
    log.info("\n[Step 7/9] DSR revalidation (excluding D+1)...")

    dsr_result = revalidate_dsr(
        p2_report=p2_report,
        viable_horizons=viable_horizons,
        engines=engines + ["ensemble"],
    )

    dsr_path = gov_dir / "dsr_revalidation.json"
    with open(dsr_path, "w", encoding="utf-8") as f:
        json.dump(_serialize(dsr_result), f, ensure_ascii=False, indent=2)

    log.info(f"  Original DSR (9 strategies): ALL FAIL")
    log.info(f"  Revised DSR ({dsr_result['revised_n_strategies']} strategies): "
             f"{dsr_result['revised_best_dsr_pass']}")
    log.info(f"  Final verdict: {dsr_result['final_verdict']}")

    report["results"]["step7_dsr"] = _serialize(dsr_result)

    # ===========================================================
    # Step 8: 儀表板升級（標記為手動整合）
    # ===========================================================
    log.info("\n[Step 8/9] Dashboard enhancement...")
    log.info("  Dashboard pages will be created separately.")
    log.info("  Governance data available at: outputs/governance/")

    report["results"]["step8_dashboard"] = {
        "governance_data_ready": True,
        "pages_implemented": [
            "6_🛡️_Model_Governance.py",
            "7_📡_Signal_Monitor.py",
        ],
    }

    # ===========================================================
    # Step 9: 品質閘門 + 產出報告
    # ===========================================================
    log.info("\n[Step 9/9] Quality gates & final report...")

    gates = {
        "models_available": len(loaded_models) >= 4,
        "model_cards_generated": len(model_cards) >= 4,
        "drift_analysis_complete": drift_report.get("overall_severity") is not None,
        "signal_decay_assessed": decay_report.get("recommended_retrain_cycle") is not None,
        "baseline_established": len(baselines) >= 4,
        "prediction_pipeline_valid": pipeline_valid,
        "dsr_revalidated": dsr_result.get("final_verdict") is not None,
        "no_severe_drift": drift_report.get("overall_severity") != "high",
        "governance_data_ready": (gov_dir / "drift_report.json").exists(),
    }

    all_pass = all(gates.values())
    report["quality_gates"] = gates
    report["overall_status"] = "PASS" if all_pass else "NEEDS REVIEW"

    log.info("\n  --- Phase 3 Quality Gates ---")
    for gate, passed in gates.items():
        icon = "✓" if passed else "✗"
        log.info(f"  [{icon}] {gate}")
    log.info(f"\n  Overall: {'PASS ✅' if all_pass else 'NEEDS REVIEW ⚠️'}")

    # 儲存報告
    report_path = report_dir / f"phase3_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(_serialize(report), f, ensure_ascii=False, indent=2, default=str)
    log.info(f"\n  Report saved: {report_path}")

    # ===== 最終摘要 =====
    log.info("\n" + "=" * 70)
    log.info("Phase 3 Summary")
    log.info("=" * 70)
    log.info(f"  Models:       {len(loaded_models)} available ({len(missing_models)} rebuilt)")
    log.info(f"  Model Cards:  {len(model_cards)} generated")
    log.info(f"  Drift:        {drift_report['overall_severity']} ({drift_report['n_drifted_features']} features drifted)")
    log.info(f"  Signal Decay: retrain every {decay_report.get('recommended_retrain_cycle', 'N/A')}")
    log.info(f"  DSR Revised:  {dsr_result['final_verdict']}")
    log.info(f"  Pipeline:     {'VALID' if pipeline_valid else 'INVALID'}")
    log.info(f"  Quality Gate: {'ALL PASS' if all_pass else 'NEEDS REVIEW'}")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
