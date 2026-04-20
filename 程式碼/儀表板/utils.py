"""Shared utilities for all dashboard pages.

Design system: glint-light
  - Inspired by glint.trade terminal (tech/data-dense) but in light theme
  - Palette: off-white canvas, electric blue → violet gradient accents
  - Typography: Inter (sans) + JetBrains Mono (numeric)
  - Motion: subtle pulse on live indicators, hover glows on cards
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path


# ============================================================================
# Design tokens (single source of truth)
# ============================================================================
THEME = {
    # canvas
    "bg_primary":      "#fafbfc",
    "bg_surface":      "#ffffff",
    "bg_subtle":       "#f1f5f9",
    "bg_tint":         "#f8fafc",
    "bg_overlay":      "rgba(255,255,255,0.72)",
    # borders
    "border":          "#e2e8f0",
    "border_strong":   "#cbd5e1",
    # text
    "text_primary":    "#0f172a",
    "text_secondary":  "#475569",
    "text_tertiary":   "#94a3b8",
    # accents
    "blue":            "#2563eb",
    "violet":          "#7c3aed",
    "cyan":            "#06b6d4",
    "emerald":         "#10b981",
    "amber":           "#f59e0b",
    "rose":            "#f43f5e",
    "indigo":          "#4f46e5",
    # gradients
    "grad_primary":    "linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)",
    "grad_tech":       "linear-gradient(135deg, #06b6d4 0%, #2563eb 50%, #7c3aed 100%)",
    "grad_success":    "linear-gradient(135deg, #10b981 0%, #06b6d4 100%)",
    "grad_warm":       "linear-gradient(135deg, #f59e0b 0%, #f43f5e 100%)",
}


def inject_custom_css():
    """Inject the shared design system (glint-light tech theme).

    Applied globally to every dashboard page. Provides:
      - CSS variables (--gl-*) usable in any component
      - Refined typography via Google Fonts (Inter + JetBrains Mono)
      - Tech-grid background pattern
      - Glass panels, metric cards, data tables, code chips
      - Pulse / glow animations for live indicators
    """
    st.markdown(f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
    /* ================================================================= */
    /* 0. CSS variables                                                   */
    /* ================================================================= */
    :root {{
        --gl-bg:          {THEME["bg_primary"]};
        --gl-surface:     {THEME["bg_surface"]};
        --gl-subtle:      {THEME["bg_subtle"]};
        --gl-tint:        {THEME["bg_tint"]};
        --gl-overlay:     {THEME["bg_overlay"]};
        --gl-border:      {THEME["border"]};
        --gl-border-str:  {THEME["border_strong"]};
        --gl-text:        {THEME["text_primary"]};
        --gl-text-2:      {THEME["text_secondary"]};
        --gl-text-3:      {THEME["text_tertiary"]};
        --gl-blue:        {THEME["blue"]};
        --gl-violet:      {THEME["violet"]};
        --gl-cyan:        {THEME["cyan"]};
        --gl-emerald:     {THEME["emerald"]};
        --gl-amber:       {THEME["amber"]};
        --gl-rose:        {THEME["rose"]};
        --gl-indigo:      {THEME["indigo"]};
        --gl-grad-pri:    {THEME["grad_primary"]};
        --gl-grad-tech:   {THEME["grad_tech"]};
        --gl-grad-ok:     {THEME["grad_success"]};
        --gl-grad-warm:   {THEME["grad_warm"]};
        --gl-font-sans:   'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft JhengHei', 'PingFang TC', sans-serif;
        --gl-font-mono:   'JetBrains Mono', 'SF Mono', 'Consolas', monospace;
        --gl-shadow-sm:   0 1px 2px rgba(15,23,42,.04), 0 1px 3px rgba(15,23,42,.06);
        --gl-shadow-md:   0 4px 6px rgba(15,23,42,.04), 0 10px 15px rgba(15,23,42,.06);
        --gl-shadow-lg:   0 10px 15px rgba(15,23,42,.06), 0 20px 25px rgba(15,23,42,.08);
        --gl-shadow-glow: 0 0 0 1px rgba(37,99,235,.08), 0 8px 30px rgba(37,99,235,.12);
    }}
    /* ================================================================= */
    /* 1. Global canvas + tech-grid background                            */
    /* ================================================================= */
    .main, .block-container, [data-testid="stAppViewContainer"] {{
        background:
            radial-gradient(ellipse at top left, rgba(37,99,235,0.05) 0%, transparent 50%),
            radial-gradient(ellipse at top right, rgba(124,58,237,0.05) 0%, transparent 50%),
            linear-gradient(180deg, var(--gl-bg) 0%, #ffffff 400px);
        background-attachment: fixed;
    }}
    .block-container {{
        padding-top: 1.5rem !important;
        font-family: var(--gl-font-sans);
        color: var(--gl-text);
    }}
    /* Subtle tech grid overlay */
    .block-container::before {{
        content: "";
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image:
            linear-gradient(rgba(37,99,235,0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(37,99,235,0.025) 1px, transparent 1px);
        background-size: 40px 40px;
        pointer-events: none;
        z-index: 0;
    }}
    .block-container > * {{ position: relative; z-index: 1; }}
    /* ================================================================= */
    /* 2. Typography                                                       */
    /* ================================================================= */
    h1, h2, h3, h4, h5, h6 {{
        font-family: var(--gl-font-sans);
        color: var(--gl-text);
        letter-spacing: -0.01em;
    }}
    h1 {{ font-weight: 800; font-size: 2.1rem; letter-spacing: -0.03em; }}
    h2 {{ font-weight: 700; font-size: 1.5rem; }}
    h3 {{ font-weight: 600; font-size: 1.15rem; }}
    p, li, span, div {{ font-family: var(--gl-font-sans); }}
    code, kbd, pre, .gl-mono, [data-testid="stMetricValue"] {{
        font-family: var(--gl-font-mono) !important;
        font-feature-settings: "tnum" 1, "zero" 1;
    }}
    /* Section headers — left accent bar */
    .block-container h2 {{
        position: relative;
        padding-left: 16px;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }}
    .block-container h2::before {{
        content: "";
        position: absolute;
        left: 0; top: 4px; bottom: 4px;
        width: 4px;
        background: var(--gl-grad-pri);
        border-radius: 4px;
    }}
    /* ================================================================= */
    /* 3. Metric cards (stMetric) — tech-density style                    */
    /* ================================================================= */
    div[data-testid="stMetric"] {{
        background: var(--gl-surface);
        border: 1px solid var(--gl-border);
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: var(--gl-shadow-sm);
        transition: all .25s ease;
        position: relative;
        overflow: hidden;
    }}
    div[data-testid="stMetric"]::before {{
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: var(--gl-grad-tech);
        opacity: 0;
        transition: opacity .25s ease;
    }}
    div[data-testid="stMetric"]:hover {{
        border-color: rgba(37,99,235,0.35);
        box-shadow: var(--gl-shadow-glow);
        transform: translateY(-1px);
    }}
    div[data-testid="stMetric"]:hover::before {{ opacity: 1; }}
    div[data-testid="stMetric"] label,
    div[data-testid="stMetricLabel"] {{
        font-size: 0.76rem !important;
        color: var(--gl-text-3) !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}
    div[data-testid="stMetricValue"] {{
        color: var(--gl-text) !important;
        font-weight: 700 !important;
        font-size: 1.7rem !important;
        font-variant-numeric: tabular-nums;
    }}
    /* ================================================================= */
    /* 4. Tables / DataFrames                                              */
    /* ================================================================= */
    div[data-testid="stDataFrame"] {{
        border: 1px solid var(--gl-border);
        border-radius: 10px;
        overflow: hidden;
        box-shadow: var(--gl-shadow-sm);
    }}
    div[data-testid="stDataFrame"] thead tr th {{
        background: var(--gl-subtle) !important;
        color: var(--gl-text) !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}
    div[data-testid="stDataFrame"] tbody tr td {{
        font-family: var(--gl-font-mono);
        font-size: 0.86rem;
    }}
    /* ================================================================= */
    /* 5. Custom components — panels, boxes, chips, badges                */
    /* ================================================================= */
    /* Glass panel */
    .gl-panel {{
        background: var(--gl-surface);
        border: 1px solid var(--gl-border);
        border-radius: 14px;
        padding: 20px 24px;
        box-shadow: var(--gl-shadow-sm);
    }}
    .gl-panel-tint {{
        background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
    }}
    /* Insight / status boxes (left accent bar) */
    .insight-box, .gl-box-info {{
        background: linear-gradient(135deg, #eff6ff 0%, #f0f9ff 100%);
        border-left: 4px solid var(--gl-blue);
        border-radius: 0 10px 10px 0;
        padding: 14px 18px;
        margin: 12px 0;
        font-size: 0.9rem;
        color: #0c4a6e;
    }}
    .insight-box strong, .gl-box-info strong {{ color: #0c4a6e; }}
    .warning-box, .gl-box-warn {{
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border-left: 4px solid var(--gl-amber);
        border-radius: 0 10px 10px 0;
        padding: 14px 18px;
        margin: 12px 0;
        font-size: 0.9rem;
        color: #92400e;
    }}
    .warning-box strong, .gl-box-warn strong {{ color: #78350f; }}
    .success-box, .gl-box-ok {{
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        border-left: 4px solid var(--gl-emerald);
        border-radius: 0 10px 10px 0;
        padding: 14px 18px;
        margin: 12px 0;
        font-size: 0.9rem;
        color: #065f46;
    }}
    .success-box strong, .gl-box-ok strong {{ color: #064e3b; }}
    .gl-box-danger {{
        background: linear-gradient(135deg, #fff1f2 0%, #ffe4e6 100%);
        border-left: 4px solid var(--gl-rose);
        border-radius: 0 10px 10px 0;
        padding: 14px 18px;
        margin: 12px 0;
        font-size: 0.9rem;
        color: #9f1239;
    }}
    .gl-box-danger strong {{ color: #881337; }}
    /* KPI card (custom, not Streamlit metric) */
    .gl-kpi {{
        background: var(--gl-surface);
        border: 1px solid var(--gl-border);
        border-radius: 14px;
        padding: 18px 22px;
        box-shadow: var(--gl-shadow-sm);
        position: relative;
        overflow: hidden;
        min-height: 110px;
        transition: all .25s ease;
    }}
    .gl-kpi::after {{
        content: "";
        position: absolute;
        inset: 0;
        background: var(--gl-grad-tech);
        opacity: 0;
        mix-blend-mode: overlay;
        transition: opacity .25s ease;
    }}
    .gl-kpi:hover {{
        border-color: rgba(37,99,235,0.35);
        box-shadow: var(--gl-shadow-glow);
        transform: translateY(-2px);
    }}
    .gl-kpi:hover::after {{ opacity: 0.05; }}
    .gl-kpi-label {{
        font-size: 0.72rem;
        color: var(--gl-text-3);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
    }}
    .gl-kpi-value {{
        font-family: var(--gl-font-mono);
        font-size: 2rem;
        font-weight: 700;
        color: var(--gl-text);
        line-height: 1.1;
        font-variant-numeric: tabular-nums;
    }}
    .gl-kpi-delta {{
        font-family: var(--gl-font-mono);
        font-size: 0.82rem;
        font-weight: 600;
        margin-top: 6px;
    }}
    .gl-kpi-delta.up   {{ color: var(--gl-emerald); }}
    .gl-kpi-delta.down {{ color: var(--gl-rose); }}
    .gl-kpi-delta.neu  {{ color: var(--gl-text-3); }}
    .gl-kpi-sub {{
        font-size: 0.78rem;
        color: var(--gl-text-3);
        margin-top: 4px;
    }}
    .gl-kpi.accent-blue    {{ border-top: 3px solid var(--gl-blue); }}
    .gl-kpi.accent-violet  {{ border-top: 3px solid var(--gl-violet); }}
    .gl-kpi.accent-emerald {{ border-top: 3px solid var(--gl-emerald); }}
    .gl-kpi.accent-amber   {{ border-top: 3px solid var(--gl-amber); }}
    .gl-kpi.accent-rose    {{ border-top: 3px solid var(--gl-rose); }}
    .gl-kpi.accent-cyan    {{ border-top: 3px solid var(--gl-cyan); }}
    /* Chips / tags */
    .gl-chip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        background: var(--gl-subtle);
        color: var(--gl-text-2);
        border: 1px solid var(--gl-border);
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        font-family: var(--gl-font-mono);
        white-space: nowrap;
    }}
    .gl-chip.primary  {{ background: rgba(37,99,235,0.08);  color: var(--gl-blue);    border-color: rgba(37,99,235,0.2); }}
    .gl-chip.violet   {{ background: rgba(124,58,237,0.08); color: var(--gl-violet);  border-color: rgba(124,58,237,0.2); }}
    .gl-chip.ok       {{ background: rgba(16,185,129,0.08); color: var(--gl-emerald); border-color: rgba(16,185,129,0.2); }}
    .gl-chip.warn     {{ background: rgba(245,158,11,0.08); color: var(--gl-amber);   border-color: rgba(245,158,11,0.2); }}
    .gl-chip.danger   {{ background: rgba(244,63,94,0.08);  color: var(--gl-rose);    border-color: rgba(244,63,94,0.2); }}
    /* Live indicator (pulsing dot) */
    .gl-live {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 4px 10px;
        background: rgba(16,185,129,0.08);
        border: 1px solid rgba(16,185,129,0.25);
        border-radius: 999px;
        font-size: 0.74rem;
        font-weight: 700;
        color: var(--gl-emerald);
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }}
    .gl-live::before {{
        content: "";
        width: 8px; height: 8px;
        border-radius: 50%;
        background: var(--gl-emerald);
        box-shadow: 0 0 0 0 rgba(16,185,129,0.6);
        animation: gl-pulse 2s cubic-bezier(0.4,0,0.6,1) infinite;
    }}
    @keyframes gl-pulse {{
        0%   {{ box-shadow: 0 0 0 0 rgba(16,185,129,0.6); }}
        70%  {{ box-shadow: 0 0 0 8px rgba(16,185,129,0);   }}
        100% {{ box-shadow: 0 0 0 0 rgba(16,185,129,0);     }}
    }}
    /* Hero banner */
    .gl-hero {{
        position: relative;
        padding: 36px 40px;
        border-radius: 18px;
        background:
            radial-gradient(ellipse at 10% 10%, rgba(37,99,235,0.12) 0%, transparent 60%),
            radial-gradient(ellipse at 90% 90%, rgba(124,58,237,0.12) 0%, transparent 60%),
            linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid var(--gl-border);
        box-shadow: var(--gl-shadow-md);
        overflow: hidden;
        margin-bottom: 1.5rem;
    }}
    .gl-hero::before {{
        content: "";
        position: absolute;
        top: -50%; right: -20%;
        width: 400px; height: 400px;
        background: radial-gradient(circle, rgba(37,99,235,0.08), transparent 70%);
        filter: blur(40px);
        pointer-events: none;
    }}
    .gl-hero-eyebrow {{
        display: inline-block;
        padding: 4px 12px;
        background: rgba(37,99,235,0.08);
        color: var(--gl-blue);
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        border-radius: 999px;
        border: 1px solid rgba(37,99,235,0.18);
        margin-bottom: 16px;
        font-family: var(--gl-font-mono);
    }}
    .gl-hero-title {{
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1.1;
        margin: 0 0 10px 0;
        background: linear-gradient(135deg, #0f172a 0%, #2563eb 55%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    .gl-hero-subtitle {{
        font-size: 1.05rem;
        color: var(--gl-text-2);
        line-height: 1.6;
        max-width: 780px;
    }}
    /* Pillar badges (9-pillar taxonomy) */
    .gl-pillar {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        font-family: var(--gl-font-mono);
        font-size: 0.72rem;
        font-weight: 600;
        border-radius: 6px;
    }}
    .gl-pillar[data-p="trend"] {{ background: #dbeafe; color: #1e40af; }}
    .gl-pillar[data-p="fund"]  {{ background: #dcfce7; color: #166534; }}
    .gl-pillar[data-p="val"]   {{ background: #fae8ff; color: #86198f; }}
    .gl-pillar[data-p="event"] {{ background: #fef3c7; color: #92400e; }}
    .gl-pillar[data-p="risk"]  {{ background: #ffe4e6; color: #9f1239; }}
    .gl-pillar[data-p="chip"]  {{ background: #e0e7ff; color: #3730a3; }}
    .gl-pillar[data-p="ind"]   {{ background: #cffafe; color: #155e75; }}
    .gl-pillar[data-p="txt"]   {{ background: #f3e8ff; color: #6b21a8; }}
    .gl-pillar[data-p="sent"]  {{ background: #fce7f3; color: #9d174d; }}
    .gl-num {{
        font-family: var(--gl-font-mono);
        font-variant-numeric: tabular-nums;
    }}
    /* Tabs */
    button[data-baseweb="tab"] {{
        font-family: var(--gl-font-sans) !important;
        font-weight: 600 !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: var(--gl-blue) !important;
    }}
    [data-baseweb="tab-highlight"] {{
        background: var(--gl-grad-pri) !important;
        height: 3px !important;
    }}
    /* Buttons */
    .stButton > button {{
        border-radius: 10px !important;
        font-family: var(--gl-font-sans) !important;
        font-weight: 600 !important;
        border: 1px solid var(--gl-border) !important;
        transition: all .25s ease !important;
    }}
    .stButton > button[kind="primary"] {{
        background: var(--gl-grad-pri) !important;
        color: white !important;
        border: 1px solid transparent !important;
        box-shadow: 0 4px 14px rgba(37,99,235,0.25) !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        box-shadow: 0 6px 20px rgba(37,99,235,0.35) !important;
        transform: translateY(-1px);
    }}
    /* Footer */
    .page-footer, .gl-footer {{
        text-align: center;
        padding: 16px 0;
        color: var(--gl-text-3);
        font-size: 0.78rem;
        border-top: 1px solid var(--gl-border);
        margin-top: 2rem;
        font-family: var(--gl-font-sans);
    }}
    hr {{ border-color: var(--gl-border) !important; }}
    div[data-testid="stExpander"] {{
        border: 1px solid var(--gl-border) !important;
        border-radius: 10px !important;
        background: var(--gl-surface) !important;
    }}
    div[data-baseweb="notification"] {{
        border-radius: 10px !important;
        font-family: var(--gl-font-sans) !important;
    }}
    /* Legacy compatibility */
    .nav-link {{
        display: inline-block;
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 8px;
        background: rgba(37,99,235,.08);
        color: var(--gl-blue);
        text-decoration: none;
        font-weight: 600;
        font-size: .9rem;
        transition: all .25s ease;
    }}
    .nav-link:hover {{ background: rgba(37,99,235,.15); color: #1d4ed8; }}
    .nav-link.active {{ background: var(--gl-blue); color: #fff; }}
    .metric-card {{
        background: var(--gl-surface);
        border: 1px solid var(--gl-border);
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
        box-shadow: var(--gl-shadow-sm);
    }}
    .metric-card-value {{
        font-family: var(--gl-font-mono);
        font-size: 1.8rem; font-weight: 700; color: var(--gl-blue); margin: 8px 0;
    }}
    .metric-card-label {{ font-size: .84rem; color: var(--gl-text-2); font-weight: 600; }}
</style>
    """, unsafe_allow_html=True)


