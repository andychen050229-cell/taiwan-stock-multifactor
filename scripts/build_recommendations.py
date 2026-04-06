#!/usr/bin/env python3
"""
Phase 2 產出 → Dashboard 推薦資料建構腳本

從 feature_store.parquet + phase2_report JSON 生成
dashboard/data/recommendations.json，供 Streamlit Cloud 使用
（因 feature_store 169 MB 無法上傳 GitHub）。

用法：
  python scripts/build_recommendations.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths ───────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"
PARQUET_DIR = ROOT / "選用資料集" / "parquet"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

FEATURE_STORE = OUTPUT_DIR / "feature_store.parquet"
REPORTS_DIR = OUTPUT_DIR / "reports"
STOCK_PRICES = PARQUET_DIR / "stock_prices.parquet"
COMPANIES = PARQUET_DIR / "companies.parquet"

TOP_N = 10  # 每個 horizon 保留的推薦股票數

# ── Feature columns used in dashboard stock cards ────────────────
FUND_COLS = [
    "fund_revenue_sq", "fund_cost_of_revenue_sq", "fund_operating_income_sq",
    "fund_net_income_sq", "fund_total_comprehensive_income_sq", "fund_eps_sq",
    "fund_gross_margin_sq", "fund_operating_margin_sq", "fund_net_margin_sq",
    "fund_revenue_yoy", "fund_eps_yoy",
]
VAL_COLS = ["val_pe", "val_pe_rank"]
RISK_COLS = ["risk_drawdown", "risk_volatility_regime", "risk_market_ret_20d"]
EXTRA_COLS = FUND_COLS + VAL_COLS + RISK_COLS

# ── Industry inference from company full name ────────────────────
INDUSTRY_KEYWORDS = {
    "半導體": ["半導體", "晶圓", "晶片", "積體電路", "IC設計"],
    "電子零組件": ["電子", "電機", "電氣", "零組件", "連接器", "被動元件", "PCB", "電路板"],
    "光電": ["光電", "LED", "顯示", "面板", "光學"],
    "通訊網路": ["通訊", "網通", "電信", "無線"],
    "資訊服務": ["資訊", "軟體", "資料", "雲端", "科技"],
    "生技醫療": ["生技", "醫療", "製藥", "藥品", "生物", "醫藥"],
    "金融": ["金融", "銀行", "證券", "保險", "投資", "控股"],
    "鋼鐵": ["鋼鐵", "鋼", "金屬", "鑄造"],
    "塑化": ["塑膠", "化工", "化學", "石化", "塑化"],
    "紡織": ["紡織", "纖維", "成衣", "織"],
    "食品": ["食品", "食", "飲料", "農"],
    "營建": ["營建", "建設", "營造", "工程", "建築"],
    "航運": ["航運", "海運", "航空", "物流", "運輸"],
    "觀光": ["觀光", "旅遊", "飯店", "餐飲"],
    "水泥": ["水泥"],
    "汽車": ["汽車", "車輛", "車用"],
    "造紙": ["紙", "造紙"],
    "橡膠": ["橡膠", "輪胎"],
    "貿易百貨": ["貿易", "百貨", "零售", "量販"],
    "油電燃氣": ["石油", "天然氣", "電力", "能源"],
}


def infer_industry(company_name: str) -> str:
    """Infer industry from company full name using keyword matching."""
    if not company_name:
        return "其他"
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        for kw in keywords:
            if kw in company_name:
                return industry
    return "其他"


def generate_risk_summary(stock: dict, company_name: str) -> str:
    """Generate a company-specific risk summary in plain language."""
    parts = []

    # Drawdown risk
    dd = stock.get("risk_drawdown")
    if dd is not None and not np.isnan(dd):
        dd_abs = abs(dd)
        if dd_abs > 0.3:
            parts.append(f"近期最大回撤達 {dd_abs:.0%}，波動風險偏高，適合風險承受度較高的投資人")
        elif dd_abs > 0.15:
            parts.append(f"近期回撤約 {dd_abs:.0%}，波動幅度中等")
        elif dd_abs > 0:
            parts.append(f"近期回撤僅 {dd_abs:.0%}，價格走勢相對穩定")
        else:
            parts.append("近期無顯著回撤，走勢相對穩定")

    # Volatility regime
    vol = stock.get("risk_volatility_regime")
    if vol is not None and not np.isnan(vol):
        if vol >= 2:
            parts.append("目前處於高波動環境，短期價格變動可能較劇烈")
        elif vol <= 0:
            parts.append("目前處於低波動環境，價格變動相對平穩")

    # Profitability risk
    net_margin = stock.get("fund_net_margin_sq")
    op_margin = stock.get("fund_operating_margin_sq")
    if net_margin is not None and not np.isnan(net_margin):
        if net_margin < -0.1:
            parts.append(f"公司淨利率為 {net_margin:.1%}，目前處於虧損狀態，需留意獲利改善進度")
        elif net_margin < 0:
            parts.append(f"公司淨利率 {net_margin:.1%}，處於微虧，留意能否轉盈")
    if op_margin is not None and not np.isnan(op_margin) and op_margin < -0.1:
        parts.append("本業營運呈現虧損，短期內可能面臨資金壓力")

    # Revenue decline
    rev_yoy = stock.get("fund_revenue_yoy")
    if rev_yoy is not None and not np.isnan(rev_yoy):
        if rev_yoy < -0.2:
            parts.append(f"營收年減 {abs(rev_yoy):.0%}，衰退幅度較大，需關注產業前景")
        elif rev_yoy < -0.05:
            parts.append(f"營收年減 {abs(rev_yoy):.0%}，成長動能放緩")

    # Valuation risk
    pe_rank = stock.get("val_pe_rank")
    if pe_rank is not None and not np.isnan(pe_rank):
        if pe_rank > 0.85:
            parts.append("本益比處於歷史高位，估值偏貴，追高風險較大")
        elif pe_rank < 0.15:
            parts.append("本益比處於歷史低位，可能反映市場對未來獲利的擔憂")

    # Market environment
    mkt_ret = stock.get("risk_market_ret_20d")
    if mkt_ret is not None and not np.isnan(mkt_ret):
        if mkt_ret < -0.05:
            parts.append("大盤近期走弱，個股可能受系統性風險拖累")

    if not parts:
        return "目前無特別顯著的風險訊號，但仍需持續關注市場變化"

    return "；".join(parts[:4]) + "。"


def generate_observation_text(stock: dict, horizon: int, company_name: str) -> str:
    """Generate a plain-language historical observation for beginners."""
    fwd_ret = stock.get(f"fwd_ret_{horizon}", 0)
    if fwd_ret is None or np.isnan(fwd_ret):
        return ""

    ret_pct = fwd_ret * 100 if abs(fwd_ret) < 5 else fwd_ret  # safety
    direction = "上漲" if fwd_ret > 0 else "下跌"
    abs_ret = abs(ret_pct)

    # Strength description
    if abs_ret > 20:
        strength = "非常顯著的"
    elif abs_ret > 10:
        strength = "相當明顯的"
    elif abs_ret > 5:
        strength = "中等程度的"
    else:
        strength = "小幅的"

    # Build narrative
    period_desc = {"1": "隔天", "5": "一週（5 個交易日）", "20": "一個月（20 個交易日）"}
    period = period_desc.get(str(horizon), f"{horizon} 個交易日")

    parts = []
    parts.append(f"在模型判讀日之後的{period}內，該股歷史上出現了{strength}{direction}，幅度約 {abs_ret:.1f}%。")

    # Context from fundamentals
    eps = stock.get("fund_eps_sq")
    gm = stock.get("fund_gross_margin_sq")
    rev_yoy = stock.get("fund_revenue_yoy")

    context_parts = []
    if eps is not None and not np.isnan(eps):
        if eps > 0:
            context_parts.append(f"EPS {eps:.2f} 元")
        else:
            context_parts.append(f"EPS 為負（{eps:.2f} 元）")

    if gm is not None and not np.isnan(gm):
        context_parts.append(f"毛利率 {gm:.1%}")

    if rev_yoy is not None and not np.isnan(rev_yoy):
        if rev_yoy > 0:
            context_parts.append(f"營收年增 {rev_yoy:.1%}")
        else:
            context_parts.append(f"營收年減 {abs(rev_yoy):.1%}")

    if context_parts:
        parts.append(f"當時基本面數據：{'、'.join(context_parts)}。")

    if fwd_ret > 0.1:
        parts.append("此漲幅在全市場中屬於表現突出的個股，但歷史表現不代表未來走勢。")
    elif fwd_ret < -0.1:
        parts.append("此跌幅提醒我們即使模型看多，市場仍存在不確定性。")

    return " ".join(parts)


def load_feature_store() -> pd.DataFrame:
    if not FEATURE_STORE.exists():
        print(f"❌ Feature store not found: {FEATURE_STORE}")
        sys.exit(1)
    fs = pd.read_parquet(FEATURE_STORE)
    fs["trade_date"] = pd.to_datetime(fs["trade_date"], errors="coerce")
    for col in ["closing_price"] + EXTRA_COLS:
        if col in fs.columns:
            fs[col] = pd.to_numeric(fs[col], errors="coerce")
    return fs


def build_market_environment(fs: pd.DataFrame) -> dict:
    """Build market environment indicators for dashboard warning system."""
    env = {}

    for col in ["risk_volatility_regime", "risk_market_ret_20d",
                 "trend_volatility_20", "trend_volatility_60"]:
        if col in fs.columns:
            fs[col] = pd.to_numeric(fs[col], errors="coerce")

    # Per-date market aggregates (last 60 trading days)
    daily = fs.groupby("trade_date").agg({
        "risk_volatility_regime": "mean",
        "risk_market_ret_20d": "mean",
        "trend_volatility_20": "median",
    }).sort_index()

    # Historical baselines (full period)
    vol_regime_all = daily["risk_volatility_regime"]
    vol_mean = float(vol_regime_all.mean())
    vol_std = float(vol_regime_all.std())
    vol_p75 = float(vol_regime_all.quantile(0.75))
    vol_p90 = float(vol_regime_all.quantile(0.90))

    env["historical_baselines"] = {
        "vol_regime_mean": round(vol_mean, 3),
        "vol_regime_std": round(vol_std, 3),
        "vol_regime_p75": round(vol_p75, 3),
        "vol_regime_p90": round(vol_p90, 3),
        "high_vol_days_pct": round(float((vol_regime_all > 1.5).mean()), 4),
    }

    # Per-horizon snapshot
    for h in [1, 5, 20]:
        label_col = f"label_{h}"
        if label_col not in fs.columns:
            continue
        valid = fs.dropna(subset=[label_col])
        if valid.empty:
            continue
        rec_date = valid["trade_date"].max()
        snap = fs[fs["trade_date"] == rec_date]

        vol_regime = float(snap["risk_volatility_regime"].mean())
        mkt_ret_20d = float(snap["risk_market_ret_20d"].mean())
        vol_20 = float(snap["trend_volatility_20"].median())

        # Determine alert level
        if vol_regime > vol_p90:
            alert = "high"
            alert_text = (
                f"⚠️ 目前市場波動度處於歷史高位（波動指標 {vol_regime:.2f}，"
                f"超過 90% 歷史水準），模型在高波動環境下預測力可能下降，"
                f"請特別留意風險控管。"
            )
        elif vol_regime > vol_p75:
            alert = "elevated"
            alert_text = (
                f"📊 市場波動度略高於平均（波動指標 {vol_regime:.2f}，"
                f"歷史均值 {vol_mean:.2f}），建議適度關注市場變化。"
            )
        else:
            alert = "normal"
            alert_text = (
                f"✅ 市場波動度處於正常範圍（波動指標 {vol_regime:.2f}，"
                f"歷史均值 {vol_mean:.2f}），模型運作環境穩定。"
            )

        # Market trend description
        if mkt_ret_20d < -0.05:
            trend = "明顯下跌"
            trend_icon = "📉"
        elif mkt_ret_20d < -0.02:
            trend = "小幅走弱"
            trend_icon = "↘️"
        elif mkt_ret_20d > 0.05:
            trend = "明顯上漲"
            trend_icon = "📈"
        elif mkt_ret_20d > 0.02:
            trend = "小幅走強"
            trend_icon = "↗️"
        else:
            trend = "盤整震盪"
            trend_icon = "↔️"

        env[f"horizon_{h}"] = {
            "rec_date": str(rec_date.date()),
            "volatility_regime": round(vol_regime, 3),
            "market_ret_20d": round(mkt_ret_20d, 4),
            "volatility_20d": round(vol_20, 4),
            "alert_level": alert,
            "alert_text": alert_text,
            "market_trend": trend,
            "market_trend_icon": trend_icon,
            "trend_text": f"{trend_icon} 大盤近 20 日報酬 {mkt_ret_20d:+.2%}，走勢{trend}。",
        }

    # Recent 20-day volatility trend (for chart)
    recent = daily.tail(20)
    env["recent_volatility_trend"] = [
        {"date": str(d.date()), "vol_regime": round(float(v), 3)}
        for d, v in recent["risk_volatility_regime"].items()
    ]

    return env


def load_companies() -> pd.DataFrame:
    if not COMPANIES.exists():
        print(f"⚠️  companies.parquet not found")
        return pd.DataFrame(columns=["company_id", "company_name", "short_name"])
    return pd.read_parquet(COMPANIES)


def load_latest_report() -> tuple[dict, str]:
    reports = sorted(REPORTS_DIR.glob("phase2_report_*.json"), reverse=True)
    if not reports:
        print("❌ No Phase 2 report found. Run `python run_phase2.py` first.")
        sys.exit(1)
    with open(reports[0], "r", encoding="utf-8") as f:
        return json.load(f), reports[0].name


def load_stock_prices() -> pd.DataFrame:
    if not STOCK_PRICES.exists():
        print(f"⚠️  stock_prices.parquet not found at {STOCK_PRICES}")
        return pd.DataFrame()
    sp = pd.read_parquet(STOCK_PRICES)
    sp["closing_price"] = pd.to_numeric(sp["closing_price"], errors="coerce")
    sp["trade_date"] = pd.to_datetime(sp["trade_date"], errors="coerce")
    return sp


def get_latest_price(sp: pd.DataFrame, company_id: str) -> float | None:
    if sp.empty:
        return None
    sub = sp[sp["company_id"] == company_id].dropna(subset=["closing_price"])
    if sub.empty:
        return None
    return float(sub.sort_values("trade_date").iloc[-1]["closing_price"])


def build_horizon_data(
    fs: pd.DataFrame, sp: pd.DataFrame, companies: pd.DataFrame,
    horizon: int, rec_date: pd.Timestamp
) -> dict:
    """Build recommendation data for one horizon (1, 5, or 20)."""
    fwd_col = f"fwd_ret_{horizon}"
    label_col = f"label_{horizon}"

    snapshot = fs[fs["trade_date"] == rec_date].copy()
    if snapshot.empty:
        print(f"  ⚠️  No data on {rec_date} for horizon {horizon}")
        return {}

    # ── Signal distribution (full market) ──
    label_counts = snapshot[label_col].value_counts(normalize=True)
    signal_dist = {}
    for label_val in [-1, 0, 1]:
        signal_dist[str(label_val)] = round(float(label_counts.get(label_val, 0)), 4)

    # ── Market distribution (UP / FLAT / DOWN counts + return stats) ──
    valid_ret = snapshot[fwd_col].dropna()
    total = len(valid_ret)
    up_count = int((valid_ret > 0.02).sum())
    down_count = int((valid_ret < -0.02).sum())
    flat_count = total - up_count - down_count

    return_stats = {}
    if total > 0:
        return_stats = {
            "mean": round(float(valid_ret.mean()), 6),
            "median": round(float(valid_ret.median()), 6),
            "std": round(float(valid_ret.std()), 6),
            "p10": round(float(np.nanpercentile(valid_ret, 10)), 6),
            "p90": round(float(np.nanpercentile(valid_ret, 90)), 6),
        }

    market_distribution = {
        "total": total,
        "up": up_count,
        "flat": flat_count,
        "down": down_count,
        "return_stats": return_stats,
    }

    # ── Top N UP stocks by forward return ──
    up_stocks = snapshot[snapshot[label_col] == 1].nlargest(TOP_N, fwd_col)

    # Build company name lookup
    comp_map = {}
    if not companies.empty:
        comp_map = companies.set_index("company_id")[["company_name", "short_name"]].to_dict("index")

    stocks_list = []
    keep_cols = ["company_id", "trade_date", fwd_col, label_col] + [
        c for c in EXTRA_COLS if c in snapshot.columns
    ]

    for _, row in up_stocks.iterrows():
        rec = {}
        for col in keep_cols:
            val = row[col]
            if pd.isna(val):
                continue
            if col == "trade_date":
                rec["date"] = str(val)
            elif col == "company_id":
                rec["stock_id"] = str(val)
            else:
                rec[col] = round(float(val), 4) if isinstance(val, (float, np.floating)) else val

        cid = str(row["company_id"])

        # Add company info
        if cid in comp_map:
            rec["company_name"] = comp_map[cid].get("company_name", "")
            rec["short_name"] = comp_map[cid].get("short_name", "")
            rec["industry"] = infer_industry(comp_map[cid].get("company_name", ""))
        else:
            rec["company_name"] = ""
            rec["short_name"] = ""
            rec["industry"] = "其他"

        # Add closing price
        price = get_latest_price(sp, cid)
        if price is not None:
            rec["closing_price"] = round(price, 2)

        # Add risk summary (plain language)
        rec["risk_summary"] = generate_risk_summary(rec, rec.get("company_name", ""))

        # Add observation text (plain language)
        rec["observation_text"] = generate_observation_text(rec, horizon, rec.get("company_name", ""))

        stocks_list.append(rec)

    total_up = int((snapshot[label_col] == 1).sum())
    total_all = len(snapshot)

    return {
        "date": str(rec_date),
        "stocks": stocks_list,
        "total_up_stocks": total_up,
        "total_stocks": total_all,
        "signal_distribution": signal_dist,
        "market_distribution": market_distribution,
    }


def build_backtest_summary(report: dict) -> dict:
    results = report.get("results", {})
    summary = {}
    for horizon in [1, 5, 20]:
        model_key = f"model_horizon_{horizon}"
        if model_key in results:
            model_data = results[model_key]
            model_entry = {}
            for engine in ["lightgbm", "xgboost"]:
                if engine in model_data:
                    eng_data = model_data[engine]
                    model_entry[engine] = {
                        "avg_metrics": eng_data.get("avg_metrics", {}),
                        "fold_metrics": eng_data.get("fold_metrics", []),
                    }
            summary[model_key] = model_entry

        bt_key = f"backtest_horizon_{horizon}"
        if bt_key in results:
            summary[bt_key] = results[bt_key]
    return summary


def main():
    print("=" * 60)
    print("  📦 Building recommendations.json for Dashboard")
    print("=" * 60)

    print("\n📂 Loading feature store...")
    fs = load_feature_store()
    print(f"   {fs.shape[0]:,} rows × {fs.shape[1]} columns")
    print(f"   Date range: {fs['trade_date'].min()} ~ {fs['trade_date'].max()}")

    print("📂 Loading companies...")
    companies = load_companies()
    print(f"   {len(companies)} companies")

    print("📂 Loading Phase 2 report...")
    report, report_name = load_latest_report()
    print(f"   Report: {report_name}")

    print("📂 Loading stock prices...")
    sp = load_stock_prices()
    if not sp.empty:
        latest_price_date = str(sp["trade_date"].max().date())
        print(f"   Latest price date: {latest_price_date}")
    else:
        latest_price_date = "N/A"

    # Each horizon uses its own latest date with valid labels
    output = {}
    for h in [1, 5, 20]:
        label_col = f"label_{h}"
        valid = fs.dropna(subset=[label_col])
        rec_date = valid["trade_date"].max()
        print(f"\n📊 Building horizon D+{h} (rec_date={rec_date.date()})...")
        hdata = build_horizon_data(fs, sp, companies, h, rec_date)
        if hdata:
            output[f"horizon_{h}"] = hdata
            print(f"   ✅ {len(hdata['stocks'])} top stocks | "
                  f"{hdata['total_up_stocks']} UP / {hdata['total_stocks']} total")
            md = hdata["market_distribution"]
            print(f"   📈 Market: UP={md['up']} FLAT={md['flat']} DOWN={md['down']}")

    # Market environment indicators
    print("\n📊 Building market environment indicators...")
    output["market_environment"] = build_market_environment(fs)
    for h in [1, 5, 20]:
        hkey = f"horizon_{h}"
        if hkey in output["market_environment"]:
            me = output["market_environment"][hkey]
            print(f"   D+{h}: alert={me['alert_level']} | vol={me['volatility_regime']:.3f} | mkt_ret={me['market_ret_20d']:+.4f}")

    # Backtest summary
    print("\n📊 Extracting backtest summary...")
    output["backtest_summary"] = build_backtest_summary(report)

    # Feature columns
    feature_cols = [c for c in fs.columns if c not in [
        "trade_date", "company_id", "fwd_ret_1", "fwd_ret_5", "fwd_ret_20",
        "label_1", "label_5", "label_20",
    ]]
    output["feature_columns"] = feature_cols
    output["date_col"] = "trade_date"
    output["id_col"] = "company_id"

    # Market summary
    output["market_summary"] = {
        "total_stocks_tracked": int(fs["company_id"].nunique()),
        "data_period": f"{fs['trade_date'].min().strftime('%Y-%m')} ~ {fs['trade_date'].max().strftime('%Y-%m')}",
        "latest_price_date": latest_price_date,
    }

    # Write output
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    out_path = DASHBOARD_DATA / "recommendations.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    size_kb = out_path.stat().st_size / 1024
    print(f"\n✅ Written: {out_path}")
    print(f"   Size: {size_kb:.1f} KB")
    print("=" * 60)


if __name__ == "__main__":
    main()
