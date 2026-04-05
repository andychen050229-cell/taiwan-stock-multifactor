"""
統計檢驗模組 — Phase 2 補強

包含：
  1. Permutation Test（排列檢定）— 驗證 AUC 不是隨機結果
  2. Deflated Sharpe Ratio (DSR) — 校正多重比較後的策略顯著性
  3. OOD 壓力測試（簡化版）— 分析最近一期退化原因
"""

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats


# ============================================================
# 1. Permutation Test（排列檢定）
# ============================================================

def permutation_test_auc(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    n_permutations: int = 1000,
    seed: int = 42,
) -> dict:
    """
    Permutation Test：打亂標籤 N 次，計算隨機 AUC 分佈，
    檢驗真實 AUC 是否顯著高於隨機。

    Args:
        y_true: 真實標籤 (0, 1, 2)
        y_proba: 模型預測概率 (n_samples, 3)
        n_permutations: 隨機排列次數
        seed: 隨機種子

    Returns:
        {
            'observed_auc': float,
            'permuted_aucs': list,
            'p_value': float,              # 右尾 p-value
            'mean_permuted_auc': float,
            'std_permuted_auc': float,
            'z_score': float,              # (observed - mean) / std
            'significant_at_05': bool,
            'significant_at_01': bool,
        }
    """
    from sklearn.metrics import roc_auc_score

    rng = np.random.RandomState(seed)

    # 移除 NaN
    valid = ~np.isnan(y_true) & ~np.isnan(y_proba).any(axis=1)
    y_true_clean = y_true[valid].astype(int)
    y_proba_clean = y_proba[valid]

    if len(y_true_clean) < 50:
        logger.warning("  Permutation test: insufficient samples")
        return {"error": "insufficient samples"}

    # 觀測 AUC
    try:
        observed_auc = roc_auc_score(
            y_true_clean, y_proba_clean, multi_class="ovr", average="macro"
        )
    except ValueError:
        return {"error": "AUC calculation failed"}

    # 排列檢定
    permuted_aucs = []
    for i in range(n_permutations):
        shuffled_labels = rng.permutation(y_true_clean)
        try:
            perm_auc = roc_auc_score(
                shuffled_labels, y_proba_clean, multi_class="ovr", average="macro"
            )
            permuted_aucs.append(perm_auc)
        except ValueError:
            continue

    permuted_aucs = np.array(permuted_aucs)

    if len(permuted_aucs) == 0:
        return {"error": "all permutations failed"}

    # p-value：隨機 AUC ≥ 觀測 AUC 的比例
    p_value = float(np.mean(permuted_aucs >= observed_auc))

    mean_perm = float(permuted_aucs.mean())
    std_perm = float(permuted_aucs.std())
    z_score = (observed_auc - mean_perm) / std_perm if std_perm > 0 else 0.0

    result = {
        'observed_auc': round(observed_auc, 4),
        'permuted_aucs': permuted_aucs.tolist(),
        'p_value': round(p_value, 4),
        'mean_permuted_auc': round(mean_perm, 4),
        'std_permuted_auc': round(std_perm, 4),
        'z_score': round(z_score, 2),
        'significant_at_05': p_value < 0.05,
        'significant_at_01': p_value < 0.01,
    }

    logger.info(
        f"  Permutation test: observed AUC={observed_auc:.4f} | "
        f"permuted mean={mean_perm:.4f}±{std_perm:.4f} | "
        f"p={p_value:.4f} | z={z_score:.2f}"
    )

    return result


# ============================================================
# 2. Deflated Sharpe Ratio (DSR)
# ============================================================