def render_kpi(label: str, value, delta=None, sub=None, accent="blue"):
    """Render a custom KPI tile with tech-mono value.

    Args:
        label: Small uppercase label.
        value: Main value (formatted string, e.g. "0.0153").
        delta: Optional tuple of (text, direction) where direction ∈ {"up","down","neu"}.
        sub: Optional sub-text (e.g. "vs baseline 0.26").
        accent: Top border colour. One of blue/violet/emerald/amber/rose/cyan.
    """
    delta_html = ""
    if delta:
        txt, direction = delta
        delta_html = f'<div class="gl-kpi-delta {direction}">{txt}</div>'
    sub_html = f'<div class="gl-kpi-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="gl-kpi accent-{accent}">
        <div class="gl-kpi-label">{label}</div>
        <div class="gl-kpi-value">{value}</div>
        {delta_html}
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def inject_advanced_sidebar(report_name: str = "", report: dict = None, current_page: str = ""):
    """Sidebar for advanced dashboard pages."""
    st.sidebar.markdown("### ⚙️ 量化分析工作台")
    if report_name:
        st.sidebar.caption(f"Report: `{report_name}`")

    if report:
        status_icon = "✅" if report.get("overall_status") == "PASS" else "⚠️"
        st.sidebar.caption(f"Status: {status_icon} {'ALL PASS' if report.get('overall_status') == 'PASS' else 'REVIEW NEEDED'}")
        gates = report.get("quality_gates", {})
        with st.sidebar.expander("🔒 Quality Gates", expanded=False):
            for gate, passed in gates.items():
                icon = "✅" if (passed is True or passed == "True") else "❌"
                st.write(f"{icon} {gate.replace('_', ' ').title()}")

    st.sidebar.divider()
    st.sidebar.markdown("**ℹ️ 系統資訊**")
    st.sidebar.caption(
        "🔧 LightGBM + XGBoost Ensemble\n\n"
        "📐 Purged Walk-Forward CV (4 Folds)\n\n"
        "📊 1,930 家上市櫃 | 2023/3–2025/3\n\n"
        "🎯 九支柱 1,623 → 91 特徵"
    )


