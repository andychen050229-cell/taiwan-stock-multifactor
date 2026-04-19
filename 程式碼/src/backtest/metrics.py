"""
績效評估模組 — Phase 2

指標清單：
  - Sharpe Ratio（年化）
  - Sortino Ratio（年化）
  - Maximum Drawdown (MDD)
  - Calmar Ratio (Annual Return / MDD)
  - Information Coefficient (Rank IC)
  - Hit Rate（方向正確率）
  - 年化報酬率
  - 累積報酬
  - 周轉率
"""

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats


# ============================================================
# 基礎指標
# ============================================================

def annualized_return(daily_returns: pd.Series, trading_days: int = 252) -> float:
    """年化報酬率。"""
    total = (1 + daily_returns).prod()
    n_days = len(daily_returns)
    if n_days == 0 or total <= 0:
        return 0.0
    return float(total ** (trading_days / n_days) - 1)


def sharpe_ratio(daily_returns: pd.Series, rf: float = 0.0, trading_days: int = 252) -> float:
    """年化 Sharpe Ratio。"""
    if len(daily_returns) < 2:
        return 0.0
    excess = daily_returns - rf / trading_days
    std = excess.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return float(excess.mean() / std * np.sqrt(trading_days))


def sortino_ratio(daily_returns: pd.Series, rf: float = 0.0, trading_days: int = 252) -> float:
    """年化 Sortino Ratio（下行偏差 = sqrt(mean(min(r-rf, 0)^2))）。"""
    if len(daily_returns) < 2:
        return 0.0
    excess = daily_returns - rf / trading_days
    downside_diff = np.minimum(excess, 0)
    downside_dev = np.sqrt(np.mean(downside_diff ** 2))
    if downside_dev == 0 or np.isnan(downside_dev):
        return 0.0
    return float(excess.mean() / downside_dev * np.sqrt(trading_days))


def max_drawdown(daily_returns: pd.Series) -> float:
    """最大回撤。"""
    cum = (1 + daily_returns).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    return float(dd.min())


def calmar_ratio(daily_returns: pd.Series, trading_days: int = 252) -> float:
    """Calmar Ratio = 年化報酬 / |MDD|。"""
    ann_ret = annualized_return(daily_returns, trading_days)
    mdd = abs(max_drawdown(daily_returns))
    if mdd == 0:
        return 0.0
    return float(ann_ret / mdd)


def hit_rate(predicted_direction: np.ndarray, actual_direction: np.ndarray) -> float:
    """方向正確率（僅計算非 FLAT 的預測）。"""
    # 排除 FLAT 預測
    non_flat = predicted_direction != 0
    if non_flat.sum() == 0:
        return 0.0
    return float((predicted_direction[non_flat] == actual_direction[non_flat]).mean())


# ============================================================
# Information Coefficient (Rank IC)
# ============================================================

def rank_ic(predicted_scores: pd.Series, actual_returns: pd.Series) -> float:
    """
    Rank IC = Spearman 等級相關係數。
    衡量預測得分排序與實際報酬排序的一致性。
    """
    valid = predicted_scores.notna() & actual_returns.notna()
    if valid.sum() < 10:
        return 0.0
    corr, _ = stats.spearmanr(predicted_scores[valid], actual_returns[valid])
    return float(corr) if not np.isnan(corr) else 0.0


def rank_ic_by_date(
    df: pd.DataFrame,
    score_col: str,
    return_col: str,
    date_col: str = "trade_date",
) -> pd.Series:
    """
    逐日計算 Rank IC，回傳時間序列。
    """
    def _daily_ic(group):
        if len(group) < 10:
            return np.nan
        corr, _ = stats.spearmanr(group[score_col], group[return_col])
        return corr

    ic_series = df.groupby(date_col).apply(_daily_ic)
    return ic_series


# ============================================================
# 綜合績效報告
# ============================================================

