"""
投資解讀面板 — 歷史快照判讀 + 五層資訊架構 + 漸進式揭露

目標使用者：想了解研究方法論與歷史模型判讀的投資者
核心邏輯：展示固定歷史時期內的模型判讀結果，用於展示研究能力
展示資訊：
  - 每期的模型判讀方向（D+5 / D+20）與信心度
  - 五層資訊架構：方向信心 > 公司基本面 > 解讀原因 > 成本風險 > 歷史觀察值
  - 近期價格走勢圖 + 技術指標（MA20、RSI）
  - 漸進式揭露（expandable 設計）
  - 交易成本試算（用於教育目的）
  - 市場信號分佈 + 報酬分析
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

# ===== Page Config =====
# NOTE: st.set_page_config() is now managed by st.navigation in app.py
# Do not uncomment or re-add the set_page_config call

# ===== Custom CSS =====
st.markdown("""
<style>

    /* KPI cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f8f9fc 0%, #e8ecf4 100%);
        border: 1px solid #dde1eb;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.82rem !important;
        color: #5a6577 !important;
    }

    /* Stock card with left border indicator */
    .stock-card {
        background: #ffffff;
        border: 1px solid #e0e4ea;
        border-left: 5px solid #636EFA;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .stock-card.bullish {
        border-left-color: #059669;
    }
    .stock-card.neutral {
        border-left-color: #f59e0b;
    }
    .stock-card.bearish {
        border-left-color: #dc2626;
    }

    .stock-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 12px;
    }
    .stock-name {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1a1f36;
    }
    .stock-id {
        font-size: 0.9rem;
        color: #636EFA;
        font-weight: 600;
        margin-left: 8px;
    }

    /* Confidence badge */
    .confidence-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .confidence-high {
        background: #dbeafe;
        color: #0c4a6e;
    }
    .confidence-medium {
        background: #fed7aa;
        color: #7c2d12;
    }
    .confidence-low {
        background: #fecaca;
        color: #7f1d1d;
    }

    /* Direction badge */
    .direction-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
    }
    .direction-bullish {
        background: #ecfdf5;
        color: #059669;
    }
    .direction-neutral {
        background: #fef3c7;
        color: #92400e;
    }
    .direction-bearish {
        background: #fef2f2;
        color: #dc2626;
    }

    /* Info panels */
    .info-panel {
        background: #f8fafc;
        border-left: 4px solid #636EFA;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    .warning-panel {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 12px 0;
        font-size: 0.9rem;
    }

    .history-disclaimer {
        background: #fef2f2;
        border-left: 4px solid #dc2626;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.85rem;
        color: #7f1d1d;
        font-weight: 500;
    }

    /* Metric boxes */
    .metric-box {
        background: linear-gradient(135deg, #f8f9fc 0%, #f0f2f8 100%);
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 10px 14px;
        text-align: center;
        font-size: 0.85rem;
    }
    .metric-val {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1a1f36;
        margin-top: 4px;
    }
    .metric-label {
        font-size: 0.7rem;
        color: #6b7280;
    }

    /* Section header */
    .section-header {
        border-left: 4px solid #636EFA;
        padding-left: 12px;
        margin-top: 24px;
        margin-bottom: 16px;
    }

    /* Cost result */
    .cost-result {
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
    }
    .cost-total {
        font-size: 1.8rem;
        font-weight: 700;
        color: #059669;
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
            st.error(f"載入 dashboard/data/ 時發生錯誤: {e}")
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
            fs = pd.read_parquet(base / "outputs" / "feature_store.parquet")
        except Exception as e:
            st.error(f"無法載入資料: {e}")
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
                recs_df = recs_df.merge(companies, on="company_id", how="left")
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
        result["eps"] = latest.get("eps")

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
                if drawdown > 0.3:
                    result["risk_level"] = "高"
                elif drawdown > 0.15:
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

        if stock_row.get("fund_revenue_yoy"):
            result["revenue_yoy"] = stock_row.get("fund_revenue_yoy")

        # Risk level
        drawdown = stock_row.get("risk_drawdown")
        if pd.notna(drawdown):
            if drawdown > 0.3:
                result["risk_level"] = "高"
            elif drawdown > 0.15:
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
    /* Selectbox & slider inner text */
    section[data-testid="stSidebar"] [data-baseweb="select"] {
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #e8edf3 !important;
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
st.sidebar.markdown("### 🌱 投資解讀面板")
st.sidebar.caption("固定歷史資料期間的模型判讀展示")
st.sidebar.divider()

horizon = st.sidebar.selectbox(
    "📅 預測週期",
    options=[20, 5],
    format_func=lambda x: f"D+{x}（{'約一個月 ≈ 20 交易日' if x == 20 else '約一週 ≈ 5 交易日'}）",
    index=0,
)

n_display = st.sidebar.slider("📊 顯示判讀數量", 3, 10, 5)

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
    # Historical context disclaimer
    st.markdown("""
    <div class="warning-panel">
        <strong>📋 面板說明</strong><br>
        本頁面呈現的是固定歷史資料期間內的模型判讀結果，用於展示研究能力與方法論，非即時投資建議。
        歷史判讀不構成未來預測，過去績效不代表未來報酬。
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"# 🌱 投資解讀面板 — D+{horizon} 判讀結果")

    # Get recommendations
    recs, rec_date = get_recommendations(fs, companies, horizon=horizon, n_top=n_display, recommendations=recommendations)

    if rec_date:
        st.caption(f"快照日期：{rec_date.strftime('%Y-%m-%d')}（歷史基準日）")
    else:
        st.warning("目前沒有可用的判讀資料")
        st.stop()

    if recs.empty:
        st.info(f"在 D+{horizon} 週期的判讀中，目前沒有偏多信號。")
        st.stop()

    # ===== Market Overview =====
    st.markdown("### 📊 本期市場概況")

    label_col = f"label_{horizon}"
    ret_col = f"fwd_ret_{horizon}"

    # Use market_summary from recommendations if available
    total_stocks = 1886  # Default fallback
    if recommendations and "market_summary" in recommendations:
        total_stocks = recommendations["market_summary"].get("total_stocks_tracked", 1886)

    # Compute direction counts from entire recommendations data
    if recommendations and f"horizon_{horizon}" in recommendations:
        all_recs = recommendations[f"horizon_{horizon}"].get("stocks", [])
        all_recs_df = pd.DataFrame(all_recs)
        up_count = (all_recs_df.get(label_col, all_recs_df.get("label_20", [])) == 1.0).sum()
        flat_count = (all_recs_df.get(label_col, all_recs_df.get("label_20", [])) == 0.0).sum()
        down_count = (all_recs_df.get(label_col, all_recs_df.get("label_20", [])) == -1.0).sum()
    elif fs is not None:
        latest_snap = fs[fs["trade_date"] == rec_date]
        up_count = (latest_snap[label_col] == 1.0).sum()
        flat_count = (latest_snap[label_col] == 0.0).sum()
        down_count = (latest_snap[label_col] == -1.0).sum()
    else:
        # Fallback: use only available recs
        up_count = (recs[label_col] == 1.0).sum()
        flat_count = (recs[label_col] == 0.0).sum()
        down_count = (recs[label_col] == -1.0).sum()

    avg_ret = recs[ret_col].mean()

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("分析股票數", f"{int(total_stocks):,}")
    with k2:
        pct_up = (up_count / total_stocks * 100) if total_stocks > 0 else 0
        st.metric("🟢 偏多", f"{int(up_count)}", delta=f"{pct_up:.1f}%")
    with k3:
        pct_flat = (flat_count / total_stocks * 100) if total_stocks > 0 else 0
        st.metric("🟡 中性", f"{int(flat_count)}", delta=f"{pct_flat:.1f}%")
    with k4:
        pct_down = (down_count / total_stocks * 100) if total_stocks > 0 else 0
        st.metric("🔴 觀望", f"{int(down_count)}", delta=f"{pct_down:.1f}%")
    with k5:
        st.metric("判讀股平均報酬", f"{avg_ret:+.1%}")

    st.divider()

    # ===== Stock Cards with 5-Layer Architecture =====
    st.markdown(f"### 📌 判讀結果 Top {len(recs)}")
    st.caption("以下為按模型信心度與預測報酬排序的判讀結果。展開各層瞭解詳細資訊。")

    for idx, (_, stock) in enumerate(recs.iterrows()):
        cid = str(stock["company_id"])
        name = stock.get("short_name", cid)
        full_name = stock.get("company_name", "")
        price = float(stock.get("closing_price", 0) or 0)
        fwd_ret = float(stock.get(ret_col, 0) or 0)
        label_val = float(stock.get(label_col, 0) or 0)

        direction_label, direction_class = get_direction_label(label_val)
        direction_emoji = get_direction_emoji(label_val)

        # Determine confidence level
        fwd_abs = abs(fwd_ret)
        if fwd_abs > 0.15:
            conf_level = "高"
            conf_class = "confidence-high"
        elif fwd_abs > 0.08:
            conf_level = "中"
            conf_class = "confidence-medium"
        else:
            conf_level = "低"
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
            <span class="confidence-badge {conf_class}">信心：{conf_level}</span>
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
                    line=dict(color="#636EFA", width=2.5),
                    fill="tozeroy",
                    fillcolor="rgba(99, 110, 250, 0.08)",
                    name="收盤價",
                    hovertemplate="日期: %{x|%Y-%m-%d}<br>收盤價: $%{y:.2f}<extra></extra>",
                ), row=1, col=1)

                fig.add_trace(go.Scatter(
                    x=price_hist["trade_date"],
                    y=price_hist["ma20"],
                    mode="lines",
                    line=dict(color="#f59e0b", width=1.5, dash="dash"),
                    name="MA20",
                    hovertemplate="MA20: $%{y:.2f}<extra></extra>",
                ), row=1, col=1)

                fig.add_trace(go.Scatter(
                    x=[price_hist["trade_date"].iloc[-1]],
                    y=[price_hist["closing_price"].iloc[-1]],
                    mode="markers",
                    marker=dict(size=12, color="#636EFA"),
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
                    template="plotly_white",
                    margin=dict(l=10, r=10, t=40, b=10),
                    hovermode="x unified",
                    showlegend=True,
                    legend=dict(x=0.01, y=0.98)
                )
                st.plotly_chart(fig, use_container_width=True, key=f"price_{cid}_{horizon}")
            else:
                st.info("無價格資料")

        with col_right:
            # ===== LAYER 2: Company Profile (Always Visible) =====
            st.markdown("""<div class="section-header"><strong>公司資訊</strong></div>""", unsafe_allow_html=True)

            if full_name:
                st.caption(f"{full_name}")

            st.metric("目前股價", f"${price:.2f}" if price > 0 else "—")

            # ===== LAYER 3: Why This Interpretation (Expandable) =====
            with st.expander("📖 判讀原因", expanded=True):
                fund = get_company_fundamentals(fs, income, cid, rec_date, stock_row=stock)

                st.markdown("**基於以下特徵分析：**")

                reasons = []

                # Momentum
                if fund.get("momentum") is not None:
                    mom = fund["momentum"]
                    if mom > 0:
                        reasons.append(f"• 近期價格動能偏強（動能值：{mom:.2f}）")
                    else:
                        reasons.append(f"• 近期價格動能相對較弱（動能值：{mom:.2f}）")

                # EPS
                if fund.get("eps") is not None and fund["eps"] > 0:
                    reasons.append(f"• 基本面顯示獲利穩定（最新 EPS：${fund['eps']:.2f}）")
                elif fund.get("eps") is not None:
                    reasons.append(f"• 基本面獲利面臨挑戰（最新 EPS：${fund['eps']:.2f}）")

                # Valuation
                if fund.get("pe_rank") is not None:
                    if fund["pe_rank"] < 0.3:
                        reasons.append(f"• 估值相對偏低（本益比排位：{fund['pe_rank']:.1%}）")
                    elif fund["pe_rank"] > 0.7:
                        reasons.append(f"• 估值相對偏高（本益比排位：{fund['pe_rank']:.1%}）")

                # Revenue growth
                if fund.get("revenue_yoy") is not None:
                    if fund["revenue_yoy"] > 0.05:
                        reasons.append(f"• 營收成長趨勢向上（年增率：{fund['revenue_yoy']:+.1%}）")
                    elif fund["revenue_yoy"] < -0.05:
                        reasons.append(f"• 營收成長趨勢向下（年增率：{fund['revenue_yoy']:+.1%}）")

                # Risk
                if fund.get("risk_level") == "低":
                    reasons.append(f"• 歷史波動性相對穩定（風險等級：低）")
                elif fund.get("risk_level") == "高":
                    reasons.append(f"• 歷史波動性較大（風險等級：高）")

                if not reasons:
                    st.caption("資料不足，暫不做明確解讀")
                else:
                    for reason in reasons[:5]:
                        st.caption(reason)

            # ===== LAYER 4: Cost & Risk (Expandable) =====
            with st.expander("⚠️ 成本與風險"):
                fund = get_company_fundamentals(fs, income, cid, rec_date, stock_row=stock)

                c1, c2 = st.columns(2)
                with c1:
                    st.metric("風險等級", fund["risk_level"], help="基於歷史最大回撤計算")

                with c2:
                    if fund.get("rsi") is not None:
                        rsi_val = fund["rsi"]
                        if rsi_val > 70:
                            rsi_status = "超買"
                        elif rsi_val < 30:
                            rsi_status = "超賣"
                        else:
                            rsi_status = "正常"
                        st.metric("RSI-14", f"{rsi_val:.0f}", help=f"技術面動能：{rsi_status}")

                st.markdown("**交易成本概估**")
                st.caption("費率僅供參考，實際費率依券商公告")
                st.caption("""
- 買進手續費：0.1425%（券商可議價至 2.8 折）
- 賣出手續費：0.1425%
- 證交稅（賣出）：0.3%
- 總成本約 0.6-0.8%（含折扣）
                """)

            # ===== LAYER 5: Historical Observation =====
            with st.expander("📊 歷史觀察值"):
                st.markdown("""<div class="history-disclaimer">
⚠️ 以下為歷史觀察值，非當時可見資訊，不構成即時預測承諾。
此為模型在歷史資料上的判讀結果，用於展示研究能力，不代表未來表現。
                </div>""", unsafe_allow_html=True)

                ret_color = "#059669" if fwd_ret >= 0 else "#dc2626"
                st.markdown(f"""
**D+{horizon} 歷史觀察報酬**：<span style='color:{ret_color}; font-weight:bold; font-size:1.3em;'>{fwd_ret:+.1%}</span>
                """, unsafe_allow_html=True)

                st.caption(f"""
該股票在 {rec_date.strftime('%Y-%m-%d')} 後的 {horizon} 個交易日內，
歷史上實現了 {fwd_ret:+.1%} 的報酬。此數據僅用於展示模型判讀的準確性，
無法用於預測未來表現。
                """)

                fund = get_company_fundamentals(fs, income, cid, rec_date, stock_row=stock)
                if fund.get("fiscal_year"):
                    st.caption(f"財報基準：{fund['fiscal_year']} 年 Q{fund['fiscal_quarter']}")

        if idx < len(recs) - 1:
            st.divider()

    # ===== Comparison Table =====
    st.divider()
    st.markdown("### 📊 多週期判讀對比")
    st.caption("D+5 與 D+20 的判讀結果對比。")

    comp_col1, comp_col2 = st.columns(2)

    with comp_col1:
        st.markdown("**D+5 判讀前 5 名**")
        recs_5, _ = get_recommendations(fs, companies, horizon=5, n_top=5, recommendations=recommendations)
        if not recs_5.empty:
            comp_df_5 = pd.DataFrame({
                "股票": recs_5["short_name"].fillna(recs_5["company_id"]),
                "代碼": recs_5["company_id"],
                "現價": recs_5["closing_price"].apply(lambda x: f"${x:.2f}" if pd.notna(x) and x > 0 else "—"),
                "歷史報酬": recs_5["fwd_ret_5"].apply(lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
                "信號": recs_5["label_5"].apply(lambda x: "🟢 偏多" if x == 1.0 else ("🟡 中性" if x == 0.0 else "🔴 觀望")),
            })
            st.dataframe(comp_df_5, use_container_width=True, hide_index=True)
        else:
            st.info("無 D+5 判讀資料")

    with comp_col2:
        st.markdown("**D+20 判讀前 5 名**")
        recs_20, _ = get_recommendations(fs, companies, horizon=20, n_top=5, recommendations=recommendations)
        if not recs_20.empty:
            comp_df_20 = pd.DataFrame({
                "股票": recs_20["short_name"].fillna(recs_20["company_id"]),
                "代碼": recs_20["company_id"],
                "現價": recs_20["closing_price"].apply(lambda x: f"${x:.2f}" if pd.notna(x) and x > 0 else "—"),
                "歷史報酬": recs_20["fwd_ret_20"].apply(lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
                "信號": recs_20["label_20"].apply(lambda x: "🟢 偏多" if x == 1.0 else ("🟡 中性" if x == 0.0 else "🔴 觀望")),
            })
            st.dataframe(comp_df_20, use_container_width=True, hide_index=True)
        else:
            st.info("無 D+20 判讀資料")

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
    <div style="font-size:0.8rem; color:#5a6577;">買進金額</div>
    <div class="cost-total" style="color:#1a1f36;">${buy_amount:,.0f}</div>
</div>
        """, unsafe_allow_html=True)
    with r2:
        st.markdown(f"""
<div class="cost-result">
    <div style="font-size:0.8rem; color:#5a6577;">手續費（買+賣）</div>
    <div class="cost-total" style="font-size:1.3rem;">${buy_fee + sell_fee:,.0f}</div>
</div>
        """, unsafe_allow_html=True)
    with r3:
        st.markdown(f"""
<div class="cost-result">
    <div style="font-size:0.8rem; color:#5a6577;">證交稅（賣出）</div>
    <div class="cost-total" style="font-size:1.3rem;">${sell_tax:,.0f}</div>
</div>
        """, unsafe_allow_html=True)
    with r4:
        st.markdown(f"""
<div class="cost-result">
    <div style="font-size:0.8rem; color:#5a6577;">總成本</div>
    <div class="cost-total">${total_cost:,.0f}</div>
    <div style="font-size:0.75rem; color:#9ca3af;">{cost_ratio:.2f}%</div>
</div>
        """, unsafe_allow_html=True)

    col_breakdown, col_breakeven = st.columns([1, 1])

    with col_breakdown:
        st.markdown("**成本分解**")
        fig_cost = go.Figure(data=[go.Pie(
            labels=["買進手續費", "賣出手續費", "證交稅"],
            values=[buy_fee, sell_fee, sell_tax],
            marker_colors=["#3b82f6", "#8b5cf6", "#ec4899"],
            textinfo="label+value",
            textfont_size=11,
        )])
        fig_cost.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_cost, use_container_width=True)

    with col_breakeven:
        st.markdown("**損益平衡**")
        st.info(f"""
買進價格：${calc_price:.2f}

損益平衡點：${breakeven_price:.2f}

需漲幅：{breakeven_pct:+.2f}%

💡 至少需漲到 ${breakeven_price:.2f} 才能回本。
        """)

    # ===== Market Distribution =====
    st.divider()
    st.markdown("### 📈 市場信號分佈")

    dist_col1, dist_col2 = st.columns([1, 1])

    with dist_col1:
        fig_pie = go.Figure(data=[go.Pie(
            labels=["🟢 偏多", "🟡 中性", "🔴 觀望"],
            values=[int(up_count), int(flat_count), int(down_count)],
            marker_colors=["#059669", "#f59e0b", "#dc2626"],
            hole=0.4,
            textinfo="label+percent",
            textfont_size=11,
        )])
        fig_pie.update_layout(
            title=f"D+{horizon} 信號分佈",
            height=350,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with dist_col2:
        # Show distribution from available recommendations data
        if not recs.empty:
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=recs[ret_col] * 100,
                nbinsx=50,
                marker_color="#636EFA",
                opacity=0.7,
                hovertemplate="報酬率: %{x:.1f}%<br>股票數: %{y}<extra></extra>",
            ))
            fig_hist.add_vline(x=0, line_dash="dash", line_color="red", line_width=2,
                              annotation_text="零軸", annotation_position="right")
            fig_hist.update_layout(
                title=f"D+{horizon} 歷史報酬分佈（判讀股票）",
                xaxis_title="報酬率 (%)",
                yaxis_title="股票數",
                height=350,
                template="plotly_white",
                margin=dict(l=20, r=20, t=50, b=20),
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("無充足的報酬分佈資料")

    # ===== Investment Education =====
    st.divider()
    st.markdown("### 📚 研究方法論")

    tip1, tip2, tip3 = st.columns(3)

    with tip1:
        st.markdown("""
**🔬 23 因子多元模型**

本研究使用 23 個特徵因子：

- 技術面：趨勢、動能、RSI、波動度、價格比較
- 基本面：EPS、毛利率、營業利益率、營收成長
- 估值面：本益比、市淨比排位
- 風險面：歷史回撤、相對波動性

使用 5 年歷史資料訓練，經過嚴格防過擬合測試。
        """)

    with tip2:
        st.markdown("""
**⚠️ 重要限制**

- 歷史不代表未來
- 模型會犯錯
- 過度擬合風險存在
- 市場環境變化影響大
- 單一模型不足以決策

請務必進行獨立研究與風險管理。
        """)

    with tip3:
        st.markdown("""
**🛡️ 風險管理建議**

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
