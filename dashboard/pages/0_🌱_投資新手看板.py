"""
投資新手看板 — 精選推薦 + 公司基本面 + 成本試算 + 風險提示

目標使用者：股市新手或小有經驗的散戶
提供資訊：
  - 每期精選推薦股票（D+5 / D+20）
  - 公司基本面摘要（EPS、毛利率、營收年增率）
  - 近期價格走勢圖
  - 交易成本試算（含手續費 + 證交稅）
  - 風險提示與注意事項
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
    page_title="投資新手看板 | 台灣股市多因子預測系統",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Custom CSS =====
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
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .stock-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .stock-name {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1a1f36;
    }
    .stock-id {
        font-size: 0.85rem;
        color: #636EFA;
        font-weight: 600;
    }
    .stock-signal-up {
        background: #ecfdf5;
        color: #059669;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
    }
    .stock-signal-flat {
        background: #fef3c7;
        color: #92400e;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
    }
    .stock-signal-down {
        background: #fef2f2;
        color: #dc2626;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
    }
    .metric-row {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        margin-top: 8px;
    }
    .metric-box {
        background: #f8f9fc;
        border-radius: 8px;
        padding: 8px 14px;
        text-align: center;
        min-width: 80px;
    }
    .metric-val {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1a1f36;
    }
    .metric-label {
        font-size: 0.72rem;
        color: #9ca3af;
    }

    /* Risk banner */
    .risk-banner {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-left: 4px solid #f59e0b;
        border-radius: 0 12px 12px 0;
        padding: 16px 20px;
        margin-bottom: 20px;
    }
    .risk-banner strong { color: #92400e; }

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
</style>
""", unsafe_allow_html=True)


# ===== Data Loading =====
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
def get_price_history(prices, company_id, n_days=90):
    """取得某公司近 N 日收盤價"""
    cp = prices[prices["company_id"] == str(company_id)].copy()
    cp["trade_date"] = pd.to_datetime(cp["trade_date"])
    cp = cp.sort_values("trade_date").tail(n_days)
    return cp


@st.cache_data
def get_company_fundamentals(income, company_id):
    """取得某公司最新一季的基本面指標"""
    ci = income[income["company_id"] == str(company_id)].copy()
    if ci.empty:
        return {}
    ci = ci.sort_values(["fiscal_year", "fiscal_quarter"])
    latest = ci.iloc[-1]

    result = {
        "fiscal_year": int(latest.get("fiscal_year", 0)),
        "fiscal_quarter": int(latest.get("fiscal_quarter", 0)),
        "eps": latest.get("eps"),
        "revenue": latest.get("revenue"),
        "operating_income": latest.get("operating_income"),
        "net_income": latest.get("net_income"),
    }

    # 計算簡易利潤率
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

    # YoY: 比較去年同期
    prev_q = ci[
        (ci["fiscal_year"] == latest["fiscal_year"] - 1) &
        (ci["fiscal_quarter"] == latest["fiscal_quarter"])
    ]
    if not prev_q.empty:
        prev_rev = prev_q.iloc[0].get("revenue")
        if pd.notna(prev_rev) and prev_rev != 0 and pd.notna(rev):
            result["revenue_yoy"] = (rev - prev_rev) / abs(prev_rev)

    return result


# ===== Load Data =====
fs, companies, prices, income, report = load_all_data()


# ===== Sidebar =====
st.sidebar.markdown("### 🌱 投資新手看板")
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
""")

if st.sidebar.button("🏠 回到首頁"):
    st.switch_page("app.py")


# ===== Main Content =====

# Risk disclaimer banner
st.markdown("""
<div class="risk-banner">
    <strong>⚠️ 投資提醒</strong>：以下推薦基於歷史資料的機器學習分析結果，
    <strong>不構成投資建議</strong>。股市有風險，請根據自身情況審慎決策，切勿盲目跟單。
    過去績效不代表未來報酬。
</div>
""", unsafe_allow_html=True)

st.markdown(f"# 🌱 投資新手看板 — D+{horizon} 精選推薦")

# Get recommendations
recs, rec_date = get_recommendations(fs, companies, horizon=horizon, n_top=n_display)

if rec_date:
    st.caption(f"資料基準日：{rec_date.strftime('%Y-%m-%d')}（最新一期有完整標籤的交易日）")
else:
    st.warning("目前沒有可用的推薦資料")
    st.stop()

if recs.empty:
    st.info(f"在 D+{horizon} 週期中，目前沒有被分類為「看漲」的股票。")
    st.stop()


# ===== Market Overview KPIs =====
st.markdown("### 📊 本期概況")

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


# ===== Recommended Stocks =====
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
    with st.container():
        st.markdown(f"""