def compute_strategy_metrics(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series = None,
    predicted_scores: pd.Series = None,
    actual_returns: pd.Series = None,
) -> dict:
    """
    計算策略的完整績效指標。

    Args:
        daily_returns: 策略日報酬
        benchmark_returns: 基準日報酬（可選）
        predicted_scores: 預測分數（計算 IC 用）
        actual_returns: 實際報酬（計算 IC 用）

    Returns:
        dict with all metrics
    """
    metrics = {
        "annualized_return": round(annualized_return(daily_returns), 4),
        "sharpe_ratio": round(sharpe_ratio(daily_returns), 4),
        "sortino_ratio": round(sortino_ratio(daily_returns), 4),
        "max_drawdown": round(max_drawdown(daily_returns), 4),
        "calmar_ratio": round(calmar_ratio(daily_returns), 4),
        "total_return": round(float((1 + daily_returns).prod() - 1), 4),
        "daily_volatility": round(float(daily_returns.std()), 6),
        "annual_volatility": round(float(daily_returns.std() * np.sqrt(252)), 4),
        "positive_days": int((daily_returns > 0).sum()),
        "negative_days": int((daily_returns < 0).sum()),
        "win_rate": round(float((daily_returns > 0).mean()), 4),
        "n_trading_days": len(daily_returns),
    }

    # 超額報酬（如果有基準）
    if benchmark_returns is not None and len(benchmark_returns) > 0:
        excess = daily_returns - benchmark_returns
        metrics["excess_return"] = round(annualized_return(excess), 4)
        metrics["information_ratio"] = round(sharpe_ratio(excess), 4)

    # Rank IC（如果有預測分數）
    if predicted_scores is not None and actual_returns is not None:
        ic = rank_ic(predicted_scores, actual_returns)
        metrics["rank_ic"] = round(ic, 4)

    return metrics


# ============================================================
# 進階分析模組 - Phase 2 擴展
# ============================================================

def compute_quintile_returns(
    df: pd.DataFrame,
    score_col: str,
    return_col: str,
    date_col: str = "trade_date",
    n_groups: int = 5,
    holding_days: int = 1,
) -> dict:
    """
    Quintile Factor Analysis: 按評分分層排序，計算各分層報酬。

    Args:
        df: DataFrame containing score, return, and date columns
        score_col: 評分列名
        return_col: 報酬列名（forward return，週期由 holding_days 指定）
        date_col: 日期列名
        n_groups: 分層數量（默認 5=五分位）
        holding_days: 持有天數（1=日報酬, 5=週報酬, 20=月報酬）

    Returns:
        {
            'quintile_returns': {1: ann_ret, 2: ann_ret, ...},
            'long_short_spread': float,
            'monotonicity_score': float (Spearman correlation),
            'daily_quintile_returns': DataFrame
        }
    """
    df = df.copy()

    # 按日期分組，計算每日的五分位分組
    def _daily_quintiles(group):
        if len(group) < n_groups:
            return group
        group['quintile'] = pd.qcut(group[score_col], q=n_groups, labels=False, duplicates='drop') + 1
        return group

    df = df.groupby(date_col).apply(_daily_quintiles).reset_index(drop=True)

    # 計算每個五分位的平均報酬（每個 rebalance period）
    daily_quintile_returns = df.groupby([date_col, 'quintile'])[return_col].mean().unstack(fill_value=0)

    # Annualization fix: 正確處理非日報酬的年化
    # 每年有 252 / holding_days 個 rebalance periods
    periods_per_year = 252 / max(holding_days, 1)

    # 計算各五分位的年化報酬
    quintile_returns = {}
    for q in range(1, n_groups + 1):
        if q in daily_quintile_returns.columns:
            returns = daily_quintile_returns[q]
            # 用正確的 periods_per_year 替代默認 252
            total = (1 + returns).prod()
            n_periods = len(returns)
            if n_periods > 0 and total > 0:
                ann_ret = float(total ** (periods_per_year / n_periods) - 1)
            else:
                ann_ret = 0.0
            quintile_returns[q] = round(ann_ret, 4)
        else:
            quintile_returns[q] = 0.0

    # Long-Short Spread (Q5 - Q1)
    long_short = quintile_returns.get(n_groups, 0.0) - quintile_returns.get(1, 0.0)

    # Monotonicity Score: Spearman correlation of quintile rank vs avg return per quintile
    avg_returns_by_q = [quintile_returns.get(q, 0.0) for q in range(1, n_groups + 1)]
    quintile_ranks = np.arange(1, n_groups + 1)
    monotonicity_corr, _ = stats.spearmanr(quintile_ranks, avg_returns_by_q)
    monotonicity_score = float(monotonicity_corr) if not np.isnan(monotonicity_corr) else 0.0

    return {
        'quintile_returns': quintile_returns,
        'long_short_spread': round(long_short, 4),
        'monotonicity_score': round(monotonicity_score, 4),
        'daily_quintile_returns': daily_quintile_returns,
    }


