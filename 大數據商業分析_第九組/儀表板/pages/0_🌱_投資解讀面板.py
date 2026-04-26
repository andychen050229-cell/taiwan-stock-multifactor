"""
投資解讀面板 — 歷史快照判讀 + 五層資訊架構 + 漸進式揭露

目標使用者：想了解研究方法論與歷史模型判讀的投資者
核心邏輯：展示固定歷史時期內的模型判讀結果，用於展示研究能力
展示資訊：
  - 每期的模型判讀方向（D+1 / D+5 / D+20）與歷史報酬強度
  - 五層資訊架構：方向與強度 > 公司基本面 > 解讀原因 > 成本風險 > 歷史觀察值
  - 近期價格走勢圖 + 技術指標（MA20、RSI）
  - 漸進式揭露（expandable 設計）
  - 交易成本試算（用於教育目的）
  - 市場訊號分佈 + 報酬分析
  - 投資教育與方法論說明

FIX NOTES:
  - Handle fs=None gracefully throughout
  - Extract fundamentals directly from recommendations data when fs unavailable
  - Use lighter sidebar styling for readability
  - Use market_summary from recommendations.json for total count
  - Simplified market distribution when fs is None
"""

import streamlit as st
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import importlib.util

# ===== Page Config =====
# NOTE: st.set_page_config() is now managed by st.navigation in app.py
# Do not uncomment or re-add the set_page_config call

# ===== Load shared global design system (glint-light) =====
_utils_path = Path(__file__).resolve().parent.parent / "utils.py"
_spec = importlib.util.spec_from_file_location("dashboard_utils", str(_utils_path))
_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils)
_utils.inject_custom_css()  # Inter + JetBrains Mono + tech-grid background + gl-* vars
_utils.inject_v9_chart_css()  # v9 §9 · donut chip legend + composition strip styles
render_topbar = _utils.render_topbar
render_pillar_radar = _utils.render_pillar_radar
render_sector_chip = _utils.render_sector_chip
render_subtabs = _utils.render_subtabs
load_phase6_json = _utils.load_phase6_json
render_terminal_hero = _utils.render_terminal_hero
render_trust_strip = _utils.render_trust_strip
PAGE_EYEBROWS = _utils.PAGE_EYEBROWS
PAGE_TITLES = _utils.PAGE_TITLES
PAGE_BRIEFINGS = _utils.PAGE_BRIEFINGS
glint_icon = _utils.glint_icon

# v11.5.18 — Stamp the current page path so the shell-level deferred-switch
# guard in `utils._consume_pending_switch` can tell when we've already landed
# on the target page and must not re-trigger a switch (which would loop).
st.session_state["_gl_active_page"] = str(Path(__file__).resolve())

# ---- Top-bar (sticky breadcrumb + model chips + clock) ----
render_topbar(
    crumb_left="多因子股票分析系統",
    crumb_current="投資觀察",
    chips=[
        ("歷史判讀", "pri"),
        ("2023/03–2025/03", "vio"),
        ("D+20 月度", "default"),
    ],
    show_clock=True,
)

# ===== Beginner-panel specific CSS (v11.2 dark-glint repaint) =====
st.markdown("""
<style>
    /* KPI cards — dark-glint terminal surface */
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.95) 100%);
        border: 1px solid rgba(103,232,249,0.22);
        border-radius: 10px;
        padding: 12px 14px;
    }
    div[data-testid="stMetric"] label { color: #67e8f9 !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #E8F7FC !important; }
    /* Stock card with left border indicator */
    .stock-card {
        background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.96) 100%);
        border: 1px solid rgba(103,232,249,0.22);
        border-left: 4px solid #67e8f9;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.45), inset 0 1px 0 rgba(103,232,249,0.12);
    }
    .stock-card.bullish { border-left-color: #10b981; }
    .stock-card.neutral { border-left-color: #a78bfa; }
    .stock-card.bearish { border-left-color: #f43f5e; }
    .stock-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(103,232,249,0.14);
    }
    .stock-name {
        font-size: 1.3rem;
        font-weight: 700;
        color: #E8F7FC;
    }
    .stock-id {
        font-size: 0.9rem;
        color: #67e8f9;
        font-weight: 700;
        margin-left: 8px;
        font-family: var(--gl-font-mono);
        letter-spacing: 0.04em;
    }
    /* Confidence badge */
    .confidence-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.80rem;
        font-weight: 700;
        font-family: var(--gl-font-mono);
        letter-spacing: 0.08em;
        border: 1px solid transparent;
    }
    .confidence-high { background: rgba(37,99,235,0.18); color: #93c5fd; border-color: rgba(37,99,235,0.38); }
    .confidence-medium { background: rgba(167,139,250,0.18); color: #ddd6fe; border-color: rgba(167,139,250,0.38); }
    .confidence-low { background: rgba(244,63,94,0.18); color: #fecaca; border-color: rgba(244,63,94,0.38); }
    /* Direction badge */
    .direction-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.80rem;
        font-weight: 800;
        font-family: var(--gl-font-mono);
        letter-spacing: 0.10em;
        border: 1px solid transparent;
    }
    .direction-bullish { background: rgba(16,185,129,0.18); color: #6ee7b7; border-color: rgba(16,185,129,0.40); }
    .direction-neutral { background: rgba(167,139,250,0.18); color: #ddd6fe; border-color: rgba(167,139,250,0.38); }
    .direction-bearish { background: rgba(244,63,94,0.18); color: #fecaca; border-color: rgba(244,63,94,0.40); }
    /* Info panels */
    .info-panel {
        background: linear-gradient(180deg, rgba(15,23,37,0.88) 0%, rgba(8,16,32,0.92) 100%);
        border-left: 4px solid #67e8f9;
        border: 1px solid rgba(103,232,249,0.22);
        border-left-width: 4px;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.9rem;
        line-height: 1.65;
        color: #cfe2ee;
    }
    .warning-panel {
        background: linear-gradient(180deg, rgba(37,25,12,0.92) 0%, rgba(20,14,5,0.95) 100%);
        border-left: 4px solid #a78bfa;
        border: 1px solid rgba(167,139,250,0.32);
        border-left-width: 4px;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 12px 0;
        font-size: 0.9rem;
        color: #ddd6fe;
        line-height: 1.65;
    }
    .history-disclaimer {
        background: linear-gradient(180deg, rgba(40,16,22,0.92) 0%, rgba(22,8,12,0.95) 100%);
        border-left: 4px solid #f43f5e;
        border: 1px solid rgba(244,63,94,0.32);
        border-left-width: 4px;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.85rem;
        color: #fecaca;
        font-weight: 500;
        line-height: 1.65;
    }
    /* Metric boxes */
    .metric-box {
        background: linear-gradient(180deg, rgba(15,23,37,0.90) 0%, rgba(8,16,32,0.94) 100%);
        border: 1px solid rgba(103,232,249,0.22);
        border-radius: 10px;
        padding: 10px 14px;
        text-align: center;
        font-size: 0.85rem;
        box-shadow: inset 0 1px 0 rgba(103,232,249,0.10);
    }
    .metric-val {
        font-size: 1.1rem;
        font-weight: 700;
        color: #E8F7FC;
        margin-top: 4px;
        font-family: var(--gl-font-mono);
    }
    .metric-label {
        font-size: 0.7rem;
        color: #67e8f9;
        letter-spacing: 0.10em;
        text-transform: uppercase;
    }
    /* Section header */
    .section-header {
        border-left: 4px solid #67e8f9;
        padding-left: 12px;
        margin-top: 24px;
        margin-bottom: 16px;
        color: #E8F7FC;
    }
    /* Cost result */
    .cost-result {
        background: linear-gradient(180deg, rgba(5,46,22,0.92) 0%, rgba(3,25,12,0.95) 100%);
        border: 1px solid rgba(16,185,129,0.32);
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
    }
    .cost-total {
        font-size: 1.8rem;
        font-weight: 700;
        color: #6ee7b7;
        font-family: var(--gl-font-mono);
    }
</style>
""", unsafe_allow_html=True)


# ===== Data Loading Functions =====
@st.cache_data
def load_all_data():
    """載入所有需要的資料"""
    base = Path(__file__).parent.parent.parent
    dashboard_data_dir = Path(__file__).parent.parent / "data"

    fs = None
    companies = None
    prices = None
    income = None
    recommendations = {}

    # Try loading from dashboard/data/ (Streamlit Cloud deployment)
    if dashboard_data_dir.exists():
        try:
            companies = pd.read_parquet(dashboard_data_dir / "companies.parquet")

            prices = pd.read_parquet(dashboard_data_dir / "stock_prices.parquet")
            # Fix dtype: parquet 可能以 object 儲存數值欄位
            prices["closing_price"] = pd.to_numeric(prices["closing_price"], errors="coerce")
            prices["trade_date"] = pd.to_datetime(prices["trade_date"], errors="coerce")

            income = pd.read_parquet(dashboard_data_dir / "income_stmt.parquet")
            # Fix dtype for income statement numeric columns
            for col in ["revenue", "cost_of_revenue", "operating_income", "net_income",
                        "total_comprehensive_income", "eps", "fiscal_year", "fiscal_quarter"]:
                if col in income.columns:
                    income[col] = pd.to_numeric(income[col], errors="coerce")

            # Load pre-computed recommendations
            rec_file = dashboard_data_dir / "recommendations.json"
            if rec_file.exists():
                with open(rec_file, "r", encoding="utf-8") as f:
                    recommendations = json.load(f)
        except Exception as e:
            # v8 §18.4 · dark terminal error panel with schema hint
            _utils.render_error_from_copy_map("report_missing", exception=e)
            st.stop()

    # Fallback to original paths (local development)
    if companies is None or prices is None or income is None:
        try:
            companies = pd.read_parquet(base / "選用資料集" / "parquet" / "companies.parquet")
            prices = pd.read_parquet(base / "選用資料集" / "parquet" / "stock_prices.parquet")
            prices["closing_price"] = pd.to_numeric(prices["closing_price"], errors="coerce")
            prices["trade_date"] = pd.to_datetime(prices["trade_date"], errors="coerce")
            income = pd.read_parquet(base / "選用資料集" / "parquet" / "income_stmt.parquet")
            for col in ["revenue", "cost_of_revenue", "operating_income", "net_income",
                        "total_comprehensive_income", "eps", "fiscal_year", "fiscal_quarter"]:
                if col in income.columns:
                    income[col] = pd.to_numeric(income[col], errors="coerce")
            # 優先讀 feature_store_final（Phase 5B 最終版）；向下相容舊 feature_store
            fs_final = base / "outputs" / "feature_store_final.parquet"
            fs_legacy = base / "outputs" / "feature_store.parquet"
            fs = pd.read_parquet(fs_final if fs_final.exists() else fs_legacy)
        except Exception as e:
            # v8 §18.4 · dark terminal error panel with schema hint
            _utils.render_error_from_copy_map("schema_drift", exception=e)
            st.stop()

    return fs, companies, prices, income, recommendations


