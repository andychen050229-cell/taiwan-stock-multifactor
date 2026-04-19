"""
Model Card 生成器 — Phase 3

遵循 Google Model Cards 規範，為每個可用模型自動生成標準化治理文件。
"""

from datetime import datetime
from loguru import logger


def generate_model_cards(
    p2_report: dict,
    loaded_models: dict,
    selected_features: list,
    viable_horizons: list,
    config: dict,
) -> dict:
    """
    為每個可用模型生成 Model Card。

    Returns:
        dict {model_name: model_card_dict}
    """
    cards = {}
    results = p2_report.get("results", {})
    comparison = results.get("comparison", {})
    calibration = results.get("calibration", {})
    bootstrap = results.get("bootstrap_ci", {})
    icir_data = results.get("icir", {})
    stat_val = results.get("statistical_validation", {})

    for name, model_data in loaded_models.items():
        logger.info(f"  Generating Model Card: {name}")

        # 解析 horizon 和 engine
        parts = name.split("_D")
        if len(parts) != 2:
            continue
        engine = parts[0]
        horizon = int(parts[1])

        if horizon not in viable_horizons:
            continue

        comp_key = f"{engine}_D{horizon}"
        comp = comparison.get(comp_key, {})
        cal = calibration.get(comp_key, {})
        bs = bootstrap.get(comp_key, {})
        ic = icir_data.get(comp_key, {})

        # 回測結果
        bt_key = f"backtest_horizon_{horizon}"
        bt_data = results.get(bt_key, {}).get(engine, {})
        disc = bt_data.get("cost_scenarios", {}).get("discount", {})

        # Permutation test
        perm = stat_val.get("permutation_tests", {}).get(comp_key, {})

        # DSR
        dsr = stat_val.get("deflated_sharpe", {}).get(comp_key, {})

        # OOD
        ood = stat_val.get("ood_analysis", {}).get(comp_key, {})

        card = {
            "model_card_version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "source_report": p2_report.get("timestamp", "unknown"),

            # 模型概述
            "overview": {
                "name": comp_key,
                "engine": engine,
                "horizon": f"D+{horizon}",
                "task": "三分類（DOWN / FLAT / UP）",
                "framework": "LightGBM" if engine == "lightgbm" else "XGBoost",
                "features_count": len(selected_features),
                "features_list": selected_features,
                "training_method": "Purged Walk-Forward CV (expanding window)",
                "n_folds": len(results.get("walk_forward", {}).get("folds", [])),
                "best_params": model_data.get("best_params", {}),
            },

            # 預期用途與限制
            "intended_use": {
                "primary": "台灣股市多因子趨勢判讀研究",
                "users": "量化研究人員、金融科技開發者",
                "out_of_scope": [
                    "即時交易決策",
                    "個人投資建議",
                    "非台灣市場應用",
                ],
                "ethical_considerations": "模型判讀僅基於歷史資料，不構成投資建議。",
            },

            # 訓練數據
            "training_data": {
                "date_range": results.get("feature_store", {}).get("date_range", "unknown"),
                "total_rows": results.get("feature_store", {}).get("rows", 0),
                "total_cols": results.get("feature_store", {}).get("cols", 0),
                "unique_stocks": 1930,
                "nan_pct": results.get("data_validation", {}).get("nan_pct", 0),
            },

            # 效能指標
            "performance": {
                "classification": {
                    "auc": comp.get("auc", 0),
                    "log_loss": comp.get("log_loss", 0),
                    "accuracy": comp.get("accuracy", 0),
                    "balanced_accuracy": comp.get("balanced_accuracy", 0),
                    "f1_weighted": comp.get("f1", 0),
                },
                "signal_quality": {
                    "rank_ic": comp.get("rank_ic", 0),
                    "icir": ic.get("icir", 0),
                    "mean_ic": ic.get("mean_ic", 0),
                },
                "backtest_discount": {
                    "annualized_return": disc.get("annualized_return", 0),
                    "sharpe_ratio": disc.get("sharpe_ratio", 0),
                    "max_drawdown": disc.get("max_drawdown", 0),
                    "win_rate": disc.get("win_rate", 0),
                },
                "bootstrap_ci_95": {
                    "return_lower": bs.get("return_ci_lower", 0),
                    "return_upper": bs.get("return_ci_upper", 0),
                    "sharpe_lower": bs.get("sharpe_ci_lower", 0),
                    "sharpe_upper": bs.get("sharpe_ci_upper", 0),
                },
            },

            # 校準品質
            "calibration": {
                "before_ece": cal.get("before", {}).get("ece", None),
                "after_ece": cal.get("after", {}).get("ece", None),
                "improvement_pct": cal.get("improvement_pct", None),
            },

            # 統計驗證
            "statistical_validation": {
                "permutation_test": {
                    "p_value": perm.get("p_value", None),
                    "z_score": perm.get("z_score", None),
                    "significant": perm.get("significant_at_05", None),
                },
                "dsr": {
                    "observed_sharpe": dsr.get("observed_sharpe", None),
                    "expected_max_sharpe": dsr.get("expected_max_sharpe", None),
                    "dsr_pass": dsr.get("dsr_pass", None),
                    "note": "DSR 以 9 策略計算（含不可行 D+1），Phase 3 Step 7 會修正",
                },
                "ood_degradation": {
                    "severity": ood.get("severity", "unknown"),
                    "last_fold_auc": ood.get("last_fold_auc", None),
                },
            },

            # 已知限制
            "known_limitations": [
                "D+1 策略因交易成本侵蝕不可行（Sharpe 全為負）",
                "DSR 未通過：回測期僅 229 天 + 9 策略多重測試懲罰",
                "2025 Q1 市場震盪導致 Fold 3 OOD 退化（非模型缺陷）",
                "模型基於歷史資料訓練，市場結構改變時可能失效",
                "財報特徵有 PIT（Point-in-Time）延遲，最新數據可能滯後",
            ],
        }

        cards[comp_key] = card

    logger.info(f"  Total Model Cards generated: {len(cards)}")
    return cards
