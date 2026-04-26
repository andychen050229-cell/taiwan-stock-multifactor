"""
資料載入模組 — 從 Parquet 檔案載入四張核心資料表

資料表：
  - companies: 上市公司基本資料 (1,932 筆)
  - stock_prices: 每日股價 (877,699 筆)
  - income_stmt: 損益表 (14,968 筆)
  - stock_text: 新聞/社群文本 (1,125,134 筆)

使用方式：
    loader = DataLoader(config)
    companies = loader.load_companies()
    prices = loader.load_stock_prices()
    income = loader.load_income_stmt()
    text = loader.load_stock_text(lite=True)  # 開發用精簡版
"""
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger


class DataLoader:
    """Parquet 資料載入器"""

    def __init__(self, config: dict):
        """
        Args:
            config: 設定字典（來自 load_config()）
        """
        self.config = config
        root = Path(config.get("_project_root", "."))
        self.parquet_dir = root / config["data"]["parquet_dir"]
        self.tables = config["data"]["tables"]

        if not self.parquet_dir.exists():
            logger.warning(f"Parquet directory not found: {self.parquet_dir}")

    def _load_parquet(self, table_key: str, columns: Optional[list] = None) -> pd.DataFrame:
        """
        載入單一 Parquet 檔案。

        Args:
            table_key: 資料表 key（如 "companies"）
            columns: 只讀取指定欄位（節省記憶體）

        Returns:
            DataFrame
        """
        filename = self.tables[table_key]
        filepath = self.parquet_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Parquet file not found: {filepath}")

        df = pd.read_parquet(filepath, columns=columns)
        logger.info(f"Loaded {table_key}: {df.shape[0]:,} rows × {df.shape[1]} cols | {filepath.name}")

        return df

    def load_companies(self, columns: Optional[list] = None) -> pd.DataFrame:
        """載入上市公司基本資料"""
        df = self._load_parquet("companies", columns)
        logger.info(f"  Unique companies: {df.shape[0]}")
        return df

    def load_stock_prices(self, columns: Optional[list] = None) -> pd.DataFrame:
        """
        載入每日股價資料。
        自動將日期欄位轉換為 datetime 型別。
        """
        df = self._load_parquet("stock_prices", columns)

        # 自動偵測並轉換日期欄位
        date_cols = [c for c in df.columns if "date" in c.lower() or "日期" in c]
        for col in date_cols:
            if df[col].dtype == "object" or str(df[col].dtype).startswith("str"):
                df[col] = pd.to_datetime(df[col], errors="coerce")
                logger.debug(f"  Converted {col} to datetime")

        # 基本統計
        if date_cols:
            date_col = date_cols[0]
            logger.info(f"  Date range: {df[date_col].min()} ~ {df[date_col].max()}")

        ticker_cols = [c for c in df.columns if "ticker" in c.lower() or "stock_id" in c.lower()
                       or "代號" in c or "symbol" in c.lower() or "company_id" in c.lower()]
        if ticker_cols:
            n_tickers = df[ticker_cols[0]].nunique()
            logger.info(f"  Unique tickers: {n_tickers}")

        return df

    def load_income_stmt(self, columns: Optional[list] = None) -> pd.DataFrame:
        """
        載入損益表資料。
        注意 PIT (Point-in-Time) 對齊需在後續處理。
        """
        df = self._load_parquet("income_stmt", columns)

        # 偵測期間欄位
        period_cols = [c for c in df.columns if "period" in c.lower() or "quarter" in c.lower()
                       or "年" in c or "季" in c or "date" in c.lower()]
        if period_cols:
            logger.info(f"  Period columns: {period_cols}")

        return df

    def load_balance_sheet(self, columns: Optional[list] = None) -> pd.DataFrame:
        """載入資產負債表資料（Phase 4 新增）。若檔案不存在則回傳空 DataFrame。"""
        try:
            df = self._load_parquet("balance_sheet", columns)
            logger.info(f"  Balance sheet: {df['stock_id'].nunique() if 'stock_id' in df.columns else '?'} companies")
            return df
        except (FileNotFoundError, KeyError):
            logger.warning("Balance sheet parquet not found. Skipping.")
            return pd.DataFrame()

    def load_cashflow(self, columns: Optional[list] = None) -> pd.DataFrame:
        """載入現金流量表資料（Phase 4 新增）。若檔案不存在則回傳空 DataFrame。"""
        try:
            df = self._load_parquet("cashflow", columns)
            logger.info(f"  Cashflow: {df['stock_id'].nunique() if 'stock_id' in df.columns else '?'} companies")
            return df
        except (FileNotFoundError, KeyError):
            logger.warning("Cashflow parquet not found. Skipping.")
            return pd.DataFrame()

    def load_industry(self, columns: Optional[list] = None) -> pd.DataFrame:
        """載入產業分類資料（Phase 5A 新增）。若檔案不存在則回傳空 DataFrame。

        來源：FinMind TaiwanStockInfo
        欄位：company_id, stock_name, industry_category, industry_code,
              listing_type (twse/tpex), info_date
        """
        try:
            df = self._load_parquet("industry", columns)
            if not df.empty:
                logger.info(
                    f"  Industry: {df['company_id'].nunique()} companies, "
                    f"{df['industry_category'].nunique()} categories"
                )
            return df
        except (FileNotFoundError, KeyError):
            logger.warning("Industry parquet not found. Skipping.")
            return pd.DataFrame()

    def load_institutional_investors(self, columns: Optional[list] = None) -> pd.DataFrame:
        """載入三大法人買賣超資料（Phase 5A 新增）。若檔案不存在則回傳空 DataFrame。

        來源：FinMind TaiwanStockInstitutionalInvestorsBuySell（已 pivot）
        欄位：company_id, trade_date,
              foreign_buy/sell/net, trust_buy/sell/net, dealer_buy/sell/net,
              all_inst_net
        """
        try:
            df = self._load_parquet("institutional_investors", columns)
            if not df.empty and "trade_date" in df.columns:
                logger.info(
                    f"  Institutional: {df['company_id'].nunique()} companies, "
                    f"{df['trade_date'].min()} ~ {df['trade_date'].max()}"
                )
            return df
        except (FileNotFoundError, KeyError):
            logger.warning("Institutional investors parquet not found. Skipping.")
            return pd.DataFrame()

    def load_margin_trading(self, columns: Optional[list] = None) -> pd.DataFrame:
        """載入融資融券資料（Phase 5A 新增）。若檔案不存在則回傳空 DataFrame。

        來源：FinMind TaiwanStockMarginPurchaseShortSale
        欄位：company_id, trade_date,
              margin_buy/sell/balance/change, short_buy/sell/balance/change,
              margin_short_ratio, margin_use_rate
        """
        try:
            df = self._load_parquet("margin_trading", columns)
            if not df.empty and "trade_date" in df.columns:
                logger.info(
                    f"  Margin: {df['company_id'].nunique()} companies, "
                    f"{df['trade_date'].min()} ~ {df['trade_date'].max()}"
                )
            return df
        except (FileNotFoundError, KeyError):
            logger.warning("Margin trading parquet not found. Skipping.")
            return pd.DataFrame()

    def load_stock_text(self, lite: bool = None, columns: Optional[list] = None) -> pd.DataFrame:
        """
        載入新聞/社群文本資料。

        Args:
            lite: 是否使用精簡版。None 時依設定檔決定。
            columns: 只讀取指定欄位
        """
        # 判斷是否使用 lite 版本
        if lite is None:
            lite = self.config.get("preprocessing", {}).get("text", {}).get("use_lite", False)

        table_key = "stock_text_lite" if lite else "stock_text"
        df = self._load_parquet(table_key, columns)

        # 文本基本統計
        text_cols = [c for c in df.columns if "text" in c.lower() or "content" in c.lower()
                     or "title" in c.lower() or "內容" in c]
        if text_cols:
            sample_col = text_cols[0]
            avg_len = df[sample_col].dropna().str.len().mean()
            logger.info(f"  Text column '{sample_col}' avg length: {avg_len:.0f} chars")

        return df

    def load_all(self, text_lite: bool = None) -> dict:
        """
        一次載入全部資料表。

        Returns:
            dict with keys: companies, stock_prices, income_stmt, stock_text
        """
        logger.info("=" * 60)
        logger.info("Loading all tables from Parquet...")
        logger.info("=" * 60)

        data = {
            "companies": self.load_companies(),
            "stock_prices": self.load_stock_prices(),
            "income_stmt": self.load_income_stmt(),
            "stock_text": self.load_stock_text(lite=text_lite),
            "balance_sheet": self.load_balance_sheet(),
            "cashflow": self.load_cashflow(),
            # Phase 5A
            "industry": self.load_industry(),
            "institutional_investors": self.load_institutional_investors(),
            "margin_trading": self.load_margin_trading(),
        }

        total_rows = sum(df.shape[0] for df in data.values())
        total_mem = sum(df.memory_usage(deep=True).sum() for df in data.values()) / 1024**2
        logger.info(f"All tables loaded: {total_rows:,} total rows | {total_mem:.1f} MB memory")

        return data


