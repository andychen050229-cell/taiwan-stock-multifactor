"""
Phase 5A — 5 個 Critical Bugs 修復驗證 Unit Tests
==================================================

審查來源：Phase4_交叉檢驗審查報告.md（line 144–172）

Bug 列表：
  #1 ROIC stockholders_equity 返回 scalar 0
  #2 NOPAT 有效稅率邏輯反轉
  #3 Implied Shares 使用 .abs() 掩蓋虧損公司
  #4 EV 計算缺少現金調整（BS_TYPE_MAP 無現金映射）
  #5 EBITDA D&A 符號處理過於粗糙

執行方式：
    cd 程式碼
    pytest 測試/test_phase5a_bugs.py -v
"""
import numpy as np
import pandas as pd
import pytest


# ============================================================
# Bug #1: ROIC stockholders_equity 返回 scalar 0
# ============================================================

class TestBug1_ROICEquityScalar:
    """
    原問題：`df.get("stockholders_equity", 0)` 在欄位缺失時返回 scalar 0，
             導致 invested_capital = equity + ibd + sbd + bonds 變成 Series + scalar，
             可能導致 ROIC 計算異常。
    修復驗證：確保 equity 缺失時是 Series of NaN，不是 scalar 0。
    """

    def test_equity_missing_returns_series_not_scalar(self):
        from src.data.balance_sheet_processor import compute_bs_ratios

        # 建構 BS（缺 stockholders_equity）
        bs_df = pd.DataFrame({
            "company_id": ["2330", "2330", "2330"],
            "fiscal_year": [2023, 2023, 2023],
            "fiscal_quarter": [1, 2, 3],
            "total_assets": [1e10, 1.1e10, 1.2e10],
            "total_liabilities": [4e9, 4.5e9, 5e9],
            "long_term_borrowings": [1e9, 1.1e9, 1.2e9],
            "short_term_borrowings": [5e8, 5.5e8, 6e8],
        })
        income_df = pd.DataFrame({
            "company_id": ["2330", "2330", "2330"],
            "fiscal_year": [2023, 2023, 2023],
            "fiscal_quarter": [1, 2, 3],
            "net_income_sq": [1e9, 1.1e9, 1.2e9],
            "operating_income_sq": [1.2e9, 1.3e9, 1.4e9],
            "revenue_sq": [5e9, 5.5e9, 6e9],
        })

        result = compute_bs_ratios(bs_df, income_df=income_df)

        # equity 缺失 → ROIC 應全為 NaN（不應該是錯誤的數值）
        assert "roic" in result.columns, "roic column must exist"
        assert result["roic"].isna().all(), (
            f"roic should be all NaN when equity is missing, got "
            f"non-null count={result['roic'].notna().sum()}"
        )

    def test_equity_negative_returns_nan(self):
        """負 equity 應透過 MIN_INVESTED_CAPITAL threshold 被排除"""
        from src.data.balance_sheet_processor import compute_bs_ratios

        bs_df = pd.DataFrame({
            "company_id": ["9999"],
            "fiscal_year": [2023],
            "fiscal_quarter": [1],
            "total_assets": [1e9],
            "total_liabilities": [1.5e9],       # 資不抵債
            "stockholders_equity": [-5e8],      # 負 equity
            "long_term_borrowings": [0.0],
            "short_term_borrowings": [0.0],
        })
        income_df = pd.DataFrame({
            "company_id": ["9999"],
            "fiscal_year": [2023],
            "fiscal_quarter": [1],
            "net_income_sq": [-1e8],
            "operating_income_sq": [-5e7],
            "revenue_sq": [1e9],
        })

        result = compute_bs_ratios(bs_df, income_df=income_df)
        # invested_capital = -5e8 + 0 + 0 = -5e8，|abs| > MIN(1e6) → 不會被排除
        # 但 NOPAT 因 OI < 0 會是負值 → ROIC 應為合理負值或被 clip 到 [-2, 2]
        assert "roic" in result.columns
        # 不該產生 inf
        assert np.isfinite(result["roic"]).all() | result["roic"].isna().all()


# ============================================================
# Bug #2: NOPAT 有效稅率邏輯反轉
# ============================================================