<div class="stock-card">
    <div class="stock-header">
        <div>
            <span class="stock-name">{name}</span>
            <span class="stock-id">&nbsp; {cid}</span>
        </div>
        {signal_html}
    </div>
</div>
""", unsafe_allow_html=True)

    # Content in two columns
    col_chart, col_info = st.columns([3, 2])

    with col_chart:
        # Price chart
        price_hist = get_price_history(prices, cid, n_days=120)
        if not price_hist.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=price_hist["trade_date"],
                y=price_hist["closing_price"],
                mode="lines",
                line=dict(color="#636EFA", width=2),
                fill="tozeroy",
                fillcolor="rgba(99, 110, 250, 0.08)",
                hovertemplate="日期: %{x|%Y-%m-%d}<br>收盤價: $%{y:.2f}<extra></extra>",
            ))

            # Mark the current price
            fig.add_trace(go.Scatter(
                x=[price_hist["trade_date"].iloc[-1]],
                y=[price_hist["closing_price"].iloc[-1]],
                mode="markers",
                marker=dict(size=10, color="#636EFA"),
                showlegend=False,
                hoverinfo="skip",
            ))

            fig.update_layout(
                title=f"{name}（{cid}）近期走勢",
                height=250,
                template="plotly_white",
                xaxis_title="",
                yaxis_title="收盤價（元）",
                margin=dict(l=10, r=10, t=40, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, key=f"price_{cid}_{horizon}")
        else:
            st.info("無價格資料")

    with col_info:
        # Company fundamentals
        fund = get_company_fundamentals(income, cid)

        st.markdown(f"**公司資訊**")
        if full_name:
            st.caption(full_name)

        st.markdown(f"**目前股價**: ${price:.2f}")
        st.markdown(f"**預測期間報酬**: {fwd_ret:+.1%}")

        if fund:
            fy = fund.get("fiscal_year", "?")
            fq = fund.get("fiscal_quarter", "?")
            st.markdown(f"**最新財報**: {fy}年 Q{fq}")

            # Display fundamentals
            f1, f2 = st.columns(2)
            with f1:
                eps = fund.get("eps")
                if pd.notna(eps):
                    st.metric("每股盈餘 (EPS)", f"${eps:.2f}")
                gm = fund.get("gross_margin")
                if gm is not None:
                    st.metric("毛利率", f"{gm:.1%}")
            with f2:
                om = fund.get("operating_margin")
                if om is not None:
                    st.metric("營業利益率", f"{om:.1%}")
                yoy = fund.get("revenue_yoy")
                if yoy is not None:
                    delta_color = "normal" if yoy >= 0 else "inverse"
                    st.metric("營收年增率", f"{yoy:+.1%}")
        else:
            st.caption("暫無基本面資料")

    if idx < len(recs) - 1:
        st.divider()


# ===== Transaction Cost Calculator =====
st.divider()
st.markdown("### 🧮 交易成本試算器")
st.caption("輸入你想買入的價格與張數，系統幫你計算總成本（含手續費與證交稅）。")

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
buy_fee = max(buy_amount * 0.001425 * broker_discount, 20)  # 最低 20 元
sell_fee = max(buy_amount * 0.001425 * broker_discount, 20)
sell_tax = buy_amount * 0.003
total_cost = buy_fee + sell_fee + sell_tax
cost_ratio = total_cost / buy_amount * 100

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
    <div style="font-size:0.8rem; color:#5a6577;">買入手續費</div>
    <div class="cost-total" style="font-size:1.3rem;">${buy_fee:,.0f}</div>
    <div style="font-size:0.75rem; color:#9ca3af;">賣出手續費 ${sell_fee:,.0f}</div>
</div>
""", unsafe_allow_html=True)
with r3:
    st.markdown(f"""
<div class="cost-result">
    <div style="font-size:0.8rem; color:#5a6577;">證交稅（賣出時）</div>
    <div class="cost-total" style="font-size:1.3rem;">${sell_tax:,.0f}</div>
    <div style="font-size:0.75rem; color:#9ca3af;">稅率 0.3%</div>
</div>
""", unsafe_allow_html=True)
with r4:
    st.markdown(f"""
<div class="cost-result">
    <div style="font-size:0.8rem; color:#5a6577;">總交易成本</div>
    <div class="cost-total">${total_cost:,.0f}</div>
    <div style="font-size:0.75rem; color:#9ca3af;">佔金額 {cost_ratio:.2f}%</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
> 💡 **成本提醒**：以折扣 {broker_discount*100:.0f}% 計算，一買一賣的總交易成本約為成交金額的 **{cost_ratio:.2f}%**。
> 這意味著你的投資至少要獲利超過 {cost_ratio:.2f}% 才能真正賺到錢。短線交易成本累積更快，建議優先考慮中長期持有。
""")


