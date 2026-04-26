"""
融資融券資料抓取腳本 — Phase 5A M2
==================================
用 FinMind API 抓取台股融資融券日資料。

資料來源：TaiwanStockMarginPurchaseShortSale
原始欄位（已是 wide format）：
    date, stock_id,
    MarginPurchaseBuy/Sell/TodayBalance/YesterdayBalance/CashRepayment/Limit,
    ShortSaleBuy/Sell/TodayBalance/YesterdayBalance/CashRepayment/Limit,
    OffsetLoanAndShort, Note

本腳本會精簡並衍生：
    company_id, trade_date,
    margin_buy, margin_sell, margin_balance, margin_change,
    short_buy, short_sell, short_balance, short_change,
    margin_short_ratio      (= margin_balance / short_balance)
    margin_use_rate         (= margin_balance / margin_limit)

使用方式：
    1. 確認 .env 的 FINMIND_TOKEN 已設定
    2. 執行此腳本（可中斷續傳）
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

# ============================================================
# 設定
# ============================================================
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
TOKEN = os.environ.get("FINMIND_TOKEN", "")

START_DATE = "2023-03-01"
END_DATE = "2025-03-31"

COMPANIES_PARQUET = "選用資料集/parquet/companies.parquet"
OUTPUT_PARQUET = "選用資料集/parquet/margin_trading.parquet"

BATCH_SIZE = 50
MAX_RETRIES = 3
DELAY_BETWEEN = 0.3
RATE_LIMIT = 580 if TOKEN else 280

TEMP_DIR = "outputs/chip_temp/margin"
PROGRESS_FILE = "margin_fetch_progress.json"

# 欄位映射：FinMind → 統一欄位名
COLUMN_MAP = {
    "date": "trade_date",
    "stock_id": "company_id",
    "MarginPurchaseBuy": "margin_buy",
    "MarginPurchaseSell": "margin_sell",
    "MarginPurchaseTodayBalance": "margin_balance",
    "MarginPurchaseYesterdayBalance": "margin_balance_prev",
    "MarginPurchaseCashRepayment": "margin_repay",
    "MarginPurchaseLimit": "margin_limit",
    "ShortSaleBuy": "short_buy",
    "ShortSaleSell": "short_sell",
    "ShortSaleTodayBalance": "short_balance",
    "ShortSaleYesterdayBalance": "short_balance_prev",
    "ShortSaleCashRepayment": "short_repay",
    "ShortSaleLimit": "short_limit",
    "OffsetLoanAndShort": "offset_loan_short",
}

# ============================================================
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "WAIT": "⏳"}
    print(f"[{ts}] {prefix.get(level, '  ')} {msg}")


class RateLimiter:
    def __init__(self, max_per_hour: int):
        self.max_per_hour = max_per_hour
        self._times = []

    def wait(self):
        now = time.time()
        self._times = [t for t in self._times if now - t < 3600]
        if len(self._times) >= self.max_per_hour:
            oldest = self._times[0]
            wait_sec = 3600 - (now - oldest) + 2
            resume = datetime.now() + timedelta(seconds=wait_sec)
            log(f"達到流量上限 ({self.max_per_hour}/hr)，等待 {wait_sec:.0f} 秒（到 {resume:%H:%M:%S}）", "WAIT")
            time.sleep(wait_sec)
        self._times.append(time.time())


def fetch_stock(dl, stock_id: str, rate_limiter: RateLimiter) -> pd.DataFrame | None:
    for attempt in range(MAX_RETRIES):
        try:
            rate_limiter.wait()
            df = dl.taiwan_stock_margin_purchase_short_sale(
                stock_id=stock_id,
                start_date=START_DATE,
                end_date=END_DATE,
            )
            if df is None or len(df) == 0:
                return None
            return df
        except Exception as e:
            wait = (attempt + 1) * 5
            log(f"  {stock_id} 第 {attempt+1} 次失敗: {e}，{wait}s 後重試", "WARN")
            time.sleep(wait)

    log(f"  {stock_id} 全部 {MAX_RETRIES} 次重試失敗", "ERR")
    return None


def clean_and_derive(df: pd.DataFrame) -> pd.DataFrame:
    """清理原始資料並衍生比率指標"""
    df = df.copy()

    # 改名
    rename = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    # 確保數值型
    numeric_cols = [c for c in df.columns if c not in ["trade_date", "company_id", "Note"]]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # 衍生：日變化量
    if "margin_balance" in df.columns and "margin_balance_prev" in df.columns:
        df["margin_change"] = df["margin_balance"] - df["margin_balance_prev"]
    if "short_balance" in df.columns and "short_balance_prev" in df.columns:
        df["short_change"] = df["short_balance"] - df["short_balance_prev"]

    # 衍生：融資融券比（多空比代理）
    if "margin_balance" in df.columns and "short_balance" in df.columns:
        safe_short = df["short_balance"].replace(0, np.nan)
        df["margin_short_ratio"] = (df["margin_balance"] / safe_short).clip(0, 1000)

    # 衍生：融資使用率
    if "margin_balance" in df.columns and "margin_limit" in df.columns:
        safe_limit = df["margin_limit"].replace(0, np.nan)
        df["margin_use_rate"] = (df["margin_balance"] / safe_limit).clip(0, 2)

    # 丟掉 Note 欄位（通常為空或除權息標記，非數值）
    if "Note" in df.columns:
        df = df.drop(columns=["Note"])

    # 整理欄位順序
    priority = [
        "company_id", "trade_date",
        "margin_buy", "margin_sell", "margin_balance", "margin_balance_prev",
        "margin_repay", "margin_limit", "margin_change", "margin_use_rate",
        "short_buy", "short_sell", "short_balance", "short_balance_prev",
        "short_repay", "short_limit", "short_change",
        "margin_short_ratio", "offset_loan_short",
    ]
    df = df[[c for c in priority if c in df.columns]]

    return df


def merge_batches(temp_dir: Path, output_path: Path):
    log("合併所有批次檔案...")
    batch_files = sorted(temp_dir.glob("batch_*.parquet"))
    if not batch_files:
        log("找不到任何批次檔案！", "ERR")
        return

    frames = [pd.read_parquet(f) for f in batch_files]
    merged = pd.concat(frames, ignore_index=True)
    del frames

    before = len(merged)
    merged = merged.drop_duplicates(subset=["company_id", "trade_date"], keep="last")
    dup = before - len(merged)
    if dup > 0:
        log(f"  移除 {dup:,} 筆重複")

    merged = merged.sort_values(["company_id", "trade_date"]).reset_index(drop=True)
    merged["trade_date"] = pd.to_datetime(merged["trade_date"])

    merged.to_parquet(output_path, index=False)

    log("=" * 60)
    log(f"完成！已儲存至: {output_path}", "OK")
    log(f"  筆數: {merged.shape[0]:,} rows × {merged.shape[1]} cols")
    log(f"  公司數: {merged['company_id'].nunique()}")
    log(f"  日期範圍: {merged['trade_date'].min()} ~ {merged['trade_date'].max()}")
    log(f"  欄位: {merged.columns.tolist()}")
    log(f"  檔案大小: {output_path.stat().st_size / 1024**2:.1f} MB")

    # 品質檢查
    for col in ["margin_balance", "short_balance", "margin_short_ratio", "margin_use_rate"]:
        if col in merged.columns:
            log(f"  {col}: mean={merged[col].mean():+.2f}, non-null={merged[col].notna().mean()*100:.1f}%")
    log("=" * 60)


def load_progress(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"completed": [], "failed": []}


def save_progress(progress: dict, path: Path):
    path.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    log("=" * 60)
    log("融資融券資料抓取腳本")
    log(f"日期範圍: {START_DATE} ~ {END_DATE}")
    log(f"流量限制: {RATE_LIMIT} req/hr {'(有 Token)' if TOKEN else '(無 Token)'}")
    log("=" * 60)

    try:
        from FinMind.data import DataLoader
    except ImportError:
        log("FinMind 未安裝！請執行: pip install FinMind", "ERR")
        return

    dl = DataLoader()
    if TOKEN:
        dl.login_by_token(api_token=TOKEN)
        log("FinMind Token 登入成功", "OK")
    else:
        log("未設定 Token，使用免費慢速模式 (280 req/hr)")

    rate_limiter = RateLimiter(RATE_LIMIT)

    companies_path = PROJECT_ROOT / COMPANIES_PARQUET
    if not companies_path.exists():
        log(f"找不到公司清單: {companies_path}", "ERR")
        return

    companies = pd.read_parquet(companies_path)
    all_stocks = sorted(companies["company_id"].unique().tolist())
    log(f"股票總數: {len(all_stocks)}")

    temp_dir = PROJECT_ROOT / TEMP_DIR
    temp_dir.mkdir(parents=True, exist_ok=True)
    progress_path = temp_dir / PROGRESS_FILE

    progress = load_progress(progress_path)
    completed = set(progress["completed"])
    remaining = [s for s in all_stocks if s not in completed]

    log(f"已完成: {len(completed)} | 剩餘: {len(remaining)}")

    if not remaining:
        log("全部已完成，直接合併")
        merge_batches(temp_dir, PROJECT_ROOT / OUTPUT_PARQUET)
        return

    est_hours = len(remaining) / RATE_LIMIT
    log(f"預估耗時: {est_hours:.1f} 小時")
    log("")

    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(total_batches):
        batch_start = batch_idx * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(remaining))
        batch_stocks = remaining[batch_start:batch_end]

        log(f"--- 第 {batch_idx+1}/{total_batches} 批 ({len(batch_stocks)} 支) ---")

        batch_frames = []
        for i, stock_id in enumerate(batch_stocks):
            log(f"  [{batch_start+i+1}/{len(remaining)}] {stock_id}...")
            df = fetch_stock(dl, stock_id, rate_limiter)

            if df is not None and len(df) > 0:
                cleaned = clean_and_derive(df)
                batch_frames.append(cleaned)
                progress["completed"].append(stock_id)
                log(f"    {stock_id}: {len(df)} 筆", "OK")
            else:
                progress["failed"].append(stock_id)
                log(f"    {stock_id}: 無資料", "WARN")

            time.sleep(DELAY_BETWEEN)

        if batch_frames:
            batch_df = pd.concat(batch_frames, ignore_index=True)
            batch_path = temp_dir / f"batch_{batch_idx:04d}.parquet"
            batch_df.to_parquet(batch_path, index=False)
            log(f"  暫存: {len(batch_df):,} 筆 → {batch_path.name}")
            del batch_frames, batch_df

        save_progress(progress, progress_path)

        pct = len(progress["completed"]) / len(all_stocks) * 100
        log(f"  進度: {len(progress['completed'])}/{len(all_stocks)} ({pct:.1f}%) | 失敗: {len(progress['failed'])}")
        log("")

    merge_batches(temp_dir, PROJECT_ROOT / OUTPUT_PARQUET)

    if progress["failed"]:
        log(f"\n以下 {len(progress['failed'])} 支股票抓取失敗:", "WARN")
        for s in progress["failed"][:30]:
            print(f"    {s}")
        if len(progress["failed"]) > 30:
            print(f"    ... 還有 {len(progress['failed'])-30} 支")


if __name__ == "__main__":
    main()