def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_strategies: int,
    n_trading_days: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> dict:
    """
    Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014)

    校正多重比較偏差：從 N 個策略中挑出 Sharpe 最高的，
    計算此 Sharpe 在 N 次獨立測試下仍然顯著的概率。

    公式：
      E[max(SR)] ≈ (1 - γ) * Φ⁻¹(1 - 1/N) + γ * Φ⁻¹(1 - 1/N·e)
      其中 γ ≈ 0.5772（Euler-Mascheroni constant）

      DSR = Φ( (SR_observed - E[max(SR)]) / σ̂_SR )
      其中 σ̂_SR = sqrt( (1 - γ₃·SR + (γ₄-1)/4·SR²) / (T-1) )

    Args:
        observed_sharpe: 觀測到的最佳策略 Sharpe Ratio（年化）
        n_strategies: 測試的策略總數
        n_trading_days: 測試期交易日數
        skewness: 報酬分配的偏態（默認 0 = 常態）
        kurtosis: 報酬分配的峰態（默認 3 = 常態）

    Returns:
        {
            'observed_sharpe': float,
            'expected_max_sharpe': float,  # 隨機下的最大 Sharpe 期望值
            'sharpe_std_error': float,
            'dsr_statistic': float,        # z-score
            'dsr_p_value': float,          # 右尾 p-value
            'dsr_pass': bool,              # p < 0.05
        }
    """
    if n_strategies < 1 or n_trading_days < 2:
        return {"error": "invalid parameters"}

    gamma = 0.5772156649  # Euler-Mascheroni constant

    # E[max(SR)] under null (all strategies have SR=0)
    # 使用 Bonferroni-like expected maximum from N independent draws
    if n_strategies == 1:
        expected_max_sr = 0.0
    else:
        z_n = stats.norm.ppf(1 - 1 / n_strategies)
        z_ne = stats.norm.ppf(1 - 1 / (n_strategies * np.e))
        expected_max_sr = (1 - gamma) * z_n + gamma * z_ne

    # 將年化 Sharpe 轉換為日 Sharpe（因為 T 是日數）
    sr_daily = observed_sharpe / np.sqrt(252)

    # Standard error of Sharpe Ratio estimator
    # σ̂(SR) = sqrt( (1 - skew*SR + (kurt-1)/4 * SR²) / (T-1) )
    sr_var_numer = 1 - skewness * sr_daily + (kurtosis - 1) / 4 * sr_daily ** 2
    sr_se = np.sqrt(max(sr_var_numer, 0.01) / max(n_trading_days - 1, 1))

    # DSR 統計量：觀測 SR 是否顯著高於多重比較下的期望最大 SR
    # Bailey & Lopez de Prado (2014) 公式：
    #   E[max(SR)] = σ̂(SR) × [(1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(Ne))]
    #   DSR = Φ( (SR_observed - E[max(SR)]) / σ̂(SR) )
    # expected_max_sr 是 z-score，需乘以 sr_se 轉為 SR 單位
    expected_max_sr_value = expected_max_sr * sr_se  # 轉為 daily SR 單位
    dsr_z = (sr_daily - expected_max_sr_value) / sr_se if sr_se > 0 else 0.0
    dsr_p = 1 - stats.norm.cdf(dsr_z)

    # 轉回年化方便閱讀
    expected_max_annual = expected_max_sr_value * np.sqrt(252)

    result = {
        'observed_sharpe': round(observed_sharpe, 4),
        'n_strategies': n_strategies,
        'n_trading_days': n_trading_days,
        'expected_max_sharpe': round(expected_max_annual, 4),
        'sharpe_std_error': round(sr_se * np.sqrt(252), 4),
        'dsr_statistic': round(dsr_z, 4),
        'dsr_p_value': round(dsr_p, 4),
        'dsr_pass': bool(dsr_p < 0.05),
    }

    logger.info(
        f"  DSR: observed Sharpe={observed_sharpe:.4f} | "
        f"E[max]={expected_max_annual:.4f} | "
        f"z={dsr_z:.4f} | p={dsr_p:.4f} | "
        f"{'PASS' if dsr_p < 0.05 else 'FAIL'}"
    )

    return result


# ============================================================
# 3. OOD 壓力測試（簡化版）
# ============================================================