# ============================================================================
# Data loaders
# ============================================================================
@st.cache_data
def load_report():
    """Load the latest Phase 2 report JSON with caching."""
    report_dir = Path(__file__).resolve().parent.parent / "outputs" / "reports"
    if not report_dir.exists():
        report_dir = Path.cwd() / "outputs" / "reports"
    reports = sorted(report_dir.glob("phase2_report_*.json"), reverse=True)
    if not reports:
        st.error("找不到 Phase 2 報告。請先執行 `python run_phase2.py`。")
        st.stop()
    with open(reports[0], "r", encoding="utf-8") as f:
        return json.load(f), reports[0].name


@st.cache_data
def load_phase3_report():
    """Load the latest Phase 3 report JSON with caching."""
    report_dir = Path(__file__).resolve().parent.parent / "outputs" / "reports"
    if not report_dir.exists():
        report_dir = Path.cwd() / "outputs" / "reports"
    reports = sorted(report_dir.glob("phase3_report_*.json"), reverse=True)
    if not reports:
        return None, None
    with open(reports[0], "r", encoding="utf-8") as f:
        return json.load(f), reports[0].name


def _project_outputs_dir():
    """Resolve the project-root outputs directory."""
    here = Path(__file__).resolve()
    for candidate in (
        here.parent.parent.parent / "outputs",
        here.parent.parent / "outputs",
        Path.cwd() / "outputs",
    ):
        if candidate.exists():
            return candidate
    return Path.cwd() / "outputs"


