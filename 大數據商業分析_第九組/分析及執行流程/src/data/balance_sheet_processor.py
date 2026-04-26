"""
資產負債表 + 現金流量表資料處理模組 (Phase 4)
=============================================

處理流程：
  1. Long → Wide Pivot（FinMind 回傳的長格式轉成每公司每季一行）
  2. 推算 fiscal_year / fiscal_quarter
  3. PIT 日期估算（共用損益表相同的台灣 IFRS 法定期限）
  4. 衍生指標計算（ROE, ROA, ROIC, EBITDA, D/E 等）
  5. 品質檢查
"""
import pandas as pd
import numpy as np
from loguru import logger
from ..utils.helpers import timer

# 共用 PIT 期限（與 financial_processor.py 一致）
PIT_DEADLINES = {
    1: {"month": 5, "day": 15},
    2: {"month": 8, "day": 14},
    3: {"month": 11, "day": 14},
    4: {"month": 3, "day": 31, "next_year": True},
}

# ============================================================
# L1: 可調參數集中管理（未來可遷移至 config.yaml）
# ============================================================
CLIP_RANGES = {
    "debt_equity": (0, 10),
    "current_ratio": (0, 10),
    "roe": (-2, 2),
    "roa": (-1, 1),
    "roic": (-2, 2),
    "ebitda_margin": (-0.5, 1.0),
}
TAX_RATE_CLIP = (0, 0.4)
TAX_RATE_FALLBACK = 0.17           # 台灣上市公司中位數有效稅率
MIN_INVESTED_CAPITAL = 1e6         # 100萬 TWD，避免 ROIC 極端值
ACCOUNTING_TOLERANCE = 0.005       # 會計恆等式容差 0.5%

# ============================================================
# 科目名稱映射表（中英文 → 統一欄位名）
# ============================================================

BS_TYPE_MAP = {
    # 中文
    "資產總額": "total_assets",
    "資產總計": "total_assets",
    "負債總額": "total_liabilities",
    "負債總計": "total_liabilities",
    "股東權益總額": "stockholders_equity",
    "權益總額": "stockholders_equity",
    "權益總計": "stockholders_equity",
    "歸屬於母公司業主之權益合計": "stockholders_equity",
    "流動資產合計": "current_assets",
    "流動資產": "current_assets",
    "流動負債合計": "current_liabilities",
    "流動負債": "current_liabilities",
    "長期借款": "long_term_borrowings",
    "短期借款": "short_term_borrowings",
    "短期票券": "short_term_notes",
    "非流動資產合計": "non_current_assets",
    "非流動負債合計": "non_current_liabilities",
    # English IFRS type names
    "TotalAssets": "total_assets",
    "TotalLiabilities": "total_liabilities",
    "StockholdersEquity": "stockholders_equity",
    "Equity": "stockholders_equity",
    "CurrentAssets": "current_assets",
    "CurrentLiabilities": "current_liabilities",
    "LongTermBorrowings": "long_term_borrowings",
    "LongtermBorrowings": "long_term_borrowings",       # FinMind 實際欄位名
    "ShortTermBorrowings": "short_term_borrowings",
    "ShorttermBorrowings": "short_term_borrowings",     # FinMind 實際欄位名
    "NonCurrentAssets": "non_current_assets",
    "NoncurrentAssets": "non_current_assets",            # FinMind 實際欄位名
    "NonCurrentLiabilities": "non_current_liabilities",
    "NoncurrentLiabilities": "non_current_liabilities",  # FinMind 實際欄位名
    "AccountsReceivableNet": "accounts_receivable",      # FinMind 實際欄位名
    "BondsPayable": "bonds_payable",                     # 公司債（補充債務項）
    # === Phase 5A Bug #4 fix: 加入現金科目（原本未映射，導致 cash_proxy=0） ===
    "現金及約當現金": "cash_and_equivalents",
    "CashAndCashEquivalents": "cash_and_equivalents",
    # === Phase 5A 追加：股本/保留盈餘/資本公積，供未來使用（不影響現有邏輯）===
    "OrdinaryShare": "ordinary_share",                   # 股本金額（元），÷面額=股數
    "CapitalStock": "capital_stock",                     # 股本（總額）
    "RetainedEarnings": "retained_earnings",             # 保留盈餘
    "CapitalSurplus": "capital_surplus",                 # 資本公積
    "PropertyPlantAndEquipment": "ppe",                  # 不動產廠房設備
}

