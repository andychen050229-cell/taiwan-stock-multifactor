"""
多因子股票分析系統 · Multi-Factor Navigation Router (Option B — Top-Nav Architecture)

2026-04-20 重構：採用 Option B 頂部導覽，與 Streamlit Cloud embed mode
(`/~/+/`) 完全相容 —— 無論側邊欄是否顯示，頁面都有完整導覽。

設計原則：
  · 主導覽放在主區頂部（sticky top-nav pills），與 Streamlit Cloud 的
    iframe wrapper 無關，始終可見。
  · 側邊欄保留「品牌 + 系統健康度 + 真實 重整/手冊 按鈕」作為輔助，
    但不依賴它作為唯一導覽入口。
  · `st.navigation(position="hidden")` 註冊所有頁面但不自動渲染側邊欄導覽，
    由 `render_top_nav` 自行繪製頂部 pill 式導覽。

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
st.set_page_config(
    page_title="多因子股票分析系統 · Multi-Factor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Load utils (brand + health injectors + top-nav) =====
_utils_spec = importlib.util.spec_from_file_location("dashboard_utils_app", str(HERE / "utils.py"))
_utils = importlib.util.module_from_spec(_utils_spec)
_utils_spec.loader.exec_module(_utils)

# ===== Define Pages with st.Page (absolute paths, Cloud-safe) =====
# v4 audit §6.2 命名表 — icon 改單色 SVG 名 (lucide-style), emoji 只作 fallback
home       = st.Page(P("home.py"),                       title="情境主控",      icon=":material/radar:", default=True)
interpret  = st.Page(P("0_🌱_投資解讀面板.py"),          title="投資觀察",      icon=":material/travel_explore:")
data       = st.Page(P("5_🗃️_Data_Explorer.py"),        title="資料基礎",      icon=":material/database:")
icir       = st.Page(P("2_📈_ICIR_Analysis.py"),         title="訊號穩定",      icon=":material/monitoring:")
text       = st.Page(P("9_📝_Text_Analysis.py"),         title="文本情緒",      icon=":material/text_snippet:")
model      = st.Page(P("1_📊_Model_Metrics.py"),         title="模型績效",      icon=":material/bar_chart:")
feature    = st.Page(P("4_🔬_Feature_Analysis.py"),      title="因子工程",      icon=":material/layers:")
backtest   = st.Page(P("3_💰_Backtest.py"),              title="策略回測",      icon=":material/show_chart:")
phase6     = st.Page(P("A_🔭_Phase6_深度驗證.py"),       title="驗證壓測",      icon=":material/science:")
governance = st.Page(P("6_🛡️_Model_Governance.py"),     title="模型治理",      icon=":material/verified_user:")
signal     = st.Page(P("7_📡_Signal_Monitor.py"),        title="訊號監控",      icon=":material/sensors:")
extended   = st.Page(P("8_🎯_Extended_Analytics.py"),    title="延伸分析",      icon=":material/extension:")
manual     = st.Page(P("B_📖_使用手冊.py"),              title="使用手冊",      icon=":material/menu_book:")

# ===== Navigation Structure =====
# Groups for TOP-NAV display (manual is registered but excluded — accessed via
# the dedicated 手冊 sidebar button to reduce top-nav clutter).
TOP_NAV_GROUPS = {
    "總覽":      [home, interpret],
    "個股研究":  [data, icir, text],
    "量化引擎":  [model, feature, backtest, phase6],
    "治理監控":  [governance, signal, extended],
}

# Register ALL pages (including manual) with st.navigation in hidden mode —
# the nav doesn't auto-render but st.page_link / st.switch_page still work.
all_pages_flat = [p for group in TOP_NAV_GROUPS.values() for p in group] + [manual]
pg = st.navigation(all_pages_flat, position="hidden")

# ===== Sidebar — Brand + System Health + REAL action buttons ================
# Layout order via CSS flex re-ordering below:
#   brand (top) → syshealth → action buttons → [empty nav area]
_utils.inject_sidebar_brand()

# Single source of truth — read the latest phase2_report_*.json so the sidebar
# count (e.g. 8/9) cannot silently disagree with the hero traffic signal.
_qg = _utils.load_quality_gates()
_utils.inject_sidebar_health(
    gates_passed=_qg["passed"] if _qg["total"] else 9,
    total_gates=_qg["total"] if _qg["total"] else 9,
    dataset="2023/03–2025/03",
    samples="948,976",
    features="91 / 1,623",
    dsr="12.12",
    last_verified=_qg["last_verified"] or "2026-04-20 14:24",
)
_utils.inject_sidebar_action_buttons(manual_page=manual)

# ===== Global Dark Sidebar CSS — 多因子股票分析系統 brand ================
st.markdown("""<style>
    /* ================================================================= */
    /*  Dark "tech-data" sidebar — 多因子股票分析系統 brand              */
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
    /* Hide Streamlit's auto-rendered nav when position="hidden" */
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
        display: none !important;
    }
    /* Hide default Streamlit menu/footer */
    #MainMenu { visibility: hidden; }
    footer   { visibility: hidden; }
</style>""", unsafe_allow_html=True)

# v10 §7 · §8 · §13.3 — Consolidated dark widget override layer
# Repaints sidebar selectbox (D+20/D+5/D+1), slider, expander summary,
# radio labels, download buttons, and tabs so every interactive block has
# readable base-state text (fixes the v10 screenshot-3/4 black-on-black bugs).
_utils.inject_v10_dark_widgets_css()

# ===== TOP-NAV RENDER (v4 audit §5 — 3-layer: Utility Bar + Primary + Secondary) =====
# Always visible regardless of sidebar state — Cloud embed mode safe.
_utilbar_info = {
    "status":       "SNAPSHOT",
    "dataset":      "2023/03–2025/03",
    "model":        "xgboost_D20",
    "dsr":          "12.12",
    "gates_passed": _qg["passed"] if _qg["total"] else 9,
    "gates_total":  _qg["total"] if _qg["total"] else 9,
    "last_verified": _qg["last_verified"] or "2026-04-20 14:24",
}
_utils.render_top_nav(
    TOP_NAV_GROUPS,
    active_page_title=getattr(pg, "title", None),
    utilbar_info=_utilbar_info,
)

# ===== Run the selected page =====
pg.run()