def bootstrap_ci(
    daily_returns: pd.Series,
    n_bootstrap: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> dict:
    """
    Bootstrap Confidence Intervals for annualized return and Sharpe ratio.

    Args:
        daily_returns: 日報酬序列
        n_bootstrap: Bootstrap 重抽樣次數
        ci: 信心水準 (默認 0.95 = 95%)
        seed: 隨機種子

    Returns:
        {
            'annualized_return': {'point_estimate': float, 'ci': (lower, upper)},
            'sharpe_ratio': {'point_estimate': float, 'ci': (lower, upper)},
            'bootstrap_returns': array,
            'bootstrap_sharpe': array,
        }
    """
    np.random.seed(seed)
    returns_array = daily_returns.values

    bootstrap_ann_returns = []
    bootstrap_sharpes = []

    for _ in range(n_bootstrap):
        # 有放回重抽樣
        sample = np.random.choice(returns_array, size=len(returns_array), replace=True)
        sample_series = pd.Series(sample)

        ann_ret = annualized_return(sample_series)
        sh = sharpe_ratio(sample_series)

        bootstrap_ann_returns.append(ann_ret)
        bootstrap_sharpes.append(sh)

    bootstrap_ann_returns = np.array(bootstrap_ann_returns)
    bootstrap_sharpes = np.array(bootstrap_sharpes)

    # 計算點估計（原始樣本）
    point_ret = annualized_return(daily_returns)
    point_sharpe = sharpe_ratio(daily_returns)

    # 計算置信區間
    alpha = 1 - ci
    lower_pct = alpha / 2 * 100
    upper_pct = (1 - alpha / 2) * 100

    ret_ci = (
        round(float(np.percentile(bootstrap_ann_returns, lower_pct)), 4),
        round(float(np.percentile(bootstrap_ann_returns, upper_pct)), 4),
    )
    sharpe_ci = (
        round(float(np.percentile(bootstrap_sharpes, lower_pct)), 4),
        round(float(np.percentile(bootstrap_sharpes, upper_pct)), 4),
    )

    return {
        'annualized_return': {
            'point_estimate': round(point_ret, 4),
            'ci': ret_ci,
        },
        'sharpe_ratio': {
            'point_estimate': round(point_sharpe, 4),
            'ci': sharpe_ci,
        },
        'bootstrap_returns': bootstrap_ann_returns,
        'bootstrap_sharpe': bootstrap_sharpes,
    }


def compute_drawdown_analysis(daily_returns: pd.Series) -> dict:
    """
    Conditional Drawdown Analysis: 詳細的回撤分析。

    Args:
        daily_returns: 日報酬序列

    Returns:
        {
            'drawdown_series': Series,
            'top_5_episodes': [
                {
                    'start_date': idx,
                    'trough_date': idx,
                    'recovery_date': idx or None,
                    'depth': float,
                    'duration_to_trough': int (days),
                    'duration_to_recovery': int or None (days),
                },
                ...
            ],
            'avg_recovery_time': int (days),
            'cdar_95': float,
        }
    """
    # 計算累積報酬和最大值
    cum_returns = (1 + daily_returns).cumprod()
    running_max = cum_returns.cummax()
    drawdown = (cum_returns - running_max) / running_max

    # 識別回撤區間
    in_drawdown = drawdown < 0
    drawdown_changes = in_drawdown.astype(int).diff()

    # 回撤開始和結束的索引
    dd_starts = daily_returns.index[drawdown_changes == 1]
    dd_ends = daily_returns.index[drawdown_changes == -1]

    episodes = []

    # 如果末尾仍在回撤中，添加虛擬結束點
    if len(dd_starts) > len(dd_ends):
        dd_ends = dd_ends.union(pd.Index([daily_returns.index[-1]]))

    for start_idx, end_idx in zip(dd_starts, dd_ends):
        # 取得回撤期間的數據
        mask = (daily_returns.index >= start_idx) & (daily_returns.index <= end_idx)
        dd_period = drawdown[mask]

        if len(dd_period) == 0:
            continue

        trough_idx = dd_period.idxmin()
        if pd.isna(trough_idx):
            continue
        trough_depth = float(dd_period.min())

        # 從低谷到完全恢復
        recovery_mask = (daily_returns.index >= trough_idx)
        recovery_period = cum_returns[recovery_mask]

        recovery_idx = None
        recovery_days = None
        if len(recovery_period) > 1:
            # 找到第一次回到之前最高點的時間
            pre_trough_max = cum_returns[daily_returns.index < trough_idx].max()
            recovered = recovery_period >= pre_trough_max
            if recovered.any():
                recovery_idx = recovered.idxmax()
                try:
                    recovery_days = (recovery_idx - trough_idx).days
                except AttributeError:
                    # Integer index fallback
                    recovery_days = int(recovery_idx - trough_idx)

        try:
            duration_to_trough = (trough_idx - start_idx).days
        except AttributeError:
            duration_to_trough = int(trough_idx - start_idx)

        episodes.append({
            'start_date': start_idx,
            'trough_date': trough_idx,
            'recovery_date': recovery_idx,
            'depth': round(trough_depth, 4),
            'duration_to_trough': duration_to_trough,
            'duration_to_recovery': recovery_days,
        })

    # 排序並取前 5 個最深的回撤
    episodes_sorted = sorted(episodes, key=lambda x: x['depth'])
    top_5 = episodes_sorted[:5]

    # 計算平均恢復時間
    recovery_times = [e['duration_to_recovery'] for e in episodes if e['duration_to_recovery'] is not None]
    avg_recovery = int(np.mean(recovery_times)) if recovery_times else 0

    # Conditional Drawdown at Risk (CDaR) at 95th percentile
    dd_positive = drawdown[drawdown < 0]
    if len(dd_positive) > 0:
        cdar_95 = float(np.percentile(dd_positive, 5))  # 下側 5% (對應 95% CDaR)
    else:
        cdar_95 = 0.0

    return {
        'drawdown_series': drawdown,
        'top_5_episodes': top_5,
        'avg_recovery_time': avg_recovery,
        'cdar_95': round(cdar_95, 4),
    }


def compute_alpha_decay(
    df: pd.DataFrame,
    score_col: str,
    return_cols: list,
    date_col: str = "trade_date",
) -> dict:
    """
    Alpha Decay Analysis: 跨多時間視野計算 Rank IC，展示預測力衰減。

    Args:
        df: DataFrame
        score_col: 評分列名
        return_cols: 多個報酬列名，如 ["fwd_ret_1", "fwd_ret_5", "fwd_ret_20"]
        date_col: 日期列名

    Returns:
        {
            'horizon_metrics': {
                horizon: {'mean_ic': float, 'icir': float},
                ...
            },
            'ic_by_date': DataFrame (date x horizon),
        }
    """
    results = {}
    ic_by_date = {}

    for ret_col in return_cols:
        # 提取視野名（假設格式為 "fwd_ret_N"）
        horizon = ret_col.replace('fwd_ret_', '')

        # 逐日計算 Rank IC
        def _daily_ic(group):
            if len(group) < 10:
                return np.nan
            valid = group[score_col].notna() & group[ret_col].notna()
            if valid.sum() < 10:
                return np.nan
            corr, _ = stats.spearmanr(group[score_col][valid], group[ret_col][valid])
            return corr if not np.isnan(corr) else np.nan

        ic_series = df.groupby(date_col).apply(_daily_ic)
        ic_by_date[horizon] = ic_series

        # 計算平均 IC 和 ICIR
        mean_ic = float(ic_series.mean()) if len(ic_series) > 0 else 0.0
        ic_std = float(ic_series.std()) if len(ic_series) > 0 and ic_series.std() > 0 else 1e-6
        icir = mean_ic / ic_std * np.sqrt(252)  # 年化 ICIR

        results[horizon] = {
            'mean_ic': round(mean_ic, 4),
            'icir': round(icir, 4),
        }

    ic_by_date_df = pd.DataFrame(ic_by_date)

    return {
        'horizon_metrics': results,
        'ic_by_date': ic_by_date_df,
    }


def format_metrics_table(results: dict) -> pd.DataFrame:
    """
    將多個策略/模型的績效整理成比較表。

    Args:
        results: {model_name: metrics_dict}

    Returns:
        pd.DataFrame
    """
    rows = []
    for name, metrics in results.items():
        row = {"Model": name}
        row.update(metrics)
        rows.append(row)

    df = pd.DataFrame(rows).set_index("Model")
    return df