CF_TYPE_MAP = {
    "折舊費用": "depreciation",
    "攤銷費用": "amortization",
    "折舊及攤銷費用": "depreciation_and_amortization",
    "不動產、廠房及設備折舊費用": "depreciation",
    "DepreciationExpense": "depreciation",
    "AmortizationExpense": "amortization",
    "DepreciationAndAmortization": "depreciation_and_amortization",
}


# ============================================================
# 1. Long → Wide Pivot
# ============================================================

@timer
def pivot_financial_statement(df: pd.DataFrame, type_map: dict, name: str) -> pd.DataFrame:
    """
    將 FinMind 長格式財報轉為寬格式（每公司每季一行）。

    FinMind 格式: date, stock_id, type, value, origin_name
    輸出格式: company_id, date, total_assets, stockholders_equity, ...
    """
    if df is None or len(df) == 0:
        logger.warning(f"No {name} data to pivot.")
        return pd.DataFrame()

    df = df.copy()

    # 標準化 type → 統一欄位名
    df["mapped_type"] = df["type"].map(type_map)

    # 也嘗試用 origin_name 映射
    if "origin_name" in df.columns:
        unmapped = df["mapped_type"].isna()
        df.loc[unmapped, "mapped_type"] = df.loc[unmapped, "origin_name"].map(type_map)

    # 只保留有映射的科目
    mapped = df[df["mapped_type"].notna()].copy()
    dropped = len(df) - len(mapped)
    logger.info(f"  {name}: {len(mapped):,} mapped / {len(df):,} total ({dropped:,} unmapped)")

    if len(mapped) == 0:
        logger.warning(f"No mapped items for {name}! Check type_map against actual data.")
        logger.info(f"  Top 20 types in data: {df['type'].value_counts().head(20).to_dict()}")
        return pd.DataFrame()

    # 確保 value 是數值
    mapped["value"] = pd.to_numeric(mapped["value"], errors="coerce")

    # Pivot: 同一 stock_id + date 如果有多個相同 mapped_type，取最後一個
    mapped = mapped.drop_duplicates(subset=["stock_id", "date", "mapped_type"], keep="last")

    pivoted = mapped.pivot_table(
        index=["stock_id", "date"],
        columns="mapped_type",
        values="value",
        aggfunc="first",
    ).reset_index()

    pivoted.columns.name = None
    pivoted = pivoted.rename(columns={"stock_id": "company_id"})

    logger.info(f"  Pivoted {name}: {pivoted.shape[0]:,} rows × {pivoted.shape[1]} cols")
    logger.info(f"  Columns: {[c for c in pivoted.columns if c not in ['company_id', 'date']]}")

    return pivoted


# ============================================================
# 2. 推算 fiscal_year / fiscal_quarter + PIT
# ============================================================

@timer
def assign_fiscal_period_and_pit(df: pd.DataFrame) -> pd.DataFrame:
    """從 date 欄位推算 fiscal_year, fiscal_quarter，再估算 PIT 日期。"""
    if df is None or len(df) == 0:
        return df

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # 從季報日期推算 fiscal_year, fiscal_quarter
    df["fiscal_year"] = df["date"].dt.year
    month = df["date"].dt.month
    df["fiscal_quarter"] = pd.cut(
        month, bins=[0, 3, 6, 9, 12], labels=[1, 2, 3, 4]
    ).astype("Int64")

    # PIT 日期
    pit_dates = []
    for _, row in df.iterrows():
        year = int(row["fiscal_year"])
        quarter = int(row["fiscal_quarter"])
        dl = PIT_DEADLINES.get(quarter, {})
        pit_year = year + 1 if dl.get("next_year", False) else year
        try:
            pit_dates.append(pd.Timestamp(year=pit_year, month=dl["month"], day=dl["day"]))
        except (ValueError, KeyError):
            pit_dates.append(pd.NaT)

    df["pit_date"] = pit_dates

    non_null = df["pit_date"].notna().sum()
    logger.info(f"  Fiscal period + PIT assigned: {non_null}/{len(df)} rows")

    return df