# ===== Market Distribution Chart =====
st.divider()
st.markdown("### 📈 市場信號分佈")

dist_col1, dist_col2 = st.columns([1, 1])

with dist_col1:
    # Pie chart
    fig_pie = go.Figure(data=[go.Pie(
        labels=["🟢 看漲 (UP)", "🟡 盤整 (FLAT)", "🔴 看跌 (DOWN)"],
        values=[int(up_count), int(flat_count), int(down_count)],
        marker_colors=["#059669", "#f59e0b", "#dc2626"],
        hole=0.5,
        textinfo="label+percent",
        textfont_size=12,
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
        ))
        fig_hist.add_vline(x=0, line_dash="dash", line_color="red")
        fig_hist.update_layout(
            title=f"D+{horizon} 實際報酬率分佈",
            xaxis_title="報酬率 (%)",
            yaxis_title="股票數量",
            height=350,
            template="plotly_white",
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_hist, use_container_width=True)


# ===== Investment Tips =====
st.divider()
st.markdown("### 📚 新手投資小知識")

tip1, tip2, tip3 = st.columns(3)

with tip1:
    st.markdown("""
**🎯 什麼是基本面？**

基本面是指公司的實際經營狀況，包括：

- **EPS（每股盈餘）**：公司替每股股票賺了多少錢，越高越好
- **毛利率**：賣東西扣掉成本後的獲利比率，反映產品競爭力
- **營收年增率**：跟去年同期比較，公司營收是成長還是衰退

有基本面撐著的公司，股價比較有底氣。
""")

with tip2:
    st.markdown("""
**🛡️ 如何避免「被割韭菜」？**

幾個重要原則：

- **不要盲目跟單**：了解公司在做什麼再投資
- **分散風險**：不要把所有資金壓在同一檔股票
- **設定停損**：預先決定虧損多少就賣出（例如 -10%）
- **注意交易成本**：頻繁交易的成本會吃掉獲利
- **長期思維**：避免追高殺低，耐心等待合理價位
""")

with tip3:
    st.markdown("""
**📊 本系統的預測原理**

本系統使用機器學習分析：

- **技術面因子**：價格趨勢、均線、動能、波動度
- **基本面因子**：EPS、毛利率、營收成長
- **估值因子**：本益比 (P/E)
- **風險因子**：個股回撤、市場環境

綜合 23 個因子，預測未來股價漲跌方向。模型用過去資料訓練，並經過嚴格的防過擬合測試。
""")


# ===== Backtest Performance Summary =====
st.divider()
st.markdown("### 💰 策略回測績效摘要")
st.caption("以下是模型在歷史資料上的回測結果，採用折扣券商成本假設。過去績效不代表未來報酬。")

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
> 💡 **解讀方式**：年化報酬 > 大盤基準 代表模型策略勝過單純買大盤。
> 夏普比率 > 0.5 代表報酬相對風險的效率不錯。最大回撤是策略歷史上最大的虧損幅度。
""")


# ===== Footer =====
st.divider()
st.markdown("""
<div style="text-align:center; padding:10px 0; color:#9ca3af; font-size:0.82rem;">
    投資新手看板 &nbsp;|&nbsp; 台灣股市多因子預測系統 &nbsp;|&nbsp; 大數據與商業分析專案<br>
    ⚠️ 本系統僅供學術研究用途，不構成投資建議
</div>
""", unsafe_allow_html=True)
