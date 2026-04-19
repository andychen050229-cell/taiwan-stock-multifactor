"""
時序交叉驗證模組 — Purged Walk-Forward CV

核心設計：
  - Expanding window（訓練集持續累積）
  - Embargo gap（防止標籤洩漏）
  - 按交易日切分（非隨機）
"""

import numpy as np
import pandas as pd
from loguru import logger
from dataclasses import dataclass

from ..utils.helpers import timer


@dataclass
class WalkForwardFold:
    """單一 fold 的索引與元資料。"""
    fold_id: int
    train_start: str          # 訓練起始日
    train_end: str            # 訓練結束日
    test_start: str           # 測試起始日
    test_end: str             # 測試結束日
    embargo_start: str        # embargo 起始日
    embargo_end: str          # embargo 結束日
    train_idx: np.ndarray     # 訓練集 row index
    test_idx: np.ndarray      # 測試集 row index
    n_train: int
    n_test: int


@timer
def generate_walk_forward_splits(
    df: pd.DataFrame,
    date_col: str = "trade_date",
    config: dict = None,
) -> list:
    """
    產生 Purged Walk-Forward CV 的 fold 切分。

    使用 expanding window + embargo：
      Train: [day_0, ..., day_T]
      Embargo: [day_T+1, ..., day_T+embargo]
      Test:  [day_T+embargo+1, ..., day_T+embargo+test_window]

    Returns:
        list of WalkForwardFold
    """
    if config is None:
        config = {}

    bt_config = config.get("backtest", {})
    initial_train = bt_config.get("initial_train_days", 252)
    test_window = bt_config.get("test_window", 63)
    step = bt_config.get("step", 63)
    embargo = bt_config.get("embargo", 20)
    min_samples = bt_config.get("min_samples", 1000)

    # 取得排序後的唯一交易日
    dates = sorted(df[date_col].dropna().unique())
    n_dates = len(dates)
    logger.info(f"  Total trading days: {n_dates}")
    logger.info(f"  Config: initial_train={initial_train}, test={test_window}, "
                f"step={step}, embargo={embargo}")

    folds = []
    fold_id = 0
    train_end_idx = initial_train - 1  # 初始訓練期結束位置

    while True:
        # Embargo 期間
        embargo_start_idx = train_end_idx + 1
        embargo_end_idx = min(embargo_start_idx + embargo - 1, n_dates - 1)

        # Test 期間
        test_start_idx = embargo_end_idx + 1
        test_end_idx = min(test_start_idx + test_window - 1, n_dates - 1)

        # 檢查是否還有足夠的測試資料
        if test_start_idx >= n_dates:
            break
        actual_test_days = test_end_idx - test_start_idx + 1
        if actual_test_days < 10:  # 至少 10 天測試
            break

        train_dates = set(dates[0:train_end_idx + 1])
        embargo_dates = set(dates[embargo_start_idx:embargo_end_idx + 1])
        test_dates = set(dates[test_start_idx:test_end_idx + 1])

        # 取得 row indices
        date_values = df[date_col].values
        train_mask = pd.Series(date_values).isin(train_dates).values
        test_mask = pd.Series(date_values).isin(test_dates).values

        train_idx = np.where(train_mask)[0]
        test_idx = np.where(test_mask)[0]

        # 檢查最小樣本數
        if len(train_idx) < min_samples:
            logger.warning(
                f"  Fold {fold_id}: only {len(train_idx)} train samples "
                f"(need {min_samples}), skipping"
            )
            train_end_idx += step
            continue

        fold = WalkForwardFold(
            fold_id=fold_id,
            train_start=str(dates[0]),
            train_end=str(dates[train_end_idx]),
            test_start=str(dates[test_start_idx]),
            test_end=str(dates[test_end_idx]),
            embargo_start=str(dates[embargo_start_idx]) if embargo_start_idx < n_dates else "",
            embargo_end=str(dates[min(embargo_end_idx, n_dates - 1)]),
            train_idx=train_idx,
            test_idx=test_idx,
            n_train=len(train_idx),
            n_test=len(test_idx),
        )
        folds.append(fold)

        logger.info(
            f"  Fold {fold_id}: "
            f"train [{fold.train_start} → {fold.train_end}] ({fold.n_train:,} rows) | "
            f"embargo {embargo}d | "
            f"test [{fold.test_start} → {fold.test_end}] ({fold.n_test:,} rows)"
        )

        fold_id += 1
        train_end_idx += step

    logger.info(f"  Walk-forward splits: {len(folds)} folds generated")
    return folds


def get_fold_summary(folds: list) -> dict:
    """將 fold 資訊摘要成可序列化的 dict。"""
    return {
        "n_folds": len(folds),
        "folds": [
            {
                "fold_id": f.fold_id,
                "train_period": f"{f.train_start} → {f.train_end}",
                "test_period": f"{f.test_start} → {f.test_end}",
                "n_train": f.n_train,
                "n_test": f.n_test,
            }
            for f in folds
        ],
        "total_train_samples": sum(f.n_train for f in folds),
        "total_test_samples": sum(f.n_test for f in folds),
    }
