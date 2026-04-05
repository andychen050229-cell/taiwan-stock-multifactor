"""Shared utilities for all dashboard pages."""

import streamlit as st
import json
import pandas as pd
from pathlib import Path


def inject_custom_css():
    """Inject shared custom CSS for consistent styling across all pages."""
    st.markdown("""
    <style>
        /* KPI cards / Metrics */
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

        /* Section headers */
        .block-container h2 {
            border-left: 4px solid #636EFA;
            padding-left: 12px;
        }
        .block-container h3 {
            color: #1a1f36;
            margin-top: 20px;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1f36 0%, #232946 100%);
        }
        section[data-testid="stSidebar"] * {
            color: #e0e6f0 !important;
        }
        section[data-testid="stSidebar"] h3 {
            color: #ffffff !important;
        }
        section[data-testid="stSidebar"] a {
            color: #8892b0 !important;
            text-decoration: none;
        }
        section[data-testid="stSidebar"] a:hover {
            color: #e0e6f0 !important;
            text-decoration: underline;
        }

        /* Insight boxes */
        .insight-box {
            background: linear-gradient(135deg, #eef2ff 0%, #e0f2fe 100%);
            border-left: 4px solid #636EFA;
            border-radius: 0 8px 8px 0;
            padding: 14px 18px;
            margin: 10px 0;
            font-size: 0.9rem;
            color: #0c4a6e;
        }
        .insight-box strong { color: #1a1f36; }

        /* Warning box for alerts */
        .warning-box {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            border-radius: 0 8px 8px 0;
            padding: 14px 18px;
            margin: 10px 0;
            font-size: 0.9rem;
            color: #92400e;
        }
        .warning-box strong { color: #92400e; }

        /* Success box for positive messages */
        .success-box {
            background: #ecfdf5;
            border-left: 4px solid #10b981;
            border-radius: 0 8px 8px 0;
            padding: 14px 18px;
            margin: 10px 0;
            font-size: 0.9rem;
            color: #065f46;
        }
        .success-box strong { color: #065f46; }

        /* Responsive metric cards */
        .metric-card {
            background: #ffffff;
            border: 1px solid #dde1eb;
            border-radius: 12px;
            padding: 16px 20px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .metric-card-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #636EFA;
            margin: 8px 0;
        }
        .metric-card-label {
            font-size: 0.85rem;
            color: #5a6577;
            font-weight: 600;
        }

        /* Footer */
        .page-footer {
            text-align: center;
            padding: 10px 0;
            color: #9ca3af;
            font-size: 0.82rem;
            border-top: 1px solid #e0e4ea;
            margin-top: 30px;
        }

        /* Navigation links */
        .nav-link {
            display: inline-block;
            padding: 8px 12px;
            margin: 4px 0;
            border-radius: 6px;
            background: rgba(99, 110, 250, 0.1);
            color: #636EFA;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }
        .nav-link:hover {
            background: rgba(99, 110, 250, 0.2);
            color: #5156d4;
        }
        .nav-link.active {
            background: #636EFA;
            color: #ffffff;
        }
    </style>
    """, unsafe_allow_html=True)


def inject_advanced_sidebar(report_name: str = "", report: dict = None, current_page: str = ""):
    """
    Inject the shared sidebar for advanced dashboard pages with navigation.

    Args:
        report_name: Name of the current report (e.g., "phase2_report_...")
        report: Dictionary containing the report data with quality gates
        current_page: Current page identifier for active indicator (e.g., "model_metrics")
    """
    st.sidebar.markdown("### ⚙️ 量化分析工作台")
    if report_name:
        st.sidebar.caption(f"Report: `{report_name}`")

    if report:
        status_icon = "✅" if report.get("overall_status") == "PASS" else "⚠️"
        st.sidebar.caption(f"Status: {status_icon} {'ALL PASS' if report.get('overall_status') == 'PASS' else 'REVIEW NEEDED'}")

        # Quality gates
        gates = report.get("quality_gates", {})
        with st.sidebar.expander("🔒 Quality Gates", expanded=False):
            for gate, passed in gates.items():
                icon = "✅" if (passed is True or passed == "True") else "❌"
                st.write(f"{icon} {gate.replace('_', ' ').title()}")

    st.sidebar.divider()

    # Navigation links to all advanced pages
    st.sidebar.markdown("**📍 Navigation**")
    pages = [
        ("📊 Model Metrics", "pages/1_📊_Model_Metrics.py", "model_metrics"),
        ("📈 ICIR Analysis", "pages/2_📈_ICIR_Analysis.py", "icir_analysis"),
        ("💰 Backtest", "pages/3_💰_Backtest.py", "backtest"),
        ("🔬 Feature Analysis", "pages/4_🔬_Feature_Analysis.py", "feature_analysis"),
        ("🗃️ Data Explorer", "pages/5_🗃️_Data_Explorer.py", "data_explorer"),
    ]

    for page_label, page_path, page_id in pages:
        is_active = current_page == page_id
        if st.sidebar.button(page_label, use_container_width=True, key=f"nav_{page_id}"):
            st.switch_page(page_path)

    st.sidebar.divider()

    st.sidebar.markdown("**ℹ️ System Info**")
    st.sidebar.markdown(
        "**Tech Stack**\n\n"
        "LightGBM + XGBoost + Ensemble\n\n"
        "**Cross-Validation**\n\n"
        "Purged Walk-Forward (4 Folds)\n\n"
        "**Data Coverage**\n\n"
        "1,932 companies | 2023/3–2025/3"
    )
    st.sidebar.divider()

    if st.sidebar.button("🏠 回到首頁", use_container_width=True):
        st.switch_page("app.py")

    st.sidebar.caption("Built with Streamlit & Plotly")


