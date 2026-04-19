"""
信號衰減監控模組 — Phase 3

量化模型預測信號隨時間的衰減速度，判斷模型再訓練的頻率。

改善點（v2）：
  - 直接從 Feature Store 計算 monthly IC，取得 ~24 個月的時間序列
  - 以此進行真正的指數衰減擬合，產出有效的半衰期估算
  - 增加 monthly_ic_trends 欄位供 Dashboard 繪圖使用
"""

import numpy as np
import pandas as pd
from loguru import logger


def _compute_monthly_ic(
    df: pd.DataFrame,
    score_col: str,
    ret_col: str,
    date_col: str = "trade_date",
) -> list:
    """
    計算每月的 Rank IC（Spearman Correlation）。

    Args:
        df: Feature Store DataFrame
        score_col: 預測分數欄位（這裡用特徵作為代理）
        ret_col: 實際報酬或標籤欄位
        date_col: 日期欄位

    Returns:
        list of {"month": str, "ic": float, "n_samples": int}
    """
    sub = df[[date_col, score_col, ret_col]].dropna().copy()
    sub["month"] = pd.to_datetime(sub[date_col]).dt.to_period("M")

    monthly_ic = []
    for month, group in sub.groupby("month"):
        if len(group) < 30:
            continue
        ic = group[score_col].corr(group[ret_col], method="spearman")
        monthly_ic.append({
            "month": str(month),
            "ic": round(float(ic), 6) if pd.notna(ic) else 0,
            "n_samples": len(group),
        })

    return monthly_ic


def _estimate_half_life(ic_values: list) -> dict:
    """
    估算信號半衰期：IC 從峰值降至 50% 所需月數。

    使用指數衰減模型: IC(t) = IC_0 * exp(-λ * t)
    半衰期 = ln(2) / λ

    改善：放寬對「峰值後衰減」的嚴格要求，改用全序列的
    移動平均線性趨勢判斷。
    """
    if len(ic_values) < 6:
        return {
            "half_life_months": None,
            "decay_rate": None,
            "trend_direction": "insufficient_data",
            "note": "數據不足（需至少 6 個月）",
        }

    ic_arr = np.array([x["ic"] for x in ic_values])

    # 3 個月移動平均平滑
    kernel = np.ones(3) / 3
    smoothed = np.convolve(ic_arr, kernel, mode="valid")

    if len(smoothed) < 4:
        return {
            "half_life_months": None,
            "decay_rate": None,
            "trend_direction": "insufficient_smoothed",
            "note": "平滑後數據不足",
        }

    # 方法 1：全序列線性趨勢（判斷是否正在衰減）
    t_full = np.arange(len(smoothed))
    slope_full, intercept_full = np.polyfit(t_full, smoothed, 1)

    if slope_full > 0.001:
        trend = "improving"
        trend_note = "信號持續改善中，尚未出現衰減"
    elif slope_full < -0.001:
        trend = "decaying"
        trend_note = "信號呈衰減趨勢"
    else:
        trend = "stable"
        trend_note = "信號穩定，無明顯衰減或改善"

    # 方法 2：找峰值後的衰減段做指數擬合
    peak_idx = np.argmax(smoothed)
    decay_segment = smoothed[peak_idx:]

    half_life = None
    decay_rate = None

    if len(decay_segment) >= 3 and decay_segment[0] > 0:
        # 取正值做 log 回歸
        positive_mask = decay_segment > 0
        if positive_mask.sum() >= 3:
            t = np.arange(len(decay_segment))[positive_mask]
            log_ic = np.log(decay_segment[positive_mask])

            if len(t) >= 2 and not np.all(log_ic == log_ic[0]):
                slope, _ = np.polyfit(t, log_ic, 1)
                if slope < -0.001:
                    decay_rate = float(-slope)
                    half_life = float(np.log(2) / decay_rate)
                    trend_note = f"信號半衰期 ≈ {half_life:.1f} 個月"

    # 方法 3：若指數擬合失敗，用線性估算
    if half_life is None and trend == "decaying" and smoothed[0] > 0:
        # 線性外推：IC 從當前值降至一半的時間
        current_ic = smoothed[-1]
        initial_ic = smoothed[0]
        if initial_ic > 0 and current_ic > 0 and abs(slope_full) > 1e-6:
            half_target = initial_ic / 2
            months_to_half = (initial_ic - half_target) / abs(slope_full)
            if 0 < months_to_half < 120:  # 合理範圍
                half_life = float(months_to_half)
                decay_rate = float(np.log(2) / half_life) if half_life > 0 else None
                trend_note = f"線性估算半衰期 ≈ {half_life:.1f} 個月"

    return {
        "half_life_months": round(half_life, 1) if half_life else None,
        "decay_rate": round(decay_rate, 4) if decay_rate else None,
        "trend_direction": trend,
        "monthly_slope": round(float(slope_full), 6),
        "peak_month_idx": int(peak_idx),
        "n_months_analyzed": len(smoothed),
        "note": trend_note,
    }