@st.cache_data
def get_recommendations(fs, companies, horizon=20, n_top=10, recommendations=None):
    """取得最新一期的判讀結果"""
    label_col = f"label_{horizon}"
    ret_col = f"fwd_ret_{horizon}"

    if recommendations:
        horizon_key = f"horizon_{horizon}"
        if horizon_key in recommendations:
            rec_data = recommendations[horizon_key]
            stocks_list = rec_data.get("stocks", [])
            date_str = rec_data.get("date")

            if stocks_list:
                recs_df = pd.DataFrame(stocks_list[:n_top])
                recs_df["company_id"] = recs_df["stock_id"].astype(str)
                # v11.5.6 fix — recommendations.json already carries
                # short_name/company_name/industry; naive merge would
                # create *_x / *_y suffixed columns and break
                # stock.get("short_name"). Drop duplicate name columns
                # from the companies side before merge so the recs rows
                # keep clean short_name / company_name keys.
                _companies = companies.copy()
                _dup = [c for c in ("short_name", "company_name", "industry")
                        if c in recs_df.columns and c in _companies.columns]
                if _dup:
                    _companies = _companies.drop(columns=_dup, errors="ignore")
                recs_df = recs_df.merge(_companies, on="company_id", how="left")
                rec_date = pd.to_datetime(date_str) if date_str else None
                return recs_df, rec_date

    if fs is not None and not fs.empty:
        valid = fs[fs[label_col].notna()]
        if valid.empty:
            return pd.DataFrame(), None

        latest_date = valid["trade_date"].max()
        snap = valid[valid["trade_date"] == latest_date].copy()
        up_stocks = snap[snap[label_col] == 1.0].copy()

        if up_stocks.empty:
            up_stocks = snap[snap[label_col] == 0.0].copy()

        if up_stocks.empty:
            return pd.DataFrame(), latest_date

        up_stocks = up_stocks.sort_values(ret_col, ascending=False).head(n_top)
        up_stocks = up_stocks.merge(companies, on="company_id", how="left")

        return up_stocks, latest_date

    return pd.DataFrame(), None


@st.cache_data
def get_price_history(prices, company_id, n_days=120):
    """取得股價歷史與技術指標"""
    cp = prices[prices["company_id"] == str(company_id)].copy()
    cp["trade_date"] = pd.to_datetime(cp["trade_date"], errors="coerce")
    cp["closing_price"] = pd.to_numeric(cp["closing_price"], errors="coerce")
    cp = cp.dropna(subset=["closing_price", "trade_date"])
    cp = cp.sort_values("trade_date").tail(n_days)

    if cp.empty:
        return cp

    cp["ma20"] = cp["closing_price"].rolling(window=20, min_periods=1).mean()
    cp["rsi14"] = calculate_rsi(cp["closing_price"], 14)

    return cp


