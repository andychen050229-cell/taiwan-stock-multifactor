"""
台灣股市多因子預測系統 — Navigation Router
Streamlit st.navigation API (v1.36+) powered navigation.

⚠️ Absolute paths required:
   Streamlit Cloud uses `dashboard/app.py` (the shim) as its *main script*;
   when the shim exec()s this file, st.Page() resolves relative paths against
   the shim's directory, NOT this file's directory. Absolute paths via
   __file__ work identically on local dev and Cloud.
"""
from pathlib import Path
import streamlit as st

# ===== Path anchors =====
HERE = Path(__file__).resolve().parent           # 程式碼/儀表板
PAGES = HERE / "pages"

def P(name: str) -> str:
    """Build absolute path string for a page file inside pages/."""
    return str(PAGES / name)

# ===== Page Config (MUST be before st.navigation) =====
st.set_page_config(
    page_title="台灣股市多因子預測系統",
    page_icon="📈",
    layout="wide",
)

# ===== Define Pages with st.Page (absolute paths, Cloud-safe) =====
home = st.Page(P("home.py"), title="首頁", icon="🏠", default=True)
interpret = st.Page(P("0_🌱_投資解讀面板.py"), title="投資解讀面板", icon="🌱")
model = st.Page(P("1_📊_Model_Metrics.py"), title="模型績效", icon="📊")
icir = st.Page(P("2_📈_ICIR_Analysis.py"), title="ICIR 信號穩定性", icon="📈")
backtest = st.Page(P("3_💰_Backtest.py"), title="策略回測", icon="💰")
feature = st.Page(P("4_🔬_Feature_Analysis.py"), title="特徵工程分析", icon="🔬")
data = st.Page(P("5_🗃️_Data_Explorer.py"), title="資料品質總覽", icon="🗃️")
governance = st.Page(P("6_🛡️_Model_Governance.py"), title="模型治理", icon="🛡️")
signal = st.Page(P("7_📡_Signal_Monitor.py"), title="信號監控", icon="📡")
extended = st.Page(P("8_🎯_Extended_Analytics.py"), title="擴充分析", icon="🎯")
text = st.Page(P("9_📝_Text_Analysis.py"), title="文本分析", icon="📝")
phase6 = st.Page(P("A_🔭_Phase6_深度驗證.py"), title="Phase 6 深度驗證", icon="🔭")

# ===== Navigation Structure =====
pg = st.navigation({
    "": [home],
    "📖 投資解讀": [interpret],
    "🔬 量化研究工作台": [model, icir, backtest, feature, data, text],
    "🛡️ 模型治理與監控": [governance, signal, extended, phase6],
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

    /* ── Selectbox dropdown panel (the popover that floats) ── */
    /* Extra specificity for Streamlit Cloud light/dark theme compatibility */
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
    /* Selected option highlight */
    [data-baseweb="popover"] li[aria-selected="true"],
    [data-baseweb="popover"] [role="option"][aria-selected="true"],
    div[data-baseweb="popover"] li[aria-selected="true"] {
        background: rgba(99, 110, 250, 0.35) !important;
        background-color: rgba(99, 110, 250, 0.35) !important;
        color: #ffffff !important;
    }
    /* Selectbox trigger (the button you click) in sidebar — BLACK text */
    section[data-testid="stSidebar"] [data-baseweb="select"] {
        border: 1px solid rgba(0,0,0,0.2) !important;
        border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] *,
    section[data-testid="stSidebar"] [data-baseweb="select"] span,
    section[data-testid="stSidebar"] [data-baseweb="select"] div,
    [data-baseweb="select"] [class*="singleValue"],
    [data-baseweb="select"] [class*="ValueContainer"] span {
        color: #000000 !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] svg {
        fill: #000000 !important;
        color: #000000 !important;
    }
    /* Hide the text input / search inside selectbox (force dropdown-only) */
    section[data-testid="stSidebar"] [data-baseweb="select"] input {
        caret-color: transparent !important;
        user-select: none !important;
    }

    /* Hide default Streamlit footer and unnecessary UI */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>""", unsafe_allow_html=True)

# ===== Run the selected page =====
pg.run()
