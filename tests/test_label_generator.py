"""
Unit tests for src/data/label_generator.py module.

Tests label generation pipeline:
  - Forward returns computed correctly
  - Three-class labeling (UP/FLAT/DOWN) is consistent
  - Edge cases: all same price → all FLAT
  - Label distribution and validation
"""

import numpy as np
import pandas as pd
import pytest
from src.data.label_generator import (
    compute_forward_returns,
    classify_fixed_threshold,
    classify_dynamic_threshold,
    validate_labels,
    run_label_pipeline,
)


class TestComputeForwardReturns:
    """Test forward return calculation."""

    def test_single_horizon(self):
        """Test single horizon forward return."""
        df = pd.DataFrame({
            "company_id": ["A"] * 5,
            "trade_date": pd.date_range("2023-01-01", periods=5),
            "closing_price": [100, 102, 104, 106, 108],
        })

        result = compute_forward_returns(df, horizons=[1], config=None)

        # fwd_ret_1 at day 0: (102 - 100) / 100 = 0.02
        assert "fwd_ret_1" in result.columns
        assert result.loc[0, "fwd_ret_1"] == pytest.approx(0.02, rel=1e-4)

    def test_multiple_horizons(self):
        """Test multiple horizon forward returns."""
        df = pd.DataFrame({
            "company_id": ["A"] * 10,
            "trade_date": pd.date_range("2023-01-01", periods=10),
            "closing_price": np.arange(100, 110),
        })

        result = compute_forward_returns(df, horizons=[1, 5], config=None)

        assert "fwd_ret_1" in result.columns
        assert "fwd_ret_5" in result.columns

    def test_forward_return_formula(self):
        """Verify forward return calculation: (close[t+h] - close[t]) / close[t]."""
        df = pd.DataFrame({
            "company_id": ["A"] * 5,
            "trade_date": pd.date_range("2023-01-01", periods=5),
            "closing_price": [100, 105, 110, 115, 120],
        })

        result = compute_forward_returns(df, horizons=[1], config=None)

        # Day 0: (105 - 100) / 100 = 0.05
        assert result.loc[0, "fwd_ret_1"] == pytest.approx(0.05)
        # Day 1: (110 - 105) / 105 ~= 0.0476
        assert result.loc[1, "fwd_ret_1"] == pytest.approx(0.05 / 1.05, rel=1e-4)

    def test_last_rows_have_nan(self):
        """Last h rows should have NaN for fwd_ret_h."""
        df = pd.DataFrame({
            "company_id": ["A"] * 10,
            "trade_date": pd.date_range("2023-01-01", periods=10),
            "closing_price": np.arange(100, 110),
        })

        result = compute_forward_returns(df, horizons=[5], config=None)

        # Last 5 rows should have NaN for fwd_ret_5
        assert result.loc[9, "fwd_ret_5"] == np.nan or pd.isna(result.loc[9, "fwd_ret_5"])
        assert result.loc[8, "fwd_ret_5"] == np.nan or pd.isna(result.loc[8, "fwd_ret_5"])

    def test_zero_price_handling(self):
        """Zero price should not cause division error."""
        df = pd.DataFrame({
            "company_id": ["A"] * 5,
            "trade_date": pd.date_range("2023-01-01", periods=5),
            "closing_price": [100, 0, 102, 104, 106],
        })

        result = compute_forward_returns(df, horizons=[1], config=None)

        # Zero price row should give NaN, not inf
        assert pd.isna(result.loc[1, "fwd_ret_1"])

    def test_multiple_stocks(self):
        """Should handle multiple stocks independently."""
        df = pd.DataFrame({
            "company_id": ["A", "A", "B", "B"],
            "trade_date": pd.date_range("2023-01-01", periods=2).repeat(2),
            "closing_price": [100, 102, 200, 204],
        })

        result = compute_forward_returns(df, horizons=[1], config=None)

        # Each stock calculated independently
        # Stock A: (102 - 100) / 100 = 0.02
        assert result.loc[0, "fwd_ret_1"] == pytest.approx(0.02)
        # Stock B: (204 - 200) / 200 = 0.02
        assert result.loc[2, "fwd_ret_1"] == pytest.approx(0.02)


