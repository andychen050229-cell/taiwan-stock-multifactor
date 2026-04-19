"""
產業分類資料抓取腳本 — Phase 5A M3
====================================
用 FinMind API 抓取 TaiwanStockInfo，取得每檔股票的「產業別」與「上市/上櫃」分類。
僅需一次 API call，免費 tier 也能用。

資料來源：TaiwanStockInfo（FinMind 免費）
原始欄位：industry_category, stock_id, stock_name, type, date

輸出：
    選用資料集/parquet/industry.parquet
    欄位：
        company_id        : 股票代號（統一欄名）
        stock_name        : 股票中文名稱
        industry_category : 產業別（中文，例如：半導體業、電子零組件業、金融業...）
        industry_code     : 產業 hash 代碼（ASCII 8 位元，便於特徵工程 one-hot）
        listing_type      : twse（上市）/ tpex（上櫃）
        info_date         : 資訊登記日（FinMind 原始 date）

與 companies.parquet 以 company_id 做 left-join 可取得完整資訊。
"""

import os
from pathlib import Path

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

TOKEN = os.environ.get("FINMIND_TOKEN", "")

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
COMPANIES_PARQUET = PROJECT_ROOT / "選用資料集" / "parquet" / "companies.parquet"
OUTPUT_PARQUET = PROJECT_ROOT / "選用資料集" / "parquet" / "industry.parquet"


def main():
    print("=" * 60)
    print("產業分類抓取腳本（TaiwanStockInfo）")
    print("=" * 60)

    params = {"dataset": "TaiwanStockInfo"}
    if TOKEN:
        params["token"] = TOKEN
        print("mode: paid (with token)")
    else:
        print("mode: free tier (no token)")

    print("fetching TaiwanStockInfo ...")
    r = requests.get(
        "https://api.finmindtrade.com/api/v4/data",
        params=params,
        timeout=60,
    )
    data = r.json()
    if data.get("status") != 200:
        print(f"API error: {data.get('msg')}")
        return

    raw = pd.DataFrame(data.get("data", []))
    print(f"raw rows: {len(raw):,}")
    print(f"raw columns: {list(raw.columns)}")

    # 以 stock_id 去重（每檔股票最新 date 為準）
    # FinMind 某些 row 的 date 為字串 "None"；用 errors='coerce' 轉為 NaT
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
    raw = raw.sort_values(["stock_id", "date"], na_position="first").drop_duplicates(
        subset=["stock_id"], keep="last"
    )
    print(f"after dedupe by stock_id: {len(raw):,}")

    # 對齊 companies.parquet
    companies = pd.read_parquet(COMPANIES_PARQUET)
    my_stocks = set(companies["company_id"].astype(str).unique())
    print(f"companies.parquet stocks: {len(my_stocks):,}")

    # 篩選：只保留 companies 名單中的股票
    matched = raw[raw["stock_id"].isin(my_stocks)].copy()
    print(f"matched rows: {len(matched):,}")

    # 缺失覆蓋度
    missing = my_stocks - set(matched["stock_id"])
    print(f"missing industry: {len(missing)} stocks")
    if missing and len(missing) <= 30:
        print(f"  {sorted(missing)[:30]}")

    # 欄名重組
    out = matched.rename(
        columns={
            "stock_id": "company_id",
            "industry_category": "industry_category",
            "type": "listing_type",
            "date": "info_date",
        }
    )

    # industry_code：用 hash 給每個 industry 一個穩定的小整數，方便後續 one-hot
    cat_codes = {
        name: idx
        for idx, name in enumerate(
            sorted(out["industry_category"].dropna().unique())
        )
    }
    out["industry_code"] = out["industry_category"].map(cat_codes).astype("Int32")

    # 最終欄位順序
    final_cols = [
        "company_id",
        "stock_name",
        "industry_category",
        "industry_code",
        "listing_type",
        "info_date",
    ]
    out = out[final_cols].sort_values("company_id").reset_index(drop=True)

    # 儲存
    OUTPUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUTPUT_PARQUET, index=False)

    print("=" * 60)
    print(f"OK saved: {OUTPUT_PARQUET}")
    print(f"  rows: {len(out):,}")
    print(f"  unique industries: {out['industry_category'].nunique()}")
    print(f"  listing_type distribution:")
    print(out["listing_type"].value_counts().to_string())
    print()
    print(f"  top 15 industries by count:")
    print(out["industry_category"].value_counts().head(15).to_string())
    print()
    print(f"  file size: {OUTPUT_PARQUET.stat().st_size / 1024:.1f} KB")
    print("=" * 60)


if __name__ == "__main__":
    main()
