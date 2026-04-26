"""
三大法人買賣超抓取腳本 — Phase 5A M2
====================================
用 FinMind API 抓取台股三大法人買賣超日資料。

資料來源：TaiwanStockInstitutionalInvestorsBuySell
欄位結構（long format）：
    date, stock_id, buy, name, sell
    name ∈ {Foreign_Investor, Investment_Trust, Dealer_self,
            Dealer_Hedging, Foreign_Dealer_Self}

本腳本會 pivot 成 wide format：
    company_id, trade_date,
    foreign_buy, foreign_sell, foreign_net,
    trust_buy, trust_sell, trust_net,
    dealer_buy, dealer_sell, dealer_net,
    all_inst_net    (= foreign_net + trust_net + dealer_net)

使用方式：
    1. 確認 .env 的 FINMIND_TOKEN 已設定
    2. 執行此腳本（可中斷續傳）
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

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
OUTPUT_PARQUET = "選用資料集/parquet/institutional_investors.parquet"

BATCH_SIZE = 50
MAX_RETRIES = 3
DELAY_BETWEEN = 0.3
RATE_LIMIT = 580 if TOKEN else 280

TEMP_DIR = "outputs/chip_temp/inst"
PROGRESS_FILE = "inst_fetch_progress.json"

# 法人名稱 → 統一欄位前綴
INSTITUTION_MAP = {
    "Foreign_Investor": "foreign",         # 外資（不含自營）
    "Investment_Trust": "trust",           # 投信
    "Dealer_self": "dealer_self",          # 自營商自行買賣
    "Dealer_Hedging": "dealer_hedge",      # 自營商避險
    "Foreign_Dealer_Self": "foreign_dealer",  # 外資自營
}

# 主要合併後的三大分類
MAIN_CATEGORIES = ["foreign", "trust", "dealer"]

# ============================================================
# Utilities
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
    """抓單支股票三大法人資料，含重試"""
    for attempt in range(MAX_RETRIES):
        try:
            rate_limiter.wait()
            df = dl.taiwan_stock_institutional_investors(
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


def pivot_to_wide(long_df: pd.DataFrame) -> pd.DataFrame:
    """
    Long format → Wide format，並合併成三大分類（foreign/trust/dealer）。

    Input:  date, stock_id, buy, name, sell
    Output: company_id, trade_date,
            foreign_buy, foreign_sell, foreign_net,
            trust_buy, trust_sell, trust_net,
            dealer_buy, dealer_sell, dealer_net,
            all_inst_net
    """
    df = long_df.copy()

    # 統一法人名稱前綴
    df["inst"] = df["name"].map(INSTITUTION_MAP)
    df = df[df["inst"].notna()]
    df["buy"] = pd.to_numeric(df["buy"], errors="coerce")
    df["sell"] = pd.to_numeric(df["sell"], errors="coerce")

    # Dealer 合併：dealer_self + dealer_hedge → dealer
    df["inst_main"] = df["inst"].replace({
        "dealer_self": "dealer",
        "dealer_hedge": "dealer",
        "foreign_dealer": "foreign",   # 外資自營併入外資
    })

    # Group by (date, stock_id, inst_main) 加總 buy/sell
    agg = df.groupby(["date", "stock_id", "inst_main"], as_index=False).agg(
        buy=("buy", "sum"),
        sell=("sell", "sum"),
    )

    # Pivot
    wide = agg.pivot_table(
        index=["date", "stock_id"],
        columns="inst_main",
        values=["buy", "sell"],
        aggfunc="first",
    )

    # 攤平多層欄位：(buy, foreign) → foreign_buy
    wide.columns = [f"{col[1]}_{col[0]}" for col in wide.columns]
    wide = wide.reset_index()

    # 計算 net 與總和
    for cat in MAIN_CATEGORIES:
        buy_col = f"{cat}_buy"
        sell_col = f"{cat}_sell"
        net_col = f"{cat}_net"
        if buy_col in wide.columns and sell_col in wide.columns:
            wide[net_col] = wide[buy_col].fillna(0) - wide[sell_col].fillna(0)
        else:
            wide[net_col] = 0

    wide["all_inst_net"] = (
        wide.get("foreign_net", 0)
        + wide.get("trust_net", 0)
        + wide.get("dealer_net", 0)
    )

    # 欄位改名
    wide = wide.rename(columns={"date": "trade_date", "stock_id": "company_id"})

    # 整理欄位順序
    col_order = ["company_id", "trade_date"]
    for cat in MAIN_CATEGORIES:
        for sfx in ["buy", "sell", "net"]:
            c = f"{cat}_{sfx}"
            if c in wide.columns:
                col_order.append(c)
    col_order.append("all_inst_net")
    wide = wide[[c for c in col_order if c in wide.columns]]

    return wide


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
    for cat in MAIN_CATEGORIES:
        net_col = f"{cat}_net"
        if net_col in merged.columns:
            mean_val = merged[net_col].mean()
            log(f"  {net_col}: mean={mean_val:+.0f}, non-null={merged[net_col].notna().mean()*100:.1f}%")
    log("=" * 60)


def load_progress(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"completed": [], "failed": []}


def save_progress(progress: dict, path: Path):
    path.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    log("=" * 60)
    log("三大法人買賣超資料抓取腳本")
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
                # 立即 pivot 成 wide format
                wide = pivot_to_wide(df)
                batch_frames.append(wide)
                progress["completed"].append(stock_id)
                log(f"    {stock_id}: {len(df)} 筆(long) → {len(wide)} 筆(wide)", "OK")
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
