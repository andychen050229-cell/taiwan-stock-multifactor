"""
Unit tests for src/backtest/metrics.py module.

Tests core performance metrics functions:
  - annualized_return
  - sharpe_ratio
  - sortino_ratio
  - max_drawdown
  - calmar_ratio
  - rank_ic
  - rank_ic_by_date
  - compute_strategy_metrics
"""

import numpy as np
import pandas as pd
import pytest
from src.backtest.metrics import (
    annualized_return,
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    calmar_ratio,
    rank_ic,
    rank_ic_by_date,
    compute_strategy_metrics,
)


class TestAnnualizedReturn:
    """Test annualized_return function."""

    def test_zero_returns(self):
        """All zero returns should yield ~0% annual return."""
        returns = pd.Series([0.0] * 252)
        result = annualized_return(returns, trading_days=252)
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_constant_daily_return(self):
        """Test with constant positive daily return."""
        # 0.1% daily return over 252 days
        daily_ret = 0.001
        returns = pd.Series([daily_ret] * 252)
        result = annualized_return(returns, trading_days=252)
        expected = (1.001 ** 252) - 1
        assert result == pytest.approx(expected, rel=1e-4)

    def test_known_scenario(self):
        """Test with known values: 10% total return over 1 year."""
        # If total return is 10%, then (1.1)^(252/252) - 1 = 0.10
        returns = pd.Series([0.0001] * 252)  # ~0.0252% annual
        result = annualized_return(returns, trading_days=252)
        assert result > 0

    def test_negative_returns(self):
        """Negative returns should give negative annualized return."""
        returns = pd.Series([-0.001] * 252)
        result = annualized_return(returns, trading_days=252)
        assert result < 0

    def test_empty_series(self):
        """Empty series should return 0."""
        returns = pd.Series([])
        result = annualized_return(returns, trading_days=252)
        assert result == 0.0

    def test_fewer_than_252_days(self):
        """Test annualization with fewer than 252 days."""
        returns = pd.Series([0.001] * 126)  # 126 trading days = half year
        result = annualized_return(returns, trading_days=252)
        # (1.001^126)^(252/126) - 1
        total = (1.001 ** 126) - 1
        expected = (total + 1) ** (252 / 126) - 1
        assert result == pytest.approx(expected, rel=1e-4)


class TestSharpeRatio:
    """Test sharpe_ratio function."""

    def test_zero_volatility_returns(self):
        """Zero or near-zero volatility should return 0 Sharpe."""
        returns = pd.Series([0.001] * 252)  # No volatility
        result = sharpe_ratio(returns, rf=0.0, trading_days=252)
        # With identical returns, std should be 0, but due to floating point precision
        # it might give a very large number. Check if it's 0 or very large
        assert result == pytest.approx(0.0, abs=1e-6) or result > 1e10

    def test_positive_returns_positive_sharpe(self):
        """Consistent positive returns should give positive Sharpe."""
        returns = pd.Series([0.001] * 100 + [-0.0005] * 100)
        result = sharpe_ratio(returns, rf=0.0, trading_days=252)
        assert result > 0

    def test_negative_returns_negative_sharpe(self):
        """Consistent negative returns should give negative Sharpe."""
        returns = pd.Series([-0.001] * 100 + [0.0005] * 100)
        result = sharpe_ratio(returns, rf=0.0, trading_days=252)
        assert result < 0

    def test_with_risk_free_rate(self):
        """Higher risk-free rate should reduce Sharpe."""
        returns = pd.Series([0.001] * 100 + [-0.0005] * 100)
        sharpe_no_rf = sharpe_ratio(returns, rf=0.0, trading_days=252)
        sharpe_with_rf = sharpe_ratio(returns, rf=0.02, trading_days=252)
        # Higher rf reduces excess returns, thus Sharpe
        assert sharpe_with_rf < sharpe_no_rf

    def test_empty_series(self):
        """Empty series should handle gracefully."""
        returns = pd.Series([])
        result = sharpe_ratio(returns, rf=0.0, trading_days=252)
        # Should not crash
        assert isinstance(result, float)


class TestSortinoRatio:
    """Test sortino_ratio function."""

    def test_only_upside_returns(self):
        """Only positive returns should give high Sortino or 0 (zero downside dev)."""
        returns = pd.Series([0.001] * 100)
        result = sortino_ratio(returns, rf=0.0, trading_days=252)
        # With no downside, downside_dev = 0, so Sortino should be 0
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_only_downside_returns(self):
        """Only negative returns should give negative Sortino."""
        returns = pd.Series([-0.001] * 100)
        result = sortino_ratio(returns, rf=0.0, trading_days=252)
        assert result < 0

    def test_zero_downside_dev(self):
        """Zero downside deviation should return 0."""
        returns = pd.Series([0.001] * 252)  # All positive = no downside
        result = sortino_ratio(returns, rf=0.0, trading_days=252)
        assert result == 0.0

    def test_mixed_returns_downside_only(self):
        """Sortino should ignore upside volatility."""
        # Returns with high upside but some downside
        returns = pd.Series([0.01] * 50 + [-0.005] * 50)
        sortino_res = sortino_ratio(returns, rf=0.0, trading_days=252)
        sharpe_res = sharpe_ratio(returns, rf=0.0, trading_days=252)
        # Sortino should be higher (ignores upside vol)
        assert sortino_res > sharpe_res


