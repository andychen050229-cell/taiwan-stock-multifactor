"""
特徵選擇模組 — Phase 2

三階段篩選流程：
  1. Mutual Information (MI) — 單變量相關性
  2. VIF (Variance Inflation Factor) — 多重共線性
  3. Cross-fold Stability — 跨 fold 重要性穩定度
"""

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.feature_selection import mutual_info_classif
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor

from ..utils.helpers import timer


# ============================================================
# 工具函式
# ============================================================

def _get_feature_cols(df: pd.DataFrame) -> list:
    """辨識特徵欄位（以五大支柱 prefix 開頭）。"""
    prefixes = ("trend_", "fund_", "val_", "event_", "risk_")
    return [c for c in df.columns if c.startswith(prefixes)]


def _encode_label(y: pd.Series) -> pd.Series:
    """將 label (-1, 0, 1) 轉換為 (0, 1, 2)，供 sklearn 使用。"""
    mapping = {-1.0: 0, 0.0: 1, 1.0: 2, -1: 0, 0: 1, 1: 2}
    return y.map(mapping)


# ============================================================
# Stage 1: Mutual Information
# ============================================================

@timer
def select_by_mutual_info(
    df: pd.DataFrame,
    label_col: str,
    feature_cols: list,
    config: dict,
) -> tuple:
    """
    以 Mutual Information 篩選與目標最相關的特徵。

    Returns:
        (selected_cols: list, mi_scores: pd.Series)
    """
    threshold_pct = config.get("features", {}).get("selection", {}).get(
        "mi_threshold_percentile", 25
    )

    # 取樣以加速 — 使用時序尾段（保留時序結構，避免 random 破壞自相關）
    sample_n = min(100_000, len(df))
    sample = df.tail(sample_n)

    # 明確對齊 X, y — 先建 valid mask 再切片
    valid_mask = sample[label_col].notna() & (~sample[feature_cols].isna().all(axis=1))
    sample = sample[valid_mask]

    X = sample[feature_cols].fillna(0).values
    y = _encode_label(sample[label_col]).values.astype(int)

    mi = mutual_info_classif(X, y, discrete_features=False, random_state=42, n_neighbors=5)
    mi_series = pd.Series(mi, index=feature_cols).sort_values(ascending=False)

    cutoff = np.percentile(mi, 100 - threshold_pct)
    selected = mi_series[mi_series >= cutoff].index.tolist()

    logger.info(
        f"  MI selection: {len(selected)}/{len(feature_cols)} features "
        f"(top {threshold_pct}%, cutoff={cutoff:.4f})"
    )
    return selected, mi_series


# ============================================================
# Stage 2: VIF (Variance Inflation Factor)
# ============================================================

@timer
def remove_high_vif(
    df: pd.DataFrame,
    feature_cols: list,
    config: dict,
) -> list:
    """
    迭代移除 VIF > 閾值的特徵，降低多重共線性。

    Returns:
        remaining_cols: list
    """
    vif_max = config.get("features", {}).get("selection", {}).get("vif_max", 10)
    min_features = config.get("features", {}).get("selection", {}).get(
        "rfecv_min_features", 30
    )

    # 取樣加速（時序尾段）+ 標準化確保 VIF 數值穩定
    sample_n = min(50_000, len(df))
    raw_sample = df[feature_cols].tail(sample_n).fillna(0)
    scaler = StandardScaler()
    sample_scaled = pd.DataFrame(
        scaler.fit_transform(raw_sample), columns=feature_cols, index=raw_sample.index
    )

    remaining = list(feature_cols)
    max_iterations = len(remaining) - min_features

    for iteration in range(max_iterations):
        if len(remaining) <= min_features:
            break

        X = sample_scaled[remaining].values
        try:
            vifs = [variance_inflation_factor(X, i) for i in range(X.shape[1])]
        except Exception:
            logger.warning("  VIF computation failed, skipping VIF filter")
            break

        vif_series = pd.Series(vifs, index=remaining)
        worst = vif_series.idxmax()
        worst_val = vif_series.max()

        if worst_val <= vif_max:
            break

        remaining.remove(worst)
        if iteration < 3 or iteration % 5 == 0:
            logger.debug(f"  VIF iter {iteration}: dropped {worst} (VIF={worst_val:.1f})")

    logger.info(
        f"  VIF filter: {len(remaining)}/{len(feature_cols)} features "
        f"(threshold={vif_max})"
    )
    return remaining


# ============================================================
# Stage 3: Cross-fold Stability（在 walk-forward 後執行）
# ============================================================

def check_feature_stability(
    importance_per_fold: list,
    feature_cols: list,
    top_k: int = 20,
) -> dict:
    """
    檢查跨 fold 的特徵重要性穩定度。

    Args:
        importance_per_fold: list of dict {feature: importance}
        feature_cols: all feature column names
        top_k: 取前 K 重要特徵計算 overlap

    Returns:
        dict with stability metrics
    """
    if len(importance_per_fold) < 2:
        return {"stability_score": 1.0, "consistent_top_features": feature_cols[:top_k]}

    # 每個 fold 取 top_k
    top_sets = []
    for imp in importance_per_fold:
        sorted_feats = sorted(imp.items(), key=lambda x: x[1], reverse=True)
        top_sets.append(set([f for f, _ in sorted_feats[:top_k]]))

    # 計算兩兩 Jaccard
    jaccards = []
    for i in range(len(top_sets)):
        for j in range(i + 1, len(top_sets)):
            inter = len(top_sets[i] & top_sets[j])
            union = len(top_sets[i] | top_sets[j])
            jaccards.append(inter / union if union > 0 else 0)

    stability_score = np.mean(jaccards)

    # 取所有 fold 都出現的特徵
    consistent = set.intersection(*top_sets) if top_sets else set()

    logger.info(
        f"  Feature stability: Jaccard={stability_score:.3f} | "
        f"Consistent top-{top_k}: {len(consistent)} features"
    )

    return {
        "stability_score": round(stability_score, 4),
        "consistent_top_features": sorted(consistent),
        "pairwise_jaccards": [round(j, 4) for j in jaccards],
    }


# ============================================================
# 主流程
# ============================================================

@timer
def run_feature_selection(
    df: pd.DataFrame,
    label_col: str,
    config: dict,
) -> dict:
    """
    特徵選擇主流程（MI → VIF）。

    Returns:
        dict with selected_features, mi_scores, etc.
    """
    feature_cols = _get_feature_cols(df)
    logger.info(f"Feature selection: {len(feature_cols)} candidate features")

    # Stage 1: MI
    mi_selected, mi_scores = select_by_mutual_info(df, label_col, feature_cols, config)

    # Stage 2: VIF
    vif_selected = remove_high_vif(df, mi_selected, config)

    return {
        "all_features": feature_cols,
        "after_mi": mi_selected,
        "after_vif": vif_selected,
        "selected_features": vif_selected,
        "mi_scores": mi_scores.to_dict(),
        "n_selected": len(vif_selected),
        "n_candidates": len(feature_cols),
    }
