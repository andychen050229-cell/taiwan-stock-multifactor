"""
損益表資料處理模組 — 累計轉單季 + PIT 日期估算

處理流程：
  1. dtype 型別轉換（所有欄位從 object 轉為正確型別）
  2. 累計值 → 單季值（Q2_single = Q2_cum - Q1_cum）
  3. PIT (Point-in-Time) 日期估算（台灣 IFRS 法定期限）
  4. 基本面衍生指標（毛利率、營業利益率、淨利率）
  5. 品質檢查

報告中對應章節：§3.2, §5.2
"""
import pandas as pd
import numpy as np
from loguru import logger
from ..utils.helpers import timer


# ============================================================
# 台灣 IFRS 法定申報期限（保守估計）
# ============================================================

PIT_DEADLINES = {
    1: {"month": 5, "day": 15},
    2: {"month": 8, "day": 14},
    3: {"month": 11, "day": 14},
    4: {"month": 3, "day": 31, "next_year": True},
}


# ============================================================
# 1. 型別轉換
# ============================================================

@timer
def convert_income_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """系統化型別轉換：object → 正確型別"""
    df = df.copy()

    int_cols = ["fiscal_year", "fiscal_quarter"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    money_cols = [
        "revenue", "cost_of_revenue", "operating_income",
        "net_income", "total_comprehensive_income",
    ]
    for col in money_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "eps" in df.columns:
        df["eps"] = pd.to_numeric(df["eps"], errors="coerce")

    date_cols = ["period_start", "period_end"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "id" in df.columns:
        df["id"] = df["id"].astype(str)
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].astype(str)

    converted = {col: str(df[col].dtype) for col in df.columns}
    logger.info(f"Income dtype conversion complete: {len(df)} rows")
    logger.debug(f"  Dtypes: {converted}")

    return df


# ============================================================
# 2. 累計值 → 單季值
# ============================================================

@timer
def derive_single_quarter(df: pd.DataFrame) -> pd.DataFrame:
    """
    將累計財報轉換為單季數字。

    邏輯：
      - Q1: 直接使用（Q1 累計 = Q1 單季）
      - Q2: Q2_cum - Q1_cum
      - Q3: Q3_cum - Q2_cum
      - Q4: Q4_cum - Q3_cum

    新增欄位：所有財務欄位加上 _sq 後綴（single quarter）。
    """
    df = df.copy()

    cumulative_cols = [
        "revenue", "cost_of_revenue", "operating_income",
        "net_income", "total_comprehensive_income", "eps",
    ]
    existing_cols = [c for c in cumulative_cols if c in df.columns]

    if not existing_cols:
        logger.warning("No cumulative financial columns found.")
        return df

    df = df.sort_values(["company_id", "fiscal_year", "fiscal_quarter"]).reset_index(drop=True)

    # 初始化 _sq 欄位
    for col in existing_cols:
        df[f"{col}_sq"] = np.nan

    # 逐公司逐年處理
    for (company_id, year), group in df.groupby(["company_id", "fiscal_year"]):
        quarters_present = set(group["fiscal_quarter"].dropna().astype(int).tolist())
        idx = group.index

        for q in sorted(quarters_present):
            q_mask = group["fiscal_quarter"] == q
            q_idx = idx[q_mask]

            if len(q_idx) == 0:
                continue

            if q == 1:
                for col in existing_cols:
                    df.loc[q_idx, f"{col}_sq"] = df.loc[q_idx, col]
            else:
                prev_q = q - 1
                prev_mask = group["fiscal_quarter"] == prev_q
                prev_idx = idx[prev_mask]

                if len(prev_idx) == 0:
                    logger.debug(f"  {company_id} {year} Q{q}: missing Q{prev_q}")
                    continue

                for col in existing_cols:
                    cum_val = df.loc[q_idx, col].values[0]
                    prev_cum = df.loc[prev_idx, col].values[0]

                    if pd.notna(cum_val) and pd.notna(prev_cum):
                        df.loc[q_idx, f"{col}_sq"] = cum_val - prev_cum

    # 統計
    for col in existing_cols:
        sq_col = f"{col}_sq"
        non_null = df[sq_col].notna().sum()
        logger.info(f"  {sq_col}: {non_null}/{len(df)} ({non_null/len(df)*100:.1f}%) non-null")

    # 合理性驗證：Q1 的 _sq 應等於原始值
    q1 = df[df["fiscal_quarter"] == 1]
    for col in existing_cols:
        both_valid = q1[col].notna() & q1[f"{col}_sq"].notna()
        if both_valid.any():
            mismatch = (q1.loc[both_valid, col] != q1.loc[both_valid, f"{col}_sq"]).sum()
            if mismatch > 0:
                logger.warning(f"  Q1 mismatch in {col}: {mismatch} rows")

    logger.info(f"Single quarter derivation: {len(existing_cols)} cols x {len(df)} rows")
    return df


# ============================================================
# 3. PIT 日期估算
# ============================================================

@timer
def estimate_pit_dates(df: pd.DataFrame, config: dict = None) -> pd.DataFrame:
    """
    估算 Point-in-Time 可用日期（台灣 IFRS 法定最晚期限）。

    新增欄位：
      - pit_date: 該筆財報最早可安全使用的日期
      - filing_deadline: 法定申報期限（同 pit_date）
    """
    df = df.copy()

    deadlines = PIT_DEADLINES.copy()
    if config:
        custom = config.get("preprocessing", {}).get("financial", {}).get("pit_deadlines", {})
        for q_str, date_str in custom.items():
            q = int(str(q_str).replace("Q", ""))
            if isinstance(date_str, str) and date_str.startswith("+1-"):
                parts = date_str[3:].split("-")
                deadlines[q] = {"month": int(parts[0]), "day": int(parts[1]), "next_year": True}
            elif isinstance(date_str, str):
                parts = date_str.split("-")
                deadlines[q] = {"month": int(parts[0]), "day": int(parts[1])}

    pit_dates = []

    for _, row in df.iterrows():
        year = row.get("fiscal_year")
        quarter = row.get("fiscal_quarter")

        if pd.isna(year) or pd.isna(quarter):
            pit_dates.append(pd.NaT)
            continue

        year = int(year)
        quarter = int(quarter)

        if quarter not in deadlines:
            pit_dates.append(pd.NaT)
            continue

        dl = deadlines[quarter]
        pit_year = year + 1 if dl.get("next_year", False) else year

        try:
            pit_date = pd.Timestamp(year=pit_year, month=dl["month"], day=dl["day"])
            pit_dates.append(pit_date)
        except ValueError:
            pit_dates.append(pd.NaT)

    df["pit_date"] = pit_dates
    df["filing_deadline"] = df["pit_date"]

    # 驗證：pit_date 應晚於 period_end
    if "period_end" in df.columns:
        bad = df[df["pit_date"].notna() & df["period_end"].notna() & (df["pit_date"] <= df["period_end"])]
        if len(bad) > 0:
            logger.error(f"  {len(bad)} rows where pit_date <= period_end!")

    non_null = df["pit_date"].notna().sum()
    logger.info(f"PIT date estimation: {non_null}/{len(df)} rows assigned")
    logger.info(f"  PIT range: {df['pit_date'].min()} ~ {df['pit_date'].max()}")

    return df


# ============================================================
# 4. 基本面衍生指標
# ============================================================

@timer
def compute_fundamental_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """
    計算基本面衍生比率（使用單季數字）。

    新增欄位：
      - gross_margin_sq: 毛利率
      - operating_margin_sq: 營業利益率
      - net_margin_sq: 淨利率
      - revenue_yoy: 營收年增率
      - eps_yoy: EPS 年增率
    """
    df = df.copy()

    # 毛利率（clip 至 [-1, 2] 避免離群值污染特徵）
    if "revenue_sq" in df.columns and "cost_of_revenue_sq" in df.columns:
        safe_rev = df["revenue_sq"].replace(0, np.nan)
        df["gross_margin_sq"] = (
            (df["revenue_sq"] - df["cost_of_revenue_sq"]) / safe_rev
        ).clip(-1.0, 2.0)
        logger.info(f"  gross_margin_sq: mean={df['gross_margin_sq'].mean():.4f}")

    # 營業利益率（clip 至 [-2, 2] 容許虧損但壓制極端值）
    if "operating_income_sq" in df.columns and "revenue_sq" in df.columns:
        safe_rev = df["revenue_sq"].replace(0, np.nan)
        df["operating_margin_sq"] = (
            df["operating_income_sq"] / safe_rev
        ).clip(-2.0, 2.0)
        logger.info(f"  operating_margin_sq: mean={df['operating_margin_sq'].mean():.4f}")

    # 淨利率（clip 至 [-2, 2]）
    if "net_income_sq" in df.columns and "revenue_sq" in df.columns:
        safe_rev = df["revenue_sq"].replace(0, np.nan)
        df["net_margin_sq"] = (
            df["net_income_sq"] / safe_rev
        ).clip(-2.0, 2.0)
        logger.info(f"  net_margin_sq: mean={df['net_margin_sq'].mean():.4f}")

    # 年增率（YoY）
    df = df.sort_values(["company_id", "fiscal_quarter", "fiscal_year"]).reset_index(drop=True)

    for col, yoy_col in [("revenue_sq", "revenue_yoy"), ("eps_sq", "eps_yoy")]:
        if col not in df.columns:
            continue
        df[yoy_col] = np.nan
        for (cid, q), group in df.groupby(["company_id", "fiscal_quarter"]):
            if len(group) < 2:
                continue
            sorted_g = group.sort_values("fiscal_year")
            prev = sorted_g[col].shift(1)
            yoy = ((sorted_g[col] - prev) / prev.abs()).replace([np.inf, -np.inf], np.nan)
            df.loc[sorted_g.index, yoy_col] = yoy.values

        non_null = df[yoy_col].notna().sum()
        logger.info(f"  {yoy_col}: {non_null} non-null values")

    return df


# ============================================================
# 5. 品質檢查
# ============================================================

@timer
def quality_check_financials(df: pd.DataFrame) -> dict:
    """財務資料品質綜合檢查"""
    report = {
        "total_records": len(df),
        "total_companies": df["company_id"].nunique() if "company_id" in df.columns else None,
    }

    if "fiscal_year" in df.columns and "fiscal_quarter" in df.columns:
        coverage = df.groupby(["fiscal_year", "fiscal_quarter"]).size()
        report["quarter_coverage"] = {str(k): int(v) for k, v in coverage.to_dict().items()}
        logger.info(f"  Quarter coverage:\n{coverage.to_string()}")

    sq_cols = [c for c in df.columns if c.endswith("_sq")]
    null_report = {}
    for col in sq_cols:
        null_pct = df[col].isnull().mean() * 100
        null_report[col] = f"{null_pct:.1f}%"
    report["null_pct_sq"] = null_report

    if "gross_margin_sq" in df.columns:
        extreme = ((df["gross_margin_sq"] > 1.0) | (df["gross_margin_sq"] < -1.0)).sum()
        report["extreme_gross_margin"] = int(extreme)
        if extreme > 0:
            logger.warning(f"  {extreme} rows with |gross_margin| > 100%")

    if "revenue_sq" in df.columns:
        zero_rev = (df["revenue_sq"] == 0).sum()
        report["zero_revenue_sq"] = int(zero_rev)

    if "pit_date" in df.columns:
        pit_valid = df["pit_date"].notna().sum()
        pit_coverage_pct = pit_valid / len(df) * 100
        report["pit_coverage"] = f"{pit_valid}/{len(df)} ({pit_coverage_pct:.1f}%)"
    else:
        pit_coverage_pct = 0.0

    # Compute overall_pass
    extreme_gm = report.get("extreme_gross_margin", 0)
    zero_rev = report.get("zero_revenue_sq", 0)
    # pit_coverage_pct already computed above (line 329 or 332)
    report["overall_pass"] = (
        extreme_gm < 100 and zero_rev < 50 and pit_coverage_pct == 100.0
    )

    logger.info(f"Financial quality check: {len(report)} metrics")
    return report


# ============================================================
# 主流程
# ============================================================

@timer
def run_financial_pipeline(df: pd.DataFrame, config: dict) -> tuple:
    """
    損益表完整處理流程。

    Returns: (處理後的 DataFrame, 品質報告 dict)
    """
    logger.info("=" * 60)
    logger.info("Financial Data Pipeline")
    logger.info("=" * 60)

    logger.info("\n[Step 1/5] dtype conversion...")
    df = convert_income_dtypes(df)

    logger.info("\n[Step 2/5] Cumulative -> Single Quarter...")
    df = derive_single_quarter(df)

    logger.info("\n[Step 3/5] PIT date estimation...")
    df = estimate_pit_dates(df, config)

    logger.info("\n[Step 4/5] Fundamental ratios...")
    df = compute_fundamental_ratios(df)

    logger.info("\n[Step 5/5] Quality check...")
    report = quality_check_financials(df)

    logger.info(f"\nFinancial pipeline complete: {df.shape[0]:,} rows x {df.shape[1]} cols")
    return df, report