def ood_fold_analysis(
    df: pd.DataFrame,
    model_results: dict,
    folds: list,
    feature_cols: list,
    label_col: str,
    fwd_ret_col: str,
    config: dict,
) -> dict:
    """
    OOD 壓力測試（簡化版）：逐 fold 分析模型表現，
    特別檢查最新 fold 是否出現退化，並診斷原因。

    分析內容：
      1. 逐 fold AUC 趨勢
      2. 最新 fold vs 歷史 fold 差異
      3. 特徵重要性漂移（最新 fold vs 平均）
      4. 市場 regime 差異（波動率、報酬率分佈）
      5. 標籤分佈變化

    Returns:
        {
            'fold_trend': [{'fold_id': int, 'auc': float, ...}, ...],
            'degradation_detected': bool,
            'degradation_severity': str,  # 'none' | 'mild' | 'severe'
            'regime_analysis': {...},
            'feature_drift': {...},
            'diagnosis': str,
        }
    """
    from sklearn.metrics import roc_auc_score

    results = {
        'fold_trend': [],
        'degradation_detected': False,
        'degradation_severity': 'none',
        'regime_analysis': {},
        'feature_drift': {},
        'diagnosis': '',
    }

    if not folds:
        return results

    # --- 1. 逐 fold 分析 ---
    fold_details = []
    for fold in folds:
        test_df = df.iloc[fold.test_idx].copy()
        dates = test_df['trade_date'] if 'trade_date' in test_df.columns else None

        fold_info = {
            'fold_id': fold.fold_id,
            'n_test': len(test_df),
        }

        if dates is not None:
            fold_info['test_start'] = str(dates.min())
            fold_info['test_end'] = str(dates.max())

        # 標籤分佈
        if label_col in test_df.columns:
            label_dist = test_df[label_col].value_counts(normalize=True).to_dict()
            fold_info['label_distribution'] = {
                str(k): round(v, 3) for k, v in label_dist.items()
            }

        # 市場 regime 指標
        if 'trend_volatility_20' in test_df.columns:
            fold_info['avg_volatility_20'] = round(
                float(test_df['trend_volatility_20'].mean()), 4
            )
        if fwd_ret_col in test_df.columns:
            fold_info['avg_fwd_return'] = round(
                float(test_df[fwd_ret_col].mean()), 6
            )
            fold_info['fwd_return_std'] = round(
                float(test_df[fwd_ret_col].std()), 6
            )
        if 'risk_market_ret_20d' in test_df.columns:
            fold_info['avg_market_ret'] = round(
                float(test_df['risk_market_ret_20d'].mean()), 4
            )

        fold_details.append(fold_info)

    # --- 2. 從 model_results 取得 per-fold AUC ---
    for engine_name, engine_result in model_results.items():
        if 'error' in engine_result or engine_name == 'ensemble':
            continue

        fold_metrics = engine_result.get('fold_metrics', [])
        importance_per_fold = engine_result.get('importance_per_fold', [])

        for i, fm in enumerate(fold_metrics):
            if i < len(fold_details):
                key = f'auc_{engine_name}'
                fold_details[i][key] = fm.get('auc', 0)

        # --- 3. 特徵重要性漂移 ---
        if len(importance_per_fold) >= 2:
            # 計算平均重要性（排除最後一折）
            avg_imp = {}
            for feat in feature_cols:
                vals = [imp.get(feat, 0) for imp in importance_per_fold[:-1]]
                avg_imp[feat] = np.mean(vals) if vals else 0

            # 最後一折的重要性
            last_imp = importance_per_fold[-1]

            # 計算漂移
            drift = {}
            for feat in feature_cols:
                avg_v = avg_imp.get(feat, 0)
                last_v = last_imp.get(feat, 0)
                if avg_v > 0:
                    change_pct = (last_v - avg_v) / avg_v
                else:
                    change_pct = 0
                drift[feat] = round(change_pct, 3)

            # 排序：變化最大的前 10
            sorted_drift = sorted(drift.items(), key=lambda x: abs(x[1]), reverse=True)
            results['feature_drift'] = {
                'engine': engine_name,
                'top_drifted_features': dict(sorted_drift[:10]),
                'avg_abs_drift': round(np.mean([abs(v) for v in drift.values()]), 3),
            }

    results['fold_trend'] = fold_details

    # --- 4. 退化檢測 ---
    # 收集所有引擎的最後 fold AUC vs 平均
    auc_keys = [k for k in fold_details[0].keys() if k.startswith('auc_')]
    for auc_key in auc_keys:
        aucs = [fd.get(auc_key, 0) for fd in fold_details if auc_key in fd]
        if len(aucs) >= 2:
            last_auc = aucs[-1]
            prev_avg = np.mean(aucs[:-1])
            drop = prev_avg - last_auc

            if drop > 0.03:
                results['degradation_detected'] = True
                results['degradation_severity'] = 'severe'
            elif drop > 0.015:
                results['degradation_detected'] = True
                if results['degradation_severity'] != 'severe':
                    results['degradation_severity'] = 'mild'

    # --- 5. 診斷 ---
    diagnosis_parts = []

    if results['degradation_detected']:
        # 檢查是否為 regime 變化
        if len(fold_details) >= 2:
            last_vol = fold_details[-1].get('avg_volatility_20', 0)
            prev_vols = [fd.get('avg_volatility_20', 0) for fd in fold_details[:-1]]
            avg_prev_vol = np.mean(prev_vols) if prev_vols else 0

            if last_vol > 0 and avg_prev_vol > 0:
                vol_change = (last_vol - avg_prev_vol) / avg_prev_vol
                if abs(vol_change) > 0.2:
                    diagnosis_parts.append(
                        f"波動率 regime 變化 ({vol_change:+.1%})，"
                        f"最新期波動率={last_vol:.4f} vs 歷史均值={avg_prev_vol:.4f}"
                    )

            last_ret = fold_details[-1].get('avg_market_ret', 0)
            prev_rets = [fd.get('avg_market_ret', 0) for fd in fold_details[:-1]]
            avg_prev_ret = np.mean(prev_rets) if prev_rets else 0

            if abs(last_ret - avg_prev_ret) > 0.02:
                diagnosis_parts.append(
                    f"市場報酬 regime 變化：最新期={last_ret:.4f} vs 歷史={avg_prev_ret:.4f}"
                )

        # 檢查特徵漂移
        avg_drift = results.get('feature_drift', {}).get('avg_abs_drift', 0)
        if avg_drift > 0.3:
            diagnosis_parts.append(f"特徵重要性漂移較大（平均變化 {avg_drift:.1%}），模型可能需要重訓")

        if not diagnosis_parts:
            diagnosis_parts.append("退化原因不明，建議檢查個別特徵在最新期間的分佈")
    else:
        diagnosis_parts.append("未偵測到顯著退化，模型穩定性良好")

    results['diagnosis'] = "；".join(diagnosis_parts)

    logger.info(f"  OOD analysis: degradation={'YES' if results['degradation_detected'] else 'NO'} "
                f"({results['degradation_severity']})")
    logger.info(f"  Diagnosis: {results['diagnosis']}")

    return results


