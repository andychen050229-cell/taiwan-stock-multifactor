"""
台灣股市多因子預測系統 — Landing Page（分流入口）
Taiwan Stock Multi-Factor Prediction System

兩條路徑：
  1. 投資新手看板 → 簡單易懂的選股推薦與公司基本面
  2. 量化分析工作台 → 進階模型指標、回測績效、特徵分析

啟動方式：
  streamlit run dashboard/app.py
"""

import streamlit as st
from pathlib import Path

# ===== Page Config =====
st.set_page_config(
    page_title="台灣股市多因子預測系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ===== Custom CSS =====
st.markdown("""
<style>
    /* Hide sidebar toggle on landing */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1f36 0%, #232946 100%);
    }
    section[data-testid="stSidebar"] * { color: #e0e6f0 !important; }

    /* Hero section */
    .hero-container {
        text-align: center;
        padding: 40px 20px 20px 20px;
    }
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #636EFA, #00CC96);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
        line-height: 1.2;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        color: #5a6577;
        margin-top: 0;
        margin-bottom: 30px;
    }

    /* Pathway cards */
    .path-card {
        background: #ffffff;
        border: 2px solid #e0e4ea;
        border-radius: 20px;
        padding: 36px 28px;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
        min-height: 360px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .path-card:hover {
        border-color: #636EFA;
        box-shadow: 0 8px 30px rgba(99, 110, 250, 0.15);
        transform: translateY(-4px);
    }
    .path-icon {
        font-size: 3.5rem;
        margin-bottom: 16px;
    }
    .path-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a1f36;
        margin-bottom: 8px;
    }
    .path-desc {
        font-size: 0.92rem;
        color: #5a6577;
        line-height: 1.6;
        margin-bottom: 20px;
    }
    .path-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: center;
    }
    .path-tag {
        background: #f0f2ff;
        color: #636EFA;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 20px;
    }
    .path-tag-green {
        background: #ecfdf5;
        color: #059669;
    }

    /* System stats */
    .stat-row {
        display: flex;
        justify-content: center;
        gap: 40px;
        margin: 30px 0 10px 0;
        flex-wrap: wrap;
    }
    .stat-item {
        text-align: center;
    }
    .stat-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #636EFA;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #9ca3af;
        margin-top: 2px;
    }

    /* Footer */
    .landing-footer {
        text-align: center;
        padding: 20px 0;
        color: #9ca3af;
        font-size: 0.82rem;
        border-top: 1px solid #e0e4ea;
        margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)


# ===== Hero Section =====
st.markdown("""
<div class="hero-container">
    <div class="hero-title">📈 台灣股市多因子預測系統</div>
    <div class="hero-subtitle">
        Taiwan Stock Multi-Factor Prediction System<br>
        運用機器學習，分析 1,932 家上市櫃公司的多維度因子，輔助投資決策
    </div>
</div>
""", unsafe_allow_html=True)

# ===== System Stats =====
st.markdown("""
<div class="stat-row">
    <div class="stat-item">
        <div class="stat-value">1,932</div>
        <div class="stat-label">上市櫃公司</div>
    </div>
    <div class="stat-item">
        <div class="stat-value">23</div>
        <div class="stat-label">分析因子</div>
    </div>
    <div class="stat-item">
        <div class="stat-value">3</div>
        <div class="stat-label">預測週期</div>
    </div>
    <div class="stat-item">
        <div class="stat-value">7/7</div>
        <div class="stat-label">品質門控通過</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("")
st.markdown("")

# ===== Two Pathway Cards =====
col_left, col_space, col_right = st.columns([5, 1, 5])

with col_left:
    st.markdown("""
<div class="path-card">
    <div class="path-icon">🌱</div>
    <div class="path-title">投資新手看板</div>
    <div class="path-desc">
        每期精選推薦股票，搭配公司基本面介紹、<br>
        交易成本試算、風險提示，讓你看得懂、買得安心。<br>
        不再盲目跟風，做有根據的投資。
    </div>
    <div class="path-tags">
        <span class="path-tag">精選推薦</span>
        <span class="path-tag">公司介紹</span>
        <span class="path-tag">成本試算</span>
        <span class="path-tag">風險提示</span>
    </div>
</div>
""", unsafe_allow_html=True)

    if st.button("🌱  進入新手看板", use_container_width=True, type="primary"):
        st.switch_page("pages/0_🌱_投資新手看板.py")

with col_right:
    st.markdown("""
<div class="path-card">
    <div class="path-icon">⚙️</div>
    <div class="path-title">量化分析工作台</div>
    <div class="path-desc">
        完整的模型指標、ICIR 信號分析、多情境回測績效、<br>
        特徵重要度與選擇過程、Walk-Forward CV 結構。<br>
        為量化研究者與進階投資人設計的專業儀表板。
    </div>
    <div class="path-tags">
        <span class="path-tag path-tag-green">模型指標</span>
        <span class="path-tag path-tag-green">ICIR 分析</span>
        <span class="path-tag path-tag-green">策略回測</span>
        <span class="path-tag path-tag-green">特徵工程</span>
    </div>
</div>
""", unsafe_allow_html=True)

    if st.button("⚙️  進入量化工作台", use_container_width=True, type="secondary"):
        st.switch_page("pages/1_📊_Model_Metrics.py")


# ===== Brief Methodology =====
st.markdown("")
st.divider()

st.markdown("#### 🔧 系統方法論")

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown("""
**五支柱特徵工程**

趨勢動能 · 基本面 · 估值 · 事件輿情 · 風險環境，共 43 候選因子經三階段篩選至 23 個。
""")

with m2:
    st.markdown("""
**嚴謹的交叉驗證**

Purged Walk-Forward CV（4 折），Expanding Window + 20 日 Embargo 杜絕前瞻偏差。
""")

with m3:
    st.markdown("""
**雙引擎 + 回測**

LightGBM / XGBoost 雙引擎加上等權 Ensemble，三種成本情境下的策略回測驗證。
""")


# ===== Disclaimer =====
st.markdown("")
st.markdown("""
<div style="background:#fef3c7; border-left:4px solid #f59e0b; padding:14px 18px; border-radius:0 8px 8px 0; font-size:0.85rem; color:#92400e;">
⚠️ <strong>免責聲明</strong>：本系統僅供學術研究與教學用途，不構成任何投資建議。
股市投資有風險，過去的回測績效不代表未來報酬。投資前請審慎評估自身風險承受能力。
</div>
""", unsafe_allow_html=True)


# ===== Footer =====
st.markdown("""
<div class="landing-footer">
    大數據與商業分析專案 &nbsp;|&nbsp; Built with Streamlit & Plotly &nbsp;|&nbsp;
    Data: FinMind API &nbsp;|&nbsp; Models: LightGBM + XGBoost
</div>
""", unsafe_allow_html=True)
