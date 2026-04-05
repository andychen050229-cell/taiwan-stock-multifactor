"""
智慧選股看板 — 精選推薦 + 公司基本面 + 成本試算 + 風險提示

目標使用者：股市新手或小有經驗的散戶
提供資訊：
  - 每期精選推薦股票（D+5 / D+20）
  - 公司基本面摘要（EPS、毛利率、營收年增率、P/E、風險等級）
  - 近期價格走勢圖 + 技術指標（MA20、RSI）
  - 詳細新手解讀說明
  - 交易成本試算（含成本分解 + 損益平衡點分析）
  - 多週期對比表
  - 市場信號分佈 + 回報率分佈
  - 風險提示與投資教育
"""

import streamlit as st
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# ===== Page Config =====
st.set_page_config(
    page_title="智慧選股看板 | 台灣股市多因子預測系統",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Custom CSS (Enhanced) =====
st.markdown("""
<style>
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1f36 0%, #232946 100%);
    }
    section[data-testid="stSidebar"] * { color: #e0e6f0 !important; }

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

    /* Stock card */
    .stock-card {
        background: #ffffff;
        border: 1px solid #e0e4ea;
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        transition: box-shadow 0.3s ease;
    }
    .stock-card:hover {
        box-shadow: 0 6px 20px rgba(0,0,0,0.1);
    }

    .stock-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        border-bottom: 2px solid #f0f1f3;
        padding-bottom: 12px;
    }
    .stock-name {
        font-size: 1.35rem;
        font-weight: 700;
        color: #1a1f36;
    }
    .stock-id {
        font-size: 0.9rem;
        color: #636EFA;
        font-weight: 600;
        margin-left: 8px;
    }
    .stock-signal-up {
        background: #ecfdf5;
        color: #059669;
        font-weight: 700;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.9rem;
    }
    .stock-signal-flat {
        background: #fef3c7;
        color: #92400e;
        font-weight: 700;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.9rem;
    }
    .stock-signal-down {
        background: #fef2f2;
        color: #dc2626;
        font-weight: 700;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.9rem;
    }

    .metric-row {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin: 12px 0;
    }
    .metric-box {
        background: linear-gradient(135deg, #f8f9fc 0%, #f0f2f8 100%);
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 10px 14px;
        text-align: center;
        min-width: 90px;
        flex: 1;
    }
    .metric-box.up {
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        border-color: #6ee7b7;
    }
    .metric-box.down {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border-color: #fca5a5;
    }
    .metric-val {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1a1f36;
    }
    .metric-label {
        font-size: 0.7rem;
        color: #6b7280;
        margin-top: 4px;
    }

    /* Risk banner */
    .risk-banner {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-left: 5px solid #f59e0b;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 24px;
    }
    .risk-banner strong { color: #92400e; }

    /* Info panels */
    .info-panel {
        background: #f8fafc;
        border-left: 4px solid #636EFA;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.9rem;
    }

    .beginner-guide {
        background: linear-gradient(135deg, #e0e7ff 0%, #f3f4f6 100%);
        border-radius: 10px;
        padding: 14px 16px;
        margin: 12px 0;
        border-left: 4px solid #4f46e5;
    }

    /* Cost calculator */
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

    .cost-breakdown {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 14px;
        margin: 12px 0;
    }

    /* Table styling */
    .comparison-table {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# ===== Data Loading Functions =====
@st.cache_data
def load_all_data():
    """載入所有需要的資料"""
    base = Path(__file__).parent.parent.parent

    # Feature store
    fs = pd.read_parquet(base / "outputs" / "feature_store.parquet")

    # Companies
    companies = pd.read_parquet(base / "選用資料集" / "parquet" / "companies.parquet")

    # Stock prices (for price chart)
    prices = pd.read_parquet(base / "選用資料集" / "parquet" / "stock_prices.parquet")

    # Income statement (for fundamentals)
    income = pd.read_parquet(base / "選用資料集" / "parquet" / "income_stmt.parquet")

    # Phase 2 report
    report_dir = base / "outputs" / "reports"
    reports = sorted(report_dir.glob("phase2_report_*.json"), reverse=True)
    report = {}
    if reports:
        with open(reports[0], "r", encoding="utf-8") as f:
            report = json.load(f)

    return fs, companies, prices, income, report


@st.cache_data
def get_recommendations(fs, companies, horizon=20, n_top=10):
    """
    從 feature store 中取得最新一期有標籤的推薦股票。

    策略邏輯：
    - 選出 label_{horizon} == 1 (UP) 的股票
    - 按 forward return 排序取前 N 名
    - 合併公司名稱和基本面資訊
    """
    label_col = f"label_{horizon}"
    ret_col = f"fwd_ret_{horizon}"

    # 找到最新有標籤的日期
    valid = fs[fs[label_col].notna()]
    if valid.empty:
        return pd.DataFrame(), None

    latest_date = valid["trade_date"].max()
    snap = valid[valid["trade_date"] == latest_date].copy()

    # UP 股票
    up_stocks = snap[snap[label_col] == 1.0].copy()

    if up_stocks.empty:
        # 退而求其次：FLAT 中取 forward return 最高者
        up_stocks = snap[snap[label_col] == 0.0].copy()

    if up_stocks.empty:
        return pd.DataFrame(), latest_date

    # 排序
    up_stocks = up_stocks.sort_values(ret_col, ascending=False).head(n_top)

    # 合併公司名
    up_stocks = up_stocks.merge(companies, on="company_id", how="left")

    return up_stocks, latest_date


@st.cache_data
def get_price_history(prices, company_id, n_days=120):
    """取得某公司近 N 日收盤價，計算 MA20 和 RSI"""
    cp = prices[prices["company_id"] == str(company_id)].copy()
    cp["trade_date"] = pd.to_datetime(cp["trade_date"])
    cp = cp.sort_values("trade_date").tail(n_days)

    if cp.empty:
        return cp

    # Calculate MA20
    cp["ma20"] = cp["closing_price"].rolling(window=20, min_periods=1).mean()

    # Calculate RSI-14
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
def get_company_fundamentals(fs, income, company_id, trade_date):
    """取得某公司最新一季的基本面指標 + 特徵儲存裡的技術/估值指標"""
    result = {
        "eps": None,
        "gross_margin": None,
        "operating_margin": None,
        "net_margin": None,
        "revenue_yoy": None,
        "pe_ratio": None,
        "risk_level": "中等",
        "rsi": None,
        "fiscal_year": None,
        "fiscal_quarter": None,
    }

    # 從 income statement 取得財報指標
    ci = income[income["company_id"] == str(company_id)].copy()
    if not ci.empty:
        ci = ci.sort_values(["fiscal_year", "fiscal_quarter"])
        latest = ci.iloc[-1]

        result["fiscal_year"] = int(latest.get("fiscal_year", 0))
        result["fiscal_quarter"] = int(latest.get("fiscal_quarter", 0))
        result["eps"] = latest.get("eps")

        # 計算利潤率
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

        # YoY
        prev_q = ci[
            (ci["fiscal_year"] == latest["fiscal_year"] - 1) &
            (ci["fiscal_quarter"] == latest["fiscal_quarter"])
        ]
        if not prev_q.empty:
            prev_rev = prev_q.iloc[0].get("revenue")
            if pd.notna(prev_rev) and prev_rev != 0 and pd.notna(rev):
                result["revenue_yoy"] = (rev - prev_rev) / abs(prev_rev)

    # 從 feature store 取得 P/E 和風險指標
    fs_rec = fs[
        (fs["company_id"] == str(company_id)) &
        (fs["trade_date"] == trade_date)
    ]
    if not fs_rec.empty:
        rec = fs_rec.iloc[0]
        result["pe_ratio"] = rec.get("val_pe")

        # 風險等級 (基於 drawdown)
        drawdown = rec.get("risk_drawdown")
        if pd.notna(drawdown):
            if drawdown > 0.3:
                result["risk_level"] = "高"
            elif drawdown > 0.15:
                result["risk_level"] = "中等"
            else:
                result["risk_level"] = "低"

        # RSI
        result["rsi"] = rec.get("trend_rsi_14")

    return result


def get_risk_color(risk_level):
    """根據風險等級返回顏色"""
    if risk_level == "低":
        return "#059669"
    elif risk_level == "中等":
        return "#f59e0b"
    else:
        return "#dc2626"


# ===== Load Data =====
fs, companies, prices, income, report = load_all_data()


# ===== Sidebar =====
st.sidebar.markdown("### 🌱 智慧選股看板")
st.sidebar.divider()

horizon = st.sidebar.radio(
    "預測週期",
    options=[20, 5],
    format_func=lambda x: f"D+{x}（{'約一個月' if x == 20 else '約一週'}）",
    index=0,
    help="D+20 = 預測未來 20 個交易日的股價方向；D+5 = 預測未來 5 個交易日"
)

n_display = st.sidebar.slider("顯示推薦數量", 3, 10, 5)

st.sidebar.divider()
st.sidebar.markdown("""
**標籤說明**

🟢 **看漲 (UP)** — 模型預測未來漲幅 > 5%

🟡 **盤整 (FLAT)** — 預測漲跌幅在 ±5% 內

🔴 **看跌 (DOWN)** — 預測跌幅 > 5%
""")

st.sidebar.divider()
st.sidebar.markdown("""
**交易成本參考**

- 買進手續費：0.1425%
- 賣出手續費：0.1425%
- 證交稅（賣出）：0.3%
- 券商折扣後：手續費通常打 2.8 折

最低單筆手續費：20 元
""")

if st.sidebar.button("🏠 回到首頁", use_container_width=True):
    st.switch_page("app.py")


# ===== Main Content =====

# Risk disclaimer banner
st.markdown("""
<div class="risk-banner">
    <strong>⚠️ 重要投資提醒</strong><br>
    以下推薦基於歷史資料的機器學習分析結果，<strong>不構成投資建議</strong>。股市有風險，請根據自身情況審慎決策，切勿盲目跟單。
    過去績效不代表未來報酬。本系統為學術研究用途。
</div>
""", unsafe_allow_html=True)

st.markdown(f"# 🌱 智慧選股看板 — D+{horizon} 精選推薦")

# Get recommendations
recs, rec_date = get_recommendations(fs, companies, horizon=horizon, n_top=n_display)

if rec_date:
    st.caption(f"📅 資料基準日：{rec_date.strftime('%Y-%m-%d')}（最新一期有完整標籤的交易日）")
else:
    st.warning("目前沒有可用的推薦資料")
    st.stop()

if recs.empty:
    st.info(f"在 D+{horizon} 週期中，目前沒有被分類為「看漲」的股票。")
    st.stop()


# ===== Market Overview KPIs =====
st.markdown("### 📊 本期市場概況")

latest_snap = fs[fs["trade_date"] == rec_date]
label_col = f"label_{horizon}"
total_stocks = len(latest_snap)
up_count = (latest_snap[label_col] == 1.0).sum()
flat_count = (latest_snap[label_col] == 0.0).sum()
down_count = (latest_snap[label_col] == -1.0).sum()
avg_ret = recs[f"fwd_ret_{horizon}"].mean()

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("分析股票數", f"{total_stocks:,}")
with k2:
    st.metric("🟢 看漲", f"{up_count}", delta=f"{up_count/total_stocks*100:.1f}%")
with k3:
    st.metric("🟡 盤整", f"{flat_count}", delta=f"{flat_count/total_stocks*100:.1f}%")
with k4:
    st.metric("🔴 看跌", f"{down_count}", delta=f"{down_count/total_stocks*100:.1f}%")
with k5:
    st.metric("推薦股平均報酬", f"{avg_ret:+.1%}")

st.divider()


# ===== Recommended Stocks - Main Section =====
st.markdown(f"### 🏆 精選推薦 Top {len(recs)}")
st.caption("以下股票由模型從近 2,000 檔上市櫃股票中篩選而出，按預測報酬排序。")

for idx, (_, stock) in enumerate(recs.iterrows()):
    cid = str(stock["company_id"])
    name = stock.get("short_name", cid)
    full_name = stock.get("company_name", "")
    price = stock.get("closing_price", 0)
    fwd_ret = stock.get(f"fwd_ret_{horizon}", 0)
    label_val = stock.get(label_col, 0)

    # Signal tag
    if label_val == 1.0:
        signal_html = '<span class="stock-signal-up">🟢 看漲</span>'
    elif label_val == 0.0:
        signal_html = '<span class="stock-signal-flat">🟡 盤整</span>'
    else:
        signal_html = '<span class="stock-signal-down">🔴 看跌</span>'

    # Card header
    st.markdown(f"""
<div class="stock-card">
    <div class="stock-header">
        <div>
            <span class="stock-name">{name}</span>
            <span class="stock-id">{cid}</span>
        </div>
        {signal_html}
    </div>
</div>
""", unsafe_allow_html=True)

    # Content in two columns
    col_chart, col_info = st.columns([6, 4])

    with col_chart:
        # Price chart with MA20 and RSI
        price_hist = get_price_history(prices, cid, n_days=120)
        if not price_hist.empty:
            # Create subplots: price chart + RSI
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.08,
                row_heights=[0.7, 0.3],
                subplot_titles=("近 120 日走勢", "RSI 動能指標")
            )

            # Price trace
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

            # MA20 trace
            fig.add_trace(go.Scatter(
                x=price_hist["trade_date"],
                y=price_hist["ma20"],
                mode="lines",
                line=dict(color="#f59e0b", width=1.5, dash="dash"),
                name="MA20（20日均線）",
                hovertemplate="MA20: $%{y:.2f}<extra></extra>",
            ), row=1, col=1)

            # Mark the current price
            fig.add_trace(go.Scatter(
                x=[price_hist["trade_date"].iloc[-1]],
                y=[price_hist["closing_price"].iloc[-1]],
                mode="markers",
                marker=dict(size=12, color="#636EFA", symbol="circle"),
                showlegend=False,
                hoverinfo="skip",
            ), row=1, col=1)

            # RSI trace
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

                # RSI reference lines
                fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5,
                             annotation_text="超買 (70)", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5,
                             annotation_text="超賣 (30)", row=2, col=1)

            fig.update_xaxes(title_text="", row=1, col=1)
            fig.update_xaxes(title_text="日期", row=2, col=1)
            fig.update_yaxes(title_text="股價 (元)", row=1, col=1)
            fig.update_yaxes(title_text="RSI", row=2, col=1)

            fig.update_layout(
                height=350,
                template="plotly_white",
                margin=dict(l=10, r=10, t=40, b=10),
                hovermode="x unified",
                showlegend=True,
                legend=dict(x=0.01, y=0.98)
            )
            st.plotly_chart(fig, use_container_width=True, key=f"price_{cid}_{horizon}")
        else:
            st.info("無價格資料")

    with col_info:
        # Company fundamentals
        fund = get_company_fundamentals(fs, income, cid, rec_date)

        st.markdown("**公司資訊**")
        if full_name:
            st.caption(f"全名：{full_name}")

        st.markdown(f"**📈 目前股價**：{price:.2f} 元")

        # Highlight prediction
        ret_color = "#059669" if fwd_ret >= 0 else "#dc2626"
        st.markdown(f"**🎯 預測報酬 (D+{horizon})**： <span style='color:{ret_color}; font-weight:bold; font-size:1.2em;'>{fwd_ret:+.1%}</span>", unsafe_allow_html=True)

        if fund.get("fiscal_year"):
            st.markdown(f"**最新財報**：{fund['fiscal_year']} 年 Q{fund['fiscal_quarter']}")

        # Metrics in a grid
        m1, m2 = st.columns(2)

        with m1:
            if fund.get("eps") is not None:
                st.markdown(f"""
<div class="metric-box">
    <div class="metric-label">每股盈餘 (EPS)</div>
    <div class="metric-val">${fund['eps']:.2f}</div>
</div>
""", unsafe_allow_html=True)
            if fund.get("gross_margin") is not None:
                st.markdown(f"""
<div class="metric-box">
    <div class="metric-label">毛利率</div>
    <div class="metric-val">{fund['gross_margin']:.1%}</div>
</div>
""", unsafe_allow_html=True)

        with m2:
            if fund.get("operating_margin") is not None:
                st.markdown(f"""
<div class="metric-box">
    <div class="metric-label">營業利益率</div>
    <div class="metric-val">{fund['operating_margin']:.1%}</div>
</div>
""", unsafe_allow_html=True)
            if fund.get("pe_ratio") is not None and fund['pe_ratio'] > 0:
                st.markdown(f"""
<div class="metric-box">
    <div class="metric-label">本益比 (P/E)</div>
    <div class="metric-val">{fund['pe_ratio']:.1f}x</div>
</div>
""", unsafe_allow_html=True)

        # Additional metrics
        m3, m4 = st.columns(2)

        with m3:
            if fund.get("revenue_yoy") is not None:
                yoy_val = fund['revenue_yoy']
                yoy_color = "up" if yoy_val >= 0 else "down"
                st.markdown(f"""
<div class="metric-box {yoy_color}">
    <div class="metric-label">營收年增率</div>
    <div class="metric-val">{yoy_val:+.1%}</div>
</div>
""", unsafe_allow_html=True)

        with m4:
            risk_color = get_risk_color(fund['risk_level'])
            st.markdown(f"""
<div class="metric-box" style="background: linear-gradient(135deg, rgba({risk_color.lstrip('#')}, 0.1) 0%, rgba({risk_color.lstrip('#')}, 0.05) 100%); border-color: {risk_color};">
    <div class="metric-label">風險等級</div>
    <div class="metric-val" style="color: {risk_color};">{fund['risk_level']}</div>
</div>
""", unsafe_allow_html=True)

        # RSI indicator
        if fund.get("rsi") is not None:
            rsi_val = fund['rsi']
            if rsi_val > 70:
                rsi_status = "超買"
                rsi_color = "#dc2626"
            elif rsi_val < 30:
                rsi_status = "超賣"
                rsi_color = "#059669"
            else:
                rsi_status = "正常"
                rsi_color = "#f59e0b"
            st.markdown(f"""
<div class="metric-box" style="background: linear-gradient(135deg, rgba({rsi_color.lstrip('#')}, 0.1) 0%, rgba({rsi_color.lstrip('#')}, 0.05) 100%); border-color: {rsi_color};">
    <div class="metric-label">RSI-14 ({rsi_status})</div>
    <div class="metric-val" style="color: {rsi_color};">{rsi_val:.0f}</div>
</div>
""", unsafe_allow_html=True)

        # Beginner interpretation
        st.divider()
        st.markdown("**🎓 新手解讀**")

        interp_parts = []

        if fund.get("eps") is not None:
            interp_parts.append(f"**EPS {fund['eps']:.2f}**：公司每股賺了 {fund['eps']:.2f} 元。數字越大代表公司獲利越好。")

        if fund.get("gross_margin") is not None:
            gm_pct = fund['gross_margin'] * 100
            if gm_pct > 40:
                gm_desc = "高獲利"
            elif gm_pct > 20:
                gm_desc = "中等獲利"
            else:
                gm_desc = "低獲利"
            interp_parts.append(f"**毛利率 {gm_pct:.1f}%**：{gm_desc}能力。說明公司商品有競爭力。")

        if fund.get("revenue_yoy") is not None:
            yoy_val = fund['revenue_yoy']
            if yoy_val > 0:
                yoy_desc = "成長中"
            else:
                yoy_desc = "衰退中"
            interp_parts.append(f"**營收年增率 {yoy_val:+.1%}**：跟去年同期比較，公司營收{yoy_desc}。")

        if fund.get("pe_ratio") is not None and fund['pe_ratio'] > 0:
            if fund['pe_ratio'] < 15:
                pe_desc = "便宜"
            elif fund['pe_ratio'] < 25:
                pe_desc = "合理"
            else:
                pe_desc = "昂貴"
            interp_parts.append(f"**本益比 {fund['pe_ratio']:.1f}x**：{pe_desc}的價格。越低越便宜，但要看公司成長性。")

        if fund['risk_level'] == "低":
            risk_desc = "股價波動較小，相對穩定。"
        elif fund['risk_level'] == "中等":
            risk_desc = "股價會有中度波動，屬正常。"
        else:
            risk_desc = "股價波動較大，較容易虧損。要設好停損。"
        interp_parts.append(f"**風險 {fund['risk_level']}**：{risk_desc}")

        if len(interp_parts) > 0:
            st.markdown(f"""
<div class="beginner-guide">
{chr(10).join(['• ' + part for part in interp_parts[:4]])}
</div>
""", unsafe_allow_html=True)

    if idx < len(recs) - 1:
        st.divider()


# ===== Comparison Table: D+5 vs D+20 =====
st.divider()
st.markdown("### 📊 各週期推薦前五名總覽")
st.caption("對比 D+5（約一週）與 D+20（約一個月）的推薦結果。")

comp_col1, comp_col2 = st.columns(2)

with comp_col1:
    st.markdown(f"**D+5 前 5 名**")
    recs_5, _ = get_recommendations(fs, companies, horizon=5, n_top=5)
    if not recs_5.empty:
        comp_df_5 = recs_5[["short_name", "company_id", "closing_price", "fwd_ret_5", "val_pe", "label_5"]].copy()
        comp_df_5.columns = ["股票", "代碼", "現價", "預測報酬", "P/E", "信號"]
        comp_df_5["信號"] = comp_df_5["信號"].apply(
            lambda x: "🟢 UP" if x == 1.0 else ("🟡 FLAT" if x == 0.0 else "🔴 DOWN")
        )
        comp_df_5["現價"] = comp_df_5["現價"].apply(lambda x: f"${x:.2f}")
        comp_df_5["預測報酬"] = comp_df_5["預測報酬"].apply(lambda x: f"{x:+.1%}")
        comp_df_5["P/E"] = comp_df_5["P/E"].apply(lambda x: f"{x:.1f}x" if pd.notna(x) and x > 0 else "N/A")
        st.dataframe(comp_df_5, use_container_width=True, hide_index=True)
    else:
        st.info("無 D+5 推薦資料")

with comp_col2:
    st.markdown(f"**D+20 前 5 名**")
    recs_20, _ = get_recommendations(fs, companies, horizon=20, n_top=5)
    if not recs_20.empty:
        comp_df_20 = recs_20[["short_name", "company_id", "closing_price", "fwd_ret_20", "val_pe", "label_20"]].copy()
        comp_df_20.columns = ["股票", "代碼", "現價", "預測報酬", "P/E", "信號"]
        comp_df_20["信號"] = comp_df_20["信號"].apply(
            lambda x: "🟢 UP" if x == 1.0 else ("🟡 FLAT" if x == 0.0 else "🔴 DOWN")
        )
        comp_df_20["現價"] = comp_df_20["現價"].apply(lambda x: f"${x:.2f}")
        comp_df_20["預測報酬"] = comp_df_20["預測報酬"].apply(lambda x: f"{x:+.1%}")
        comp_df_20["P/E"] = comp_df_20["P/E"].apply(lambda x: f"{x:.1f}x" if pd.notna(x) and x > 0 else "N/A")
        st.dataframe(comp_df_20, use_container_width=True, hide_index=True)
    else:
        st.info("無 D+20 推薦資料")


# ===== Enhanced Transaction Cost Calculator =====
st.divider()
st.markdown("### 🧮 交易成本試算器")
st.caption("輸入你想買入的價格與張數，系統幫你計算總成本與損益平衡點。")

calc_col1, calc_col2, calc_col3 = st.columns(3)

with calc_col1:
    calc_price = st.number_input("買入價格（元/股）", min_value=1.0, value=50.0, step=0.5)
with calc_col2:
    calc_shares = st.number_input("買入張數（1 張 = 1,000 股）", min_value=1, value=1, step=1)
with calc_col3:
    broker_discount = st.selectbox(
        "券商手續費折扣",
        options=[1.0, 0.6, 0.5, 0.38, 0.28],
        format_func=lambda x: f"{x*100:.0f}%（{'原價' if x == 1.0 else '打 ' + str(x*10) + ' 折'}）",
        index=3,
        help="多數網路券商提供 2.8~6 折的手續費優惠"
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

# KPI cards
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
    <div style="font-size:0.8rem; color:#5a6577;">總交易成本</div>
    <div class="cost-total">${total_cost:,.0f}</div>
    <div style="font-size:0.75rem; color:#9ca3af;">{cost_ratio:.2f}% 佔金額</div>
</div>
""", unsafe_allow_html=True)

# Cost breakdown and break-even analysis
col_breakdown, col_breakeven = st.columns([1, 1])

with col_breakdown:
    st.markdown("**成本分解**")
    # Pie chart
    fig_cost = go.Figure(data=[go.Pie(
        labels=["買進手續費", "賣出手續費", "證交稅"],
        values=[buy_fee, sell_fee, sell_tax],
        marker_colors=["#3b82f6", "#8b5cf6", "#ec4899"],
        textinfo="label+value",
        textfont_size=11,
    )])
    fig_cost.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(fig_cost, use_container_width=True)

with col_breakeven:
    st.markdown("**損益平衡點**")
    st.info(f"""
    **買進價格**：${calc_price:.2f}

    **損益平衡點**：${breakeven_price:.2f}

    **需要漲幅**：{breakeven_pct:+.2f}%

    💡 股票至少要漲到 **${breakeven_price:.2f}** 才能回本。
    """)

# Scenario comparison
st.markdown("**情境對比**")
scenarios = []
for discount_label, discount_val in [("原價 (100%)", 1.0), ("6 折", 0.6), ("2.8 折", 0.28)]:
    buy_f = max(buy_amount * 0.001425 * discount_val, 20)
    sell_f = max(buy_amount * 0.001425 * discount_val, 20)
    total_f = buy_f + sell_f + sell_tax
    cost_r = (total_f / buy_amount) * 100
    be_price = calc_price * (1 + cost_r / 100)
    be_pct = (be_price - calc_price) / calc_price * 100
    scenarios.append({
        "券商折扣": discount_label,
        "手續費": f"${buy_f + sell_f:,.0f}",
        "總成本": f"${total_f:,.0f}",
        "成本率": f"{cost_r:.2f}%",
        "損益平衡": f"${be_price:.2f}",
        "需漲幅": f"{be_pct:+.2f}%"
    })

scenario_df = pd.DataFrame(scenarios)
st.dataframe(scenario_df, use_container_width=True, hide_index=True)

st.markdown(f"""
> 💡 **成本提醒**：
> - 折扣越低（如 2.8 折），實際繳費越少，更快達到損益平衡
> - 短線頻繁交易會重複產生成本，建議選擇中長期持有策略
> - 預期報酬應至少 **2-3 倍於成本率**，才是值得的交易
""")


# ===== Market Distribution Charts =====
st.divider()
st.markdown("### 📈 市場信號分佈與報酬分析")

dist_col1, dist_col2 = st.columns([1, 1])

with dist_col1:
    # Pie chart
    fig_pie = go.Figure(data=[go.Pie(
        labels=["🟢 看漲 (UP)", "🟡 盤整 (FLAT)", "🔴 看跌 (DOWN)"],
        values=[int(up_count), int(flat_count), int(down_count)],
        marker_colors=["#059669", "#f59e0b", "#dc2626"],
        hole=0.4,
        textinfo="label+percent",
        textfont_size=11,
    )])
    fig_pie.update_layout(
        title=f"D+{horizon} 信號分佈（{rec_date.strftime('%Y-%m-%d')}）",
        height=350,
        showlegend=False,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with dist_col2:
    # Return distribution histogram
    ret_col = f"fwd_ret_{horizon}"
    valid_snap = latest_snap[latest_snap[ret_col].notna()]
    if not valid_snap.empty:
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=valid_snap[ret_col] * 100,
            nbinsx=50,
            marker_color="#636EFA",
            opacity=0.7,
            hovertemplate="報酬率: %{x:.1f}%<br>股票數: %{y}<extra></extra>",
            name="股票數"
        ))
        fig_hist.add_vline(x=0, line_dash="dash", line_color="red", line_width=2,
                          annotation_text="零軸", annotation_position="right")
        fig_hist.update_layout(
            title=f"D+{horizon} 報酬率分佈（所有股票）",
            xaxis_title="報酬率 (%)",
            yaxis_title="股票數量",
            height=350,
            template="plotly_white",
            margin=dict(l=20, r=20, t=50, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig_hist, use_container_width=True)


# ===== Investment Education =====
st.divider()
st.markdown("### 📚 新手投資小知識")

tip1, tip2, tip3 = st.columns(3)

with tip1:
    st.markdown("""
**🎯 什麼是基本面？**

基本面是指公司的實際經營狀況，包括：

- **EPS（每股盈餘）**：公司替每股股票賺了多少錢。越高越好，代表獲利能力強。

- **毛利率**：賣東西扣掉成本後的獲利比率，反映產品競爭力。毛利率高的公司通常有定價權。

- **營收年增率**：跟去年同期比較，公司營收是成長還是衰退。持續成長是好信號。

- **本益比 (P/E)**：股價除以每股盈餘。低本益比可能便宜，但也要檢查成長性。

有基本面撐著的公司，股價比較有底氣，風險較低。
""")

with tip2:
    st.markdown("""
**🛡️ 如何避免「被割韭菜」？**

重要的風險管理原則：

- **不要盲目跟單**：聽朋友推薦或看新聞就買，通常都是高點。了解公司在做什麼、為什麼漲跌再投資。

- **分散風險**：不要把所有資金壓在同一檔股票。即使是好公司，也應該分散配置。

- **設定停損**：預先決定虧損多少就賣出（例如 -10%）。不要怠惰或心存僥倖。

- **注意交易成本**：頻繁交易（短線）的成本會吃掉獲利。建議優先考慮中長期持有。

- **長期思維**：避免追高殺低。股市 3-5 年才能看出真正的成長。
""")

with tip3:
    st.markdown("""
**📊 本系統的預測原理**

本系統使用機器學習分析超過 2,000 檔股票：

**使用的因子（23 個）：**
- 技術面：價格趨勢、均線、RSI、動能、波動度
- 基本面：EPS、毛利率、營業利益率、營收成長
- 估值面：本益比 (P/E)
- 風險面：個股回撤、市場環境

模型用過去 5 年資料訓練，並經過嚴格的防過擬合測試。

**重要提醒**：過去績效不代表未來報酬。模型會犯錯，請務必自己做功課。
""")


# ===== Backtest Performance Summary =====
st.divider()
st.markdown("### 💰 策略回測績效摘要")
st.caption("以下是模型在歷史資料上的回測結果（折扣券商成本）。過去績效不代表未來報酬。")

results = report.get("results", {})
benchmark = results.get("benchmark", {})
bt_h = results.get(f"backtest_horizon_{horizon}", {})

bt_rows = []
for eng, bt_data in bt_h.items():
    disc = bt_data.get("cost_scenarios", {}).get("discount", {})
    if disc:
        bt_rows.append({
            "策略": f"{eng.upper()} D+{horizon}",
            "年化報酬": f"{disc.get('annualized_return', 0):+.1%}",
            "夏普比率": f"{disc.get('sharpe_ratio', 0):.2f}",
            "最大回撤": f"{disc.get('max_drawdown', 0):.1%}",
            "勝率": f"{disc.get('win_rate', 0):.0%}",
        })

if benchmark:
    bt_rows.append({
        "策略": "📊 大盤基準（等權）",
        "年化報酬": f"{benchmark.get('annualized_return', 0):+.1%}",
        "夏普比率": f"{benchmark.get('sharpe_ratio', 0):.2f}",
        "最大回撤": f"{benchmark.get('max_drawdown', 0):.1%}",
        "勝率": f"{benchmark.get('win_rate', 0):.0%}",
    })

if bt_rows:
    st.dataframe(pd.DataFrame(bt_rows), use_container_width=True, hide_index=True)
    st.markdown("""
    **指標解釋：**
    - **年化報酬**：平均每年的回報率。超過 10% 算不錯。
    - **夏普比率**：報酬相對風險的效率。越高越好，> 0.5 代表不錯。
    - **最大回撤**：策略歷史上最大的虧損幅度。越小越好。
    - **勝率**：有獲利的交易佔比。> 50% 就可以接受。
    """)


# ===== Footer =====
st.divider()
st.markdown("""
<div style="text-align:center; padding:20px 0; color:#9ca3af; font-size:0.82rem;">
    <strong>智慧選股看板</strong> &nbsp;|&nbsp; 台灣股市多因子預測系統 &nbsp;|&nbsp; 大數據與商業分析專案<br>
    <br>
    <span style="font-size:0.75rem;">
        ⚠️ 本系統僅供學術研究用途，不構成投資建議。<br>
        過去績效不代表未來報酬。投資前請自行研究，審慎決策。
    </span>
</div>
""", unsafe_allow_html=True)
