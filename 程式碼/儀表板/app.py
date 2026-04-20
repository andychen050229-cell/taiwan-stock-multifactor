"""
股票預測系統 · Multi-Factor Navigation Router
Streamlit st.navigation API (v1.36+) powered navigation.

⚠️ Absolute paths required:
   Streamlit Cloud uses `dashboard/app.py` (the shim) as its *main script*;
   when the shim exec()s this file, st.Page() resolves relative paths against
   the shim's directory, NOT this file's directory. Absolute paths via
   __file__ work identically on local dev and Cloud.
"""
from pathlib import Path
import importlib.util
import streamlit as st

# ===== Path anchors =====
HERE = Path(__file__).resolve().parent           # 程式碼/儀表板
PAGES = HERE / "pages"

def P(name: str) -> str:
    """Build absolute path string for a page file inside pages/."""
    return str(PAGES / name)

# ===== Page Config (MUST be before st.navigation) =====
# initial_sidebar_state="expanded" is set, but Streamlit Cloud's /~/+/ embed
# path suppresses sidebar regardless unless embed_options=show_sidebar_nav is
# in the URL. We bootstrap that via a tiny client-side redirect (below).
st.set_page_config(
    page_title="股票預測系統 · Multi-Factor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Force sidebar visibility in Streamlit Cloud /~/+/ embed mode =====
# Without ?embed_options=show_sidebar_nav, Streamlit Cloud's wrapper iframe
# hides sidebar nav + st.sidebar.markdown content entirely (tested 2026-04-20).
# This one-shot JS redirect adds the param and reloads the iframe URL.
st.markdown("""<script>
(function(){
  try {
    var qs = new URLSearchParams(window.location.search);
    var opts = (qs.get('embed_options') || '').toLowerCase();
    if (opts.indexOf('show_sidebar_nav') === -1) {
      var newOpts = opts ? (opts + ',show_sidebar_nav') : 'show_sidebar_nav';
      qs.set('embed_options', newOpts);
      var newUrl = window.location.pathname + '?' + qs.toString() + window.location.hash;
      window.location.replace(newUrl);
    }
  } catch(e) { /* noop */ }
})();
</script>""", unsafe_allow_html=True)

# ===== Load utils (brand + health injectors) =====
_utils_spec = importlib.util.spec_from_file_location("dashboard_utils_app", str(HERE / "utils.py"))
_utils = importlib.util.module_from_spec(_utils_spec)
_utils_spec.loader.exec_module(_utils)

# ===== Define Pages with st.Page (absolute paths, Cloud-safe) =====
home       = st.Page(P("home.py"),                       title="情境主控台",    icon="🧭", default=True)
interpret  = st.Page(P("0_🌱_投資解讀面板.py"),          title="投資觀察台",    icon="🌱")
data       = st.Page(P("5_🗃️_Data_Explorer.py"),        title="企業體檢",      icon="🧬")
icir       = st.Page(P("2_📈_ICIR_Analysis.py"),         title="信號穩定性",    icon="📈")
text       = st.Page(P("9_📝_Text_Analysis.py"),         title="影響鏈情緒",    icon="📝")
model      = st.Page(P("1_📊_Model_Metrics.py"),         title="模型績效",      icon="📊")
feature    = st.Page(P("4_🔬_Feature_Analysis.py"),      title="特徵工程",      icon="🔬")
backtest   = st.Page(P("3_💰_Backtest.py"),              title="策略回測",      icon="💰")
phase6     = st.Page(P("A_🔭_Phase6_深度驗證.py"),       title="Phase 6 深度",  icon="🔭")
governance = st.Page(P("6_🛡️_Model_Governance.py"),     title="模型治理",      icon="🛡️")
signal     = st.Page(P("7_📡_Signal_Monitor.py"),        title="信號監控",      icon="📡")
extended   = st.Page(P("8_🎯_Extended_Analytics.py"),    title="擴充分析",      icon="🧩")

# ===== Navigation Structure (Claude-Design later-version: 總覽/個股研究/量化引擎/治理監控) =====
# NOTE: st.navigation() must run BEFORE any st.sidebar.* call — otherwise the
# sidebar DOM never materialises on Streamlit Cloud (tested 2026-04-20).
# Visual order (品牌 + 系統健康度 at TOP, nav below) is achieved via CSS flex
# ordering on [data-testid="stSidebarContent"] children (see CSS block below).
pg = st.navigation({
    "總覽":      [home, interpret],
    "個股研究":  [data, icir, text],
    "量化引擎":  [model, feature, backtest, phase6],
    "治理監控":  [governance, signal, extended],
})

# ===== Sidebar — Brand + System Health INJECTED AFTER navigation =====
# Call-order places them below nav in the DOM, but CSS flex `order`
# re-orders them visually ABOVE the nav list (top-of-sidebar eye-catcher).
_utils.inject_sidebar_brand()
_utils.inject_sidebar_health(
    gates_passed=9,
    total_gates=9,
    dataset="2023/03–2025/03",
    samples="948,976",
    features="91 / 1,623",
    dsr="12.12",
    last_verified="2026-04-20 14:24",
)

# ===== Global Dark Sidebar CSS — 股票預測系統 brand ================
st.markdown("""<style>
    /* ================================================================= */
    /*  Dark "tech-data" sidebar — 股票預測系統 brand                    */
    /* ================================================================= */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a1420 0%, #121c2b 55%, #0f1a28 100%) !important;
        border-right: 1px solid rgba(6,182,212,0.08) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        background: transparent !important;
        padding-top: 0 !important;
        display: flex !important;
        flex-direction: column !important;
    }
    /* Visual re-ordering: brand + syshealth TOP, nav BOTTOM —
       DOM order is determined by call-order in app.py (nav first, then injections),
       but CSS flex `order` overrides this for visual rendering. */
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
        order: 10 !important;  /* navigation list: pushed after markdown injections */
    }
    /* All markdown injections (brand, syshealth, etc) appear before nav */
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] > [data-testid="stElementContainer"] {
        order: 1 !important;
    }
    /* More specific: brand first (order 1), syshealth second (order 2) */
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] > [data-testid="stElementContainer"]:has(.gl-brand) {
        order: 1 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] > [data-testid="stElementContainer"]:has(.gl-syshealth) {
        order: 2 !important;
    }
    /* Subtle tech grid behind sidebar */
    section[data-testid="stSidebar"]::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image:
            linear-gradient(rgba(6,182,212,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(6,182,212,0.03) 1px, transparent 1px);
        background-size: 26px 26px;
        pointer-events: none;
        opacity: 0.5;
    }
    /* Sidebar group-heading (Claude-design + 財報狗 style — softer for Chinese) */
    /* Streamlit v1.36+ uses <header data-testid="stNavSectionHeader"> for dict-keyed groups */
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] {
        padding: 18px 14px 8px 14px !important;
        margin-top: 10px !important;
        border-top: 1px solid rgba(255,255,255,0.06) !important;
        position: relative;
    }
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"]:first-of-type {
        border-top: none !important;
        margin-top: 2px !important;
        padding-top: 14px !important;
    }
    /* Cyan accent bar before each group title */
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"]::before {
        content: "";
        position: absolute;
        left: 14px;
        top: 22px;
        width: 3px;
        height: 10px;
        border-radius: 2px;
        background: linear-gradient(180deg, #06b6d4, #2563eb);
        box-shadow: 0 0 6px rgba(6,182,212,0.5);
    }
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"]:first-of-type::before {
        top: 18px;
    }
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] span,
    section[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] span {
        color: #9fb6cc !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.08em !important;
        padding-left: 10px !important;
        font-family: 'Inter', 'Noto Sans TC', 'Microsoft JhengHei', sans-serif !important;
    }
    /* Nav list container spacing */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] {
        padding: 2px 8px 6px 8px !important;
    }
    /* Nav links — item style */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {
        color: #b4ccdf !important;
        border-radius: 8px !important;
        margin: 1px 0 !important;
        padding: 8px 12px !important;
        transition: all 0.2s ease;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        position: relative;
        border: 1px solid transparent !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] span {
        color: #cce4f1 !important;
        font-family: 'Inter', -apple-system, 'Microsoft JhengHei', sans-serif !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {
        background: rgba(6,182,212,0.08) !important;
        border-color: rgba(6,182,212,0.15) !important;
        color: #e8f7fc !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover span {
        color: #e8f7fc !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {
        background: linear-gradient(90deg, rgba(6,182,212,0.18), rgba(37,99,235,0.08)) !important;
        border-color: rgba(6,182,212,0.35) !important;
        color: #e8f7fc !important;
        box-shadow: inset 3px 0 0 #06b6d4;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] span {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"]::after {
        content: "";
        position: absolute;
        right: 10px; top: 50%;
        transform: translateY(-50%);
        width: 6px; height: 6px;
        border-radius: 50%;
        background: #06b6d4;
        box-shadow: 0 0 8px rgba(6,182,212,0.7);
    }
    /* Default text colour inside sidebar */
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] li,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] a {
        color: #b4ccdf !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #e8f7fc !important;
    }
    /* Selectbox dropdown (popover) — dark mode */
    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [data-baseweb="popover"] [data-baseweb="menu"],
    [data-baseweb="popover"] ul,
    div[data-baseweb="popover"] {
        background: #0f1a28 !important;
        background-color: #0f1a28 !important;
        border: 1px solid rgba(6,182,212,0.2) !important;
        border-radius: 8px !important;
    }
    [data-baseweb="popover"] li,
    [data-baseweb="popover"] [role="option"],
    div[data-baseweb="popover"] li {
        color: #cce4f1 !important;
        background: transparent !important;
    }
    [data-baseweb="popover"] li:hover,
    [data-baseweb="popover"] [role="option"]:hover,
    div[data-baseweb="popover"] li:hover {
        background: rgba(6,182,212,0.15) !important;
        color: #ffffff !important;
    }
    [data-baseweb="popover"] li[aria-selected="true"],
    [data-baseweb="popover"] [role="option"][aria-selected="true"],
    div[data-baseweb="popover"] li[aria-selected="true"] {
        background: rgba(6,182,212,0.25) !important;
        color: #ffffff !important;
    }
    /* Selectbox trigger in sidebar (black text for readability) */
    section[data-testid="stSidebar"] [data-baseweb="select"] {
        background: rgba(255,255,255,0.85) !important;
        border: 1px solid rgba(6,182,212,0.25) !important;
        border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] *,
    section[data-testid="stSidebar"] [data-baseweb="select"] span,
    section[data-testid="stSidebar"] [data-baseweb="select"] div,
    [data-baseweb="select"] [class*="singleValue"],
    [data-baseweb="select"] [class*="ValueContainer"] span {
        color: #0f172a !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] svg {
        fill: #0f172a !important;
        color: #0f172a !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] input {
        caret-color: transparent !important;
        user-select: none !important;
    }
    /* Hide default Streamlit menu/footer */
    #MainMenu { visibility: hidden; }
    footer   { visibility: hidden; }
</style>""", unsafe_allow_html=True)

# ===== Run the selected page =====
pg.run()