@st.cache_data
def load_phase3_analytics():
    """Load the latest Phase 3 extended analytics JSON."""
    report_dir = _project_outputs_dir() / "reports"
    reports = sorted(report_dir.glob("phase3_analytics_*.json"), reverse=True)
    if not reports:
        return None, None
    with open(reports[0], "r", encoding="utf-8") as f:
        return json.load(f), reports[0].name


@st.cache_data
def load_phase6_json(filename: str):
    """Load a Phase 6 JSON artefact (lopo / threshold_sweep / single_stock).

    Returns (data, filepath) or (None, None) if not found.
    """
    report_dir = _project_outputs_dir() / "reports"
    fp = report_dir / filename
    if not fp.exists():
        return None, None
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f), str(fp)


def figures_dir():
    """Return the figures output directory."""
    return _project_outputs_dir() / "figures"


@st.cache_data
def load_governance_json(filename):
    """Load a governance JSON file with caching."""
    gov_dir = Path(__file__).resolve().parent.parent / "outputs" / "governance"
    if not gov_dir.exists():
        gov_dir = Path.cwd() / "outputs" / "governance"
    fp = gov_dir / filename
    if fp.exists():
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


@st.cache_data
def load_feature_store():
    """Load the feature store parquet file with caching.

    Resolution order (first match wins):
      1. Single-file local dev: outputs/feature_store_final.parquet (272 MB, gitignored)
      2. Streamlit Cloud: outputs/fs_chunks/fs_YYYY_QN.parquet (9 quarterly chunks, ~35 MB each)
      3. Legacy fallbacks for older feature_store.parquet and dashboard/data/ copies.

    Cloud deployment cannot host the 272 MB single file (GitHub 100 MB / file hard limit),
    so we glob the quarterly chunks and concat — identical result, just reassembled at load.
    """
    here = Path(__file__).resolve().parent
    base_root = here.parent.parent  # project root

    # ---- 1. Single-file candidates (local dev) ---------------------
    single_candidates = [
        base_root / "outputs" / "feature_store_final.parquet",
        Path.cwd() / "outputs" / "feature_store_final.parquet",
        here.parent / "outputs" / "feature_store_final.parquet",
        base_root / "outputs" / "feature_store.parquet",
        Path.cwd() / "outputs" / "feature_store.parquet",
        here.parent / "outputs" / "feature_store.parquet",
        here / "data" / "feature_store_final.parquet",
        here / "data" / "feature_store.parquet",
    ]
    for fp in single_candidates:
        if fp.exists():
            return pd.read_parquet(fp)

    # ---- 2. Quarterly chunks (Streamlit Cloud) ---------------------
    chunk_dirs = [
        base_root / "outputs" / "fs_chunks",
        Path.cwd() / "outputs" / "fs_chunks",
        here.parent / "outputs" / "fs_chunks",
        here / "data" / "fs_chunks",
    ]
    for cdir in chunk_dirs:
        if cdir.exists():
            parts = sorted(cdir.glob("fs_*.parquet"))
            if parts:
                frames = [pd.read_parquet(p) for p in parts]
                return pd.concat(frames, ignore_index=True)

    st.error(
        "Feature store not found. Tried single-file (feature_store_final.parquet) "
        "and chunked layout (outputs/fs_chunks/fs_*.parquet). "
        "On Streamlit Cloud the chunked layout should be present — check repo state."
    )
    st.stop()


@st.cache_data
def load_companies():
    """Load the companies reference data parquet file with caching."""
    companies_path = Path(__file__).resolve().parent / "data" / "companies.parquet"
    if not companies_path.exists():
        companies_path = Path(__file__).resolve().parent.parent / "選用資料集" / "parquet" / "companies.parquet"
    if not companies_path.exists():
        companies_path = Path.cwd() / "選用資料集" / "parquet" / "companies.parquet"
    if not companies_path.exists():
        st.error("Companies data not found in any expected location")
        st.stop()
    return pd.read_parquet(companies_path)