# ============================================================
# 4. 綜合統計驗證報告
# ============================================================

def run_statistical_validation(
    all_horizon_results: dict,
    all_backtest_results: dict,
    folds: list,
    df: pd.DataFrame,
    feature_cols: list,
    config: dict,
) -> dict:
    """
    執行完整的統計驗證流程。

    Returns:
        {
            'permutation_tests': {engine_horizon: result, ...},
            'deflated_sharpe': {engine_horizon: result, ...},
            'ood_analysis': {horizon: result, ...},
            'overall_validity': str,
        }
    """
    horizons = config.get("model", {}).get("horizons", [1, 5, 20])
    results = {
        'permutation_tests': {},
        'deflated_sharpe': {},
        'ood_analysis': {},
        'overall_validity': 'PENDING',
    }

    # --- Permutation Tests ---
    logger.info("\n  --- Permutation Tests ---")
    for h in horizons:
        for eng, res in all_horizon_results.get(h, {}).items():
            if 'error' in res or res.get('oof_predictions') is None:
                continue

            oof = res['oof_predictions']
            labels = res['oof_labels']

            # 只取 OOF test 資料
            test_idx = np.concatenate([f.test_idx for f in folds])
            y_true = labels[test_idx]
            y_proba = oof[test_idx]

            valid = ~np.isnan(y_true) & ~np.isnan(y_proba).any(axis=1)
            key = f"{eng}_D{h}"
            logger.info(f"\n  {key}:")

            perm_result = permutation_test_auc(
                y_true[valid], y_proba[valid],
                n_permutations=1000,
                seed=42,
            )
            results['permutation_tests'][key] = {
                k: v for k, v in perm_result.items()
                if k != 'permuted_aucs'  # 不存完整 array
            }

    # --- Deflated Sharpe Ratio ---
    logger.info("\n  --- Deflated Sharpe Ratio ---")
    # 計算所有策略數量（engines × horizons）
    engines = config.get("model", {}).get("engines", ["lightgbm", "xgboost"])
    n_strategies = len(engines) * len(horizons)  # 不含 ensemble
    if n_strategies < 1:
        n_strategies = 1

    for h in horizons:
        for eng, bt_res in all_backtest_results.get(h, {}).items():
            disc = bt_res.get('cost_scenarios', {}).get('discount', {})
            if not disc:
                continue

            sharpe = disc.get('sharpe_ratio', 0)
            n_days = bt_res.get('n_trading_days', 232)

            # 從日報酬估算偏態和峰態
            daily_returns = bt_res.get('daily_returns')
            skew = 0.0
            kurt = 3.0
            if daily_returns is not None and len(daily_returns) > 10:
                skew = float(daily_returns.skew())
                kurt = float(daily_returns.kurtosis() + 3)  # scipy kurtosis is excess

            key = f"{eng}_D{h}"
            logger.info(f"\n  {key}:")

            dsr_result = deflated_sharpe_ratio(
                observed_sharpe=sharpe,
                n_strategies=n_strategies,
                n_trading_days=n_days,
                skewness=skew,
                kurtosis=kurt,
            )
            results['deflated_sharpe'][key] = dsr_result

    # --- OOD Fold Analysis ---
    logger.info("\n  --- OOD Fold Analysis ---")
    for h in horizons:
        label_col = f"label_{h}"
        fwd_ret_col = f"fwd_ret_{h}"
        logger.info(f"\n  Horizon D+{h}:")

        ood_result = ood_fold_analysis(
            df=df,
            model_results=all_horizon_results.get(h, {}),
            folds=folds,
            feature_cols=feature_cols,
            label_col=label_col,
            fwd_ret_col=fwd_ret_col,
            config=config,
        )
        results['ood_analysis'][f"D{h}"] = ood_result

    # --- Overall Validity ---
    all_perm_pass = all(
        r.get('significant_at_05', False)
        for r in results['permutation_tests'].values()
        if 'error' not in r
    )
    any_dsr_pass = any(
        r.get('dsr_pass', False)
        for r in results['deflated_sharpe'].values()
        if 'error' not in r
    )
    no_severe_degradation = not any(
        r.get('degradation_severity') == 'severe'
        for r in results['ood_analysis'].values()
    )

    if all_perm_pass and any_dsr_pass and no_severe_degradation:
        results['overall_validity'] = 'STRONG'
    elif all_perm_pass and no_severe_degradation:
        results['overall_validity'] = 'MODERATE'
    elif all_perm_pass:
        results['overall_validity'] = 'WEAK'
    else:
        results['overall_validity'] = 'INSUFFICIENT'

    logger.info(f"\n  Overall statistical validity: {results['overall_validity']}")

    return results
