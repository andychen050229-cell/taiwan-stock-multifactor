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
    /* CJK-aware line-break defaults — 避免中文在奇怪位置斷字 */
    p, li, .gl-panel, .gl-box-info, .gl-box-warn, .path-card, .path-desc,
    .mn-tile-body, .mn-tile-example, .mn-callout, .mn-flow-step-desc,
    .stMarkdown p, .stMarkdown li {{
        word-break: keep-all;          /* 中文不在字元中間斷 */
        overflow-wrap: break-word;
        line-break: strict;
        line-height: 1.78;             /* CJK 適度行高 */
    }}
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
    /* Tabs — minimal base (detailed rules appear later in CSS cascade,
       near st.tabs section — override font/weight/color there).            */
    button[data-baseweb="tab"] {{
        font-family: var(--gl-font-sans) !important;
        font-weight: 600 !important;
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
    /* Secondary / default buttons — dark-mode readable (fixes black-on-black bug) */
    .stButton > button:not([kind="primary"]) {{
        background: var(--gl-surface) !important;
        color: var(--gl-text) !important;
        border: 1px solid var(--gl-border) !important;
    }}
    .stButton > button:not([kind="primary"]):hover {{
        background: var(--gl-subtle) !important;
        border-color: var(--gl-blue) !important;
        color: var(--gl-text) !important;
        transform: translateY(-1px);
    }}
    .stButton > button:not([kind="primary"]) p,
    .stButton > button:not([kind="primary"]) span,
    .stButton > button:not([kind="primary"]) div {{
        color: var(--gl-text) !important;
    }}
    /* Download button — match secondary style */
    .stDownloadButton > button {{
        background: var(--gl-surface) !important;
        color: var(--gl-text) !important;
        border: 1px solid var(--gl-border) !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }}
    .stDownloadButton > button:hover {{
        background: var(--gl-subtle) !important;
        border-color: var(--gl-blue) !important;
        color: var(--gl-text) !important;
    }}
    .stDownloadButton > button p,
    .stDownloadButton > button span {{
        color: var(--gl-text) !important;
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
        /* Default background (fallback for unknown pillars) */
        background: linear-gradient(90deg, #6366f1 0%, #a78bfa 100%);
        box-shadow: 0 0 8px rgba(99,102,241,0.25);
    }}
    /* Per-pillar gradients — echo the pill colors but stronger saturation */
    .gl-pb-bar[data-p="trend"] {{ background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%); box-shadow: 0 0 8px rgba(59,130,246,0.3); }}
    .gl-pb-bar[data-p="fund"]  {{ background: linear-gradient(90deg, #10b981 0%, #34d399 100%); box-shadow: 0 0 8px rgba(16,185,129,0.3); }}
    .gl-pb-bar[data-p="val"]   {{ background: linear-gradient(90deg, #a855f7 0%, #c084fc 100%); box-shadow: 0 0 8px rgba(168,85,247,0.3); }}
    .gl-pb-bar[data-p="event"] {{ background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%); box-shadow: 0 0 8px rgba(245,158,11,0.3); }}
    .gl-pb-bar[data-p="risk"]  {{ background: linear-gradient(90deg, #f43f5e 0%, #fb7185 100%); box-shadow: 0 0 8px rgba(244,63,94,0.3); }}
    .gl-pb-bar[data-p="chip"]  {{ background: linear-gradient(90deg, #6366f1 0%, #818cf8 100%); box-shadow: 0 0 8px rgba(99,102,241,0.3); }}
    .gl-pb-bar[data-p="ind"]   {{ background: linear-gradient(90deg, #06b6d4 0%, #22d3ee 100%); box-shadow: 0 0 8px rgba(6,182,212,0.3); }}
    .gl-pb-bar[data-p="txt"]   {{ background: linear-gradient(90deg, #8b5cf6 0%, #a78bfa 100%); box-shadow: 0 0 8px rgba(139,92,246,0.3); }}
    .gl-pb-bar[data-p="sent"]  {{ background: linear-gradient(90deg, #ec4899 0%, #f472b6 100%); box-shadow: 0 0 8px rgba(236,72,153,0.3); }}
    .gl-pb:hover .gl-pb-bar {{ filter: brightness(1.12); }}
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
        gap: 4px !important;
        border-bottom: 1px solid rgba(6,182,212,0.18) !important;
        background: transparent !important;
        padding-bottom: 2px !important;
    }}
    button[data-baseweb="tab"] {{
        padding: 12px 22px !important;
        background: transparent !important;
        border-radius: 10px 10px 0 0 !important;
        border-bottom: 2px solid transparent !important;
        color: #475569 !important;            /* dark slate on light canvas — readable */
        font-family: var(--gl-font-sans) !important;
        font-size: 0.96rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.02em !important;    /* CJK-friendly spacing */
        transition: all .2s ease !important;
        position: relative;
    }}
    button[data-baseweb="tab"] p {{
        color: inherit !important;
        font-weight: inherit !important;
        font-size: inherit !important;
    }}
    button[data-baseweb="tab"]:hover {{
        color: #0f172a !important;           /* near-black on white hover */
        background: linear-gradient(180deg, rgba(6,182,212,0.06), rgba(37,99,235,0.03)) !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: #0b1220 !important;            /* deep slate — HIGH contrast on light bg */
        background: linear-gradient(180deg, rgba(6,182,212,0.12), rgba(37,99,235,0.05)) !important;
        border-bottom-color: #06b6d4 !important;
        box-shadow: 0 -1px 12px rgba(6,182,212,0.12) inset;
    }}
    /* Cyan glow underline pulse for active tab */
    button[data-baseweb="tab"][aria-selected="true"]::after {{
        content: "";
        position: absolute;
        left: 10%; right: 10%;
        bottom: -2px;
        height: 2px;
        background: linear-gradient(90deg, transparent, #06b6d4, #2563eb, transparent);
        box-shadow: 0 0 10px rgba(6,182,212,0.55);
    }}
    /* Baseweb-generated underline — hide (we use our own) */
    [data-baseweb="tab-highlight"] {{
        background: transparent !important;
        height: 0 !important;
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
    /* ================================================================= */
    /* 6. 股票預測系統 — sidebar brand + system health card (dark theme) */
    /* ================================================================= */
    /* Brand block at the top of the dark sidebar — softer, tech-luxe */
    .gl-brand {{
        padding: 18px 18px 16px 18px;
        border-bottom: 1px solid rgba(6,182,212,0.14);
        margin: -8px -16px 0 -16px;
        background:
            radial-gradient(120% 80% at 0% 0%, rgba(6,182,212,0.12), transparent 60%),
            linear-gradient(180deg, rgba(6,182,212,0.06), transparent);
        position: relative;
    }}
    .gl-brand::before {{
        content: "";
        position: absolute;
        left: 0; right: 0; bottom: -1px;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(6,182,212,0.4), transparent);
    }}
    .gl-brand-eyebrow {{
        font-family: var(--gl-font-mono);
        font-size: 0.62rem;
        color: #06b6d4 !important;
        letter-spacing: 0.22em;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 6px;
    }}
    .gl-brand-title {{
        font-size: 1.22rem;
        font-weight: 800;
        color: #e8f7fc !important;
        letter-spacing: 0.02em;
        display: flex;
        align-items: center;
        gap: 10px;
        font-family: var(--gl-font-sans);
        text-shadow: 0 0 18px rgba(6,182,212,0.25);
    }}
    .gl-brand-dot {{
        width: 8px; height: 8px;
        border-radius: 50%;
        background: #06b6d4;
        box-shadow: 0 0 0 0 rgba(6,182,212,0.55);
        animation: gl-pulse-cyan 2s cubic-bezier(0.4,0,0.6,1) infinite;
        display: inline-block;
    }}
    @keyframes gl-pulse-cyan {{
        0%   {{ box-shadow: 0 0 0 0 rgba(6,182,212,0.6); }}
        70%  {{ box-shadow: 0 0 0 10px rgba(6,182,212,0);  }}
        100% {{ box-shadow: 0 0 0 0 rgba(6,182,212,0);    }}
    }}
    /* Section headers inside dark sidebar */
    .gl-side-group-head {{
        padding: 14px 8px 6px 4px;
        color: #5b7186 !important;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        font-family: var(--gl-font-sans);
    }}
    /* Count pill on right of sidebar nav items */
    .gl-side-count {{
        float: right;
        font-family: var(--gl-font-mono);
        font-size: 0.66rem;
        color: #8899aa !important;
        background: rgba(255,255,255,0.04);
        padding: 1px 7px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.06);
        letter-spacing: 0.04em;
    }}
    /* ---- System health card (now at TOP of sidebar, above nav) ---- */
    .gl-syshealth {{
        margin: 10px 6px 14px 6px;
        padding: 14px 14px 12px 14px;
        background: linear-gradient(180deg, rgba(6,182,212,0.08), rgba(10,20,30,0.55));
        border: 1px solid rgba(6,182,212,0.18);
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.04);
        position: relative;
        overflow: hidden;
    }}
    .gl-syshealth::after {{
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #06b6d4, #2563eb, #7c3aed);
        opacity: 0.7;
    }}
    .gl-syshealth-head {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
    }}
    /* CSS conic-gradient ring (no SVG — avoids Streamlit code-block bug) */
    .gl-syshealth-ring {{
        --pct: 100;
        --ring-color: #06b6d4;
        --ring-track: rgba(255,255,255,0.08);
        --ring-bg: #0f1a28;
        --ring-text: #e8f7fc;
        position: relative;
        width: 54px; height: 54px;
        flex-shrink: 0;
        border-radius: 50%;
        background:
            conic-gradient(var(--ring-color) calc(var(--pct) * 1%), var(--ring-track) 0);
        display: grid;
        place-items: center;
    }}
    .gl-syshealth-ring::before {{
        content: "";
        position: absolute;
        inset: 5px;
        background: var(--ring-bg);
        border-radius: 50%;
    }}
    .gl-syshealth-ring-label {{
        position: relative;
        z-index: 1;
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 0.82rem;
        font-weight: 700;
        color: var(--ring-text);
        letter-spacing: 0;
    }}
    .gl-syshealth.light .gl-syshealth-ring {{
        --ring-track: #e2e8f0;
        --ring-bg: #ffffff;
        --ring-text: #0f172a;
    }}
    .gl-syshealth-labels {{
        display: flex;
        flex-direction: column;
        gap: 1px;
    }}
    .gl-syshealth-title {{
        font-size: 0.68rem;
        font-weight: 700;
        color: #b4ccdf !important;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        font-family: var(--gl-font-sans);
    }}
    .gl-syshealth-value {{
        font-family: var(--gl-font-mono);
        font-variant-numeric: tabular-nums;
        font-size: 1.35rem;
        font-weight: 700;
        color: #e8f7fc !important;
        line-height: 1;
    }}
    .gl-syshealth-sub {{
        font-size: 0.66rem;
        color: #06b6d4 !important;
        font-family: var(--gl-font-mono);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 600;
    }}
    .gl-syshealth-kpi {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 3px 0;
        font-family: var(--gl-font-mono);
        font-size: 0.68rem;
        border-top: 1px dotted rgba(255,255,255,0.06);
    }}
    .gl-syshealth-kpi:first-of-type {{ border-top: none; }}
    .gl-syshealth-kpi-k {{ color: #5b7186 !important; letter-spacing: 0.06em; }}
    .gl-syshealth-kpi-v {{ color: #cce4f1 !important; font-weight: 600; font-variant-numeric: tabular-nums; }}
    .gl-syshealth-foot {{
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px dotted rgba(255,255,255,0.08);
        font-size: 0.62rem;
        color: #5b7186 !important;
        font-family: var(--gl-font-mono);
        letter-spacing: 0.04em;
    }}
    .gl-syshealth-foot strong {{ color: #b4ccdf !important; font-weight: 600; }}
    .gl-syshealth-btns {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px;
        margin-top: 8px;
    }}
    .gl-syshealth-btn {{
        padding: 5px 8px;
        text-align: center;
        font-family: var(--gl-font-sans);
        font-size: 0.72rem;
        font-weight: 600;
        border-radius: 6px;
        color: #cce4f1 !important;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        cursor: pointer;
        transition: all .2s ease;
    }}
    .gl-syshealth-btn:hover {{
        background: rgba(6,182,212,0.1);
        border-color: rgba(6,182,212,0.3);
        color: #e8f7fc !important;
    }}
    /* ---- Light-mode system health card (when used in main canvas) ---- */
    .gl-syshealth.light {{
        margin: 0 0 14px 0;
        padding: 16px 20px;
        background: linear-gradient(135deg, #ffffff 0%, #f0fafe 100%);
        border: 1px solid var(--gl-border);
        border-left: 3px solid var(--gl-cyan);
        border-radius: 12px;
        box-shadow: var(--gl-shadow-sm);
    }}
    .gl-syshealth.light .gl-syshealth-title {{ color: var(--gl-text-3) !important; }}
    .gl-syshealth.light .gl-syshealth-value {{ color: var(--gl-text) !important; }}
    .gl-syshealth.light .gl-syshealth-sub {{ color: var(--gl-cyan) !important; }}
    .gl-syshealth.light .gl-syshealth-kpi {{ border-top: 1px dotted var(--gl-border); }}
    .gl-syshealth.light .gl-syshealth-kpi-k {{ color: var(--gl-text-3) !important; }}
    .gl-syshealth.light .gl-syshealth-kpi-v {{ color: var(--gl-text) !important; }}
    .gl-syshealth.light .gl-syshealth-foot {{ color: var(--gl-text-3) !important; border-top-color: var(--gl-border); }}
    .gl-syshealth.light .gl-syshealth-foot strong {{ color: var(--gl-text) !important; }}
    /* ---- Search chip in topbar ---- */
    .gl-topbar-search {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        background: var(--gl-subtle);
        border: 1px solid var(--gl-border);
        border-radius: 999px;
        color: var(--gl-text-3);
        font-size: 0.78rem;
        font-family: var(--gl-font-mono);
        margin-right: 10px;
        min-width: 240px;
    }}
    .gl-topbar-search .kbd {{
        margin-left: auto;
        padding: 1px 5px;
        font-size: 0.64rem;
        background: rgba(255,255,255,0.6);
        border: 1px solid var(--gl-border);
        border-radius: 4px;
        color: var(--gl-text-3);
    }}
    /* ---- Dynamic hero orbital ring (SVG globe accent) ---- */
    .gl-orbit {{
        position: absolute;
        top: -50px;
        right: -40px;
        width: 280px;
        height: 280px;
        pointer-events: none;
        opacity: 0.75;
        z-index: 0;
    }}
    .gl-orbit circle {{ fill: none; stroke: rgba(37,99,235,0.18); stroke-width: 1; }}
    .gl-orbit circle.c1 {{ stroke: rgba(37,99,235,0.28); }}
    .gl-orbit circle.c2 {{ stroke: rgba(124,58,237,0.22); }}
    .gl-orbit circle.c3 {{ stroke: rgba(6,182,212,0.22); }}
    .gl-orbit .dot {{ fill: #06b6d4; }}
    @keyframes gl-orbit-rot {{ to {{ transform: rotate(360deg); }} }}
    .gl-orbit .spin-fast {{ transform-origin: 140px 140px; animation: gl-orbit-rot 18s linear infinite; }}
    .gl-orbit .spin-med  {{ transform-origin: 140px 140px; animation: gl-orbit-rot 32s linear infinite reverse; }}
    .gl-orbit .spin-slow {{ transform-origin: 140px 140px; animation: gl-orbit-rot 56s linear infinite; }}
    /* ---- Traffic-light signal cards (🟢🟡🔴) ---- */
    .gl-signal {{
        position: relative;
        padding: 18px 22px;
        border-radius: 14px;
        border: 1px solid var(--gl-border);
        background: var(--gl-surface);
        box-shadow: var(--gl-shadow-sm);
        overflow: hidden;
    }}
    .gl-signal::before {{
        content: "";
        position: absolute;
        top: 0; left: 0;
        width: 4px; height: 100%;
    }}
    .gl-signal.green::before  {{ background: linear-gradient(180deg, #10b981, #06b6d4); }}
    .gl-signal.amber::before  {{ background: linear-gradient(180deg, #f59e0b, #f43f5e); }}
    .gl-signal.red::before    {{ background: linear-gradient(180deg, #f43f5e, #ef4444); }}
    .gl-signal-head {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
    }}
    .gl-signal-light {{
        width: 14px; height: 14px;
        border-radius: 50%;
        flex-shrink: 0;
    }}
    .gl-signal.green .gl-signal-light {{ background: #10b981; box-shadow: 0 0 12px rgba(16,185,129,0.5); }}
    .gl-signal.amber .gl-signal-light {{ background: #f59e0b; box-shadow: 0 0 12px rgba(245,158,11,0.5); }}
    .gl-signal.red   .gl-signal-light {{ background: #f43f5e; box-shadow: 0 0 12px rgba(244,63,94,0.5); }}
    .gl-signal-title {{
        font-size: 0.92rem;
        font-weight: 700;
        color: var(--gl-text);
    }}
    .gl-signal-val {{
        font-family: var(--gl-font-mono);
        font-variant-numeric: tabular-nums;
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--gl-text);
        line-height: 1.1;
    }}
    .gl-signal-val.up   {{ color: var(--gl-emerald); }}
    .gl-signal-val.down {{ color: var(--gl-rose); }}
    .gl-signal-desc {{
        font-size: 0.82rem;
        color: var(--gl-text-2);
        margin-top: 6px;
        line-height: 1.55;
    }}
    /* ---- Sector colour codes (產業色碼) ---- */
    .gl-sector {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 2px 8px;
        font-size: 0.7rem;
        font-family: var(--gl-font-sans);
        font-weight: 600;
        border-radius: 5px;
    }}
    .gl-sector::before {{
        content: "";
        width: 6px; height: 6px;
        border-radius: 50%;
    }}
    .gl-sector[data-s="半導體"]    {{ background: #dbeafe; color: #1e40af; }}
    .gl-sector[data-s="半導體"]::before {{ background: #2563eb; }}
    .gl-sector[data-s="電子零組件"]  {{ background: #e0e7ff; color: #3730a3; }}
    .gl-sector[data-s="電子零組件"]::before {{ background: #4f46e5; }}
    .gl-sector[data-s="金融"]      {{ background: #dcfce7; color: #166534; }}
    .gl-sector[data-s="金融"]::before {{ background: #10b981; }}
    .gl-sector[data-s="生技醫療"]   {{ background: #fae8ff; color: #86198f; }}
    .gl-sector[data-s="生技醫療"]::before {{ background: #a855f7; }}
    .gl-sector[data-s="傳產"]      {{ background: #fef3c7; color: #92400e; }}
    .gl-sector[data-s="傳產"]::before {{ background: #f59e0b; }}
    .gl-sector[data-s="航運"]      {{ background: #cffafe; color: #155e75; }}
    .gl-sector[data-s="航運"]::before {{ background: #06b6d4; }}
    .gl-sector[data-s="通訊網路"]   {{ background: #f3e8ff; color: #6b21a8; }}
    .gl-sector[data-s="通訊網路"]::before {{ background: #7c3aed; }}
    .gl-sector[data-s="汽車"]      {{ background: #ffe4e6; color: #9f1239; }}
    .gl-sector[data-s="汽車"]::before {{ background: #f43f5e; }}
    /* ---- 財報狗-style subsection tabs (per-page navigation) ---- */
    .gl-subtabs {{
        display: flex;
        gap: 4px;
        padding: 4px;
        background: var(--gl-subtle);
        border: 1px solid var(--gl-border);
        border-radius: 10px;
        margin-bottom: 18px;
        overflow-x: auto;
    }}
    /* Streamlit radio rendered as segmented tab strip */
    div[data-baseweb="radio"][role="radiogroup"] label {{
        padding: 7px 14px !important;
        border-radius: 7px !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        cursor: pointer !important;
        font-family: var(--gl-font-sans) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        color: var(--gl-text-2) !important;
        transition: all .2s ease !important;
    }}
    div[data-baseweb="radio"][role="radiogroup"] label:hover {{
        color: var(--gl-text) !important;
        background: rgba(37,99,235,0.04) !important;
    }}
    /* Phase-chip helper */
    .phase-chip {{
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--gl-surface);
        border: 1px solid var(--gl-border);
        text-align: left;
        box-shadow: var(--gl-shadow-sm);
    }}
    .phase-chip.cur {{
        border-color: rgba(37,99,235,0.35);
        background: linear-gradient(135deg, #f0f7ff, #f5f0ff);
        box-shadow: var(--gl-shadow-glow);
    }}
    /* Path-card (KPI gateway) base & inv/qnt already covered */
    .path-card {{
        position: relative;
        padding: 20px 22px;
        border-radius: 14px;
        background: var(--gl-surface);
        border: 1px solid var(--gl-border);
        box-shadow: var(--gl-shadow-sm);
        overflow: hidden;
        transition: all .25s ease;
    }}
    .path-card::before {{
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: var(--gl-grad-tech);
    }}
    .path-card:hover {{
        border-color: rgba(37,99,235,0.35);
        box-shadow: var(--gl-shadow-glow);
        transform: translateY(-2px);
    }}
    .path-title {{
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--gl-text);
        margin-bottom: 10px;
        letter-spacing: -0.005em;
    }}
    .path-desc {{
        font-size: 0.92rem;
        color: var(--gl-text-2);
        line-height: 1.6;
        margin-bottom: 14px;
    }}
    .path-desc strong {{ color: var(--gl-text); }}
    .path-tags {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }}
    /* ================================================================= */
    /*  7. Top navigation pills — CYBERPUNK DARK (match dark sidebar)      */
    /* ================================================================= */
    /* Design target: 與左側 股票預測系統 sidebar 同血統 —
       深色漸層、青藍霓虹邊框、等寬字體、淡網格背景、scan-line 輝光。    */
    .gl-topnav {{
        position: sticky;
        top: 0;
        z-index: 40;
        background:
            radial-gradient(140% 90% at 0% 0%, rgba(6,182,212,0.14), transparent 55%),
            radial-gradient(120% 80% at 100% 100%, rgba(37,99,235,0.12), transparent 60%),
            linear-gradient(180deg, #0a1420 0%, #101c2d 55%, #0c1725 100%);
        border: 1px solid rgba(6,182,212,0.22);
        border-radius: 0 0 14px 14px;
        padding: 14px 14px 12px 14px;
        margin: -0.5rem -1rem 22px -1rem;
        box-shadow:
            0 10px 28px rgba(2,6,23,0.28),
            inset 0 1px 0 rgba(6,182,212,0.18),
            inset 0 -1px 0 rgba(6,182,212,0.08);
        overflow: hidden;
    }}
    /* Subtle tech-grid backdrop (matches sidebar) */
    .gl-topnav::before {{
        content: "";
        position: absolute;
        inset: 0;
        background-image:
            linear-gradient(rgba(6,182,212,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(6,182,212,0.05) 1px, transparent 1px);
        background-size: 28px 28px;
        pointer-events: none;
        opacity: 0.55;
        mask-image: linear-gradient(180deg, rgba(0,0,0,0.9), rgba(0,0,0,0.35));
        -webkit-mask-image: linear-gradient(180deg, rgba(0,0,0,0.9), rgba(0,0,0,0.35));
    }}
    /* Top scan-line accent */
    .gl-topnav::after {{
        content: "";
        position: absolute;
        top: 0; left: 10%; right: 10%;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(103,232,249,0.75), rgba(37,99,235,0.55), transparent);
        box-shadow: 0 0 8px rgba(103,232,249,0.4);
    }}
    /* Group label — cyan mono eyebrow */
    .gl-topnav-gname {{
        font-family: var(--gl-font-mono);
        font-size: 0.64rem;
        color: #67e8f9 !important;
        letter-spacing: 0.20em;
        font-weight: 700;
        text-transform: uppercase;
        padding: 0 6px 8px 10px;
        position: relative;
        text-shadow: 0 0 8px rgba(103,232,249,0.35);
    }}
    .gl-topnav-gname::before {{
        content: "";
        display: inline-block;
        width: 3px;
        height: 10px;
        vertical-align: -1px;
        margin-right: 7px;
        background: linear-gradient(180deg, #67e8f9, #2563eb);
        border-radius: 2px;
        box-shadow: 0 0 6px rgba(103,232,249,0.6);
    }}
    /* Page-link pills — dark glass on dark nav */
    .gl-topnav [data-testid="stPageLink-NavLink"],
    .gl-topnav a[data-testid="stPageLink"] {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 7px;
        padding: 10px 12px !important;
        border-radius: 10px !important;
        border: 1px solid rgba(103,232,249,0.18) !important;
        background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015)) !important;
        font-family: var(--gl-font-sans) !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.04em !important;    /* CJK breathing room — 避免密集 */
        color: #cfe1f2 !important;
        transition: all .22s ease !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.04),
            0 1px 2px rgba(0,0,0,0.25);
        position: relative;
        overflow: hidden;
        white-space: nowrap !important;        /* 禁止分頁名稱奇怪斷行 */
        text-overflow: ellipsis;
        min-height: 40px;
        line-height: 1.2 !important;
    }}
    /* Override any inner text elements — force bright-on-dark readability */
    .gl-topnav [data-testid="stPageLink-NavLink"] *,
    .gl-topnav a[data-testid="stPageLink"] *,
    .gl-topnav [data-testid="stPageLink-NavLink"] p,
    .gl-topnav a[data-testid="stPageLink"] p,
    .gl-topnav [data-testid="stPageLink-NavLink"] span,
    .gl-topnav a[data-testid="stPageLink"] span {{
        color: inherit !important;
        font-weight: inherit !important;
        font-size: inherit !important;
        letter-spacing: inherit !important;
        margin: 0 !important;
        text-shadow: none !important;
    }}
    /* Hover — cyan neon accent */
    .gl-topnav [data-testid="stPageLink-NavLink"]:hover,
    .gl-topnav a[data-testid="stPageLink"]:hover {{
        border-color: rgba(103,232,249,0.55) !important;
        background: linear-gradient(180deg, rgba(6,182,212,0.14), rgba(37,99,235,0.10)) !important;
        color: #ffffff !important;
        transform: translateY(-1px);
        box-shadow:
            0 8px 22px rgba(6,182,212,0.28),
            inset 0 1px 0 rgba(255,255,255,0.08),
            0 0 0 1px rgba(103,232,249,0.18) !important;
    }}
    /* Active page — bright cyan glow, obvious contrast */
    .gl-topnav .gl-active [data-testid="stPageLink-NavLink"],
    .gl-topnav .gl-active a[data-testid="stPageLink"] {{
        background: linear-gradient(180deg, rgba(103,232,249,0.22), rgba(37,99,235,0.16)) !important;
        border-color: rgba(103,232,249,0.85) !important;
        color: #ecfeff !important;
        box-shadow:
            0 0 0 1px rgba(103,232,249,0.28),
            0 6px 22px rgba(6,182,212,0.38),
            inset 0 1px 0 rgba(255,255,255,0.12) !important;
        text-shadow: 0 0 10px rgba(103,232,249,0.55);
    }}
    .gl-topnav .gl-active [data-testid="stPageLink-NavLink"]::before,
    .gl-topnav .gl-active a[data-testid="stPageLink"]::before {{
        content: "";
        position: absolute;
        left: 0; top: 0; bottom: 0;
        width: 3px;
        background: linear-gradient(180deg, #67e8f9 0%, #2563eb 100%);
        border-radius: 2px 0 0 2px;
        box-shadow: 0 0 8px rgba(103,232,249,0.75);
    }}
    /* Animated sweep for active pill (subtle cyber feel) */
    .gl-topnav .gl-active [data-testid="stPageLink-NavLink"]::after,
    .gl-topnav .gl-active a[data-testid="stPageLink"]::after {{
        content: "";
        position: absolute;
        top: 0; bottom: 0;
        left: -60%;
        width: 50%;
        background: linear-gradient(90deg, transparent, rgba(103,232,249,0.18), transparent);
        animation: gl-topnav-sweep 3.5s ease-in-out infinite;
        pointer-events: none;
    }}
    @keyframes gl-topnav-sweep {{
        0%   {{ left: -60%; }}
        60%  {{ left: 120%; }}
        100% {{ left: 120%; }}
    }}
    /* Icon tint (emoji or Material glyph preceding the label) */
    .gl-topnav [data-testid="stPageLink-NavLink"] [data-testid="stIconMaterial"],
    .gl-topnav a[data-testid="stPageLink"] [data-testid="stIconMaterial"] {{
        color: #67e8f9 !important;
        text-shadow: 0 0 6px rgba(103,232,249,0.45);
    }}
    /* Group divider — subtle vertical cyan rule */
    .gl-topnav-sep {{
        width: 1px;
        background: linear-gradient(180deg, transparent, rgba(103,232,249,0.35), transparent);
        margin: 0 6px;
        min-height: 56px;
    }}
    /* ================================================================= */
    /*  8. Fix sidebar expand/collapse Material Symbol icon overlap        */
    /* ================================================================= */
    /* When the Material Symbols font fails to load (common on Cloud cold
       start), the raw text "expand_more" / "expand_less" shows instead of
       the glyph. Replace with a pure-CSS triangle that rotates on expand. */
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] span[class*="material-symbols"],
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] span[class*="MaterialSymbols"],
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] [data-testid*="ExpandMore"],
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] [data-testid*="ExpandLess"] {{
        font-size: 0 !important;
        line-height: 0 !important;
        width: 16px;
        height: 16px;
        position: relative;
        color: transparent !important;
        display: inline-block !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] span[class*="material-symbols"]::after,
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] span[class*="MaterialSymbols"]::after,
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] [data-testid*="ExpandMore"]::after,
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] [data-testid*="ExpandLess"]::after {{
        content: "";
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-style: solid;
        border-width: 4px 0 4px 6px;
        border-color: transparent transparent transparent #9fb6cc;
        transform-origin: 2px 50%;
        transform: translate(-2px, -50%) rotate(0deg);
        transition: transform 0.2s ease;
    }}
    /* Rotate triangle when expanded */
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"][aria-expanded="true"] span[class*="material-symbols"]::after,
    section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"][aria-expanded="true"] span[class*="MaterialSymbols"]::after {{
        transform: translate(-2px, -50%) rotate(90deg);
    }}
    /* Same fix for collapsible expanders inside main content */
    details > summary span[class*="material-symbols"],
    [data-testid="stExpander"] span[class*="material-symbols"] {{
        font-size: 0 !important;
        color: transparent !important;
        width: 14px;
        height: 14px;
        display: inline-block !important;
        position: relative;
    }}
    details > summary span[class*="material-symbols"]::after,
    [data-testid="stExpander"] span[class*="material-symbols"]::after {{
        content: "";
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-style: solid;
        border-width: 4px 0 4px 6px;
        border-color: transparent transparent transparent var(--gl-text-2);
        transform: translate(-2px, -50%) rotate(0deg);
        transition: transform 0.2s ease;
    }}
    details[open] > summary span[class*="material-symbols"]::after,
    [data-testid="stExpander"][open] summary span[class*="material-symbols"]::after {{
        transform: translate(-2px, -50%) rotate(90deg);
    }}
    /* ================================================================= */
    /*  9. Sidebar real action buttons (重整 / 手冊) — compact grid       */
    /* ================================================================= */
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button {{
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        color: #cce4f1 !important;
        font-family: var(--gl-font-sans) !important;
        font-size: 0.74rem !important;
        font-weight: 600 !important;
        padding: 6px 10px !important;
        border-radius: 8px !important;
        min-height: 30px !important;
        height: 30px !important;
        transition: all .2s ease !important;
        box-shadow: none !important;
    }}
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button:hover {{
        background: rgba(6,182,212,0.12) !important;
        border-color: rgba(6,182,212,0.35) !important;
        color: #e8f7fc !important;
        transform: translateY(-1px);
    }}
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button:active {{
        transform: translateY(0);
    }}
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
    # Single-line HTML — CommonMark-safe (empty conditional fragments were
    # leaving whitespace-only lines that terminated the HTML block on Cloud,
    # causing {sub_html} to render as escaped text on a black background).
    st.markdown(
        (
            f'<div class="gl-kpi accent-{accent}">'
            f'<div class="gl-kpi-label">{label}</div>'
            f'<div class="gl-kpi-value">{value}</div>'
            f'{delta_html}'
            f'{sub_html}'
            f'</div>'
        ),
        unsafe_allow_html=True,
    )


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
    st.markdown(
        f'<div class="gl-topbar">'
        f'<div class="gl-topbar-l">'
        f'<span style="color:var(--gl-text-3);font-size:0.85rem;">{crumb_left}</span>'
        f'<span style="color:var(--gl-text-3);">›</span>'
        f'<span style="color:var(--gl-text-1);font-weight:600;font-size:0.9rem;">{crumb_current}</span>'
        f'</div>'
        f'<div class="gl-topbar-r">{chip_html}{clock_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


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
    # Single-line HTML — CommonMark-safe (no blank / whitespace-only lines).
    return (
        f'<div class="gl-pb">'
        f'<span class="gl-pb-pill" data-p="{pillar_key}">{label}</span>'
        f'<div class="gl-pb-bar-wrap"><div class="gl-pb-bar" data-p="{pillar_key}" style="width:{pct:.1f}%"></div></div>'
        f'<span class="gl-pb-num">{feat_count}</span>'
        f'{delta_html}'
        f'</div>'
    )


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


def render_hero(eyebrow: str, title_html: str, meta_chips: list = None,
                subtitle: str = "", show_orbit: bool = False):
    """Hero block with gradient title + eyebrow + meta chips + blur orb.

    Args:
        eyebrow: Uppercase eyebrow text (letter-spaced).
        title_html: Hero title (may include <span class="gl-hero-accent"> for gradient highlight).
        meta_chips: Optional list of (label, variant) tuples.
        subtitle: Short Chinese subtitle under the title.
        show_orbit: If True, render a decorative rotating orbital ring (right side of hero).
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
    orbit_html = render_orbital_ring_svg() if show_orbit else ""
    # Single-line HTML — CommonMark-safe.
    st.markdown(
        f'<div class="gl-hero">'
        f'<div class="gl-hero-orb"></div>'
        f'{orbit_html}'
        f'<span class="gl-hero-eyebrow">{eyebrow}</span>'
        f'<div class="gl-hero-title">{title_html}</div>'
        f'{subtitle_html}'
        f'<div style="margin-top:18px;display:flex;gap:8px;flex-wrap:wrap;">{chip_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_live_chip(text: str = "LIVE · 研究快照"):
    """Pulsing emerald dot chip for live-status indicators."""
    st.markdown(
        f'<span class="gl-live">{text}</span>',
        unsafe_allow_html=True,
    )


def _cyan_ring_svg(pct: float, size: int = 48, stroke: int = 5,
                   color: str = "#06b6d4", track: str = "rgba(255,255,255,0.08)",
                   label_color: str = "#e8f7fc") -> str:
    """Return a dark-themed ring (0–100%) using pure CSS conic-gradient.

    CRITICAL: NO SVG — Streamlit Cloud's markdown renderer treats ``<svg>``
    followed by nested ``<div>`` children as an indented code block, which
    causes the inner HTML (e.g. ``.gl-syshealth-labels``) to be escaped and
    wrapped in a ``stCode`` component. A pure HTML + CSS conic-gradient ring
    bypasses this issue entirely.

    Function name kept for backward-compat (a few pages may import it). Width,
    stroke, and colours are passed as CSS custom properties so the single
    stylesheet rule can handle both dark (sidebar) and light (main) modes.
    """
    pct = max(0, min(100, pct))
    # Dark mode defaults are in the CSS; only override light mode here.
    return (
        f'<div class="gl-syshealth-ring" '
        f'style="--pct:{pct:.0f}; --ring-color:{color};">'
        f'<span class="gl-syshealth-ring-label">{pct:.0f}%</span>'
        f'</div>'
    )


def render_system_health_card(gates_passed: int = 9, total_gates: int = 9,
                              dataset: str = "2023/03–2025/03",
                              samples: str = "948,976",
                              features: str = "91 / 1,623",
                              dsr: str = "12.12",
                              last_verified: str = "2026-04-20 14:24",
                              mode: str = "dark",
                              show_buttons: bool = False) -> str:
    """Return the HTML for a 系統健康度 card.

    Args:
        gates_passed / total_gates: quality-gate pass counts.
        dataset / samples / features / dsr: the four core KPI values.
        last_verified: ISO-ish timestamp for the last verification run.
        mode: "dark" (sidebar footer) or "light" (main-canvas panel).
        show_buttons: legacy fake HTML buttons (default False — real Streamlit
            buttons are injected separately via `inject_sidebar_action_buttons`).
    """
    pct = (gates_passed / total_gates * 100) if total_gates else 0
    klass = "gl-syshealth light" if mode == "light" else "gl-syshealth"
    ring = _cyan_ring_svg(
        pct,
        size=54,
        label_color=("#0f172a" if mode == "light" else "#e8f7fc"),
        track=("#e2e8f0" if mode == "light" else "rgba(255,255,255,0.08)"),
    )
    btns_html = ""
    if show_buttons:
        btns_html = (
            f'<div class="gl-syshealth-btns">'
            f'<div class="gl-syshealth-btn">🔄 重整</div>'
            f'<div class="gl-syshealth-btn">? 手冊</div>'
            f'</div>'
        )
    # CRITICAL: no blank lines inside HTML — CommonMark terminates HTML blocks on blank lines.
    return (
        f'<div class="{klass}">'
        f'<div class="gl-syshealth-head">{ring}'
        f'<div class="gl-syshealth-labels">'
        f'<div class="gl-syshealth-title">系統健康度</div>'
        f'<div class="gl-syshealth-value">{gates_passed} / {total_gates}</div>'
        f'<div class="gl-syshealth-sub">品質閘門 PASS</div>'
        f'</div></div>'
        f'<div class="gl-syshealth-kpi"><span class="gl-syshealth-kpi-k">DATASET</span><span class="gl-syshealth-kpi-v">{dataset}</span></div>'
        f'<div class="gl-syshealth-kpi"><span class="gl-syshealth-kpi-k">SAMPLES</span><span class="gl-syshealth-kpi-v">{samples}</span></div>'
        f'<div class="gl-syshealth-kpi"><span class="gl-syshealth-kpi-k">FEATURES</span><span class="gl-syshealth-kpi-v">{features}</span></div>'
        f'<div class="gl-syshealth-kpi"><span class="gl-syshealth-kpi-k">DSR</span><span class="gl-syshealth-kpi-v">{dsr}</span></div>'
        f'<div class="gl-syshealth-foot">最後驗證時間　<strong>{last_verified}</strong></div>'
        f'{btns_html}'
        f'</div>'
    )


def inject_sidebar_brand(product: str = "股票預測系統",
                         eyebrow: str = "MULTI-FACTOR"):
    """Inject the 股票預測系統 brand block at the top of the sidebar.

    Renders on every page because app.py's sidebar runs first.
    Single-line HTML — CommonMark-safe.
    """
    st.sidebar.markdown(
        (
            f'<div class="gl-brand">'
            f'<div class="gl-brand-eyebrow">{eyebrow}</div>'
            f'<div class="gl-brand-title"><span class="gl-brand-dot"></span>{product}</div>'
            f'</div>'
        ),
        unsafe_allow_html=True,
    )


def inject_sidebar_health(gates_passed: int = 9, total_gates: int = 9,
                          dataset: str = "2023/03–2025/03",
                          samples: str = "948,976",
                          features: str = "91 / 1,623",
                          dsr: str = "12.12",
                          last_verified: str = "2026-04-20 14:24"):
    """Inject the 系統健康度 card at the bottom of the sidebar."""
    st.sidebar.markdown(
        render_system_health_card(
            gates_passed=gates_passed,
            total_gates=total_gates,
            dataset=dataset,
            samples=samples,
            features=features,
            dsr=dsr,
            last_verified=last_verified,
            mode="dark",
        ),
        unsafe_allow_html=True,
    )


def render_traffic_signal(color: str, title: str, value: str,
                          desc: str = "", val_class: str = "") -> str:
    """Return HTML for a traffic-light signal card (🟢🟡🔴).

    Args:
        color: "green" | "amber" | "red"
        title: short title (e.g. "模型判讀")
        value: main number (e.g. "0.6490")
        desc: short description line.
        val_class: optional "up" / "down" to tint the main number.
    """
    # Single-line HTML — CommonMark-safe (no blank lines).
    return (
        f'<div class="gl-signal {color}">'
        f'<div class="gl-signal-head">'
        f'<span class="gl-signal-light"></span>'
        f'<span class="gl-signal-title">{title}</span>'
        f'</div>'
        f'<div class="gl-signal-val {val_class}">{value}</div>'
        f'<div class="gl-signal-desc">{desc}</div>'
        f'</div>'
    )


def render_sector_chip(sector: str) -> str:
    """Return HTML for a sector colour-coded chip."""
    return f'<span class="gl-sector" data-s="{sector}">{sector}</span>'


def render_pillar_radar(values: dict, title: str = "九支柱雷達圖",
                        reference: dict = None, height: int = 420):
    """Render a Plotly polar radar of the 9 pillars with glint theme.

    Args:
        values: dict keyed by pillar code (trend/fund/val/event/risk/chip/ind/txt/sent)
                to a 0–1 score.
        title: chart title.
        reference: optional dict (same shape) rendered as a lighter comparison layer.
        height: chart height in px.

    Returns the Plotly Figure.
    """
    import plotly.graph_objects as go
    order = ["trend", "fund", "val", "event", "risk", "chip", "ind", "txt", "sent"]
    labels = {
        "trend": "技術面",
        "fund":  "基本面",
        "val":   "評價面",
        "event": "事件面",
        "risk":  "風險面",
        "chip":  "籌碼面",
        "ind":   "產業面",
        "txt":   "文本面",
        "sent":  "情緒面",
    }
    theta = [labels[k] for k in order] + [labels[order[0]]]
    r_main = [float(values.get(k, 0)) for k in order]
    r_main.append(r_main[0])
    fig = go.Figure()
    if reference is not None:
        r_ref = [float(reference.get(k, 0)) for k in order]
        r_ref.append(r_ref[0])
        fig.add_trace(go.Scatterpolar(
            r=r_ref, theta=theta,
            fill="toself",
            name="Baseline",
            line=dict(color="rgba(148,163,184,0.55)", width=1.5),
            fillcolor="rgba(148,163,184,0.12)",
            hovertemplate="%{theta}: %{r:.3f}<extra>Baseline</extra>",
        ))
    fig.add_trace(go.Scatterpolar(
        r=r_main, theta=theta,
        fill="toself",
        name="LOPO Δ",
        line=dict(color="#2563eb", width=2.2),
        fillcolor="rgba(37,99,235,0.22)",
        marker=dict(size=7, color="#7c3aed", line=dict(color="#fff", width=1.2)),
        hovertemplate="<b>%{theta}</b><br>score: %{r:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, x=0.02, y=0.98,
                   font=dict(family="Inter, 'Microsoft JhengHei'", size=14,
                             color="#0f172a")),
        polar=dict(
            bgcolor="rgba(248,250,252,0.7)",
            radialaxis=dict(
                visible=True, range=[0, max(1.0, max(r_main) * 1.15)],
                showline=False, gridcolor="rgba(37,99,235,0.08)",
                tickfont=dict(family="JetBrains Mono", size=9, color="#94a3b8"),
                tickformat=".2f",
            ),
            angularaxis=dict(
                gridcolor="rgba(37,99,235,0.12)",
                linecolor="rgba(37,99,235,0.18)",
                tickfont=dict(family="Inter, 'Microsoft JhengHei'", size=11,
                              color="#475569"),
            ),
        ),
        showlegend=True,
        legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center",
                    font=dict(family="Inter", size=11)),
        height=height,
        margin=dict(t=50, b=40, l=40, r=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def glint_plotly_layout(title: str = "", height: int = 360) -> dict:
    """Return a glint-themed Plotly layout dict for any figure.

    Use with ``fig.update_layout(**glint_plotly_layout(title=..., height=...))``
    to unify chart styling across all pages.
    """
    return dict(
        title=dict(text=title, x=0.02, y=0.97,
                   font=dict(family="Inter, 'Microsoft JhengHei'", size=14,
                             color="#0f172a")),
        font=dict(family="Inter, 'Microsoft JhengHei'", color="#334155", size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.6)",
        height=height,
        margin=dict(t=46, b=40, l=50, r=28),
        xaxis=dict(
            gridcolor="rgba(37,99,235,0.06)",
            linecolor="rgba(37,99,235,0.15)",
            tickfont=dict(family="JetBrains Mono", size=10, color="#64748b"),
        ),
        yaxis=dict(
            gridcolor="rgba(37,99,235,0.06)",
            linecolor="rgba(37,99,235,0.15)",
            tickfont=dict(family="JetBrains Mono", size=10, color="#64748b"),
        ),
        hoverlabel=dict(
            bgcolor="#0f1a28",
            bordercolor="rgba(6,182,212,0.4)",
            font=dict(family="JetBrains Mono", color="#e8f7fc", size=11),
        ),
        legend=dict(
            font=dict(family="Inter", size=11, color="#475569"),
            bgcolor="rgba(255,255,255,0.6)",
            bordercolor="rgba(37,99,235,0.15)",
            borderwidth=1,
        ),
    )


GLINT_COLORS = {
    "blue":    "#2563eb",
    "violet":  "#7c3aed",
    "cyan":    "#06b6d4",
    "emerald": "#10b981",
    "amber":   "#f59e0b",
    "rose":    "#f43f5e",
    "indigo":  "#4f46e5",
    "slate":   "#64748b",
}

# 9-pillar palette aligned with the .gl-pillar badges
PILLAR_COLORS = {
    "trend":  "#2563eb",
    "fund":   "#10b981",
    "val":    "#a855f7",
    "event":  "#f59e0b",
    "risk":   "#f43f5e",
    "chip":   "#4f46e5",
    "ind":    "#06b6d4",
    "txt":    "#7c3aed",
    "sent":   "#ec4899",
}


def render_orbital_ring_svg() -> str:
    """Return a decorative orbital-ring SVG (three concentric orbits + satellite dots).

    CRITICAL: single-line output so it can be embedded in HTML strings passed to
    st.markdown without triggering CommonMark's blank-line-terminates-HTML-block rule.
    """
    return (
        '<svg class="gl-orbit" viewBox="0 0 280 280">'
        '<g class="spin-slow">'
        '<circle class="c1" cx="140" cy="140" r="120"/>'
        '<circle class="dot" cx="260" cy="140" r="3"/>'
        '</g>'
        '<g class="spin-med">'
        '<circle class="c2" cx="140" cy="140" r="90"/>'
        '<circle class="dot" cx="50" cy="140" r="2.5" fill="#7c3aed"/>'
        '</g>'
        '<g class="spin-fast">'
        '<circle class="c3" cx="140" cy="140" r="60"/>'
        '<circle class="dot" cx="200" cy="140" r="2"/>'
        '</g>'
        '<circle cx="140" cy="140" r="8" fill="url(#orb-grad)"/>'
        '<defs>'
        '<radialGradient id="orb-grad">'
        '<stop offset="0%" stop-color="#06b6d4"/>'
        '<stop offset="100%" stop-color="#2563eb"/>'
        '</radialGradient>'
        '</defs>'
        '</svg>'
    )


def render_subtabs(options: list, key: str, default_idx: int = 0,
                   label: str = "子頁切換") -> str:
    """Render 財報狗-style subsection tabs using st.radio + custom CSS.

    Returns the selected option label. Use this at the top of each page to
    split content into financial-website-style tabs.
    """
    import streamlit as st
    st.markdown('<div class="gl-subtabs-wrap">', unsafe_allow_html=True)
    choice = st.radio(
        label,
        options,
        index=default_idx,
        horizontal=True,
        key=key,
        label_visibility="collapsed",
    )
    st.markdown('</div>', unsafe_allow_html=True)
    return choice


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
def _project_outputs_dir():
    """Resolve the project-root outputs directory.

    Handles the Streamlit Cloud shim case where dashboard/app.py does
    os.chdir(程式碼/儀表板/) — Path.cwd() alone is insufficient.
    """
    here = Path(__file__).resolve()
    for candidate in (
        here.parent.parent.parent / "outputs",   # project_root/outputs  ← canonical
        here.parent.parent / "outputs",          # 程式碼/outputs (legacy layout)
        Path.cwd() / "outputs",
        Path.cwd().parent / "outputs",
        Path.cwd().parent.parent / "outputs",
    ):
        if candidate.exists():
            return candidate
    # Last resort so callers get a consistent return type
    return Path.cwd() / "outputs"


@st.cache_data
def load_report():
    """Load the latest Phase 2 report JSON with caching."""
    report_dir = _project_outputs_dir() / "reports"
    reports = sorted(report_dir.glob("phase2_report_*.json"), reverse=True)
    if not reports:
        st.error(
            "找不到 Phase 2 報告。請先執行 `python run_phase2.py`。\n\n"
            f"(已掃描路徑: `{report_dir}`)"
        )
        st.stop()
    with open(reports[0], "r", encoding="utf-8") as f:
        return json.load(f), reports[0].name


@st.cache_data
def load_phase3_report():
    """Load the latest Phase 3 report JSON with caching."""
    report_dir = _project_outputs_dir() / "reports"
    reports = sorted(report_dir.glob("phase3_report_*.json"), reverse=True)
    if not reports:
        return None, None
    with open(reports[0], "r", encoding="utf-8") as f:
        return json.load(f), reports[0].name


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
    gov_dir = _project_outputs_dir() / "governance"
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


# ============================================================================
# Top-nav (Option B) — renders 4-group horizontal nav in main canvas
# Works identically with or without sidebar (embed mode safe)
# ============================================================================
def render_top_nav(groups: dict, active_page_title: str = None):
    """Render sticky top navigation bar with 4 groups × 12 pages.

    Args:
        groups: ordered dict mapping group label (str) → list of st.Page objects
        active_page_title: title of currently active page (for active-state styling)

    Rendered HTML tree:
      .gl-topnav
        ├─ row 1: 4 columns (proportional widths) — group labels
        └─ row 2: N equal columns — one st.page_link per page, wrapped in
                  span.gl-active when matching active_page_title
    """
    weights = [len(pages) for pages in groups.values()]
    total = sum(weights)

    st.markdown('<div class="gl-topnav">', unsafe_allow_html=True)

    # Row 1: group labels with proportional widths
    label_cols = st.columns(weights, gap="small")
    for col, gname in zip(label_cols, groups.keys()):
        with col:
            st.markdown(
                f'<div class="gl-topnav-gname">{gname}</div>',
                unsafe_allow_html=True,
            )

    # Row 2: one column per page, equal widths — spans align with row 1 groups
    page_cols = st.columns(total, gap="small")
    idx = 0
    for gname, pages in groups.items():
        for p in pages:
            with page_cols[idx]:
                is_active = (active_page_title is not None
                             and getattr(p, "title", None) == active_page_title)
                if is_active:
                    st.markdown('<div class="gl-active">', unsafe_allow_html=True)
                st.page_link(
                    p,
                    label=getattr(p, "title", str(p)),
                    icon=getattr(p, "icon", None),
                    use_container_width=True,
                )
                if is_active:
                    st.markdown('</div>', unsafe_allow_html=True)
            idx += 1

    st.markdown('</div>', unsafe_allow_html=True)


def inject_sidebar_action_buttons(manual_page=None, reset_key: str = "_gl_reset",
                                  manual_key: str = "_gl_manual"):
    """Render real 重整 + 手冊 buttons in the sidebar (below system-health card).

    Args:
        manual_page: st.Page object for the 使用手冊 page, or a path string.
            If None, manual button triggers st.rerun() as a noop fallback.
        reset_key / manual_key: unique widget keys to avoid collisions.
    """
    with st.sidebar:
        st.markdown('<div class="gl-sidebtn-row">', unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="small")
        with c1:
            if st.button("🔄 重整", key=reset_key, use_container_width=True,
                         help="清除快取並重新載入儀表板資料"):
                st.cache_data.clear()
                # Give users visible feedback — otherwise "nothing happens" UX
                st.toast("✅ 快取已清除 · 重新載入中…", icon="🔄")
                st.rerun()
        with c2:
            if st.button("❓ 手冊", key=manual_key, use_container_width=True,
                         help="查看使用手冊與白話解說"):
                if manual_page is not None:
                    try:
                        st.switch_page(manual_page)
                    except Exception:
                        st.toast("找不到手冊頁。", icon="⚠️")
                else:
                    st.toast("手冊頁未註冊。", icon="⚠️")
        st.markdown('</div>', unsafe_allow_html=True)
