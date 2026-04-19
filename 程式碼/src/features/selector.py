"""
特徵選擇模組 — Phase 2

三階段篩選流程：
  1. Mutual Information (MI) — 單變量相關性
  2. VIF (Variance Inflation Factor) — 多重共線性
  3. Cross-fold Stability — 跨 fold 重要性穩定度
"""

import gc
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
    """辨識特徵欄位（五大支柱 + Phase 5A 擴充支柱 + Phase 5B 文本支柱 prefix）。

    支柱列表：
      ① trend_ / ② fund_ / ③ val_ / ④ event_ / ⑤ risk_
      Phase 5A 新增：chip_ / mg_ / ind_
      Phase 5B 新增：txt_ / sent_ / topic_
      （mg_ 於 2026-04-19 停用，但保留 prefix 相容舊檔）
    """
    prefixes = (
        "trend_", "fund_", "val_", "event_", "risk_",
        "chip_", "mg_", "ind_",
        "txt_", "sent_", "topic_",
    )
    return [c for c in df.columns if c.startswith(prefixes)]


def prefilter_by_correlation(
    df: pd.DataFrame,
    feature_cols: list,
    train_idx: np.ndarray | None = None,
    corr_max: float = 0.95,
) -> list:
    """Phase 5A 新增：共線前置過濾

    在 VIF 迭代前先用簡單相關係數快速移除 |corr| > corr_max 的冗餘對。
    若兩特徵高度相關，保留 name 字典序較小的那個（可重現）。

    Args:
        df: 完整 DataFrame
        feature_cols: 候選特徵列
        train_idx: 訓練集索引
        corr_max: 相關係數絕對值上限，預設 0.95

    Returns:
        remaining_cols
    """
    if train_idx is None:
        raise ValueError(
            "train_idx is required for correlation prefilter to prevent leakage."
        )
    if len(feature_cols) < 2:
        return feature_cols

    subset = df.iloc[train_idx]
    sample_n = min(50_000, len(subset))
    X = subset[feature_cols].tail(sample_n).fillna(0)

    corr = X.corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))

    to_drop = set()
    for col in upper.columns:
        if col in to_drop:
            continue
        # 找出所有與 col 高相關的特徵
        dup = upper.index[upper[col] > corr_max].tolist()
        for d in dup:
            if d in to_drop:
                continue
            # 字典序較大者刪掉
            victim = max(col, d)
            to_drop.add(victim)

    remaining = [c for c in feature_cols if c not in to_drop]
    logger.info(
        f"  Corr prefilter: {len(remaining)}/{len(feature_cols)} features "
        f"(|corr| ≤ {corr_max}, dropped {len(to_drop)})"
    )
    return remaining


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
    train_idx: np.ndarray | None = None,
) -> tuple:
    """
    以 Mutual Information 篩選與目標最相關的特徵。

    Args:
        df: 完整 DataFrame
        label_col: 標籤欄位名稱
        feature_cols: 候選特徵欄位列表
        config: 設定字典
        train_idx: 訓練集索引（防止資料洩漏）。若提供，僅使用訓練集計算 MI。

    Returns:
        (selected_cols: list, mi_scores: pd.Series)
    """
    sel_cfg = config.get("features", {}).get("selection", {})
    threshold_pct = sel_cfg.get("mi_threshold_percentile", 25)
    # Phase 5B 新增：大量文本特徵時，用硬上限避免 VIF 階段爆炸
    mi_top_n = sel_cfg.get("mi_top_n", 150)
    # Phase 5B-fix：分層配額（per-pillar）— 防止 txt/sent 因數量壓制其他支柱
    pillar_quotas = sel_cfg.get("pillar_quotas")  # dict: prefix -> max_n

    # [D fix] 若未提供 train_idx，強制報錯防止資料洩漏
    if train_idx is None:
        raise ValueError(
            "train_idx is required for feature selection to prevent data leakage. "
            "Pass training fold indices explicitly."
        )
    subset = df.iloc[train_idx]
    logger.info(f"  MI: using training subset only ({len(subset):,} rows)")

    # 取樣以加速 — 使用時序尾段（保留時序結構，避免 random 破壞自相關）
    # 2026-04-19 14:30：原 100k 在 1540 features 下導致 9.7GB 峰值 + OOM；降至 50k → ~4GB 峰值
    sample_n = min(50_000, len(subset))
    sample = subset.tail(sample_n)

    # 明確對齊 X, y — 先建 valid mask 再切片
    valid_mask = sample[label_col].notna() & (~sample[feature_cols].isna().all(axis=1))
    sample = sample[valid_mask]

    # Phase 5B-fix: 轉 float32 降低記憶體；sklearn 內部會複製但峰值仍減半
    X = sample[feature_cols].fillna(0).astype(np.float32).values
    y = _encode_label(sample[label_col]).values.astype(int)

    # 釋放 sample DataFrame（X, y 已取到）
    del sample, valid_mask
    gc.collect()

    mi = mutual_info_classif(X, y, discrete_features=False, random_state=42, n_neighbors=5)
    mi_series = pd.Series(mi, index=feature_cols).sort_values(ascending=False)

    # 釋放 X, y
    del X, y, mi
    gc.collect()

    if pillar_quotas:
        # === 分層 MI 選擇：每個支柱依 MI 排名各取 quota 個 ===
        # 解決 Phase 5B 整合後 txt_(1521) 主導 top-150 → trend/fund 被擠出 → IC 崩潰問題
        selected = []
        per_pillar_log = []
        for prefix, quota in pillar_quotas.items():
            pillar_feats = [f for f in mi_series.index if f.startswith(prefix)]
            if not pillar_feats:
                continue
            top_picks = mi_series.loc[pillar_feats].head(quota).index.tolist()
            selected.extend(top_picks)
            per_pillar_log.append(
                f"{prefix}{len(top_picks)}/{len(pillar_feats)}(q{quota})"
            )
        # 收集未被任何 quota 覆蓋的特徵（保險：若 base.yaml 漏了某 prefix，不要全丟）
        covered_prefixes = tuple(pillar_quotas.keys())
        uncovered = [
            f for f in mi_series.index if not f.startswith(covered_prefixes)
        ]
        if uncovered:
            # 不在 quota 中的支柱 → 不選（明確意圖）
            logger.info(f"  MI stratified: {len(uncovered)} features in no-quota pillars (skipped)")
        # dedupe (防止 prefix 重疊；理論上不會發生)
        selected = list(dict.fromkeys(selected))
        logger.info(
            f"  MI stratified: {len(selected)}/{len(feature_cols)} features "
            f"(per-pillar quotas: {' '.join(per_pillar_log)})"
        )
    else:
        cutoff = np.percentile(mi, 100 - threshold_pct)
        selected = mi_series[mi_series >= cutoff].index.tolist()
        # Phase 5B：硬上限（防止特徵爆炸拖垮 VIF）
        if mi_top_n is not None and len(selected) > mi_top_n:
            selected = mi_series.head(mi_top_n).index.tolist()
            logger.info(
                f"  MI selection: {len(selected)}/{len(feature_cols)} features "
                f"(top {threshold_pct}% capped to top {mi_top_n})"
            )
        else:
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
    train_idx: np.ndarray | None = None,
) -> list:
    """
    迭代移除 VIF > 閾值的特徵，降低多重共線性。

    Args:
        df: 完整 DataFrame
        feature_cols: 候選特徵欄位列表
        config: 設定字典
        train_idx: 訓練集索引（防止資料洩漏）。若提供，僅使用訓練集計算 VIF。

    Returns:
        remaining_cols: list
    """
    vif_max = config.get("features", {}).get("selection", {}).get("vif_max", 10)
    min_features = config.get("features", {}).get("selection", {}).get(
        "rfecv_min_features", 30
    )

    # [D fix] 強制要求 train_idx
    if train_idx is None:
        raise ValueError(
            "train_idx is required for VIF calculation to prevent data leakage."
        )
    subset = df.iloc[train_idx]
    logger.info(f"  VIF: using training subset only ({len(subset):,} rows)")

    # 取樣加速（時序尾段）+ 標準化確保 VIF 數值穩定
    # 2026-04-19 14:30：VIF sample 50k → 30k（降低記憶體）。Stratified MI 後只剩 150 特徵，
    # 30k × 150 × 4 byte = 18 MB，足夠穩定計算 VIF。
    sample_n = min(30_000, len(subset))
    raw_sample = subset[feature_cols].tail(sample_n).fillna(0).astype(np.float32)
    scaler = StandardScaler()
    sample_scaled = pd.DataFrame(
        scaler.fit_transform(raw_sample).astype(np.float32),
        columns=feature_cols, index=raw_sample.index
    )
    del raw_sample
    gc.collect()

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
    train_idx: np.ndarray | None = None,
) -> dict:
    """
    特徵選擇主流程（MI → VIF）。

    Args:
        df: 完整 DataFrame
        label_col: 標籤欄位名稱
        config: 設定字典
        train_idx: 訓練集索引（防止資料洩漏）。
                   應傳入第一個 fold 的訓練集索引，確保特徵篩選
                   僅使用訓練資料，不會洩漏測試集統計量。

    Returns:
        dict with selected_features, mi_scores, etc.
    """
    feature_cols = _get_feature_cols(df)
    logger.info(f"Feature selection: {len(feature_cols)} candidate features")

    # Phase 5A 新增：Stage 0 相關係數前置過濾（可由 config 關閉）
    sel_cfg = config.get("features", {}).get("selection", {})
    corr_max = sel_cfg.get("corr_max_prefilter", 0.95)
    enable_corr = sel_cfg.get("enable_corr_prefilter", True)

    if enable_corr and len(feature_cols) > 1:
        corr_selected = prefilter_by_correlation(
            df, feature_cols, train_idx=train_idx, corr_max=corr_max
        )
    else:
        corr_selected = feature_cols

    # Stage 1: MI（僅使用訓練集）
    mi_selected, mi_scores = select_by_mutual_info(
        df, label_col, corr_selected, config, train_idx=train_idx
    )

    # Stage 2: VIF（僅使用訓練集）
    vif_selected = remove_high_vif(df, mi_selected, config, train_idx=train_idx)

    return {
        "all_features": feature_cols,
        "after_corr": corr_selected,
        "after_mi": mi_selected,
        "after_vif": vif_selected,
        "selected_features": vif_selected,
        "mi_scores": mi_scores.to_dict(),
        "n_selected": len(vif_selected),
        "n_candidates": len(feature_cols),
    }