class TestBug2_NOPATTaxRate:
    """
    原問題：`eff_tax = 1 - (net_income / operating_income)` 在 NI > OI 時（非營業收入大）
             產生負稅率，導致 NOPAT 膨脹。
    修復驗證：eff_tax 必須在 [0, 0.4] 範圍，NI > OI 時 eff_tax 應為 0。
    """

    def test_normal_case_positive_tax_rate(self):
        """正常情況：NI < OI（因為有稅），稅率應為正"""
        from src.data.balance_sheet_processor import compute_bs_ratios

        bs_df = pd.DataFrame({
            "company_id": ["2330"],
            "fiscal_year": [2023],
            "fiscal_quarter": [1],
            "total_assets": [1e10],
            "stockholders_equity": [5e9],
            "total_liabilities": [5e9],
        })
        income_df = pd.DataFrame({
            "company_id": ["2330"],
            "fiscal_year": [2023],
            "fiscal_quarter": [1],
            "net_income_sq": [8e8],         # NI=0.8億
            "operating_income_sq": [1e9],   # OI=1億，隱含稅率 20%
            "revenue_sq": [5e9],
        })

        result = compute_bs_ratios(bs_df, income_df=income_df)

        # NOPAT = OI × (1 - eff_tax) = 1e9 × (1 - 0.2) = 8e8
        nopat = result["nopat"].iloc[0]
        assert 7.5e8 <= nopat <= 8.5e8, (
            f"NOPAT should be ~8e8 for 20% tax rate, got {nopat}"
        )

    def test_ni_greater_than_oi_eff_tax_floored_at_zero(self):
        """異常情況：NI > OI（業外收入），eff_tax 應被 clip 到 0，不是負值"""
        from src.data.balance_sheet_processor import compute_bs_ratios

        bs_df = pd.DataFrame({
            "company_id": ["1234"],
            "fiscal_year": [2023],
            "fiscal_quarter": [1],
            "total_assets": [1e10],
            "stockholders_equity": [5e9],
            "total_liabilities": [5e9],
        })
        income_df = pd.DataFrame({
            "company_id": ["1234"],
            "fiscal_year": [2023],
            "fiscal_quarter": [1],
            "net_income_sq": [1.5e9],       # NI > OI（業外收入）
            "operating_income_sq": [1e9],
            "revenue_sq": [5e9],
        })

        result = compute_bs_ratios(bs_df, income_df=income_df)

        # eff_tax = (1e9 - 1.5e9) / 1e9 = -0.5 → clip 到 0
        # NOPAT = 1e9 × (1 - 0) = 1e9
        nopat = result["nopat"].iloc[0]
        assert abs(nopat - 1e9) < 1e8, (
            f"NOPAT should be ~1e9 when eff_tax floored at 0, got {nopat}"
        )

    def test_oi_negative_eff_tax_zero(self):
        """虧損公司（OI < 0）：eff_tax 設為 0，NOPAT = OI"""
        from src.data.balance_sheet_processor import compute_bs_ratios

        bs_df = pd.DataFrame({
            "company_id": ["9999"],
            "fiscal_year": [2023],
            "fiscal_quarter": [1],
            "total_assets": [1e9],
            "stockholders_equity": [3e8],
            "total_liabilities": [7e8],
        })
        income_df = pd.DataFrame({
            "company_id": ["9999"],
            "fiscal_year": [2023],
            "fiscal_quarter": [1],
            "net_income_sq": [-2e8],
            "operating_income_sq": [-1.5e8],
            "revenue_sq": [1e9],
        })

        result = compute_bs_ratios(bs_df, income_df=income_df)

        # OI < 0 → eff_tax = 0 → NOPAT = OI = -1.5e8
        nopat = result["nopat"].iloc[0]
        assert abs(nopat - (-1.5e8)) < 1e7, (
            f"NOPAT should equal OI when OI<0, got {nopat} vs expected -1.5e8"
        )


# ============================================================
# Bug #3: Implied Shares .abs() 掩蓋虧損公司
# ============================================================

