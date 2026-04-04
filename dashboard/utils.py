"""Shared utilities for all dashboard pages."""

import streamlit as st
import json
from pathlib import Path


def inject_custom_css():
    """Inject shared custom CSS for consistent styling."""
    st.markdown("""
    <style>
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
        .block-container h2 {
            border-left: 4px solid #636EFA;
            padding-left: 12px;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1f36 0%, #232946 100%);
        }
        section[data-testid="stSidebar"] * {
            color: #e0e6f0 !important;
        }
    </style>
    """, unsafe_allow_html=True)


@st.cache_data
def load_report():
    """Load the latest Phase 2 report JSON."""
    report_dir = Path(__file__).parent.parent / "outputs" / "reports"
    reports = sorted(report_dir.glob("phase2_report_*.json"), reverse=True)
    if not reports:
        st.error("找不到 Phase 2 報告。請先執行 `python run_phase2.py`。")
        st.stop()
    with open(reports[0], "r", encoding="utf-8") as f:
        return json.load(f)
