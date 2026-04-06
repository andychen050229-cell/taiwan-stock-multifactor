"""
概率校準模組 — Phase 2 補強

Platt Scaling（溫度校準）：
  多分類模型的預測概率通常未校準（overconfident），
  使用 CalibratedClassifierCV 對 OOF 預測進行事後校準，
  使預測概率更接近真實的類別機率。

為什麼重要：
  1. 決策引擎需要校準概率來設定閾值（例如 P(UP) > 60% 才建議買入）
  2. Ensemble 時，校準概率的平均比未校準的更可靠
  3. 提供 Brier Score / ECE 作為概率品質指標
"""

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.calibration import CalibratedClassifierCV
from sklearn.base import BaseEstimator, ClassifierMixin


class _PretrainedWrapper(BaseEstimator, ClassifierMixin):
    """
    包裝已訓練的模型，讓它符合 sklearn estimator 介面，
    以便傳入 CalibratedClassifierCV。
    """

    def __init__(self, model, classes):
        self.model = model
        self.classes_ = np.array(classes)

    def fit(self, X, y):
        # 已經訓練過了，不做事
        return self

    def predict_proba(self, X):
        return self.model.predict_proba(X)

    def predict(self, X):
        proba = self.predict_proba(X)
        return self.classes_[np.argmax(proba, axis=1)]

    def decision_function(self, X):
        return self.predict_proba(X)


def calibrate_probabilities(
    model,
    X_cal: np.ndarray,
    y_cal: np.ndarray,
    method: str = "sigmoid",
    classes: list = None,
) -> dict:
    """
    對已訓練模型進行 Platt Scaling 校準。

    Args:
        model: 已訓練的模型（需要 predict_proba 方法）
        X_cal: 校準用特徵（建議用 validation set，非 training set）
        y_cal: 校準用標籤 (0, 1, 2)
        method: 'sigmoid' (Platt) 或 'isotonic'
        classes: 類別列表，默認 [0, 1, 2]

    Returns:
        {
            'calibrated_model': CalibratedClassifierCV,
            'before_calibration': {'brier_score': float, 'ece': float},
            'after_calibration': {'brier_score': float, 'ece': float},
            'improvement': float,  # ECE 改善百分比
        }
    """
    if classes is None:
        classes = [0, 1, 2]

    # 移除 NaN
    valid = ~np.isnan(y_cal)
    if X_cal.ndim == 2:
        valid &= ~np.isnan(X_cal).any(axis=1)
    X_clean = X_cal[valid]
    y_clean = y_cal[valid].astype(int)

    if len(X_clean) < 50:
        logger.warning("  Calibration: insufficient samples, skipping")
        return {"error": "insufficient samples"}

    # 校準前的概率品質
    proba_before = model.predict_proba(X_clean)
    ece_before = _expected_calibration_error(y_clean, proba_before, n_bins=10)
    brier_before = _multiclass_brier_score(y_clean, proba_before, n_classes=len(classes))

    # Platt Scaling
    wrapper = _PretrainedWrapper(model, classes)

    try:
        calibrated = CalibratedClassifierCV(
            wrapper,
            method=method,
            cv="prefit",  # 使用已訓練的模型
        )
        calibrated.fit(X_clean, y_clean)
    except Exception as e:
        logger.warning(f"  Calibration failed: {e}")
        return {"error": str(e)}

    # 校準後的概率品質
    proba_after = calibrated.predict_proba(X_clean)
    ece_after = _expected_calibration_error(y_clean, proba_after, n_bins=10)
    brier_after = _multiclass_brier_score(y_clean, proba_after, n_classes=len(classes))

    improvement = (ece_before - ece_after) / ece_before * 100 if ece_before > 0 else 0

    logger.info(
        f"  Calibration ({method}): "
        f"ECE {ece_before:.4f} → {ece_after:.4f} ({improvement:+.1f}%) | "
        f"Brier {brier_before:.4f} → {brier_after:.4f}"
    )

    return {
        'calibrated_model': calibrated,
        'before_calibration': {
            'brier_score': round(brier_before, 4),
            'ece': round(ece_before, 4),
        },
        'after_calibration': {
            'brier_score': round(brier_after, 4),
            'ece': round(ece_after, 4),
        },
        'improvement_pct': round(improvement, 2),
    }