@st.cache_data
def load_report():
    """Load the latest Phase 2 report JSON with caching.

    Tries multiple paths to handle both local and Streamlit Cloud deployments:
    1. Path(__file__).resolve().parent.parent / "outputs" / "reports"  (standard)
    2. Path.cwd() / "outputs" / "reports"  (fallback for Cloud)
    """
    # Try standard path first
    report_dir = Path(__file__).resolve().parent.parent / "outputs" / "reports"

    # Fallback to cwd-based path if standard path doesn't exist
    if not report_dir.exists():
        report_dir = Path.cwd() / "outputs" / "reports"

    reports = sorted(report_dir.glob("phase2_report_*.json"), reverse=True)
    if not reports:
        st.error("找不到 Phase 2 報告。請先執行 `python run_phase2.py`。")
        st.stop()
    with open(reports[0], "r", encoding="utf-8") as f:
        return json.load(f), reports[0].name


@st.cache_data
def load_feature_store():
    """Load the feature store parquet file with caching.

    Tries multiple paths to handle both local and Streamlit Cloud deployments:
    1. Path(__file__).resolve().parent.parent / "outputs" / "feature_store.parquet"
    2. Path.cwd() / "outputs" / "feature_store.parquet"
    3. Path(__file__).resolve().parent / "data" / (as fallback, may not exist on Cloud)

    Returns:
        pd.DataFrame: Feature store containing all engineered features
    """
    # Try standard path first
    feature_store_path = Path(__file__).resolve().parent.parent / "outputs" / "feature_store.parquet"

    # Fallback to cwd-based path if standard path doesn't exist
    if not feature_store_path.exists():
        feature_store_path = Path.cwd() / "outputs" / "feature_store.parquet"

    # Final fallback to dashboard/data directory (may not exist on Cloud)
    if not feature_store_path.exists():
        feature_store_path = Path(__file__).resolve().parent / "data" / "feature_store.parquet"

    if not feature_store_path.exists():
        st.error(f"Feature store not found in any expected location")
        st.stop()

    return pd.read_parquet(feature_store_path)


@st.cache_data
def load_companies():
    """Load the companies reference data parquet file with caching.

    Tries multiple paths to handle both local and Streamlit Cloud deployments:
    1. Path(__file__).resolve().parent / "data" / "companies.parquet"  (dashboard/data/)
    2. Path(__file__).resolve().parent.parent / "選用資料集" / "parquet" / "companies.parquet"  (standard)
    3. Path.cwd() / "選用資料集" / "parquet" / "companies.parquet"  (fallback)

    Returns:
        pd.DataFrame: Companies data containing stock codes, names, sectors, etc.
    """
    # Try dashboard/data first
    companies_path = Path(__file__).resolve().parent / "data" / "companies.parquet"

    # Standard path
    if not companies_path.exists():
        companies_path = Path(__file__).resolve().parent.parent / "選用資料集" / "parquet" / "companies.parquet"

    # Fallback to cwd
    if not companies_path.exists():
        companies_path = Path.cwd() / "選用資料集" / "parquet" / "companies.parquet"

    if not companies_path.exists():
        st.error(f"Companies data not found in any expected location")
        st.stop()

    return pd.read_parquet(companies_path)