def quick_profile(df: pd.DataFrame, name: str = "DataFrame") -> dict:
    """
    快速資料品質概覽。

    Args:
        df: 要分析的 DataFrame
        name: 顯示名稱

    Returns:
        品質統計字典
    """
    profile = {
        "name": name,
        "rows": len(df),
        "cols": len(df.columns),
        "memory_mb": df.memory_usage(deep=True).sum() / 1024**2,
        "dtypes": df.dtypes.value_counts().to_dict(),
        "null_pct": (df.isnull().sum() / len(df) * 100).to_dict(),
        "duplicated_rows": df.duplicated().sum(),
    }

    logger.info(f"--- Profile: {name} ---")
    logger.info(f"  Shape: {profile['rows']:,} × {profile['cols']}")
    logger.info(f"  Memory: {profile['memory_mb']:.1f} MB")
    logger.info(f"  Duplicated rows: {profile['duplicated_rows']:,}")

    # 列出缺值 > 0 的欄位
    nulls = {k: v for k, v in profile["null_pct"].items() if v > 0}
    if nulls:
        logger.info(f"  Columns with nulls:")
        for col, pct in sorted(nulls.items(), key=lambda x: -x[1])[:10]:
            logger.info(f"    {col}: {pct:.1f}%")
    else:
        logger.info(f"  No null values found")

    return profile