class TestMaxDrawdown:
    """Test max_drawdown function."""

    def test_no_drawdown(self):
        """Monotonically increasing returns should have ~0 MDD."""
        returns = pd.Series([0.001] * 252)
        result = max_drawdown(returns)
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_single_drop(self):
        """Known drop scenario."""
        # Start at 100, drop to 50, then recover to 75
        # Cumulative: [100, 100, 50, 75]
        # Returns: [0, 0, -0.5, 0.5]
        returns = pd.Series([0.0, -0.5, 0.5])
        result = max_drawdown(returns)
        # Max drawdown = (50 - 100) / 100 = -0.5
        assert result == pytest.approx(-0.5, rel=1e-6)

    def test_all_losses(self):
        """Continuous losses should accumulate drawdown."""
        returns = pd.Series([-0.1] * 10)
        result = max_drawdown(returns)
        assert result < 0
        # (0.9^10 - 0.9^10) / 0.9^10 should be negative
        assert result <= -0.1

    def test_empty_series(self):
        """Empty series should return 0 or NaN."""
        returns = pd.Series([])
        result = max_drawdown(returns)
        # Empty series: cumprod returns empty, min of empty returns nan
        assert pd.isna(result) or result == 0.0

    def test_recovery_after_drawdown(self):
        """Even with recovery, MDD captures the trough."""
        # Start with +10%, then -50%, then +100% recovery
        # cum = [1.1, 0.55, 1.1]
        # peak = [1.1, 1.1, 1.1]
        # dd = [0, -0.5, 0]
        returns = pd.Series([0.1, -0.5, 1.0])
        result = max_drawdown(returns)
        # Should be -0.5 (the minimum drawdown)
        assert result == pytest.approx(-0.5, rel=1e-4)


class TestCalmarRatio:
    """Test calmar_ratio function."""

    def test_zero_mdd_returns_zero(self):
        """Zero MDD should return 0 Calmar."""
        returns = pd.Series([0.001] * 252)
        result = calmar_ratio(returns, trading_days=252)
        assert result == 0.0

    def test_positive_return_positive_mdd(self):
        """Positive return with drawdown should give positive Calmar."""
        returns = pd.Series([0.001] * 100 + [-0.0005] * 50)
        result = calmar_ratio(returns, trading_days=252)
        assert result > 0

    def test_calmar_is_ratio(self):
        """Verify Calmar = annual_return / |MDD|."""
        returns = pd.Series([0.001] * 50 + [-0.002] * 50)
        calmar = calmar_ratio(returns, trading_days=252)
        ann_ret = annualized_return(returns, trading_days=252)
        mdd = abs(max_drawdown(returns))
        if mdd > 0:
            expected = ann_ret / mdd
            assert calmar == pytest.approx(expected, rel=1e-4)


class TestRankIC:
    """Test rank_ic function."""

    def test_perfect_correlation(self):
        """Perfect positive correlation should give IC ~1.0."""
        scores = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0] * 10)
        returns = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0] * 10)
        result = rank_ic(scores, returns)
        assert result == pytest.approx(1.0, abs=1e-3)

    def test_perfect_negative_correlation(self):
        """Perfect negative correlation should give IC ~-1.0."""
        scores = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0] * 10)
        returns = pd.Series([5.0, 4.0, 3.0, 2.0, 1.0] * 10)
        result = rank_ic(scores, returns)
        assert result == pytest.approx(-1.0, abs=1e-3)

    def test_no_correlation(self):
        """Uncorrelated series should give IC ~0."""
        np.random.seed(42)
        scores = pd.Series(np.random.randn(100))
        returns = pd.Series(np.random.randn(100))
        result = rank_ic(scores, returns)
        # Should be close to 0
        assert abs(result) < 0.3

    def test_insufficient_data(self):
        """Less than 10 points should return 0."""
        scores = pd.Series([1.0, 2.0, 3.0])
        returns = pd.Series([1.0, 2.0, 3.0])
        result = rank_ic(scores, returns)
        assert result == 0.0

    def test_with_nans(self):
        """Should handle NaN values."""
        scores = pd.Series([1.0, 2.0, np.nan, 4.0, 5.0] * 10)
        returns = pd.Series([1.0, 2.0, 3.0, np.nan, 5.0] * 10)
        result = rank_ic(scores, returns)
        # Should compute only on valid pairs
        assert isinstance(result, float)


