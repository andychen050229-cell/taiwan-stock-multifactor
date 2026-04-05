"""
模型訓練模組 — Phase 2

支援引擎：
  - LightGBM (multiclass)
  - XGBoost (multiclass)

流程：
  1. Walk-forward fold 切分
  2. 每個 fold: train → predict (OOF)
  3. Optuna 超參數優化（optional）
  4. 彙整 OOF 預測與特徵重要性
"""

import numpy as np
import pandas as pd
from loguru import logger
from pathlib import Path
import warnings
import json
import joblib

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False
    logger.warning("lightgbm not installed, LightGBM models will be skipped")

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    logger.warning("xgboost not installed, XGBoost models will be skipped")

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False

from sklearn.metrics import (
    log_loss, accuracy_score, roc_auc_score,
    classification_report, f1_score, balanced_accuracy_score,
)

from ..utils.helpers import timer


# ============================================================
# 標籤轉換
# ============================================================

def _encode_labels(y: pd.Series) -> np.ndarray:
    """將 label (-1, 0, 1) → (0, 1, 2)。"""
    mapping = {-1.0: 0, -1: 0, 0.0: 1, 0: 1, 1.0: 2, 1: 2}
    return y.map(mapping).values


def _decode_labels(y: np.ndarray) -> np.ndarray:
    """將 (0, 1, 2) → (-1, 0, 1)。"""
    mapping = {0: -1, 1: 0, 2: 1}
    return np.vectorize(mapping.get)(y)


# ============================================================
# 模型工廠
# ============================================================

def _build_lgb_model(params: dict, config: dict):
    """建立 LightGBM 分類器。"""
    model_cfg = config.get("model", {}).get("lightgbm", {})
    merged = {**model_cfg, **params}
    # 移除非 lgb 參數
    for k in ["objective", "metric", "num_class"]:
        merged.pop(k, None)
    return lgb.LGBMClassifier(
        objective="multiclass",
        num_class=3,
        **merged,
    )


def _build_xgb_model(params: dict, config: dict):
    """建立 XGBoost 分類器。"""
    model_cfg = config.get("model", {}).get("xgboost", {})
    merged = {**model_cfg, **params}
    for k in ["objective", "eval_metric", "num_class"]:
        merged.pop(k, None)
    return xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        use_label_encoder=False,
        **merged,
    )


# ============================================================
# Optuna 超參數搜尋
# ============================================================

def _optuna_lgb_objective(trial, X_train, y_train, X_val, y_val):
    """LightGBM 的 Optuna 目標函式。"""
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 800),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 15, 127),
        "max_depth": trial.suggest_int("max_depth", 4, 10),
        "min_child_samples": trial.suggest_int("min_child_samples", 20, 200),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
    }
    model = lgb.LGBMClassifier(
        objective="multiclass", num_class=3, verbosity=-1, **params,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )
    pred_proba = model.predict_proba(X_val)
    return log_loss(y_val, pred_proba)


def _optuna_xgb_objective(trial, X_train, y_train, X_val, y_val):
    """XGBoost 的 Optuna 目標函式。"""
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 800),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "min_child_weight": trial.suggest_int("min_child_weight", 20, 200),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
    }
    model = xgb.XGBClassifier(
        objective="multi:softprob", num_class=3,
        eval_metric="mlogloss", verbosity=0,
        use_label_encoder=False, early_stopping_rounds=50,
        **params,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    pred_proba = model.predict_proba(X_val)
    return log_loss(y_val, pred_proba)


@timer
def run_optuna_search(
    engine: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    config: dict,
) -> dict:
    """執行 Optuna 超參數搜尋。"""
    if not HAS_OPTUNA:
        logger.warning("  Optuna not available, using default params")
        return {}

    optuna_cfg = config.get("model", {}).get("optuna", {})
    n_trials = optuna_cfg.get("n_trials", 50)
    timeout = optuna_cfg.get("timeout", 600)

    if engine == "lightgbm":
        objective_fn = lambda trial: _optuna_lgb_objective(
            trial, X_train, y_train, X_val, y_val
        )
    else:
        objective_fn = lambda trial: _optuna_xgb_objective(
            trial, X_train, y_train, X_val, y_val
        )

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective_fn, n_trials=n_trials, timeout=timeout, show_progress_bar=False)

    logger.info(
        f"  Optuna {engine}: best logloss={study.best_value:.4f} "
        f"({study.best_trial.number + 1}/{len(study.trials)} trials)"
    )
    return study.best_params


# ============================================================
# 單引擎訓練
# ============================================================