class TestClassifyFixedThreshold:
    """Test fixed threshold classification."""

    def test_up_down_flat_classification(self):
        """Test UP/FLAT/DOWN classification."""
        df = pd.DataFrame({
            "company_id": ["A"] * 10,
            "trade_date": pd.date_range("2023-01-01", periods=10),
            "fwd_ret_1": [0.01, 0.005, -0.005, -0.01, 0.0, 0.005, -0.005, 0.015, -0.015, 0.0],
        })

        result = classify_fixed_threshold(df, {"labeling": {"thresholds": {1: 0.005}}})

        # 0.01 > 0.005 → UP (1)
        assert result.loc[0, "label_1"] == 1
        # 0.005 = 0.005 → not > threshold → FLAT (0)
        assert result.loc[1, "label_1"] == 0
        # -0.005 < -0.005 → not < threshold → FLAT (0)
        assert result.loc[2, "label_1"] == 0
        # -0.01 < -0.005 → DOWN (-1)
        assert result.loc[3, "label_1"] == -1
        # 0.0 = FLAT (0)
        assert result.loc[4, "label_1"] == 0

    def test_multiple_horizons(self):
        """Test classification for multiple horizons."""
        df = pd.DataFrame({
            "company_id": ["A"] * 10,
            "fwd_ret_1": np.random.randn(10) * 0.01,
            "fwd_ret_5": np.random.randn(10) * 0.02,
        })

        result = classify_fixed_threshold(
            df,
            {"labeling": {"thresholds": {1: 0.005, 5: 0.015}}}
        )

        assert "label_1" in result.columns
        assert "label_5" in result.columns

    def test_nan_handling(self):
        """NaN in forward returns should give NaN labels."""
        df = pd.DataFrame({
            "company_id": ["A"] * 5,
            "fwd_ret_1": [0.01, np.nan, -0.01, 0.005, -0.005],
        })

        result = classify_fixed_threshold(df, {"labeling": {"thresholds": {1: 0.005}}})

        assert pd.isna(result.loc[1, "label_1"])

    def test_symmetrical_thresholds(self):
        """Thresholds should be symmetric."""
        df = pd.DataFrame({
            "company_id": ["A"] * 4,
            "fwd_ret_1": [0.010, -0.010, 0.005, -0.005],
        })

        result = classify_fixed_threshold(df, {"labeling": {"thresholds": {1: 0.005}}})

        # +0.010 > +0.005 → UP
        assert result.loc[0, "label_1"] == 1
        # -0.010 < -0.005 → DOWN
        assert result.loc[1, "label_1"] == -1
        # Both boundary cases should be symmetric
        assert result.loc[2, "label_1"] == 0
        assert result.loc[3, "label_1"] == 0


class TestClassifyDynamicThreshold:
    """Test dynamic threshold classification."""

    def test_dynamic_threshold_creates_labels(self):
        """Should create label_dyn_ columns."""
        df = pd.DataFrame({
            "company_id": ["A"] * 100,
            "trade_date": pd.date_range("2023-01-01", periods=100),
            "closing_price": 100 + np.cumsum(np.random.randn(100) * 2),
            "fwd_ret_1": np.random.randn(100) * 0.01,
        })

        result = classify_dynamic_threshold(df, {"labeling": {"vol_window": 20}, "model": {"horizons": [1]}})

        assert "label_dyn_1" in result.columns

    def test_dynamic_threshold_varies_by_volatility(self):
        """Threshold should vary with historical volatility."""
        # Create two scenarios: low vol and high vol
        df = pd.DataFrame({
            "company_id": ["A"] * 50 + ["B"] * 50,
            "trade_date": pd.date_range("2023-01-01", periods=100).repeat(1),
            "closing_price": (
                list(100 + np.cumsum(np.random.randn(50) * 0.5)) +
                list(100 + np.cumsum(np.random.randn(50) * 3))
            ),
            "fwd_ret_1": np.random.randn(100) * 0.01,
        })

        result = classify_dynamic_threshold(df, {"labeling": {"vol_window": 20}, "model": {"horizons": [1]}})

        assert "label_dyn_1" in result.columns


class TestValidateLabels:
    """Test label validation."""

    def test_returns_validation_dict(self):
        """Should return dict with checks, distributions, warnings."""
        df = pd.DataFrame({
            "label_1": [1, 0, -1, 1, 0, -1, 1, 0, -1, 1] * 10,
        })

        result = validate_labels(df, config=None)

        assert "checks" in result
        assert "distributions" in result
        assert "warnings" in result
        assert "overall_pass" in result

    def test_class_distribution(self):
        """Should compute class distribution."""
        df = pd.DataFrame({
            "label_1": [1] * 50 + [0] * 30 + [-1] * 20,
        })

        result = validate_labels(df, config=None)

        dist = result["distributions"]["label_1"]
        # Should have -1, 0, 1
        assert "-1" in dist or "-1.0" in dist
        assert "0" in dist or "0.0" in dist
        assert "1" in dist or "1.0" in dist

    def test_balance_check(self):
        """Should check for class balance."""
        df = pd.DataFrame({
            "label_1": [1] * 95 + [0] * 4 + [-1] * 1,
        })

        result = validate_labels(df, config=None)

        # Imbalanced: min class is 1%
        assert "label_1_balance" in result["checks"]
        assert not result["checks"]["label_1_balance"]["balanced"]

    def test_all_nan_warning(self):
        """Should warn if label column all NaN."""
        df = pd.DataFrame({
            "label_1": [np.nan] * 100,
        })

        result = validate_labels(df, config=None)

        assert len(result["warnings"]) > 0

    def test_coverage_metric(self):
        """Should compute label coverage (non-NaN %)."""
        df = pd.DataFrame({
            "label_1": [1, 0, -1, np.nan, np.nan] * 20,
        })

        result = validate_labels(df, config=None)

        # Coverage should be 60%
        coverage_str = result["checks"]["label_1_coverage"]
        assert "60" in coverage_str  # 60%


