"""
OHLCV 股價資料抓取腳本
======================
用 FinMind 免費 API 抓取台股 open/high/low/close/volume 資料。

使用方式（在 VSCode 中直接按 F5 或右鍵 → Run）：
    1. 先安裝套件：pip install FinMind pandas pyarrow
    2. 把下方 TOKEN 換成你自己的（或留空用免費慢速）
    3. 執行這支檔案

功能：
    - 自動從 companies.parquet 讀取股票清單
    - 每小時 580 次請求（有 token）/ 280 次（無 token）
    - 每 50 支一批存檔，中斷後重跑會自動續傳
    - 全部完成後合併成一個 stock_prices_ohlcv.parquet
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

# ============================================================
#  ★★★ 請修改這裡 ★★★
# ============================================================

# 你的 FinMind Token（到 https://finmindtrade.com/ 免費註冊取得）
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0wNCAxNDoxNzo1OCIsInVzZXJfaWQiOiJhbmR5Y2hlbjA0MTAiLCJpcCI6IjEwMS4xMC44My4yMzkiLCJleHAiOjE3NzU4ODgyNzh9.xnhljQups8cM9D_i2qD8U97rub-X3TV5eNms4iQPUZU"

# 資料日期範圍
START_DATE = "2023-03-01"
END_DATE = "2025-03-31"

# Parquet 檔案路徑（相對於這支腳本的位置）
COMPANIES_PARQUET = "選用資料集/parquet/companies.parquet"
OUTPUT_PARQUET = "選用資料集/parquet/stock_prices_ohlcv.parquet"

# 執行參數
BATCH_SIZE = 50          # 每批幾支股票（寫入一次暫存檔）
MAX_RETRIES = 3          # 每支股票最多重試幾次
DELAY_BETWEEN = 0.3      # 每支股票之間等待秒數
RATE_LIMIT = 580 if TOKEN else 280  # 每小時最多請求數

# 暫存目錄（斷點續傳用）
TEMP_DIR = "outputs/ohlcv_temp"
PROGRESS_FILE = "ohlcv_fetch_progress.json"

# FinMind → 標準欄位對照
COLUMN_MAP = {
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

# ============================================================
#  以下不需要修改
# ============================================================

# 取得腳本所在目錄，作為所有相對路徑的基準
SCRIPT_DIR = Path(__file__).parent.resolve()


def log(msg, level="INFO"):
    """簡易日誌"""
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "WAIT": "⏳"}
    print(f"[{ts}] {prefix.get(level, '  ')} {msg}")


class RateLimiter:
    """滑動視窗流量控制器"""

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
    """抓取單支股票，含重試"""
    for attempt in range(MAX_RETRIES):
        try:
            rate_limiter.wait()
            df = dl.taiwan_stock_daily(
                stock_id=stock_id,
                start_date=START_DATE,
                end_date=END_DATE,
            )
            if df is None or len(df) == 0:
                return None

            rename = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
            df = df.rename(columns=rename)
            return df

        except Exception as e:
            wait = (attempt + 1) * 5
            log(f"  {stock_id} 第 {attempt+1} 次失敗: {e}，{wait}s 後重試", "WARN")
            time.sleep(wait)

    log(f"  {stock_id} 全部 {MAX_RETRIES} 次重試失敗", "ERR")
    return None


def load_progress(progress_path: Path) -> dict:
    if progress_path.exists():
        with open(progress_path, "r") as f:
            return json.load(f)
    return {"completed": [], "failed": []}


def save_progress(progress: dict, progress_path: Path):
    with open(progress_path, "w") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def merge_batches(temp_dir: Path, output_path: Path):
    """合併所有暫存 batch → 最終 Parquet"""
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

    # 型別整理
    for col in ["open_price", "high_price", "low_price", "closing_price"]:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce")
    if "volume" in merged.columns:
        merged["volume"] = pd.to_numeric(merged["volume"], errors="coerce").astype("Int64")
    if "trade_date" in merged.columns:
        merged["trade_date"] = pd.to_datetime(merged["trade_date"])

    merged.to_parquet(output_path, index=False)

    log("=" * 60)
    log(f"完成！已儲存至: {output_path}", "OK")
    log(f"  筆數: {merged.shape[0]:,} rows × {merged.shape[1]} cols")
    log(f"  公司數: {merged['company_id'].nunique()}")
    log(f"  日期範圍: {merged['trade_date'].min()} ~ {merged['trade_date'].max()}")
    log(f"  欄位: {merged.columns.tolist()}")
    log(f"  檔案大小: {output_path.stat().st_size / 1024**2:.1f} MB")
    log("=" * 60)

    # 品質快檢
    if all(c in merged.columns for c in ["open_price", "high_price", "low_price", "closing_price"]):
        bad = (merged["high_price"] < merged["low_price"]).sum()
        if bad > 0:
            log(f"  ⚠ {bad} 筆 high < low（資料異常）", "WARN")
        else:
            log(f"  OHLC 一致性檢查: 全部通過", "OK")


def main():
    log("=" * 60)
    log("OHLCV 資料抓取腳本")
    log(f"日期範圍: {START_DATE} ~ {END_DATE}")
    log(f"流量限制: {RATE_LIMIT} req/hr {'(有 Token)' if TOKEN else '(無 Token)'}")
    log("=" * 60)

    # 1. 初始化 FinMind
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

    # 2. 讀取股票清單
    companies_path = SCRIPT_DIR / COMPANIES_PARQUET
    if not companies_path.exists():
        log(f"找不到公司清單: {companies_path}", "ERR")
        return

    companies = pd.read_parquet(companies_path)
    all_stocks = sorted(companies["company_id"].unique().tolist())
    log(f"股票總數: {len(all_stocks)}")

    # 3. 斷點續傳
    temp_dir = SCRIPT_DIR / TEMP_DIR
    temp_dir.mkdir(parents=True, exist_ok=True)
    progress_path = temp_dir / PROGRESS_FILE

    progress = load_progress(progress_path)
    completed = set(progress["completed"])
    remaining = [s for s in all_stocks if s not in completed]

    log(f"已完成: {len(completed)} | 剩餘: {len(remaining)}")

    if not remaining:
        log("全部已完成，直接合併")
        merge_batches(temp_dir, SCRIPT_DIR / OUTPUT_PARQUET)
        return

    # 4. 估算時間
    est_hours = len(remaining) / RATE_LIMIT
    log(f"預估耗時: {est_hours:.1f} 小時")
    log("")

    # 5. 分批抓取
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
                batch_frames.append(df)
                progress["completed"].append(stock_id)
                log(f"    {stock_id}: {len(df)} 筆", "OK")
            else:
                progress["failed"].append(stock_id)
                log(f"    {stock_id}: 無資料", "WARN")

            time.sleep(DELAY_BETWEEN)

        # 寫入暫存
        if batch_frames:
            batch_df = pd.concat(batch_frames, ignore_index=True)
            batch_path = temp_dir / f"batch_{batch_idx:04d}.parquet"
            batch_df.to_parquet(batch_path, index=False)
            log(f"  暫存: {len(batch_df):,} 筆 → {batch_path.name}")
            del batch_frames, batch_df

        # 儲存進度
        save_progress(progress, progress_path)

        pct = len(progress["completed"]) / len(all_stocks) * 100
        log(f"  進度: {len(progress['completed'])}/{len(all_stocks)} ({pct:.1f}%) | 失敗: {len(progress['failed'])}")
        log("")

    # 6. 合併
    merge_batches(temp_dir, SCRIPT_DIR / OUTPUT_PARQUET)

    # 7. 失敗清單
    if progress["failed"]:
        log(f"\n以下 {len(progress['failed'])} 支股票抓取失敗（可能已下市或代號有誤）:", "WARN")
        for s in progress["failed"][:30]:
            print(f"    {s}")
        if len(progress["failed"]) > 30:
            print(f"    ... 還有 {len(progress['failed'])-30} 支")


if __name__ == "__main__":
    main()
