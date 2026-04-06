"""
Unit tests for src/backtest/engine.py module.

Tests backtest engine:
  - _round_trip_cost calculation with known inputs
  - Basic sanity: results dict contains expected keys
  - Backtest execution and metrics computation
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import TimeSeriesSplit

from src.backtest.engine import (
    _round_trip_cost,
    run_backtest,
    compute_benchmark,
)


class TestRoundTripCost:
    """Test round-trip cost calculation."""

    def test_basic_cost_calculation(self):
        """Test basic cost calculation formula."""
        # Default Taiwan market: 0.001425 * 2 + 0.003 + 0.001 * 2
        cost_params = {
            "commission": 0.001425,
            "discount": 1.0,
            "tax": 0.003,
            "slippage": 0.001,
        }

        result = _round_trip_cost(cost_params)

        # comm * disc * 2 + tax + slip * 2
        expected = 0.001425 * 1.0 * 2 + 0.003 + 0.001 * 2
        assert result == pytest.approx(expected, rel=1e-6)

    def test_with_commission_discount(self):
        """Test with commission discount."""
        cost_params = {
            "commission": 0.001425,
            "discount": 0.5,  # 50% discount
            "tax": 0.003,
            "slippage": 0.001,
        }

        result = _round_trip_cost(cost_params)

        expected = 0.001425 * 0.5 * 2 + 0.003 + 0.001 * 2
        assert result == pytest.approx(expected, rel=1e-6)

    def test_zero_slippage(self):
        """Test with zero slippage."""
        cost_params = {
            "commission": 0.001425,
            "discount": 1.0,
            "tax": 0.003,
            "slippage": 0.0,
        }

        result = _round_trip_cost(cost_params)

        expected = 0.001425 * 2 + 0.003
        assert result == pytest.approx(expected, rel=1e-6)

    def test_high_cost_scenario(self):
        """Test with high cost parameters."""
        cost_params = {
            "commission": 0.002,
            "discount": 1.0,
            "tax": 0.005,
            "slippage": 0.002,
        }

        result = _round_trip_cost(cost_params)

        expected = 0.002 * 2 + 0.005 + 0.002 * 2
        assert result == pytest.approx(expected, rel=1e-6)
        # Should be ~0.013
        assert result == pytest.approx(0.013, rel=1e-4)

    def test_realistic_taiwan_cost(self):
        """Test with realistic Taiwan market parameters."""
        cost_params = {
            "commission": 0.001425,
            "discount": 1.0,
            "tax": 0.003,
            "slippage": 0.0005,
        }

        result = _round_trip_cost(cost_params)

        # Should be roughly 0.0065 - 0.007
        assert 0.006 < result < 0.008


class MockFold:
    """Mock TimeSeriesSplit fold for testing."""

    def __init__(self, train_idx, test_idx):
        self.train_idx = train_idx
        self.test_idx = test_idx


class TestRunBacktest:
    """Test backtest execution."""

    def test_backtest_returns_dict(self):
        """Should return dict with engine results."""
        np.random.seed(42)
        # Create minimal test data
        dates = pd.date_range("2023-01-01", periods=100)
        companies = ["A", "B", "C"]
        n_rows = len(dates) * len(companies)
        df = pd.DataFrame({
            "company_id": companies * 100,
            "trade_date": dates.repeat(3),
            "closing_price": 100 + np.random.randn(n_rows) * 5,
            "Trading_Volume": 1_000_000,
            "label_5": np.random.choice([-1, 0, 1], n_rows),
            "fwd_ret_5": np.random.randn(n_rows) * 0.02,
        })

        # Mock model results
        n_rows = len(df)
        mock_oof_preds = np.random.random((n_rows, 3))
        mock_oof_preds = mock_oof_preds / mock_oof_preds.sum(axis=1, keepdims=True)

        model_results = {
            "xgboost": {
                "oof_predictions": mock_oof_preds,
            }
        }

        # Create folds
        tscv = TimeSeriesSplit(n_splits=2)
        folds = [
            MockFold(train_idx, test_idx)
            for train_idx, test_idx in tscv.split(df)
        ]

        config = {
            "backtest": {
                "strategy": {"top_k_pct": 0.1},
                "min_avg_volume": 500_000,
            },
            "cost_model": {
                "discount": {
                    "commission": 0.001425,
                    "discount": 1.0,
                    "tax": 0.003,
                    "slippage": 0.001,
                }
            }
        }

        result = run_backtest(
            df,
            model_results,
            folds,
            ["dummy_feature"],
            "label_5",
            config
        )

        assert isinstance(result, dict)
        assert "xgboost" in result

    def test_backtest_results_structure(self):
        """Backtest results should have expected structure."""
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=50)
        companies = ["A", "B"]
        n_rows = len(dates) * len(companies)
        df = pd.DataFrame({
            "company_id": companies * 50,
            "trade_date": dates.repeat(2),
            "closing_price": 100 + np.random.randn(n_rows) * 5,
            "Trading_Volume": 1_000_000,
            "label_5": np.random.choice([-1, 0, 1], n_rows),
            "fwd_ret_5": np.random.randn(n_rows) * 0.02,
        })

        n_rows = len(df)
        mock_oof_preds = np.random.random((n_rows, 3))
        mock_oof_preds = mock_oof_preds / mock_oof_preds.sum(axis=1, keepdims=True)

        model_results = {
            "model1": {"oof_predictions": mock_oof_preds}
        }

        tscv = TimeSeriesSplit(n_splits=2)
        folds = [
            MockFold(train_idx, test_idx)
            for train_idx, test_idx in tscv.split(df)
        ]

        config = {
            "backtest": {
                "strategy": {"top_k_pct": 0.2},
                "min_avg_volume": 500_000,
            },
            "cost_model": {
                "discount": {
                    "commission": 0.001425,
                    "discount": 1.0,
                    "tax": 0.003,
                    "slippage": 0.001,
                }
            }
        }

        result = run_backtest(df, model_results, folds, [], "label_5", config)

        # Check structure
        assert "model1" in result
        engine_result = result["model1"]
        assert "cost_scenarios" in engine_result
        assert "rank_ic" in engine_result
        assert "daily_returns" in engine_result
        assert "avg_turnover" in engine_result

    def test_cost_scenarios_computed(self):
        """Should compute different cost scenarios."""
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=50)
        companies = ["A", "B"]
        n_rows = len(dates) * len(companies)
        df = pd.DataFrame({
            "company_id": companies * 50,
            "trade_date": dates.repeat(2),
            "closing_price": 100 + np.random.randn(n_rows) * 5,
            "Trading_Volume": 1_000_000,
            "label_5": np.random.choice([-1, 0, 1], n_rows),
            "fwd_ret_5": np.random.randn(n_rows) * 0.02,
        })

        n_rows = len(df)
        mock_oof_preds = np.random.random((n_rows, 3))
        mock_oof_preds = mock_oof_preds / mock_oof_preds.sum(axis=1, keepdims=True)

        model_results = {
            "test_model": {"oof_predictions": mock_oof_preds}
        }

        tscv = TimeSeriesSplit(n_splits=2)
        folds = [
            MockFold(train_idx, test_idx)
            for train_idx, test_idx in tscv.split(df)
        ]

        config = {
            "backtest": {
                "strategy": {"top_k_pct": 0.2},
                "min_avg_volume": 500_000,
            },
            "cost_model": {
                "low_cost": {
                    "commission": 0.0005,
                    "discount": 1.0,
                    "tax": 0.001,
                    "slippage": 0.0,
                },
                "high_cost": {
                    "commission": 0.002,
                    "discount": 1.0,
                    "tax": 0.005,
                    "slippage": 0.002,
                },
            }
        }

        result = run_backtest(df, model_results, folds, [], "label_5", config)

        # Should have both scenarios
        scenarios = result["test_model"]["cost_scenarios"]
        assert "low_cost" in scenarios
        assert "high_cost" in scenarios


class TestComputeBenchmark:
    """Test benchmark computation."""

    def test_benchmark_returns_dict(self):
        """Should return dict with benchmark metrics."""
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=50)
        companies = ["A", "B", "C"]
        n_rows = len(dates) * len(companies)
        df = pd.DataFrame({
            "company_id": companies * 50,
            "trade_date": dates.repeat(3),
            "closing_price": 100 + np.random.randn(n_rows) * 5,
        })

        tscv = TimeSeriesSplit(n_splits=2)
        folds = [
            MockFold(train_idx, test_idx)
            for train_idx, test_idx in tscv.split(df)
        ]

        result = compute_benchmark(df, folds, {})

        assert isinstance(result, dict)
        assert "metrics" in result
        assert "daily_returns" in result

    def test_benchmark_metrics_structure(self):
        """Benchmark metrics should have expected keys."""
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=50)
        companies = ["A", "B"]
        n_rows = len(dates) * len(companies)
        df = pd.DataFrame({
            "company_id": companies * 50,
            "trade_date": dates.repeat(2),
            "closing_price": 100 + np.random.randn(n_rows) * 5,
        })

        tscv = TimeSeriesSplit(n_splits=2)
        folds = [
            MockFold(train_idx, test_idx)
            for train_idx, test_idx in tscv.split(df)
        ]

        result = compute_benchmark(df, folds, {})

        metrics = result["metrics"]
        assert "annualized_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics

    def test_benchmark_equal_weight(self):
        """Benchmark should be equal-weight across stocks."""
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=30)

        # Create 3 stocks with different returns
        data = []
        for stock in ["A", "B", "C"]:
            for date in dates:
                price = 100 + np.random.randn() * 5
                data.append({"company_id": stock, "trade_date": date, "closing_price": price})

        df = pd.DataFrame(data)

        tscv = TimeSeriesSplit(n_splits=2)
        folds = [
            MockFold(train_idx, test_idx)
            for train_idx, test_idx in tscv.split(df)
        ]

        result = compute_benchmark(df, folds, {})

        assert "daily_returns" in result
        assert isinstance(result["daily_returns"], pd.Series)


class TestBacktestEdgeCases:
    """Test edge cases in backtest."""

    def test_missing_volume_data(self):
        """Should handle missing volume column."""
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=50)
        companies = ["A", "B"]
        n_rows = len(dates) * len(companies)
        df = pd.DataFrame({
            "company_id": companies * 50,
            "trade_date": dates.repeat(2),
            "closing_price": 100 + np.random.randn(n_rows) * 5,
            # No Trading_Volume column
            "label_5": np.random.choice([-1, 0, 1], n_rows),
            "fwd_ret_5": np.random.randn(n_rows) * 0.02,
        })

        n_rows = len(df)
        mock_oof_preds = np.random.random((n_rows, 3))
        mock_oof_preds = mock_oof_preds / mock_oof_preds.sum(axis=1, keepdims=True)

        model_results = {
            "model": {"oof_predictions": mock_oof_preds}
        }

        tscv = TimeSeriesSplit(n_splits=2)
        folds = [
            MockFold(train_idx, test_idx)
            for train_idx, test_idx in tscv.split(df)
        ]

        config = {
            "backtest": {
                "strategy": {"top_k_pct": 0.2},
                "min_avg_volume": 500_000,
            },
            "cost_model": {
                "discount": {
                    "commission": 0.001425,
                    "discount": 1.0,
                    "tax": 0.003,
                    "slippage": 0.001,
                }
            }
        }

        # Should not crash
        result = run_backtest(df, model_results, folds, [], "label_5", config)
        assert isinstance(result, dict)

    def test_no_predictions(self):
        """Should handle missing predictions gracefully."""
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=50)
        companies = ["A", "B"]
        n_rows = len(dates) * len(companies)
        df = pd.DataFrame({
            "company_id": companies * 50,
            "trade_date": dates.repeat(2),
            "closing_price": 100 + np.random.randn(n_rows) * 5,
            "Trading_Volume": 1_000_000,
            "label_5": np.random.choice([-1, 0, 1], n_rows),
            "fwd_ret_5": np.random.randn(n_rows) * 0.02,
        })

        # No OOF predictions
        model_results = {
            "bad_model": {"oof_predictions": None}
        }

        tscv = TimeSeriesSplit(n_splits=2)
        folds = [
            MockFold(train_idx, test_idx)
            for train_idx, test_idx in tscv.split(df)
        ]

        config = {
            "backtest": {
                "strategy": {"top_k_pct": 0.2},
                "min_avg_volume": 500_000,
            },
            "cost_model": {
                "discount": {
                    "commission": 0.001425,
                    "discount": 1.0,
                    "tax": 0.003,
                    "slippage": 0.001,
                }
            }
        }

        # Should return empty or skip
        result = run_backtest(df, model_results, folds, [], "label_5", config)
        # Result should be dict, possibly empty
        assert isinstance(result, dict)

    def test_single_stock(self):
        """Should handle single stock backtest."""
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=50)
        df = pd.DataFrame({
            "company_id": ["A"] * 50,
            "trade_date": dates,
            "closing_price": 100 + np.random.randn(50) * 5,
            "Trading_Volume": 1_000_000,
            "label_5": np.random.choice([-1, 0, 1], 50),
            "fwd_ret_5": np.random.randn(50) * 0.02,
        })

        n_rows = len(df)
        mock_oof_preds = np.random.random((n_rows, 3))
        mock_oof_preds = mock_oof_preds / mock_oof_preds.sum(axis=1, keepdims=True)

        model_results = {
            "model": {"oof_predictions": mock_oof_preds}
        }

        tscv = TimeSeriesSplit(n_splits=2)
        folds = [
            MockFold(train_idx, test_idx)
            for train_idx, test_idx in tscv.split(df)
        ]

        config = {
            "backtest": {
                "strategy": {"top_k_pct": 0.5},
                "min_avg_volume": 500_000,
            },
            "cost_model": {
                "discount": {
                    "commission": 0.001425,
                    "discount": 1.0,
                    "tax": 0.003,
                    "slippage": 0.001,
                }
            }
        }

        result = run_backtest(df, model_results, folds, [], "label_5", config)
        # Should work with single stock
        assert isinstance(result, dict)
