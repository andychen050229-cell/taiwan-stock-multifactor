"""Shared utilities for all dashboard pages."""

import streamlit as st
import json
from pathlib import Path


def inject_custom_css():
    """Inject shared custom CSS for consistent styling."""
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
        /* Section headers */
        .block-container h2 {
            border-left: 4px solid #636EFA;
            padding-left: 12px;
        }
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1f36 0%, #232946 100%);
        }
        section[data-testid="stSidebar"] * {
            color: #e0e6f0 !important;
        }
        /* Insight boxes */
        .insight-box {
            background: linear-gradient(135deg, #eef2ff 0%, #e0f2fe 100%);
            border-left: 4px solid #636EFA;
            border-radius: 0 8px 8px 0;
            padding: 14px 18px;
            margin: 10px 0;
            font-size: 0.9rem;
        }
        .insight-box strong { color: #1a1f36; }
        /* Footer */
        .page-footer {
            text-align: center;
            padding: 10px 0;
            color: #9ca3af;
            font-size: 0.82rem;
            border-top: 1px solid #e0e4ea;
            margin-top: 30px;
        }
    </style>
    """, unsafe_allow_html=True)


def inject_advanced_sidebar(report_name: str = "", report: dict = None):
    """Inject the shared sidebar for advanced dashboard pages."""
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
    st.sidebar.markdown(
        "**Tech Stack**\n\n"
        "LightGBM + XGBoost + Ensemble\n\n"
        "**Cross-Validation**\n\n"
        "Purged Walk-Forward (4 Folds)\n\n"
        "**Data Coverage**\n\n"
        "1,932 companies | 2023/3–2025/3"
    )
    st.sidebar.divider()

    if st.sidebar.button("🏠 回到首頁"):
        st.switch_page("app.py")

    st.sidebar.caption("Built with Streamlit & Plotly")


@st.cache_data
def load_report():
    """Load the latest Phase 2 report JSON."""
    report_dir = Path(__file__).parent.parent / "outputs" / "reports"
    reports = sorted(report_dir.glob("phase2_report_*.json"), reverse=True)
    if not reports:
        st.error("找不到 Phase 2 報告。請先執行 `python run_phase2.py`。")
        st.stop()
    with open(reports[0], "r", encoding="utf-8") as f:
        return json.load(f), reports[0].name
