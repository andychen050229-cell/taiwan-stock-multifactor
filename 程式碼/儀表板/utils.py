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
    .gl-hero-orb {{
        position: absolute;
        top: -40%; left: -10%;
        width: 360px; height: 360px;
        background: radial-gradient(circle, rgba(124,58,237,0.08), transparent 70%);
        filter: blur(40px);
        pointer-events: none;
        z-index: 0;
    }}
    .gl-hero-accent {{
        background: linear-gradient(135deg, #2563eb 0%, #7c3aed 55%, #06b6d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
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
    /* ================================================================= */
    /* Design-system extensions — ported from Claude Design bundle       */
    /* ================================================================= */
    /* ---- Sticky topbar (breadcrumb + model chips + live clock) ---- */
    .gl-topbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 18px;
        background: rgba(255,255,255,.72);
        border: 1px solid var(--gl-border);
        border-radius: 12px;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        margin-bottom: 14px;
        box-shadow: var(--gl-shadow-sm);
        font-size: 0.82rem;
    }}
    .gl-topbar-l {{
        display: flex;
        align-items: center;
        gap: 10px;
        color: var(--gl-text-2);
    }}
    .gl-topbar-l .gl-slash {{ color: var(--gl-text-3); }}
    .gl-topbar-l .gl-crumb-cur {{ color: var(--gl-text); font-weight: 600; }}
    .gl-topbar-r {{
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: var(--gl-font-mono);
        font-size: 0.72rem;
        color: var(--gl-text-3);
    }}
    .gl-topbar-r .gl-sep {{ opacity: .4; }}
    .gl-topbar-clock {{
        font-family: var(--gl-font-mono);
        font-variant-numeric: tabular-nums;
        color: var(--gl-text-2);
        font-weight: 600;
    }}
    /* ---- AUC gauge SVG wrapper ---- */
    .gl-gauge {{
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 6px 0;
    }}
    .gl-gauge-val {{
        font-family: var(--gl-font-mono);
        font-variant-numeric: tabular-nums;
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--gl-text);
        line-height: 1;
        margin-top: 8px;
    }}
    .gl-gauge-lbl {{
        font-size: 0.72rem;
        color: var(--gl-text-3);
        margin-top: 4px;
        font-family: var(--gl-font-mono);
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }}
    /* ---- Segmented control (horizon switcher) ---- */
    .gl-seg-wrap {{
        display: inline-flex;
        background: var(--gl-subtle);
        border: 1px solid var(--gl-border);
        border-radius: 8px;
        padding: 3px;
        gap: 2px;
    }}
    .gl-seg-btn {{
        background: transparent;
        border: none;
        padding: 5px 14px;
        font-size: 0.72rem;
        font-family: var(--gl-font-mono);
        font-weight: 700;
        color: var(--gl-text-2);
        border-radius: 6px;
        letter-spacing: 0.04em;
    }}
    .gl-seg-btn.on {{
        background: var(--gl-surface);
        color: var(--gl-blue);
        box-shadow: var(--gl-shadow-sm);
    }}
    /* ---- Pillar progress bar (colored pill + bar + delta) ---- */
    .gl-pb {{
        display: flex;
        align-items: center;
        gap: 10px;
        font-family: var(--gl-font-mono);
        font-size: 0.72rem;
        padding: 3px 0;
    }}
    .gl-pb-pill {{
        padding: 3px 8px;
        border-radius: 5px;
        font-weight: 700;
        font-size: 0.66rem;
        width: 58px;
        text-align: center;
        flex-shrink: 0;
    }}
    .gl-pb-pill[data-p="trend"] {{ background: #dbeafe; color: #1e40af; }}
    .gl-pb-pill[data-p="fund"]  {{ background: #dcfce7; color: #166534; }}
    .gl-pb-pill[data-p="val"]   {{ background: #fae8ff; color: #86198f; }}
    .gl-pb-pill[data-p="event"] {{ background: #fef3c7; color: #92400e; }}
    .gl-pb-pill[data-p="risk"]  {{ background: #ffe4e6; color: #9f1239; }}
    .gl-pb-pill[data-p="chip"]  {{ background: #e0e7ff; color: #3730a3; }}
    .gl-pb-pill[data-p="ind"]   {{ background: #cffafe; color: #155e75; }}
    .gl-pb-pill[data-p="txt"]   {{ background: #f3e8ff; color: #6b21a8; }}
    .gl-pb-pill[data-p="sent"]  {{ background: #fce7f3; color: #9d174d; }}
    .gl-pb-bar-wrap {{
        flex: 1;
        height: 10px;
        background: var(--gl-subtle);
        border-radius: 4px;
        overflow: hidden;
        position: relative;
    }}
    .gl-pb-bar {{
        height: 100%;
        border-radius: 4px;
        transition: width .6s cubic-bezier(.34,1.56,.64,1);
    }}
    .gl-pb-num {{
        color: var(--gl-text);
        font-weight: 600;
        width: 46px;
        text-align: right;
        font-size: 0.72rem;
    }}
    .gl-pb-delta {{
        color: var(--gl-emerald);
        font-size: 0.66rem;
        width: 64px;
        text-align: right;
        font-weight: 600;
    }}
    .gl-pb-delta.down {{ color: var(--gl-rose); }}
    /* ---- Ticker tape (running marquee) ---- */
    .gl-ticker {{
        overflow: hidden;
        border-top: 1px solid var(--gl-border);
        border-bottom: 1px solid var(--gl-border);
        background: linear-gradient(90deg, var(--gl-tint), #fff 50%, var(--gl-tint));
        padding: 6px 0;
        white-space: nowrap;
        position: relative;
        border-radius: 10px;
        margin-bottom: 14px;
    }}
    .gl-ticker-track {{
        display: inline-block;
        animation: gl-ticker-scroll 60s linear infinite;
        font-family: var(--gl-font-mono);
        font-variant-numeric: tabular-nums;
        font-size: 0.78rem;
    }}
    .gl-ticker-track .gl-ticker-item {{
        display: inline-block;
        padding: 0 22px;
        color: var(--gl-text-2);
    }}
    .gl-ticker-track .gl-ticker-item.up   {{ color: var(--gl-emerald); }}
    .gl-ticker-track .gl-ticker-item.down {{ color: var(--gl-rose);    }}
    .gl-ticker-track .gl-ticker-item b    {{ color: var(--gl-text); font-weight: 700; margin-right: 6px; }}
    @keyframes gl-ticker-scroll {{
        0%   {{ transform: translateX(0); }}
        100% {{ transform: translateX(-50%); }}
    }}
    /* ---- Enhanced tab styling (mode switcher at top of home) ---- */
    div[data-baseweb="tab-list"] {{
        gap: 2px !important;
        border-bottom: 1px solid var(--gl-border) !important;
        background: transparent !important;
    }}
    button[data-baseweb="tab"] {{
        padding: 12px 20px !important;
        background: transparent !important;
        border-radius: 0 !important;
        border-bottom: 2px solid transparent !important;
        color: var(--gl-text-2) !important;
        font-family: var(--gl-font-sans) !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.005em !important;
    }}
    button[data-baseweb="tab"]:hover {{
        color: var(--gl-text) !important;
        background: rgba(37,99,235,.04) !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: var(--gl-blue) !important;
        border-bottom-color: var(--gl-blue) !important;
        background: transparent !important;
    }}
    /* ---- Path card variants (inv / qnt from Design) ---- */
    .path-card.path-inv {{ background: linear-gradient(135deg, #fff 0%, #fffbeb 100%); }}
    .path-card.path-inv::before {{ background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%) !important; }}
    .path-card.path-qnt {{ background: linear-gradient(135deg, #fff 0%, #f0f9ff 100%); }}
    /* ---- Compact stock table ---- */
    .gl-stk-tbl {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.82rem;
    }}
    .gl-stk-tbl th {{
        text-align: left;
        font-size: 0.66rem;
        color: var(--gl-text-3);
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 8px 10px;
        border-bottom: 1px solid var(--gl-border);
        background: var(--gl-tint);
        font-family: var(--gl-font-sans);
    }}
    .gl-stk-tbl td {{
        padding: 9px 10px;
        border-bottom: 1px solid var(--gl-border);
        font-family: var(--gl-font-mono);
        font-variant-numeric: tabular-nums;
        color: var(--gl-text);
        vertical-align: middle;
    }}
    .gl-stk-tbl tr:hover td {{ background: rgba(37,99,235,.03); }}
    .gl-stk-tbl .ticker {{ font-weight: 700; color: var(--gl-blue); }}
    .gl-stk-tbl .name-zh {{ font-family: var(--gl-font-sans); color: var(--gl-text); }}
    .gl-stk-tbl .ret-up {{ color: var(--gl-emerald); font-weight: 600; }}
    .gl-stk-tbl .ret-dn {{ color: var(--gl-rose); font-weight: 600; }}
    .gl-stk-tbl .ind-chip {{
        display: inline-block;
        padding: 1px 7px;
        background: var(--gl-subtle);
        color: var(--gl-text-2);
        border-radius: 4px;
        font-size: 0.68rem;
        font-family: var(--gl-font-sans);
        font-weight: 500;
    }}
    /* ---- Methodology card (span-4 layout helpers) ---- */
    .gl-grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
    .gl-grid-6 {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }}
    @media (max-width: 1200px) {{ .gl-grid-6 {{ grid-template-columns: repeat(3, 1fr); }} }}
    @media (max-width: 900px) {{ .gl-grid-3 {{ grid-template-columns: 1fr; }} .gl-grid-6 {{ grid-template-columns: repeat(2, 1fr); }} }}
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


# ============================================================================
# Design-system helpers — ported from Claude Design bundle
# ============================================================================
def render_topbar(crumb_left: str = "量化研究終端", crumb_current: str = "首頁",
                  chips: list = None, show_clock: bool = True):
    """Sticky top-bar with breadcrumb + model chips + live clock.

    Args:
        crumb_left: Left-side breadcrumb root (e.g. "量化研究終端").
        crumb_current: Right-side active crumb (e.g. "首頁", "模型績效").
        chips: Optional list of (label, variant) tuples. Variant ∈ {pri, vio, ok, warn, default}.
        show_clock: Render the JetBrains-mono clock on the right.
    """
    chips = chips or []
    chip_html = "".join(
        f'<span class="gl-chip {v}">{lbl}</span>' for lbl, v in chips
    )
    clock_html = ''
    if show_clock:
        clock_html = (
            '<span class="gl-chip" style="font-family: var(--gl-font-mono);" id="gl-clock">--:--:--</span>'
            '<script>(function(){var el=document.getElementById("gl-clock");'
            'if(!el)return;function t(){var d=new Date();'
            'el.textContent=String(d.getHours()).padStart(2,"0")+":"+'
            'String(d.getMinutes()).padStart(2,"0")+":"+'
            'String(d.getSeconds()).padStart(2,"0");}'
            't();setInterval(t,1000);})();</script>'
        )
    st.markdown(f"""
<div class="gl-topbar">
  <div class="gl-topbar-l">
    <span style="color:var(--gl-text-3);font-size:0.85rem;">{crumb_left}</span>
    <span style="color:var(--gl-text-3);">›</span>
    <span style="color:var(--gl-text-1);font-weight:600;font-size:0.9rem;">{crumb_current}</span>
  </div>
  <div class="gl-topbar-r">
    {chip_html}
    {clock_html}
  </div>
</div>
    """, unsafe_allow_html=True)


def render_auc_gauge(val: float, min_v: float = 0.5, max_v: float = 0.7,
                     label: str = "AUC · target ≥ 0.52", width: int = 260, height: int = 150):
    """SVG half-ring gauge for AUC / ratio metrics.

    Args:
        val: The measured value.
        min_v: Minimum of the arc (left end).
        max_v: Maximum of the arc (right end).
        label: Sub-label under the number.
        width/height: SVG dimensions.
    """
    import math
    cx, cy, r = width / 2, height - 20, min(width, height * 2) / 2 - 20
    clamped = max(min_v, min(max_v, val))
    t = (clamped - min_v) / (max_v - min_v)
    angle = math.pi * (1 - t)
    x2 = cx + r * math.cos(angle)
    y2 = cy - r * math.sin(angle)
    large_arc = 0
    path_full = f"M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r} {cy}"
    path_val = f"M {cx - r} {cy} A {r} {r} 0 {large_arc} 1 {x2} {y2}"
    # Tick marks at min, mid, max
    def tick(t_val):
        a = math.pi * (1 - t_val)
        x1 = cx + (r - 6) * math.cos(a)
        y1 = cy - (r - 6) * math.sin(a)
        x = cx + r * math.cos(a)
        y = cy - r * math.sin(a)
        return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="#cbd5e1" stroke-width="1.5"/>'
    ticks = "".join(tick(v) for v in [0, 0.5, 1])
    return f"""
<div class="gl-gauge-wrap">
  <svg class="gl-gauge" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
    <defs>
      <linearGradient id="ggrad-{int(val*10000)}" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#2563eb"/>
        <stop offset="60%" stop-color="#7c3aed"/>
        <stop offset="100%" stop-color="#06b6d4"/>
      </linearGradient>
    </defs>
    <path d="{path_full}" fill="none" stroke="#e2e8f0" stroke-width="10" stroke-linecap="round"/>
    <path d="{path_val}" fill="none" stroke="url(#ggrad-{int(val*10000)})" stroke-width="10" stroke-linecap="round"/>
    {ticks}
    <text x="{cx}" y="{cy - r * 0.4}" text-anchor="middle"
          font-family="JetBrains Mono, monospace" font-size="28" font-weight="700"
          fill="#0f172a">{val:.4f}</text>
    <text x="{cx - r}" y="{cy + 16}" text-anchor="middle"
          font-family="JetBrains Mono, monospace" font-size="10" fill="#64748b">{min_v:.2f}</text>
    <text x="{cx + r}" y="{cy + 16}" text-anchor="middle"
          font-family="JetBrains Mono, monospace" font-size="10" fill="#64748b">{max_v:.2f}</text>
  </svg>
  <div class="gl-gauge-lbl">{label}</div>
</div>
"""


def render_pillar_bar(pillar_key: str, label: str, feat_count: int, pct: float,
                      delta_bps: float = None) -> str:
    """Return HTML for a single pillar bar row.

    Args:
        pillar_key: One of trend/fund/val/event/risk/chip/ind/txt/sent.
        label: Chinese label (e.g. "技術面").
        feat_count: Feature count (shown on right).
        pct: Progress bar fill 0–100.
        delta_bps: Optional delta in basis points (e.g. +24 → "+24bps").
    """
    pct = max(0, min(100, pct))
    delta_html = ""
    if delta_bps is not None:
        sign = "+" if delta_bps >= 0 else ""
        cls = "up" if delta_bps >= 0 else "dn"
        delta_html = f'<span class="gl-pb-delta {cls}">{sign}{delta_bps:.1f}bps</span>'
    return f"""
<div class="gl-pb">
  <span class="gl-pb-pill" data-p="{pillar_key}">{label}</span>
  <div class="gl-pb-bar-wrap"><div class="gl-pb-bar" data-p="{pillar_key}" style="width:{pct:.1f}%"></div></div>
  <span class="gl-pb-num">{feat_count}</span>
  {delta_html}
</div>"""


def render_phase_timeline(current_phase: int = 6, phases: list = None):
    """Render Phase 1–6 chip row with the current phase highlighted.

    Args:
        current_phase: 1–6, which chip gets the ``cur`` styling.
        phases: Optional override list of dicts with keys {num, title, subtitle}.
    """
    phases = phases or [
        {"num": 1, "title": "資料清洗",       "subtitle": "Stage 1 Cleaning"},
        {"num": 2, "title": "因子建構",       "subtitle": "9 Pillars · 1,623"},
        {"num": 3, "title": "特徵篩選",       "subtitle": "Purged WF CV"},
        {"num": 4, "title": "模型訓練",       "subtitle": "LGBM + XGB"},
        {"num": 5, "title": "解釋與文本",     "subtitle": "SHAP · NLP"},
        {"num": 6, "title": "整合驗證",       "subtitle": "LOPO · DSR"},
    ]
    chips = []
    for p in phases:
        cur = " cur" if p["num"] == current_phase else ""
        chips.append(
            f'<div class="phase-chip{cur}">'
            f'<div style="font-size:.72rem;color:var(--gl-text-3);font-weight:600;letter-spacing:.06em;">PHASE {p["num"]}</div>'
            f'<div style="font-weight:700;font-size:.92rem;color:var(--gl-text-1);margin-top:2px;">{p["title"]}</div>'
            f'<div style="font-size:.76rem;color:var(--gl-text-3);font-family:var(--gl-font-mono);margin-top:2px;">{p["subtitle"]}</div>'
            f'</div>'
        )
    st.markdown(
        f'<div class="gl-grid-6" style="margin:14px 0;">{"".join(chips)}</div>',
        unsafe_allow_html=True,
    )


def render_ticker_tape(items: list):
    """Render a horizontal scrolling ticker tape (marquee).

    Args:
        items: List of dicts {ticker, name, value, direction} where direction ∈ {up, down, neu}.
    """
    html_parts = []
    # Duplicate list so the marquee can loop seamlessly
    for it in items + items:
        d = it.get("direction", "neu")
        html_parts.append(
            f'<span class="gl-ticker-item">'
            f'<span style="font-family:var(--gl-font-mono);font-weight:700;">{it["ticker"]}</span> '
            f'<span style="color:var(--gl-text-2);">{it["name"]}</span> '
            f'<span class="{d}" style="font-family:var(--gl-font-mono);font-weight:600;">{it["value"]}</span>'
            f'</span>'
        )
    st.markdown(
        f'<div class="gl-ticker"><div class="gl-ticker-track">{"".join(html_parts)}</div></div>',
        unsafe_allow_html=True,
    )


def render_horizon_segmented(options: list = None, current: str = "D+20", key_prefix: str = "seg"):
    """Visual segmented control (non-interactive display only — pair with st.radio for state).

    Args:
        options: list of horizon labels (e.g. ["D+1", "D+5", "D+20"]).
        current: Label currently highlighted.
    """
    options = options or ["D+1", "D+5", "D+20"]
    btns = "".join(
        f'<span class="gl-seg-btn{" on" if o == current else ""}">{o}</span>' for o in options
    )
    st.markdown(f'<div class="gl-seg-wrap">{btns}</div>', unsafe_allow_html=True)


def render_hero(eyebrow: str, title_html: str, meta_chips: list = None, subtitle: str = ""):
    """Hero block with gradient title + eyebrow + meta chips + blur orb.

    Args:
        eyebrow: Uppercase eyebrow text (letter-spaced).
        title_html: Hero title (may include <span class="gl-hero-accent"> for gradient highlight).
        meta_chips: Optional list of (label, variant) tuples.
        subtitle: Short Chinese subtitle under the title.
    """
    meta_chips = meta_chips or []
    chip_html = "".join(
        f'<span class="gl-chip {v}">{lbl}</span>' for lbl, v in meta_chips
    )
    subtitle_html = ""
    if subtitle:
        subtitle_html = (
            f'<div style="margin-top:14px;color:var(--gl-text-2);font-size:0.98rem;max-width:860px;">'
            f'{subtitle}</div>'
        )
    st.markdown(f"""
<div class="gl-hero">
  <div class="gl-hero-orb"></div>
  <span class="gl-hero-eyebrow">{eyebrow}</span>
  <div class="gl-hero-title">{title_html}</div>
  {subtitle_html}
  <div style="margin-top:18px;display:flex;gap:8px;flex-wrap:wrap;">{chip_html}</div>
</div>
    """, unsafe_allow_html=True)


def render_live_chip(text: str = "LIVE · 研究快照"):
    """Pulsing emerald dot chip for live-status indicators."""
    st.markdown(
        f'<span class="gl-live">{text}</span>',
        unsafe_allow_html=True,
    )


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