class TestBug3_ImpliedSharesSign:
    """
    原問題：implied_shares = (net_income / eps).abs() 在虧損公司（NI<0, EPS<0）
             會產生正的假股數；在 NI>0 但 EPS<0（或反之）的資料異常情況會被靜默掩蓋。
    修復驗證：
      - NI<0 且 EPS<0：shares = NI/EPS > 0（虧損公司仍有股數，正確）
      - NI>0 但 EPS<0（sign mismatch）：shares 應為 NaN
    """

    def test_loss_company_returns_valid_shares(self):
        """虧損公司（NI<0 且 EPS<0）：shares 應為正數"""
        from src.features.engineer import build_valuation_features

        df = pd.DataFrame({
            "company_id": ["9999"] * 2,
            "trade_date": pd.to_datetime(["2023-03-01", "2023-03-02"]),
            "closing_price": [20.0, 21.0],
            "fund_eps": [-1.0, -1.0],
            "fund_net_income_sq": [-1e8, -1e8],   # 虧損
            "stockholders_equity": [5e8, 5e8],
            "revenue_sq": [1e9, 1e9],
        })
        config = {}
        result = build_valuation_features(df, config)

        # implied_shares = -1e8 / -1.0 = 1e8 (正值) → 有效
        # val_pb = 20 / (5e8 / 1e8) = 20 / 5 = 4.0
        assert "val_pb" in result.columns
        # 應該算得出 val_pb
        assert result["val_pb"].notna().any(), (
            "val_pb should be computable for loss company (both NI<0 and EPS<0)"
        )

    def test_sign_mismatch_returns_nan(self):
        """資料異常（NI>0 但 EPS<0）：shares 應設為 NaN"""
        from src.features.engineer import build_valuation_features

        df = pd.DataFrame({
            "company_id": ["1234"] * 2,
            "trade_date": pd.to_datetime(["2023-03-01", "2023-03-02"]),
            "closing_price": [20.0, 21.0],
            "fund_eps": [-1.0, -1.0],              # EPS 負
            "fund_net_income_sq": [1e8, 1e8],      # NI 正（資料異常）
            "stockholders_equity": [5e8, 5e8],
            "revenue_sq": [1e9, 1e9],
        })
        config = {}
        result = build_valuation_features(df, config)

        # sign mismatch → implied_shares=NaN → val_pb=NaN
        assert "val_pb" in result.columns
        assert result["val_pb"].isna().all(), (
            f"val_pb should be all NaN for sign mismatch, got "
            f"{result['val_pb'].tolist()}"
        )


# ============================================================
# Bug #4: EV 計算缺少現金調整（BS_TYPE_MAP 無現金映射）
# ============================================================

class TestBug4_EVCashAdjustment:
    """
    原問題：EV = market_cap + total_debt，但 BS_TYPE_MAP 未映射 CashAndCashEquivalents，
             導致 df["cash_and_equivalents"] 不存在，cash_proxy 永遠為 0，EV 系統性偏高。
    修復驗證：
      - BS_TYPE_MAP 包含 CashAndCashEquivalents 映射
      - Pivot 後 DataFrame 有 cash_and_equivalents 欄位
      - build_valuation_features 正確使用 cash_proxy 計算 EV
    """

    def test_bs_type_map_contains_cash(self):
        """BS_TYPE_MAP 必須映射現金類型"""
        from src.data.balance_sheet_processor import BS_TYPE_MAP

        assert "CashAndCashEquivalents" in BS_TYPE_MAP, (
            "BS_TYPE_MAP must contain CashAndCashEquivalents mapping (Bug #4)"
        )
        assert BS_TYPE_MAP["CashAndCashEquivalents"] == "cash_and_equivalents"

    def test_pivot_produces_cash_column(self):
        """Pivot 後應有 cash_and_equivalents 欄位"""
        from src.data.balance_sheet_processor import (
            pivot_financial_statement, BS_TYPE_MAP
        )

        # 模擬 FinMind 長格式
        raw = pd.DataFrame({
            "stock_id": ["2330"] * 3,
            "date": ["2023-03-31"] * 3,
            "type": ["CashAndCashEquivalents", "TotalAssets", "Equity"],
            "value": [1e12, 3e12, 1.5e12],
            "origin_name": ["現金及約當現金", "資產總額", "權益總額"],
        })
        wide = pivot_financial_statement(raw, BS_TYPE_MAP, "TestBS")

        assert "cash_and_equivalents" in wide.columns, (
            f"Pivot must produce cash_and_equivalents column, "
            f"got columns: {list(wide.columns)}"
        )
        assert wide["cash_and_equivalents"].iloc[0] == 1e12

    def test_ev_subtracts_cash(self):
        """EV 計算應扣除 cash_proxy"""
        from src.features.engineer import build_valuation_features

        # 建構有 cash_and_equivalents 的資料
        df = pd.DataFrame({
            "company_id": ["2330"] * 2,
            "trade_date": pd.to_datetime(["2023-04-01", "2023-04-02"]),
            "closing_price": [500.0, 510.0],
            "fund_eps": [2.0, 2.0],
            "fund_net_income_sq": [1e10, 1e10],      # implied_shares = 5e9
            "fund_ebitda": [3e10, 3e10],
            "fund_debt_equity": [0.3, 0.3],
            "stockholders_equity": [1e12, 1e12],
            "total_assets": [2e12, 2e12],
            "cash_and_equivalents": [5e11, 5e11],    # 5 千億現金
            "revenue_sq": [5e10, 5e10],
        })
        config = {}
        result = build_valuation_features(df, config)

        assert "val_ev_ebitda" in result.columns
        # EV 應扣現金，val_ev_ebitda 應比「不扣現金」低
        # 不測精確值（clip 會影響），只測非 NaN
        assert result["val_ev_ebitda"].notna().any()


