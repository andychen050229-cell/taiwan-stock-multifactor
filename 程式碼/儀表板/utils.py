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
    # v11.5.11 — "amber" role retired from warm amber to cool violet-400
    # so the dark cockpit palette stays unified.  The key name is kept for
    # backwards compatibility with every tone="amber" caller across pages.
    "amber":           "#a78bfa",
    "rose":            "#f43f5e",
    "indigo":          "#4f46e5",
    # gradients
    "grad_primary":    "linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)",
    "grad_tech":       "linear-gradient(135deg, #06b6d4 0%, #2563eb 50%, #7c3aed 100%)",
    "grad_success":    "linear-gradient(135deg, #10b981 0%, #06b6d4 100%)",
    # v11.5.11 — "grad_warm" repurposed to a cool violet→rose duo so it
    # still reads "attention" but no longer clashes with the dark panels.
    "grad_warm":       "linear-gradient(135deg, #a78bfa 0%, #f43f5e 100%)",
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
    /* 4. Tables / DataFrames — refined per design-system st-tbl           */
    /* ================================================================= */
    div[data-testid="stDataFrame"], div[data-testid="stTable"] {{
        border: 1px solid var(--gl-border);
        border-radius: 12px;
        overflow: hidden;
        box-shadow: var(--gl-shadow-sm);
        background: var(--gl-surface);
        transition: box-shadow .25s var(--gl-ease), border-color .25s var(--gl-ease);
    }}
    div[data-testid="stDataFrame"]:hover, div[data-testid="stTable"]:hover {{
        border-color: rgba(37,99,235,0.22) !important;
        box-shadow: var(--gl-shadow-glow);
    }}
    div[data-testid="stDataFrame"] thead tr th,
    div[data-testid="stTable"] thead tr th {{
        background: var(--gl-tint) !important;
        color: var(--gl-text-2) !important;
        font-family: var(--gl-font-mono) !important;
        font-weight: 700 !important;
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        border-bottom: 1px solid var(--gl-border) !important;
        padding: 10px 12px !important;
    }}
    div[data-testid="stDataFrame"] tbody tr td,
    div[data-testid="stTable"] tbody tr td {{
        font-family: var(--gl-font-mono) !important;
        font-variant-numeric: tabular-nums;
        font-size: 0.84rem !important;
        color: var(--gl-text) !important;
        border-bottom: 1px solid var(--gl-border) !important;
        padding: 9px 12px !important;
    }}
    div[data-testid="stDataFrame"] tbody tr:hover td,
    div[data-testid="stTable"] tbody tr:hover td {{
        background: rgba(37,99,235,0.03) !important;
    }}
    /* Native HTML tables in markdown (for case-study / methodology blocks) */
    .gl-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.86rem;
        background: var(--gl-surface);
        border: 1px solid var(--gl-border);
        border-radius: 12px;
        overflow: hidden;
        box-shadow: var(--gl-shadow-sm);
    }}
    .gl-table thead th {{
        background: var(--gl-tint);
        color: var(--gl-text-2);
        font-family: var(--gl-font-mono);
        font-weight: 700;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        text-align: left;
        padding: 10px 12px;
        border-bottom: 1px solid var(--gl-border);
    }}
    .gl-table tbody td {{
        font-family: var(--gl-font-mono);
        font-variant-numeric: tabular-nums;
        padding: 9px 12px;
        border-bottom: 1px solid var(--gl-border);
        color: var(--gl-text);
    }}
    .gl-table tbody tr:hover td {{
        background: rgba(37,99,235,0.03);
    }}
    .gl-table tbody tr:last-child td {{ border-bottom: none; }}
    .gl-table .cell-up   {{ color: var(--gl-emerald); font-weight: 600; }}
    .gl-table .cell-down {{ color: var(--gl-rose);    font-weight: 600; }}
    .gl-table .cell-ticker {{ color: var(--gl-blue); font-weight: 700; }}
    .gl-table .cell-dim  {{ color: var(--gl-text-3); }}
    /* Section-header accent bar (matches design-system .sh h2) */
    .gl-section-head {{
        display: flex; align-items: baseline; justify-content: space-between;
        margin: 22px 0 12px;
    }}
    .gl-section-head h2 {{
        font-size: 1.35rem; font-weight: 700; letter-spacing: -0.01em;
        position: relative; padding-left: 14px; color: var(--gl-text);
    }}
    .gl-section-head h2::before {{
        content: ""; position: absolute; left: 0; top: 5px; bottom: 5px;
        width: 4px; background: var(--gl-grad-pri); border-radius: 4px;
    }}
    .gl-section-head .sub {{
        font-size: 12px; color: var(--gl-text-3);
        font-family: var(--gl-font-mono);
    }}
    /* Chip-explainer grid (used on hero blocks for per-chip rationale) */
    .gl-chip-explain {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px; margin-top: 14px;
    }}
    .gl-chip-explain .item {{
        background: rgba(255,255,255,0.72);
        border: 1px solid var(--gl-border);
        border-left: 3px solid var(--gl-blue);
        border-radius: 10px;
        padding: 10px 14px;
        transition: all .25s var(--gl-ease);
    }}
    .gl-chip-explain .item:hover {{
        border-left-color: var(--gl-violet);
        box-shadow: var(--gl-shadow-glow);
        transform: translateY(-1px);
    }}
    .gl-chip-explain .item .head {{
        font-family: var(--gl-font-mono);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--gl-blue);
        margin-bottom: 4px;
    }}
    .gl-chip-explain .item.vio .head {{ color: var(--gl-violet); }}
    .gl-chip-explain .item.vio {{ border-left-color: var(--gl-violet); }}
    .gl-chip-explain .item.ok  .head {{ color: var(--gl-emerald); }}
    .gl-chip-explain .item.ok  {{ border-left-color: var(--gl-emerald); }}
    .gl-chip-explain .item.warn .head {{ color: var(--gl-amber); }}
    .gl-chip-explain .item.warn {{ border-left-color: var(--gl-amber); }}
    .gl-chip-explain .item .desc {{
        font-size: 0.82rem;
        color: var(--gl-text-2);
        line-height: 1.55;
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
    /* v11 §4a — Insight / status callout boxes repainted as Glint dark
       terminal cards. Previous pastel backgrounds (#eff6ff / #ede9fe /
       #ecfdf5 / #fff1f2) rendered as washed-out islands on the mostly
       dark canvas and caused the "yellow-on-yellow invisible text" bug
       when a nested strong inherited the light tone. Dark-bg + kind-
       specific accent text keeps every callout readable AND on-brand. */
    .insight-box, .gl-box-info {{
        background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(10,20,32,0.92) 100%);
        border: 1px solid rgba(103,232,249,0.30);
        border-left: 3px solid #67e8f9;
        border-radius: 10px;
        padding: 14px 18px;
        margin: 12px 0;
        font-size: 0.9rem;
        color: #cffafe;
        box-shadow: 0 2px 10px rgba(2,6,23,0.28), inset 0 1px 0 rgba(103,232,249,0.12);
    }}
    .insight-box strong, .gl-box-info strong {{ color: #e0f9ff; font-weight: 700; }}
    .warning-box, .gl-box-warn {{
        background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(10,20,32,0.92) 100%);
        border: 1px solid rgba(167,139,250,0.40);
        border-left: 3px solid #a78bfa;
        border-radius: 10px;
        padding: 14px 18px;
        margin: 12px 0;
        font-size: 0.9rem;
        color: #ddd6fe;
        box-shadow: 0 2px 10px rgba(2,6,23,0.28), inset 0 1px 0 rgba(167,139,250,0.10);
    }}
    .warning-box strong, .gl-box-warn strong {{ color: #ede9fe; font-weight: 700; }}
    .success-box, .gl-box-ok {{
        background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(10,20,32,0.92) 100%);
        border: 1px solid rgba(16,185,129,0.40);
        border-left: 3px solid #10b981;
        border-radius: 10px;
        padding: 14px 18px;
        margin: 12px 0;
        font-size: 0.9rem;
        color: #a7f3d0;
        box-shadow: 0 2px 10px rgba(2,6,23,0.28), inset 0 1px 0 rgba(16,185,129,0.10);
    }}
    .success-box strong, .gl-box-ok strong {{ color: #d1fae5; font-weight: 700; }}
    .gl-box-danger {{
        background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(10,20,32,0.92) 100%);
        border: 1px solid rgba(244,63,94,0.40);
        border-left: 3px solid #f43f5e;
        border-radius: 10px;
        padding: 14px 18px;
        margin: 12px 0;
        font-size: 0.9rem;
        color: #fecaca;
        box-shadow: 0 2px 10px rgba(2,6,23,0.28), inset 0 1px 0 rgba(244,63,94,0.10);
    }}
    .gl-box-danger strong {{ color: #fde0e0; font-weight: 700; }}
    /* Legacy code/ticker chips inside these dark callouts need a visible bg */
    .insight-box code, .gl-box-info code,
    .warning-box code, .gl-box-warn code,
    .success-box code, .gl-box-ok code,
    .gl-box-danger code {{
        background: rgba(103,232,249,0.14) !important;
        color: #e8f7fc !important;
        border: 1px solid rgba(103,232,249,0.22);
        border-radius: 5px;
        padding: 1px 6px;
        font-family: var(--gl-font-mono);
        font-size: 0.84em;
    }}
    /* Degraded-mode banner — 優雅降級提示（非錯誤，而是摘要版模式） */
    .gl-degraded {{
        background: var(--gl-surface);
        border: 1px solid var(--gl-border);
        border-left: 4px solid var(--gl-amber);
        border-radius: 0 12px 12px 0;
        padding: 14px 18px;
        margin: 16px 0 20px;
        box-shadow: var(--gl-shadow-sm);
    }}
    .gl-degraded-blue  {{ border-left-color: var(--gl-blue); }}
    .gl-degraded-rose  {{ border-left-color: var(--gl-rose); }}
    .gl-degraded-head {{
        font-size: 0.95rem;
        color: var(--gl-text);
        margin-bottom: 6px;
        font-weight: 600;
    }}
    .gl-degraded-body {{
        font-size: 0.86rem;
        color: var(--gl-text-2);
        line-height: 1.6;
        margin-bottom: 8px;
    }}
    .gl-degraded-kv {{
        display: flex;
        align-items: flex-start;
        gap: 10px;
        font-size: 0.8rem;
        color: var(--gl-text-2);
        line-height: 1.55;
        padding: 4px 0;
    }}
    .gl-degraded-kv span {{
        flex: 0 0 70px;
        font-family: var(--gl-font-mono);
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--gl-text-3);
        padding-top: 2px;
    }}
    /* Chart note — 1-2 行短 insight，放在圖下 */
    .gl-chart-note {{
        font-family: var(--gl-font-sans);
    }}
    .gl-chart-note b {{
        color: var(--gl-text);
        font-weight: 600;
    }}
    /* Page heading — 統一的分頁 h1 + command-center 副標 */
    .gl-page-heading {{
        --gl-page-accent: var(--gl-blue);
        margin: 12px 0 10px 0;
        padding: 18px 22px 16px 22px;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid var(--gl-border);
        border-left: 4px solid var(--gl-page-accent);
        border-radius: 12px;
        box-shadow: 0 1px 2px rgba(15,23,42,0.04);
        position: relative;
        overflow: hidden;
    }}
    .gl-page-heading::after {{
        content: "";
        position: absolute; inset: 0 0 auto auto;
        width: 180px; height: 100%;
        background: radial-gradient(ellipse at top right,
            color-mix(in srgb, var(--gl-page-accent) 12%, transparent) 0%,
            transparent 70%);
        pointer-events: none;
    }}
    .gl-page-heading-title {{
        display: flex; align-items: baseline; flex-wrap: wrap;
        gap: 10px;
        font-family: var(--gl-font-sans);
    }}
    .gl-page-heading-icon {{
        font-size: 1.6rem; line-height: 1;
    }}
    .gl-page-heading-zh {{
        font-size: 1.55rem; font-weight: 700;
        color: var(--gl-text);
        letter-spacing: -0.01em;
    }}
    .gl-page-heading-en {{
        font-family: var(--gl-font-mono);
        font-size: 0.82rem; font-weight: 500;
        color: var(--gl-text-3);
        letter-spacing: 0.02em;
    }}
    .gl-page-heading-cmd {{
        margin-top: 8px;
        display: flex; align-items: center; gap: 8px;
        font-size: 0.92rem;
        color: var(--gl-text-2);
        line-height: 1.5;
    }}
    .gl-page-heading-cmd-dot {{
        display: inline-block;
        width: 7px; height: 7px; border-radius: 50%;
        box-shadow: 0 0 0 3px color-mix(in srgb, currentColor 10%, transparent);
        flex-shrink: 0;
    }}
    /* Trust strip — 一行資料信任條 (Dataset · Samples · Gates …) */
    .gl-trust-strip {{
        display: flex; flex-wrap: wrap; gap: 6px;
        margin: 10px 0 14px 0;
        padding: 8px 10px;
        background: #ffffff;
        border: 1px solid var(--gl-border);
        border-radius: 10px;
        box-shadow: 0 1px 2px rgba(15,23,42,0.03);
        font-family: var(--gl-font-sans);
    }}
    .gl-trust-cell {{
        display: inline-flex; align-items: center; gap: 6px;
        padding: 5px 11px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 999px;
        font-size: 0.78rem;
        line-height: 1;
    }}
    .gl-trust-k {{
        color: var(--gl-text-3);
        font-size: 0.7rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 600;
    }}
    .gl-trust-v {{
        font-family: var(--gl-font-mono);
        color: var(--gl-text);
        font-weight: 600;
    }}
    .gl-trust-blue    {{ border-color: rgba(37,99,235,0.25);   background: rgba(37,99,235,0.05); }}
    .gl-trust-violet  {{ border-color: rgba(124,58,237,0.25);  background: rgba(124,58,237,0.05); }}
    .gl-trust-cyan    {{ border-color: rgba(6,182,212,0.25);   background: rgba(6,182,212,0.05); }}
    .gl-trust-emerald {{ border-color: rgba(16,185,129,0.25);  background: rgba(16,185,129,0.05); }}
    .gl-trust-amber   {{ border-color: rgba(167,139,250,0.25);  background: rgba(167,139,250,0.05); }}
    .gl-trust-rose    {{ border-color: rgba(244,63,94,0.25);   background: rgba(244,63,94,0.05); }}
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
    .gl-chip.warn     {{ background: rgba(167,139,250,0.08); color: var(--gl-amber);   border-color: rgba(167,139,250,0.2); }}
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
    .gl-pillar[data-p="event"] {{ background: #ede9fe; color: #92400e; }}
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
    /* v10 §12.2 — meta strip repainted as a dark-terminal sibling to the
       utility bar. Previously this was a light glass panel which felt like
       a separate widget; now it extends the shell's dark palette so the
       utility bar + primary nav + secondary nav + meta strip read as one
       stacked instrument header. */
    .gl-topbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 16px;
        background: linear-gradient(180deg, rgba(10,20,32,0.88) 0%, rgba(8,16,32,0.88) 100%);
        border: 1px solid rgba(103,232,249,0.22);
        border-radius: 10px;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        margin-bottom: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.22), inset 0 1px 0 rgba(103,232,249,0.10);
        font-size: 0.80rem;
        font-family: var(--gl-font-mono);
    }}
    .gl-topbar-l {{
        display: flex;
        align-items: center;
        gap: 10px;
        color: #8397ac;
        letter-spacing: 0.04em;
    }}
    /* Overlay the inline color specified by render_topbar — v10 §12.2
       wants muted breadcrumb root and bright current-page crumb. */
    .gl-topbar-l span:first-child {{ color: #8397ac !important; }}
    .gl-topbar-l span:nth-child(2) {{ color: #5B7186 !important; }}
    .gl-topbar-l span:last-child {{ color: #E8F7FC !important; font-weight: 700 !important; }}
    .gl-topbar-l .gl-slash {{ color: #5B7186; }}
    .gl-topbar-l .gl-crumb-cur {{ color: #E8F7FC; font-weight: 700; }}
    .gl-topbar-r {{
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: var(--gl-font-mono);
        font-size: 0.70rem;
        color: #8397ac;
    }}
    .gl-topbar-r .gl-sep {{ opacity: .4; }}
    /* Meta-strip clock — mono tabular, cyan, subtle */
    .gl-topbar-r #gl-clock {{
        background: rgba(6,10,18,0.65) !important;
        color: #67e8f9 !important;
        border: 1px solid rgba(103,232,249,0.28) !important;
        font-family: var(--gl-font-mono) !important;
        letter-spacing: 0.04em !important;
    }}
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
    .gl-pb-pill[data-p="event"] {{ background: #ede9fe; color: #92400e; }}
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
    .gl-pb-bar[data-p="event"] {{ background: linear-gradient(90deg, #14b8a6 0%, #5eead4 100%); box-shadow: 0 0 8px rgba(20,184,166,0.3); }}
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
    .path-card.path-inv::before {{ background: linear-gradient(135deg, #a78bfa 0%, #7c3aed 100%) !important; }}
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
    /* 6. 多因子股票分析系統 — sidebar brand + system health card       */
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
    .gl-brand-subtitle {{
        margin-top: 6px;
        font-family: var(--gl-font-sans);
        font-size: 0.72rem;
        color: #9fb7c6 !important;
        letter-spacing: 0.02em;
        line-height: 1.45;
        font-weight: 500;
        opacity: 0.92;
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
    /* v11.5.12 — smooth, organic frame breathing.
       Three fixes over the v11.5.10 version that felt janky:
       1. MATCHED shadow-layer counts (4 layers in both 0% and 50%) so
          the browser can interpolate each layer continuously.  When
          layer counts differ, browsers can't tween the missing layer
          and the animation snaps at the transition.
       2. GENTLER amplitude (border 0.30→0.70, 2.3× swing instead of
          3.5×) so the effect reads as breathing rather than flashing.
       3. Base layers never drop to 0 opacity — they fade down to low
          but non-zero values so the halo is always subtly present
          and grows/recedes smoothly rather than popping on/off. */
    @keyframes gl-frame-breathe {{
        0%, 100% {{
            border-color: rgba(103,232,249,0.30);
            box-shadow:
                0 0 0 0 rgba(103,232,249,0.04),
                0 0 12px 0 rgba(103,232,249,0.14),
                0 0 24px 0 rgba(103,232,249,0.06),
                inset 0 1px 0 rgba(103,232,249,0.08);
        }}
        50% {{
            border-color: rgba(103,232,249,0.70);
            box-shadow:
                0 0 0 1px rgba(103,232,249,0.22),
                0 0 22px 0 rgba(103,232,249,0.36),
                0 0 42px 0 rgba(103,232,249,0.16),
                inset 0 1px 0 rgba(103,232,249,0.18);
        }}
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
        /* v11.5.12 — 4.8s cubic-bezier sine-like curve (the natural breath
           curve) + will-change hint so the compositor keeps the element on
           its own layer and box-shadow repaints no longer fight the conic
           gradient ring for paint bandwidth. */
        animation: gl-frame-breathe 4.8s cubic-bezier(0.445, 0.050, 0.550, 0.950) infinite;
        will-change: border-color, box-shadow;
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
    .gl-signal.amber::before  {{ background: linear-gradient(180deg, #a78bfa, #f43f5e); }}
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
    .gl-signal.amber .gl-signal-light {{ background: #a78bfa; box-shadow: 0 0 12px rgba(167,139,250,0.5); }}
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
    .gl-sector[data-s="傳產"]      {{ background: #ede9fe; color: #92400e; }}
    .gl-sector[data-s="傳產"]::before {{ background: #a78bfa; }}
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
    /* ARCHITECTURAL NOTE (fix for 看不出任何東西 bug 2026-04-20):
       st.markdown('<div class="gl-topnav">') is AUTO-CLOSED by Streamlit's
       markdown sanitizer — the <div> cannot span sibling st.columns/st.page_link
       calls. So `.gl-topnav [data-testid="stPageLink-NavLink"]` matched NOTHING.
       Since render_top_nav is the ONLY site that emits st.page_link, we target
       stPageLink-NavLink globally. Active state uses aria-current="page"
       (set by Streamlit natively on the current page-link). The .gl-topnav
       div is kept only as a decorative band above the horizontal blocks. */

    /* Decorative dark band (empty marker div — visually covers nav area via
       :has() extending into the sibling horizontal blocks) */
    .gl-topnav {{
        position: sticky;
        top: 0;
        z-index: 40;
        background:
            radial-gradient(140% 90% at 0% 0%, rgba(6,182,212,0.16), transparent 55%),
            radial-gradient(120% 80% at 100% 100%, rgba(37,99,235,0.14), transparent 60%),
            linear-gradient(180deg, #0a1420 0%, #101c2d 55%, #0c1725 100%);
        border: 1px solid rgba(6,182,212,0.25);
        border-bottom: none;
        border-radius: 14px 14px 0 0;
        padding: 14px 14px 2px 14px;
        margin: -0.5rem -1rem 0 -1rem;
        box-shadow:
            0 -6px 18px rgba(2,6,23,0.15) inset,
            inset 0 1px 0 rgba(6,182,212,0.22);
        overflow: hidden;
        min-height: 28px;
    }}
    .gl-topnav::before {{
        content: "";
        position: absolute;
        inset: 0;
        background-image:
            linear-gradient(rgba(6,182,212,0.06) 1px, transparent 1px),
            linear-gradient(90deg, rgba(6,182,212,0.06) 1px, transparent 1px);
        background-size: 28px 28px;
        pointer-events: none;
        opacity: 0.55;
    }}
    .gl-topnav::after {{
        content: "";
        position: absolute;
        top: 0; left: 10%; right: 10%;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(103,232,249,0.85), rgba(37,99,235,0.55), transparent);
        box-shadow: 0 0 8px rgba(103,232,249,0.5);
    }}
    /* Extend the dark band into the next 2 sibling horizontal blocks using
       :has() — these are the group-label row and page-link row that Streamlit
       renders as siblings (NOT children) of the .gl-topnav marker. */
    div[data-testid="stElementContainer"]:has(.gl-topnav)
        + div[data-testid="stHorizontalBlock"],
    div[data-testid="stElementContainer"]:has(.gl-topnav)
        + div[data-testid="stHorizontalBlock"]
        + div[data-testid="stHorizontalBlock"] {{
        background:
            radial-gradient(120% 80% at 100% 100%, rgba(37,99,235,0.08), transparent 60%),
            linear-gradient(180deg, #101c2d 0%, #0f1a28 100%) !important;
        border-left: 1px solid rgba(6,182,212,0.25) !important;
        border-right: 1px solid rgba(6,182,212,0.25) !important;
        margin-left: -1rem !important;
        margin-right: -1rem !important;
        padding: 0 14px !important;
        position: relative;
        z-index: 39;
    }}
    /* Close off the bottom of the dark band on the page-link row (2nd block) */
    div[data-testid="stElementContainer"]:has(.gl-topnav)
        + div[data-testid="stHorizontalBlock"]
        + div[data-testid="stHorizontalBlock"] {{
        border-bottom: 1px solid rgba(6,182,212,0.25) !important;
        border-radius: 0 0 14px 14px !important;
        padding-bottom: 14px !important;
        margin-bottom: 22px !important;
        box-shadow: 0 10px 28px rgba(2,6,23,0.28);
    }}

    /* Group label — cyan mono eyebrow */
    .gl-topnav-gname {{
        font-family: var(--gl-font-mono);
        font-size: 0.64rem;
        color: #67e8f9 !important;
        letter-spacing: 0.20em;
        font-weight: 700;
        text-transform: uppercase;
        padding: 6px 6px 8px 10px;
        position: relative;
        text-shadow: 0 0 8px rgba(103,232,249,0.4);
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
        box-shadow: 0 0 6px rgba(103,232,249,0.65);
    }}

    /* ---- Page-link pills — GLOBAL (drop .gl-topnav prefix) ------------- */
    /* render_top_nav is the only st.page_link caller, so these are safe
       globally. Selector list covers Streamlit DOM variations. */
    /* v11.5.12 — smooth breathing border animation.
       Matched shadow-layer counts (5 both sides) so interpolation is
       continuous; amplitude tamed so it reads as a breath rather than
       a flash (border 0.28 → 0.72, 2.6× swing). */
    @keyframes gl-topnav-breathe {{
        0%, 100% {{
            border-color: rgba(103,232,249,0.28);
            box-shadow:
                inset 0 1px 0 rgba(103,232,249,0.14),
                0 0 0 0 rgba(103,232,249,0.02),
                0 0 10px 0 rgba(103,232,249,0.08),
                0 0 20px 0 rgba(103,232,249,0.04),
                0 1px 2px rgba(0,0,0,0.35);
        }}
        50% {{
            border-color: rgba(103,232,249,0.72);
            box-shadow:
                inset 0 1px 0 rgba(103,232,249,0.22),
                0 0 0 1px rgba(103,232,249,0.20),
                0 0 20px 0 rgba(103,232,249,0.30),
                0 0 34px 0 rgba(103,232,249,0.14),
                0 1px 2px rgba(0,0,0,0.35);
        }}
    }}
    a[data-testid="stPageLink-NavLink"],
    a[data-testid="stPageLink"],
    div[data-testid="stPageLink"] > a {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 7px !important;
        padding: 10px 12px !important;
        border-radius: 10px !important;
        border: 1px solid rgba(103,232,249,0.28) !important;
        background: linear-gradient(180deg, rgba(18,35,58,0.92), rgba(10,22,40,0.96)) !important;
        font-family: var(--gl-font-sans) !important;
        font-size: 0.86rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em !important;
        color: #f1f9ff !important;
        transition: all .22s ease !important;
        box-shadow:
            inset 0 1px 0 rgba(103,232,249,0.14),
            0 1px 2px rgba(0,0,0,0.35) !important;
        position: relative !important;
        overflow: hidden !important;
        white-space: nowrap !important;
        text-overflow: ellipsis !important;
        min-height: 40px !important;
        line-height: 1.2 !important;
        text-decoration: none !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.55) !important;
        /* v11.5.12 — sine-curve easing + will-change for smooth breath */
        animation: gl-topnav-breathe 4.8s cubic-bezier(0.445, 0.050, 0.550, 0.950) infinite;
        will-change: border-color, box-shadow;
    }}
    /* Force all descendants (p, span, svg text) to inherit bright color */
    a[data-testid="stPageLink-NavLink"] *,
    a[data-testid="stPageLink"] *,
    div[data-testid="stPageLink"] > a *,
    a[data-testid="stPageLink-NavLink"] p,
    a[data-testid="stPageLink"] p,
    a[data-testid="stPageLink-NavLink"] span,
    a[data-testid="stPageLink"] span {{
        color: inherit !important;
        font-weight: inherit !important;
        font-size: inherit !important;
        letter-spacing: inherit !important;
        margin: 0 !important;
        background: transparent !important;
    }}
    /* Hover */
    a[data-testid="stPageLink-NavLink"]:hover,
    a[data-testid="stPageLink"]:hover,
    div[data-testid="stPageLink"] > a:hover {{
        border-color: rgba(103,232,249,0.8) !important;
        background: linear-gradient(180deg, rgba(6,182,212,0.24), rgba(37,99,235,0.16)) !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
        box-shadow:
            0 8px 22px rgba(6,182,212,0.38),
            inset 0 1px 0 rgba(255,255,255,0.14),
            0 0 0 1px rgba(103,232,249,0.32) !important;
        animation: none !important;  /* v11.5.9 · freeze breath on hover */
    }}
    /* Keyboard focus */
    a[data-testid="stPageLink-NavLink"]:focus-visible,
    a[data-testid="stPageLink"]:focus-visible,
    div[data-testid="stPageLink"] > a:focus-visible {{
        outline: 2px solid #67e8f9 !important;
        outline-offset: 2px !important;
    }}
    /* Active page — Streamlit natively sets aria-current="page" on the link.
       This replaces the unreliable .gl-active wrapper (which was auto-closed). */
    a[data-testid="stPageLink-NavLink"][aria-current="page"],
    a[data-testid="stPageLink"][aria-current="page"],
    div[data-testid="stPageLink"] > a[aria-current="page"],
    /* Defensive fallback: kept in case older Streamlit omits aria-current */
    .gl-active a[data-testid="stPageLink-NavLink"],
    .gl-active a[data-testid="stPageLink"] {{
        background: linear-gradient(180deg, rgba(103,232,249,0.34), rgba(37,99,235,0.22)) !important;
        border-color: rgba(103,232,249,1) !important;
        color: #ffffff !important;
        box-shadow:
            0 0 0 1px rgba(103,232,249,0.48),
            0 6px 22px rgba(6,182,212,0.5),
            inset 0 1px 0 rgba(255,255,255,0.2) !important;
        text-shadow: 0 0 10px rgba(103,232,249,0.75), 0 1px 2px rgba(0,0,0,0.55) !important;
        animation: none !important;  /* v11.5.9 · active page uses strong sweep, no breath */
    }}
    a[data-testid="stPageLink-NavLink"][aria-current="page"]::before,
    a[data-testid="stPageLink"][aria-current="page"]::before,
    div[data-testid="stPageLink"] > a[aria-current="page"]::before {{
        content: "";
        position: absolute;
        left: 0; top: 0; bottom: 0;
        width: 3px;
        background: linear-gradient(180deg, #67e8f9 0%, #2563eb 100%);
        border-radius: 2px 0 0 2px;
        box-shadow: 0 0 8px rgba(103,232,249,0.8);
    }}
    a[data-testid="stPageLink-NavLink"][aria-current="page"]::after,
    a[data-testid="stPageLink"][aria-current="page"]::after,
    div[data-testid="stPageLink"] > a[aria-current="page"]::after {{
        content: "";
        position: absolute;
        top: 0; bottom: 0;
        left: -60%;
        width: 50%;
        background: linear-gradient(90deg, transparent, rgba(103,232,249,0.26), transparent);
        animation: gl-topnav-sweep 3.5s ease-in-out infinite;
        pointer-events: none;
    }}
    @keyframes gl-topnav-sweep {{
        0%   {{ left: -60%; }}
        60%  {{ left: 120%; }}
        100% {{ left: 120%; }}
    }}
    /* Icon tint — cyan glow on both emoji + material glyphs */
    a[data-testid="stPageLink-NavLink"] [data-testid="stIconMaterial"],
    a[data-testid="stPageLink"] [data-testid="stIconMaterial"] {{
        color: #67e8f9 !important;
        text-shadow: 0 0 6px rgba(103,232,249,0.5) !important;
    }}
    /* Group divider */
    .gl-topnav-sep {{
        width: 1px;
        background: linear-gradient(180deg, transparent, rgba(103,232,249,0.35), transparent);
        margin: 0 6px;
        min-height: 56px;
    }}

    /* ================================================================= */
    /*  7b. v4 audit §5 — 3-layer top-nav: Utility Bar + Primary + Secondary */
    /* ================================================================= */
    /* v9 §4 — Shell root safe top spacing: never let utility bar clip against
       viewport top. Also ensure no Streamlit parent clips the sticky header. */
    section.main > div.block-container,
    [data-testid="stAppViewContainer"] [data-testid="stMain"] .block-container {{
        padding-top: max(12px, env(safe-area-inset-top, 12px)) !important;
    }}
    [data-testid="stVerticalBlock"]:has(> div > .gl-utilbar-marker),
    [data-testid="stVerticalBlock"]:has(> .gl-utilbar-marker) {{
        overflow: visible !important;
    }}

    /* ============================================================
       v10 §6 — Utility Bar shell (columns-backed, functional Search)
       The render function now emits a marker div + a 3-column
       stHorizontalBlock; the outer VerticalBlock is promoted to the
       sticky terminal-style shell via :has() so the visual contract
       from v8/v9 is preserved but the CENTER zone becomes a real
       Streamlit selectbox for ticker search.
       ============================================================ */
    [data-testid="stVerticalBlock"]:has(> div > .gl-utilbar-marker) {{
        margin: 6px -1rem 0 -1rem;
        padding: 10px 14px;
        min-height: 56px;
        background:
            linear-gradient(180deg, #050b15 0%, #081020 55%, #060d1a 100%);
        border: 1px solid rgba(6,182,212,0.35);
        border-bottom: 1px solid rgba(6,182,212,0.14);
        border-radius: 14px 14px 0 0;
        font-family: var(--gl-font-mono);
        font-size: 0.70rem;
        line-height: 1.75;
        letter-spacing: 0.04em;
        color: #b4ccdf;
        box-shadow: inset 0 1px 0 rgba(103,232,249,0.18);
        position: sticky;
        top: 0;
        z-index: 41;
        overflow: visible;
    }}
    /* Marker is 0-height — it only exists to anchor the :has() selector */
    .gl-utilbar-marker {{ display: none !important; }}
    /* Horizontal columns row inside the bar shell — align vertically, no gap bleed */
    [data-testid="stVerticalBlock"]:has(> div > .gl-utilbar-marker)
        > div[data-testid="stHorizontalBlock"] {{
        align-items: center !important;
        gap: 14px !important;
        padding: 0 !important;
        margin: 0 !important;
    }}
    /* Each column: no vertical padding so the bar stays 44px */
    [data-testid="stVerticalBlock"]:has(> div > .gl-utilbar-marker)
        > div[data-testid="stHorizontalBlock"]
        > div[data-testid="column"] {{
        padding: 0 !important;
    }}
    /* LEFT / RIGHT inline HTML wrappers
       v11.1 §1 — prevent BOTH horizontal AND vertical truncation:
       · flex-wrap: nowrap + overflow-x: clip so chips always render in a
         single row and the last chip never gets clipped at viewport edge
       · overflow-y: visible so descenders/ascenders aren't top/bottom-cut
         when the shell is 56px (previously 44 clipped text vertically)
       · tighter font-size + padding so Model/Gates/PASS/DSR fit at 1280px */
    .gl-util-left {{
        display: inline-flex;
        flex-wrap: nowrap;
        align-items: center;
        justify-content: flex-start;
        min-width: 0;
        max-width: 100%;
        width: 100%;
        overflow-x: clip;
        overflow-y: visible;
        line-height: 1.75;
    }}
    .gl-util-right {{
        display: inline-flex;
        flex-wrap: nowrap;
        align-items: center;
        justify-content: flex-end;
        gap: 4px;
        min-width: 0;
        max-width: 100%;
        width: 100%;
        overflow-x: clip;
        overflow-y: visible;
        line-height: 1.75;
    }}
    .gl-util-seg {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 4px 10px;
        border-right: 1px solid rgba(6,182,212,0.18);
        white-space: nowrap;
        flex-shrink: 0;
        line-height: 1.6;
    }}
    .gl-util-left .gl-util-seg:last-child {{ border-right: none; }}
    .gl-util-right .gl-util-seg {{ border-right: none; padding: 4px 6px; }}
    /* v11 §1 — shrink LEFT seg padding further and the RIGHT monospace chip
       font so the full right triplet (Model · Gates N/N PASS · DSR) fits
       even at 1280px viewport without clipping. */
    .gl-util-right .gl-util-k {{ font-size: 0.64rem; }}
    .gl-util-right .gl-util-mono {{ font-size: 0.68rem; letter-spacing: 0.02em; }}
    .gl-util-right .gl-util-chip {{ font-size: 0.62rem; padding: 1px 6px; }}

    /* ============================================================
       v10 §6 — Functional Search widget paint (selectbox as terminal input)
       Scope: only the selectbox inside the .gl-util-search-slot column.
       ============================================================ */
    /* Target the element-container that holds the search marker */
    div[data-testid="stElementContainer"]:has(> div > .gl-util-search-slot) {{
        margin: 0 !important;
        padding: 0 !important;
        height: 0 !important;
        min-height: 0 !important;
    }}
    .gl-util-search-slot {{ display: none !important; }}
    /* The selectbox lives in the SAME column, as a SIBLING after the marker.
       Use :has(~ ...) to promote the column to a search-palette shell. */
    div[data-testid="column"]:has(> div > div > .gl-util-search-slot) {{
        position: relative;
    }}
    div[data-testid="column"]:has(> div > div > .gl-util-search-slot)
        div[data-testid="stSelectbox"] {{
        margin: 0 !important;
        padding: 0 !important;
    }}
    div[data-testid="column"]:has(> div > div > .gl-util-search-slot)
        div[data-testid="stSelectbox"] > div {{
        margin: 0 !important;
        padding: 0 !important;
    }}
    /* The actual select control — BaseWeb wraps it in a nested div[data-baseweb] */
    div[data-testid="column"]:has(> div > div > .gl-util-search-slot)
        div[data-baseweb="select"] > div {{
        background: rgba(103,232,249,0.06) !important;
        border: 1px solid rgba(103,232,249,0.32) !important;
        border-radius: 7px !important;
        min-height: 32px !important;
        height: 32px !important;
        font-family: var(--gl-font-mono) !important;
        font-size: 0.72rem !important;
        letter-spacing: 0.04em !important;
        color: #b4ccdf !important;
        transition: all 0.18s ease !important;
        box-shadow: none !important;
    }}
    div[data-testid="column"]:has(> div > div > .gl-util-search-slot)
        div[data-baseweb="select"] > div:hover {{
        background: rgba(103,232,249,0.10) !important;
        border-color: rgba(103,232,249,0.55) !important;
    }}
    div[data-testid="column"]:has(> div > div > .gl-util-search-slot)
        div[data-baseweb="select"] > div:focus-within {{
        border-color: rgba(103,232,249,0.75) !important;
        box-shadow: 0 0 0 3px rgba(103,232,249,0.18) !important;
    }}
    /* Value text */
    div[data-testid="column"]:has(> div > div > .gl-util-search-slot)
        div[data-baseweb="select"] [data-baseweb="tag"],
    div[data-testid="column"]:has(> div > div > .gl-util-search-slot)
        div[data-baseweb="select"] input,
    div[data-testid="column"]:has(> div > div > .gl-util-search-slot)
        div[data-baseweb="select"] span {{
        color: #e8f7fc !important;
        font-family: var(--gl-font-mono) !important;
    }}
    /* Placeholder look when sentinel is active */
    div[data-testid="column"]:has(> div > div > .gl-util-search-slot)
        div[data-baseweb="select"] span[aria-live] {{
        color: #8397ac !important;
    }}
    /* Caret */
    div[data-testid="column"]:has(> div > div > .gl-util-search-slot)
        div[data-baseweb="select"] svg {{
        color: #67e8f9 !important;
    }}
    /* The popup/dropdown panel — BaseWeb portals this to body, so scope
       by a unique class the widget exposes. Target generic popover menus
       whose option text starts with the sentinel or a digit (ticker). */
    div[data-baseweb="popover"] ul[role="listbox"] {{
        background: #07101c !important;
        border: 1px solid rgba(6,182,212,0.32) !important;
        border-radius: 7px !important;
        box-shadow: 0 8px 26px rgba(0,0,0,0.55) !important;
    }}
    div[data-baseweb="popover"] ul[role="listbox"] li {{
        color: #cbd8e3 !important;
        font-family: var(--gl-font-mono) !important;
        font-size: 0.72rem !important;
        letter-spacing: 0.04em !important;
        padding: 7px 12px !important;
    }}
    div[data-baseweb="popover"] ul[role="listbox"] li:hover,
    div[data-baseweb="popover"] ul[role="listbox"] li[aria-selected="true"] {{
        background: rgba(103,232,249,0.12) !important;
        color: #e8f7fc !important;
    }}
    .gl-util-k {{
        color: #67e8f9;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-size: 0.62rem;
    }}
    .gl-util-v {{
        color: #e8f7fc;
        font-weight: 600;
    }}
    .gl-util-mono {{ font-family: var(--gl-font-mono); }}
    .gl-util-label {{
        color: #e8f7fc;
        font-weight: 800;
        letter-spacing: 0.16em;
        font-size: 0.64rem;
    }}
    .gl-util-dot {{
        width: 8px; height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 2px;
    }}
    .gl-util-live {{
        background: #10b981;
        box-shadow: 0 0 8px rgba(16,185,129,0.8);
        animation: gl-util-pulse 1.6s ease-in-out infinite;
    }}
    .gl-util-snapshot {{
        background: #a78bfa;
        box-shadow: 0 0 6px rgba(167,139,250,0.55);
    }}
    @keyframes gl-util-pulse {{
        0%,100% {{ opacity: 1; }}
        50%     {{ opacity: 0.35; }}
    }}
    .gl-util-chip {{
        display: inline-block;
        padding: 1px 6px;
        border-radius: 4px;
        font-size: 0.58rem;
        font-weight: 800;
        letter-spacing: 0.10em;
        margin-left: 4px;
    }}
    .gl-util-chip.ok {{
        background: rgba(16,185,129,0.16);
        color: #10b981;
        border: 1px solid rgba(16,185,129,0.45);
    }}
    .gl-util-chip.warn {{
        background: rgba(167,139,250,0.16);
        color: #a78bfa;
        border: 1px solid rgba(167,139,250,0.45);
    }}

    /* Primary nav — 4 large group pills (aria-current styles still apply) */
    .gl-primary-nav {{
        display: block;
        padding: 10px 14px 4px 14px;
        margin: 0 -1rem;
        background: linear-gradient(180deg, #0a1420 0%, #101c2d 100%);
        border-left: 1px solid rgba(6,182,212,0.25);
        border-right: 1px solid rgba(6,182,212,0.25);
        position: relative;
        z-index: 40;
    }}
    /* Inherit the sibling stHorizontalBlock that follows .gl-primary-nav */
    div[data-testid="stElementContainer"]:has(.gl-primary-nav)
        + div[data-testid="stHorizontalBlock"] {{
        background: linear-gradient(180deg, #0a1420 0%, #101c2d 100%) !important;
        border-left: 1px solid rgba(6,182,212,0.25) !important;
        border-right: 1px solid rgba(6,182,212,0.25) !important;
        margin-left: -1rem !important;
        margin-right: -1rem !important;
        padding: 0 14px 10px 14px !important;
        position: relative;
        z-index: 39;
    }}
    /* v7 §10 — terminal-tab style (flat top, seamless into content below) */
    .gl-pri-pill a[data-testid="stPageLink-NavLink"],
    .gl-pri-pill a[data-testid="stPageLink"] {{
        min-height: 42px !important;
        font-size: 0.88rem !important;
        letter-spacing: 0.08em !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        background: rgba(10,20,32,0.72) !important;
        border: 1px solid rgba(103,232,249,0.18) !important;
        border-bottom: 1px solid rgba(103,232,249,0.28) !important;
        border-radius: 6px 6px 0 0 !important;
        color: #8397ac !important;
        padding: 8px 14px !important;
        box-shadow: none !important;
        position: relative;
        transition: all .2s ease !important;
    }}
    .gl-pri-pill a[data-testid="stPageLink-NavLink"]:hover,
    .gl-pri-pill a[data-testid="stPageLink"]:hover {{
        background: rgba(15,29,52,0.90) !important;
        color: #b4ccdf !important;
        border-color: rgba(103,232,249,0.35) !important;
    }}
    .gl-pri-active a[data-testid="stPageLink-NavLink"],
    .gl-pri-active a[data-testid="stPageLink"] {{
        background: linear-gradient(180deg, #101c2d 0%, #0f1a28 100%) !important;
        border: 1px solid rgba(103,232,249,0.55) !important;
        /* Seamless bottom — the tab "belongs" to the secondary row below */
        border-bottom: 1px solid transparent !important;
        border-radius: 6px 6px 0 0 !important;
        color: #E8F7FC !important;
        box-shadow:
            0 -2px 0 0 #67E8F9 inset,
            0 -4px 14px rgba(103,232,249,0.30) !important;
    }}
    .gl-pri-active a[data-testid="stPageLink-NavLink"]::before,
    .gl-pri-active a[data-testid="stPageLink"]::before {{
        content: "";
        position: absolute;
        top: -1px; left: 8%; right: 8%;
        height: 2px;
        background: linear-gradient(90deg, transparent, #67E8F9 50%, transparent);
        opacity: 0.85;
    }}

    /* Secondary nav — contextual sub-pills within active group */
    .gl-secondary-nav {{
        display: block;
        padding: 6px 14px 12px 14px;
        margin: 0 -1rem 18px -1rem;
        background: linear-gradient(180deg, #101c2d 0%, #0f1a28 100%);
        border: 1px solid rgba(6,182,212,0.25);
        border-top: 1px dashed rgba(103,232,249,0.22);
        border-radius: 0 0 14px 14px;
        box-shadow: 0 10px 28px rgba(2,6,23,0.28);
        position: relative;
        z-index: 38;
    }}
    div[data-testid="stElementContainer"]:has(.gl-secondary-nav)
        + div[data-testid="stHorizontalBlock"] {{
        background: linear-gradient(180deg, #101c2d 0%, #0f1a28 100%) !important;
        border-left: 1px solid rgba(6,182,212,0.25) !important;
        border-right: 1px solid rgba(6,182,212,0.25) !important;
        border-bottom: 1px solid rgba(6,182,212,0.25) !important;
        border-radius: 0 0 14px 14px !important;
        margin: 0 -1rem 22px -1rem !important;
        padding: 0 14px 12px 14px !important;
        box-shadow: 0 10px 28px rgba(2,6,23,0.28);
        position: relative;
        z-index: 38;
    }}
    /* v11 §2 — sec-nav group label is the page's section title bar. Previous
       1.02rem was too small on a 44px-tall band — the eye reads it as an
       eyebrow label rather than a section header. Now:
         · font-size 1.45rem (scales up to ~23px) — clearly a header
         · bracket rules widened and centered with flex so they mirror the
           label regardless of label length
         · stronger cyan glow (breathing-light effect) to reinforce the
           "LIVE TERMINAL section" feel */
    .gl-sec-gname {{
        display: flex !important;
        align-items: center;
        justify-content: center;
        width: 100%;
        text-align: center;
        font-family: var(--gl-font-mono);
        font-size: 1.45rem;
        color: #e8f9ff;
        font-weight: 800;
        letter-spacing: 0.34em;
        text-transform: uppercase;
        margin: 8px 0 18px 0;
        padding: 12px 0 14px 0;
        border-bottom: 1px dashed rgba(103,232,249,0.32);
        text-shadow:
            0 0 14px rgba(103,232,249,0.55),
            0 0 32px rgba(103,232,249,0.20);
        position: relative;
        animation: gl-sec-breathe 4.8s ease-in-out infinite;
    }}
    @keyframes gl-sec-breathe {{
        0%, 100% {{
            text-shadow:
                0 0 14px rgba(103,232,249,0.55),
                0 0 32px rgba(103,232,249,0.20);
        }}
        50% {{
            text-shadow:
                0 0 22px rgba(103,232,249,0.78),
                0 0 48px rgba(103,232,249,0.32);
        }}
    }}
    .gl-sec-gname::before,
    .gl-sec-gname::after {{
        content: "";
        display: inline-block;
        flex: 0 0 60px;
        height: 1px;
        margin: 0 18px;
        background: linear-gradient(90deg, transparent, rgba(103,232,249,0.70), transparent);
    }}
    .gl-sec-pill a[data-testid="stPageLink-NavLink"],
    .gl-sec-pill a[data-testid="stPageLink"] {{
        min-height: 34px !important;
        font-size: 0.80rem !important;
        font-weight: 600 !important;
        padding: 7px 10px !important;
        background: linear-gradient(180deg, rgba(18,35,58,0.72), rgba(10,22,40,0.80)) !important;
        border-color: rgba(103,232,249,0.20) !important;
    }}
    .gl-sec-active a[data-testid="stPageLink-NavLink"],
    .gl-sec-active a[data-testid="stPageLink"] {{
        background: linear-gradient(180deg, rgba(103,232,249,0.34), rgba(37,99,235,0.22)) !important;
        border-color: rgba(103,232,249,1) !important;
        color: #ffffff !important;
        box-shadow: 0 0 0 1px rgba(103,232,249,0.48), 0 4px 14px rgba(6,182,212,0.38) !important;
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
    /*     v11.5.6 · smaller type + breathing-light tech accent           */
    /* ================================================================= */
    /* v11.5.12 — smooth breathing rhythm.  Matched 4-layer shadows
       on both 0% and 50% keyframes, gentler amplitude, never-fully-
       zero base layers so the glow grows and recedes continuously
       rather than snapping on/off. */
    @keyframes gl-sidebtn-pulse {{
        0%, 100% {{
            box-shadow:
                0 0 0 0 rgba(103,232,249,0.04),
                0 0 8px 0 rgba(103,232,249,0.08),
                0 0 16px 0 rgba(103,232,249,0.04),
                inset 0 0 0 1px rgba(103,232,249,0.10);
            border-color: rgba(103,232,249,0.26);
        }}
        50% {{
            box-shadow:
                0 0 0 1px rgba(103,232,249,0.24),
                0 0 14px 0 rgba(103,232,249,0.34),
                0 0 26px 0 rgba(103,232,249,0.18),
                inset 0 0 0 1px rgba(103,232,249,0.32);
            border-color: rgba(103,232,249,0.70);
        }}
    }}
    @keyframes gl-sidebtn-dot-blink {{
        0%, 100% {{ opacity: 0.35; box-shadow: 0 0 0 0 rgba(103,232,249,0); }}
        50%      {{ opacity: 1.00; box-shadow: 0 0 6px 1px rgba(103,232,249,0.65); }}
    }}
    /* v11.5.8 — shine-sweep travelling across the button face */
    @keyframes gl-sidebtn-shimmer {{
        0%   {{ background-position: -160% 0; }}
        55%  {{ background-position:  160% 0; }}
        100% {{ background-position:  160% 0; }}
    }}
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button {{
        position: relative !important;
        background: linear-gradient(180deg, rgba(14,23,38,0.88), rgba(8,14,24,0.92)) !important;
        border: 1px solid rgba(103,232,249,0.18) !important;
        color: #cfe2ee !important;
        font-family: var(--gl-font-mono, 'JetBrains Mono', ui-monospace, monospace) !important;
        font-size: 0.50rem !important;              /* v11.5.9 · 0.58 → 0.50 so MANUAL always fits */
        font-weight: 700 !important;
        letter-spacing: 0.04em !important;          /* v11.5.9 · tighter tracking */
        text-transform: uppercase !important;
        padding: 4px 6px 4px 13px !important;
        border-radius: 7px !important;
        min-height: 28px !important;
        height: 28px !important;
        line-height: 1 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: clip !important;
        transition: all .2s ease !important;
        /* v11.5.12 — sine-curve easing on the same 4.8s beat as the
           system-health card / top-nav pills so the whole cockpit
           breathes on one organic rhythm. */
        animation: gl-sidebtn-pulse 4.8s cubic-bezier(0.445, 0.050, 0.550, 0.950) infinite !important;
        will-change: border-color, box-shadow !important;
    }}
    /* v11.5.9 — Streamlit renders the button label inside nested
       <div><p>LABEL</p></div>.  Streamlit's default <p> font-size can
       override the button-level font-size, making the MANUAL label
       wrap onto two lines.  Force the inner text elements to inherit
       the tiny 0.50rem and keep them on a single line. */
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button > div,
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button > div > p,
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button p,
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button span,
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button [data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button [data-testid="stMarkdownContainer"] p {{
        font-size: 0.50rem !important;
        letter-spacing: 0.04em !important;
        line-height: 1 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: clip !important;
        max-width: 100% !important;
        margin: 0 !important;
    }}
    /* breathing status-dot on the left edge */
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button::before {{
        content: "";
        position: absolute;
        left: 6px;
        top: 50%;
        transform: translateY(-50%);
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: #67e8f9;
        animation: gl-sidebtn-dot-blink 2.4s ease-in-out infinite;
        pointer-events: none;
        z-index: 2;
    }}
    /* v11.5.8 — travelling shimmer sweep (the "shiny" effect like
       screenshot 2). Low-opacity diagonal gradient animated across the
       full button face. Uses mix-blend-mode: screen so it brightens
       the label text and icon without washing out the background. */
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button::after {{
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 7px;
        background:
            linear-gradient(115deg,
                transparent 0%,
                transparent 38%,
                rgba(255,255,255,0.22) 46%,
                rgba(167,243,208,0.38) 50%,
                rgba(103,232,249,0.32) 54%,
                transparent 62%,
                transparent 100%);
        background-size: 220% 100%;
        background-repeat: no-repeat;
        background-position: -160% 0;
        animation: gl-sidebtn-shimmer 3.8s ease-in-out infinite;
        pointer-events: none;
        mix-blend-mode: screen;
        opacity: 0.90;
        z-index: 1;
    }}
    /* Keep the label/icon above the shimmer overlay */
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button > div,
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button > * {{
        position: relative !important;
        z-index: 3 !important;
    }}
    /* tighten the Material icon + label so MANUAL fits in one line */
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button [data-testid="stIconMaterial"],
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button span[class*="material-symbols"] {{
        font-size: 13px !important;                 /* v11.5.8 · 14 → 13 */
        margin-right: 3px !important;
    }}
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button:hover {{
        background: linear-gradient(180deg, rgba(6,182,212,0.14), rgba(6,182,212,0.06)) !important;
        border-color: rgba(103,232,249,0.55) !important;
        color: #e8f7fc !important;
        transform: translateY(-1px) !important;
        box-shadow:
            0 0 14px 0 rgba(103,232,249,0.32),
            inset 0 0 0 1px rgba(103,232,249,0.28) !important;
        animation: none !important;  /* freeze breath on hover for deliberate feel */
    }}
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button:hover::before {{
        background: #a7f3d0;
        box-shadow: 0 0 8px 1px rgba(167,243,208,0.8);
        animation: none !important;
        opacity: 1;
    }}
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button:hover::after {{
        animation-duration: 1.6s;  /* shimmer speeds up on hover */
        opacity: 1;
    }}
    section[data-testid="stSidebar"] .gl-sidebtn-row [data-testid="stButton"] > button:active {{
        transform: translateY(0) !important;
    }}
    /* v11.5.10 — 3-zone layout spacing: top row (RELOAD + HOME) sits
       flush to the system-health card above it; bottom row (MANUAL
       full-width) gets a small gap under the top row so the two rows
       read as a visually unified 2×1 + 1×2 grid.  MANUAL inherits
       the same breathing/shimmer/dot treatment automatically because
       it still lives inside a .gl-sidebtn-row wrapper. */
    section[data-testid="stSidebar"] .gl-sidebtn-row.gl-sidebtn-top {{
        margin-bottom: 6px !important;
    }}
    section[data-testid="stSidebar"] .gl-sidebtn-row.gl-sidebtn-bottom {{
        margin-top: 0 !important;
    }}
    /* Stagger MANUAL's breath phase by half the cycle so the three
       buttons don't pulse in lockstep — reads more "alive". */
    section[data-testid="stSidebar"] .gl-sidebtn-row.gl-sidebtn-bottom [data-testid="stButton"] > button {{
        animation-delay: -2.4s !important;  /* v11.5.12 · half of 4.8s */
    }}
    /* ================================================================= */
    /* 10. v7 Dark-Terminal tokens (surface layer — panels / banners)    */
    /* ================================================================= */
    :root {{
        --gl-bg-root:     #060A12;   /* App canvas — under everything       */
        --gl-bg-shell:    #0A1420;   /* Shell / chrome                      */
        --gl-bg-panel:    #0F1725;   /* Default panel surface               */
        --gl-bg-card:     #111B2B;   /* Card surface                        */
        --gl-bg-elevated: #152235;   /* Elevated card (hovered / active)    */
        --gl-fg-primary:  #E8F7FC;   /* High-contrast text                  */
        --gl-fg-muted:    #B4CCDF;   /* Body text                           */
        --gl-fg-dim:      #8397AC;   /* Tertiary / caption text             */
        --gl-cyan-bright: #67E8F9;
        --gl-cyan-core:   #06B6D4;
        --gl-border-dim:  rgba(103,232,249,0.12);
        --gl-border-acc:  rgba(103,232,249,0.28);
    }}
    /* ================================================================= */
    /* 11. Terminal banner (render_terminal_banner)                       */
    /* ================================================================= */
    .gl-term-banner {{
        background: var(--tb-bg);
        border: 1px solid var(--tb-border);
        border-left: 3px solid var(--tb-accent);
        border-radius: 8px;
        padding: 12px 16px;
        margin: 10px 0 16px;
        color: var(--tb-text);
        font-family: var(--gl-font-sans);
    }}
    .gl-term-head {{
        display: flex; align-items: center; gap: 10px;
        font-size: 0.88rem; font-weight: 600;
    }}
    .gl-term-glyph {{
        color: var(--tb-accent);
        font-family: var(--gl-font-mono);
        font-size: 1.05rem; line-height: 1;
    }}
    .gl-term-label {{
        font-family: var(--gl-font-mono);
        font-size: 0.68rem;
        letter-spacing: 0.14em;
        color: var(--tb-accent);
        opacity: 0.85;
        padding: 2px 7px;
        border: 1px solid var(--tb-border);
        border-radius: 4px;
    }}
    .gl-term-title {{
        color: var(--tb-text);
        font-weight: 600;
    }}
    .gl-term-cmd {{
        margin-top: 6px;
        font-family: var(--gl-font-mono);
        font-size: 0.78rem;
        color: var(--tb-accent);
        opacity: 0.85;
    }}
    .gl-term-body {{
        margin-top: 6px;
        font-size: 0.85rem;
        line-height: 1.7;
        color: var(--tb-text);
        opacity: 0.92;
    }}
    /* ================================================================= */
    /* 12. Signal / status / decision cards                               */
    /* ================================================================= */
    .gl-signal-card {{
        background: linear-gradient(180deg, var(--sc-bg), transparent);
        border: 1px solid var(--sc-border);
        border-radius: 10px;
        padding: 10px 14px;
        min-height: 78px;
        font-family: var(--gl-font-sans);
        color: var(--sc-text);
        box-shadow: 0 2px 10px rgba(6,10,18,.25);
    }}
    .gl-sig-head {{
        display: flex; align-items: center; gap: 8px;
        font-size: 0.72rem; letter-spacing: 0.08em;
        color: var(--sc-accent);
        text-transform: uppercase;
    }}
    .gl-sig-glyph {{ font-family: var(--gl-font-mono); line-height: 1; }}
    .gl-sig-value {{
        font-family: var(--gl-font-mono);
        font-size: 1.35rem; font-weight: 700; margin-top: 4px;
        color: var(--sc-text);
    }}
    .gl-sig-delta {{
        margin-left: 8px;
        font-size: 0.78rem;
        color: var(--sc-accent);
        opacity: 0.9;
    }}
    .gl-sig-hint {{
        margin-top: 4px;
        font-size: 0.75rem;
        color: var(--gl-fg-dim, #8397AC);
        line-height: 1.55;
    }}
    .gl-status-card {{
        background: var(--st-bg);
        border: 1px solid var(--st-border);
        border-left: 3px solid var(--st-accent);
        border-radius: 8px;
        padding: 10px 14px;
        margin: 6px 0;
        color: var(--st-text);
    }}
    .gl-stat-head {{
        display: flex; align-items: center; gap: 10px;
        font-family: var(--gl-font-sans);
    }}
    .gl-stat-glyph {{ color: var(--st-accent); font-family: var(--gl-font-mono); }}
    .gl-stat-label {{ font-weight: 600; color: var(--st-text); }}
    .gl-stat-state {{
        margin-left: auto;
        font-family: var(--gl-font-mono);
        font-size: 0.78rem;
        color: var(--st-accent);
        padding: 2px 8px;
        border: 1px solid var(--st-border);
        border-radius: 4px;
    }}
    .gl-stat-detail {{
        margin-top: 4px;
        font-size: 0.82rem;
        color: var(--st-text);
        opacity: 0.9;
        line-height: 1.65;
    }}
    .gl-decision-card {{
        background: linear-gradient(180deg, var(--dc-bg), transparent);
        border: 1px solid var(--dc-border);
        border-radius: 12px;
        padding: 14px 18px;
        margin: 10px 0 16px;
        color: var(--dc-text);
    }}
    .gl-dec-head {{
        display: flex; align-items: center; gap: 10px;
        font-size: 0.72rem; letter-spacing: 0.12em;
        color: var(--dc-accent);
    }}
    .gl-dec-glyph {{ font-family: var(--gl-font-mono); }}
    .gl-dec-label {{
        font-family: var(--gl-font-mono);
        padding: 2px 7px;
        border: 1px solid var(--dc-border);
        border-radius: 4px;
    }}
    .gl-dec-conf {{
        margin-left: auto;
        font-family: var(--gl-font-mono);
        font-size: 0.72rem;
        color: var(--dc-accent);
        opacity: 0.85;
    }}
    .gl-dec-verdict {{
        margin-top: 8px;
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--dc-text);
    }}
    .gl-dec-reason {{
        margin-top: 4px;
        font-size: 0.88rem;
        color: var(--dc-text);
        opacity: 0.92;
        line-height: 1.7;
    }}
    .gl-dec-action {{
        margin-top: 10px;
        font-family: var(--gl-font-mono);
        font-size: 0.82rem;
        color: var(--dc-accent);
    }}
    /* ================================================================= */
    /* 13. v8 Terminal hero (render_terminal_hero)                        */
    /*     v11.5.8 · breathing-light border animation (cyan, same rhythm  */
    /*     as the brand-dot .gl-brand-dot next to the product title)      */
    /* ================================================================= */
    @keyframes gl-thero-breathe {{
        0%, 100% {{
            border-color: rgba(103,232,249,0.22);
            box-shadow:
                0 0 0 0 rgba(103,232,249,0),
                0 0 14px 0 rgba(103,232,249,0.08),
                inset 0 1px 0 rgba(103,232,249,0.04);
        }}
        50% {{
            border-color: rgba(103,232,249,0.68);
            box-shadow:
                0 0 0 1px rgba(103,232,249,0.18),
                0 0 28px 0 rgba(103,232,249,0.30),
                inset 0 1px 0 rgba(103,232,249,0.16);
        }}
    }}
    .gl-thero {{
        position: relative;
        background: linear-gradient(180deg, #0F1725 0%, #0A1420 100%);
        border: 1px solid var(--th-border);
        border-radius: 14px;
        padding: 26px 32px 22px;
        margin: 8px 0 22px;
        color: var(--gl-fg-primary, #E8F7FC);
        overflow: hidden;
        animation: gl-thero-breathe 3.6s ease-in-out infinite;
    }}
    .gl-thero::before {{
        content: "";
        position: absolute;
        inset: 0;
        background:
            radial-gradient(ellipse at 12% 18%, rgba(103,232,249,0.10), transparent 50%),
            radial-gradient(ellipse at 92% 100%, rgba(124,58,237,0.07), transparent 55%);
        pointer-events: none;
        z-index: 0;
    }}
    .gl-thero > * {{ position: relative; z-index: 1; }}
    .gl-thero-topline {{
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg,
            transparent 0%,
            var(--th-accent) 30%,
            var(--th-accent) 70%,
            transparent 100%);
        opacity: 0.85;
        z-index: 2;
    }}
    .gl-thero-eyebrow {{
        display: inline-block;
        font-family: var(--gl-font-mono);
        font-size: 0.70rem;
        font-weight: 700;
        letter-spacing: 0.22em;
        color: var(--th-accent);
        padding: 3px 10px;
        border: 1px solid var(--th-border);
        border-radius: 4px;
        background: rgba(103,232,249,0.04);
        text-transform: uppercase;
    }}
    .gl-thero-title {{
        font-family: var(--gl-font-sans);
        font-size: 2.05rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        color: #F6FDFF;
        margin-top: 12px;
        line-height: 1.2;
    }}
    .gl-thero-briefing {{
        margin-top: 10px;
        font-family: var(--gl-font-sans);
        font-size: 0.96rem;
        color: #B4CCDF;
        line-height: 1.78;
        max-width: 780px;
    }}
    .gl-thero-chips {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 14px;
    }}
    .gl-thero-chip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 3px 10px;
        background: var(--ch-bg);
        border: 1px solid var(--ch-border);
        border-radius: 5px;
        font-family: var(--gl-font-mono);
        font-size: 0.74rem;
        letter-spacing: 0.06em;
        color: var(--ch-accent);
        font-weight: 600;
    }}
    .gl-thero-chipval {{
        color: #E8F7FC;
        font-weight: 700;
    }}
    .gl-thero-verdict {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 18px;
        padding: 10px 14px;
        background: rgba(103,232,249,0.05);
        border: 1px solid rgba(103,232,249,0.18);
        border-left: 3px solid var(--th-accent);
        border-radius: 6px;
    }}
    .gl-thero-verdict-tag {{
        font-family: var(--gl-font-mono);
        font-size: 0.66rem;
        letter-spacing: 0.20em;
        color: var(--th-accent);
        padding: 2px 8px;
        border: 1px solid var(--th-border);
        border-radius: 3px;
    }}
    .gl-thero-verdict-text {{
        font-family: var(--gl-font-sans);
        font-size: 0.92rem;
        color: #E8F7FC;
        font-weight: 600;
    }}
    /* ================================================================= */
    /* 14. Terminal chip / table / empty / error                          */
    /* ================================================================= */
    .gl-tchip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 2px 10px;
        background: var(--tc-bg);
        border: 1px solid var(--tc-border);
        border-radius: 4px;
        font-family: var(--gl-font-mono);
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        color: var(--tc-accent);
        font-weight: 600;
    }}
    .gl-tchip-val {{
        color: #E8F7FC;
        font-weight: 700;
        padding-left: 4px;
        border-left: 1px solid var(--tc-border);
        margin-left: 4px;
    }}
    .gl-tterm-caption {{
        background: var(--tt-bg);
        border: 1px solid var(--tt-border);
        border-left: 3px solid var(--tt-accent);
        border-radius: 6px 6px 0 0;
        padding: 8px 14px;
        margin: 6px 0 0;
        display: flex;
        align-items: flex-start;
        gap: 10px;
        font-family: var(--gl-font-sans);
        font-size: 0.82rem;
        color: #B4CCDF;
    }}
    .gl-tterm-caption-tag {{
        font-family: var(--gl-font-mono);
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        color: var(--tt-accent);
        padding: 2px 8px;
        border: 1px solid var(--tt-border);
        border-radius: 3px;
        white-space: nowrap;
    }}
    .gl-tterm-caption-text {{
        line-height: 1.7;
    }}
    .gl-tterm-wrap {{
        background: #0A1420;
        border: 1px solid rgba(103,232,249,0.12);
        border-top: none;
        border-radius: 0 0 10px 10px;
        padding: 0;
        margin: 0 0 18px;
    }}
    .gl-tterm-wrap [data-testid="stDataFrame"],
    .gl-tterm-wrap div[data-testid="stDataFrameResizable"] {{
        background: transparent !important;
    }}
    .gl-tempty {{
        background:
            repeating-linear-gradient(0deg,
                rgba(103,232,249,0.02) 0 1px,
                transparent 1px 3px),
            #0A1420;
        border: 1px dashed rgba(103,232,249,0.26);
        border-radius: 12px;
        padding: 28px 24px;
        text-align: center;
        margin: 12px 0 20px;
    }}
    .gl-tempty-glyph {{
        font-family: var(--gl-font-mono);
        font-size: 1.8rem;
        color: #67E8F9;
        opacity: 0.75;
        margin-bottom: 6px;
    }}
    .gl-tempty-title {{
        font-family: var(--gl-font-sans);
        font-size: 1.02rem;
        font-weight: 700;
        color: #E8F7FC;
    }}
    .gl-tempty-reason {{
        margin-top: 6px;
        font-family: var(--gl-font-sans);
        font-size: 0.88rem;
        color: #8397AC;
        line-height: 1.7;
    }}
    .gl-tempty-actions-label {{
        margin-top: 14px;
        font-family: var(--gl-font-mono);
        font-size: 0.68rem;
        letter-spacing: 0.14em;
        color: #67E8F9;
    }}
    .gl-tempty-actions {{
        display: inline-flex;
        flex-direction: column;
        gap: 4px;
        list-style: none;
        padding: 6px 0 0;
        margin: 0;
    }}
    .gl-tempty-item {{
        font-family: var(--gl-font-sans);
        font-size: 0.86rem;
        color: #B4CCDF;
    }}
    .gl-tempty-item::before {{
        content: "› ";
        color: #67E8F9;
        opacity: 0.8;
    }}
    .gl-terror {{
        background: var(--te-bg);
        border: 1px solid var(--te-border);
        border-left: 3px solid var(--te-accent);
        border-radius: 8px;
        padding: 14px 18px;
        margin: 12px 0 18px;
        color: var(--te-text);
    }}
    .gl-terror-head {{
        display: flex; align-items: center; gap: 10px;
        font-family: var(--gl-font-sans);
        font-weight: 700;
    }}
    .gl-terror-glyph {{
        font-family: var(--gl-font-mono);
        color: var(--te-accent);
        font-size: 1.05rem;
    }}
    .gl-terror-tag {{
        font-family: var(--gl-font-mono);
        font-size: 0.68rem;
        letter-spacing: 0.18em;
        color: var(--te-accent);
        padding: 2px 8px;
        border: 1px solid var(--te-border);
        border-radius: 3px;
    }}
    .gl-terror-title {{ color: var(--te-text); }}
    .gl-terror-reason {{
        margin-top: 6px;
        font-size: 0.88rem;
        color: var(--te-text);
        opacity: 0.95;
        line-height: 1.7;
    }}
    .gl-terror-schema,
    .gl-terror-fallback {{
        margin-top: 8px;
        font-family: var(--gl-font-mono);
        font-size: 0.80rem;
        color: var(--te-text);
        display: flex;
        gap: 10px;
        align-items: flex-start;
    }}
    .gl-terror-schema span:first-child,
    .gl-terror-fallback span:first-child {{
        font-size: 0.62rem;
        letter-spacing: 0.14em;
        color: var(--te-accent);
        padding: 2px 7px;
        border: 1px solid var(--te-border);
        border-radius: 3px;
        flex: 0 0 auto;
    }}

    /* ============================================================ */
    /* v8 §15.10 · Governance 3×3 Gate Matrix                        */
    /* Dark cards · 3px left colour bar · mono GATE NN eyebrow       */
    /* PASS/FAIL chip top-right · Chinese label + key underneath      */
    /* title attribute surfaces technical detail on hover            */
    /* ============================================================ */
    .gl-gate-matrix {{
        display: grid;
        grid-template-columns: repeat(var(--gate-cols, 3), 1fr);
        gap: 10px;
        margin: 10px 0 18px;
    }}
    @media (max-width: 900px) {{
        .gl-gate-matrix {{ grid-template-columns: 1fr; }}
    }}
    .gl-gate-cell {{
        position: relative;
        background: linear-gradient(180deg, #111B2B 0%, #0F1725 100%);
        border: 1px solid rgba(103,232,249,0.14);
        border-left: 3px solid var(--gate-accent, #67e8f9);
        border-radius: 8px;
        padding: 10px 14px 10px 16px;
        overflow: hidden;
        transition: all .2s ease;
    }}
    .gl-gate-cell:hover {{
        border-color: rgba(103,232,249,0.32);
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(6,10,18,0.35);
    }}
    .gl-gate-cell.gl-gate-danger {{
        background: linear-gradient(180deg, #1a0f14 0%, #15151f 100%);
        border-color: rgba(244,63,94,0.18);
    }}
    .gl-gate-cell.gl-gate-danger:hover {{
        border-color: rgba(244,63,94,0.45);
    }}
    .gl-gate-head {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }}
    .gl-gate-eyebrow {{
        font-family: var(--gl-font-mono);
        font-size: 0.62rem;
        font-weight: 700;
        color: #8397ac;
        letter-spacing: 0.18em;
        text-transform: uppercase;
    }}
    .gl-gate-chip {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 8px;
        border-radius: 4px;
        font-family: var(--gl-font-mono);
        font-size: 0.60rem;
        font-weight: 800;
        letter-spacing: 0.12em;
    }}
    .gl-gate-ok .gl-gate-chip {{
        color: #10b981;
        background: rgba(16,185,129,0.12);
        border: 1px solid rgba(16,185,129,0.45);
    }}
    .gl-gate-danger .gl-gate-chip {{
        color: #f43f5e;
        background: rgba(244,63,94,0.12);
        border: 1px solid rgba(244,63,94,0.45);
    }}
    .gl-gate-label {{
        font-family: var(--gl-font-sans);
        font-size: 0.92rem;
        font-weight: 600;
        color: #E8F7FC;
        line-height: 1.35;
        margin-top: 2px;
    }}
    .gl-gate-key {{
        margin-top: 4px;
        font-family: var(--gl-font-mono);
        font-size: 0.62rem;
        color: #5B7186;
        letter-spacing: 0.04em;
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


def render_section_title(title_zh: str, title_en: str = "", sub: str = "") -> None:
    """v11.3 § dark-glint section header — replaces raw ``st.header(...)``.

    Uses ``.gl-section-head`` (cyan left-bar + gradient) so every page
    gets the same monospace-english sub + chinese-bold divider instead
    of Streamlit's default white ``h2``.

    Args:
        title_zh: primary (Chinese) section title.
        title_en: optional monospace english gloss rendered on the right.
        sub:      alternative for ``title_en`` — kept for call-site flexibility.
    """
    right = title_en or sub or ""
    right_html = f'<span class="sub">{right}</span>' if right else ""
    st.markdown(
        f'<div class="gl-section-head">'
        f'<h2>{title_zh}</h2>'
        f'{right_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# v11.3 § dead-code removal — legacy light-mode ``render_page_heading``
# has been superseded by ``render_terminal_hero`` (dark terminal) + the
# ``render_topbar + render_secnav`` breadcrumb stack. No page imports it
# any more, so the function was deleted. The ``.gl-page-heading*`` CSS
# classes remain for now in case a downstream user re-enables it.


def render_trust_strip(items: list) -> None:
    """Render a single-line *trust cue* row under the hero.

    ``items`` is a list of ``(label, value, tone)`` tuples where ``tone`` is
    optional and defaults to ``"default"``. Each cell renders as
    ``LABEL·VALUE`` with monospace value styling.
    """
    if not items:
        return
    parts = []
    for tup in items:
        if len(tup) == 3:
            lbl, val, tone = tup
        else:
            lbl, val = tup
            tone = "default"
        parts.append(
            f'<span class="gl-trust-cell gl-trust-{tone}">'
            f'<span class="gl-trust-k">{lbl}</span>'
            f'<span class="gl-trust-v">{val}</span>'
            f'</span>'
        )
    st.markdown(
        f'<div class="gl-trust-strip">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def render_live_chip(text: str = "LIVE · 研究快照"):
    """Pulsing emerald dot chip for live-status indicators."""
    st.markdown(
        f'<span class="gl-live">{text}</span>',
        unsafe_allow_html=True,
    )


def render_page_footer(page_name_en: str,
                       limits_note: str = "",
                       product: str = "量化分析工作台",
                       system: str = "多因子股票分析系統") -> None:
    """Unified bottom-of-page footer block (per v3 audit §27, §28).

    Three fixed rows, in this exact visual order:
      1. A horizontal divider (st.markdown("---"))
      2. Constraints caption (📌 limits_note) — defaults to the standard
         "固定歷史資料集 ｜ 非即時市場數據 ｜ …" line if empty
      3. Footer band ("{product} — {page_name_en} | {system}")

    Replaces the ad-hoc mixture of st.caption + page-footer div that used to
    appear at the bottom of every analyst page, so every page now ends with
    the same trust-closing cadence regardless of degraded state or missing
    artefacts.
    """
    default_limits = (
        "📌 限制條件：固定歷史資料集 ｜ 非即時市場數據 ｜ 基準為等權計算 ｜ "
        "Ensemble = 簡單平均 ｜ Phase 3 治理已實現"
    )
    note = limits_note or default_limits
    if not note.startswith("📌"):
        note = f"📌 {note}"
    st.markdown("---")
    st.caption(note)
    st.markdown(
        f'<div class="page-footer">{product} — {page_name_en} | {system}</div>',
        unsafe_allow_html=True,
    )


def render_read_guide(body: str, title: str = "如何閱讀這張圖",
                      icon: str = "📖", tone: str = "info") -> None:
    """Canonical "如何閱讀" explainer block (v4 audit §14.4).

    Single styling contract for every chart/table intro so the dashboard never
    shows three flavours of guidance boxes on the same page.

    Args:
        body: plain text or minimal markdown (accepts <br>, <strong>).
        title: section label shown in the eyebrow strip.
        icon: leading glyph (emoji or inline SVG string).
        tone: one of {info, ok, warn, violet}. Maps to the gl- color system.
    """
    tones = {
        "info":   ("#0ea5e9", "#e0f2fe", "#075985"),
        "ok":     ("#10b981", "#ecfdf5", "#065f46"),
        "warn":   ("#a78bfa", "#fffbeb", "#92400e"),
        "violet": ("#7c3aed", "#f5f3ff", "#5b21b6"),
    }
    border, bg, text = tones.get(tone, tones["info"])
    st.markdown(
        f'''
<div style="
    background:{bg};
    border:1px solid {border}33;
    border-left:4px solid {border};
    border-radius:10px;
    padding:12px 16px;
    margin:8px 0 14px 0;
    color:{text};
    font-size:0.92rem;
    line-height:1.65;
">
    <div style="
        display:inline-block;
        font-size:0.66rem;
        font-weight:800;
        letter-spacing:0.14em;
        text-transform:uppercase;
        background:{border};
        color:#fff;
        padding:2px 10px;
        border-radius:4px;
        margin-bottom:6px;
    ">{icon} {title}</div>
    <div>{body}</div>
</div>
''',
        unsafe_allow_html=True,
    )


def render_chart_headline(conclusion: str, detail: str = "",
                          tone: str = "blue") -> None:
    """Conclusion-oriented chart headline (v4 audit §14.4).

    Renders a two-line headline: the conclusion (bold, prominent) followed by
    the technical detail (smaller, muted). Use above a chart whose raw title
    would otherwise be neutral like "ICIR 月度趨勢".

    Args:
        conclusion: the lede — "D+20 ICIR 穩定 > 0.5,適合月頻部署"
        detail:     the spec — "Pearson IC,Purged WF · 27 folds"
        tone:       blue / violet / emerald / amber / rose
    """
    tones = {
        "blue":    "#2563eb",
        "violet":  "#7c3aed",
        "emerald": "#10b981",
        "amber":   "#a78bfa",
        "rose":    "#f43f5e",
    }
    accent = tones.get(tone, tones["blue"])
    st.markdown(
        f'''
<div style="margin:14px 0 6px 0;">
    <div style="font-size:1.08rem; font-weight:800; color:#0f172a; line-height:1.4;">
        <span style="
            display:inline-block;
            width:4px;
            height:16px;
            background:{accent};
            border-radius:2px;
            margin-right:10px;
            vertical-align:-3px;
        "></span>{conclusion}
    </div>
    {f'<div style="font-size:0.82rem; color:#64748b; margin-top:3px; margin-left:14px;">{detail}</div>' if detail else ''}
</div>
''',
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


def inject_sidebar_brand(product: str = "多因子股票分析系統",
                         eyebrow: str = "MULTI-FACTOR RESEARCH TERMINAL",
                         subtitle: str = "三引擎整合｜九支柱快照｜Phase 3 治理"):
    """Inject the 多因子股票分析系統 brand block at the top of the sidebar.

    Three-layer layout (per v3 audit §17, v10 §5 copy refresh):
      · eyebrow (mono, cyan, uppercased) — product category
      · main title (sans, bold, pulsing cyan dot) — product name
      · subtitle (sans, slate, 1-line tagline) — what this product does

    v10 §5 copy rewrite: the old subtitle "台灣股市 × 三引擎集成 × Phase 3 治理"
    read like an engineering tag rather than a product name. Per audit it must
    move to the subtitle layer in 管顧 style, and the brand lead-line upgrades
    from "股票預測系統" → "多因子股票分析系統" for consistency with the
    terminal-grade product positioning.

    Renders on every page because app.py's sidebar runs first.
    Single-line HTML — CommonMark-safe.
    """
    st.sidebar.markdown(
        (
            f'<div class="gl-brand">'
            f'<div class="gl-brand-eyebrow">{eyebrow}</div>'
            f'<div class="gl-brand-title"><span class="gl-brand-dot"></span>{product}</div>'
            f'<div class="gl-brand-subtitle">{subtitle}</div>'
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
                             color="#E8F7FC")),
        polar=dict(
            bgcolor="rgba(10,20,32,0.60)",
            radialaxis=dict(
                visible=True, range=[0, max(1.0, max(r_main) * 1.15)],
                showline=False, gridcolor="rgba(103,232,249,0.14)",
                tickfont=dict(family="JetBrains Mono", size=9, color="#b4ccdf"),
                tickformat=".2f",
            ),
            angularaxis=dict(
                gridcolor="rgba(103,232,249,0.14)",
                linecolor="rgba(103,232,249,0.22)",
                tickfont=dict(family="Inter, 'Microsoft JhengHei'", size=11,
                              color="#cfe2ee"),
            ),
        ),
        showlegend=True,
        legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center",
                    font=dict(family="Inter", size=11, color="#b4ccdf")),
        height=height,
        margin=dict(t=50, b=40, l=40, r=40),
        paper_bgcolor="#0A1420",
        plot_bgcolor="#081220",
    )
    return fig


_GL_FONT_SANS = "Inter, 'Noto Sans TC', 'Microsoft JhengHei', -apple-system, BlinkMacSystemFont, sans-serif"
_GL_FONT_MONO = "'JetBrains Mono', 'Noto Sans TC', SF Mono, Consolas, monospace"


GLINT_DARK_COLORWAY = [
    "#67e8f9",  # cyan-bright — primary line
    "#7c3aed",  # violet — secondary
    "#10b981",  # emerald — positive
    "#a78bfa",  # amber — caution
    "#f43f5e",  # rose — negative
    "#2563eb",  # blue — tertiary
    "#a78bfa",  # violet-light — fallback
    "#22d3ee",  # cyan — fallback
]


def glint_plotly_layout(title: str = "", height: int = 360,
                        subtitle: str = "", show_grid: bool = True,
                        ylabel: str = "", xlabel: str = "",
                        dark: bool = True) -> dict:
    """Return a glint-themed Plotly layout dict for any figure (v7 §14.4).

    Defaults to DARK terminal styling per v7 audit. Set ``dark=False`` only
    for printing/export scenarios that need the legacy light palette.

    Aligned with dark tokens:
      paper / plot bg = gl-bg-panel / transparent
      grid            = rgba(103,232,249,0.06)
      text            = gl-text / gl-text-2
      colorway        = cyan / violet / emerald / amber / rose / blue
    """
    if dark:
        title_color = "#E8F7FC"
        subtitle_color = "#8397ac"
        body_color = "#B4CCDF"
        tick_color = "#8397ac"
        axis_label_color = "#5B7186"
        grid_color = "rgba(103,232,249,0.06)"
        line_color = "rgba(103,232,249,0.22)"
        zero_color = "rgba(103,232,249,0.18)"
        tick_line = "rgba(103,232,249,0.22)"
        hover_bg = "#0A1420"
        hover_border = "rgba(103,232,249,0.55)"
        hover_text = "#E8F7FC"
        legend_text = "#B4CCDF"
        legend_bg = "rgba(15,23,37,0.88)"
        legend_border = "rgba(103,232,249,0.22)"
        # v11 §4b — opaque dark backgrounds so charts render as a crisp
        # terminal panel even when the host page canvas is light. Previously
        # the glint layout used fully transparent paper/plot bg which made
        # charts look washed-out on Streamlit's default white main canvas.
        paper_bg = "#0A1420"
        plot_bg = "#081220"
        colorway = GLINT_DARK_COLORWAY
    else:
        title_color = "#0f172a"
        subtitle_color = "#94a3b8"
        body_color = "#334155"
        tick_color = "#64748b"
        axis_label_color = "#94a3b8"
        grid_color = "rgba(37,99,235,0.06)"
        line_color = "rgba(37,99,235,0.18)"
        zero_color = "rgba(37,99,235,0.15)"
        tick_line = "rgba(37,99,235,0.15)"
        hover_bg = "#0f1419"
        hover_border = "rgba(6,182,212,0.45)"
        hover_text = "#e8f7fc"
        legend_text = "#475569"
        legend_bg = "rgba(255,255,255,0.75)"
        legend_border = "rgba(37,99,235,0.18)"
        paper_bg = "rgba(0,0,0,0)"
        plot_bg = "rgba(255,255,255,0)"
        colorway = ["#2563eb", "#7c3aed", "#06b6d4", "#10b981", "#a78bfa", "#f43f5e", "#4f46e5", "#ec4899"]

    title_obj = dict(
        text=f"<b>{title}</b>" + (f"<br><span style='font-size:11px;color:{subtitle_color};font-weight:400;'>{subtitle}</span>" if subtitle else ""),
        x=0.01, y=0.97, xanchor="left",
        font=dict(family=_GL_FONT_SANS, size=15, color=title_color),
    )
    return dict(
        title=title_obj,
        font=dict(family=_GL_FONT_SANS, color=body_color, size=12),
        paper_bgcolor=paper_bg,
        plot_bgcolor=plot_bg,
        height=height,
        margin=dict(t=60 if subtitle else 48, b=44, l=54, r=28),
        xaxis=dict(
            title=dict(text=xlabel, font=dict(family=_GL_FONT_MONO, size=10, color=axis_label_color)) if xlabel else None,
            gridcolor=grid_color if show_grid else "rgba(0,0,0,0)",
            linecolor=line_color,
            zerolinecolor=zero_color,
            tickfont=dict(family=_GL_FONT_MONO, size=10, color=tick_color),
            showline=True, mirror=False, ticks="outside", ticklen=4, tickcolor=tick_line,
        ),
        yaxis=dict(
            title=dict(text=ylabel, font=dict(family=_GL_FONT_MONO, size=10, color=axis_label_color)) if ylabel else None,
            gridcolor=grid_color if show_grid else "rgba(0,0,0,0)",
            linecolor=line_color,
            zerolinecolor=zero_color,
            tickfont=dict(family=_GL_FONT_MONO, size=10, color=tick_color),
            showline=True, mirror=False, ticks="outside", ticklen=4, tickcolor=tick_line,
        ),
        hoverlabel=dict(
            bgcolor=hover_bg,
            bordercolor=hover_border,
            font=dict(family=_GL_FONT_MONO, color=hover_text, size=11),
        ),
        legend=dict(
            font=dict(family=_GL_FONT_SANS, size=11, color=legend_text),
            bgcolor=legend_bg,
            bordercolor=legend_border,
            borderwidth=1, itemsizing="constant",
        ),
        colorway=colorway,
    )


# v7 §18.3 — canonical dark helpers. Aliases that guarantee dark mode.
def glint_dark_layout(**kwargs) -> dict:
    """Canonical dark Plotly layout (v7 §14.4, §18.3). Wrapper that forces
    ``dark=True`` — use this when intent should be obvious."""
    kwargs["dark"] = True
    return glint_plotly_layout(**kwargs)


def glint_dark_colorway() -> list:
    """Canonical dark colorway — cyan / violet / emerald / amber / rose / blue."""
    return list(GLINT_DARK_COLORWAY)


def glint_dark_tooltip() -> dict:
    """Dark terminal hoverlabel dict for ``fig.update_traces(hoverlabel=...)``."""
    return dict(
        bgcolor="#0A1420",
        bordercolor="rgba(103,232,249,0.55)",
        font=dict(family=_GL_FONT_MONO, color="#E8F7FC", size=11),
    )


def glint_dark_table_style() -> dict:
    """Dark terminal Plotly ``go.Table`` header/cells style dict.

    Use ``go.Table(header=dict(**style["header"]), cells=dict(**style["cells"]))``.
    Returns typography/color only — caller supplies ``values``.
    """
    return {
        "header": dict(
            fill_color="#0F1725",
            line_color="rgba(103,232,249,0.18)",
            font=dict(family=_GL_FONT_MONO, color="#67E8F9", size=11),
            align="left",
            height=30,
        ),
        "cells": dict(
            fill_color=["#0A1420", "#111B2B"],   # alternating rows
            line_color="rgba(103,232,249,0.08)",
            font=dict(family=_GL_FONT_SANS, color="#E8F7FC", size=11),
            align="left",
            height=26,
        ),
    }


def glint_dark_axes(show_grid: bool = True, x_title: str = "",
                    y_title: str = "") -> dict:
    """Canonical dark terminal axis overrides (v8 §15.2).

    Returns a dict containing ``xaxis`` / ``yaxis`` sub-dicts suitable for
    ``fig.update_layout(**glint_dark_axes())``. Use this when a chart is
    built from raw ``go.Figure()`` without ``glint_plotly_layout``, so axis
    typography stays consistent (mono ticks, cyan grid 0.06α, 0.22α lines).

    Example::

        fig = go.Figure()
        fig.add_trace(go.Bar(...))
        fig.update_layout(**glint_dark_layout(), **glint_dark_axes())
    """
    base_axis = dict(
        showgrid=show_grid,
        gridcolor="rgba(103,232,249,0.06)",
        linecolor="rgba(103,232,249,0.22)",
        zeroline=False,
        ticks="outside",
        ticklen=4,
        tickcolor="rgba(103,232,249,0.22)",
        tickfont=dict(family=_GL_FONT_MONO, size=10, color="#8397AC"),
    )
    xaxis = dict(base_axis)
    if x_title:
        xaxis["title"] = dict(
            text=x_title,
            font=dict(family=_GL_FONT_MONO, size=10, color="#5B7186"),
        )
    yaxis = dict(base_axis)
    if y_title:
        yaxis["title"] = dict(
            text=y_title,
            font=dict(family=_GL_FONT_MONO, size=10, color="#5B7186"),
        )
    return {"xaxis": xaxis, "yaxis": yaxis}


# Terminal tone → Plotly bar accent lookup (v8 §15.2 / §13).
_GL_DARK_BAR_ACCENTS = {
    "cyan":    "#67e8f9",
    "blue":    "#2563eb",
    "violet":  "#a78bfa",
    "emerald": "#10b981",
    "amber":   "#a78bfa",
    "rose":    "#f43f5e",
    "slate":   "#475569",
    "info":    "#67e8f9",   # alias of cyan
    "ok":      "#10b981",   # alias of emerald
    "warn":    "#a78bfa",   # alias of amber
    "danger":  "#f43f5e",   # alias of rose
}


def glint_dark_bar_style(tone: str = "cyan", opacity: float = 0.85,
                         border: bool = True) -> dict:
    """Canonical dark terminal ``go.Bar`` marker style (v8 §15.2).

    Returns a ``marker`` dict — pass as ``go.Bar(..., marker=glint_dark_bar_style())``.
    Pages MUST NOT hardcode their own hex per spec §15.2. For multi-series
    bars, call once per series with tone ``"cyan"`` / ``"violet"`` / ``"emerald"``.

    ``tone`` accepts any key in ``_GL_DARK_BAR_ACCENTS`` (cyan/blue/violet/
    emerald/amber/rose/slate plus info/ok/warn/danger aliases).
    """
    accent = _GL_DARK_BAR_ACCENTS.get(tone, _GL_DARK_BAR_ACCENTS["cyan"])
    marker = dict(
        color=accent,
        opacity=max(0.0, min(1.0, float(opacity))),
    )
    if border:
        marker["line"] = dict(
            color="rgba(6,10,18,0.85)",
            width=0.6,
        )
    return marker


def glint_dark_hist_style(series: str = "primary",
                          opacity: float = 0.65) -> dict:
    """Canonical dark terminal ``go.Histogram`` marker style (v8 §15.2).

    Distinct overlay styles for ``"primary"`` (cyan) vs ``"secondary"``
    (violet) so two populations can be compared on the same axis without
    page-level color choices. Use ``opacity≈0.55`` when overlaying.

    Example::

        fig.add_trace(go.Histogram(x=live,     marker=glint_dark_hist_style("primary")))
        fig.add_trace(go.Histogram(x=baseline, marker=glint_dark_hist_style("secondary")))
    """
    series = (series or "primary").lower()
    if series in ("secondary", "violet", "baseline"):
        color = "#a78bfa"
        line_color = "rgba(167,139,250,0.55)"
    elif series in ("tertiary", "emerald", "ok"):
        color = "#10b981"
        line_color = "rgba(16,185,129,0.55)"
    else:  # primary / cyan / live
        color = "#67e8f9"
        line_color = "rgba(103,232,249,0.55)"
    return dict(
        color=color,
        opacity=max(0.0, min(1.0, float(opacity))),
        line=dict(color=line_color, width=0.8),
    )


# ============================================================================
#  v9 §9 — Glint Dark Chart Language: extended helpers
#   The §9 audit requires zero plotly_white and a single source of truth for
#   donut / composition / gauge / legend styling. Pages that need a composition
#   visual MUST call ``render_signal_donut()`` or ``render_market_composition_strip()``
#   instead of constructing their own ``go.Pie()`` with hand-picked hex.
# ============================================================================

# Canonical semantic palette for 5-bucket signal mixes. Cyan-bright for strong
# long, blue for long, muted slate for neutral, amber for short, rose for
# strong short — mirroring v9 §8.4 "radial spectrum" spec.
GLINT_SIGNAL_SEMANTIC_COLORS = {
    "strong_long":  "#67e8f9",   # cyan-bright
    "long":         "#2563eb",   # blue
    "neutral":      "#5B7186",   # muted slate
    "short":        "#f472b6",   # rose — bearish soft negative (cool-shifted from legacy amber)
    "strong_short": "#f43f5e",   # rose
    # zh aliases the existing pages use freely
    "偏多": "#2563eb",
    "看多": "#2563eb",
    "強烈看多": "#67e8f9",
    "中性": "#5B7186",
    "觀望": "#5B7186",
    "看空": "#f472b6",
    "強烈看空": "#f43f5e",
}

# 5-pillar colorway for feature-pillar / category donuts (v9 §8.5).
GLINT_CATEGORY_COLORWAY = ["#67e8f9", "#a78bfa", "#10b981", "#a78bfa", "#f43f5e", "#2563eb"]


def glint_dark_legend(orientation: str = "h", position: str = "bottom") -> dict:
    """Canonical dark terminal legend style (v9 §9.1).

    ``orientation``: ``"h"`` (horizontal, bottom) or ``"v"`` (vertical, right).
    ``position``   : ``"bottom"`` | ``"top"`` | ``"right"``.

    Wrap as ``fig.update_layout(legend=glint_dark_legend())``.
    """
    base = dict(
        font=dict(family=_GL_FONT_MONO, size=10.5, color="#B4CCDF"),
        bgcolor="rgba(10,20,32,0.72)",
        bordercolor="rgba(103,232,249,0.22)",
        borderwidth=1,
        itemsizing="constant",
    )
    if orientation == "h":
        base["orientation"] = "h"
        if position == "top":
            base.update(yanchor="bottom", y=1.08, xanchor="center", x=0.5)
        else:
            base.update(yanchor="top", y=-0.12, xanchor="center", x=0.5)
    else:
        base["orientation"] = "v"
        base.update(yanchor="middle", y=0.5, xanchor="left", x=1.02)
    return base


def glint_dark_donut_style(hole: float = 0.62) -> dict:
    """Canonical ``go.Pie`` props for a dark terminal donut (v9 §8.4).

    Returns a dict of `go.Pie(...)` kwargs: narrow ring, dark separators,
    no side-legend (caller supplies chip-style legend), hover mono text.
    Caller supplies ``labels``, ``values`` and a ``marker.colors`` list
    (recommend mapping via ``GLINT_SIGNAL_SEMANTIC_COLORS``).

    Example::

        fig = go.Figure(go.Pie(
            labels=labels, values=values,
            marker=dict(colors=[GLINT_SIGNAL_SEMANTIC_COLORS[l] for l in labels],
                        line=dict(color="#060A12", width=1.4)),
            **glint_dark_donut_style(),
        ))
    """
    return dict(
        hole=max(0.25, min(0.80, float(hole))),
        sort=False,                    # respect caller order (semantic ordering matters)
        direction="clockwise",
        rotation=270,                  # start at 9 o'clock — feels more "gauge-like"
        textinfo="none",               # keep ring clean; counts live in custom legend
        hovertemplate=(
            "<b>%{label}</b><br>"
            "<span style='font-family:JetBrains Mono,monospace;'>%{value}</span> · "
            "<span style='color:#67e8f9;'>%{percent}</span>"
            "<extra></extra>"
        ),
        showlegend=False,
    )


def glint_dark_composition_style(tones: list | None = None,
                                 border_color: str = "#060A12",
                                 opacity: float = 0.90) -> list:
    """Canonical per-segment marker specs for a horizontal composition strip.

    Returns a list of ``dict(color=..., opacity=..., line=...)`` the caller
    can zip with their segment values. Used by
    :func:`render_market_composition_strip`.
    """
    tones = tones or ["cyan", "blue", "slate", "amber", "rose"]
    out = []
    for t in tones:
        accent = _GL_DARK_BAR_ACCENTS.get(t, _GL_DARK_BAR_ACCENTS["cyan"])
        out.append(dict(
            color=accent,
            opacity=max(0.0, min(1.0, float(opacity))),
            line=dict(color=border_color, width=0.8),
        ))
    return out


def glint_dark_gauge_style(tone: str = "cyan") -> dict:
    """Canonical dark terminal gauge (``go.Indicator`` mode='gauge+number') style.

    Returns a ``gauge`` dict — pass via ``go.Indicator(gauge=glint_dark_gauge_style())``.

    v11 §5 — tick numbers bumped up (9→12) so the 0/1/2/…/9 labels around
    the arc are visible on screenshot at any DPI, and bar thickness
    widened (0.22→0.30) so the "filled" portion reads as a strong chip.
    """
    accent = _GL_DARK_BAR_ACCENTS.get(tone, _GL_DARK_BAR_ACCENTS["cyan"])
    return dict(
        axis=dict(
            tickfont=dict(family=_GL_FONT_MONO, size=12, color="#b4ccdf"),
            tickcolor="rgba(103,232,249,0.40)",
            tickwidth=1.5,
            ticklen=6,
            tickmode="linear",
            dtick=1,
        ),
        bar=dict(color=accent, thickness=0.30,
                 line=dict(color="rgba(103,232,249,0.55)", width=1.5)),
        bgcolor="rgba(10,20,32,0.75)",
        bordercolor="rgba(103,232,249,0.32)",
        borderwidth=1,
    )


def render_signal_donut(labels: list, values: list, *,
                        title: str = "全市場訊號分布",
                        subtitle: str = "Market Signal Mix",
                        center_metric: str | None = None,
                        center_metric_label: str | None = None,
                        tones: list | None = None,
                        height: int = 320,
                        key: str | None = None,
                        verdict: str | None = None) -> None:
    """Render a v9 §8.4 "Glint-style signal donut" — Plotly donut + center
    metric + dark panel + chip-style legend, emitted directly via
    ``st.plotly_chart`` / ``st.markdown``. Zero page-level styling needed.

    Args:
        labels: segment labels in canonical order (e.g. ``["偏多","中性","觀望"]``).
        values: matching segment values (counts or fractions).
        title / subtitle: center-stacked heading in the donut hole.
        center_metric: large mono number (e.g. ``"N=1,930"``); when omitted, auto-set to
            ``f"N={sum(values):,}"``.
        center_metric_label: small mono label under the metric (e.g. ``"Total"``).
        tones: explicit list of tone keys (``cyan/blue/violet/emerald/amber/rose/slate``)
            matching ``labels``. If omitted, picks a sensible default based on label text
            via ``GLINT_SIGNAL_SEMANTIC_COLORS``.
        height: chart height in px (default 320 — the spec's compact reading height).
        key: Streamlit chart key.
        verdict: optional one-line summary line rendered under the donut as a subtle
            mono caption (terminal verdict feel).
    """
    import plotly.graph_objects as go  # noqa: WPS433

    # Resolve colors per label
    if tones is not None:
        colors = [_GL_DARK_BAR_ACCENTS.get(t, _GL_DARK_BAR_ACCENTS["cyan"]) for t in tones]
    else:
        colors = [
            GLINT_SIGNAL_SEMANTIC_COLORS.get(lbl, GLINT_CATEGORY_COLORWAY[i % len(GLINT_CATEGORY_COLORWAY)])
            for i, lbl in enumerate(labels)
        ]

    total = sum(float(v) for v in values)
    if center_metric is None:
        if total == int(total):
            center_metric = f"N={int(total):,}"
        else:
            center_metric = f"{total:,.2f}"

    fig = go.Figure(go.Pie(
        labels=list(labels),
        values=list(values),
        marker=dict(colors=colors, line=dict(color="#060A12", width=1.4)),
        **glint_dark_donut_style(),
    ))

    # Center annotation — stacked title / subtitle / metric / metric-label.
    annot_lines = []
    if title:
        annot_lines.append(
            f"<span style='font-family:{_GL_FONT_SANS};font-size:13px;font-weight:700;"
            f"color:#E8F7FC;'>{safe_html(title)}</span>"
        )
    if subtitle:
        annot_lines.append(
            f"<span style='font-family:{_GL_FONT_MONO};font-size:10px;"
            f"letter-spacing:0.18em;color:#8397ac;text-transform:uppercase;'>"
            f"{safe_html(subtitle)}</span>"
        )
    if center_metric:
        annot_lines.append(
            f"<span style='font-family:{_GL_FONT_MONO};font-size:17px;"
            f"color:#67e8f9;font-weight:700;'>{safe_html(center_metric)}</span>"
        )
    if center_metric_label:
        annot_lines.append(
            f"<span style='font-family:{_GL_FONT_MONO};font-size:9.5px;"
            f"letter-spacing:0.22em;color:#5B7186;text-transform:uppercase;'>"
            f"{safe_html(center_metric_label)}</span>"
        )
    annot_text = "<br>".join(annot_lines) if annot_lines else ""
    fig.update_layout(
        annotations=[dict(
            text=annot_text, x=0.5, y=0.5,
            showarrow=False, align="center",
        )],
        **glint_dark_layout(height=height, show_grid=False),
    )
    # Override — donuts don't want axes (glint_dark_layout's default x/y axes are invisible
    # for pie anyway but it's cleaner to force margins tighter).
    fig.update_layout(margin=dict(t=12, b=12, l=12, r=12), xaxis=dict(visible=False),
                      yaxis=dict(visible=False), showlegend=False)

    st.plotly_chart(fig, use_container_width=True, key=key)

    # Chip legend (v9 §8.4 — replaces default side legend).
    legend_chips_html = []
    for lbl, val, color in zip(labels, values, colors):
        pct = (float(val) / total * 100.0) if total else 0.0
        legend_chips_html.append(
            '<span class="gl-donut-chip">'
            f'<span class="gl-donut-chip-dot" style="background:{color};'
            f'box-shadow:0 0 8px {color}80;"></span>'
            f'<span class="gl-donut-chip-label">{safe_html(str(lbl))}</span>'
            f'<span class="gl-donut-chip-val">{val:,.0f}</span>'
            f'<span class="gl-donut-chip-pct">{pct:.1f}%</span>'
            '</span>'
        )
    st.markdown(
        '<div class="gl-donut-legend">' + "".join(legend_chips_html) + "</div>",
        unsafe_allow_html=True,
    )
    if verdict:
        st.markdown(
            f'<div class="gl-donut-verdict">&gt; {safe_html(verdict)}</div>',
            unsafe_allow_html=True,
        )


def render_market_composition_strip(segments: list, *,
                                    title: str | None = None,
                                    height: int = 46,
                                    show_percent: bool = True,
                                    key: str | None = None) -> None:
    """Render a v9 §8.3 "Signal Composition Strip" — a single horizontal bar
    split into semantic segments (強烈看多 → 看多 → 中性 → 看空 → 強烈看空).

    Args:
        segments: list of ``(label, value, tone)`` tuples where ``tone`` keys any
            ``_GL_DARK_BAR_ACCENTS`` entry.  Order matters — the strip renders
            left-to-right in the order given.
        title: small mono label rendered above the strip (e.g. ``"D+20 · 市場訊號比例"``).
        height: strip height in px (default 46 — reads as a clean signal bar).
        show_percent: if True, overlays ``n · p%`` inside each segment.
        key: Streamlit chart key.
    """
    import plotly.graph_objects as go  # noqa: WPS433

    # Normalise input — filter zeros that would render as hairlines.
    segs = [(lbl, float(v), t) for (lbl, v, t) in segments if float(v) > 0]
    if not segs:
        st.info("無訊號分佈資料。")
        return

    total = sum(v for _, v, _ in segs)

    if title:
        st.markdown(
            f'<div class="gl-composition-title">{safe_html(title)}'
            f'<span class="gl-composition-total">TOTAL {total:,.0f}</span></div>',
            unsafe_allow_html=True,
        )

    fig = go.Figure()
    for lbl, val, tone in segs:
        accent = _GL_DARK_BAR_ACCENTS.get(tone, _GL_DARK_BAR_ACCENTS["cyan"])
        pct = val / total * 100.0 if total else 0.0
        text = f"{safe_html(str(lbl))} · {int(val):,} · {pct:.1f}%" if show_percent else safe_html(str(lbl))
        fig.add_trace(go.Bar(
            y=["mkt"], x=[val], name=lbl, orientation="h",
            marker=dict(color=accent, opacity=0.92,
                        line=dict(color="#060A12", width=0.8)),
            text=[text],
            textposition="inside",
            textangle=0,
            insidetextanchor="middle",
            textfont=dict(family=_GL_FONT_MONO, size=10.5, color="#06111C"),
            hovertemplate=f"<b>{safe_html(str(lbl))}</b><br>%{{x:,.0f}} · {pct:.1f}%<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        height=height + 24,
        margin=dict(t=8, b=6, l=10, r=10),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, showgrid=False, range=[0, total]),
        yaxis=dict(visible=False, showgrid=False),
        hoverlabel=dict(
            bgcolor="#0A1420",
            bordercolor="rgba(103,232,249,0.55)",
            font=dict(family=_GL_FONT_MONO, color="#E8F7FC", size=11),
        ),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


# --- v9 §9 · CSS for donut chip legend + composition strip --------------
_GLINT_V9_CHART_CSS = """
<style>
/* Chip-style legend that accompanies render_signal_donut (v9 §8.4) */
.gl-donut-legend {
    display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;
    margin: -4px 0 10px 0;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace);
}
.gl-donut-chip {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 5px 11px;
    background: rgba(10,20,32,0.78);
    border: 1px solid rgba(103,232,249,0.22);
    border-radius: 999px;
    font-size: 0.72rem;
    color: #B4CCDF;
    white-space: nowrap;
}
.gl-donut-chip-dot {
    width: 8px; height: 8px; border-radius: 50%;
    flex: 0 0 auto;
}
.gl-donut-chip-label { color: #E8F7FC; font-weight: 600; letter-spacing: 0.04em; }
.gl-donut-chip-val   { color: #67e8f9; font-weight: 700; }
.gl-donut-chip-pct   { color: #8397ac; font-size: 0.66rem; }
.gl-donut-verdict {
    text-align: center;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace);
    font-size: 0.72rem;
    color: #8397ac;
    margin: 4px 0 10px 0;
    letter-spacing: 0.04em;
}

/* Composition strip (v9 §8.3 signal composition bar) */
.gl-composition-title {
    display: flex; justify-content: space-between; align-items: baseline;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace);
    font-size: 0.68rem; letter-spacing: 0.18em;
    color: #8397ac; text-transform: uppercase;
    margin: 0 2px 4px 2px;
}
.gl-composition-total { color: #67e8f9; font-weight: 700; letter-spacing: 0.12em; }
</style>
"""


def inject_v9_chart_css():
    """Inject the v9 chart-language CSS (donut chip legend + composition strip).

    Safe to call multiple times — Streamlit dedupes identical st.markdown writes
    within a single script run. Call near the top of pages that use
    ``render_signal_donut`` or ``render_market_composition_strip``.
    """
    st.markdown(_GLINT_V9_CHART_CSS, unsafe_allow_html=True)


# ============================================================================
# v10 §7 · §8 · §13.3 — Consolidated dark widget override layer
# Single source of truth for: sidebar select, sidebar slider, expander base
# state, radio labels, tabs, download buttons. Fixes the black-on-black
# readability bugs flagged in v10 screenshots 3 & 4.
# ============================================================================
_GLINT_V10_DARK_WIDGETS_CSS = """
<style>
/* =========================================================================
   v10 §7 — Base-state readability fixes (non-hover legibility)
   Applied GLOBALLY (main canvas + sidebar). Makes sure every interactive
   block has either:
     · dark bg + light text    OR
     · light bg + dark text
   Never dark bg + dark text.
   ========================================================================= */
/* --- Expander summary: always dark-bg + light-text in dark context ------ */
section[data-testid="stSidebar"] details summary,
section[data-testid="stSidebar"] details summary span,
section[data-testid="stSidebar"] details summary p,
section[data-testid="stSidebar"] details summary div {
    color: #d6e6f0 !important;
    font-weight: 600 !important;
}
section[data-testid="stSidebar"] details {
    background: rgba(10,20,32,0.55) !important;
    border: 1px solid rgba(103,232,249,0.20) !important;
    border-radius: 10px !important;
}
section[data-testid="stSidebar"] details[open] {
    background: rgba(10,20,32,0.72) !important;
    border-color: rgba(103,232,249,0.36) !important;
}
section[data-testid="stSidebar"] details summary:hover {
    background: rgba(103,232,249,0.08) !important;
}
/* --- Radio labels (light canvas): dark-text on light-bg --------------- */
div[data-testid="stRadio"] label {
    color: #1a1f36 !important;
    font-weight: 500 !important;
}
div[data-testid="stRadio"] label[data-baseweb] > div:first-child {
    border-color: #94a3b8 !important;
}
/* --- Radio inside sidebar (dark canvas): light-text ------------------- */
section[data-testid="stSidebar"] div[data-testid="stRadio"] label,
section[data-testid="stSidebar"] div[data-testid="stRadio"] label p,
section[data-testid="stSidebar"] div[data-testid="stRadio"] label span {
    color: #d6e6f0 !important;
}
/* --- Download buttons: always readable in base state ----------------- */
.stDownloadButton > button,
.stDownloadButton > button p,
.stDownloadButton > button span {
    color: #0f172a !important;
    background: #ffffff !important;
}
section[data-testid="stSidebar"] .stDownloadButton > button,
section[data-testid="stSidebar"] .stDownloadButton > button p,
section[data-testid="stSidebar"] .stDownloadButton > button span {
    background: rgba(10,20,32,0.55) !important;
    color: #d6e6f0 !important;
    border: 1px solid rgba(103,232,249,0.28) !important;
}
section[data-testid="stSidebar"] .stDownloadButton > button:hover {
    background: rgba(103,232,249,0.14) !important;
    border-color: rgba(103,232,249,0.55) !important;
    color: #e8f7fc !important;
}

/* =========================================================================
   v10 §8.2 — Sidebar Selectbox: terminal-grade dark readable control
   The D+20/D+5/D+1 horizon selector lives in the sidebar. This block
   repaints it (and any other sidebar selectbox) as a terminal-style
   control with subtle cyan border, mono value text, and a glowing focus
   state. Dropdown panel inherits the same dark palette.
   ========================================================================= */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] label,
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] label p {
    color: #cbe9f2 !important;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace) !important;
    font-size: 0.70rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background: rgba(10,20,32,0.78) !important;
    border: 1px solid rgba(103,232,249,0.32) !important;
    border-radius: 9px !important;
    min-height: 40px !important;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace) !important;
    color: #e8f7fc !important;
    box-shadow: inset 0 1px 0 rgba(103,232,249,0.10) !important;
    transition: all 0.18s ease !important;
}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div:hover {
    background: rgba(10,20,32,0.90) !important;
    border-color: rgba(103,232,249,0.55) !important;
}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {
    border-color: rgba(103,232,249,0.80) !important;
    box-shadow: 0 0 0 3px rgba(103,232,249,0.18) !important;
}
/* Value text colour — v11.5.6: broaden selectors so the closed-state
   "single-value" <div> (not a span/input/tag) also gets the light palette.
   Streamlit's baseweb select renders the selected label inside a nested
   <div> that inherits color from the outer control; force all descendants
   to light cyan-white so the dark track never reads black-on-black. */
section[data-testid="stSidebar"] div[data-baseweb="select"] [data-baseweb="tag"],
section[data-testid="stSidebar"] div[data-baseweb="select"] input,
section[data-testid="stSidebar"] div[data-baseweb="select"] span,
section[data-testid="stSidebar"] div[data-baseweb="select"] div,
section[data-testid="stSidebar"] div[data-baseweb="select"] [class*="singleValue"],
section[data-testid="stSidebar"] div[data-baseweb="select"] [class*="ValueContainer"] {
    color: #e8f7fc !important;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace) !important;
    font-size: 0.84rem !important;
    letter-spacing: 0.06em !important;
    font-weight: 700 !important;
}
/* Preserve the container's own background/border (overridden above) */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background: rgba(10,20,32,0.78) !important;
    color: #e8f7fc !important;
}
/* Placeholder (when nothing selected) stays dim so the real value pops */
section[data-testid="stSidebar"] div[data-baseweb="select"] [class*="placeholder"] {
    color: #8397ac !important;
    font-weight: 500 !important;
}
section[data-testid="stSidebar"] div[data-baseweb="select"] svg {
    color: #67e8f9 !important;
}

/* =========================================================================
   v11.5.6 §8.2b — Selectbox POPOVER (dropdown list) dark-readable override
   The popover renders OUTSIDE the sidebar via React portal, so it doesn't
   inherit sidebar-scoped rules. Target it globally by baseweb attributes
   and repaint as a terminal-style dropdown with cyan accent on the
   highlighted/selected item. Fixes black-on-black unreadable menu.
   ========================================================================= */
div[data-baseweb="popover"] ul[role="listbox"],
div[data-baseweb="popover"] [data-baseweb="menu"] ul,
div[data-baseweb="popover"] [data-baseweb="menu"] {
    background: linear-gradient(180deg, rgba(12,22,36,0.98), rgba(8,16,28,0.98)) !important;
    border: 1px solid rgba(103,232,249,0.34) !important;
    border-radius: 10px !important;
    box-shadow:
        0 14px 40px rgba(0,0,0,0.55),
        0 0 22px rgba(103,232,249,0.18),
        inset 0 1px 0 rgba(103,232,249,0.16) !important;
    padding: 4px !important;
    backdrop-filter: blur(6px) !important;
}
div[data-baseweb="popover"] ul[role="listbox"] li,
div[data-baseweb="popover"] [data-baseweb="menu"] li {
    background: transparent !important;
    color: #cfe2ee !important;
    font-family: var(--gl-font-mono, 'JetBrains Mono', ui-monospace, monospace) !important;
    font-size: 0.84rem !important;
    letter-spacing: 0.04em !important;
    padding: 8px 12px !important;
    border-radius: 6px !important;
    transition: all 0.15s ease !important;
    position: relative !important;
}
div[data-baseweb="popover"] ul[role="listbox"] li > *,
div[data-baseweb="popover"] [data-baseweb="menu"] li > * {
    color: #cfe2ee !important;
}
/* Hover state — cyan highlight strip */
div[data-baseweb="popover"] ul[role="listbox"] li:hover,
div[data-baseweb="popover"] [data-baseweb="menu"] li:hover,
div[data-baseweb="popover"] ul[role="listbox"] li[aria-selected="true"],
div[data-baseweb="popover"] [data-baseweb="menu"] li[aria-selected="true"] {
    background: linear-gradient(90deg, rgba(103,232,249,0.18), rgba(103,232,249,0.04)) !important;
    color: #e8f7fc !important;
    box-shadow: inset 2px 0 0 #67e8f9 !important;
}
div[data-baseweb="popover"] ul[role="listbox"] li:hover > *,
div[data-baseweb="popover"] [data-baseweb="menu"] li:hover > *,
div[data-baseweb="popover"] ul[role="listbox"] li[aria-selected="true"] > *,
div[data-baseweb="popover"] [data-baseweb="menu"] li[aria-selected="true"] > * {
    color: #e8f7fc !important;
}

/* =========================================================================
   v11.5.7 §8.3 — Sidebar Slider: Eclipse / Spirit-Blossom HUD dial
   Inspired by LoL Eclipse (幽冥煞星) + targeting-HUD aesthetics.
   Design elements:
     · hexagonal thumb with dual-chroma core (violet → cyan → white)
     · orbiting halo ring around the thumb (conic-gradient spin)
     · violet-to-cyan active fill with white scan-streak sweeping across
     · deep-void track with violet hairline + micro tick grid wash
     · bracket-framed value bubble in deep-space violet
     · min/max labels wrapped in [ … ] runic glyph frame
   Scoped to sidebar so main-canvas sliders stay on the light theme.
   ========================================================================= */
@keyframes gl-slider-scan {
    0%   { background-position: -120% 0, 0 0; }
    100% { background-position: 220% 0, 0 0; }
}
@keyframes gl-slider-thumb-pulse {
    0%, 100% {
        filter:
            drop-shadow(0 0 4px rgba(103,232,249,0.55))
            drop-shadow(0 0 10px rgba(139,92,246,0.45));
    }
    50% {
        filter:
            drop-shadow(0 0 8px rgba(103,232,249,0.85))
            drop-shadow(0 0 18px rgba(139,92,246,0.70));
    }
}
/* v11.5.8 — wrap the entire slider as a standalone framed cartridge.
   The whole stSlider element becomes a unified module (label + track +
   thumb + min/max labels inside one dark violet panel with cyan frame),
   instead of the rail floating over a bare sidebar background. */
section[data-testid="stSidebar"] div[data-testid="stSlider"] {
    position: relative !important;
    padding: 10px 14px 10px 14px !important;
    margin: 6px 0 !important;
    background:
        linear-gradient(180deg, rgba(14,8,28,0.85), rgba(8,4,18,0.92)) !important;
    border: 1px solid rgba(139,92,246,0.28) !important;
    border-radius: 10px !important;
    box-shadow:
        0 0 12px rgba(103,232,249,0.10),
        inset 0 1px 0 rgba(167,139,250,0.18),
        inset 0 0 0 1px rgba(103,232,249,0.06) !important;
}
/* Corner bracket notches on the cartridge frame */
section[data-testid="stSidebar"] div[data-testid="stSlider"]::before,
section[data-testid="stSidebar"] div[data-testid="stSlider"]::after {
    content: "";
    position: absolute;
    width: 8px;
    height: 8px;
    border-color: rgba(103,232,249,0.55);
    pointer-events: none;
}
section[data-testid="stSidebar"] div[data-testid="stSlider"]::before {
    top: 4px; left: 4px;
    border-top: 1px solid; border-left: 1px solid;
    border-top-left-radius: 3px;
}
section[data-testid="stSidebar"] div[data-testid="stSlider"]::after {
    bottom: 4px; right: 4px;
    border-bottom: 1px solid; border-right: 1px solid;
    border-bottom-right-radius: 3px;
}
section[data-testid="stSidebar"] div[data-testid="stSlider"] label,
section[data-testid="stSidebar"] div[data-testid="stSlider"] label p {
    color: #cbe9f2 !important;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace) !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    margin-bottom: 4px !important;
}
/* Slider track container — tick wash removed in v11.5.8 per request */
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-baseweb="slider"] {
    position: relative !important;
    padding-top: 12px !important;
    padding-bottom: 4px !important;
    background: transparent !important;
}
/* v11.5.9 — force every intermediate wrapper div INSIDE the cartridge to be
   fully transparent so ONLY the outer violet frame + the inner rail +
   thumb are visible.  The user reported a clearly-visible lighter violet
   rectangle in the middle of the cartridge — that is one of the baseweb
   wrapper divs carrying its own background.  Blanket-zap them but keep
   the track ([role=progressbar]), active fill, thumb ([role=slider]),
   value bubble, and tick bar intact. */
section[data-testid="stSidebar"] div[data-testid="stSlider"] > div,
section[data-testid="stSidebar"] div[data-testid="stSlider"] > div > div,
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-baseweb="slider"] > div {
    background: transparent !important;
    background-color: transparent !important;
    box-shadow: none !important;
    border: none !important;
}
/* Re-assert the track, active fill, thumb, value bubble as non-transparent
   (they were intentionally styled above; this guards against the blanket
   rule above accidentally resetting them on baseweb DOM changes). */
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[role="progressbar"] {
    background:
        linear-gradient(180deg, rgba(10,4,20,0.95), rgba(20,12,40,0.92)) !important;
    box-shadow:
        inset 0 0 0 1px rgba(139,92,246,0.32),
        inset 0 1px 4px rgba(0,0,0,0.70),
        0 0 0 1px rgba(103,232,249,0.08) !important;
}
/* Track (unfilled portion) — deep violet-black void with hairline */
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-baseweb="slider"] div[role="progressbar"],
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-baseweb="slider"] > div > div:first-child {
    background:
        linear-gradient(180deg, rgba(10,4,20,0.95), rgba(20,12,40,0.92)) !important;
    box-shadow:
        inset 0 0 0 1px rgba(139,92,246,0.32),
        inset 0 1px 4px rgba(0,0,0,0.70),
        0 0 0 1px rgba(103,232,249,0.08) !important;
    height: 7px !important;
    border-radius: 4px !important;
    position: relative !important;
    z-index: 1 !important;
}
/* Active fill portion — violet→cyan gradient with animated scan-streak */
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-baseweb="slider"] div[role="slider"] ~ div,
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-baseweb="slider"] > div > div:nth-child(2) {
    background:
        linear-gradient(90deg,
            transparent 0%,
            rgba(255,255,255,0.60) 50%,
            transparent 100%) ,
        linear-gradient(90deg,
            #4c1d95 0%,
            #7c3aed 22%,
            #8b5cf6 42%,
            #22d3ee 72%,
            #67e8f9 100%) !important;
    background-size: 35% 100%, 100% 100% !important;
    background-repeat: no-repeat, no-repeat !important;
    background-position: -120% 0, 0 0 !important;
    animation: gl-slider-scan 2.6s linear infinite !important;
    box-shadow:
        0 0 10px rgba(139,92,246,0.55),
        0 0 18px rgba(103,232,249,0.35),
        inset 0 1px 0 rgba(255,255,255,0.22) !important;
    height: 7px !important;
    border-radius: 4px !important;
    position: relative !important;
    z-index: 2 !important;
}
/* Thumb — hexagonal core (clip-path) with dual-chroma radial gradient
   The hex silhouette is produced by clip-path; drop-shadow filters follow
   the clipped shape, so the cyan+violet glow aura hugs the hex edge for
   the Eclipse / Spirit-Blossom feel. */
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[role="slider"] {
    background:
        radial-gradient(circle at 50% 50%,
            #ffffff 0%,
            #e0e7ff 12%,
            #a78bfa 28%,
            #8b5cf6 46%,
            #22d3ee 70%,
            #4c1d95 100%) !important;
    border: none !important;
    clip-path: polygon(50% 0%, 93% 25%, 93% 75%, 50% 100%, 7% 75%, 7% 25%) !important;
    width: 22px !important;
    height: 22px !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    animation: gl-slider-thumb-pulse 2.4s ease-in-out infinite !important;
    transition: transform 0.18s ease, filter 0.18s ease !important;
    position: relative !important;
    z-index: 4 !important;
    outline: none !important;
}
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[role="slider"]:hover,
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[role="slider"]:focus {
    transform: scale(1.22);
    animation-play-state: paused !important;
    filter:
        drop-shadow(0 0 6px #ffffff)
        drop-shadow(0 0 14px rgba(103,232,249,0.95))
        drop-shadow(0 0 24px rgba(139,92,246,0.80)) !important;
}
/* Value bubble above thumb — deep-space violet plate with cyan frame */
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-baseweb="slider"] [role="slider"] + div {
    background:
        linear-gradient(180deg, rgba(28,14,54,0.98), rgba(10,6,24,0.98)) !important;
    color: #e0e7ff !important;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace) !important;
    font-size: 0.76rem !important;
    font-weight: 700 !important;
    border: 1px solid rgba(139,92,246,0.60) !important;
    border-radius: 5px !important;
    padding: 2px 10px !important;
    letter-spacing: 0.10em !important;
    text-shadow:
        0 0 6px rgba(103,232,249,0.55),
        0 0 10px rgba(139,92,246,0.35) !important;
    box-shadow:
        0 0 12px rgba(139,92,246,0.30),
        0 0 22px rgba(103,232,249,0.15),
        inset 0 1px 0 rgba(167,139,250,0.30) !important;
}
/* Min/Max end-labels — bracket framing with violet glow */
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-testid="stTickBar"] {
    padding: 3px 0 !important;
}
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-testid="stTickBar"],
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-testid="stTickBar"] div {
    color: #a78bfa !important;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace) !important;
    font-size: 0.66rem !important;
    letter-spacing: 0.14em !important;
    font-weight: 600 !important;
    text-shadow: 0 0 4px rgba(139,92,246,0.45) !important;
}
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-testid="stTickBar"] div:first-child::before {
    content: "[ ";
    color: rgba(103,232,249,0.70);
}
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-testid="stTickBar"] div:last-child::after {
    content: " ]";
    color: rgba(103,232,249,0.70);
}

/* =========================================================================
   v11.5.7 §L1 — Layout Lock
   Freeze the sidebar at a fixed width and disable the drag-resize handle so
   users can't accidentally change the canvas width and break chart/image
   framing. Also disables the browser's native resize affordance on any
   resizable surfaces (textareas, dataframe cells) so the UI renders
   identically every session. Keep MANUAL button legibility by pinning the
   sidebar at 300px which comfortably fits the 0.66rem mono label.
   ========================================================================= */
section[data-testid="stSidebar"] {
    width: 300px !important;
    min-width: 300px !important;
    max-width: 300px !important;
    flex: 0 0 300px !important;
    resize: none !important;
}
section[data-testid="stSidebar"] > div:first-child {
    width: 300px !important;
    min-width: 300px !important;
    max-width: 300px !important;
}
/* Hide / neutralise the sidebar resize-handle (multiple baseweb versions) */
[data-testid="stSidebarResizeHandle"],
section[data-testid="stSidebar"] [data-testid*="ResizeHandle" i],
section[data-testid="stSidebar"] > div[role="separator"],
section[data-testid="stSidebar"] div[role="separator"][style*="cursor"] {
    display: none !important;
    pointer-events: none !important;
    width: 0 !important;
    opacity: 0 !important;
    cursor: default !important;
}
/* Freeze any element the browser marks resizable (textareas, etc.) */
textarea,
[data-testid="stTextArea"] textarea,
[style*="resize: both"],
[style*="resize:both"],
[style*="resize: vertical"],
[style*="resize:vertical"],
[style*="resize: horizontal"],
[style*="resize:horizontal"] {
    resize: none !important;
}
/* Lock dataframe column resizers so the grid can't be dragged wider */
div[data-testid="stDataFrame"] [data-testid*="Resizer"],
div[data-testid="stDataFrameResizable"] [role="separator"] {
    pointer-events: none !important;
    cursor: default !important;
}
/* Plotly: already use_container_width=True — keep images/charts from
   overflowing their containers, and prevent the modebar zoom/autoscale
   from visually resizing the plot beyond its box. */
div[data-testid="stPlotlyChart"],
div[data-testid="stPlotlyChart"] > div,
div[data-testid="stPlotlyChart"] .plot-container {
    max-width: 100% !important;
    overflow: hidden !important;
}
div[data-testid="stImage"] img,
div[data-testid="element-container"] img {
    max-width: 100% !important;
    height: auto !important;
}

/* =========================================================================
   v10 §11 — Tabs: dark base state in sidebar; light-canvas readable in main
   ========================================================================= */
section[data-testid="stSidebar"] div[data-baseweb="tab-list"] button[role="tab"],
section[data-testid="stSidebar"] div[data-baseweb="tab-list"] button[role="tab"] p {
    color: #b4ccdf !important;
}
section[data-testid="stSidebar"] div[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"],
section[data-testid="stSidebar"] div[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"] p {
    color: #67e8f9 !important;
    font-weight: 700 !important;
}

/* =========================================================================
   v10 §7 — Number-input + text-input base state fixes (readable in sidebar)
   ========================================================================= */
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input,
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input {
    background: rgba(10,20,32,0.78) !important;
    color: #e8f7fc !important;
    border: 1px solid rgba(103,232,249,0.32) !important;
    border-radius: 9px !important;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace) !important;
}
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input:focus,
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input:focus {
    border-color: rgba(103,232,249,0.80) !important;
    box-shadow: 0 0 0 3px rgba(103,232,249,0.18) !important;
}

/* =========================================================================
   v11 §4a — Native st.warning / st.info / st.success / st.error alerts
   as dark-glint terminal callouts (fixes invisible yellow-on-yellow text).
   BaseWeb's default notification keeps inheriting the page colour stack
   which lands on light-bg + light-text on some browser profiles. Anchor
   the colour explicitly + add glint accents so each alert reads as a
   kind-specific terminal chip.
   ========================================================================= */
div[data-baseweb="notification"] {
    background: linear-gradient(180deg, rgba(15,23,37,0.95) 0%, rgba(10,20,32,0.95) 100%) !important;
    border: 1px solid rgba(167,139,250,0.45) !important;
    border-left: 3px solid #a78bfa !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.28), inset 0 1px 0 rgba(167,139,250,0.10) !important;
    font-family: var(--gl-font-sans, 'Inter', sans-serif) !important;
}
div[data-baseweb="notification"],
div[data-baseweb="notification"] > div,
div[data-baseweb="notification"] p,
div[data-baseweb="notification"] span,
div[data-baseweb="notification"] a {
    color: #ddd6fe !important;
    font-weight: 500 !important;
}
div[data-baseweb="notification"] svg,
div[data-baseweb="notification"] [data-testid="stIcon"] {
    color: #a78bfa !important;
    fill: #a78bfa !important;
}
/* Kind-specific accents — Streamlit tags the notification div with kind="*" */
div[data-baseweb="notification"][kind="info"],
div[data-baseweb="notification"].stAlertContainer-info {
    border-color: rgba(103,232,249,0.45) !important;
    border-left-color: #67e8f9 !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.28), inset 0 1px 0 rgba(103,232,249,0.10) !important;
}
div[data-baseweb="notification"][kind="info"],
div[data-baseweb="notification"][kind="info"] > div,
div[data-baseweb="notification"][kind="info"] p,
div[data-baseweb="notification"].stAlertContainer-info p {
    color: #cffafe !important;
}
div[data-baseweb="notification"][kind="info"] svg {
    color: #67e8f9 !important;
    fill: #67e8f9 !important;
}
div[data-baseweb="notification"][kind="success"],
div[data-baseweb="notification"].stAlertContainer-success {
    border-color: rgba(16,185,129,0.45) !important;
    border-left-color: #10b981 !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.28), inset 0 1px 0 rgba(16,185,129,0.10) !important;
}
div[data-baseweb="notification"][kind="success"],
div[data-baseweb="notification"][kind="success"] > div,
div[data-baseweb="notification"][kind="success"] p {
    color: #a7f3d0 !important;
}
div[data-baseweb="notification"][kind="success"] svg {
    color: #10b981 !important;
    fill: #10b981 !important;
}
div[data-baseweb="notification"][kind="error"],
div[data-baseweb="notification"].stAlertContainer-error {
    border-color: rgba(244,63,94,0.45) !important;
    border-left-color: #f43f5e !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.28), inset 0 1px 0 rgba(244,63,94,0.10) !important;
}
div[data-baseweb="notification"][kind="error"],
div[data-baseweb="notification"][kind="error"] > div,
div[data-baseweb="notification"][kind="error"] p {
    color: #fecaca !important;
}
div[data-baseweb="notification"][kind="error"] svg {
    color: #f43f5e !important;
    fill: #f43f5e !important;
}

/* =========================================================================
   v11 §3 — Glint terminal dataframe (fallback styling for st.dataframe)
   When pages can't switch to render_glint_table (e.g. interactive sorting
   needed), anchor Streamlit dataframe wrappers to the dark terminal palette.
   ========================================================================= */
div[data-testid="stDataFrame"],
div[data-testid="stDataFrameResizable"] {
    border: 1px solid rgba(103,232,249,0.24) !important;
    border-radius: 10px !important;
    background: linear-gradient(180deg, rgba(15,23,37,0.55) 0%, rgba(10,20,32,0.55) 100%) !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.18) !important;
    overflow: hidden;
}

/* =========================================================================
   v11 §3 — render_glint_table: native-looking Glint terminal table
   ========================================================================= */
.gl-term-table-wrap {
    margin: 10px 0 14px 0;
    border: 1px solid rgba(103,232,249,0.28);
    border-radius: 12px;
    background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(10,20,32,0.92) 100%);
    box-shadow:
        0 4px 18px rgba(2,6,23,0.32),
        inset 0 1px 0 rgba(103,232,249,0.14);
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: thin;
}
.gl-term-table-wrap::-webkit-scrollbar { height: 6px; }
.gl-term-table-wrap::-webkit-scrollbar-thumb {
    background: rgba(103,232,249,0.28);
    border-radius: 3px;
}
.gl-term-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--gl-font-sans, 'Inter', sans-serif);
    font-size: 0.86rem;
    color: #cfe2ee;
    table-layout: auto;
}
.gl-term-table thead tr {
    background: linear-gradient(180deg, rgba(103,232,249,0.16) 0%, rgba(103,232,249,0.05) 100%);
    border-bottom: 1px solid rgba(103,232,249,0.38);
}
.gl-term-table thead th {
    padding: 10px 16px;
    text-align: left;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace);
    font-size: 0.70rem;
    font-weight: 800;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #cffafe;
    text-shadow: 0 0 10px rgba(103,232,249,0.35);
    white-space: nowrap;
}
.gl-term-table tbody tr {
    border-bottom: 1px solid rgba(103,232,249,0.08);
    transition: background 0.18s ease;
}
.gl-term-table tbody tr:last-child { border-bottom: none; }
.gl-term-table tbody tr:hover {
    background: rgba(103,232,249,0.05);
}
.gl-term-table tbody td {
    padding: 9px 16px;
    vertical-align: top;
    line-height: 1.46;
}
.gl-term-table tbody td.gl-term-mono {
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace);
    font-size: 0.82rem;
    color: #e8f7fc;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.gl-term-table tbody td.gl-term-accent-cyan {
    color: #67e8f9;
    font-weight: 600;
}
.gl-term-table tbody td.gl-term-accent-emerald {
    color: #34d399;
    font-weight: 600;
}
.gl-term-table tbody td.gl-term-accent-amber {
    color: #c4b5fd;
    font-weight: 600;
}
.gl-term-table tbody td.gl-term-accent-rose {
    color: #fda4af;
    font-weight: 600;
}
.gl-term-table-title {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px 8px 16px;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #cffafe;
    border-bottom: 1px dashed rgba(103,232,249,0.24);
}
.gl-term-table-title::before {
    content: "";
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #67e8f9;
    box-shadow: 0 0 8px rgba(103,232,249,0.70);
}
.gl-term-table-meta {
    padding: 8px 16px;
    font-family: var(--gl-font-mono, 'JetBrains Mono', monospace);
    font-size: 0.68rem;
    letter-spacing: 0.08em;
    color: #8397ac;
    border-top: 1px solid rgba(103,232,249,0.10);
}

/* =========================================================================
   v11.4 §A — Legacy light-theme hero/chip override (20-person-team audit)
   The base `.gl-hero`, `.gl-chip-explain` and `.gl-chip` classes were
   designed for the original glint-LIGHT canvas (white hero surface, dark
   text). When pages 0 & 8 embed them on dark-terminal pages they appear
   as bright white blocks ripping a hole through the dark theme. This
   override layer repaints them as glint-dark terminal heroes so every
   hero in the app looks consistent.
   ========================================================================= */
.gl-hero {
    background:
        radial-gradient(ellipse at 10% 10%, rgba(103,232,249,0.10) 0%, transparent 60%),
        radial-gradient(ellipse at 90% 90%, rgba(167,139,250,0.08) 0%, transparent 60%),
        linear-gradient(180deg, rgba(15,23,37,0.94) 0%, rgba(8,16,32,0.98) 100%) !important;
    border: 1px solid rgba(103,232,249,0.22) !important;
    box-shadow: 0 0 0 1px rgba(103,232,249,0.08),
                0 8px 30px rgba(2,6,23,0.45) !important;
    color: #cfe2ee !important;
}
.gl-hero::before {
    background: radial-gradient(circle, rgba(103,232,249,0.12), transparent 70%) !important;
}
.gl-hero-orb {
    background: radial-gradient(circle, rgba(167,139,250,0.12), transparent 70%) !important;
}
.gl-hero-eyebrow {
    background: rgba(103,232,249,0.10) !important;
    color: #67e8f9 !important;
    border: 1px solid rgba(103,232,249,0.30) !important;
}
.gl-hero-title {
    background: linear-gradient(135deg, #E8F7FC 0%, #67e8f9 55%, #a78bfa 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}
.gl-hero-subtitle {
    color: #cfe2ee !important;
}
.gl-hero-subtitle strong {
    color: #E8F7FC !important;
}
.gl-hero-accent {
    background: linear-gradient(135deg, #67e8f9 0%, #a78bfa 55%, #6ee7b7 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}
/* chip-explain grid items (Pages 0 & 8 hero cards) */
.gl-chip-explain .item {
    background: rgba(10,20,32,0.72) !important;
    border: 1px solid rgba(103,232,249,0.18) !important;
    border-left: 3px solid #67e8f9 !important;
}
.gl-chip-explain .item:hover {
    border-left-color: #a78bfa !important;
    box-shadow: 0 0 0 1px rgba(167,139,250,0.22),
                0 8px 22px rgba(2,6,23,0.45) !important;
}
.gl-chip-explain .item .head { color: #67e8f9 !important; }
.gl-chip-explain .item .desc { color: #cfe2ee !important; }
.gl-chip-explain .item.vio              { border-left-color: #a78bfa !important; }
.gl-chip-explain .item.vio .head        { color: #c4b5fd !important; }
.gl-chip-explain .item.ok               { border-left-color: #6ee7b7 !important; }
.gl-chip-explain .item.ok  .head        { color: #6ee7b7 !important; }
.gl-chip-explain .item.warn             { border-left-color: #ddd6fe !important; }
.gl-chip-explain .item.warn .head       { color: #ddd6fe !important; }
/* Generic .gl-chip pill — terminal dark base */
.gl-chip {
    background: rgba(10,20,32,0.68) !important;
    color: #cfe2ee !important;
    border: 1px solid rgba(103,232,249,0.22) !important;
}
.gl-chip.primary { background: rgba(103,232,249,0.10) !important; color: #67e8f9 !important; border-color: rgba(103,232,249,0.35) !important; }
.gl-chip.violet  { background: rgba(167,139,250,0.10) !important; color: #c4b5fd !important; border-color: rgba(167,139,250,0.35) !important; }
.gl-chip.ok      { background: rgba(16,185,129,0.12) !important; color: #6ee7b7 !important; border-color: rgba(16,185,129,0.38) !important; }
.gl-chip.warn    { background: rgba(167,139,250,0.12) !important; color: #ddd6fe !important; border-color: rgba(167,139,250,0.38) !important; }
.gl-chip.danger  { background: rgba(244,63,94,0.12) !important; color: #fda4af !important; border-color: rgba(244,63,94,0.38) !important; }
/* 9-pillar badges — dark terminal variant */
.gl-pillar[data-p="trend"] { background: rgba(37,99,235,0.14)  !important; color: #93c5fd !important; }
.gl-pillar[data-p="fund"]  { background: rgba(16,185,129,0.14) !important; color: #6ee7b7 !important; }
.gl-pillar[data-p="val"]   { background: rgba(217,70,239,0.14) !important; color: #f0abfc !important; }
.gl-pillar[data-p="event"] { background: rgba(167,139,250,0.14) !important; color: #ddd6fe !important; }
.gl-pillar[data-p="risk"]  { background: rgba(244,63,94,0.14)  !important; color: #fda4af !important; }
.gl-pillar[data-p="chip"]  { background: rgba(99,102,241,0.14) !important; color: #a5b4fc !important; }
.gl-pillar[data-p="ind"]   { background: rgba(6,182,212,0.14)  !important; color: #67e8f9 !important; }
.gl-pillar[data-p="txt"]   { background: rgba(167,139,250,0.14) !important; color: #c4b5fd !important; }
.gl-pillar[data-p="sent"]  { background: rgba(236,72,153,0.14) !important; color: #f9a8d4 !important; }

/* =========================================================================
   v11.5 §A — Main-canvas CSS variable FLIP (root fix for dark-on-dark)
   The THEME Python dict still ships light-theme values:
     bg_primary=#fafbfc · bg_surface=#ffffff · text_primary=#0f172a
   Every v7-v11 component that uses `var(--gl-surface)` / `var(--gl-text)`
   therefore renders as "light bg + dark text". That worked when the
   canvas was light. Since v8 darkened the canvas via panels/hero/shell,
   ~862 DOM elements on the main canvas still compute color #0f172a
   (dark-on-dark invisible — live-probed 2026-04-21).

   Strategy: redefine the tokens at `[data-testid="stMain"]` scope.
   This re-routes every `var(--gl-*)` usage to dark-theme values —
   single change, ~40 components fixed via CSS cascade. Sidebar tokens
   are NOT touched (sidebar has its own palette in inject_custom_css).
   ========================================================================= */
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    /* Text — all three tiers flipped bright for dark canvas */
    --gl-text:       #E8F7FC !important;   /* was #0f172a  */
    --gl-text-2:     #cfe2ee !important;   /* was #475569  */
    --gl-text-3:     #b4ccdf !important;   /* was #94a3b8  */
    /* Surfaces — flip to glint-dark gradient base */
    --gl-bg:         #060A12 !important;   /* was #fafbfc  */
    --gl-surface:    #0F1725 !important;   /* was #ffffff  */
    --gl-subtle:     rgba(10,20,32,0.72) !important;   /* was #f1f5f9 */
    --gl-tint:       rgba(15,23,37,0.60) !important;   /* was #f8fafc */
    --gl-overlay:    rgba(10,20,32,0.86) !important;
    /* Borders — cyan-tint for glint terminal feel */
    --gl-border:     rgba(103,232,249,0.22) !important;
    --gl-border-str: rgba(103,232,249,0.42) !important;
    color: #E8F7FC;
}
/* Base text elements on main canvas — guarantee light color even when
   a rule uses `color: inherit` or an explicit hex like #0f172a that
   the variable flip can't reach. */
[data-testid="stMain"] p,
[data-testid="stMain"] li,
[data-testid="stMain"] label,
[data-testid="stMain"] .stMarkdown,
[data-testid="stMain"] .stMarkdown p,
[data-testid="stMain"] .stMarkdown li,
[data-testid="stMain"] .stMarkdown strong,
[data-testid="stMain"] .stMarkdown em,
[data-testid="stMain"] .stMarkdown code {
    color: #E8F7FC;
}
/* Captions and small text — slightly dimmer for hierarchy, still readable */
[data-testid="stMain"] [data-testid="stCaptionContainer"],
[data-testid="stMain"] .stCaption,
[data-testid="stMain"] small,
[data-testid="stMain"] figcaption {
    color: #b4ccdf !important;
}
/* stMetric (KPI cards) — label+value+delta all light */
[data-testid="stMain"] [data-testid="stMetric"] [data-testid="stMetricLabel"],
[data-testid="stMain"] [data-testid="stMetric"] [data-testid="stMetricLabel"] p {
    color: #67e8f9 !important;
}
[data-testid="stMain"] [data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #E8F7FC !important;
}
[data-testid="stMain"] [data-testid="stMetric"] [data-testid="stMetricDelta"] {
    color: #6ee7b7 !important;
}

/* =========================================================================
   v11.5 §B — Hardcoded light-bg component overrides
   These components use explicit hex like `#ffffff` / `#f8fafc` in their
   base definition, so the variable flip above can't reach them.
   ========================================================================= */
/* Trust strip (hero metadata row) */
[data-testid="stMain"] .gl-trust-strip {
    background: linear-gradient(180deg, rgba(15,23,37,0.88) 0%, rgba(8,16,32,0.94) 100%) !important;
    border: 1px solid rgba(103,232,249,0.22) !important;
    box-shadow: 0 1px 2px rgba(2,6,23,0.40) !important;
}
[data-testid="stMain"] .gl-trust-cell {
    background: rgba(10,20,32,0.72) !important;
    border: 1px solid rgba(103,232,249,0.20) !important;
    color: #cfe2ee !important;
}
/* 9-pillar bar pills (.gl-pb-pill — pillar contribution charts) */
[data-testid="stMain"] .gl-pb-pill[data-p="trend"] { background: rgba(37,99,235,0.14)  !important; color: #93c5fd !important; }
[data-testid="stMain"] .gl-pb-pill[data-p="fund"]  { background: rgba(16,185,129,0.14) !important; color: #6ee7b7 !important; }
[data-testid="stMain"] .gl-pb-pill[data-p="val"]   { background: rgba(217,70,239,0.14) !important; color: #f0abfc !important; }
[data-testid="stMain"] .gl-pb-pill[data-p="event"] { background: rgba(167,139,250,0.14) !important; color: #ddd6fe !important; }
[data-testid="stMain"] .gl-pb-pill[data-p="risk"]  { background: rgba(244,63,94,0.14)  !important; color: #fda4af !important; }
[data-testid="stMain"] .gl-pb-pill[data-p="chip"]  { background: rgba(99,102,241,0.14) !important; color: #a5b4fc !important; }
[data-testid="stMain"] .gl-pb-pill[data-p="ind"]   { background: rgba(6,182,212,0.14)  !important; color: #67e8f9 !important; }
[data-testid="stMain"] .gl-pb-pill[data-p="txt"]   { background: rgba(167,139,250,0.14) !important; color: #c4b5fd !important; }
[data-testid="stMain"] .gl-pb-pill[data-p="sent"]  { background: rgba(236,72,153,0.14) !important; color: #f9a8d4 !important; }
/* Industry sector chips (.gl-sector) */
[data-testid="stMain"] .gl-sector[data-s="半導體"]    { background: rgba(37,99,235,0.14)  !important; color: #93c5fd !important; }
[data-testid="stMain"] .gl-sector[data-s="電子零組件"]  { background: rgba(99,102,241,0.14) !important; color: #a5b4fc !important; }
[data-testid="stMain"] .gl-sector[data-s="金融"]      { background: rgba(16,185,129,0.14) !important; color: #6ee7b7 !important; }
[data-testid="stMain"] .gl-sector[data-s="生技醫療"]   { background: rgba(217,70,239,0.14) !important; color: #f0abfc !important; }
[data-testid="stMain"] .gl-sector[data-s="傳產"]      { background: rgba(167,139,250,0.14) !important; color: #ddd6fe !important; }
[data-testid="stMain"] .gl-sector[data-s="航運"]      { background: rgba(6,182,212,0.14)  !important; color: #67e8f9 !important; }
[data-testid="stMain"] .gl-sector[data-s="通訊網路"]   { background: rgba(167,139,250,0.14) !important; color: #c4b5fd !important; }
[data-testid="stMain"] .gl-sector[data-s="汽車"]      { background: rgba(244,63,94,0.14)  !important; color: #fda4af !important; }
/* Download button on main canvas — was forced #ffffff / #0f172a in v10 §7 */
[data-testid="stMain"] .stDownloadButton > button,
[data-testid="stMain"] .stDownloadButton > button p,
[data-testid="stMain"] .stDownloadButton > button span {
    background: rgba(10,20,32,0.72) !important;
    color: #E8F7FC !important;
    border: 1px solid rgba(103,232,249,0.28) !important;
}
[data-testid="stMain"] .stDownloadButton > button:hover {
    background: rgba(103,232,249,0.14) !important;
    border-color: rgba(103,232,249,0.55) !important;
    color: #E8F7FC !important;
}
/* Radio labels on main canvas — dark canvas needs light text */
[data-testid="stMain"] div[data-testid="stRadio"] label,
[data-testid="stMain"] div[data-testid="stRadio"] label p,
[data-testid="stMain"] div[data-testid="stRadio"] label span {
    color: #E8F7FC !important;
}

/* =========================================================================
   v11.5.1 — Residual offenders found by live-probe (2026-04-21)
   Two components still compute dark text on the dark main canvas:
     · button[data-testid="stTab"] inactive state → #475569 (slate-500)
     · .gl-footer <a> links → #2563eb (too dim on dark canvas)
   ========================================================================= */
/* Streamlit tab inactive state — light muted on dark */
[data-testid="stMain"] button[data-testid="stTab"],
[data-testid="stMain"] button[data-testid="stTab"] p,
[data-testid="stMain"] button[data-testid="stTab"] div[data-testid="stMarkdownContainer"] {
    color: #b4ccdf !important;
}
/* Active tab → brighter cyan accent */
[data-testid="stMain"] button[data-testid="stTab"][aria-selected="true"],
[data-testid="stMain"] button[data-testid="stTab"][aria-selected="true"] p,
[data-testid="stMain"] button[data-testid="stTab"][aria-selected="true"] div[data-testid="stMarkdownContainer"] {
    color: #67e8f9 !important;
}
/* Hover state on main-canvas tabs */
[data-testid="stMain"] button[data-testid="stTab"]:hover,
[data-testid="stMain"] button[data-testid="stTab"]:hover p {
    color: #E8F7FC !important;
}
/* Footer anchor links — cyan accent on dark canvas */
[data-testid="stMain"] .gl-footer a,
[data-testid="stMain"] .page-footer a {
    color: #67e8f9 !important;
    text-decoration: underline dotted rgba(103,232,249,0.4);
    text-underline-offset: 2px;
}
[data-testid="stMain"] .gl-footer a:hover,
[data-testid="stMain"] .page-footer a:hover {
    color: #E8F7FC !important;
    text-decoration-color: rgba(232,247,252,0.7);
}

/* =========================================================================
   v11.5.2 — Legacy light-surface components that pre-date the dark canvas
   flip. With v11.5 turning body text #E8F7FC, any component that still
   renders with `background: #ffffff` (or a near-white pastel) produces
   LIGHT-text-on-LIGHT-bg — invisible.

   Strategy: repaint each offender with the Glint dark panel palette
   (#0F1725 surface on #060A12 canvas, cyan accents). Also override the
   inline-style alert callouts (`#ecfdf5`/`#fffbeb`/`#fef2f2`) via
   attribute-substring selectors so we don't have to touch call sites.
   ========================================================================= */

/* --- A. Global canvas gradient — remove white stop ---------------------- */
/* utils.py line 103 ended at `#ffffff 400px`; that creates a white smear
   at the top of every page. Anchor to the Glint canvas instead.         */
[data-testid="stMain"] .main,
[data-testid="stMain"] .block-container,
div.main,
div.block-container {
    background:
        radial-gradient(ellipse at top left, rgba(37,99,235,0.05) 0%, transparent 50%),
        radial-gradient(ellipse at top right, rgba(124,58,237,0.05) 0%, transparent 50%),
        linear-gradient(180deg, #060A12 0%, #0A1420 400px) !important;
}

/* --- B. Path cards (home 個股觀察 / 量化引擎) --------------------------- */
[data-testid="stMain"] .path-card.path-inv,
[data-testid="stMain"] .path-card.path-qnt {
    background: linear-gradient(135deg, rgba(15,23,37,0.92) 0%, rgba(10,20,32,0.85) 100%) !important;
    border: 1px solid rgba(103,232,249,0.22) !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.35), inset 0 1px 0 rgba(103,232,249,0.08) !important;
}
[data-testid="stMain"] .path-card.path-qnt {
    border-color: rgba(167,139,250,0.28) !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.35), inset 0 1px 0 rgba(167,139,250,0.10) !important;
}
[data-testid="stMain"] .path-card .path-title,
[data-testid="stMain"] .path-card .path-desc,
[data-testid="stMain"] .path-card .path-tags,
[data-testid="stMain"] .path-card .path-tags span {
    color: #E8F7FC !important;
}
[data-testid="stMain"] .path-card .path-desc {
    color: #cfe2ee !important;
}
[data-testid="stMain"] .path-card .path-tags span {
    background: rgba(103,232,249,0.12) !important;
    color: #67e8f9 !important;
    border: 1px solid rgba(103,232,249,0.25) !important;
}
[data-testid="stMain"] .path-card.path-qnt .path-tags span {
    background: rgba(167,139,250,0.14) !important;
    color: #c4b5fd !important;
    border-color: rgba(167,139,250,0.28) !important;
}

/* --- C. Phase chips (current/active state) ------------------------------ */
[data-testid="stMain"] .phase-chip.cur,
[data-testid="stMain"] .phase-chip.current {
    background: linear-gradient(135deg, rgba(37,99,235,0.22) 0%, rgba(124,58,237,0.22) 100%) !important;
    color: #E8F7FC !important;
    border: 1px solid rgba(103,232,249,0.35) !important;
}

/* --- D. Ticker bar — remove mid white stop ------------------------------ */
[data-testid="stMain"] .gl-ticker {
    background: linear-gradient(90deg,
        rgba(15,23,37,0.85) 0%,
        rgba(10,20,32,0.95) 50%,
        rgba(15,23,37,0.85) 100%) !important;
    color: #E8F7FC !important;
    border: 1px solid rgba(103,232,249,0.18) !important;
}

/* --- E. Legacy page heading block (pre-terminal-hero) ------------------- */
[data-testid="stMain"] .gl-page-heading {
    background: linear-gradient(135deg, rgba(15,23,37,0.95) 0%, rgba(6,10,18,0.92) 100%) !important;
    border: 1px solid rgba(103,232,249,0.22) !important;
    color: #E8F7FC !important;
}
[data-testid="stMain"] .gl-page-heading *,
[data-testid="stMain"] .gl-page-heading h1,
[data-testid="stMain"] .gl-page-heading h2,
[data-testid="stMain"] .gl-page-heading h3,
[data-testid="stMain"] .gl-page-heading p {
    color: inherit !important;
}

/* --- F. Panel tint surface --------------------------------------------- */
[data-testid="stMain"] .gl-panel-tint {
    background: linear-gradient(135deg, rgba(15,23,37,0.88) 0%, rgba(10,20,32,0.82) 100%) !important;
    border: 1px solid rgba(103,232,249,0.18) !important;
    color: #E8F7FC !important;
}

/* --- G. System-health light variant (shouldn't render in main, belt&braces) */
[data-testid="stMain"] .gl-syshealth.light,
[data-testid="stMain"] .gl-syshealth {
    background: linear-gradient(180deg, rgba(10,20,32,0.88) 0%, rgba(18,28,43,0.92) 100%) !important;
    color: #E8F7FC !important;
    border-color: rgba(103,232,249,0.18) !important;
}

/* --- H. Inline-style alert callouts (page 0_投資解讀面板) --------------- */
/* Page 0 sets alert_bg = #ecfdf5 | #fffbeb | #fef2f2 via inline styles.
   Catch them via attribute-substring selectors so the call site stays
   untouched and future pastels fall under the same treatment.

   Browsers serialize `#ecfdf5` to `rgb(236, 253, 245)` in the style
   attribute, so we need BOTH the hex form (source) AND the rgb form
   (serialized) — with and without spaces because serialization rules
   differ across engines.                                              */
[data-testid="stMain"] div[style*="#ecfdf5"],
[data-testid="stMain"] div[style*="#fffbeb"],
[data-testid="stMain"] div[style*="#fef2f2"],
[data-testid="stMain"] div[style*="#ECFDF5"],
[data-testid="stMain"] div[style*="#FFFBEB"],
[data-testid="stMain"] div[style*="#FEF2F2"],
[data-testid="stMain"] div[style*="rgb(236, 253, 245)"],
[data-testid="stMain"] div[style*="rgb(255, 251, 235)"],
[data-testid="stMain"] div[style*="rgb(254, 242, 242)"],
[data-testid="stMain"] div[style*="rgb(236,253,245)"],
[data-testid="stMain"] div[style*="rgb(255,251,235)"],
[data-testid="stMain"] div[style*="rgb(254,242,242)"] {
    background: linear-gradient(135deg, rgba(15,23,37,0.92) 0%, rgba(10,20,32,0.86) 100%) !important;
    color: #E8F7FC !important;
}
[data-testid="stMain"] div[style*="#ecfdf5"] *,
[data-testid="stMain"] div[style*="#fffbeb"] *,
[data-testid="stMain"] div[style*="#fef2f2"] *,
[data-testid="stMain"] div[style*="#ECFDF5"] *,
[data-testid="stMain"] div[style*="#FFFBEB"] *,
[data-testid="stMain"] div[style*="#FEF2F2"] *,
[data-testid="stMain"] div[style*="rgb(236, 253, 245)"] *,
[data-testid="stMain"] div[style*="rgb(255, 251, 235)"] *,
[data-testid="stMain"] div[style*="rgb(254, 242, 242)"] *,
[data-testid="stMain"] div[style*="rgb(236,253,245)"] *,
[data-testid="stMain"] div[style*="rgb(255,251,235)"] *,
[data-testid="stMain"] div[style*="rgb(254,242,242)"] * {
    color: #E8F7FC !important;
}
/* Preserve colour coding on the border-left stripe: high = rose,
   elevated = amber, normal = emerald. The original inline `color:`
   on interior spans (if any) already override, so just ensure the
   banner header text is readable.                                     */
[data-testid="stMain"] div[style*="#fef2f2"] strong,
[data-testid="stMain"] div[style*="#FEF2F2"] strong,
[data-testid="stMain"] div[style*="rgb(254, 242, 242)"] strong,
[data-testid="stMain"] div[style*="rgb(254,242,242)"] strong { color: #fda4af !important; }
[data-testid="stMain"] div[style*="#fffbeb"] strong,
[data-testid="stMain"] div[style*="#FFFBEB"] strong,
[data-testid="stMain"] div[style*="rgb(255, 251, 235)"] strong,
[data-testid="stMain"] div[style*="rgb(255,251,235)"] strong { color: #ddd6fe !important; }
[data-testid="stMain"] div[style*="#ecfdf5"] strong,
[data-testid="stMain"] div[style*="#ECFDF5"] strong,
[data-testid="stMain"] div[style*="rgb(236, 253, 245)"] strong,
[data-testid="stMain"] div[style*="rgb(236,253,245)"] strong { color: #6ee7b7 !important; }

/* --- I. Generic .insight-box / .warning-box / .tip-box pastels --------- */
/* Some pages wrap commentary in these classes with near-white or pastel
   backgrounds. Give them dark-panel treatment consistently.             */
[data-testid="stMain"] .insight-box,
[data-testid="stMain"] .warning-box,
[data-testid="stMain"] .tip-box,
[data-testid="stMain"] .info-box,
[data-testid="stMain"] .note-box {
    background: linear-gradient(135deg, rgba(15,23,37,0.88) 0%, rgba(10,20,32,0.82) 100%) !important;
    color: #E8F7FC !important;
    border: 1px solid rgba(103,232,249,0.20) !important;
}
[data-testid="stMain"] .insight-box *,
[data-testid="stMain"] .warning-box *,
[data-testid="stMain"] .tip-box *,
[data-testid="stMain"] .info-box *,
[data-testid="stMain"] .note-box * {
    color: inherit !important;
}
[data-testid="stMain"] .insight-box strong,
[data-testid="stMain"] .tip-box strong { color: #67e8f9 !important; }
[data-testid="stMain"] .warning-box    { border-left: 4px solid #a78bfa !important; }
[data-testid="stMain"] .warning-box strong { color: #ddd6fe !important; }
</style>
"""


def inject_v10_dark_widgets_css():
    """Inject the v10 consolidated dark-widget override layer.

    This single CSS block repaints every widget that appears in a dark
    context (sidebar by default, plus the utility-bar Search) so they
    satisfy the v10 §7 readability rule:

        Interactive blocks must have dark-bg + light-text OR light-bg +
        dark-text. Never dark-bg + dark-text at base state.

    Included overrides:
      · v10 §7  — Expander summary, radio labels, download buttons, tabs
      · v10 §8.2 — Sidebar Selectbox (D+20/D+5/D+1) as terminal control
      · v10 §8.3 — Sidebar Slider as terminal range control (track/thumb/value)
      · v10 §13.3 — Consolidated override layer so patches don't scatter

    Call near the top of every page, right after ``inject_custom_css()``.
    Safe to call multiple times (Streamlit dedupes identical writes).
    """
    st.markdown(_GLINT_V10_DARK_WIDGETS_CSS, unsafe_allow_html=True)


# ============================================================================
# v11 §3 — Glint terminal table renderer (replaces raw st.dataframe
# for static reference tables where we want editorial control over the
# look). Unlike st.dataframe (canvas-based, not CSS-stylable), this emits
# a real <table> so we can apply the Glint dark terminal palette.
# ============================================================================
def render_glint_table(df,
                       *,
                       title: str | None = None,
                       caption: str | None = None,
                       mono_columns: list | None = None,
                       accent_columns: dict | None = None,
                       max_rows: int | None = None) -> None:
    """Render a small reference dataframe as a Glint dark terminal table.

    Use this for editorial / static tables (data dictionaries, legend
    tables, schema tables). For interactive sortable tables with large
    row counts, keep ``st.dataframe`` — it's CSS-accented via v11 §3.

    Args:
        df: pandas DataFrame. Must have string-safe values in cells.
        title: optional header label rendered above the table with a
            cyan terminal dot. Appears as a left-aligned mono header.
        caption: optional footer caption in mono muted colour.
        mono_columns: list of column names to render in the mono accent
            face (good for counts, IDs, numeric codes).
        accent_columns: map of ``{column_name: accent}`` where accent is
            one of ``"cyan" | "emerald" | "amber" | "rose"``. Applies to
            the whole column's body cells.
        max_rows: optional row cap — rows beyond this are elided with
            a footer meta line (e.g. "…{N} more rows").
    """
    import html as _html
    if df is None or len(df) == 0:
        st.markdown(
            '<div class="gl-term-table-wrap">'
            '<div class="gl-term-table-meta">— no rows —</div>'
            '</div>', unsafe_allow_html=True
        )
        return

    mono = set(mono_columns or [])
    accents = dict(accent_columns or {})
    cols = list(df.columns)
    total_rows = len(df)
    shown = df.head(max_rows) if max_rows is not None and total_rows > max_rows else df

    header_cells = "".join(
        f"<th>{_html.escape(str(c))}</th>" for c in cols
    )

    body_rows = []
    for _, row in shown.iterrows():
        tds = []
        for c in cols:
            raw = row[c]
            cell_text = _html.escape("" if raw is None else str(raw))
            classes = []
            if c in mono:
                classes.append("gl-term-mono")
            if c in accents:
                tone = str(accents[c]).lower().strip()
                if tone in {"cyan", "emerald", "amber", "rose"}:
                    classes.append(f"gl-term-accent-{tone}")
            cls_attr = f' class="{" ".join(classes)}"' if classes else ""
            tds.append(f"<td{cls_attr}>{cell_text}</td>")
        body_rows.append(f"<tr>{''.join(tds)}</tr>")

    title_html = (
        f'<div class="gl-term-table-title">{_html.escape(title)}</div>'
        if title else ""
    )
    meta_parts = []
    if max_rows is not None and total_rows > max_rows:
        meta_parts.append(f"... {total_rows - max_rows} more rows")
    if caption:
        meta_parts.append(_html.escape(caption))
    meta_html = (
        f'<div class="gl-term-table-meta">{" · ".join(meta_parts)}</div>'
        if meta_parts else ""
    )

    html_out = (
        '<div class="gl-term-table-wrap">'
        + title_html
        + '<table class="gl-term-table">'
        + f'<thead><tr>{header_cells}</tr></thead>'
        + f'<tbody>{"".join(body_rows)}</tbody>'
        + '</table>'
        + meta_html
        + '</div>'
    )
    st.markdown(html_out, unsafe_allow_html=True)


# --- v7 §18.2 Schema-safe helpers ----------------------------------------
def safe_col(df, primary, fallbacks=(), default=None):
    """Return a Series from ``df`` using a schema-safe lookup chain.

    Tries ``primary`` first, then each name in ``fallbacks`` in order. If
    none are present, returns ``default`` (can be a scalar, Series or
    iterable). This prevents ``KeyError`` crashes when upstream data frames
    evolve — pages should call ``safe_col`` instead of ``df[col]`` whenever
    the column is not strictly guaranteed by a schema contract.

    Example::

        name_series = safe_col(df, "short_name",
                               fallbacks=("company_name", "name"),
                               default=df.get("company_id", ""))
    """
    try:
        import pandas as _pd
    except Exception:
        _pd = None
    # Primary
    if df is not None and hasattr(df, "columns") and primary in df.columns:
        return df[primary]
    if isinstance(fallbacks, str):
        fallbacks = (fallbacks,)
    for fb in (fallbacks or ()):
        if df is not None and hasattr(df, "columns") and fb in df.columns:
            return df[fb]
    # No match — return default verbatim (may be Series/scalar/None)
    return default


def safe_html(value) -> str:
    """Minimal HTML-escape for values interpolated into ``st.markdown(...,
    unsafe_allow_html=True)`` templates.

    Uses :func:`html.escape` with ``quote=True`` so single/double quotes are
    also escaped. ``None`` becomes an empty string. Non-string values are
    coerced via :func:`str`. This prevents accidental tag injection when
    rendering user-supplied or data-derived fragments (e.g. ticker symbols,
    company names) into HTML blocks.
    """
    import html as _html
    if value is None:
        return ""
    return _html.escape(str(value), quote=True)


def safe_get(obj, key, *fallbacks, default=None):
    """Schema-safe dict / object attribute lookup with fallback chain.

    Mirrors :func:`safe_col` but for plain dicts / objects instead of
    DataFrames. Tries ``key`` first, then each name in ``fallbacks`` in
    order. Returns ``default`` if none are present. Handles both
    ``obj[key]`` (mappings) and ``getattr(obj, key)`` (objects) styles.

    Example::

        name = safe_get(stock, "short_name", "company_name", "name",
                        default=str(stock.get("company_id", "")))
    """
    if obj is None:
        return default
    keys = (key,) + tuple(fallbacks)
    for k in keys:
        # Dict-style
        try:
            if k in obj:
                v = obj[k]
                if v is not None:
                    return v
        except TypeError:
            pass
        # Attribute-style
        v = getattr(obj, k, None)
        if v is not None:
            return v
    return default


def schema_adapter(df, rename_map: dict | None = None,
                   required: tuple = (), defaults: dict | None = None):
    """Normalize a DataFrame to an expected schema.

    * ``rename_map`` — ``{old_name: new_name}`` applied via ``DataFrame.rename``.
    * ``required`` — iterable of column names that MUST exist after rename.
      Missing columns are added filled with ``defaults.get(name)`` if
      ``defaults`` provides a value, otherwise NaN.
    * Returns a *copy* (never mutates caller's df).

    Use at page entry to insulate render code from upstream column drift.
    """
    if df is None:
        return df
    import pandas as _pd  # local import to avoid loading unless needed
    out = df.copy()
    if rename_map:
        out = out.rename(columns=rename_map)
    defaults = defaults or {}
    for col in (required or ()):
        if col not in out.columns:
            out[col] = defaults.get(col, _pd.NA)
    return out


def fallback_display_name(row, primary: str = "short_name",
                          fallbacks=("company_name", "name"),
                          default: str = "") -> str:
    """Return the best display name from a pandas row / dict.

    Always returns a string (never raises). Tries ``primary`` then each
    fallback; if none resolve to a non-empty value, returns ``default``.

    Typical use inside a row-apply loop::

        df["股票"] = df.apply(fallback_display_name, axis=1)
    """
    if row is None:
        return default
    if isinstance(fallbacks, str):
        fallbacks = (fallbacks,)
    for key in (primary,) + tuple(fallbacks or ()):
        try:
            val = row[key]
        except Exception:
            val = getattr(row, key, None)
        if val is None:
            continue
        s = str(val).strip()
        if s and s.lower() not in ("nan", "none", "<na>"):
            return s
    return str(default) if default is not None else ""


# --- v8 §19.4 Centralized naming / copy maps -----------------------------
# Single source of truth so page-level code never hardcodes labels. Pages
# read ``NAV_LABELS[key]`` / ``PAGE_TITLES[key]`` etc. rather than literal
# strings so a rename cascades automatically.

NAV_LABELS = {
    "home":       "情境主控",
    "interpret":  "投資觀察",
    "data":       "資料基礎",
    "icir":       "訊號穩定",
    "text":       "文本情緒",
    "model":      "模型績效",
    "feature":    "因子工程",
    "backtest":   "策略回測",
    "phase6":     "驗證壓測",
    "governance": "模型治理",
    "signal":     "訊號監控",
    "extended":   "延伸分析",
    "manual":     "使用手冊",
}

PAGE_EYEBROWS = {
    "home":       "SITUATION COMMAND",
    "interpret":  "INVESTMENT RESEARCH",
    "data":       "DATA FOUNDATION",
    "icir":       "SIGNAL STABILITY LAB",
    "text":       "TEXT SENTIMENT",
    "model":      "MODEL PERFORMANCE",
    "feature":    "FACTOR ENGINEERING",
    "backtest":   "STRATEGY LAB",
    "phase6":     "VALIDATION LAB",
    "governance": "MODEL GOVERNANCE",
    "signal":     "SIGNAL MONITOR",
    "extended":   "EXTENDED ANALYTICS",
    "manual":     "USER MANUAL",
}

PAGE_TITLES = {
    "home":       "情境主控",
    "interpret":  "投資觀察",
    "data":       "資料基礎",
    "icir":       "訊號穩定",
    "text":       "文本情緒",
    "model":      "模型績效",
    "feature":    "因子工程",
    "backtest":   "策略回測",
    "phase6":     "驗證壓力測試",   # full descriptive for hero
    "governance": "模型治理",
    "signal":     "訊號監控",
    "extended":   "延伸分析",
    "manual":     "使用手冊",
}

PAGE_BRIEFINGS = {
    "home":       "把最新研究快照用三個主要訊號說清楚：方向、信心、風險。",
    "interpret":  "把機器推薦的候選股，換成投資人能讀懂的結論與風險。",
    "data":       "看資料從哪來、覆蓋多廣、Walk-Forward 怎麼切、品質門檻過了幾關。",
    "icir":       "三個角度驗證訊號穩不穩：橫截面、時序、衰減。",
    "text":       "新聞／公告／法說情緒如何影響訊號方向與強度。",
    "model":      "九引擎績效、AUC 分佈、特徵重要性與風格一覽。",
    "feature":    "1,623 → 91 因子漏斗，九支柱結構與篩選三階段。",
    "backtest":   "九引擎策略回測：累積報酬、Sharpe、MDD、成本敏感度。",
    "phase6":     "用三種最嚴格的方式檢查模型是否真的有用：LOPO 支柱拔測、閾值敏感度掃描、2454 實證個案。",
    "governance": "九道品質門、模型卡、DSR、漂移監控，讓每次上線可被審查。",
    "signal":     "訓練 vs 生產的 PSI / KS 漂移、特徵分佈變化與告警。",
    "extended":   "成本敏感度、跨地平線穩定性、支柱貢獻、龍頭個股實測。",
    "manual":     "系統導讀、專業術語、九支柱架構、常見 Q&A。",
}

TOOLTIP_MAP = {
    "AUC":       "ROC 曲線下面積，0.5 為隨機、1.0 為完美。金融訊號常見 0.52–0.60。",
    "ICIR":      "資訊係數 / 標準差 — 訊號穩定度指標，越高表示預測力越一致。",
    "IC":        "Information Coefficient — 預測值與實際報酬的 rank 相關係數。",
    "DSR":       "Deflated Sharpe Ratio — 多重檢定修正後的 Sharpe，過關表示績效非偶然。",
    "Sharpe":    "年化超額報酬 / 年化波動。越高代表單位風險換到的報酬越多。",
    "MDD":       "Max Drawdown — 峰值回撤，衡量策略最壞情況下能虧多少。",
    "PSI":       "Population Stability Index — 分佈漂移量測，>0.25 代表顯著漂移。",
    "LOPO":      "Leave-One-Pillar-Out — 輪流拔掉一個支柱重訓，量化該支柱邊際貢獻。",
    "Hit Rate":  "命中率 — 模型出手時預測方向正確的比例。",
    "Call Rate": "出手率 — 模型在全部樣本中產生建議的比例。",
    "Gates":     "品質門 — 上線前的強制檢查（資料、訓練、穩定、治理）。",
    "Walk-Forward":"Purged Walk-Forward CV — 考慮時間序列洩漏的分段驗證法。",
    "Pillar":    "支柱 — 九類因子面向：趨勢 / 基本面 / 估值 / 事件 / 風險 / 籌碼 / 產業 / 文本 / 情緒。",
}

ERROR_COPY_MAP = {
    "report_missing":   ("報告檔缺件", "找不到最新的研究報告 JSON，請先執行對應的 Phase 指令。"),
    "schema_drift":     ("欄位結構不符", "上游資料的欄位名稱與本頁預期不同，請檢查 schema 對應表。"),
    "feature_store_offline":("因子倉離線", "雲端部署未同步 feature_store，以降級模式顯示總覽統計。"),
    "governance_offline":("治理報告不可用", "尚未產生 governance JSON；請重新執行模型治理流程。"),
    "phase6_missing":   ("壓測報告缺件", "LOPO / Threshold / Case 三份壓測 JSON 缺一不可，請執行 run_phase6。"),
}

EMPTY_COPY_MAP = {
    "no_recommendations":  ("目前無建議", "此橫線 / 情境組合沒有符合門檻的候選股，改試其他情境。"),
    "no_news":             ("尚無新聞", "此期間內無可用公告 / 法說資料，情緒訊號暫不顯示。"),
    "no_industry_peer":    ("找不到同業", "此類股樣本不足，無法進行產業相對比較。"),
    "no_gate_history":     ("尚無歷史品質門", "系統首次執行或 gate 歷史尚未累積，請於下次 Phase 2 後回訪。"),
    "no_drift":            ("近期無漂移", "PSI/KS 均低於告警門檻，訊號穩定。"),
}


# --- v8 §18.4 · Error / empty from copy-map (one-line site of use) --------
def render_error_from_copy_map(key: str, exception: Exception | None = None,
                               schema_hint: str = "",
                               fallback_note: str = "") -> None:
    """Render a dark terminal error panel using a key from ``ERROR_COPY_MAP``.

    Lets page code shrink:

        except Exception as e:
            render_error_from_copy_map("report_missing", exception=e)
            st.stop()

    If ``exception`` is provided and no explicit ``schema_hint`` is given, the
    truncated exception message is surfaced as the schema hint so debugging is
    possible without blocking the user experience.
    """
    entry = ERROR_COPY_MAP.get(key)
    if entry is None:
        title = "未預期錯誤"
        reason = "此錯誤尚未在 ERROR_COPY_MAP 中定義，請補上明確文案後重試。"
    else:
        title, reason = entry
    if not schema_hint and exception is not None:
        msg = str(exception)
        schema_hint = msg[:220] + ("…" if len(msg) > 220 else "")
    render_terminal_error_state(
        title=title,
        reason=reason,
        schema_hint=schema_hint,
        fallback_note=fallback_note,
    )


def render_empty_from_copy_map(key: str, actions: list | None = None,
                               icon: str = "◇") -> None:
    """Render a dark terminal empty-state panel from ``EMPTY_COPY_MAP``.

    Pairs with ``render_terminal_empty_state``. Lets pages call::

        if df.empty:
            render_empty_from_copy_map(
                "no_recommendations",
                actions=["切換至 D+5 橫線", "放寬情境門檻"],
            )
            st.stop()
    """
    entry = EMPTY_COPY_MAP.get(key)
    if entry is None:
        title = "查無資料"
        reason = ""
    else:
        title, reason = entry
    render_terminal_empty_state(
        title=title,
        reason=reason,
        available_actions=actions,
        icon=icon,
    )


# --- v8 §11 · SVG icon registry (lucide-inspired, zero-emoji mandate) -----
# Each icon is a standalone inline SVG path set that inherits currentColor.
# Callers use ``render_page_icon("radar", size=20, color="#67e8f9")`` or
# just ``GLINT_ICON_SVG["radar"]`` to paste into their own markup.
# Names mirror the v8 §11 icon registry roster (radar / eye / building-2
# / waveform / text-search / chart-column / layers-3 / line-chart /
# flask-conical / shield-check / activity / combine / search / pulse-dot).
GLINT_ICON_SVG = {
    # Situation command · 總覽 hub
    "radar": (
        '<circle cx="12" cy="12" r="10"/>'
        '<circle cx="12" cy="12" r="6"/>'
        '<circle cx="12" cy="12" r="2"/>'
        '<path d="M12 12L22 5"/>'
    ),
    # Investment research · 個股解讀
    "eye": (
        '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/>'
        '<circle cx="12" cy="12" r="3"/>'
    ),
    # Data foundation · 資料基礎
    "building-2": (
        '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/>'
        '<path d="M6 12H4a2 2 0 0 0-2 2v8h4"/>'
        '<path d="M18 9h2a2 2 0 0 1 2 2v11h-4"/>'
        '<path d="M10 6h4"/>'
        '<path d="M10 10h4"/>'
        '<path d="M10 14h4"/>'
        '<path d="M10 18h4"/>'
    ),
    # Signal stability · 訊號穩定
    "waveform": (
        '<path d="M2 12h2l3-9 4 18 3-12 3 6h5"/>'
    ),
    # Text sentiment · 文本情緒
    "text-search": (
        '<path d="M14 18h1"/>'
        '<path d="M10 4h9"/>'
        '<path d="M5 8h14"/>'
        '<circle cx="15" cy="14" r="4"/>'
        '<path d="m21 20-2.1-2.1"/>'
    ),
    # Model performance · 模型績效
    "chart-column": (
        '<path d="M3 3v18h18"/>'
        '<path d="M7 13v5"/>'
        '<path d="M12 9v9"/>'
        '<path d="M17 5v13"/>'
    ),
    # Factor engineering · 因子工程
    "layers-3": (
        '<path d="M12 2 2 7l10 5 10-5-10-5Z"/>'
        '<path d="M2 17l10 5 10-5"/>'
        '<path d="M2 12l10 5 10-5"/>'
    ),
    # Strategy lab · 策略回測
    "line-chart": (
        '<path d="M3 3v18h18"/>'
        '<path d="m19 9-5 5-4-4-3 3"/>'
    ),
    # Validation lab · 驗證壓測 (Phase 6)
    "flask-conical": (
        '<path d="M10 2v7.527a2 2 0 0 1-.211.896L4.72 20.55a1 1 0 0 0 .9 1.45h12.76a1 1 0 0 0 .9-1.45l-5.069-10.127A2 2 0 0 1 14 9.527V2"/>'
        '<path d="M8.5 2h7"/>'
        '<path d="M7 16h10"/>'
    ),
    # Model governance · 模型治理
    "shield-check": (
        '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>'
        '<path d="m9 12 2 2 4-4"/>'
    ),
    # Signal monitor · 訊號監控
    "activity": (
        '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>'
    ),
    # Extended analytics · 延伸分析
    "combine": (
        '<path d="M10 18H5a3 3 0 0 1-3-3v-1"/>'
        '<path d="M14 2a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>'
        '<path d="M20 2a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>'
        '<path d="M20 14a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2z"/>'
        '<path d="M7 9v6"/>'
    ),
    # User manual · 使用手冊
    "book-open": (
        '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
        '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'
    ),
    # Generic search (utility bar etc)
    "search": (
        '<circle cx="11" cy="11" r="7"/>'
        '<path d="m21 21-4.3-4.3"/>'
    ),
    # Pulse dot (small live indicator)
    "pulse-dot": (
        '<circle cx="12" cy="12" r="3"/>'
    ),
}

# Nav key → icon name mapping (v8 §11 roster).
PAGE_ICON_NAMES = {
    "home":        "radar",
    "interpret":   "eye",
    "data":        "building-2",
    "icir":        "waveform",
    "text":        "text-search",
    "model":       "chart-column",
    "feature":     "layers-3",
    "backtest":    "line-chart",
    "phase6":      "flask-conical",
    "governance":  "shield-check",
    "signal":      "activity",
    "extended":    "combine",
    "manual":      "book-open",
}


def render_page_icon(name: str, size: int = 20, color: str = "currentColor",
                     stroke_width: float = 2.0, as_html: bool = True,
                     aria_hidden: bool = True):
    """Return (or render) a lucide-style SVG icon string by name.

    Args:
        name: key in ``GLINT_ICON_SVG`` (e.g. ``"radar"``, ``"shield-check"``).
        size: px width/height. Default 20 for inline header glyphs.
        color: CSS colour. ``"currentColor"`` lets CSS control tint.
        stroke_width: stroke width in SVG units.
        as_html: if ``True`` returns the raw SVG markup string; if ``False``
            emits via ``st.markdown`` and returns None.
        aria_hidden: adds ``aria-hidden="true"`` so screen readers skip
            purely decorative glyphs.

    The registry is immutable at runtime — unknown names fall back to a
    small bullet so the UI never crashes.
    """
    path_data = GLINT_ICON_SVG.get(name, '<circle cx="12" cy="12" r="5"/>')
    aria = ' aria-hidden="true"' if aria_hidden else ''
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{int(size)}" height="{int(size)}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="{stroke_width}" stroke-linecap="round" '
        f'stroke-linejoin="round"{aria}>'
        f'{path_data}'
        f'</svg>'
    )
    if as_html:
        return svg
    import streamlit as _st
    _st.markdown(svg, unsafe_allow_html=True)
    return None


def render_nav_icon(page_key: str, size: int = 18, color: str = "currentColor",
                    stroke_width: float = 2.0, as_html: bool = True):
    """Convenience wrapper: resolve ``page_key`` → icon name → SVG.

    Use this inside top-nav / sidebar / hero icon slots so page-level code
    never needs to know the icon name directly.
    """
    icon_name = PAGE_ICON_NAMES.get(page_key, "pulse-dot")
    return render_page_icon(
        icon_name,
        size=size,
        color=color,
        stroke_width=stroke_width,
        as_html=as_html,
    )


# --- Unified colorscales for heatmaps -------------------------------------
GLINT_DIVERGING = [
    [0.00, "#9f1239"],   # deep rose
    [0.18, "#f43f5e"],
    [0.35, "#fda4af"],
    [0.50, "#f8fafc"],   # neutral center
    [0.65, "#7dd3fc"],
    [0.82, "#06b6d4"],
    [1.00, "#065f46"],   # deep emerald
]
GLINT_SEQUENTIAL_COOL = [
    [0.00, "#f0f9ff"],
    [0.25, "#bae6fd"],
    [0.50, "#06b6d4"],
    [0.75, "#2563eb"],
    [1.00, "#1e3a8a"],
]
GLINT_SEQUENTIAL_WARM = [
    [0.00, "#fffbeb"],
    [0.25, "#ddd6fe"],
    [0.50, "#a78bfa"],
    [0.75, "#6d28d9"],
    [1.00, "#7c2d12"],
]


def glint_heatmap_colorscale(kind: str = "diverging") -> list:
    """Return a glint-themed colorscale.

    ``kind`` ∈ {"diverging", "cool", "warm"}. Diverging goes rose→neutral→emerald
    so green = good (positive return / strong signal) by convention.
    """
    return {"diverging": GLINT_DIVERGING,
            "cool": GLINT_SEQUENTIAL_COOL,
            "warm": GLINT_SEQUENTIAL_WARM}.get(kind, GLINT_DIVERGING)


def glint_colorbar(title: str = "", fmt: str = "") -> dict:
    """Return a compact, glint-styled Plotly colorbar config (v11.2 dark-safe)."""
    cb = dict(
        title=dict(text=f"<b>{title}</b>", font=dict(family=_GL_FONT_MONO, size=10, color="#b4ccdf"), side="right"),
        thickness=10, len=0.75, outlinewidth=0,
        tickfont=dict(family=_GL_FONT_MONO, size=10, color="#b4ccdf"),
        tickformat=fmt, ticks="outside", ticklen=3, tickcolor="rgba(103,232,249,0.28)",
        bgcolor="rgba(10,20,32,0.55)",
    )
    return cb


GLINT_COLORS = {
    "blue":    "#2563eb",
    "violet":  "#7c3aed",
    "cyan":    "#06b6d4",
    "emerald": "#10b981",
    "amber":   "#a78bfa",
    "rose":    "#f43f5e",
    "indigo":  "#4f46e5",
    "slate":   "#64748b",
}


def glint_styler_cmap(kind: str = "diverging"):
    """Return a matplotlib LinearSegmentedColormap aligned with glint tokens.

    Use with ``df.style.background_gradient(cmap=glint_styler_cmap("diverging"))``
    so pandas styler output stays in the same palette as Plotly heatmaps.

    Kinds: "diverging" (rose→neutral→emerald), "cool" (light blue→deep blue),
    "warm" (cream→amber→deep rose). Falls back to diverging.
    """
    try:
        from matplotlib.colors import LinearSegmentedColormap
    except Exception:
        return kind
    palettes = {
        "diverging": ["#9f1239", "#f43f5e", "#fda4af", "#f8fafc",
                      "#7dd3fc", "#06b6d4", "#065f46"],
        "cool":      ["#f0f9ff", "#bae6fd", "#06b6d4", "#2563eb", "#1e3a8a"],
        "warm":      ["#fffbeb", "#ddd6fe", "#a78bfa", "#6d28d9", "#7c2d12"],
    }
    colors = palettes.get(kind, palettes["diverging"])
    return LinearSegmentedColormap.from_list(f"glint_{kind}", colors)


def render_degraded_banner(title: str, reason: str, available: str = "",
                           unavailable: str = "", tone: str = "warn") -> None:
    """Render a graceful degraded-mode banner instead of a bare error string.

    ``tone`` ∈ {"warn" (amber), "info" (blue), "error" (rose)}. Use this when
    a page can still render useful summary content despite a missing data
    artifact (e.g. feature store not available on Streamlit Cloud).
    """
    import streamlit as _st
    tone_map = {
        "warn":  ("⚠️", "amber",   "#a78bfa"),
        "info":  ("ℹ️",  "blue",    "#2563eb"),
        "error": ("⛔", "rose",    "#f43f5e"),
    }
    icon, key, color = tone_map.get(tone, tone_map["warn"])
    parts = [
        f'<div class="gl-degraded gl-degraded-{key}">',
        f'  <div class="gl-degraded-head">{icon} <b>{title}</b></div>',
        f'  <div class="gl-degraded-body">{reason}</div>',
    ]
    if available:
        parts.append(f'  <div class="gl-degraded-kv"><span>可查看</span>{available}</div>')
    if unavailable:
        parts.append(f'  <div class="gl-degraded-kv"><span>暫不可用</span>{unavailable}</div>')
    parts.append("</div>")
    _st.markdown("\n".join(parts), unsafe_allow_html=True)


def render_chart_note(text: str, tone: str = "insight") -> None:
    """Render a compact "so what" note below a chart (1-2 short lines).

    ``tone`` ∈ {"insight" (blue), "caveat" (amber), "risk" (rose)}.
    Keeps post-chart context consistent across pages.
    """
    import streamlit as _st
    tone_map = {
        "insight": ("#67E8F9", "rgba(103,232,249,0.08)", "#B4CCDF"),
        "caveat":  ("#A78BFA", "rgba(167,139,250,0.10)",  "#DDD6FE"),
        "risk":    ("#F43F5E", "rgba(244,63,94,0.10)",   "#FECDD3"),
    }
    color, bg, text_color = tone_map.get(tone, tone_map["insight"])
    html = (
        f'<div class="gl-chart-note" style="border-left:3px solid {color};'
        f'background:{bg};padding:8px 14px;margin:4px 0 18px;'
        f'border-radius:0 8px 8px 0;font-size:0.85rem;color:{text_color};'
        f'line-height:1.55;">{text}</div>'
    )
    _st.markdown(html, unsafe_allow_html=True)


# --- v7 §13 Terminal-style banners / cards -------------------------------
# 4-tone vocabulary (info/ok/warn/danger) aligned with Dark Terminal tokens.
# Use these for signal/status/decision panels so semantics are consistent
# across pages (no ad-hoc ``st.info`` / ``st.warning``).
_GL_TERMINAL_TONES = {
    "info":   {"accent": "#67E8F9", "bg": "rgba(103,232,249,0.07)",
               "border": "rgba(103,232,249,0.28)", "text": "#E8F7FC",
               "label": "INFO",   "glyph": "●"},
    "ok":     {"accent": "#10B981", "bg": "rgba(16,185,129,0.08)",
               "border": "rgba(16,185,129,0.30)", "text": "#D1FAE5",
               "label": "OK",     "glyph": "✓"},
    "warn":   {"accent": "#A78BFA", "bg": "rgba(167,139,250,0.08)",
               "border": "rgba(167,139,250,0.32)", "text": "#DDD6FE",
               "label": "WARN",   "glyph": "▲"},
    "danger": {"accent": "#F43F5E", "bg": "rgba(244,63,94,0.10)",
               "border": "rgba(244,63,94,0.34)", "text": "#FECDD3",
               "label": "DANGER", "glyph": "!"},
}


def render_terminal_banner(title: str, body: str = "", tone: str = "info",
                           command: str = "") -> None:
    """Render a dark-terminal status banner (v7 §13.1).

    Use for page-level status announcements (degraded mode, freshness,
    stress-test result summaries). Supports 4 tones: info / ok / warn /
    danger. Optional ``command`` renders a small monospace prompt line
    beneath the title (e.g. ``"$ lopo --pillar=trend --stress"``).
    """
    import streamlit as _st
    t = _GL_TERMINAL_TONES.get(tone, _GL_TERMINAL_TONES["info"])
    safe_title = safe_html(title)
    safe_body = safe_html(body) if body else ""
    safe_cmd = safe_html(command) if command else ""
    cmd_html = (
        f'<div class="gl-term-cmd">$ {safe_cmd}</div>' if safe_cmd else ""
    )
    body_html = (
        f'<div class="gl-term-body">{safe_body}</div>' if safe_body else ""
    )
    html = (
        f'<div class="gl-term-banner gl-term-{tone}" '
        f'style="--tb-accent:{t["accent"]};--tb-bg:{t["bg"]};'
        f'--tb-border:{t["border"]};--tb-text:{t["text"]};">'
        f'<div class="gl-term-head">'
        f'<span class="gl-term-glyph">{t["glyph"]}</span>'
        f'<span class="gl-term-label">{t["label"]}</span>'
        f'<span class="gl-term-title">{safe_title}</span>'
        f'</div>'
        f'{cmd_html}{body_html}'
        f'</div>'
    )
    _st.markdown(html, unsafe_allow_html=True)


def render_signal_card(label: str, value: str, delta: str = "",
                       tone: str = "info", hint: str = "") -> None:
    """Render a compact terminal-style signal card (v7 §13.2).

    One card = one signal reading. ``delta`` is a small trend annotation
    (e.g. "+0.02" or "↑"). ``hint`` is a 1-line caption underneath.
    """
    import streamlit as _st
    t = _GL_TERMINAL_TONES.get(tone, _GL_TERMINAL_TONES["info"])
    safe_label = safe_html(label)
    safe_value = safe_html(value)
    safe_delta = safe_html(delta) if delta else ""
    safe_hint = safe_html(hint) if hint else ""
    delta_html = (
        f'<span class="gl-sig-delta">{safe_delta}</span>' if safe_delta else ""
    )
    hint_html = (
        f'<div class="gl-sig-hint">{safe_hint}</div>' if safe_hint else ""
    )
    html = (
        f'<div class="gl-signal-card gl-signal-{tone}" '
        f'style="--sc-accent:{t["accent"]};--sc-bg:{t["bg"]};'
        f'--sc-border:{t["border"]};--sc-text:{t["text"]};">'
        f'<div class="gl-sig-head">'
        f'<span class="gl-sig-glyph">{t["glyph"]}</span>'
        f'<span class="gl-sig-label">{safe_label}</span>'
        f'</div>'
        f'<div class="gl-sig-value">{safe_value}{delta_html}</div>'
        f'{hint_html}'
        f'</div>'
    )
    _st.markdown(html, unsafe_allow_html=True)


def render_status_card(label: str, state: str, detail: str = "",
                       tone: str = "ok") -> None:
    """Render a status / health card (v7 §13.3).

    Used for quality-gate readouts, guardrail states, data-freshness
    banners. ``state`` is a terse indicator (e.g. "PASS" / "DEGRADED" /
    "FAIL"). ``detail`` adds a sentence of context.
    """
    import streamlit as _st
    t = _GL_TERMINAL_TONES.get(tone, _GL_TERMINAL_TONES["ok"])
    safe_label = safe_html(label)
    safe_state = safe_html(state)
    safe_detail = safe_html(detail) if detail else ""
    detail_html = (
        f'<div class="gl-stat-detail">{safe_detail}</div>' if safe_detail else ""
    )
    html = (
        f'<div class="gl-status-card gl-status-{tone}" '
        f'style="--st-accent:{t["accent"]};--st-bg:{t["bg"]};'
        f'--st-border:{t["border"]};--st-text:{t["text"]};">'
        f'<div class="gl-stat-head">'
        f'<span class="gl-stat-glyph">{t["glyph"]}</span>'
        f'<span class="gl-stat-label">{safe_label}</span>'
        f'<span class="gl-stat-state">{safe_state}</span>'
        f'</div>'
        f'{detail_html}'
        f'</div>'
    )
    _st.markdown(html, unsafe_allow_html=True)


def render_decision_card(verdict: str, reason: str = "", tone: str = "info",
                         confidence: str = "", action: str = "") -> None:
    """Render a decision / recommendation card (v7 §13.4).

    Used at the end of an analysis section to surface a "so what" call.
    ``verdict`` is the headline (e.g. "建議加碼 成長股"), ``reason`` the
    supporting one-liner, ``confidence`` a probability/score string, and
    ``action`` the suggested next step.
    """
    import streamlit as _st
    t = _GL_TERMINAL_TONES.get(tone, _GL_TERMINAL_TONES["info"])
    safe_verdict = safe_html(verdict)
    safe_reason = safe_html(reason) if reason else ""
    safe_conf = safe_html(confidence) if confidence else ""
    safe_action = safe_html(action) if action else ""
    conf_html = (
        f'<div class="gl-dec-conf">信心度 · {safe_conf}</div>' if safe_conf else ""
    )
    reason_html = (
        f'<div class="gl-dec-reason">{safe_reason}</div>' if safe_reason else ""
    )
    action_html = (
        f'<div class="gl-dec-action">→ {safe_action}</div>' if safe_action else ""
    )
    html = (
        f'<div class="gl-decision-card gl-decision-{tone}" '
        f'style="--dc-accent:{t["accent"]};--dc-bg:{t["bg"]};'
        f'--dc-border:{t["border"]};--dc-text:{t["text"]};">'
        f'<div class="gl-dec-head">'
        f'<span class="gl-dec-glyph">{t["glyph"]}</span>'
        f'<span class="gl-dec-label">DECISION</span>'
        f'{conf_html}'
        f'</div>'
        f'<div class="gl-dec-verdict">{safe_verdict}</div>'
        f'{reason_html}{action_html}'
        f'</div>'
    )
    _st.markdown(html, unsafe_allow_html=True)


# --- v11.5.5 Glint SVG icon library ------------------------------------
# Lucide-inspired line icons (1.5px stroke, currentColor) used to replace the
# kawaii emoji palette (🌱📈📊🔬📅📌🌟💡🎯📖🏆) dashboard-wide. These render
# crisply on dark Glint backgrounds, inherit text color via `currentColor`, and
# keep the futuristic/data-terminal feel consistent with render_terminal_hero.
GLINT_ICON_SVG = {
    # Navigation / actions
    "refresh-cw": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 12a9 9 0 0 1 15.5-6.3L21 8"/><path d="M21 3v5h-5"/>'
        '<path d="M21 12a9 9 0 0 1-15.5 6.3L3 16"/><path d="M3 21v-5h5"/></svg>'
    ),
    "book-open": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M2 4h6a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2z"/>'
        '<path d="M22 4h-6a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3h7z"/></svg>'
    ),
    # Data / analytics
    "line-chart": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 3v18h18"/><path d="M7 14l4-4 4 4 5-6"/>'
        '<circle cx="7" cy="14" r="1.2" fill="currentColor"/>'
        '<circle cx="11" cy="10" r="1.2" fill="currentColor"/>'
        '<circle cx="15" cy="14" r="1.2" fill="currentColor"/>'
        '<circle cx="20" cy="8" r="1.2" fill="currentColor"/></svg>'
    ),
    "bar-chart": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 21h18"/><rect x="5" y="11" width="3" height="9" rx="0.5"/>'
        '<rect x="10.5" y="6" width="3" height="14" rx="0.5"/>'
        '<rect x="16" y="14" width="3" height="6" rx="0.5"/></svg>'
    ),
    "trending-up": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/></svg>'
    ),
    "scatter": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 3v18h18"/>'
        '<circle cx="7" cy="15" r="1.5" fill="currentColor"/>'
        '<circle cx="11" cy="11" r="1.5" fill="currentColor"/>'
        '<circle cx="14" cy="16" r="1.5" fill="currentColor"/>'
        '<circle cx="17" cy="8" r="1.5" fill="currentColor"/>'
        '<circle cx="20" cy="13" r="1.5" fill="currentColor"/></svg>'
    ),
    # Research / science
    "microscope": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M6 18h8"/><path d="M3 22h18"/>'
        '<path d="M14 22a7 7 0 0 0 0-14"/>'
        '<path d="M9 14h2"/><path d="M8 10l3-3 4 4-3 3z"/>'
        '<path d="M13 7l3-3"/></svg>'
    ),
    "target": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/>'
        '<circle cx="12" cy="12" r="2" fill="currentColor"/></svg>'
    ),
    "radar": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10" opacity="0.35"/>'
        '<circle cx="12" cy="12" r="6" opacity="0.55"/>'
        '<circle cx="12" cy="12" r="2" fill="currentColor"/>'
        '<path d="M12 12L20 6"/></svg>'
    ),
    # Insight / meta
    "lightbulb": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M9 18h6"/><path d="M10 22h4"/>'
        '<path d="M12 2a7 7 0 0 0-4 12.7c.7.6 1 1.5 1 2.3v1h6v-1c0-.8.3-1.7 1-2.3A7 7 0 0 0 12 2z"/></svg>'
    ),
    "pin": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 17v5"/><path d="M9 10.76V6a3 3 0 0 1 6 0v4.76"/>'
        '<path d="M7 13a5 5 0 0 1 5-3 5 5 0 0 1 5 3l-2 4H9z"/></svg>'
    ),
    "sparkle": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 3l2.2 5.8L20 11l-5.8 2.2L12 19l-2.2-5.8L4 11l5.8-2.2z"/>'
        '<path d="M19 3v3"/><path d="M17.5 4.5h3"/></svg>'
    ),
    "award": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="9" r="6"/>'
        '<path d="M8.5 13.5L7 22l5-3 5 3-1.5-8.5"/></svg>'
    ),
    # Time / schedule
    "calendar": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="5" width="18" height="16" rx="2"/>'
        '<path d="M3 10h18"/><path d="M8 3v4"/><path d="M16 3v4"/>'
        '<circle cx="8" cy="15" r="0.8" fill="currentColor"/>'
        '<circle cx="12" cy="15" r="0.8" fill="currentColor"/>'
        '<circle cx="16" cy="15" r="0.8" fill="currentColor"/></svg>'
    ),
    "clock": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>'
    ),
    # Taxonomy
    "layers": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 3L3 8l9 5 9-5z"/><path d="M3 13l9 5 9-5"/>'
        '<path d="M3 18l9 5 9-5"/></svg>'
    ),
    "cpu": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="4" y="4" width="16" height="16" rx="2"/>'
        '<rect x="9" y="9" width="6" height="6" rx="1"/>'
        '<path d="M9 2v2"/><path d="M15 2v2"/>'
        '<path d="M9 20v2"/><path d="M15 20v2"/>'
        '<path d="M20 9h2"/><path d="M20 15h2"/>'
        '<path d="M2 9h2"/><path d="M2 15h2"/></svg>'
    ),
    "activity": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 12h4l3-8 4 16 3-8h4"/></svg>'
    ),
    "grid": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="3" width="7" height="7" rx="1"/>'
        '<rect x="14" y="3" width="7" height="7" rx="1"/>'
        '<rect x="3" y="14" width="7" height="7" rx="1"/>'
        '<rect x="14" y="14" width="7" height="7" rx="1"/></svg>'
    ),
}


def glint_icon(name: str, size: int = 18, color: str | None = None) -> str:
    """Return an inline SVG icon string sized and tinted for Glint UI.

    Usage (inside ``st.markdown(..., unsafe_allow_html=True)``)::

        f'<span>{glint_icon("line-chart", 20, "var(--gl-cyan)")}</span>'

    The returned SVG inherits ``currentColor`` when ``color`` is None, so
    wrap it in an element whose ``color`` you already control.
    """
    svg = GLINT_ICON_SVG.get(name)
    if not svg:
        return ""
    style = (
        f'width:{size}px;height:{size}px;display:inline-block;'
        f'vertical-align:-{max(2, size // 8)}px;flex-shrink:0;'
    )
    if color:
        style += f'color:{color};'
    # Inject style onto the root <svg> tag
    return svg.replace("<svg ", f'<svg style="{style}" ', 1)


def glint_heading(icon: str, title: str, sub: str = "", tone: str = "cyan",
                  level: int = 3) -> None:
    """Render a tech-styled section heading: Glint SVG icon + title (+ mono sub).

    Drop-in replacement for ``st.markdown("### 🎯 title | Sub")``. Uses
    inline SVG icons from ``GLINT_ICON_SVG`` so nothing reads as kawaii.

    Args:
        icon: key into ``GLINT_ICON_SVG`` (e.g. "target", "bar-chart").
        title: primary (Chinese) heading text.
        sub: optional mono English gloss rendered after a ``|`` separator.
        tone: accent color key — cyan / emerald / blue / violet / amber / rose.
        level: HTML heading level (2/3/4). Default 3.
    """
    tone_color_map = {
        "cyan":    "var(--gl-cyan)",
        "emerald": "var(--gl-emerald)",
        "blue":    "var(--gl-blue)",
        "violet":  "var(--gl-violet)",
        "amber":   "var(--gl-amber)",
        "rose":    "var(--gl-rose)",
    }
    accent = tone_color_map.get(tone, tone_color_map["cyan"])
    icon_html = glint_icon(icon, 22)
    safe_title = safe_html(title)
    sub_html = ""
    if sub:
        safe_sub = safe_html(sub)
        sub_html = (
            f'<span style="color:var(--gl-text-3);'
            f'font-family:\'JetBrains Mono\',monospace;font-size:0.85rem;'
            f'font-weight:600;margin-left:10px;letter-spacing:0.02em;">'
            f'| {safe_sub}</span>'
        )
    tag = f"h{max(2, min(4, level))}"
    st.markdown(
        f'<{tag} style="display:flex;align-items:center;gap:10px;'
        f'margin:24px 0 6px;color:var(--gl-text);">'
        f'<span style="color:{accent};display:inline-flex;align-items:center;">'
        f'{icon_html}</span>'
        f'<span>{safe_title}{sub_html}</span>'
        f'</{tag}>',
        unsafe_allow_html=True,
    )


def glint_icon_box(name: str, tone: str = "cyan", size: int = 56) -> str:
    """Return a 56-px rounded-square icon frame (for hero/action cards).

    Replaces the legacy ``font-size:2.4rem`` giant-emoji pattern with a
    glowing glyph tile that matches the dark terminal aesthetic.
    """
    tone_map = {
        "cyan":    ("#67E8F9", "rgba(103,232,249,0.18)", "rgba(103,232,249,0.35)"),
        "emerald": ("#34D399", "rgba(52,211,153,0.18)",  "rgba(52,211,153,0.35)"),
        "violet":  ("#A78BFA", "rgba(167,139,250,0.18)", "rgba(167,139,250,0.35)"),
        "blue":    ("#60A5FA", "rgba(96,165,250,0.18)",  "rgba(96,165,250,0.35)"),
        "amber":   ("#C4B5FD", "rgba(196,181,253,0.18)",  "rgba(196,181,253,0.35)"),
        "rose":    ("#FB7185", "rgba(251,113,133,0.18)", "rgba(251,113,133,0.35)"),
    }
    accent, bg, border = tone_map.get(tone, tone_map["cyan"])
    icon_html = glint_icon(name, size=int(size * 0.48), color=accent)
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:14px;'
        f'display:inline-flex;align-items:center;justify-content:center;'
        f'background:linear-gradient(135deg,{bg} 0%,rgba(8,15,28,0.55) 100%);'
        f'border:1px solid {border};'
        f'box-shadow:inset 0 1px 0 rgba(255,255,255,0.06),'
        f'0 6px 18px rgba(2,6,23,0.38),0 0 24px {bg};'
        f'margin-bottom:12px;">'
        f'{icon_html}'
        f'</div>'
    )


# --- v8 §12 / §19.5 Terminal hero ---------------------------------------
def render_terminal_hero(eyebrow: str, title: str, briefing: str = "",
                         chips: list | None = None, verdict: str = "",
                         tone: str = "cyan") -> None:
    """Render the dark terminal page hero (v8 §12).

    Structure: eyebrow → title → briefing → chips → optional verdict strip.
    Replaces the legacy light-mode ``render_page_heading`` on pages that
    have been upgraded to full dark. Keeps the signal-first discipline
    (3-second comprehension) mandated by §12.1.
    """
    import streamlit as _st
    tone_map = {
        "cyan":    ("#67E8F9", "rgba(103,232,249,0.32)"),
        "blue":    ("#60A5FA", "rgba(96,165,250,0.32)"),
        "violet":  ("#A78BFA", "rgba(167,139,250,0.32)"),
        "emerald": ("#34D399", "rgba(52,211,153,0.32)"),
        "amber":   ("#C4B5FD", "rgba(196,181,253,0.32)"),
        "rose":    ("#FB7185", "rgba(251,113,133,0.32)"),
    }
    accent, border = tone_map.get(tone, tone_map["cyan"])
    safe_eyebrow = safe_html(eyebrow)
    safe_title = safe_html(title)
    safe_briefing = safe_html(briefing) if briefing else ""

    chip_html = ""
    if chips:
        parts = []
        for c in chips:
            if isinstance(c, tuple):
                if len(c) == 2:
                    label, c_tone = c
                    val = ""
                elif len(c) >= 3:
                    label, val, c_tone = c[0], c[1], c[2]
                else:
                    label, val, c_tone = c[0], "", "info"
            elif isinstance(c, dict):
                label = c.get("label", "")
                val = c.get("value", "")
                c_tone = c.get("tone", "info")
            else:
                label, val, c_tone = str(c), "", "info"
            c_t = _GL_TERMINAL_TONES.get(c_tone, _GL_TERMINAL_TONES["info"])
            chip_inner = safe_html(label)
            if val:
                chip_inner += f' <span class="gl-thero-chipval">{safe_html(val)}</span>'
            parts.append(
                f'<span class="gl-thero-chip" '
                f'style="--ch-accent:{c_t["accent"]};--ch-border:{c_t["border"]};'
                f'--ch-bg:{c_t["bg"]};">{chip_inner}</span>'
            )
        chip_html = f'<div class="gl-thero-chips">{"".join(parts)}</div>'

    verdict_html = ""
    if verdict:
        verdict_html = (
            f'<div class="gl-thero-verdict">'
            f'<span class="gl-thero-verdict-tag">VERDICT</span>'
            f'<span class="gl-thero-verdict-text">{safe_html(verdict)}</span>'
            f'</div>'
        )

    briefing_html = (
        f'<div class="gl-thero-briefing">{safe_briefing}</div>' if safe_briefing else ""
    )

    html = (
        f'<div class="gl-thero gl-thero-{tone}" '
        f'style="--th-accent:{accent};--th-border:{border};">'
        f'<div class="gl-thero-topline"></div>'
        f'<div class="gl-thero-eyebrow">{safe_eyebrow}</div>'
        f'<div class="gl-thero-title">{safe_title}</div>'
        f'{briefing_html}'
        f'{chip_html}'
        f'{verdict_html}'
        f'</div>'
    )
    _st.markdown(html, unsafe_allow_html=True)


def render_terminal_chip(label: str, value: str = "", tone: str = "info",
                         as_html: bool = False):
    """Render a single terminal chip. Returns str when ``as_html=True``.

    Chips are the atomic status / metric marker of the terminal UI —
    useful in breadcrumb rows, inline annotations, or anywhere a tiny
    status token is needed.
    """
    import streamlit as _st
    t = _GL_TERMINAL_TONES.get(tone, _GL_TERMINAL_TONES["info"])
    inner = safe_html(label)
    if value:
        inner += f' <span class="gl-tchip-val">{safe_html(value)}</span>'
    html = (
        f'<span class="gl-tchip gl-tchip-{tone}" '
        f'style="--tc-accent:{t["accent"]};--tc-border:{t["border"]};'
        f'--tc-bg:{t["bg"]};">{inner}</span>'
    )
    if as_html:
        return html
    _st.markdown(html, unsafe_allow_html=True)
    return None


def render_terminal_table(df, how_to_read: str = "",
                          column_config: dict | None = None,
                          height: int | None = None,
                          caption_tone: str = "info") -> None:
    """Render a DataFrame wrapped in terminal-style caption + container.

    * ``how_to_read`` — 1–2 line guide shown *above* the table so readers
      know which columns to scan first.
    * ``column_config`` — passes through to ``st.dataframe(column_config=)``
    * ``height`` — px override for long tables.

    The dataframe itself is styled dark via global CSS (``.gl-tterm-table``).
    """
    import streamlit as _st
    if df is None:
        return
    if how_to_read:
        t = _GL_TERMINAL_TONES.get(caption_tone, _GL_TERMINAL_TONES["info"])
        _st.markdown(
            f'<div class="gl-tterm-caption" '
            f'style="--tt-accent:{t["accent"]};--tt-border:{t["border"]};'
            f'--tt-bg:{t["bg"]};">'
            f'<span class="gl-tterm-caption-tag">HOW TO READ</span>'
            f'<span class="gl-tterm-caption-text">{safe_html(how_to_read)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    _st.markdown('<div class="gl-tterm-wrap">', unsafe_allow_html=True)
    kwargs = {"use_container_width": True}
    if column_config:
        kwargs["column_config"] = column_config
    if height:
        kwargs["height"] = height
    _st.dataframe(df, **kwargs)
    _st.markdown('</div>', unsafe_allow_html=True)


def render_terminal_empty_state(title: str, reason: str = "",
                                available_actions: list | None = None,
                                icon: str = "◇") -> None:
    """Render a dark terminal empty-state panel (v8 §18.3).

    Answers the three mandatory questions: why empty, is it normal, what
    can I still look at. ``available_actions`` is a list of short strings
    shown as bullet-style items.
    """
    import streamlit as _st
    safe_title = safe_html(title)
    safe_reason = safe_html(reason) if reason else ""
    actions_html = ""
    if available_actions:
        items = "".join(
            f'<li class="gl-tempty-item">{safe_html(a)}</li>'
            for a in available_actions
        )
        actions_html = (
            f'<div class="gl-tempty-actions-label">仍可查看</div>'
            f'<ul class="gl-tempty-actions">{items}</ul>'
        )
    reason_html = (
        f'<div class="gl-tempty-reason">{safe_reason}</div>' if safe_reason else ""
    )
    html = (
        f'<div class="gl-tempty">'
        f'<div class="gl-tempty-glyph">{safe_html(icon)}</div>'
        f'<div class="gl-tempty-title">{safe_title}</div>'
        f'{reason_html}'
        f'{actions_html}'
        f'</div>'
    )
    _st.markdown(html, unsafe_allow_html=True)


def render_terminal_error_state(title: str, reason: str = "",
                                schema_hint: str = "",
                                fallback_note: str = "") -> None:
    """Render a dark terminal error panel (v8 §18.4).

    Answers: which module failed, what's still usable, what paused, and
    (if schema) which field is missing. ``schema_hint`` should be a short
    phrase like ``"缺欄位 short_name / company_name"``.
    """
    import streamlit as _st
    t = _GL_TERMINAL_TONES["danger"]
    safe_title = safe_html(title)
    safe_reason = safe_html(reason) if reason else ""
    safe_schema = safe_html(schema_hint) if schema_hint else ""
    safe_fallback = safe_html(fallback_note) if fallback_note else ""
    reason_html = (
        f'<div class="gl-terror-reason">{safe_reason}</div>' if safe_reason else ""
    )
    schema_html = (
        f'<div class="gl-terror-schema"><span>schema</span>{safe_schema}</div>'
        if safe_schema else ""
    )
    fallback_html = (
        f'<div class="gl-terror-fallback"><span>可用模式</span>{safe_fallback}</div>'
        if safe_fallback else ""
    )
    html = (
        f'<div class="gl-terror" '
        f'style="--te-accent:{t["accent"]};--te-border:{t["border"]};'
        f'--te-bg:{t["bg"]};--te-text:{t["text"]};">'
        f'<div class="gl-terror-head">'
        f'<span class="gl-terror-glyph">!</span>'
        f'<span class="gl-terror-tag">ERROR</span>'
        f'<span class="gl-terror-title">{safe_title}</span>'
        f'</div>'
        f'{reason_html}{schema_html}{fallback_html}'
        f'</div>'
    )
    _st.markdown(html, unsafe_allow_html=True)


# --- v8 §15.10 · Governance 3×3 Gate Matrix --------------------------------
# Technical descriptions surfaced on hover for each gate (kept alongside the
# zh label dict so page code only has to import one helper).
GATE_TECH_DESCRIPTIONS = {
    "models_available":
        "模型 artefact 已於 MLflow Registry 註冊並可由 predict pipeline 載入。",
    "model_cards_generated":
        "Model Card 完整輸出 (訓練資料 window / hyperparam / feature list / AUC by fold)。",
    "drift_analysis_complete":
        "PSI / KS 分析對所有特徵完成計算，閾值 PSI < 0.2 無嚴重漂移。",
    "signal_decay_assessed":
        "訊號衰減測試通過：IC 在 T+1 / T+5 / T+20 皆維持正值與單調性。",
    "baseline_established":
        "Benchmark baseline (equal-weight + industry-neutral) 已記錄並成為未來迴歸比較基線。",
    "prediction_pipeline_valid":
        "Predict pipeline 端到端通過 unit tests，欄位 schema / dtype / 無 NaN 均通過。",
    "dsr_revalidated":
        "Deflated Sharpe Ratio 重新驗證通過顯著性 (p < 0.05)，排除多重測試偏差。",
    "no_severe_drift":
        "所有特徵的 PSI 皆 < 0.25；前 10% 重要特徵的 PSI 皆 < 0.15。",
    "governance_data_ready":
        "Gate report / DSR report / drift report 已寫入 governance 資料夾且可被前端載入。",
}


def render_gate_matrix(gates: dict, gate_names_zh: dict | None = None,
                       gate_tech: dict | None = None,
                       cols: int = 3) -> None:
    """Render the v8 §15.10 governance 3×3 gate matrix.

    Each cell: dark card (``--gl-bg-card``), 3px left colour bar (emerald for
    PASS, rose for FAIL), ``GATE NN`` mono eyebrow + PASS/FAIL chip top,
    Chinese label body, technical detail surfaced via ``title`` tooltip.

    Args:
        gates: ``{gate_key: bool_pass_status}`` (ordered dict — keys determine
            cell order 01..NN).
        gate_names_zh: optional key→中文 label map. Defaults to the known
            9-gate vocabulary.
        gate_tech: optional key→hover description map. Defaults to
            ``GATE_TECH_DESCRIPTIONS``.
        cols: number of columns (default 3 → 3×3 when 9 gates present).
    """
    import streamlit as _st
    if not gates:
        _st.caption("— gate report unavailable —")
        return
    gate_names_zh = gate_names_zh or {}
    gate_tech = gate_tech or GATE_TECH_DESCRIPTIONS
    check_svg = (
        '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="3" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<polyline points="20 6 9 17 4 12"/></svg>'
    )
    cross_svg = (
        '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="3" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<line x1="18" y1="6" x2="6" y2="18"/>'
        '<line x1="6" y1="6" x2="18" y2="18"/></svg>'
    )
    cells = []
    for idx, (gate_key, passed) in enumerate(gates.items(), start=1):
        label = safe_html(gate_names_zh.get(gate_key, gate_key))
        passed = bool(passed)
        accent = "#10b981" if passed else "#f43f5e"
        status_label = "PASS" if passed else "FAIL"
        status_cls = "ok" if passed else "danger"
        glyph = check_svg if passed else cross_svg
        tech = safe_html(gate_tech.get(gate_key, ""))
        tech_attr = f' title="{tech}"' if tech else ""
        cells.append(
            f'<div class="gl-gate-cell gl-gate-{status_cls}"{tech_attr} '
            f'style="--gate-accent:{accent};">'
            f'<div class="gl-gate-head">'
            f'<span class="gl-gate-eyebrow">GATE {idx:02d}</span>'
            f'<span class="gl-gate-chip">{glyph}<span>{status_label}</span></span>'
            f'</div>'
            f'<div class="gl-gate-label">{label}</div>'
            f'<div class="gl-gate-key">{safe_html(gate_key)}</div>'
            f'</div>'
        )
    _st.markdown(
        f'<div class="gl-gate-matrix" style="--gate-cols:{cols};">'
        + "".join(cells)
        + '</div>',
        unsafe_allow_html=True,
    )


# 9-pillar palette aligned with the .gl-pillar badges
PILLAR_COLORS = {
    "trend":  "#2563eb",
    "fund":   "#10b981",
    "val":    "#a855f7",
    "event":  "#a78bfa",
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


# Cache TTL trimmed to 5 min (was 3600) so RESOLVED-report updates surface
# within a single user session on Streamlit Cloud — gate state is a critical
# trust-affecting datum, stale caches are worse than the small re-read cost.
@st.cache_data(ttl=300)
def load_quality_gates():
    """Single source of truth for quality-gate counts and their per-gate status.

    Reads the latest phase2_report_*.json, returns a dict with:
      - passed   (int)
      - total    (int)
      - failed_names (list[str])   human-readable names of failing gates
      - all_pass (bool)            convenience flag
      - last_verified (str)        report timestamp (YYYY-MM-DD HH:MM or "")

    Falls back to (9, 9, [], True, "") only if the report cannot be loaded —
    the dashboard should never silently show 9/9 when reality is 8/9.
    """
    report_dir = _project_outputs_dir() / "reports"
    candidates = sorted(report_dir.glob("phase2_report_*.json"), reverse=True)
    if not candidates:
        return {"passed": 0, "total": 0, "failed_names": [],
                "all_pass": False, "last_verified": ""}
    try:
        with open(candidates[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        gates = data.get("quality_gates", {}) or {}
        passed = sum(1 for v in gates.values() if v is True or v == "True")
        total = len(gates)
        failed_names = [k for k, v in gates.items()
                        if not (v is True or v == "True")]
        ts = data.get("timestamp", "") or ""
        last_verified = ts[:19].replace("T", " ") if ts else ""
        return {
            "passed": passed,
            "total": total,
            "failed_names": failed_names,
            "all_pass": (passed == total and total > 0),
            "last_verified": last_verified,
        }
    except Exception:
        return {"passed": 0, "total": 0, "failed_names": [],
                "all_pass": False, "last_verified": ""}


def quality_gate_zh(gate_name: str) -> str:
    """Map machine gate names to human-readable Chinese labels."""
    return {
        "all_models_trained":     "所有模型完成訓練",
        "auc_gate_pass":          "AUC 閘門通過",
        "sufficient_folds":       "交叉驗證折數充足",
        "no_data_leakage":        "無資料洩漏",
        "oof_predictions_valid":  "OOF 預測有效",
        "statistical_validity":   "統計顯著性",
        "permutation_tests_pass": "置換檢定通過",
        "feature_stability":      "特徵穩定性",
        "best_model_ic_positive": "最佳模型 IC 為正",
    }.get(gate_name, gate_name)


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
# v10 §6 — Functional Search (command-palette in utility bar center)
# ============================================================================
# Session-state keys used for the shell-level ticker search. Keeping them
# namespaced (`_gl_*`) avoids collisions with analyst-page local widget keys.
_GL_SEARCH_SELECT_KEY = "_gl_util_search"       # selectbox value
_GL_SEARCH_LAST_KEY = "_gl_util_search_last"    # last-processed selection
_GL_SEARCH_TARGET_KEY = "target_ticker"         # consumed by page 0
_GL_SEARCH_PENDING_KEY = "_gl_util_search_pending"  # defer switch_page to safe point

# v11.5.18 FIX — `st.switch_page` requires the EXACT path string that was
# registered via `st.Page()` in app.py. app.py builds absolute paths via
# `P(name) -> str(PAGES / name)` where `PAGES = Path(__file__).resolve().parent
# / "pages"`. A relative path like `"pages/0_🌱_投資解讀面板.py"` does NOT
# match and `switch_page` silently raises (then the `except Exception: pass`
# in the callback swallows it) — the search box becomes a no-op.
#
# We rebuild the same absolute path here from utils.py's own location
# (utils.py lives in the same directory as app.py, so `Path(__file__).parent
# / "pages" / <name>` matches app.py's `P()` output byte-for-byte).
_GL_SEARCH_ROUTE_PAGE = str(Path(__file__).resolve().parent / "pages" / "0_🌱_投資解讀面板.py")


@st.cache_data(show_spinner=False)
def _build_ticker_search_options():
    """Return a (labels, ticker_map) pair for the Search selectbox.

    labels: list of "{ticker} · {short_name} · {company_name}" strings
    ticker_map: dict label → ticker id string

    Cached across reruns; companies.parquet never changes at runtime.
    """
    try:
        df = load_companies().copy()
    except Exception:
        return [], {}
    # Normalise columns
    tid_col = "company_id" if "company_id" in df.columns else df.columns[0]
    short_col = "short_name" if "short_name" in df.columns else None
    name_col = "company_name" if "company_name" in df.columns else None

    labels = []
    ticker_map = {}
    for _, row in df.iterrows():
        tid = str(row[tid_col]).strip()
        if not tid:
            continue
        short = str(row[short_col]).strip() if short_col else ""
        full = str(row[name_col]).strip() if name_col else ""
        parts = [tid]
        if short:
            parts.append(short)
        if full and full != short:
            parts.append(full)
        label = " · ".join(parts)
        labels.append(label)
        ticker_map[label] = tid
    return labels, ticker_map


def _handle_gl_search_change():
    """Selectbox on_change callback — routes to the investment page when a
    real ticker is picked (i.e. not the sentinel / placeholder option).

    Flow:
      1. Resolve label → ticker id; bail on sentinel / duplicate.
      2. Persist `target_ticker` in session_state for page 0 to consume.
      3. Reset the select widget back to the sentinel so the same ticker can
         be re-picked after the user returns to the nav.
      4. Call `st.switch_page()` with the ABSOLUTE path that matches the
         `st.Page()` registration in app.py. RerunException is the intended
         signal from switch_page; any other exception is kept silent so the
         app doesn't break, but the target_ticker is already in session_state
         — the deferred-switch guard (`_consume_pending_switch`) in
         `render_utility_bar` picks it up on the next rerun if needed.

    v11.5.18 fix: the previous implementation used a RELATIVE path
    (`"pages/0_..."`) which does NOT match the absolute path registered by
    app.py's `P()` helper — `st.switch_page` raised a silent exception and
    the search box became a no-op. We now rebuild the same absolute path
    that app.py uses, and add a pending-switch fallback for robustness.
    """
    picked = st.session_state.get(_GL_SEARCH_SELECT_KEY)
    if not picked:
        return
    # Sentinel placeholder — never route on this.
    if picked.startswith("—"):
        return
    # De-dupe against the last routed value.
    last = st.session_state.get(_GL_SEARCH_LAST_KEY)
    if picked == last:
        return
    st.session_state[_GL_SEARCH_LAST_KEY] = picked
    # Resolve label → ticker id.
    _, tmap = _build_ticker_search_options()
    tid = tmap.get(picked)
    if not tid:
        return
    st.session_state[_GL_SEARCH_TARGET_KEY] = tid
    # Reset the select so the same option can be re-picked on return.
    st.session_state[_GL_SEARCH_SELECT_KEY] = "— 搜尋個股代號、公司名 —"
    # Deferred-switch fallback: only set the pending flag if the callback-
    # time switch_page truly failed. The intended RerunException propagates
    # through `raise` and exits the callback without executing the `else`
    # branch — no pending flag, no redundant rerun. If any OTHER exception
    # fires (the defensive case), the flag guarantees a jump on next rerun.
    try:
        st.switch_page(_GL_SEARCH_ROUTE_PAGE)
    except BaseException as _e:
        # RerunException (and StopException) are Streamlit's internal script-
        # control signals — they extend BaseException, not Exception, on
        # purpose so user code can't accidentally swallow them with a plain
        # `except Exception`. `switch_page()` succeeds by RAISING RerunException,
        # so we must re-raise it for the runtime to perform the rerun.
        #
        # Anything else is a real failure (e.g. path not registered with
        # st.navigation) — we swallow it and arm the deferred-switch guard
        # so `_consume_pending_switch` retries on the next rerun.
        _cls = type(_e).__name__
        if _cls in ("RerunException", "StopException") or "ScriptControl" in _cls:
            raise
        # True failure path — arm the deferred-switch guard.
        st.session_state[_GL_SEARCH_PENDING_KEY] = _GL_SEARCH_ROUTE_PAGE


def _consume_pending_switch():
    """Deferred-switch guard — called at the top of `render_utility_bar()`.

    If the previous run's `_handle_gl_search_change` callback set a pending
    switch target but the in-callback `switch_page` didn't actually rerun
    the app onto page 0, this guard completes the jump on the next rerun.

    Idempotent: once consumed, the key is popped; further reruns do nothing
    unless the user picks a new ticker.

    We only trigger the switch when the dashboard is NOT already on the
    target page — otherwise we'd cause an unnecessary rerun loop. The
    detection uses `st.session_state["_gl_active_page"]` which page 0 sets
    on every run; if that key says we're on page 0, we just clear the
    pending flag and exit.
    """
    target = st.session_state.get(_GL_SEARCH_PENDING_KEY)
    if not target:
        return
    # If page 0 has already rendered once and stamped its signature, we're
    # on the target page — no need to re-switch.
    active = st.session_state.get("_gl_active_page", "")
    already_on_target = bool(active) and (active == _GL_SEARCH_ROUTE_PAGE)
    # Always clear the flag so we don't loop — consumed on first pickup.
    st.session_state.pop(_GL_SEARCH_PENDING_KEY, None)
    if already_on_target:
        return
    try:
        st.switch_page(target)
    except Exception:
        # RerunException extends BaseException (not Exception) on purpose,
        # so it propagates past this `except Exception` block up to the
        # Streamlit runtime where it signals the rerun — exactly what we
        # want. This block only swallows TRUE failures (e.g. page not
        # registered), logging them silently so the UI doesn't crash.
        pass


def _render_gl_search_widget():
    """Render the Streamlit selectbox inside the utility-bar CENTER zone.

    Called from `render_utility_bar()` between the LEFT and RIGHT HTML blocks.
    Visual alignment is done via scoped CSS that targets this widget inside a
    `.gl-util-search-slot` marker div.
    """
    labels, _ = _build_ticker_search_options()
    sentinel = "— 搜尋個股代號、公司名 —"
    options = [sentinel] + labels
    # Ensure the session-state key exists before widget instantiation, so the
    # callback can reset it safely without triggering "modified after widget".
    if _GL_SEARCH_SELECT_KEY not in st.session_state:
        st.session_state[_GL_SEARCH_SELECT_KEY] = sentinel
    # Marker div — CSS `:has()` styles the container as a dark search-input.
    st.markdown('<div class="gl-util-search-slot"></div>', unsafe_allow_html=True)
    st.selectbox(
        label="ticker search",
        options=options,
        key=_GL_SEARCH_SELECT_KEY,
        on_change=_handle_gl_search_change,
        label_visibility="collapsed",
        help="輸入個股代號（如 2330）或公司名（如 台積電），選取後自動跳至投資觀察頁",
    )


# ============================================================================
# Top-nav (Option B) — renders 4-group horizontal nav in main canvas
# Works identically with or without sidebar (embed mode safe)
# ============================================================================
def render_utility_bar(info: dict | None = None):
    """Render the terminal-style utility bar above the primary nav (v8 §8.3).

    Three-zone grid:
      LEFT   — LIVE/SNAPSHOT status dot + Dataset window (system state)
      CENTER — functional Search (selectbox routing to 投資觀察 page) [v10 §6]
      RIGHT  — up to 3 key runtime chips: Model · Gates · DSR

    "Verified" timestamp is tucked into the LEFT zone after the Dataset chip
    so the CENTER search stays visually dominant (spec §8.3 "Search 居中").

    v10 §6 refit: the CENTER zone is now a real Streamlit `selectbox` widget
    powered by companies.parquet. Users type ticker (2330) or name (台積電);
    on selection we set `st.session_state["target_ticker"]` and switch to the
    investment-reading page which filters its card list to that ticker.

    Args:
        info: optional overrides. Keys: status, dataset, model, dsr,
              gates_passed, gates_total, last_verified, search_hint.
    """
    info = info or {}

    # v11.5.18 — Deferred-switch guard. If the Search callback set a pending
    # target ticker but switch_page didn't actually fire (older Streamlit or
    # path drift), complete the navigation now before rendering the nav.
    _consume_pending_switch()

    # Sensible defaults — the dashboard truth-of-source is the quality-gates
    # report (already loaded once at app.py boot via load_quality_gates()).
    status = safe_html(info.get("status", "SNAPSHOT"))
    dataset = safe_html(info.get("dataset", "2023/03–2025/03"))
    model = safe_html(info.get("model", "xgboost_D20"))
    dsr = safe_html(info.get("dsr", "12.12"))
    gates_passed = safe_html(info.get("gates_passed", 9))
    gates_total = safe_html(info.get("gates_total", 9))
    last_verified = safe_html(info.get("last_verified", "2026-04-20 14:24"))
    snapshot_tone = "live" if str(info.get("status", "SNAPSHOT")).upper() == "LIVE" else "snapshot"

    # --- LEFT zone: live dot + dataset window + last verified (§8.3 LEFT) ---
    left_parts = [
        f'<span class="gl-util-dot gl-util-{snapshot_tone}"></span>'
        f'<span class="gl-util-label">{status}</span>',
        f'<span class="gl-util-k">Dataset</span><span class="gl-util-v">{dataset}</span>',
        f'<span class="gl-util-k">Verified</span><span class="gl-util-v">{last_verified}</span>',
    ]
    left_html = ''.join(f'<span class="gl-util-seg">{p}</span>' for p in left_parts)

    # --- RIGHT zone: max 3 runtime chips — Model · Gates · DSR (§8.3 RIGHT) ---
    # PASS / FAIL gate chip tone follows gates_passed vs gates_total.
    try:
        gates_ok = int(info.get("gates_passed", 9)) >= int(info.get("gates_total", 9))
    except Exception:
        gates_ok = True
    gate_chip_tone = "ok" if gates_ok else "warn"
    gate_chip_label = "PASS" if gates_ok else "HOLD"
    right_parts = [
        f'<span class="gl-util-k">Model</span>'
        f'<span class="gl-util-v gl-util-mono">{model}</span>',
        f'<span class="gl-util-k">Gates</span>'
        f'<span class="gl-util-v gl-util-mono">{gates_passed}/{gates_total}</span>'
        f'<span class="gl-util-chip {gate_chip_tone}">{gate_chip_label}</span>',
        f'<span class="gl-util-k">DSR</span>'
        f'<span class="gl-util-v gl-util-mono">{dsr}</span>',
    ]
    right_html = ''.join(f'<span class="gl-util-seg">{p}</span>' for p in right_parts)

    # v10 §6 — 3-zone layout via st.columns. Wrapping marker div lets the
    # outer CSS `:has()` selector paint this block as the sticky terminal bar.
    st.markdown('<div class="gl-utilbar-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    # v11.5.9 — Left zone widened so the full `Verified 2026-04-20 HH:MM`
    # stamp no longer truncates mid-digit, and the CENTER search pill is
    # pushed a little to the right for better visual balance under the
    # 四分頁 primary nav.  Right zone loses the delta to compensate;
    # Model + Gates + DSR still fit comfortably at >=1280px canvas width.
    c_left, c_center, c_right = st.columns([2.8, 1.6, 2.4], gap="small")
    with c_left:
        st.markdown(
            f'<span class="gl-util-left">{left_html}</span>',
            unsafe_allow_html=True,
        )
    with c_center:
        _render_gl_search_widget()
    with c_right:
        st.markdown(
            f'<span class="gl-util-right">{right_html}</span>',
            unsafe_allow_html=True,
        )


# ============================================================================
# Top-nav (Option B · v4 audit §5) — 3-layer architecture
#   Layer 1: Utility Bar (system metadata, pure HTML)
#   Layer 2: Primary pills (4 groups)
#   Layer 3: Secondary contextual nav (pages within active group)
# ============================================================================
def render_top_nav(groups: dict, active_page_title: str = None,
                   utilbar_info: dict | None = None):
    """Render the 3-layer sticky top navigation (v4 audit §5).

    Args:
        groups: ordered dict mapping group label → list of st.Page objects
        active_page_title: title of currently active page
        utilbar_info: optional dict passed through to render_utility_bar
    """
    # Resolve which group contains the active page (if any) — drives both
    # the primary-pill active state AND which pages show in the secondary row.
    active_group = None
    if active_page_title is not None:
        for gname, pages in groups.items():
            if any(getattr(p, "title", None) == active_page_title for p in pages):
                active_group = gname
                break
    if active_group is None:
        # Fallback: first group (e.g. on default Home page)
        active_group = next(iter(groups.keys()))

    # ---- Layer 1 · Utility bar -----------------------------------------
    render_utility_bar(utilbar_info)

    # ---- Layer 2 · Primary pills (4 groups) ----------------------------
    st.markdown('<div class="gl-primary-nav">', unsafe_allow_html=True)
    primary_cols = st.columns(len(groups), gap="small")
    for col, (gname, pages) in zip(primary_cols, groups.items()):
        with col:
            is_group_active = (gname == active_group)
            first_page = pages[0] if pages else None
            if first_page is None:
                continue
            # Wrap the page_link so CSS can target "primary" pills distinctly
            wrapper_class = "gl-pri-pill" + (" gl-pri-active" if is_group_active else "")
            st.markdown(f'<div class="{wrapper_class}" data-group="{gname}">', unsafe_allow_html=True)
            st.page_link(
                first_page,
                label=gname,
                icon=getattr(first_page, "icon", None),
                use_container_width=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- Layer 3 · Secondary contextual nav ----------------------------
    # Show ONLY the pages belonging to the active group. If the user wants
    # another group's pages they click a primary pill first.
    secondary_pages = groups.get(active_group, [])
    if secondary_pages:
        st.markdown(
            f'<div class="gl-secondary-nav">'
            f'<span class="gl-sec-gname">{active_group}</span>',
            unsafe_allow_html=True,
        )
        sec_cols = st.columns(len(secondary_pages), gap="small")
        for col, p in zip(sec_cols, secondary_pages):
            with col:
                is_active = (active_page_title is not None
                             and getattr(p, "title", None) == active_page_title)
                wrapper_class = "gl-sec-pill" + (" gl-sec-active" if is_active else "")
                st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
                st.page_link(
                    p,
                    label=getattr(p, "title", str(p)),
                    icon=getattr(p, "icon", None),
                    use_container_width=True,
                )
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def inject_sidebar_action_buttons(manual_page=None, home_page=None,
                                  reset_key: str = "_gl_reset",
                                  home_key: str = "_gl_home",
                                  manual_key: str = "_gl_manual"):
    """Render real RELOAD + HOME + MANUAL buttons in the sidebar.

    v11.5.10 layout — 3-zone grid so operators can jump back to the
    home/情境主控 page in one click without hunting the top nav:

        ┌────────────┬───────────┐
        │  RELOAD    │   HOME    │   ← top row, 50/50 split
        ├────────────┴───────────┤
        │        MANUAL          │   ← bottom row, full width
        └────────────────────────┘

    Args:
        manual_page: st.Page object for the 使用手冊 page, or a path string.
            If None, manual button shows an error toast.
        home_page: st.Page object for the 情境主控 home page.
            If None, home button shows an error toast.
        reset_key / home_key / manual_key: unique widget keys.
    """
    with st.sidebar:
        # ---- Top row: RELOAD + HOME (50/50 split) ----
        st.markdown('<div class="gl-sidebtn-row gl-sidebtn-top">', unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="small")
        with c1:
            # v11.5.5 — Material Symbol icons replace kawaii 🔄/❓ emoji.
            if st.button("RELOAD", key=reset_key, use_container_width=True,
                         icon=":material/refresh:",
                         help="清除快取並重新載入儀表板資料"):
                st.cache_data.clear()
                # Give users visible feedback — otherwise "nothing happens" UX
                st.toast("快取已清除 · 重新載入中", icon=":material/check_circle:")
                st.rerun()
        with c2:
            if st.button("HOME", key=home_key, use_container_width=True,
                         icon=":material/home:",
                         help="回到情境主控首頁"):
                if home_page is not None:
                    try:
                        st.switch_page(home_page)
                    except Exception:
                        st.toast("找不到首頁。", icon=":material/error:")
                else:
                    st.toast("首頁未註冊。", icon=":material/error:")
        st.markdown('</div>', unsafe_allow_html=True)

        # ---- Bottom row: MANUAL (full width, same total width as top row) ----
        st.markdown('<div class="gl-sidebtn-row gl-sidebtn-bottom">', unsafe_allow_html=True)
        if st.button("MANUAL", key=manual_key, use_container_width=True,
                     icon=":material/menu_book:",
                     help="查看使用手冊與白話解說"):
            if manual_page is not None:
                try:
                    st.switch_page(manual_page)
                except Exception:
                    st.toast("找不到手冊頁。", icon=":material/error:")
            else:
                st.toast("手冊頁未註冊。", icon=":material/error:")
        st.markdown('</div>', unsafe_allow_html=True)
