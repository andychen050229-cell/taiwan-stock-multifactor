"""
台灣股市多因子預測系統 — Navigation Router
Streamlit st.navigation API (v1.36+) powered navigation.
"""
import streamlit as st

# ===== Page Config (MUST be before st.navigation) =====
st.set_page_config(
    page_title="台灣股市多因子預測系統",
    page_icon="📈",
    layout="wide",
)

# ===== Define Pages with st.Page =====
home = st.Page("pages/home.py", title="首頁", icon="🏠", default=True)
interpret = st.Page("pages/0_🌱_投資解讀面板.py", title="投資解讀面板", icon="🌱")
model = st.Page("pages/1_📊_Model_Metrics.py", title="模型績效", icon="📊")
icir = st.Page("pages/2_📈_ICIR_Analysis.py", title="ICIR 信號穩定性", icon="📈")
backtest = st.Page("pages/3_💰_Backtest.py", title="策略回測", icon="💰")
feature = st.Page("pages/4_🔬_Feature_Analysis.py", title="特徵工程分析", icon="🔬")
data = st.Page("pages/5_🗃️_Data_Explorer.py", title="資料品質總覽", icon="🗃️")

# ===== Navigation Structure =====
pg = st.navigation({
    "": [home],
    "📖 投資解讀": [interpret],
    "🔬 量化研究工作台": [model, icir, backtest, feature, data],
})

# ===== Global Dark Sidebar CSS =====
st.markdown("""<style>
    /* Dark professional sidebar — inspired by Bloomberg Terminal & 財報狗 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1419 0%, #1a2332 100%) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        background: transparent !important;
    }

    /* Nav section headers (group labels like "📖 投資解讀") */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] span {
        color: #8899aa !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* Nav links */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {
        color: #c8d6e5 !important;
        border-radius: 8px;
        margin: 2px 8px;
        padding: 8px 12px !important;
        transition: all 0.2s ease;
    }

    /* Hover state for nav links */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {
        background: rgba(99, 110, 250, 0.15) !important;
        color: #ffffff !important;
    }

    /* Active/selected nav link */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-selected="true"] {
        background: rgba(99, 110, 250, 0.25) !important;
        color: #ffffff !important;
        border-left: 3px solid #636EFA;
    }

    /* All text in sidebar */
    section[data-testid="stSidebar"] * {
        color: #c8d6e5 !important;
    }

    /* Sidebar headings */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }

    /* Hide default Streamlit footer and unnecessary UI */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>""", unsafe_allow_html=True)

# ===== Run the selected page =====
pg.run()