@timer
def train_single_engine(
    engine: str,
    df: pd.DataFrame,
    feature_cols: list,
    label_col: str,
    folds: list,
    config: dict,
    do_optuna: bool = True,
) -> dict:
    """
    對單一引擎（LightGBM 或 XGBoost）執行 walk-forward 訓練。

    Returns:
        dict with oof_predictions, fold_metrics, feature_importances, best_params
    """
    if engine == "lightgbm" and not HAS_LGB:
        return {"error": "lightgbm not installed"}
    if engine == "xgboost" and not HAS_XGB:
        return {"error": "xgboost not installed"}

    logger.info(f"\n  --- {engine.upper()} Training ---")

    # 初始化儲存
    oof_preds = np.full((len(df), 3), np.nan)  # (n_samples, 3_classes)
    oof_labels = np.full(len(df), np.nan)
    fold_metrics = []
    importance_per_fold = []
    best_params = {}

    for fold in folds:
        logger.info(f"  Fold {fold.fold_id}:")

        # 準備資料
        X_train = df.iloc[fold.train_idx][feature_cols].values
        y_train_raw = df.iloc[fold.train_idx][label_col]
        y_train = _encode_labels(y_train_raw)

        X_test = df.iloc[fold.test_idx][feature_cols].values
        y_test_raw = df.iloc[fold.test_idx][label_col]
        y_test = _encode_labels(y_test_raw)

        # 過濾 NaN 標籤
        train_valid = ~np.isnan(y_train)
        test_valid = ~np.isnan(y_test)
        X_train, y_train = X_train[train_valid], y_train[train_valid].astype(int)
        X_test_clean, y_test_clean = X_test[test_valid], y_test[test_valid].astype(int)

        # === 從訓練集末尾切出 validation set（用於 early stopping，避免用測試集洩漏） ===
        val_split = int(len(X_train) * 0.85)
        X_tr, y_tr = X_train[:val_split], y_train[:val_split]
        X_val, y_val = X_train[val_split:], y_train[val_split:]

        # 計算 class weight（處理三類不平衡）
        from sklearn.utils.class_weight import compute_sample_weight
        sample_weights = compute_sample_weight("balanced", y_tr)

        logger.info(f"    Train: {len(y_tr):,} | Val: {len(y_val):,} | Test: {len(y_test_clean):,}")

        # Optuna（僅第一個 fold）
        if do_optuna and fold.fold_id == 0 and HAS_OPTUNA:
            optuna_split = int(len(X_tr) * 0.8)
            best_params = run_optuna_search(
                engine,
                X_tr[:optuna_split], y_tr[:optuna_split],
                X_tr[optuna_split:], y_tr[optuna_split:],
                config,
            )

        # 建立模型（early stopping 用 validation set，非 test set）
        if engine == "lightgbm":
            model = _build_lgb_model(best_params, config)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(
                    X_tr, y_tr,
                    sample_weight=sample_weights,
                    eval_set=[(X_val, y_val)],
                    callbacks=[lgb.early_stopping(50, verbose=False)],
                )
        else:
            model = _build_xgb_model(best_params, config)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(
                    X_tr, y_tr,
                    sample_weight=sample_weights,
                    eval_set=[(X_val, y_val)],
                    verbose=False,
                )

        # 預測（僅對有有效標籤的 clean rows，避免 NaN 標籤行進入 OOF）
        pred_proba_clean = model.predict_proba(X_test_clean)
        pred_class_clean = model.predict(X_test_clean)

        # 儲存 OOF（只寫入 valid 行，NaN 標籤行保持初始值）
        valid_test_idx = fold.test_idx[test_valid]
        oof_preds[valid_test_idx] = pred_proba_clean
        oof_labels[valid_test_idx] = y_test_clean

        # 評估
        try:
            auc = roc_auc_score(
                y_test_clean, pred_proba_clean, multi_class="ovr", average="macro"
            )
        except ValueError:
            auc = 0.0

        logloss = log_loss(y_test_clean, pred_proba_clean)
        acc = accuracy_score(y_test_clean, pred_class_clean)
        f1 = f1_score(y_test_clean, pred_class_clean, average="weighted")

        # Per-class AUC (UP/FLAT/DOWN)
        per_class_auc = {}
        try:
            from sklearn.preprocessing import label_binarize
            y_bin = label_binarize(y_test_clean, classes=[0, 1, 2])
            for cls_idx, cls_name in enumerate(["DOWN", "FLAT", "UP"]):
                per_class_auc[cls_name] = round(float(roc_auc_score(
                    y_bin[:, cls_idx], pred_proba_clean[:, cls_idx]
                )), 4)
        except Exception:
            per_class_auc = {"DOWN": 0.0, "FLAT": 0.0, "UP": 0.0}

        # Balanced accuracy
        bal_acc = balanced_accuracy_score(y_test_clean, pred_class_clean)

        # Class-prior baseline LogLoss (predict training class frequencies)
        train_counts = np.bincount(y_tr, minlength=3).astype(float)
        train_prior = train_counts / train_counts.sum()
        prior_proba = np.tile(train_prior, (len(y_test_clean), 1))
        baseline_logloss = log_loss(y_test_clean, prior_proba)

        fold_metric = {
            "fold_id": fold.fold_id,
            "auc": round(auc, 4),
            "log_loss": round(logloss, 4),
            "accuracy": round(acc, 4),
            "f1_weighted": round(f1, 4),
            "balanced_accuracy": round(bal_acc, 4),
            "per_class_auc": per_class_auc,
            "baseline_logloss": round(baseline_logloss, 4),
            "n_train": len(y_train),
            "n_test": len(y_test_clean),
        }
        fold_metrics.append(fold_metric)
        logger.info(
            f"    AUC={auc:.4f} | LogLoss={logloss:.4f} | "
            f"Acc={acc:.4f} | BalAcc={bal_acc:.4f} | F1={f1:.4f}"
        )
        logger.info(
            f"    Per-class AUC: DOWN={per_class_auc.get('DOWN',0):.4f} "
            f"FLAT={per_class_auc.get('FLAT',0):.4f} "
            f"UP={per_class_auc.get('UP',0):.4f} | "
            f"Baseline LogLoss={baseline_logloss:.4f}"
        )

        # 特徵重要性
        if hasattr(model, "feature_importances_"):
            imp = dict(zip(feature_cols, model.feature_importances_.tolist()))
            importance_per_fold.append(imp)

    # 彙整
    avg_auc = np.mean([m["auc"] for m in fold_metrics])
    avg_logloss = np.mean([m["log_loss"] for m in fold_metrics])
    avg_acc = np.mean([m["accuracy"] for m in fold_metrics])
    avg_f1 = np.mean([m["f1_weighted"] for m in fold_metrics])
    avg_bal_acc = np.mean([m["balanced_accuracy"] for m in fold_metrics])
    avg_baseline_ll = np.mean([m["baseline_logloss"] for m in fold_metrics])

    logger.info(
        f"\n  {engine.upper()} Average: AUC={avg_auc:.4f} | "
        f"LogLoss={avg_logloss:.4f} | Acc={avg_acc:.4f} | "
        f"BalAcc={avg_bal_acc:.4f} | F1={avg_f1:.4f}"
    )
    logger.info(
        f"  Baseline LogLoss={avg_baseline_ll:.4f} | "
        f"LogLoss improvement: {avg_baseline_ll - avg_logloss:.4f}"
    )

    # 平均特徵重要性
    avg_importance = {}
    if importance_per_fold:
        for feat in feature_cols:
            vals = [imp.get(feat, 0) for imp in importance_per_fold]
            avg_importance[feat] = round(np.mean(vals), 4)

    return {
        "engine": engine,
        "oof_predictions": oof_preds,
        "oof_labels": oof_labels,
        "fold_metrics": fold_metrics,
        "avg_metrics": {
            "auc": round(avg_auc, 4),
            "log_loss": round(avg_logloss, 4),
            "accuracy": round(avg_acc, 4),
            "f1_weighted": round(avg_f1, 4),
            "balanced_accuracy": round(avg_bal_acc, 4),
            "baseline_logloss": round(avg_baseline_ll, 4),
        },
        "feature_importance": avg_importance,
        "importance_per_fold": importance_per_fold,
        "best_params": best_params,
        "last_model": model,
    }