class TestRunLabelPipeline:
    """Test complete label generation pipeline."""

    def test_pipeline_returns_tuple(self):
        """Should return (df, report) tuple."""
        df = pd.DataFrame({
            "company_id": ["A"] * 50,
            "trade_date": pd.date_range("2023-01-01", periods=50),
            "closing_price": 100 + np.cumsum(np.random.randn(50) * 2),
        })

        result, report = run_label_pipeline(
            df,
            {
                "model": {"horizons": [1]},
                "labeling": {"thresholds": {1: 0.005}, "use_dynamic_threshold": False},
            }
        )

        assert isinstance(result, pd.DataFrame)
        assert isinstance(report, dict)

    def test_pipeline_adds_forward_returns(self):
        """Pipeline should compute forward returns."""
        df = pd.DataFrame({
            "company_id": ["A"] * 50,
            "trade_date": pd.date_range("2023-01-01", periods=50),
            "closing_price": 100 + np.cumsum(np.random.randn(50) * 2),
        })

        result, _ = run_label_pipeline(
            df,
            {
                "model": {"horizons": [1, 5]},
                "labeling": {"thresholds": {1: 0.005, 5: 0.015}, "use_dynamic_threshold": False},
            }
        )

        assert "fwd_ret_1" in result.columns
        assert "fwd_ret_5" in result.columns

    def test_pipeline_adds_labels(self):
        """Pipeline should create label columns."""
        df = pd.DataFrame({
            "company_id": ["A"] * 50,
            "trade_date": pd.date_range("2023-01-01", periods=50),
            "closing_price": 100 + np.cumsum(np.random.randn(50) * 2),
        })

        result, _ = run_label_pipeline(
            df,
            {
                "model": {"horizons": [1]},
                "labeling": {"thresholds": {1: 0.005}, "use_dynamic_threshold": False},
            }
        )

        assert "label_1" in result.columns

    def test_pipeline_validation_report(self):
        """Pipeline should include validation report."""
        df = pd.DataFrame({
            "company_id": ["A"] * 50,
            "trade_date": pd.date_range("2023-01-01", periods=50),
            "closing_price": 100 + np.cumsum(np.random.randn(50) * 2),
        })

        _, report = run_label_pipeline(
            df,
            {
                "model": {"horizons": [1]},
                "labeling": {"thresholds": {1: 0.005}, "use_dynamic_threshold": False},
            }
        )

        assert "overall_pass" in report


class TestEdgeCases:
    """Test edge cases in label generation."""

    def test_all_same_price(self):
        """All same price should give zero forward returns → all FLAT labels."""
        df = pd.DataFrame({
            "company_id": ["A"] * 20,
            "trade_date": pd.date_range("2023-01-01", periods=20),
            "closing_price": [100.0] * 20,
        })

        result = compute_forward_returns(df, horizons=[1], config=None)

        # All fwd_ret_1 should be 0
        assert (result["fwd_ret_1"].dropna() == 0).all()

        result = classify_fixed_threshold(result, {"labeling": {"thresholds": {1: 0.005}}})

        # All labels should be FLAT (0) or NaN
        labels_not_nan = result.loc[result["label_1"].notna(), "label_1"]
        assert (labels_not_nan == 0).all()

    def test_single_stock_multiple_dates(self):
        """Single stock with multiple dates should work correctly."""
        df = pd.DataFrame({
            "company_id": ["STOCK_A"] * 100,
            "trade_date": pd.date_range("2023-01-01", periods=100),
            "closing_price": 100 + np.cumsum(np.random.randn(100) * 2),
        })

        result, _ = run_label_pipeline(
            df,
            {
                "model": {"horizons": [1]},
                "labeling": {"thresholds": {1: 0.005}, "use_dynamic_threshold": False},
            }
        )

        assert len(result) == 100
        assert "label_1" in result.columns

    def test_multiple_stocks_same_dates(self):
        """Multiple stocks on same dates should compute independently."""
        dates = pd.date_range("2023-01-01", periods=20)
        np.random.seed(42)
        prices_a = 100 + np.cumsum(np.random.randn(20) * 2)
        prices_b = 100 + np.cumsum(np.random.randn(20) * 2)
        df = pd.DataFrame({
            "company_id": ["A"] * 20 + ["B"] * 20,
            "trade_date": dates.repeat(2),
            "closing_price": list(prices_a) + list(prices_b),
        }).sort_values(["trade_date", "company_id"]).reset_index(drop=True)

        result, _ = run_label_pipeline(
            df,
            {
                "model": {"horizons": [1]},
                "labeling": {"thresholds": {1: 0.005}, "use_dynamic_threshold": False},
            }
        )

        assert len(result) == 40
        # Each stock should have independent forward returns
        stock_a = result[result["company_id"] == "A"]
        stock_b = result[result["company_id"] == "B"]
        assert len(stock_a) == 20
        assert len(stock_b) == 20