def run_signal_decay_analysis(
    p2_report: dict,
    fs: pd.DataFrame,
    folds: list,
    selected_features: list,
    viable_horizons: list,
    config: dict,
) -> dict:
    """
    執行信號衰減分析。

    v2 改善：
      - 直接從 Feature Store 計算 monthly IC 時間序列
      - 對每個 horizon 的 Top 特徵做半衰期分析
      - 產出 monthly_ic_trends 供 Dashboard 繪圖

    Returns:
        dict with monthly IC trends, half-life estimates, retrain recommendation
    """
    logger.info("  Running signal decay analysis...")

    results = p2_report.get("results", {})
    alpha_decay = results.get("alpha_decay", {})

    # === Phase 2 已有的 Alpha Decay 結果 ===
    decay_from_p2 = {}
    for eng, metrics in alpha_decay.items():
        if isinstance(metrics, dict):
            for horizon_key, vals in metrics.items():
                if isinstance(vals, dict):
                    decay_from_p2[f"{eng}_{horizon_key}"] = {
                        "mean_ic": vals.get("mean_ic", 0),
                        "icir": vals.get("icir", 0),
                    }

    # === Phase 2 ICIR 結果 ===
    icir_data = results.get("icir", {})
    icir_summary = {}
    for key, vals in icir_data.items():
        if isinstance(vals, dict):
            icir_summary[key] = {
                "mean_ic": vals.get("mean_ic", 0),
                "icir": vals.get("icir", 0),
            }

    # === 信號穩定性評分（基於 ICIR）===
    signal_stability = {}
    for key, vals in icir_summary.items():
        icir = abs(vals.get("icir", 0))
        if icir > 0.5:
            stability = "strong"
        elif icir > 0.2:
            stability = "moderate"
        else:
            stability = "weak"
        signal_stability[key] = {
            "icir": vals.get("icir", 0),
            "stability": stability,
        }

    # === Monthly IC 時間序列（從 Feature Store 直接計算）===
    monthly_ic_trends = {}
    half_life_results = {}

    # 選出各 horizon 的 top-3 特徵做 IC 分析
    top_features_per_horizon = {}
    comparison = results.get("comparison", {})

    for h in viable_horizons:
        label_col = f"label_{h}"
        if label_col not in fs.columns:
            continue

        # 選出 ICIR 最高的引擎組合
        best_ic = 0
        best_key = None
        for key, vals in icir_summary.items():
            if f"D{h}" in key and abs(vals.get("icir", 0)) > abs(best_ic):
                best_ic = vals.get("icir", 0)
                best_key = key

        # 從特徵清單中選 top-3 IC 特徵
        feat_ics = []
        sample = fs.dropna(subset=[label_col]).head(200000)  # 效能取樣
        for feat in selected_features:
            if feat in sample.columns:
                ic = sample[feat].corr(sample[label_col], method="spearman")
                if pd.notna(ic):
                    feat_ics.append((feat, abs(float(ic))))

        feat_ics.sort(key=lambda x: x[1], reverse=True)
        top3 = [f for f, _ in feat_ics[:3]]
        top_features_per_horizon[f"D{h}"] = top3

        # 計算 monthly IC
        horizon_trends = {}
        for feat in top3:
            monthly = _compute_monthly_ic(fs, feat, label_col, "trade_date")
            if monthly:
                horizon_trends[feat] = monthly

        monthly_ic_trends[f"D{h}"] = horizon_trends

        # 半衰期分析：用 top-1 特徵的 monthly IC
        if top3 and top3[0] in horizon_trends:
            hl = _estimate_half_life(horizon_trends[top3[0]])
            half_life_results[f"D{h}"] = hl
            logger.info(f"  D+{h} half-life ({top3[0]}): {hl['note']}")
        else:
            half_life_results[f"D{h}"] = {
                "half_life_months": None,
                "decay_rate": None,
                "trend_direction": "no_data",
                "note": "無法取得足夠的月度 IC 資料",
            }

    # === 綜合判斷再訓練週期 ===
    strong_signals = sum(1 for v in signal_stability.values() if v["stability"] == "strong")
    moderate_signals = sum(1 for v in signal_stability.values() if v["stability"] == "moderate")
    weak_signals = sum(1 for v in signal_stability.values() if v["stability"] == "weak")

    # 結合 half-life 結果做更精確的建議
    min_half_life = None
    for hl_result in half_life_results.values():
        hl = hl_result.get("half_life_months")
        if hl is not None and (min_half_life is None or hl < min_half_life):
            min_half_life = hl

    # 決策邏輯：综合 ICIR 穩定性 + 半衰期 + 漂移
    if min_half_life is not None and min_half_life < 3:
        retrain_cycle = "1-2 個月（半衰期短）"
    elif weak_signals > strong_signals + moderate_signals:
        retrain_cycle = "1-2 個月（弱信號占多數）"
    elif min_half_life is not None and min_half_life < 6:
        retrain_cycle = "2-3 個月"
    elif strong_signals >= 3:
        retrain_cycle = "3-6 個月（信號穩定）"
    elif strong_signals >= 2:
        retrain_cycle = "2-3 個月"
    else:
        retrain_cycle = "1-2 個月"

    # === 彙整結果 ===
    result = {
        "analysis_date": pd.Timestamp.now().isoformat(),
        "alpha_decay_from_p2": decay_from_p2,
        "icir_summary": icir_summary,
        "signal_stability": signal_stability,
        "half_life_analysis": half_life_results,
        "monthly_ic_trends": {
            horizon: {
                feat: [{"month": m["month"], "ic": m["ic"]} for m in months]
                for feat, months in feats.items()
            }
            for horizon, feats in monthly_ic_trends.items()
        },
        "top_features_per_horizon": top_features_per_horizon,
        "min_half_life_months": round(min_half_life, 1) if min_half_life else None,
        "recommended_retrain_cycle": retrain_cycle,
        "summary": {
            "strong_signals": strong_signals,
            "moderate_signals": moderate_signals,
            "weak_signals": weak_signals,
            "best_signal": max(icir_summary.items(), key=lambda x: abs(x[1].get("icir", 0)))[0]
            if icir_summary else "N/A",
        },
    }

    logger.info(f"  Strong signals: {strong_signals} | Moderate: {moderate_signals} | Weak: {weak_signals}")
    logger.info(f"  Min half-life: {min_half_life} months")
    logger.info(f"  Recommended retrain: {retrain_cycle}")

    return result