# ============================================================
# 主流程
# ============================================================

@timer
def train_all_models(
    df: pd.DataFrame,
    feature_cols: list,
    label_col: str,
    folds: list,
    config: dict,
) -> dict:
    """
    對所有引擎執行訓練。

    Returns:
        dict {engine_name: training_result}
    """
    engines = config.get("model", {}).get("engines", ["lightgbm", "xgboost"])
    results = {}

    for engine in engines:
        results[engine] = train_single_engine(
            engine=engine,
            df=df,
            feature_cols=feature_cols,
            label_col=label_col,
            folds=folds,
            config=config,
        )

    # 比較
    logger.info("\n  --- Model Comparison ---")
    for eng, res in results.items():
        if "error" in res:
            logger.warning(f"  {eng}: {res['error']}")
            continue
        m = res["avg_metrics"]
        logger.info(
            f"  {eng:>10s}: AUC={m['auc']:.4f} | "
            f"LogLoss={m['log_loss']:.4f} | Acc={m['accuracy']:.4f}"
        )

    return results


# ============================================================
# 模型序列化
# ============================================================

def save_models(
    model_results: dict,
    output_dir: str = "outputs/models",
    feature_cols: list = None,
    label_col: str = None,
) -> dict:
    """
    序列化已訓練的模型至磁碟。

    Args:
        model_results: {engine_name: {"model": model_obj, "best_params": {...}, ...}}
        output_dir: 輸出目錄
        feature_cols: 特徵列名稱（optional，若未提供則存空列表）
        label_col: 標籤列名稱（optional，若未提供則存空字串）

    Returns:
        dict mapping engine_name to saved file path
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    saved = {}
    for engine, res in model_results.items():
        if "error" in res:
            continue
        model = res.get("last_model")
        if model is not None:
            path = str(Path(output_dir) / f"{engine}_model.joblib")
            joblib.dump({
                "model": model,
                "best_params": res.get("best_params", {}),
                "feature_cols": feature_cols or [],
                "label_col": label_col or "",
            }, path)
            saved[engine] = path
            logger.info(f"  Model saved: {path}")
    return saved


def load_model(path: str) -> dict:
    """
    從磁碟載入已訓練的模型。

    Returns:
        dict with "model", "best_params", "feature_cols", "label_col"
    """
    data = joblib.load(path)
    logger.info(f"  Model loaded: {path}")
    return data
