"""
資產負債表資料抓取腳本 (Phase 4)
================================
用 FinMind REST API 逐檔抓取台股資產負債表（TaiwanStockBalanceSheet）。

設計原則：
  1. 逐檔抓取（data_id=stock_id），不使用全市場批次查詢（需高權限）
  2. Token 使用 Authorization: Bearer header（不放 query param）
  3. Rate limiter + 斷點續傳（與 OHLCV 抓取腳本同架構）
  4. 公司清單取自 income_stmt ∩ stock_prices（1,896 家有完整資料的公司）
     — 只抓同時有股價和損益表的公司，因為 BS 衍生指標（ROE 等）需要損益表配合

使用方式：
    1. 確認 .env 中已設定 FINMIND_TOKEN
    2. python 程式碼/資料抓取/抓取資產負債表.py
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    # 嘗試多個可能的 .env 位置
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent.parent  # 資料抓取/ → 程式碼/ → 專案根目錄
    for env_path in [project_root / ".env", script_dir / ".env", Path.cwd() / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break
    else:
        load_dotenv()  # fallback: 讓 python-dotenv 自己找
except ImportError:
    pass

TOKEN = os.environ.get("FINMIND_TOKEN", "")

# ============================================================
#  設定
# ============================================================

START_DATE = "2023-01-01"
END_DATE = "2025-03-31"

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # 資料抓取/ → 程式碼/ → 專案根目錄
PARQUET_DIR = PROJECT_ROOT / "選用資料集" / "parquet"
INCOME_STMT_PARQUET = PARQUET_DIR / "income_stmt.parquet"
STOCK_PRICES_PARQUET = PARQUET_DIR / "stock_prices_ohlcv.parquet"
COMPANIES_PARQUET = PARQUET_DIR / "companies.parquet"  # fallback
OUTPUT_FILE = PARQUET_DIR / "balance_sheet.parquet"

TEMP_DIR = PROJECT_ROOT / "outputs" / "bs_temp"
PROGRESS_FILE = "bs_fetch_progress.json"

API_URL = "https://api.finmindtrade.com/api/v4/data"
DATASET = "TaiwanStockBalanceSheet"

# 執行參數
BATCH_SIZE = 50          # 每批幾支股票（寫入一次暫存檔）
MAX_RETRIES = 3          # 每支股票最多重試幾次
DELAY_BETWEEN = 0.3      # 每支股票之間等待秒數
RATE_LIMIT = 580 if TOKEN else 280  # 每小時最多請求數


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "WAIT": "⏳"}
    print(f"[{ts}] {prefix.get(level, '  ')} {msg}")


class RateLimiter:
    """滑動視窗流量控制器（與 OHLCV 腳本一致）"""

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


def fetch_stock(stock_id: str, rate_limiter: RateLimiter) -> pd.DataFrame | None:
    """逐檔抓取單支股票的資產負債表"""
    headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    params = {
        "dataset": DATASET,
        "data_id": stock_id,
        "start_date": START_DATE,
        "end_date": END_DATE,
    }

    for attempt in range(MAX_RETRIES):
        try:
            rate_limiter.wait()
            resp = requests.get(API_URL, headers=headers, params=params, timeout=60)
            resp.raise_for_status()

            data = resp.json()
            if data.get("status") != 200:
                msg = data.get("msg", "unknown")
                if "token" in str(msg).lower() or "limited" in str(msg).lower():
                    log(f"  {stock_id}: API 權限/流量問題: {msg}", "WARN")
                    time.sleep(5)
                    continue
                log(f"  {stock_id}: API 回傳異常: {msg}", "WARN")
                return None

            records = data.get("data", [])
            if not records:
                return None

            df = pd.DataFrame(records)
            return df

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                wait = (attempt + 1) * 30
                log(f"  {stock_id}: 429 Too Many Requests，等待 {wait}s", "WAIT")
                time.sleep(wait)
                continue
            wait = (attempt + 1) * 5
            log(f"  {stock_id}: HTTP 錯誤 {e}，{wait}s 後重試 ({attempt+1}/{MAX_RETRIES})", "WARN")
            time.sleep(wait)

        except Exception as e:
            wait = (attempt + 1) * 5
            log(f"  {stock_id}: 請求失敗 {e}，{wait}s 後重試 ({attempt+1}/{MAX_RETRIES})", "WARN")
            time.sleep(wait)

    log(f"  {stock_id}: 全部 {MAX_RETRIES} 次重試失敗", "ERR")
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
    merged = merged.drop_duplicates(subset=["date", "stock_id", "type"], keep="last")
    dup = before - len(merged)
    if dup > 0:
        log(f"  移除 {dup:,} 筆重複")

    merged = merged.sort_values(["stock_id", "date", "type"]).reset_index(drop=True)

    # 確保 value 是數值
    if "value" in merged.columns:
        merged["value"] = pd.to_numeric(merged["value"], errors="coerce")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(output_path, index=False)

    log("=" * 60)
    log(f"完成！已儲存至: {output_path}", "OK")
    log(f"  筆數: {merged.shape[0]:,} rows × {merged.shape[1]} cols")
    log(f"  公司數: {merged['stock_id'].nunique()}")
    log(f"  日期範圍: {merged['date'].min()} ~ {merged['date'].max()}")
    log(f"  科目數: {merged['type'].nunique()}")
    log(f"  前 15 科目: {merged['type'].value_counts().head(15).index.tolist()}")
    log(f"  檔案大小: {output_path.stat().st_size / 1024**2:.1f} MB")
    log("=" * 60)


def _load_company_list() -> list:
    """
    取得目標公司清單：income_stmt ∩ stock_prices 的交集。
    只抓同時有股價和損益表的公司，避免浪費 API quota。
    """
    inc_ids, sp_ids = set(), set()

    if INCOME_STMT_PARQUET.exists():
        inc = pd.read_parquet(INCOME_STMT_PARQUET, columns=["company_id"])
        inc_ids = set(inc["company_id"].unique())
        log(f"  income_stmt: {len(inc_ids)} 家公司")

    if STOCK_PRICES_PARQUET.exists():
        sp = pd.read_parquet(STOCK_PRICES_PARQUET, columns=["company_id"])
        sp_ids = set(sp["company_id"].unique())
        log(f"  stock_prices: {len(sp_ids)} 家公司")

    if inc_ids and sp_ids:
        target = sorted(inc_ids & sp_ids)
        log(f"  交集: {len(target)} 家公司")
        return target

    # Fallback: 用 companies.parquet
    if COMPANIES_PARQUET.exists():
        comp = pd.read_parquet(COMPANIES_PARQUET)
        target = sorted(comp["company_id"].unique().tolist())
        log(f"  Fallback (companies.parquet): {len(target)} 家公司", "WARN")
        return target

    log("找不到任何公司清單檔案！", "ERR")
    return []


def main():
    log("=" * 60)
    log("資產負債表抓取腳本 (Phase 4) — 逐檔模式")
    log(f"日期範圍: {START_DATE} ~ {END_DATE}")
    log(f"Token: {'已設定 ✓' if TOKEN else '未設定 ✗（請在 .env 設定 FINMIND_TOKEN）'}")
    log(f"認證方式: Authorization: Bearer header")
    log(f"流量限制: {RATE_LIMIT} req/hr")
    log("=" * 60)

    if not TOKEN:
        log("警告：未偵測到 FINMIND_TOKEN，可能導致 API 被拒或限速", "WARN")
        log("  請確認 .env 檔案位於專案根目錄，且內容為: FINMIND_TOKEN=你的token", "WARN")

    # 1. 讀取公司清單（取 income_stmt ∩ stock_prices 的交集）
    all_stocks = _load_company_list()
    if not all_stocks:
        log("無法取得公司清單！", "ERR")
        return
    log(f"目標公司數: {len(all_stocks)}（income_stmt ∩ stock_prices 交集）")

    # 2. 斷點續傳
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    progress_path = TEMP_DIR / PROGRESS_FILE
    progress = load_progress(progress_path)
    completed = set(progress["completed"])
    remaining = [s for s in all_stocks if s not in completed]

    log(f"已完成: {len(completed)} | 剩餘: {len(remaining)}")

    if not remaining:
        log("全部已完成，直接合併")
        merge_batches(TEMP_DIR, OUTPUT_FILE)
        return

    # 3. 估算時間
    est_hours = len(remaining) / RATE_LIMIT
    log(f"預估耗時: {est_hours:.1f} 小時")
    log("")

    rate_limiter = RateLimiter(RATE_LIMIT)

    # 4. 分批抓取
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(total_batches):
        batch_start = batch_idx * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(remaining))
        batch_stocks = remaining[batch_start:batch_end]

        log(f"--- 第 {batch_idx+1}/{total_batches} 批 ({len(batch_stocks)} 支) ---")

        batch_frames = []
        for i, stock_id in enumerate(batch_stocks):
            df = fetch_stock(stock_id, rate_limiter)

            if df is not None and len(df) > 0:
                batch_frames.append(df)
                progress["completed"].append(stock_id)
                log(f"  [{batch_start+i+1}/{len(remaining)}] {stock_id}: {len(df)} 筆", "OK")
            else:
                progress["failed"].append(stock_id)
                log(f"  [{batch_start+i+1}/{len(remaining)}] {stock_id}: 無資料", "WARN")

            time.sleep(DELAY_BETWEEN)

        # 寫入暫存
        if batch_frames:
            batch_df = pd.concat(batch_frames, ignore_index=True)
            batch_path = TEMP_DIR / f"batch_{batch_idx:04d}.parquet"
            batch_df.to_parquet(batch_path, index=False)
            log(f"  暫存: {len(batch_df):,} 筆 → {batch_path.name}")
            del batch_frames, batch_df

        # 儲存進度
        save_progress(progress, progress_path)

        pct = len(progress["completed"]) / len(all_stocks) * 100
        log(f"  進度: {len(progress['completed'])}/{len(all_stocks)} ({pct:.1f}%) | 失敗: {len(progress['failed'])}")
        log("")

    # 5. 合併
    merge_batches(TEMP_DIR, OUTPUT_FILE)

    # 6. 失敗清單
    if progress["failed"]:
        log(f"\n以下 {len(progress['failed'])} 支股票抓取失敗（可能已下市或代號有誤）:", "WARN")
        for s in progress["failed"][:30]:
            print(f"    {s}")
        if len(progress["failed"]) > 30:
            print(f"    ... 還有 {len(progress['failed'])-30} 支")


if __name__ == "__main__":
    main()