def calibrate_oof_predictions(
    oof_predictions: np.ndarray,
    oof_labels: np.ndarray,
    folds: list,
    method: str = "sigmoid",
) -> dict:
    """
    對 OOF 預測概率進行跨 fold 的 Platt Scaling 校準。

    不需要已訓練模型，直接校準概率矩陣。
    使用 Leave-One-Fold-Out 策略：用 N-1 折的 OOF 預測學習校準映射，
    然後應用到第 N 折。

    Args:
        oof_predictions: (n_samples, n_classes) 的 OOF 概率矩陣
        oof_labels: (n_samples,) 的標籤
        folds: Walk-forward fold 列表
        method: 'sigmoid' 或 'isotonic'

    Returns:
        {
            'calibrated_proba': np.ndarray,  # 校準後的概率矩陣
            'before_calibration': {'brier_score', 'ece'},
            'after_calibration': {'brier_score', 'ece'},
            'improvement_pct': float,
            'per_fold_ece': list,
        }
    """
    from sklearn.linear_model import LogisticRegression

    n_samples = len(oof_predictions)
    calibrated_proba = np.full_like(oof_predictions, np.nan)

    # 取得所有 test indices
    all_test_idx = np.concatenate([f.test_idx for f in folds])

    # 只看 OOF test 部分
    oof_test = oof_predictions[all_test_idx]
    labels_test = oof_labels[all_test_idx]

    # 移除 NaN
    valid = ~np.isnan(labels_test) & ~np.isnan(oof_test).any(axis=1)

    if valid.sum() < 100:
        logger.warning("  OOF calibration: insufficient valid samples")
        return {"error": "insufficient samples"}

    # 校準前指標
    ece_before = _expected_calibration_error(
        labels_test[valid].astype(int),
        oof_test[valid],
        n_bins=10,
    )
    brier_before = _multiclass_brier_score(
        labels_test[valid].astype(int),
        oof_test[valid],
        n_classes=oof_predictions.shape[1],
    )

    # Leave-One-Fold-Out 校準：用 N-1 折的 OOF 預測訓練 LR，應用到第 N 折
    # 這避免了 in-sample fitting 導致 ECE 偏樂觀的問題
    calibrated_full = np.full_like(oof_predictions, np.nan)
    per_fold_ece = []
    last_lr = None  # 保留最後一個 LR 供未來使用

    try:
        for hold_out_idx, hold_out_fold in enumerate(folds):
            # 訓練集 = 其他所有 fold 的 OOF 預測
            train_indices = []
            for i, f in enumerate(folds):
                if i != hold_out_idx:
                    train_indices.append(f.test_idx)
            if not train_indices:
                continue
            train_idx = np.concatenate(train_indices)

            # 只保留有效行（非 NaN 標籤和預測）
            tr_valid = (~np.isnan(oof_labels[train_idx]) &
                        ~np.isnan(oof_predictions[train_idx]).any(axis=1))
            X_tr = oof_predictions[train_idx[tr_valid]]
            y_tr = oof_labels[train_idx[tr_valid]].astype(int)

            if len(X_tr) < 50:
                logger.warning(f"  Fold {hold_out_idx}: insufficient cal train samples, skipping")
                continue

            lr = LogisticRegression(
                max_iter=1000,
                multi_class="multinomial",
                solver="lbfgs",
                C=1.0,
            )
            lr.fit(X_tr, y_tr)
            last_lr = lr

            # 預測 hold-out fold
            ho_idx = hold_out_fold.test_idx
            ho_valid = (~np.isnan(oof_labels[ho_idx]) &
                        ~np.isnan(oof_predictions[ho_idx]).any(axis=1))
            if ho_valid.sum() == 0:
                continue

            calibrated_full[ho_idx[ho_valid]] = lr.predict_proba(
                oof_predictions[ho_idx[ho_valid]]
            )

            # 逐 fold ECE
            fold_ece = _expected_calibration_error(
                oof_labels[ho_idx[ho_valid]].astype(int),
                calibrated_full[ho_idx[ho_valid]],
                n_bins=min(10, ho_valid.sum() // 5),
            )
            per_fold_ece.append(round(fold_ece, 4))

    except Exception as e:
        logger.warning(f"  OOF LOFO calibration failed: {e}")
        return {"error": str(e)}

    # 校準後的整體指標（只看有校準結果的部分）
    valid_indices = all_test_idx[valid]
    cal_valid = ~np.isnan(calibrated_full[valid_indices]).any(axis=1)
    if cal_valid.sum() < 20:
        logger.warning("  OOF calibration: too few calibrated samples")
        return {"error": "too few calibrated samples"}

    ece_after = _expected_calibration_error(
        labels_test[valid][cal_valid].astype(int),
        calibrated_full[valid_indices[cal_valid]],
        n_bins=10,
    )
    brier_after = _multiclass_brier_score(
        labels_test[valid][cal_valid].astype(int),
        calibrated_full[valid_indices[cal_valid]],
        n_classes=oof_predictions.shape[1],
    )
    improvement = (ece_before - ece_after) / ece_before * 100 if ece_before > 0 else 0

    logger.info(
        f"  OOF Platt Scaling (LOFO): "
        f"ECE {ece_before:.4f} → {ece_after:.4f} ({improvement:+.1f}%) | "
        f"Brier {brier_before:.4f} → {brier_after:.4f}"
    )

    return {
        'calibrated_proba': calibrated_full,
        'calibrator': last_lr,
        'before_calibration': {
            'brier_score': round(brier_before, 4),
            'ece': round(ece_before, 4),
        },
        'after_calibration': {
            'brier_score': round(brier_after, 4),
            'ece': round(ece_after, 4),
        },
        'improvement_pct': round(improvement, 2),
        'per_fold_ece': per_fold_ece,
    }


# ============================================================
# 輔助函數
# ============================================================

def _expected_calibration_error(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Expected Calibration Error (ECE)
    衡量預測概率與實際頻率之間的加權平均偏差。

    ECE = Σ (|B_m| / N) * |acc(B_m) - conf(B_m)|

    對多分類取各類別的平均 ECE。
    """
    n_classes = y_proba.shape[1]
    total_ece = 0.0

    for cls in range(n_classes):
        cls_proba = y_proba[:, cls]
        cls_true = (y_true == cls).astype(float)

        bins = np.linspace(0, 1, n_bins + 1)
        ece_cls = 0.0

        for i in range(n_bins):
            in_bin = (cls_proba > bins[i]) & (cls_proba <= bins[i + 1])
            if in_bin.sum() == 0:
                continue
            avg_confidence = cls_proba[in_bin].mean()
            avg_accuracy = cls_true[in_bin].mean()
            ece_cls += in_bin.sum() / len(y_true) * abs(avg_accuracy - avg_confidence)

        total_ece += ece_cls

    return total_ece / n_classes


def _multiclass_brier_score(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    n_classes: int = 3,
) -> float:
    """
    Multiclass Brier Score
    BS = (1/N) Σ Σ (p_ij - y_ij)²
    """
    one_hot = np.eye(n_classes)[y_true.astype(int)]
    return float(np.mean(np.sum((y_proba - one_hot) ** 2, axis=1)))
