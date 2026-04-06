"""
OHLCV 資料抓取模組 — 使用 FinMind API 補齊 open/high/low/volume

功能特色：
  1. 流量控制：自動遵守 580 req/hr (token) / 280 req/hr (no token)
  2. 記憶體管理：分批處理，每批寫入 Parquet 後釋放
  3. 斷點續傳：追蹤已完成的 stock_id，中斷後可從上次進度繼續
  4. 完整日誌：每支股票的抓取狀態與錯誤記錄
  5. 備援機制：FinMind 失敗時可切換 yfinance

使用方式（在專案根目錄執行）：
    python -m src.data.ohlcv_fetcher              # 使用預設設定
    python -m src.data.ohlcv_fetcher --token YOUR_TOKEN  # 使用 FinMind token
    python -m src.data.ohlcv_fetcher --backend yfinance  # 使用 yfinance
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import numpy as np
from loguru import logger


# ============================================================
# 常數
# ============================================================

PROGRESS_FILE = "ohlcv_fetch_progress.json"
TEMP_DIR = "outputs/ohlcv_temp"

# FinMind 欄位名 → 標準欄位名
STANDARD_COLUMNS = {
    "date": "trade_date",
    "stock_id": "company_id",
    "open": "open_price",
    "max": "high_price",
    "min": "low_price",
    "close": "closing_price",
    "Trading_Volume": "volume",
    "Trading_money": "trading_value",
    "Trading_turnover": "turnover",
    "spread": "spread",
}

YFINANCE_COLUMNS = {
    "Open": "open_price",
    "High": "high_price",
    "Low": "low_price",
    "Close": "closing_price",
    "Volume": "volume",
}


# ============================================================
# FinMind Backend
# ============================================================

class FinMindFetcher:
    """FinMind API 抓取器，含流量控制"""

    def __init__(self, token: Optional[str] = None, rate_limit: int = 580):
        self.token = token
        self.rate_limit = rate_limit
        self._request_times = []
        self._init_api()

    def _init_api(self):
        try:
            from FinMind.data import DataLoader
            self.dl = DataLoader()
            if self.token:
                self.dl.login_by_token(api_token=self.token)
                logger.info(f"FinMind: logged in with token (rate limit: {self.rate_limit}/hr)")
            else:
                logger.info(f"FinMind: anonymous mode (rate limit: {self.rate_limit}/hr)")
        except ImportError:
            raise ImportError(
                "FinMind 未安裝。請執行: pip install FinMind\n"
                "或改用 yfinance: python -m src.data.ohlcv_fetcher --backend yfinance"
            )

    def _wait_for_rate_limit(self):
        """智慧流量控制：滑動視窗追蹤每小時請求數"""
        now = time.time()
        self._request_times = [t for t in self._request_times if now - t < 3600]

        if len(self._request_times) >= self.rate_limit:
            oldest = self._request_times[0]
            wait_time = 3600 - (now - oldest) + 1
            if wait_time > 0:
                logger.warning(
                    f"Rate limit reached ({self.rate_limit}/hr). "
                    f"Waiting {wait_time:.0f}s until "
                    f"{datetime.now() + timedelta(seconds=wait_time):%H:%M:%S}..."
                )
                time.sleep(wait_time)

        self._request_times.append(time.time())

    def fetch_one(self, stock_id: str, start_date: str, end_date: str,
                  max_retries: int = 3) -> Optional[pd.DataFrame]:
        """抓取單支股票的 OHLCV 資料"""
        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                df = self.dl.taiwan_stock_daily(
                    stock_id=stock_id,
                    start_date=start_date,
                    end_date=end_date,
                )
                if df is None or len(df) == 0:
                    logger.debug(f"  {stock_id}: no data returned")
                    return None

                rename_map = {k: v for k, v in STANDARD_COLUMNS.items() if k in df.columns}
                df = df.rename(columns=rename_map)
                if "company_id" not in df.columns and "stock_id" in df.columns:
                    df = df.rename(columns={"stock_id": "company_id"})
                return df

            except Exception as e:
                delay = (attempt + 1) * 5
                logger.warning(
                    f"  {stock_id} attempt {attempt+1}/{max_retries} failed: {e}. "
                    f"Retry in {delay}s..."
                )
                time.sleep(delay)

        logger.error(f"  {stock_id}: all {max_retries} attempts failed")
        return None


# ============================================================
# yfinance Backend (備援)
# ============================================================

class YFinanceFetcher:
    """yfinance 備援抓取器"""

    def __init__(self, delay: float = 0.5):
        self.delay = delay
        try:
            import yfinance  # noqa: F401
            logger.info("yfinance: initialized")
        except ImportError:
            raise ImportError("yfinance 未安裝。請執行: pip install yfinance")

    def fetch_one(self, stock_id: str, start_date: str, end_date: str,
                  max_retries: int = 3) -> Optional[pd.DataFrame]:
        import yfinance as yf
        for suffix in [".TW", ".TWO"]:
            ticker = f"{stock_id}{suffix}"
            for attempt in range(max_retries):
                try:
                    time.sleep(self.delay)
                    df = yf.download(
                        ticker, start=start_date, end=end_date,
                        progress=False, auto_adjust=False,
                    )
                    if df is None or len(df) == 0:
                        break
                    df = df.reset_index()
                    rename_map = {k: v for k, v in YFINANCE_COLUMNS.items() if k in df.columns}
                    df = df.rename(columns=rename_map)
                    if "Date" in df.columns:
                        df = df.rename(columns={"Date": "trade_date"})
                    df["company_id"] = stock_id
                    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
                    keep = ["company_id", "trade_date", "open_price", "high_price",
                            "low_price", "closing_price", "volume"]
                    df = df[[c for c in keep if c in df.columns]]
                    return df
                except Exception as e:
                    logger.warning(f"  {ticker} attempt {attempt+1}: {e}")
                    time.sleep(2)
        return None


# ============================================================
# 主控流程
# ============================================================

class OHLCVPipeline:
    """
    OHLCV 抓取主控台。
    分批處理 + 斷點續傳 + 最終合併。
    """

    def __init__(self, config: dict, backend: str = "finmind",
                 token: Optional[str] = None):
        self.config = config
        self.backend = backend

        root = Path(config.get("_project_root", "."))
        self.parquet_dir = root / config["data"]["parquet_dir"]
        self.temp_dir = root / TEMP_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.progress_path = self.temp_dir / PROGRESS_FILE

        ohlcv_cfg = config.get("ohlcv_fetch", {})
        self.batch_size = ohlcv_cfg.get("batch_size", 50)
        self.max_retries = ohlcv_cfg.get("max_retries", 3)
        self.delay = ohlcv_cfg.get("delay_between_stocks", 0.3)

        date_range = config.get("data", {}).get("date_range", {})
        self.start_date = date_range.get("start", "2023-03-01")
        self.end_date = date_range.get("end", "2025-03-31")

        if token:
            rate_limit = ohlcv_cfg.get("rate_limit_per_hour", 580)
        else:
            rate_limit = ohlcv_cfg.get("rate_limit_no_token", 280)

        if backend == "finmind":
            self.fetcher = FinMindFetcher(token=token, rate_limit=rate_limit)
        elif backend == "yfinance":
            self.fetcher = YFinanceFetcher(delay=self.delay)
        else:
            raise ValueError(f"Unknown backend: {backend}")

    def _load_progress(self) -> dict:
        if self.progress_path.exists():
            with open(self.progress_path, "r") as f:
                return json.load(f)
        return {"completed": [], "failed": [], "last_batch": 0}

    def _save_progress(self, progress: dict):
        with open(self.progress_path, "w") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    def _get_stock_list(self) -> list:
        companies_file = self.parquet_dir / self.config["data"]["tables"]["companies"]
        companies = pd.read_parquet(companies_file)
        return sorted(companies["company_id"].unique().tolist())

    def _save_batch(self, batch_df: pd.DataFrame, batch_idx: int):
        if batch_df is None or len(batch_df) == 0:
            return
        path = self.temp_dir / f"batch_{batch_idx:04d}.parquet"
        batch_df.to_parquet(path, index=False)
        logger.info(f"  Saved batch {batch_idx}: {len(batch_df):,} rows -> {path.name}")

    def run(self) -> Path:
        """執行完整 OHLCV 抓取流程"""
        logger.info("=" * 70)
        logger.info(f"OHLCV Fetch Pipeline — backend={self.backend}")
        logger.info(f"Date range: {self.start_date} ~ {self.end_date}")
        logger.info("=" * 70)

        all_stocks = self._get_stock_list()
        logger.info(f"Total stocks: {len(all_stocks)}")

        progress = self._load_progress()
        completed = set(progress["completed"])
        remaining = [s for s in all_stocks if s not in completed]
        logger.info(f"Already completed: {len(completed)} | Remaining: {len(remaining)}")

        if not remaining:
            logger.info("All stocks already fetched. Merging...")
            return self._merge_all()

        total_batches = (len(remaining) + self.batch_size - 1) // self.batch_size
        start_batch = progress.get("last_batch", 0)

        for batch_idx in range(total_batches):
            batch_start = batch_idx * self.batch_size
            batch_end = min(batch_start + self.batch_size, len(remaining))
            batch_stocks = remaining[batch_start:batch_end]

            logger.info(f"\n--- Batch {batch_idx+1}/{total_batches} ({len(batch_stocks)} stocks) ---")

            batch_frames = []
            for i, stock_id in enumerate(batch_stocks):
                logger.info(f"  [{batch_start+i+1}/{len(remaining)}] Fetching {stock_id}...")

                df = self.fetcher.fetch_one(
                    stock_id=stock_id,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    max_retries=self.max_retries,
                )

                if df is not None and len(df) > 0:
                    batch_frames.append(df)
                    progress["completed"].append(stock_id)
                    logger.info(f"    OK {stock_id}: {len(df)} rows")
                else:
                    progress["failed"].append(stock_id)
                    logger.warning(f"    FAIL {stock_id}: no data")

                time.sleep(self.delay)

            if batch_frames:
                batch_df = pd.concat(batch_frames, ignore_index=True)
                self._save_batch(batch_df, start_batch + batch_idx)
                del batch_frames, batch_df

            progress["last_batch"] = start_batch + batch_idx + 1
            self._save_progress(progress)

            logger.info(
                f"  Progress: {len(progress['completed'])}/{len(all_stocks)} "
                f"({len(progress['completed'])/len(all_stocks)*100:.1f}%) | "
                f"Failed: {len(progress['failed'])}"
            )

        return self._merge_all()

    def _merge_all(self) -> Path:
        """合併所有暫存 Parquet"""
        logger.info("\nMerging all batches...")

        batch_files = sorted(self.temp_dir.glob("batch_*.parquet"))
        if not batch_files:
            logger.error("No batch files found!")
            return None

        frames = [pd.read_parquet(f) for f in batch_files]
        merged = pd.concat(frames, ignore_index=True)
        del frames

        before = len(merged)
        merged = merged.drop_duplicates(subset=["company_id", "trade_date"], keep="last")
        if before > len(merged):
            logger.info(f"  Removed {before - len(merged):,} duplicates")

        merged = merged.sort_values(["company_id", "trade_date"]).reset_index(drop=True)

        for col in ["open_price", "high_price", "low_price", "closing_price"]:
            if col in merged.columns:
                merged[col] = pd.to_numeric(merged[col], errors="coerce")
        if "volume" in merged.columns:
            merged["volume"] = pd.to_numeric(merged["volume"], errors="coerce").astype("Int64")
        if "trade_date" in merged.columns:
            merged["trade_date"] = pd.to_datetime(merged["trade_date"])

        ohlcv_filename = self.config.get("data", {}).get("ohlcv", "stock_prices_ohlcv.parquet")
        output_path = self.parquet_dir / ohlcv_filename
        merged.to_parquet(output_path, index=False)

        logger.info("=" * 70)
        logger.info(f"OHLCV fetch complete!")
        logger.info(f"  Output: {output_path}")
        logger.info(f"  Shape: {merged.shape[0]:,} rows x {merged.shape[1]} cols")
        logger.info(f"  Companies: {merged['company_id'].nunique()}")
        logger.info(f"  Date range: {merged['trade_date'].min()} ~ {merged['trade_date'].max()}")
        logger.info(f"  Columns: {merged.columns.tolist()}")
        logger.info(f"  Memory: {merged.memory_usage(deep=True).sum()/1024**2:.1f} MB")
        logger.info("=" * 70)

        self._quality_report(merged)
        return output_path

    def _quality_report(self, df: pd.DataFrame):
        """OHLCV 品質快檢"""
        logger.info("\n--- OHLCV Quality Check ---")
        for col in df.columns:
            null_pct = df[col].isnull().mean() * 100
            if null_pct > 0:
                logger.info(f"  {col}: {null_pct:.2f}% null")

        if all(c in df.columns for c in ["open_price", "high_price", "low_price", "closing_price"]):
            bad_hl = (df["high_price"] < df["low_price"]).sum()
            bad_hc = (df["high_price"] < df["closing_price"]).sum()
            bad_ho = (df["high_price"] < df["open_price"]).sum()
            logger.info(f"  OHLC consistency: high<low={bad_hl} | high<close={bad_hc} | high<open={bad_ho}")

        for col in ["open_price", "high_price", "low_price", "closing_price", "volume"]:
            if col in df.columns:
                neg = (df[col] < 0).sum()
                if neg > 0:
                    logger.warning(f"  {col}: {neg} negative values!")

        progress = self._load_progress()
        logger.info(f"  Completed: {len(progress.get('completed', []))}")
        logger.info(f"  Failed: {len(progress.get('failed', []))}")
        if progress.get("failed"):
            logger.info(f"  Failed stocks: {progress['failed'][:20]}...")


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="OHLCV 資料抓取器")
    parser.add_argument("--token", type=str, default=None,
                        help="FinMind API token（可選，有 token 速度更快）")
    parser.add_argument("--backend", type=str, default="finmind",
                        choices=["finmind", "yfinance"],
                        help="資料來源 (default: finmind)")
    parser.add_argument("--batch-size", type=int, default=None,
                        help="每批次股票數（覆蓋 config）")
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from dotenv import load_dotenv
    load_dotenv()

    from src.utils.config_loader import load_config
    config = load_config()

    if args.batch_size:
        config.setdefault("ohlcv_fetch", {})["batch_size"] = args.batch_size

    # Token 優先順序：CLI 參數 > 環境變數
    token = args.token or os.environ.get("FINMIND_TOKEN")
    if token and token == "your_token_here":
        token = None  # 未填寫的模板值

    pipeline = OHLCVPipeline(config=config, backend=args.backend, token=token)
    output = pipeline.run()

    if output:
        print(f"\n完成！OHLCV 資料已儲存至: {output}")
    else:
        print("\n抓取失敗，請檢查日誌")


if __name__ == "__main__":
    main()