# ============================================================
# 3. 衍生指標
# ============================================================

@timer
def compute_bs_ratios(bs_df: pd.DataFrame, income_df: pd.DataFrame = None,
                      cf_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    從資產負債表計算衍生指標，可選擇性合併損益表與現金流量表資料。

    新增欄位：
      - roe: ROE = net_income_sq / avg(stockholders_equity)
      - roa: ROA = net_income_sq / avg(total_assets)
      - debt_equity: D/E = total_liabilities / stockholders_equity
      - current_ratio: 流動比率
      - roic: ROIC = NOPAT / invested_capital
      - ebitda: EBITDA (若有現金流量表的 D&A)
    """
    df = bs_df.copy()

    # 🔴3 fix: 確保按公司+時間排序，讓 groupby().shift(1) 取到正確的「前期」
    sort_cols = [c for c in ["company_id", "fiscal_year", "fiscal_quarter"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)

    # --- 純資產負債表指標 ---

    # [M2] D/E Ratio — clip 收緊到 [0, 10]
    if "total_liabilities" in df.columns and "stockholders_equity" in df.columns:
        safe_eq = df["stockholders_equity"].replace(0, np.nan)
        de_raw = df["total_liabilities"] / safe_eq
        n_neg_eq = (df["stockholders_equity"] <= 0).sum()
        if n_neg_eq > 0:
            logger.warning(f"  debt_equity: {n_neg_eq} rows with zero/negative equity → NaN")
        df["debt_equity"] = de_raw.clip(*CLIP_RANGES["debt_equity"])
        logger.info(f"  debt_equity: mean={df['debt_equity'].mean():.2f}, NaN%={df['debt_equity'].isna().mean()*100:.1f}%")

    # [M2] Current Ratio
    if "current_assets" in df.columns and "current_liabilities" in df.columns:
        safe_cl = df["current_liabilities"].replace(0, np.nan)
        df["current_ratio"] = (df["current_assets"] / safe_cl).clip(*CLIP_RANGES["current_ratio"])
        logger.info(f"  current_ratio: mean={df['current_ratio'].mean():.2f}")

    # --- 需合併損益表的指標 ---
    if income_df is not None and len(income_df) > 0:
        # 合併損益表的 net_income_sq, operating_income_sq
        inc_cols = ["company_id", "fiscal_year", "fiscal_quarter",
                    "net_income_sq", "operating_income_sq", "revenue_sq"]
        available = [c for c in inc_cols if c in income_df.columns]

        if "company_id" in available and "fiscal_year" in available:
            inc_merge = income_df[available].copy()

            df = df.merge(
                inc_merge,
                on=["company_id", "fiscal_year", "fiscal_quarter"],
                how="left",
                suffixes=("", "_inc"),
            )

            # [H1] ROE — 使用期間平均 equity（若有前期資料）
            if "net_income_sq" in df.columns and "stockholders_equity" in df.columns:
                eq_series = df["stockholders_equity"]
                # 嘗試計算 rolling 平均（同公司前後期平均）
                if "company_id" in df.columns:
                    prev_eq = df.groupby("company_id")["stockholders_equity"].shift(1)
                    avg_eq = (eq_series + prev_eq) / 2
                    avg_eq = avg_eq.fillna(eq_series)  # 首期無前期時用當期
                else:
                    avg_eq = eq_series
                safe_eq = avg_eq.where(avg_eq > 0, np.nan)
                df["roe"] = (df["net_income_sq"] / safe_eq).clip(*CLIP_RANGES["roe"])
                logger.info(f"  roe: mean={df['roe'].mean():.4f}, NaN%={df['roe'].isna().mean()*100:.1f}%")

            # [H1] ROA — 使用期間平均 total_assets
            if "net_income_sq" in df.columns and "total_assets" in df.columns:
                ta_series = df["total_assets"]
                if "company_id" in df.columns:
                    prev_ta = df.groupby("company_id")["total_assets"].shift(1)
                    avg_ta = (ta_series + prev_ta) / 2
                    avg_ta = avg_ta.fillna(ta_series)
                else:
                    avg_ta = ta_series
                safe_ta = avg_ta.where(avg_ta > 0, np.nan)
                df["roa"] = (df["net_income_sq"] / safe_ta).clip(*CLIP_RANGES["roa"])
                logger.info(f"  roa: mean={df['roa'].mean():.4f}, NaN%={df['roa'].isna().mean()*100:.1f}%")

            # Effective tax rate + NOPAT
            # Bug #2 fix: 正確公式 eff_tax = (OI - NI) / OI
            # 原邏輯 1 - (NI / OI) 等價，但在 NI > OI 時產生負稅率
            # 改用 tax_expense 直接除以 OI，並加強邊界處理
            # [C5] NOPAT — 改善有效稅率計算
            if "net_income_sq" in df.columns and "operating_income_sq" in df.columns:
                safe_oi = df["operating_income_sq"].replace(0, np.nan)
                # 有效稅率 = (OI - NI) / OI（近似值，包含非營業項目差異）
                tax_expense = df["operating_income_sq"] - df["net_income_sq"]
                eff_tax = (tax_expense / safe_oi)
                # 虧損公司 (OI <= 0) 稅率設為 0
                eff_tax = eff_tax.where(df["operating_income_sq"] > 0, 0.0)
                # clip [0, 0.4] (台灣最高邊際稅率 20%，加上附加稅等上限約 40%)
                # NaN fallback 改用 0.17（台灣上市公司有效稅率中位數）
                eff_tax = eff_tax.clip(*TAX_RATE_CLIP).fillna(TAX_RATE_FALLBACK)
                df["nopat"] = df["operating_income_sq"] * (1 - eff_tax)
                logger.info(f"  nopat: mean={df['nopat'].mean():.0f}, eff_tax median={eff_tax.median():.3f}")

                # [H2+H3+H4] ROIC — 改善 invested_capital 計算
                # invested_capital = equity + long_term_debt + short_term_debt + bonds_payable
                ibd = df["long_term_borrowings"].fillna(0) if "long_term_borrowings" in df.columns else pd.Series(0, index=df.index)
                sbd = df["short_term_borrowings"].fillna(0) if "short_term_borrowings" in df.columns else pd.Series(0, index=df.index)
                bonds = df["bonds_payable"].fillna(0) if "bonds_payable" in df.columns else pd.Series(0, index=df.index)
                # [H4] equity 缺失時保持 NaN（不用 fillna(0)）
                equity = df["stockholders_equity"] if "stockholders_equity" in df.columns else pd.Series(np.nan, index=df.index)

                invested_capital = equity + ibd + sbd + bonds

                # [H3] 分母閾值：invested_capital 太小時設 NaN（避免 ROIC 爆炸）
                min_ic_threshold = MIN_INVESTED_CAPITAL
                safe_ic = invested_capital.where(invested_capital.abs() > min_ic_threshold, np.nan)
                # [H3] clip 收緊到 [-2, 2]
                df["roic"] = (df["nopat"] / safe_ic).clip(*CLIP_RANGES["roic"])
                pct_valid = df["roic"].notna().mean() * 100
                logger.info(f"  roic: mean={df['roic'].mean():.4f}, valid={pct_valid:.1f}%")

    # --- 需合併現金流量表的指標 ---
    if cf_df is not None and len(cf_df) > 0:
        cf_cols = ["company_id", "fiscal_year", "fiscal_quarter",
                   "depreciation", "amortization", "depreciation_and_amortization"]
        available_cf = [c for c in cf_cols if c in cf_df.columns]

        if "company_id" in available_cf:
            cf_merge = cf_df[available_cf].copy()

            df = df.merge(
                cf_merge,
                on=[c for c in ["company_id", "fiscal_year", "fiscal_quarter"] if c in available_cf],
                how="left",
                suffixes=("", "_cf"),
            )

            # D&A: 優先用合併欄位，否則拆開相加
            if "depreciation_and_amortization" in df.columns:
                df["_da"] = df["depreciation_and_amortization"].fillna(0)
            else:
                dep = df.get("depreciation", pd.Series(0, index=df.index))
                amo = df.get("amortization", pd.Series(0, index=df.index))
                df["_da"] = dep.fillna(0) + amo.fillna(0)

            # [H5] Phase 5A Bug #5 fix: D&A 符號處理細化
            # 原邏輯：一律 .abs()，但混合符號（30%~70% 負值）可能是資料錯誤而非慣例
            # 新邏輯：
            #   - 純正值（negative < 5%）：信任資料，維持原值
            #   - 明顯負慣例（negative >= 70%）：公司慣例，取 .abs() 統一為正
            #   - 混合（5%~70% 負值）：視為資料品質問題，該 row 設 NaN（讓 EBITDA 走 fallback）
            if "operating_income_sq" in df.columns:
                da_series = df["_da"].copy()

                if "company_id" in df.columns:
                    n_trusted = 0       # 純正值，不動
                    n_flipped = 0       # 明顯負慣例，整欄 abs
                    n_mixed_nan = 0     # 混合符號，該公司的混合 row 設 NaN
                    total_companies = df["company_id"].nunique()

                    for cid, grp_idx in df.groupby("company_id").groups.items():
                        company_da = da_series.loc[grp_idx]
                        nonzero = company_da[company_da != 0]
                        if len(nonzero) == 0:
                            continue
                        neg_pct = (nonzero < 0).mean()
                        if neg_pct < 0.05:
                            # 純正值慣例：信任資料
                            n_trusted += 1
                        elif neg_pct >= 0.70:
                            # 明顯負慣例：取 abs
                            da_series.loc[grp_idx] = company_da.abs()
                            n_flipped += 1
                        else:
                            # 混合符號：僅把負值設為 NaN（保留正值），避免汙染 EBITDA
                            # [註] 比原先一律 .abs() 保守，但仍保留正值 row 可用
                            neg_mask = company_da < 0
                            da_series.loc[grp_idx[neg_mask]] = np.nan
                            n_mixed_nan += 1

                    logger.info(
                        f"  D&A sign (per-company refined): "
                        f"{n_trusted} trusted, {n_flipped} flipped (abs), "
                        f"{n_mixed_nan} mixed→neg set NaN, "
                        f"total {total_companies} companies"
                    )
                else:
                    # Fallback: 全域偵測
                    nonzero_da = da_series[da_series != 0]
                    if len(nonzero_da) > 0:
                        neg_pct = (nonzero_da < 0).mean()
                        if neg_pct >= 0.70:
                            da_series = da_series.abs()
                            logger.info(f"  D&A sign (global): {neg_pct*100:.0f}% negative → abs")
                        elif neg_pct >= 0.05:
                            # 混合：負值設 NaN
                            da_series = da_series.where(da_series >= 0, np.nan)
                            logger.info(f"  D&A sign (global): {neg_pct*100:.0f}% negative → set NaN")

                df["ebitda"] = df["operating_income_sq"] + da_series
                # [M2] EBITDA margin — clip 收緊到 [-0.5, 1.0]
                if "revenue_sq" in df.columns:
                    safe_rev = df["revenue_sq"].where(df["revenue_sq"] > 0, np.nan)
                    n_zero_rev = (df["revenue_sq"] <= 0).sum()
                    if n_zero_rev > 0:
                        logger.warning(f"  ebitda_margin: {n_zero_rev} rows with zero/negative revenue → NaN")
                    df["ebitda_margin"] = (df["ebitda"] / safe_rev).clip(*CLIP_RANGES["ebitda_margin"])
                    logger.info(f"  ebitda_margin: mean={df['ebitda_margin'].mean():.4f}")

            df = df.drop(columns=["_da"], errors="ignore")

    return df


# ============================================================
# 4. 品質檢查
# ============================================================

@timer
def quality_check_bs(df: pd.DataFrame) -> dict:
    """資產負債表品質檢查"""
    report = {
        "total_records": len(df),
        "total_companies": df["company_id"].nunique() if "company_id" in df.columns else 0,
    }

    # 核心欄位非空率
    key_cols = ["total_assets", "stockholders_equity", "total_liabilities"]
    for col in key_cols:
        if col in df.columns:
            non_null = df[col].notna().sum()
            report[f"{col}_coverage"] = f"{non_null}/{len(df)} ({non_null/len(df)*100:.1f}%)"

    # 會計恆等式檢查: 資產 ≈ 負債 + 權益
    if all(c in df.columns for c in ["total_assets", "total_liabilities", "stockholders_equity"]):
        check = df.dropna(subset=["total_assets", "total_liabilities", "stockholders_equity"])
        if len(check) > 0:
            diff = (check["total_assets"] - check["total_liabilities"] - check["stockholders_equity"]).abs()
            # [M3] 容差從 5% 收緊到 0.5%，違反率門檻從 5% 降至 1%
            tolerance = check["total_assets"].abs() * ACCOUNTING_TOLERANCE
            violations = (diff > tolerance).sum()
            report["accounting_equation_violations"] = int(violations)
            report["accounting_equation_violation_pct"] = round(violations / len(check) * 100, 2) if len(check) > 0 else 0
            report["accounting_equation_check"] = "PASS" if violations < len(check) * 0.01 else "WARN"
            if violations > 0:
                logger.warning(f"  Accounting equation: {violations}/{len(check)} violations ({violations/len(check)*100:.1f}%) at 0.5% tolerance")

    logger.info(f"BS quality check: {report}")
    return report


# ============================================================
# 主流程
# ============================================================

@timer
def run_balance_sheet_pipeline(bs_raw: pd.DataFrame,
                               cf_raw: pd.DataFrame = None,
                               income_df: pd.DataFrame = None,
                               config: dict = None) -> tuple:
    """
    資產負債表 + 現金流量表完整處理流程。

    Args:
        bs_raw: 資產負債表原始資料（FinMind 長格式）
        cf_raw: 現金流量表原始資料（FinMind 長格式，可選）
        income_df: 已處理的損益表（含 _sq 欄位，用於計算 ROE 等）
        config: 設定字典

    Returns:
        (處理後的 DataFrame, 品質報告 dict)
    """
    logger.info("=" * 60)
    logger.info("Balance Sheet + Cashflow Pipeline (Phase 4)")
    logger.info("=" * 60)

    # 1. Pivot 資產負債表
    logger.info("\n[Step 1/5] Pivot balance sheet (long → wide)...")
    bs_wide = pivot_financial_statement(bs_raw, BS_TYPE_MAP, "BalanceSheet")

    if len(bs_wide) == 0:
        logger.error("Balance sheet pivot produced empty result!")
        return pd.DataFrame(), {"error": "empty pivot"}

    # 2. Pivot 現金流量表
    cf_wide = pd.DataFrame()
    if cf_raw is not None and len(cf_raw) > 0:
        logger.info("\n[Step 2/5] Pivot cashflow statement...")
        cf_wide = pivot_financial_statement(cf_raw, CF_TYPE_MAP, "Cashflow")
    else:
        logger.info("\n[Step 2/5] No cashflow data provided, skipping.")

    # 3. Fiscal period + PIT
    logger.info("\n[Step 3/5] Assign fiscal period + PIT dates...")
    bs_wide = assign_fiscal_period_and_pit(bs_wide)
    if len(cf_wide) > 0:
        cf_wide = assign_fiscal_period_and_pit(cf_wide)

    # 4. 計算衍生指標
    logger.info("\n[Step 4/5] Compute derived ratios (ROE, ROIC, EBITDA, D/E)...")
    bs_final = compute_bs_ratios(
        bs_wide,
        income_df=income_df,
        cf_df=cf_wide if len(cf_wide) > 0 else None,
    )

    # 5. 品質檢查
    logger.info("\n[Step 5/5] Quality check...")
    report = quality_check_bs(bs_final)

    logger.info(f"\nBS pipeline complete: {bs_final.shape[0]:,} rows × {bs_final.shape[1]} cols")
    return bs_final, report