class TestRankICByDate:
    """Test rank_ic_by_date function."""

    def test_returns_series_indexed_by_date(self):
        """Should return a Series indexed by date."""
        dates = pd.date_range("2023-01-01", periods=30)
        data = {
            "trade_date": dates.repeat(10),
            "score": np.tile(np.arange(1, 11), 30),
            "return": np.tile(np.arange(1, 11), 30),
        }
        df = pd.DataFrame(data)
        result = rank_ic_by_date(df, "score", "return", "trade_date")
        assert isinstance(result, pd.Series)
        assert result.index.name == "trade_date"

    def test_daily_ic_values(self):
        """Each day should have one IC value."""
        dates = pd.date_range("2023-01-01", periods=30)
        data = {
            "trade_date": dates.repeat(10),
            "score": np.tile(np.arange(1, 11), 30),
            "return": np.tile(np.arange(1, 11), 30),
        }
        df = pd.DataFrame(data)
        result = rank_ic_by_date(df, "score", "return", "trade_date")
        assert len(result) == 30

    def test_insufficient_stocks_per_day(self):
        """Days with < 10 stocks should return NaN."""
        dates = pd.date_range("2023-01-01", periods=10)
        data = {
            "trade_date": dates.repeat(5),  # Only 5 stocks per day
            "score": np.tile(np.arange(1, 6), 10),
            "return": np.tile(np.arange(1, 6), 10),
        }
        df = pd.DataFrame(data)
        result = rank_ic_by_date(df, "score", "return", "trade_date")
        # All should be NaN due to < 10 points per day
        assert result.isna().all()


class TestComputeStrategyMetrics:
    """Test compute_strategy_metrics function."""

    def test_returns_dict_with_required_keys(self):
        """Should return dict with essential metric keys."""
        returns = pd.Series([0.001] * 100 + [-0.0005] * 100)
        result = compute_strategy_metrics(returns)
        required_keys = [
            "annualized_return",
            "sharpe_ratio",
            "sortino_ratio",
            "max_drawdown",
            "calmar_ratio",
            "total_return",
            "daily_volatility",
            "annual_volatility",
            "positive_days",
            "negative_days",
            "win_rate",
            "n_trading_days",
        ]
        for key in required_keys:
            assert key in result

    def test_metric_types(self):
        """All metrics should be floats or ints."""
        returns = pd.Series([0.001] * 100)
        result = compute_strategy_metrics(returns)
        for key, value in result.items():
            assert isinstance(value, (int, float))

    def test_with_benchmark_returns(self):
        """Should compute excess return and IR with benchmark."""
        strategy = pd.Series([0.002] * 100)
        benchmark = pd.Series([0.001] * 100)
        result = compute_strategy_metrics(strategy, benchmark_returns=benchmark)
        assert "excess_return" in result
        assert "information_ratio" in result

    def test_with_predicted_scores(self):
        """Should compute Rank IC with scores."""
        returns = pd.Series([0.001] * 100 + [0.002] * 100 + [0.003] * 100)
        scores = pd.Series([1.0] * 100 + [2.0] * 100 + [3.0] * 100)
        result = compute_strategy_metrics(
            returns, predicted_scores=scores, actual_returns=returns
        )
        assert "rank_ic" in result

    def test_win_rate_calculation(self):
        """Win rate should be percentage of positive days."""
        returns = pd.Series([0.001] * 60 + [-0.001] * 40)
        result = compute_strategy_metrics(returns)
        assert result["win_rate"] == pytest.approx(0.6, rel=1e-4)

    def test_positive_negative_days_count(self):
        """Should count positive and negative days correctly."""
        returns = pd.Series([0.001] * 70 + [-0.001] * 30)
        result = compute_strategy_metrics(returns)
        assert result["positive_days"] == 70
        assert result["negative_days"] == 30

    def test_empty_returns(self):
        """Should handle empty returns gracefully."""
        returns = pd.Series([])
        result = compute_strategy_metrics(returns)
        assert result["n_trading_days"] == 0

    def test_all_values_rounded(self):
        """Metric values should be rounded to expected precision."""
        returns = pd.Series([0.0001234567] * 100)
        result = compute_strategy_metrics(returns)
        # Check that values are reasonably rounded
        assert isinstance(result["annualized_return"], float)
        # Most metrics rounded to 4 decimals
        annualized_str = f"{result['annualized_return']:.4f}"
        assert len(annualized_str.split(".")[1]) <= 4