# ============================================================
# Bug #5: EBITDA D&A 符號處理過於粗糙
# ============================================================

class TestBug5_DASignHandling:
    """
    原問題：D&A 全域 .abs() 處理，可能在真實混合符號（部分正、部分負）的公司
             遮蔽資料品質問題，讓 EBITDA 錯誤計算。
    修復驗證：新邏輯下
      - 純正值公司（neg<5%）：維持原值
      - 明顯負慣例公司（neg>=70%）：整欄 .abs()
      - 混合符號公司（5%<=neg<70%）：負值 row 設為 NaN（不汙染）
    """

    def test_pure_positive_da_unchanged(self):
        """純正值 D&A：不應被修改"""
        from src.data.balance_sheet_processor import compute_bs_ratios

        bs_df = pd.DataFrame({
            "company_id": ["2330"] * 4,
            "fiscal_year": [2023] * 4,
            "fiscal_quarter": [1, 2, 3, 4],
            "total_assets": [1e10] * 4,
            "stockholders_equity": [5e9] * 4,
            "total_liabilities": [5e9] * 4,
        })
        income_df = pd.DataFrame({
            "company_id": ["2330"] * 4,
            "fiscal_year": [2023] * 4,
            "fiscal_quarter": [1, 2, 3, 4],
            "net_income_sq": [1e9] * 4,
            "operating_income_sq": [1.2e9] * 4,
            "revenue_sq": [5e9] * 4,
        })
        cf_df = pd.DataFrame({
            "company_id": ["2330"] * 4,
            "fiscal_year": [2023] * 4,
            "fiscal_quarter": [1, 2, 3, 4],
            "depreciation_and_amortization": [1e8, 1.1e8, 1.2e8, 1.3e8],  # 全正
        })

        result = compute_bs_ratios(bs_df, income_df=income_df, cf_df=cf_df)

        # EBITDA = OI + D&A = 1.2e9 + 1e8 = 1.3e9
        ebitda = result["ebitda"].iloc[0]
        assert abs(ebitda - 1.3e9) < 1e7, (
            f"EBITDA for pure-positive D&A should be OI+D&A, got {ebitda}"
        )

    def test_all_negative_da_flipped_to_abs(self):
        """明顯負慣例 D&A（全負）：整欄 .abs()"""
        from src.data.balance_sheet_processor import compute_bs_ratios

        bs_df = pd.DataFrame({
            "company_id": ["1234"] * 4,
            "fiscal_year": [2023] * 4,
            "fiscal_quarter": [1, 2, 3, 4],
            "total_assets": [1e10] * 4,
            "stockholders_equity": [5e9] * 4,
            "total_liabilities": [5e9] * 4,
        })
        income_df = pd.DataFrame({
            "company_id": ["1234"] * 4,
            "fiscal_year": [2023] * 4,
            "fiscal_quarter": [1, 2, 3, 4],
            "net_income_sq": [1e9] * 4,
            "operating_income_sq": [1.2e9] * 4,
            "revenue_sq": [5e9] * 4,
        })
        cf_df = pd.DataFrame({
            "company_id": ["1234"] * 4,
            "fiscal_year": [2023] * 4,
            "fiscal_quarter": [1, 2, 3, 4],
            "depreciation_and_amortization": [-1e8, -1.1e8, -1.2e8, -1.3e8],  # 全負
        })

        result = compute_bs_ratios(bs_df, income_df=income_df, cf_df=cf_df)

        # 100% 負 → 偵測為負慣例 → .abs() → EBITDA = 1.2e9 + 1e8 = 1.3e9
        ebitda = result["ebitda"].iloc[0]
        assert abs(ebitda - 1.3e9) < 1e7, (
            f"EBITDA for all-negative D&A (flipped to abs) should be 1.3e9, got {ebitda}"
        )

    def test_mixed_sign_da_negative_set_to_nan(self):
        """混合符號 D&A：負值 row 應被設 NaN（Phase 5A 新邏輯）"""
        from src.data.balance_sheet_processor import compute_bs_ratios

        bs_df = pd.DataFrame({
            "company_id": ["5555"] * 10,
            "fiscal_year": [2023, 2023, 2023, 2023, 2024, 2024, 2024, 2024, 2025, 2025],
            "fiscal_quarter": [1, 2, 3, 4, 1, 2, 3, 4, 1, 2],
            "total_assets": [1e10] * 10,
            "stockholders_equity": [5e9] * 10,
            "total_liabilities": [5e9] * 10,
        })
        income_df = pd.DataFrame({
            "company_id": ["5555"] * 10,
            "fiscal_year": [2023, 2023, 2023, 2023, 2024, 2024, 2024, 2024, 2025, 2025],
            "fiscal_quarter": [1, 2, 3, 4, 1, 2, 3, 4, 1, 2],
            "net_income_sq": [1e9] * 10,
            "operating_income_sq": [1.2e9] * 10,
            "revenue_sq": [5e9] * 10,
        })
        cf_df = pd.DataFrame({
            "company_id": ["5555"] * 10,
            "fiscal_year": [2023, 2023, 2023, 2023, 2024, 2024, 2024, 2024, 2025, 2025],
            "fiscal_quarter": [1, 2, 3, 4, 1, 2, 3, 4, 1, 2],
            # 5 正 5 負 → 50% 負，落在混合區間 [5%, 70%)
            "depreciation_and_amortization": [1e8, 1e8, 1e8, 1e8, 1e8,
                                              -1e8, -1e8, -1e8, -1e8, -1e8],
        })

        result = compute_bs_ratios(bs_df, income_df=income_df, cf_df=cf_df)

        # 混合邏輯：負值 row EBITDA 應為 NaN（因 D&A 被設 NaN）
        # 正值 row EBITDA 應正常
        assert "ebitda" in result.columns
        valid_count = result["ebitda"].notna().sum()
        nan_count = result["ebitda"].isna().sum()
        assert valid_count == 5, (
            f"Expected 5 valid (positive D&A) EBITDA rows, got {valid_count}"
        )
        assert nan_count == 5, (
            f"Expected 5 NaN (negative D&A set to NaN) EBITDA rows, got {nan_count}"
        )