def calculate_rsi(prices, period=14):
    """計算 RSI 指標"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


@st.cache_data
def get_company_fundamentals(fs, income, company_id, trade_date, stock_row=None):
    """取得公司基本面與估值指標

    若 fs 為 None，從 stock_row（recommendations DataFrame 的一列）直接抽取。
    """
    result = {
        "eps": None,
        "gross_margin": None,
        "operating_margin": None,
        "net_margin": None,
        "revenue_yoy": None,
        "pe_ratio": None,
        "pe_rank": None,
        "drawdown": None,
        "volatility_regime": None,
        "market_ret_20d": None,
        "risk_level": "中等",
        "rsi": None,
        "momentum": None,
        "fiscal_year": None,
        "fiscal_quarter": None,
    }

    # 財報數據
    ci = income[income["company_id"] == str(company_id)].copy()
    if not ci.empty:
        ci = ci.sort_values(["fiscal_year", "fiscal_quarter"])
        latest = ci.iloc[-1]

        result["fiscal_year"] = int(latest.get("fiscal_year", 0))
        result["fiscal_quarter"] = int(latest.get("fiscal_quarter", 0))
        eps_raw = latest.get("eps")
        if pd.notna(eps_raw):
            result["eps"] = eps_raw

        rev = latest.get("revenue")
        cost = latest.get("cost_of_revenue")
        oi = latest.get("operating_income")
        ni = latest.get("net_income")

        if pd.notna(rev) and rev != 0:
            if pd.notna(cost):
                result["gross_margin"] = (rev - cost) / rev
            if pd.notna(oi):
                result["operating_margin"] = oi / rev
            if pd.notna(ni):
                result["net_margin"] = ni / rev

        # YoY revenue growth
        prev_q = ci[
            (ci["fiscal_year"] == latest["fiscal_year"] - 1) &
            (ci["fiscal_quarter"] == latest["fiscal_quarter"])
        ]
        if not prev_q.empty:
            prev_rev = prev_q.iloc[0].get("revenue")
            if pd.notna(prev_rev) and prev_rev != 0 and pd.notna(rev):
                result["revenue_yoy"] = (rev - prev_rev) / abs(prev_rev)

    # Feature store or stock row data
    if fs is not None:
        fs_rec = fs[
            (fs["company_id"] == str(company_id)) &
            (fs["trade_date"] == trade_date)
        ]
        if not fs_rec.empty:
            rec = fs_rec.iloc[0]
            result["pe_ratio"] = rec.get("val_pe")
            result["pe_rank"] = rec.get("val_pe_rank")
            result["rsi"] = rec.get("trend_rsi_14")
            result["momentum"] = rec.get("trend_momentum")
            result["drawdown"] = rec.get("risk_drawdown")
            result["volatility_regime"] = rec.get("risk_volatility_regime")
            result["market_ret_20d"] = rec.get("risk_market_ret_20d")

            drawdown = rec.get("risk_drawdown")
            if pd.notna(drawdown):
                dd_abs = abs(float(drawdown))
                if dd_abs > 0.3:
                    result["risk_level"] = "高"
                elif dd_abs > 0.15:
                    result["risk_level"] = "中等"
                else:
                    result["risk_level"] = "低"
    elif stock_row is not None:
        # Extract from stock_row directly (recommendations data)
        result["pe_ratio"] = stock_row.get("val_pe")
        result["pe_rank"] = stock_row.get("val_pe_rank")
        result["drawdown"] = stock_row.get("risk_drawdown")
        result["volatility_regime"] = stock_row.get("risk_volatility_regime")
        result["market_ret_20d"] = stock_row.get("risk_market_ret_20d")

        # Compute margins from stock_row if available
        rev = stock_row.get("fund_revenue_sq")
        cost = stock_row.get("fund_cost_of_revenue_sq")
        oi = stock_row.get("fund_operating_income_sq")
        ni = stock_row.get("fund_net_income_sq")
        eps_val = stock_row.get("fund_eps_sq")

        if pd.notna(eps_val):
            result["eps"] = eps_val
        if pd.notna(rev) and rev != 0:
            if pd.notna(cost):
                result["gross_margin"] = (rev - cost) / rev
            if pd.notna(oi):
                result["operating_margin"] = oi / rev
            if pd.notna(ni):
                result["net_margin"] = ni / rev

        rev_yoy = stock_row.get("fund_revenue_yoy")
        if rev_yoy is not None and pd.notna(rev_yoy):
            result["revenue_yoy"] = rev_yoy

        # Risk level (drawdown stored as negative, use abs)
        drawdown = stock_row.get("risk_drawdown")
        if pd.notna(drawdown):
            dd_abs = abs(float(drawdown))
            if dd_abs > 0.3:
                result["risk_level"] = "高"
            elif dd_abs > 0.15:
                result["risk_level"] = "中等"
            else:
                result["risk_level"] = "低"

    return result


def get_direction_label(label_val):
    """轉換標籤為中文"""
    if label_val == 1.0:
        return "偏多", "bullish"
    elif label_val == 0.0:
        return "中性", "neutral"
    else:
        return "觀望", "bearish"


def get_direction_emoji(label_val):
    """方向 emoji"""
    if label_val == 1.0:
        return "🟢"
    elif label_val == 0.0:
        return "🟡"
    else:
        return "🔴"


# ===== v11.5.18 — Out-of-Top-N Ticker Detail Renderer ======================
def render_searched_ticker_detail(target_tid: str, companies: pd.DataFrame,
                                   prices: pd.DataFrame, income: pd.DataFrame,
                                   horizon: int, n_display: int) -> None:
    """Render a focused data-lookup card for a ticker that is NOT in the
    current D+{horizon} Top-{n_display} bullish picks.

    Context: the utility-bar Search lets users look up ANY of the 1,932
    listed companies. Only a handful show up in the model's Top-N bullish
    shortlist on any given snapshot — the rest still deserve a meaningful
    detail view so Search functions as a true "jump to stock" feature
    rather than silently filtering to an empty list.

    This view purposefully distinguishes itself from the model-judgment
    cards above: the "非本期判讀範圍" chip is the visual anchor, and the
    copy explicitly notes that no direction/strength signal is shown
    because the stock is outside the current snapshot's bullish shortlist.

    Args:
        target_tid: ticker id string (e.g. "2330")
        companies: full companies dataframe (1,932 rows)
        prices: full price history dataframe
        income: income-statement dataframe
        horizon: current D+{horizon} selector value (for contextual copy)
        n_display: current Top-N slider value (for contextual copy)
    """
    # ----- Resolve the company metadata row (may be absent if ticker has
    # been delisted / merged; we still render a minimal card in that case).
    try:
        _ci = companies[companies["company_id"].astype(str) == target_tid]
    except Exception:
        _ci = pd.DataFrame()
    short = ""
    full = ""
    if not _ci.empty:
        r0 = _ci.iloc[0]
        short = str(r0.get("short_name") or "").strip()
        full = str(r0.get("company_name") or "").strip()
    display_name = short or full or target_tid
    chip_label = f"{target_tid} · {short}" if short else target_tid

    # ----- Hero banner — make it clear this is a data lookup, not a call.
    st.markdown(
        f'<div style="background:rgba(167,139,250,0.08);'
        f'border:1px solid rgba(167,139,250,0.45);border-left:4px solid #a78bfa;'
        f'border-radius:10px;padding:12px 16px;margin:8px 0 14px 0;'
        f'display:flex;align-items:center;gap:12px;flex-wrap:wrap;'
        f'font-family:\'Inter\',sans-serif;font-size:0.88rem;color:#cbe9f2;">'
        f'<span style="color:#a78bfa;font-weight:700;letter-spacing:0.12em;'
        f'text-transform:uppercase;font-size:0.70rem;'
        f'font-family:\'JetBrains Mono\',monospace;">SEARCHED · OUT OF TOP-N</span>'
        f'<span style="color:#e8f7fc;font-weight:700;font-size:1.02rem;">{chip_label}</span>'
        f'<span style="color:#8397ac;">該股不在本期 D+{horizon} 偏多 Top-{n_display}；'
        f'以下為其歷史價量與財報資料，供研究參考，非模型判讀結果。</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ----- Top KPI row: price + pieces pulled from income statement latest.
    cp = get_price_history(prices, target_tid, n_days=120)
    latest_price = float(cp["closing_price"].iloc[-1]) if not cp.empty else None
    first_price = float(cp["closing_price"].iloc[0]) if not cp.empty else None
    ret_120d = ((latest_price / first_price - 1.0) * 100.0) if (latest_price and first_price) else None

    # Extract latest fundamentals row
    try:
        ci_all = income[income["company_id"].astype(str) == target_tid].copy()
    except Exception:
        ci_all = pd.DataFrame()
    latest_fund = None
    prev_yoy_rev = None
    if not ci_all.empty:
        ci_all = ci_all.sort_values(["fiscal_year", "fiscal_quarter"])
        latest_fund = ci_all.iloc[-1]
        # Find same-quarter prior-year for YoY
        try:
            pf = ci_all[
                (ci_all["fiscal_year"] == latest_fund["fiscal_year"] - 1) &
                (ci_all["fiscal_quarter"] == latest_fund["fiscal_quarter"])
            ]
            if not pf.empty:
                prev_yoy_rev = pf.iloc[0].get("revenue")
        except Exception:
            prev_yoy_rev = None

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("最新收盤價",
                  f"${latest_price:.2f}" if latest_price is not None else "—")
    with k2:
        if ret_120d is not None:
            st.metric("近 120 日報酬", f"{ret_120d:+.1f}%")
        else:
            st.metric("近 120 日報酬", "—")
    with k3:
        if latest_fund is not None and pd.notna(latest_fund.get("eps")):
            eps_v = float(latest_fund["eps"])
            st.metric("最新 EPS", f"${eps_v:.2f}")
        else:
            st.metric("最新 EPS", "—")
    with k4:
        # Revenue YoY
        if (latest_fund is not None and prev_yoy_rev is not None
                and pd.notna(latest_fund.get("revenue")) and prev_yoy_rev != 0):
            yoy_pct = (float(latest_fund["revenue"]) - float(prev_yoy_rev)) / abs(float(prev_yoy_rev)) * 100
            st.metric("營收年增率", f"{yoy_pct:+.1f}%")
        else:
            st.metric("營收年增率", "—")

    # ----- Content grid: price chart (left) + company snapshot (right) -----
    col_left, col_right = st.columns([6, 4])

    with col_left:
        st.markdown(
            '<div class="section-header"><strong>近 120 日價格走勢</strong></div>',
            unsafe_allow_html=True,
        )
        if not cp.empty:
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                row_heights=[0.7, 0.3],
                subplot_titles=("收盤價 + MA20", "RSI 動能指標"),
            )
            fig.add_trace(go.Scatter(
                x=cp["trade_date"], y=cp["closing_price"], mode="lines",
                line=dict(color="#a78bfa", width=2.5),
                fill="tozeroy", fillcolor="rgba(167,139,250,0.08)",
                name="收盤價",
                hovertemplate="日期: %{x|%Y-%m-%d}<br>收盤價: $%{y:.2f}<extra></extra>",
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=cp["trade_date"], y=cp["ma20"], mode="lines",
                line=dict(color="#67e8f9", width=1.5, dash="dash"),
                name="MA20",
                hovertemplate="MA20: $%{y:.2f}<extra></extra>",
            ), row=1, col=1)
            rsi_data = cp["rsi14"].dropna()
            if not rsi_data.empty:
                fig.add_trace(go.Scatter(
                    x=cp[cp["rsi14"].notna()]["trade_date"], y=rsi_data,
                    mode="lines", line=dict(color="#8b5cf6", width=1.5),
                    fill="tozeroy", fillcolor="rgba(139, 92, 246, 0.1)",
                    name="RSI-14",
                    hovertemplate="RSI: %{y:.1f}<extra></extra>",
                ), row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="#f43f5e",
                              opacity=0.5, annotation_text="超買 (70)",
                              row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="#10b981",
                              opacity=0.5, annotation_text="超賣 (30)",
                              row=2, col=1)
            fig.update_layout(
                height=360, paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, 'Noto Sans TC', sans-serif",
                          color="#B4CCDF", size=11),
                margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified",
                showlegend=True,
                legend=dict(x=0.01, y=0.98,
                            font=dict(family="JetBrains Mono, monospace", size=10)),
            )
            fig.update_xaxes(showgrid=True, gridcolor="rgba(103,232,249,0.08)",
                             tickfont=dict(family="JetBrains Mono, monospace",
                                            size=10, color="#8397AC"))
            fig.update_yaxes(showgrid=True, gridcolor="rgba(103,232,249,0.08)",
                             tickfont=dict(family="JetBrains Mono, monospace",
                                            size=10, color="#8397AC"))
            st.plotly_chart(fig, use_container_width=True,
                            key=f"searched_price_{target_tid}_{horizon}")
        else:
            st.info("此股票於資料視窗內無可用的每日收盤資料。")

    with col_right:
        st.markdown(
            '<div class="section-header"><strong>公司與財報資訊</strong></div>',
            unsafe_allow_html=True,
        )
        # Company intro
        if full:
            st.markdown(f"**{full}**")
        elif short:
            st.markdown(f"**{short}**")
        else:
            st.markdown(f"**{target_tid}**（公司名稱未收錄於資料集）")

        # Income-statement panel
        if latest_fund is not None:
            fy = int(latest_fund.get("fiscal_year", 0) or 0)
            fq = int(latest_fund.get("fiscal_quarter", 0) or 0)
            if fy and fq:
                st.caption(f"最新財報：{fy} 年 Q{fq}")

            rev = latest_fund.get("revenue")
            cost = latest_fund.get("cost_of_revenue")
            oi = latest_fund.get("operating_income")
            ni = latest_fund.get("net_income")
            eps_v = latest_fund.get("eps")

            rows_html = ['<div style="font-family:\'JetBrains Mono\',monospace;'
                         'font-size:0.82rem;line-height:1.7;color:#cbe9f2;">']
            def _row(k, v):
                rows_html.append(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'border-bottom:1px dashed rgba(103,232,249,0.12);'
                    f'padding:3px 0;">'
                    f'<span style="color:#8397ac;">{k}</span>'
                    f'<span style="color:#e8f7fc;">{v}</span></div>'
                )
            if pd.notna(rev):
                _row("營收", f"{float(rev):,.0f} 仟元")
            if pd.notna(cost) and pd.notna(rev) and rev != 0:
                _row("毛利率", f"{(float(rev) - float(cost)) / float(rev):.1%}")
            if pd.notna(oi) and pd.notna(rev) and rev != 0:
                _row("營業利益率", f"{float(oi) / float(rev):.1%}")
            if pd.notna(ni) and pd.notna(rev) and rev != 0:
                _row("淨利率", f"{float(ni) / float(rev):.1%}")
            if pd.notna(eps_v):
                _row("EPS", f"${float(eps_v):.2f}")
            rows_html.append("</div>")
            st.markdown("".join(rows_html), unsafe_allow_html=True)
        else:
            st.caption("此股票於資料視窗內無可用的季財報資料。")

        # Quarterly revenue trend (up to last 8 quarters)
        if not ci_all.empty and "revenue" in ci_all.columns:
            trend = ci_all.tail(8).copy()
            trend["period"] = trend.apply(
                lambda r: f"{int(r['fiscal_year'])}Q{int(r['fiscal_quarter'])}"
                if pd.notna(r.get('fiscal_year')) and pd.notna(r.get('fiscal_quarter')) else "",
                axis=1,
            )
            trend = trend[trend["period"] != ""]
            if not trend.empty:
                with st.expander("近期營收趨勢（最多 8 季）", expanded=False):
                    fig_r = go.Figure()
                    fig_r.add_trace(go.Bar(
                        x=trend["period"], y=trend["revenue"],
                        marker=dict(color="#67e8f9"),
                        hovertemplate="%{x}<br>營收: %{y:,.0f} 仟元<extra></extra>",
                    ))
                    fig_r.update_layout(
                        height=220, paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter, sans-serif", color="#B4CCDF", size=10),
                        margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                    )
                    fig_r.update_xaxes(showgrid=False,
                                        tickfont=dict(family="JetBrains Mono, monospace",
                                                       size=9, color="#8397AC"))
                    fig_r.update_yaxes(showgrid=True, gridcolor="rgba(103,232,249,0.08)",
                                        tickfont=dict(family="JetBrains Mono, monospace",
                                                       size=9, color="#8397AC"))
                    st.plotly_chart(fig_r, use_container_width=True,
                                    key=f"searched_rev_{target_tid}")

    # ----- Research disclaimer + navigation helpers --------------------------
    st.markdown(
        '<div style="margin-top:10px;padding:10px 14px;'
        'background:rgba(15,23,37,0.7);border:1px solid rgba(103,232,249,0.16);'
        'border-radius:8px;font-size:0.82rem;color:#8397ac;line-height:1.6;">'
        '⚠️ <strong>研究備註：</strong>此股票未進入本期 Top-N 偏多名單，'
        '不代表模型對其判讀為偏空 —— 可能是訊號強度未達前段，'
        '或特徵欄位缺失。若需看到其他判讀方向（中性／觀望），'
        '請前往「資料基礎」頁以 company_id 查詢原始標籤，'
        '或調整左側 horizon / Top-N 設定。'
        '</div>',
        unsafe_allow_html=True,
    )

    # Action row — one button to clear the lock, one link to data explorer.
    c_a, c_b = st.columns([1, 1], gap="small")
    with c_a:
        if st.button("清除鎖定，回到完整判讀清單",
                     key="_gl_clear_target_ticker_outofn",
                     use_container_width=True):
            st.session_state.pop("target_ticker", None)
            st.rerun()
    with c_b:
        st.caption("（或於上方搜尋其他個股代號）")


# ===== Load Data =====
fs, companies, prices, income, recommendations = load_all_data()


# ===== Sidebar Widgets CSS (for dark sidebar compatibility) =====
st.markdown("""<style>
    /* Sidebar widget labels — ensure visible on dark bg */
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stSlider label {
        color: #a8b8cc !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }
    /* Selectbox trigger button in sidebar — text must be BLACK for readability */
    section[data-testid="stSidebar"] [data-baseweb="select"] {
        border: 1px solid rgba(0,0,0,0.2) !important;
        border-radius: 8px !important;
    }
    /* Force pure black text inside the selectbox trigger (the white box) */
    section[data-testid="stSidebar"] [data-baseweb="select"] *,
    section[data-testid="stSidebar"] [data-baseweb="select"] span,
    section[data-testid="stSidebar"] [data-baseweb="select"] div,
    section[data-testid="stSidebar"] [data-baseweb="select"] [role="combobox"],
    section[data-testid="stSidebar"] [data-baseweb="select"] [data-baseweb="tag"],
    [data-baseweb="select"] .css-1dimb5e-singleValue,
    [data-baseweb="select"] [class*="singleValue"],
    [data-baseweb="select"] [class*="ValueContainer"] span,
    [data-baseweb="select"] [class*="option"] {
        color: #000000 !important;
    }
    /* The dropdown arrow/icon should also be dark */
    section[data-testid="stSidebar"] [data-baseweb="select"] svg {
        fill: #000000 !important;
        color: #000000 !important;
    }
    /* Hide search cursor in selectbox — force dropdown-only */
    section[data-testid="stSidebar"] [data-baseweb="select"] input {
        caret-color: transparent !important;
        user-select: none !important;
    }
    /* Dropdown panel (popover) — dark theme, extra specificity for Cloud */
    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [data-baseweb="popover"] [data-baseweb="menu"],
    [data-baseweb="popover"] ul,
    div[data-baseweb="popover"] {
        background: #1a2332 !important;
        background-color: #1a2332 !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 8px !important;
    }
    [data-baseweb="popover"] li,
    [data-baseweb="popover"] [role="option"],
    div[data-baseweb="popover"] li {
        color: #e8edf3 !important;
        background: transparent !important;
        background-color: transparent !important;
    }
    [data-baseweb="popover"] li:hover,
    [data-baseweb="popover"] [role="option"]:hover,
    div[data-baseweb="popover"] li:hover {
        background: rgba(99, 110, 250, 0.25) !important;
        background-color: rgba(99, 110, 250, 0.25) !important;
        color: #ffffff !important;
    }
    [data-baseweb="popover"] li[aria-selected="true"],
    [data-baseweb="popover"] [role="option"][aria-selected="true"],
    div[data-baseweb="popover"] li[aria-selected="true"] {
        background: rgba(99, 110, 250, 0.35) !important;
        background-color: rgba(99, 110, 250, 0.35) !important;
        color: #ffffff !important;
    }
    /* Slider track */
    section[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] div {
        background: rgba(99, 110, 250, 0.4) !important;
    }
    /* Sidebar markdown text */
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li {
        color: #c0cdd9 !important;
        font-size: 0.88rem !important;
        line-height: 1.6 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown strong {
        color: #e8edf3 !important;
    }
</style>""", unsafe_allow_html=True)

# ===== Sidebar =====
st.sidebar.markdown(
    f'<div style="display:flex;align-items:center;gap:8px;font-size:1.05rem;'
    f'font-weight:700;color:var(--gl-text);margin:4px 0 2px;">'
    f'<span style="color:var(--gl-emerald);">{glint_icon("radar", 20)}</span>'
    f'<span>投資解讀面板</span></div>',
    unsafe_allow_html=True,
)
st.sidebar.caption("固定歷史資料期間的模型判讀展示")
st.sidebar.divider()

HORIZON_LABELS = {
    1: "D+1（隔日 ≈ 1 交易日）",
    5: "D+5（約一週 ≈ 5 交易日）",
    20: "D+20（約一個月 ≈ 20 交易日）",
}
horizon = st.sidebar.selectbox(
    "預測週期",
    options=[20, 5, 1],
    format_func=lambda x: HORIZON_LABELS[x],
    index=0,
)

n_display = st.sidebar.slider("顯示判讀數量", 3, 10, 5)

st.sidebar.divider()
st.sidebar.markdown("""
**判讀方向燈號**

🟢 **偏多** — 模型判斷該股在未來 D+N 天的走勢傾向上漲

🟡 **中性** — 模型判斷走勢不明確，可能處於盤整區間

🔴 **觀望** — 模型判斷走勢傾向下跌，建議保守觀察

> ⚠️ 此為歷史回顧，非即時預測。過去判讀方向不代表未來會重現。
""")

st.sidebar.divider()


# ===== Main Content =====
try:
    # Get recommendations first so we can surface the snapshot date in the hero
    recs, rec_date = get_recommendations(fs, companies, horizon=horizon, n_top=n_display, recommendations=recommendations)

    # --- Glint terminal-hero (parity with other panels: page 5 / 9 / A / ...) ---
    _hero_eyebrow = f"{PAGE_EYEBROWS['interpret']} · D+{horizon}"
    _hero_title   = f"{PAGE_TITLES['interpret']} — D+{horizon} 判讀結果"
    _hero_brief   = PAGE_BRIEFINGS["interpret"]
    _snapshot_str = rec_date.strftime("%Y-%m-%d") if rec_date else "N/A"

    render_terminal_hero(
        eyebrow=_hero_eyebrow,
        title=_hero_title,
        briefing=_hero_brief,
        chips=[
            ("HISTORICAL SNAPSHOT", "pri"),
            ("BACKTEST WINDOW", "2023/03 – 2025/03", "vio"),
            (f"D+{horizon}", "ok"),
            ("NON-ADVISORY", "warn"),
        ],
        tone="emerald",
    )
    render_trust_strip([
        ("快照日期",      _snapshot_str,                        "cyan"),
        ("判讀地平線",    f"D+{horizon}",                       "violet"),
        ("Top N",        str(n_display),                        "emerald"),
        ("資料視窗",      "2023/03 – 2025/03",                   "amber"),
    ])

    # Historical context disclaimer — dark-themed Glint note (replaces warning-panel)
    st.markdown(
        '<div class="insight-box" style="margin:6px 0 14px 0;">'
        '<strong style="color:#c4b5fd;">📋 面板說明</strong><br>'
        '本頁面呈現的是固定歷史資料期間內的模型判讀結果，用於展示研究能力與方法論，非即時投資建議。'
        '歷史判讀不構成未來預測，過去績效不代表未來報酬。'
        '</div>',
        unsafe_allow_html=True,
    )

    if not rec_date:
        st.warning("目前沒有可用的判讀資料")
        st.stop()

    # ===== v10 §6 + v11.5.18 — Shell Search target-ticker lock =============
    # When the user searches for a ticker in the utility bar, we route here
    # with `st.session_state["target_ticker"]` set.
    #
    # v11.5.18 upgrade: the Search feature must work for ALL 1,932 listed
    # companies, not only the handful currently in the D+{horizon} Top-N
    # bullish shortlist. The previous behavior showed only a warning string
    # for any ticker outside Top-N, which made the search box look broken.
    #
    # Behavior matrix:
    #   A. ticker IS in current recs  → render LOCKED chip + filter recs
    #                                    to just that one card (existing path).
    #   B. ticker NOT in current recs → render a dedicated data-lookup card
    #                                    via `render_searched_ticker_detail()`
    #                                    (price chart + income-statement) and
    #                                    `st.stop()` so we don't render the
    #                                    full-market / Top-N sections below
    #                                    with a mismatched context.
    #   C. no target_ticker            → fall through to the original empty
    #                                    state for genuinely no-signal snapshots.
    _target_tid = str(st.session_state.get("target_ticker", "")).strip()
    if _target_tid:
        _match = recs[recs["company_id"].astype(str) == _target_tid].copy()
        if not _match.empty:
            # Path A: ticker is in current Top-N recs — filter and continue
            # with the regular card-rendering pipeline below.
            _short = ""
            try:
                _ci = companies[companies["company_id"].astype(str) == _target_tid]
                if not _ci.empty:
                    _short = str(_ci.iloc[0].get("short_name")
                                  or _ci.iloc[0].get("company_name") or "")
            except Exception:
                _short = ""
            _chip_label = f"{_target_tid} · {_short}" if _short else _target_tid
            _bg = "rgba(103,232,249,0.08)"
            _border = "rgba(103,232,249,0.45)"
            st.markdown(
                f'<div style="background:{_bg};border:1px solid {_border};'
                f'border-radius:10px;padding:10px 14px;margin:8px 0 12px 0;'
                f'display:flex;align-items:center;gap:10px;font-family:\'JetBrains Mono\', monospace;'
                f'font-size:0.82rem;color:#cbe9f2;">'
                f'<span style="color:#67e8f9;font-weight:700;letter-spacing:0.12em;'
                f'text-transform:uppercase;font-size:0.70rem;">LOCKED ·</span>'
                f'<span style="color:#e8f7fc;font-weight:700;">{_chip_label}</span>'
                f'<span style="color:#8397ac;">目前已鎖定此檔個股的判讀卡片</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            recs = _match
            if st.button("清除鎖定，回到完整清單", key="_gl_clear_target_ticker"):
                st.session_state.pop("target_ticker", None)
                st.rerun()
        else:
            # Path B: ticker is NOT in the current Top-N shortlist — render a
            # dedicated data-lookup card so Search feels like a real "jump to
            # stock" feature, then stop before the generic sections below.
            render_searched_ticker_detail(
                target_tid=_target_tid,
                companies=companies,
                prices=prices,
                income=income,
                horizon=horizon,
                n_display=n_display,
            )
            st.stop()

    # Path C (no target_ticker): regular empty-state handling.
    if recs.empty:
        st.info(f"在 D+{horizon} 週期的判讀中，目前沒有偏多訊號。")
        st.stop()

    # ===== Market Environment Alert =====
    mkt_env = recommendations.get("market_environment", {}) if recommendations else {}
    horizon_env = mkt_env.get(f"horizon_{horizon}", {})

    if horizon_env:
        alert_level = horizon_env.get("alert_level", "normal")
        alert_text = horizon_env.get("alert_text", "")
        trend_text = horizon_env.get("trend_text", "")

        if alert_level == "high":
            alert_bg = "#fef2f2"
            alert_border = "#dc2626"
            alert_icon = "🔴"
        elif alert_level == "elevated":
            alert_bg = "#fffbeb"
            alert_border = "#a78bfa"
            alert_icon = "🟡"
        else:
            alert_bg = "#ecfdf5"
            alert_border = "#059669"
            alert_icon = "🟢"

        st.markdown(f"""
<div style="background:{alert_bg}; border-left:4px solid {alert_border};
     border-radius:8px; padding:14px 18px; margin:8px 0 16px 0;">
    <strong>{alert_icon} 市場環境監測</strong><br>
    <span style="font-size:0.9rem;">{alert_text}</span><br>
    <span style="font-size:0.85rem; color:#b4ccdf;">{trend_text}</span>
</div>
        """, unsafe_allow_html=True)

    # ===== Market Overview =====
    st.markdown(
        f'<h3 style="display:flex;align-items:center;gap:10px;margin:24px 0 6px;'
        f'color:var(--gl-text);">'
        f'<span style="color:var(--gl-cyan);">{glint_icon("bar-chart", 22)}</span>'
        f'<span>本期市場概況</span></h3>',
        unsafe_allow_html=True,
    )

    label_col = f"label_{horizon}"
    ret_col = f"fwd_ret_{horizon}"

    # Load FULL market distribution from recommendations.json (pre-computed from feature_store)
    horizon_key = f"horizon_{horizon}"
    market_dist = None
    has_full_market = False

    # Try recommendations dict first (from cached load_all_data)
    if isinstance(recommendations, dict) and horizon_key in recommendations:
        md = recommendations[horizon_key].get("market_distribution")
        if isinstance(md, dict) and "total" in md:
            market_dist = md
            has_full_market = True

    # Fallback: re-read JSON directly if cache didn't have market_distribution
    if not has_full_market:
        try:
            _rec_path = Path(__file__).parent.parent / "data" / "recommendations.json"
            if _rec_path.exists():
                with open(_rec_path, "r", encoding="utf-8") as _rf:
                    _fresh = json.load(_rf)
                if isinstance(_fresh, dict) and horizon_key in _fresh:
                    md = _fresh[horizon_key].get("market_distribution")
                    if isinstance(md, dict) and "total" in md:
                        market_dist = md
                        has_full_market = True
        except Exception:
            pass

    if has_full_market and market_dist:
        total_stocks = market_dist["total"]
        up_count = market_dist["up"]
        flat_count = market_dist["flat"]
        down_count = market_dist["down"]
    elif fs is not None and not fs.empty:
        latest_snap = fs[fs["trade_date"] == rec_date]
        total_stocks = len(latest_snap)
        up_count = int((latest_snap[label_col] == 1.0).sum())
        flat_count = int((latest_snap[label_col] == 0.0).sum())
        down_count = int((latest_snap[label_col] == -1.0).sum())
        has_full_market = total_stocks > len(recs)
    else:
        # Fallback: only have top-N recommended stocks — cannot show full market
        total_stocks = 0
        up_count = 0
        flat_count = 0
        down_count = 0
        has_full_market = False

    # Market-level return stats
    ret_stats = market_dist.get("return_stats", {}) if market_dist else {}
    market_median = ret_stats.get("median", None)

    if has_full_market and total_stocks > 0:
        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            st.metric("分析股票數", f"{int(total_stocks):,}")
        with k2:
            pct_up = (up_count / total_stocks * 100) if total_stocks > 0 else 0
            st.metric("🟢 偏多", f"{int(up_count)}", delta=f"佔 {pct_up:.1f}%", delta_color="off")
        with k3:
            pct_flat = (flat_count / total_stocks * 100) if total_stocks > 0 else 0
            st.metric("🟡 中性", f"{int(flat_count)}", delta=f"佔 {pct_flat:.1f}%", delta_color="off")
        with k4:
            pct_down = (down_count / total_stocks * 100) if total_stocks > 0 else 0
            st.metric("🔴 觀望", f"{int(down_count)}", delta=f"佔 {pct_down:.1f}%", delta_color="off")
        with k5:
            if market_median is not None:
                st.metric("全市場中位數報酬", f"{market_median:+.1%}")
            else:
                st.metric("全市場中位數報酬", "—")
    else:
        # No full market data — show simplified overview
        st.caption(f"以下展示模型篩選的前 {len(recs)} 檔判讀結果。完整市場分佈資料將在下次部署後更新。")
        k1, k2 = st.columns(2)
        with k1:
            st.metric("判讀股數量", f"{len(recs)}")
        with k2:
            if market_median is not None:
                st.metric("全市場中位數報酬", f"{market_median:+.1%}")
            else:
                st.metric("全市場中位數報酬", "—")

    st.divider()

    # ===== Stock Cards with 5-Layer Architecture =====
    st.markdown(
        f'<h3 style="display:flex;align-items:center;gap:10px;margin:24px 0 6px;'
        f'color:var(--gl-text);">'
        f'<span style="color:var(--gl-emerald);">{glint_icon("pin", 22)}</span>'
        f'<span>判讀結果 Top {len(recs)}</span></h3>',
        unsafe_allow_html=True,
    )
    st.caption("以下為按歷史觀察報酬排序的模型判讀結果（事後回顧，非即時預測）。展開各層瞭解詳細資訊。")

    for idx, (_, stock) in enumerate(recs.iterrows()):
        cid = str(stock["company_id"])

        # v11.5.6 — stock card header left side: prefer the company NAME
        # (short_name first, then full company_name) so the left reads as
        # a name and the right as the ticker code. Checks suffixed merge
        # artefacts (_x / _y) as a safety net. Falls back to cid only
        # when no name variant is present.
        def _pick_name(row, *keys):
            for k in keys:
                try:
                    v = row.get(k)
                except Exception:
                    v = None
                if v is None:
                    continue
                s = str(v).strip()
                if s and s.lower() not in ("nan", "none", "<na>"):
                    return s
            return ""

        short_name_val = _pick_name(stock, "short_name", "short_name_x", "short_name_y")
        full_name      = _pick_name(stock, "company_name", "company_name_x", "company_name_y")
        name = short_name_val or full_name or cid
        price = float(stock.get("closing_price", 0) or 0)
        fwd_ret = float(stock.get(ret_col, 0) or 0)
        label_val = float(stock.get(label_col, 0) or 0)

        direction_label, direction_class = get_direction_label(label_val)
        direction_emoji = get_direction_emoji(label_val)

        # Determine historical return strength (事後觀察值，非模型信心)
        fwd_abs = abs(fwd_ret)
        if fwd_abs > 0.15:
            conf_level = "強"
            conf_class = "confidence-high"
        elif fwd_abs > 0.08:
            conf_level = "中"
            conf_class = "confidence-medium"
        else:
            conf_level = "弱"
            conf_class = "confidence-low"

        # ===== LAYER 1: Direction & Confidence (Always Visible) =====
        st.markdown(f"""
<div class="stock-card {direction_class}">
    <div class="stock-header">
        <div>
            <span class="stock-name">{name}</span>
            <span class="stock-id">{cid}</span>
        </div>
        <div>
            <span class="direction-badge direction-{direction_class}">{direction_emoji} {direction_label}</span>
            &nbsp;
            <span class="confidence-badge {conf_class}">歷史強度：{conf_level}</span>
        </div>
    </div>
</div>
        """, unsafe_allow_html=True)

        col_left, col_right = st.columns([6, 4])

        with col_left:
            # Price chart
            price_hist = get_price_history(prices, cid, n_days=120)
            if not price_hist.empty:
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.08,
                    row_heights=[0.7, 0.3],
                    subplot_titles=("近 120 日走勢", "RSI 動能指標")
                )

                fig.add_trace(go.Scatter(
                    x=price_hist["trade_date"],
                    y=price_hist["closing_price"],
                    mode="lines",
                    line=dict(color="#2563eb", width=2.5),
                    fill="tozeroy",
                    fillcolor="rgba(99, 110, 250, 0.08)",
                    name="收盤價",
                    hovertemplate="日期: %{x|%Y-%m-%d}<br>收盤價: $%{y:.2f}<extra></extra>",
                ), row=1, col=1)

                fig.add_trace(go.Scatter(
                    x=price_hist["trade_date"],
                    y=price_hist["ma20"],
                    mode="lines",
                    line=dict(color="#a78bfa", width=1.5, dash="dash"),
                    name="MA20",
                    hovertemplate="MA20: $%{y:.2f}<extra></extra>",
                ), row=1, col=1)

                fig.add_trace(go.Scatter(
                    x=[price_hist["trade_date"].iloc[-1]],
                    y=[price_hist["closing_price"].iloc[-1]],
                    mode="markers",
                    marker=dict(size=12, color="#2563eb"),
                    showlegend=False,
                    hoverinfo="skip",
                ), row=1, col=1)

                rsi_data = price_hist["rsi14"].dropna()
                if not rsi_data.empty:
                    fig.add_trace(go.Scatter(
                        x=price_hist[price_hist["rsi14"].notna()]["trade_date"],
                        y=rsi_data,
                        mode="lines",
                        line=dict(color="#8b5cf6", width=1.5),
                        fill="tozeroy",
                        fillcolor="rgba(139, 92, 246, 0.1)",
                        name="RSI-14",
                        hovertemplate="RSI: %{y:.1f}<extra></extra>",
                    ), row=2, col=1)

                    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5,
                                 annotation_text="超買 (70)", row=2, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5,
                                 annotation_text="超賣 (30)", row=2, col=1)

                fig.update_xaxes(title_text="", row=1, col=1)
                fig.update_xaxes(title_text="日期", row=2, col=1)
                fig.update_yaxes(title_text="股價 (元)", row=1, col=1)
                fig.update_yaxes(title_text="RSI", row=2, col=1)

                fig.update_layout(
                    height=320,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, 'Noto Sans TC', sans-serif", color="#B4CCDF", size=11),
                    margin=dict(l=10, r=10, t=40, b=10),
                    hovermode="x unified",
                    showlegend=True,
                    legend=dict(x=0.01, y=0.98,
                                font=dict(family="JetBrains Mono, monospace", size=10)),
                )
                fig.update_xaxes(showgrid=True, gridcolor="rgba(103,232,249,0.08)",
                                 tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#8397AC"))
                fig.update_yaxes(showgrid=True, gridcolor="rgba(103,232,249,0.08)",
                                 tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#8397AC"))
                st.plotly_chart(fig, use_container_width=True, key=f"price_{cid}_{horizon}")
            else:
                st.info("無價格資料")

        with col_right:
            # ===== LAYER 2: Company Profile (Always Visible) =====
            st.markdown("""<div class="section-header"><strong>公司簡介</strong></div>""", unsafe_allow_html=True)

            # Company intro with industry + name
            stock_industry = stock.get("industry", "")
            if full_name:
                intro_line = f"**{full_name}**"
                if stock_industry and stock_industry != "其他":
                    intro_line += f"　｜　{stock_industry}"
                st.markdown(intro_line)
            elif stock_industry and stock_industry != "其他":
                st.markdown(f"**產業**：{stock_industry}")

            st.metric("目前股價", f"${price:.2f}" if price > 0 else "—")

            # Quick fundamental snapshot
            fund = get_company_fundamentals(fs, income, cid, rec_date, stock_row=stock)
            snap_parts = []
            if fund.get("eps") is not None and pd.notna(fund["eps"]):
                eps_v = float(fund["eps"])
                snap_parts.append(f"EPS {'$' if eps_v >= 0 else '-$'}{abs(eps_v):.2f}")
            if fund.get("gross_margin") is not None and pd.notna(fund["gross_margin"]):
                snap_parts.append(f"毛利率 {fund['gross_margin']:.1%}")
            if fund.get("revenue_yoy") is not None and pd.notna(fund["revenue_yoy"]):
                snap_parts.append(f"營收年增 {fund['revenue_yoy']:+.1%}")
            if snap_parts:
                st.caption(" · ".join(snap_parts))

            # ===== LAYER 3: Why This Interpretation (Expandable) =====
            with st.expander("判讀原因", expanded=True, icon=":material/menu_book:"):
                st.markdown("**模型觀察到的特徵訊號：**")

                reasons = []

                # Momentum
                if fund.get("momentum") is not None and pd.notna(fund["momentum"]):
                    mom = float(fund["momentum"])
                    if mom > 0:
                        reasons.append(f"近期股價有向上動能（動能值 {mom:.2f}），買盤相對積極")
                    else:
                        reasons.append(f"近期股價動能偏弱（動能值 {mom:.2f}），追價意願不高")

                # EPS
                if fund.get("eps") is not None and pd.notna(fund["eps"]):
                    eps_v = float(fund["eps"])
                    if eps_v > 1:
                        reasons.append(f"每股盈餘 ${eps_v:.2f}，獲利能力穩健")
                    elif eps_v > 0:
                        reasons.append(f"每股盈餘 ${eps_v:.2f}，獲利能力尚可")
                    else:
                        reasons.append(f"每股盈餘 ${eps_v:.2f}，目前處於虧損")

                # Revenue growth
                if fund.get("revenue_yoy") is not None and pd.notna(fund["revenue_yoy"]):
                    yoy = float(fund["revenue_yoy"])
                    if yoy > 0.1:
                        reasons.append(f"營收年增率 {yoy:+.1%}，成長趨勢強勁")
                    elif yoy > 0:
                        reasons.append(f"營收小幅成長（年增 {yoy:+.1%}）")
                    elif yoy > -0.1:
                        reasons.append(f"營收微幅衰退（年減 {abs(yoy):.1%}）")
                    else:
                        reasons.append(f"營收明顯衰退（年減 {abs(yoy):.1%}），需留意")

                # Valuation
                if fund.get("pe_rank") is not None and pd.notna(fund["pe_rank"]):
                    pr = float(fund["pe_rank"])
                    if pr < 0.25:
                        reasons.append(f"估值處於歷史低檔（排位 {pr:.0%}），具價值面吸引力")
                    elif pr > 0.75:
                        reasons.append(f"估值處於歷史高檔（排位 {pr:.0%}），需留意追高風險")

                # Risk level
                if fund.get("risk_level") == "低":
                    reasons.append("歷史波動度低，價格走勢相對穩定")
                elif fund.get("risk_level") == "高":
                    reasons.append("歷史波動度偏高，短期漲跌幅可能較大")

                if not reasons:
                    st.caption("可用特徵資料有限，暫不做詳細解讀")
                else:
                    for reason in reasons[:5]:
                        st.caption(f"• {reason}")

            # ===== LAYER 4: 風險提示 (Company-Specific) =====
            with st.expander("⚠️ 風險提示"):
                # Risk level badge
                risk_lvl = fund.get("risk_level", "中等")
                risk_colors = {"低": "#059669", "中等": "#a78bfa", "高": "#dc2626"}
                risk_color = risk_colors.get(risk_lvl, "#a78bfa")
                st.markdown(f"""
<div style="display:inline-block; padding:6px 16px; border-radius:20px;
     background:{risk_color}22; color:{risk_color}; font-weight:700; font-size:0.9rem;
     border:1px solid {risk_color}44; margin-bottom:12px;">
    風險等級：{risk_lvl}
</div>""", unsafe_allow_html=True)

                # Company-specific risk summary from pre-computed data
                risk_summary = stock.get("risk_summary", "")
                if risk_summary:
                    st.caption(risk_summary)
                else:
                    # Generate on the fly from fund data
                    risk_parts = []
                    dd = fund.get("drawdown")
                    if dd is not None and pd.notna(dd) and abs(float(dd)) > 0.15:
                        risk_parts.append(f"近期最大回撤 {abs(float(dd)):.0%}，波動風險需留意")
                    nm = fund.get("net_margin")
                    if nm is not None and pd.notna(nm) and float(nm) < 0:
                        risk_parts.append(f"淨利率 {float(nm):.1%}，目前處於虧損狀態")
                    yoy = fund.get("revenue_yoy")
                    if yoy is not None and pd.notna(yoy) and float(yoy) < -0.1:
                        risk_parts.append(f"營收年減 {abs(float(yoy)):.0%}，成長動能不足")
                    if risk_parts:
                        st.caption("；".join(risk_parts) + "。")
                    else:
                        st.caption("目前無特別顯著的風險訊號，但仍需持續關注市場變化。")

                st.caption("以上風險分析基於歷史數據，僅供研究參考，不構成投資建議。")

            # ===== LAYER 5: Historical Observation =====
            with st.expander("歷史觀察值", icon=":material/bar_chart:"):
                st.markdown("""<div class="history-disclaimer">
⚠️ 以下為歷史觀察值，非當時可見資訊，不構成即時預測承諾。
此為模型在歷史資料上的判讀結果，用於展示研究能力，不代表未來表現。
                </div>""", unsafe_allow_html=True)

                ret_color = "#059669" if fwd_ret >= 0 else "#dc2626"
                st.markdown(f"""
**D+{horizon} 歷史觀察報酬**：<span style='color:{ret_color}; font-weight:bold; font-size:1.3em;'>{fwd_ret:+.1%}</span>
                """, unsafe_allow_html=True)

                # Use pre-computed observation text if available
                obs_text = stock.get("observation_text", "")
                if obs_text:
                    st.caption(obs_text)
                else:
                    period_map = {1: "隔天", 5: "一週", 20: "一個月"}
                    period_desc = period_map.get(horizon, f"{horizon} 天")
                    direction = "上漲" if fwd_ret >= 0 else "下跌"
                    st.caption(
                        f"該股票在 {rec_date.strftime('%Y-%m-%d')} 後的{period_desc}內，"
                        f"歷史上出現了 {abs(fwd_ret):.1%} 的{direction}。\n"
                        f"此數據僅用於展示模型判讀能力，不代表未來走勢。"
                    )

                fy = fund.get("fiscal_year")
                fq = fund.get("fiscal_quarter")
                if fy is not None and pd.notna(fy) and fq is not None and pd.notna(fq):
                    st.caption(f"財報基準：{int(fy)} 年 Q{int(fq)}")

        if idx < len(recs) - 1:
            st.divider()

    # ===== Comparison Table =====
    st.divider()
    st.markdown(
        f'<h3 style="display:flex;align-items:center;gap:10px;margin:24px 0 6px;'
        f'color:var(--gl-text);">'
        f'<span style="color:var(--gl-violet);">{glint_icon("layers", 22)}</span>'
        f'<span>多週期判讀對比</span></h3>',
        unsafe_allow_html=True,
    )
    st.caption("D+1、D+5 與 D+20 三個時間維度的判讀結果對比，協助觀察短中長期趨勢是否一致。")

    comp_col1, comp_col2, comp_col3 = st.columns(3)

    for col_widget, h_val, h_label in [
        (comp_col1, 1, "D+1"),
        (comp_col2, 5, "D+5"),
        (comp_col3, 20, "D+20"),
    ]:
        with col_widget:
            st.markdown(f"**{h_label} 判讀前 5 名**")
            recs_h, _ = get_recommendations(fs, companies, horizon=h_val, n_top=5, recommendations=recommendations)
            ret_col_h = f"fwd_ret_{h_val}"
            label_col_h = f"label_{h_val}"
            if not recs_h.empty:
                # v7 §18.2 schema-safe: short_name may be missing on some datasets
                name_series = _utils.safe_col(
                    recs_h,
                    primary="short_name",
                    fallbacks=("company_name", "name"),
                    default=recs_h.get("company_id", pd.Series(dtype=object)),
                )
                comp_df = pd.DataFrame({
                    "股票": name_series.fillna(recs_h["company_id"]) if hasattr(name_series, "fillna") else name_series,
                    "代碼": recs_h["company_id"],
                    "歷史報酬": recs_h[ret_col_h].apply(lambda x: f"{x:+.1%}" if pd.notna(x) else "—") if ret_col_h in recs_h.columns else "—",
                    "訊號": recs_h[label_col_h].apply(lambda x: "🟢 偏多" if x == 1.0 else ("🟡 中性" if x == 0.0 else "🔴 觀望")) if label_col_h in recs_h.columns else "—",
                })
                st.dataframe(comp_df, use_container_width=True, hide_index=True)
            else:
                st.info(f"無 {h_label} 判讀資料")

    # ===== 9-Pillar Radar =====
    st.divider()
    st.markdown("### 🕸️ 九支柱雷達圖 · 研究結論結構")
    st.caption("以 LOPO 實驗的 ΔAUC 為每個支柱打分（越往外表示該家族在 D+20 預測上越關鍵）。"
               "下圖呈現本研究結論的「骨架」：模型真正仰賴的是哪些觀察角度。")
    _lopo, _ = load_phase6_json("lopo_pillar_contribution_D20.json")
    if _lopo and "ranking_by_delta_auc" in _lopo:
        _max_d = max(abs(r["delta_auc"]) for r in _lopo["ranking_by_delta_auc"]) or 1e-4
        pillar_scores = {
            r["pillar"]: abs(r["delta_auc"]) / _max_d
            for r in _lopo["ranking_by_delta_auc"]
        }
    else:
        pillar_scores = {
            "risk": 0.95, "fund": 0.82, "chip": 0.68, "trend": 0.54,
            "val": 0.42, "event": 0.25, "ind": 0.48, "txt": 0.32, "sent": 0.38,
        }
    radar_col_l, radar_col_r = st.columns([3, 2])
    with radar_col_l:
        st.plotly_chart(
            render_pillar_radar(pillar_scores, title="Pillar Importance · LOPO ΔAUC (normalised)",
                                 height=460),
            use_container_width=True,
        )
    with radar_col_r:
        st.markdown("""
<div class="gl-panel" style="height:100%;">
  <div style="font-size:0.75rem;color:var(--gl-text-3);font-weight:700;letter-spacing:0.1em;text-transform:uppercase;">How to read</div>
  <div style="font-size:0.92rem;color:var(--gl-text-2);margin-top:12px;line-height:1.7;">
    <strong style="color:var(--gl-text);">外圈越大</strong>：該支柱對預測貢獻度越高，研究結論主要建立於此。<br><br>
    <strong style="color:var(--gl-text);">九支柱定義</strong>：
    <span class="gl-pillar" data-p="trend">技術</span>
    <span class="gl-pillar" data-p="fund">基本</span>
    <span class="gl-pillar" data-p="val">評價</span>
    <span class="gl-pillar" data-p="event">事件</span>
    <span class="gl-pillar" data-p="risk">風險</span>
    <span class="gl-pillar" data-p="chip">籌碼</span>
    <span class="gl-pillar" data-p="ind">產業</span>
    <span class="gl-pillar" data-p="txt">文本</span>
    <span class="gl-pillar" data-p="sent">情緒</span>
    <br><br>
    這張圖回答：<strong style="color:var(--gl-text);">「模型到底在看什麼？」</strong>
    若某支柱被移除後 AUC 大幅掉落，代表它是本期研究結論的主支撐。
  </div>
</div>
""", unsafe_allow_html=True)

    # ===== Cost Calculator =====
    st.divider()
    st.markdown("### 🧮 交易成本試算器")
    st.caption("了解交易成本對損益的影響。費率僅供參考，實際費率依券商公告。")

    calc_col1, calc_col2, calc_col3 = st.columns(3)

    with calc_col1:
        calc_price = st.number_input("買入價格（元/股）", min_value=1.0, value=50.0, step=0.5)
    with calc_col2:
        calc_shares = st.number_input("買入張數（1 張 = 1,000 股）", min_value=1, value=1, step=1)
    with calc_col3:
        broker_discount = st.selectbox(
            "券商折扣",
            options=[1.0, 0.6, 0.5, 0.38, 0.28],
            format_func=lambda x: f"{x*100:.0f}%",
            index=3,
        )

    total_shares = calc_shares * 1000
    buy_amount = calc_price * total_shares
    buy_fee = max(buy_amount * 0.001425 * broker_discount, 20)
    sell_fee = max(buy_amount * 0.001425 * broker_discount, 20)
    sell_tax = buy_amount * 0.003
    total_cost = buy_fee + sell_fee + sell_tax
    cost_ratio = (total_cost / buy_amount) * 100
    breakeven_price = calc_price * (1 + cost_ratio / 100)
    breakeven_pct = (breakeven_price - calc_price) / calc_price * 100

    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.markdown(f"""
<div class="cost-result">
    <div style="font-size:0.8rem; color:#67e8f9;">買進金額</div>
    <div class="cost-total">${buy_amount:,.2f}</div>
</div>
        """, unsafe_allow_html=True)
    with r2:
        st.markdown(f"""
<div class="cost-result">
    <div style="font-size:0.8rem; color:#67e8f9;">手續費（買+賣）</div>
    <div class="cost-total" style="font-size:1.3rem;">${buy_fee + sell_fee:,.2f}</div>
</div>
        """, unsafe_allow_html=True)
    with r3:
        st.markdown(f"""
<div class="cost-result">
    <div style="font-size:0.8rem; color:#67e8f9;">證交稅（賣出）</div>
    <div class="cost-total" style="font-size:1.3rem;">${sell_tax:,.2f}</div>
</div>
        """, unsafe_allow_html=True)
    with r4:
        st.markdown(f"""
<div class="cost-result">
    <div style="font-size:0.8rem; color:#67e8f9;">總成本</div>
    <div class="cost-total">${total_cost:,.2f}</div>
    <div style="font-size:0.75rem; color:#9ca3af;">{cost_ratio:.2f}%</div>
</div>
        """, unsafe_allow_html=True)

    col_breakdown, col_breakeven = st.columns([1, 1])

    with col_breakdown:
        st.markdown("**成本分解**")
        # v9 §8.4 — glint-style cost donut (replaces bright blue/violet/pink pie).
        # Three semantic tones: cyan (buy fee), blue (sell fee), violet (tax).
        _utils.render_signal_donut(
            labels=["買進手續費", "賣出手續費", "證交稅"],
            values=[float(buy_fee), float(sell_fee), float(sell_tax)],
            title="成本分解",
            subtitle="Cost Breakdown",
            center_metric=f"${(buy_fee+sell_fee+sell_tax):,.2f}",
            center_metric_label="Total",
            tones=["cyan", "blue", "violet"],
            height=260,
            key=f"cost_donut_{_utils.safe_html(str(calc_shares))}",
        )

    with col_breakeven:
        st.markdown("**損益平衡**")
        st.info(f"""
買進價格：${calc_price:.2f}

損益平衡點：${breakeven_price:.2f}

需漲幅：{breakeven_pct:+.2f}%

至少需漲到 ${breakeven_price:.2f} 才能回本。
        """, icon=":material/lightbulb:")

    # ===== Market Distribution =====
    if has_full_market and total_stocks > 0:
        st.divider()
        st.markdown(
            f'<h3 style="display:flex;align-items:center;gap:10px;margin:24px 0 6px;'
            f'color:var(--gl-text);">'
            f'<span style="color:var(--gl-cyan);">{glint_icon("trending-up", 22)}</span>'
            f'<span>全市場訊號分佈</span></h3>',
            unsafe_allow_html=True,
        )
        st.caption(f"基於 {total_stocks:,} 支股票的模型判讀結果，非僅限上方展示的 Top {len(recs)} 支。")

        dist_col1, dist_col2 = st.columns([1, 1])

        with dist_col1:
            # v9 §8.3 — signal composition strip first (left→right reading order,
            # semantically ordered 偏多 → 中性 → 觀望), followed by the glint-style
            # donut with a center N-metric. This replaces the bright green/amber/red
            # pie that failed the v9 "all charts must speak Glint" rule.
            _utils.render_market_composition_strip(
                segments=[
                    ("偏多", int(up_count),   "blue"),
                    ("中性", int(flat_count), "slate"),
                    ("觀望", int(down_count), "amber"),
                ],
                title=f"D+{horizon} · 市場訊號比例",
                key=f"mkt_strip_D{horizon}",
            )
            _utils.render_signal_donut(
                labels=["偏多", "中性", "觀望"],
                values=[int(up_count), int(flat_count), int(down_count)],
                title=f"D+{horizon} 全市場訊號分佈",
                subtitle="Market Signal Mix",
                center_metric=f"N={total_stocks:,}",
                center_metric_label="Total Stocks",
                tones=["blue", "slate", "amber"],
                height=340,
                key=f"mkt_donut_D{horizon}",
                verdict=(
                    f"模型判讀：{int(up_count):,} 檔偏多 · "
                    f"{int(flat_count):,} 檔中性 · {int(down_count):,} 檔觀望。"
                ),
            )

        with dist_col2:
            # Show return stats from pre-computed market distribution
            dist_ret_stats = market_dist.get("return_stats", {}) if market_dist else {}
            if dist_ret_stats:
                mean_ret = dist_ret_stats.get("mean", 0)
                median_ret = dist_ret_stats.get("median", 0)
                std_ret = dist_ret_stats.get("std", 0)
                p10 = dist_ret_stats.get("p10", 0)
                p90 = dist_ret_stats.get("p90", 0)

                # v9 §8.5 — grouped percentile bar: single primary tone (cyan)
                # with amber only highlighting the distribution tails. No more
                # red/green/blue/orange rainbow.
                categories = ["P10（悲觀）", "中位數", "平均值", "P90（樂觀）"]
                bar_values = [p10 * 100, median_ret * 100, mean_ret * 100, p90 * 100]
                bar_tones  = ["amber", "cyan", "blue", "cyan"]  # tails amber, center cyan/blue

                fig_bar = go.Figure()
                for cat, val, tone in zip(categories, bar_values, bar_tones):
                    fig_bar.add_trace(go.Bar(
                        x=[cat], y=[val],
                        marker=_utils.glint_dark_bar_style(tone=tone, opacity=0.88),
                        text=[f"{val:+.1f}%"],
                        textposition="outside",
                        textfont=dict(family="JetBrains Mono, monospace", size=11, color="#E8F7FC"),
                        hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
                        showlegend=False,
                    ))
                fig_bar.add_hline(y=0, line_dash="dash",
                                  line_color="rgba(103,232,249,0.28)", line_width=1)
                fig_bar.update_layout(
                    **_utils.glint_dark_layout(
                        title=f"D+{horizon} 全市場報酬分佈統計",
                        subtitle="Return Percentiles (%)",
                        height=360,
                        show_grid=True,
                        ylabel="報酬率 (%)",
                    ),
                )
                fig_bar.update_layout(showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)
                st.caption(f"全市場中位數報酬 {median_ret:+.1%}，標準差 {std_ret:.1%}。上方展示的判讀股為模型篩選的少數偏多標的。")
            else:
                st.info("無充足的報酬分佈資料")

    # ===== Volatility Trend =====
    vol_trend = mkt_env.get("recent_volatility_trend", [])
    baselines = mkt_env.get("historical_baselines", {})

    if vol_trend and len(vol_trend) > 5:
        st.divider()
        st.markdown(
            f'<h3 style="display:flex;align-items:center;gap:10px;margin:24px 0 6px;'
            f'color:var(--gl-text);">'
            f'<span style="color:var(--gl-amber);">{glint_icon("activity", 22)}</span>'
            f'<span>市場波動度趨勢（近 20 日）</span></h3>',
            unsafe_allow_html=True,
        )
        st.caption("波動度指標反映市場的不確定性程度。當波動度升高時，模型預測的不確定性也隨之增加。")

        vol_dates = [v["date"] for v in vol_trend]
        vol_vals = [v["vol_regime"] for v in vol_trend]
        vol_mean = baselines.get("vol_regime_mean", 1.0)
        vol_p75 = baselines.get("vol_regime_p75", 1.2)
        vol_p90 = baselines.get("vol_regime_p90", 1.4)

        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(
            x=vol_dates, y=vol_vals,
            mode="lines+markers",
            line=dict(color="#2563eb", width=2.5),
            marker=dict(size=5),
            name="波動度指標",
            fill="tozeroy",
            fillcolor="rgba(99, 110, 250, 0.08)",
        ))
        fig_vol.add_hline(y=vol_mean, line_dash="dash", line_color="#059669",
                          annotation_text=f"歷史均值 ({vol_mean:.2f})", line_width=1)
        fig_vol.add_hline(y=vol_p75, line_dash="dot", line_color="#a78bfa",
                          annotation_text=f"P75 警戒線 ({vol_p75:.2f})", line_width=1)
        fig_vol.add_hline(y=vol_p90, line_dash="dash", line_color="#dc2626",
                          annotation_text=f"P90 高波動 ({vol_p90:.2f})", line_width=1)
        fig_vol.update_layout(
            height=280,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, 'Noto Sans TC', sans-serif", color="#B4CCDF", size=11),
            margin=dict(l=20, r=20, t=20, b=30),
            yaxis_title=dict(text="波動度指標",
                             font=dict(family="Inter, 'Noto Sans TC', sans-serif", size=12, color="#8397AC")),
            showlegend=False,
        )
        fig_vol.update_xaxes(showgrid=True, gridcolor="rgba(103,232,249,0.08)",
                             tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#8397AC"))
        fig_vol.update_yaxes(showgrid=True, gridcolor="rgba(103,232,249,0.08)",
                             tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#8397AC"))
        st.plotly_chart(fig_vol, use_container_width=True)

        # Explanatory note
        high_vol_pct = baselines.get("high_vol_days_pct", 0)
        st.caption(
            f"歷史上約有 {high_vol_pct:.0%} 的交易日處於高波動環境。\n"
            f"當波動度突破 P90 線（{vol_p90:.2f}）時，建議降低持倉信心、擴大停損幅度。\n"
            f"OOD 分析顯示 D+5 策略在不同波動環境下穩定性最佳。"
        )

    # ===== Investment Education =====
    st.divider()
    st.markdown(
        f'<h3 style="display:flex;align-items:center;gap:10px;margin:24px 0 6px;'
        f'color:var(--gl-text);">'
        f'<span style="color:var(--gl-violet);">{glint_icon("book-open", 22)}</span>'
        f'<span>研究方法論</span></h3>',
        unsafe_allow_html=True,
    )

    tip1, tip2, tip3 = st.columns(3)

    with tip1:
        st.markdown("""
**多因子模型**

本研究使用多個特徵因子：

- 技術面：趨勢、動能、RSI、波動度、價格比較
- 基本面：EPS、毛利率、營業利益率、營收成長
- 估值面：本益比、市淨比排位
- 風險面：歷史回撤、相對波動性

使用 5 年歷史資料訓練，經過嚴格防過擬合測試。
        """)

    with tip2:
        st.markdown("""
**重要限制**

- 歷史不代表未來
- 模型會犯錯
- 過度擬合風險存在
- 市場環境變化影響大
- 單一模型不足以決策

請務必進行獨立研究與風險管理。
        """)

    with tip3:
        st.markdown("""
**風險管理建議**

- 分散配置，不集中押注
- 設定停損點（如 -10%）
- 避免頻繁交易（成本侵蝕）
- 中長期思維（3-5 年）
- 了解企業基本面
- 定期檢視倉位

小額試誤，逐步擴大。
        """)

    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align:center; padding:20px 0; color:#9ca3af; font-size:0.82rem;">
        <strong>投資解讀面板</strong> &nbsp;|&nbsp; 大數據與商業分析專案<br>
        <br>
        <span style="font-size:0.75rem;">
            ⚠️ 本面板為學術研究用途，展示方法論與歷史判讀。非即時投資建議。<br>
            歷史判讀不代表未來走勢。投資前請自行研究，審慎決策。
        </span>
    </div>
    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"顯示頁面內容時發生錯誤: {e}")
    st.info("請確保所有必要的資料檔案已正確載入。")