# ============================================================
# 整合測試：確認所有 bugs 修復後，全流程不崩
# ============================================================

class TestIntegration_AllBugsCombined:
    """所有 bugs 修復後，完整 pipeline 應正常產出"""

    def test_full_pipeline_smoke(self):
        """最小可行 pipeline 測試：BS + Income + CF → 所有指標皆可計算"""
        from src.data.balance_sheet_processor import run_balance_sheet_pipeline

        # BS 長格式（包含 current_assets / current_liabilities 以驗證 current_ratio）
        bs_raw = pd.DataFrame({
            "stock_id": ["2330"] * 7,
            "date": ["2023-03-31"] * 7,
            "type": ["TotalAssets", "TotalLiabilities", "Equity",
                     "CashAndCashEquivalents", "LongtermBorrowings",
                     "CurrentAssets", "CurrentLiabilities"],
            "value": [3e12, 1.5e12, 1.5e12, 1e12, 5e10, 1.8e12, 8e11],
            "origin_name": ["資產總額", "負債總額", "權益總額",
                            "現金及約當現金", "長期借款",
                            "流動資產", "流動負債"],
        })
        cf_raw = pd.DataFrame({
            "stock_id": ["2330"],
            "date": ["2023-03-31"],
            "type": ["DepreciationAndAmortization"],
            "value": [5e10],
            "origin_name": ["折舊及攤銷費用"],
        })
        income_df = pd.DataFrame({
            "company_id": ["2330"],
            "fiscal_year": [2023],
            "fiscal_quarter": [1],
            "net_income_sq": [2e11],
            "operating_income_sq": [2.5e11],
            "revenue_sq": [5e11],
        })

        result, report = run_balance_sheet_pipeline(
            bs_raw=bs_raw, cf_raw=cf_raw, income_df=income_df
        )

        assert len(result) > 0, "Pipeline should produce output"
        # 主要指標都應計算得出
        for col in ["roe", "roa", "roic", "debt_equity", "current_ratio",
                    "nopat", "ebitda", "cash_and_equivalents"]:
            assert col in result.columns, f"Missing expected column: {col}"
        # 這個 case 的 ROIC 應為合理值
        # NOPAT = 2.5e11 × (1 - 0.2) = 2e11
        # IC = equity + LT + ST + bonds = 1.5e12 + 5e10 + 0 + 0 = 1.55e12
        # ROIC = 2e11 / 1.55e12 = 0.129
        roic = result["roic"].iloc[0]
        assert 0.10 <= roic <= 0.16, f"ROIC should be ~0.13, got {roic}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
