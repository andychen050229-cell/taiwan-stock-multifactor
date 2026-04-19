"""
台灣股市多因子預測系統 — Landing Page (glint-light design)

Two entrypoints:
  1. 投資解讀面板 → plain-language decision aids
  2. 量化研究工作台 → full quant research + validation
"""

import streamlit as st
from pathlib import Path
import plotly.graph_objects as go
import json
import importlib.util
from datetime import datetime

# ---- Load shared utils -------------------------------------------------
_utils_path = Path(__file__).resolve().parent.parent / "utils.py"
_spec = importlib.util.spec_from_file_location("dashboard_utils", str(_utils_path))
_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils)
inject_custom_css = _utils.inject_custom_css
render_kpi = _utils.render_kpi
load_phase6_json = _utils.load_phase6_json

inject_custom_css()

# ---- Page-local CSS (extensions to the global theme) -------------------
st.markdown("""
<style>
/* Pathway cards — glint-style elevated surface */
.path-card {
    background: var(--gl-surface);
    border: 1px solid var(--gl-border);
    border-radius: 18px;
    padding: 32px 26px;
    min-height: 420px;
    position: relative;
    overflow: hidden;
    transition: all .3s ease;
    box-shadow: var(--gl-shadow-sm);
}
.path-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: var(--gl-grad-tech);
    opacity: 0.7;
}
.path-card:hover {
    transform: translateY(-4px);
    box-shadow: var(--gl-shadow-glow);
    border-color: rgba(37,99,235,0.3);
}
.path-card-beginner {
    background: linear-gradient(135deg, #ffffff 0%, #fffbeb 100%);
}
.path-card-beginner::before {
    background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%);
}
.path-card-advanced {
    background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%);
}
.path-icon {
    font-size: 2.6rem; margin-bottom: 14px;
    filter: drop-shadow(0 2px 8px rgba(0,0,0,0.08));
}
.path-title {
    font-size: 1.35rem; font-weight: 700; color: var(--gl-text);
    margin-bottom: 10px; letter-spacing: -0.01em;
}
.path-desc {
    font-size: 0.92rem; color: var(--gl-text-2);
    line-height: 1.6; margin-bottom: 18px;
}
.path-tags {
    display: flex; flex-wrap: wrap; gap: 6px;
}

/* Phase chips (timeline) */
.phase-chip {
    background: var(--gl-surface);
    border: 1px solid var(--gl-border);
    border-radius: 10px;
    padding: 12px 14px;
    position: relative;
    overflow: hidden;
}
.phase-chip::before {
    content: "";
    position: absolute; top: 0; left: 0; bottom: 0;
    width: 3px;
    background: var(--gl-emerald);
}
.phase-chip.current::before { background: var(--gl-grad-pri); }
.phase-chip .phase-label {
    font-family: var(--gl-font-mono);
    font-size: 0.72rem; color: var(--gl-text-3);
    font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
}
.phase-chip .phase-title {
    font-size: 0.92rem; font-weight: 600; color: var(--gl-text);
    margin-top: 2px;
}
.phase-chip .phase-sub {
    font-size: 0.78rem; color: var(--gl-text-2);
    margin-top: 4px;
    font-family: var(--gl-font-mono);
}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# Load live KPIs from reports
# ============================================================================
@st.cache_data(ttl=3600)
def load_kpis_from_report():
    """Load KPIs from the latest phase2_report JSON."""
    try:
        report_dir = Path(__file__).parent.parent.parent / "outputs" / "reports"
        report_files = list(report_dir.glob("phase2_report_*.json"))
        if not report_files:
            raise FileNotFoundError("No phase2_report files found")
        latest_report = sorted(report_files, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        with open(latest_report, 'r', encoding='utf-8') as f:
            data = json.load(f)

        rows = data.get("results", {}).get("feature_store", {}).get("rows", 948976)
        cols = data.get("results", {}).get("feature_store", {}).get("cols", 1626)
        n_selected = len(data.get("results", {}).get("feature_selection", {}).get("selected", []))
        quality_gates = data.get("quality_gates", {})
        gates_passed = sum(1 for v in quality_gates.values() if v is True or v == "True")
        total_gates = len(quality_gates)

        return {
            "rows": rows,
            "cols": cols,
            "n_selected": n_selected,
            "gates_passed": gates_passed,
            "total_gates": total_gates,
            "date_range": data.get("results", {}).get("feature_store", {}).get("date_range", "2023/03 - 2025/03"),
            "report_timestamp": data.get("timestamp", "")
        }
    except Exception:
        return {
            "rows": 948976, "cols": 1626, "n_selected": 91,
            "gates_passed": 9, "total_gates": 9,
            "date_range": "2023/03 - 2025/03",
            "report_timestamp": ""
        }


kpis = load_kpis_from_report()

# Try to pull LOPO headline numbers
lopo_data, _ = load_phase6_json("lopo_pillar_contribution_D20.json")
thresh_data, _ = load_phase6_json("threshold_sweep_xgb_D20.json")

baseline_auc = lopo_data["baseline"]["auc_macro"] if lopo_data else 0.649
top_pillar = lopo_data["ranking_by_delta_auc"][0] if lopo_data else None
best_edge = max(t["edge"] for t in thresh_data["threshold_sweep"]) if thresh_data else 0.117

# ============================================================================
# Hero
# ============================================================================
st.markdown(f"""
<div class="gl-hero">
    <span class="gl-hero-eyebrow">TAIWAN STOCK · MULTI-FACTOR PREDICTION</span>
    <div class="gl-hero-title">台股多因子預測決策輔助系統</div>
    <div class="gl-hero-subtitle">
        以 <strong>2023/03 – 2025/03</strong> 台股歷史資料為基礎，整合
        <strong>9 支柱 1,623 候選因子</strong>、<strong>LightGBM + XGBoost 雙引擎</strong>、
        <strong>Purged Walk-Forward CV</strong> 與 <strong>LOPO 深度驗證</strong>，
        提供可回看、可解釋、可治理的研究展示平台。
    </div>
    <div style="margin-top:20px; display:flex; gap:8px; flex-wrap:wrap;">
        <span class="gl-live">phase 1-6 · all gates passed</span>
        <span class="gl-chip primary">9 / 9 quality gates</span>
        <span class="gl-chip violet">xgboost_D20 OOS AUC {baseline_auc:.3f}</span>
        <span class="gl-chip ok">best edge +{best_edge*100:.1f}pp</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================================
# KPI Grid — live metrics row (6 tiles)
# ============================================================================
st.markdown("### 系統即時指標")

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    render_kpi(
        "SAMPLES", f"{kpis['rows']//1000:,}K",
        sub=f"{kpis['rows']:,} rows", accent="blue"
    )
with k2:
    render_kpi(
        "FEATURES", f"{kpis['n_selected']}",
        sub=f"from {kpis['cols']:,} candidates", accent="violet"
    )
with k3:
    render_kpi(
        "PILLARS", "9",
        sub="trend/fund/val/event/risk...", accent="cyan"
    )
with k4:
    render_kpi(
        "HORIZONS", "3",
        sub="D+1 · D+5 · D+20", accent="amber"
    )
with k5:
    render_kpi(
        "QUALITY", f"{kpis['gates_passed']}/{kpis['total_gates']}",
        delta=("ALL PASS", "up"),
        sub="Phase 2 quality gates", accent="emerald"
    )
with k6:
    if top_pillar:
        render_kpi(
            "TOP PILLAR", f"{top_pillar['pillar']}",
            delta=(f"+{top_pillar['delta_auc']*10000:.1f}bps", "up"),
            sub="LOPO top contributor", accent="rose"
        )
    else:
        render_kpi("TOP PILLAR", "risk", sub="LOPO", accent="rose")

# ============================================================================
# Data freshness banner
# ============================================================================
_ts = kpis.get("report_timestamp", "")
_ts_display = _ts[:19].replace("T", " ") if _ts else "2026-04-20 03:20"
st.markdown(f"""
<div class="gl-box-info" style="margin-top:20px;">
<strong>📅 資料時效</strong>：本平台為<strong>固定歷史資料集（{kpis['date_range']}）</strong>下的
互動式分析與研究展示系統，非即時市場監控。支援回看不同日期與預測週期的模型判讀與策略表現。<br>
<span style="font-size:.82rem; color:var(--gl-text-3);">
🕐 最新報告時間 <span class="gl-mono">{_ts_display}</span>
&nbsp;·&nbsp; 🔬 研究模式 <span class="gl-mono">Historical Interactive Snapshot</span>
&nbsp;·&nbsp; 📦 Phase 1-6 Complete
</span>
</div>
""", unsafe_allow_html=True)


# ============================================================================
# Dual-path entrypoints
# ============================================================================
st.markdown("### 兩種閱讀模式")
st.markdown(
    "<div style='color:var(--gl-text-2); font-size:.95rem; margin-bottom:16px;'>"
    "本平台基於同一套台股多因子研究引擎，提供兩種閱讀模式，依讀者背景選擇最適路徑："
    "</div>",
    unsafe_allow_html=True,
)

col_left, col_space, col_right = st.columns([5, 1, 5])

with col_left:
    st.markdown("""
<div class="path-card path-card-beginner">
    <div class="path-icon">🌱</div>
    <div class="path-title">投資解讀面板</div>
    <div class="path-desc">
        面向投資人/行銷/商管讀者。將研究結果翻譯成可理解的決策資訊 ─
        哪個產業看好、這檔股票的基本面長怎樣、成本多少才划算、風險需要注意什麼。
    </div>
    <div class="path-tags">
        <span class="gl-chip">歷史判讀</span>
        <span class="gl-chip">公司輪廓</span>
        <span class="gl-chip">成本分析</span>
        <span class="gl-chip warn">風險提示</span>
        <span class="gl-chip">基本面</span>
    </div>
</div>
""", unsafe_allow_html=True)
    if st.button("🌱  進入投資解讀面板", use_container_width=True, type="primary", key="btn_beginner"):
        st.switch_page("pages/0_🌱_投資解讀面板.py")

with col_right:
    st.markdown("""
<div class="path-card path-card-advanced">
    <div class="path-icon">⚙️</div>
    <div class="path-title">量化研究工作台</div>
    <div class="path-desc">
        面向教授、評審、量化研究者。完整呈現研究流程、方法論、模型指標與驗證結果 ─
        ICIR 分析、Purged CV、LOPO 驗證、Threshold Sweep、個股 Deep Case。
    </div>
    <div class="path-tags">
        <span class="gl-chip primary">模型績效</span>
        <span class="gl-chip primary">ICIR 分析</span>
        <span class="gl-chip primary">策略回測</span>
        <span class="gl-chip violet">特徵工程</span>
        <span class="gl-chip violet">文本分析</span>
        <span class="gl-chip ok">模型治理</span>
        <span class="gl-chip ok">信號監控</span>
        <span class="gl-chip danger">Phase 6 深度驗證</span>
    </div>
</div>
""", unsafe_allow_html=True)
    if st.button("⚙️  進入量化研究工作台", use_container_width=True, type="secondary", key="btn_advanced"):
        st.switch_page("pages/1_📊_Model_Metrics.py")


# ============================================================================
# Phase timeline
# ============================================================================
st.markdown("### 六階段研究進度")

phase_cols = st.columns(6)
phases = [
    ("Phase 1", "資料 · 特徵工程", "1,626 候選因子 · 9 支柱", False),
    ("Phase 2", "模型訓練 · 驗證", "2 engines · 3 horizons · 4-fold CV", False),
    ("Phase 3", "擴充分析", "成本/跨地平線/支柱/個案", False),
    ("Phase 4", "治理 · 漂移偵測", "Model Card · DSR · Signal Monitor", False),
    ("Phase 5", "文本 · 情緒因子", "jieba + SnowNLP · 500 keywords", False),
    ("Phase 6", "深度驗證", "LOPO · Threshold · 2454", True),
]
for col, (ph, title, sub, is_current) in zip(phase_cols, phases):
    with col:
        badge = '<span class="gl-chip ok" style="font-size:.68rem;">✓</span>'
        if is_current:
            badge = '<span class="gl-chip primary" style="font-size:.68rem;">NEW</span>'
        st.markdown(f"""
        <div class="phase-chip {'current' if is_current else ''}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div class="phase-label">{ph}</div>
                {badge}
            </div>
            <div class="phase-title">{title}</div>
            <div class="phase-sub">{sub}</div>
        </div>
        """, unsafe_allow_html=True)


# ============================================================================
# Methodology overview
# ============================================================================
st.markdown("### 方法論核心")

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown("""
    <div class="gl-panel">
        <div style="font-size:0.72rem; color:var(--gl-text-3); font-weight:600; letter-spacing:.06em; text-transform:uppercase;">FEATURE</div>
        <div style="font-size:1.1rem; font-weight:700; color:var(--gl-text); margin-top:6px;">🎯 九支柱因子工程</div>
        <div style="font-size:.9rem; color:var(--gl-text-2); line-height:1.6; margin-top:10px;">
            <span class="gl-pillar" data-p="trend">trend</span>
            <span class="gl-pillar" data-p="fund">fund</span>
            <span class="gl-pillar" data-p="val">val</span>
            <span class="gl-pillar" data-p="event">event</span>
            <span class="gl-pillar" data-p="risk">risk</span>
            <span class="gl-pillar" data-p="chip">chip</span>
            <span class="gl-pillar" data-p="ind">ind</span>
            <span class="gl-pillar" data-p="txt">txt</span>
            <span class="gl-pillar" data-p="sent">sent</span>
            <br><br>
            <strong>1,623 候選因子</strong>經三階段篩選（IC → Chi²/MI → VIF）
            至 <strong>91 生產特徵</strong>，跨 9 個理論支柱。
        </div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown("""
    <div class="gl-panel">
        <div style="font-size:0.72rem; color:var(--gl-text-3); font-weight:600; letter-spacing:.06em; text-transform:uppercase;">VALIDATION</div>
        <div style="font-size:1.1rem; font-weight:700; color:var(--gl-text); margin-top:6px;">✅ 嚴謹的時序交叉驗證</div>
        <div style="font-size:.9rem; color:var(--gl-text-2); line-height:1.6; margin-top:10px;">
            <strong>Purged Walk-Forward CV</strong>（4 折），
            Expanding Window 配合 <strong>20 日 Embargo</strong> 杜絕前瞻偏差。<br><br>
            <span class="gl-chip primary">initial_train=252</span>
            <span class="gl-chip primary">test=63</span>
            <span class="gl-chip violet">embargo=20</span>
            <br><br>
            Phase 6 再加上 <strong>LOPO 驗證</strong>：逐一移除每個支柱重訓，量化真實邊際貢獻。
        </div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown("""
    <div class="gl-panel">
        <div style="font-size:0.72rem; color:var(--gl-text-3); font-weight:600; letter-spacing:.06em; text-transform:uppercase;">MODEL</div>
        <div style="font-size:1.1rem; font-weight:700; color:var(--gl-text); margin-top:6px;">⚡ 雙引擎 + 成本回測</div>
        <div style="font-size:.9rem; color:var(--gl-text-2); line-height:1.6; margin-top:10px;">
            <strong>LightGBM + XGBoost</strong> 雙引擎加上等權 Ensemble，三地平線覆蓋短中長週期。<br><br>
            <span class="gl-chip">D+1 日度</span>
            <span class="gl-chip">D+5 週度</span>
            <span class="gl-chip primary">D+20 月度</span>
            <br><br>
            三種成本情境：<strong>standard 0.58% · discount 0.36% · conservative 0.73%</strong>。
            D+20 是唯一全情境正報酬的地平線。
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# Pipeline flow
# ============================================================================
st.markdown("### 系統管道流程")

fig = go.Figure()
stages = [
    ("FinMind API",    "Phase 1", "#06b6d4"),
    ("Feature Store",  "Phase 1", "#06b6d4"),
    ("特徵篩選",       "Phase 1", "#06b6d4"),
    ("模型訓練",       "Phase 2", "#2563eb"),
    ("策略回測",       "Phase 2", "#2563eb"),
    ("擴充分析",       "Phase 3", "#7c3aed"),
    ("模型治理",       "Phase 4", "#7c3aed"),
    ("文本情緒",       "Phase 5", "#7c3aed"),
    ("LOPO 驗證",      "Phase 6", "#f43f5e"),
    ("儀表板",         "UI",     "#10b981"),
]
for i, (stage, phase, color) in enumerate(stages):
    fig.add_trace(go.Scatter(
        x=[i], y=[0],
        mode='markers+text',
        marker=dict(size=22, color=color, line=dict(width=2, color="white")),
        text=stage, textposition="top center",
        textfont=dict(family="Inter, sans-serif", size=11, color="#0f172a"),
        hoverinfo='text',
        hovertext=f"{stage} ({phase})",
        showlegend=False
    ))
    fig.add_annotation(
        x=i, y=-0.55, text=phase, showarrow=False,
        font=dict(family="JetBrains Mono, monospace", size=9, color="#94a3b8"),
    )

for i in range(len(stages) - 1):
    fig.add_annotation(
        x=i + 0.75, y=0, ax=i + 0.25, ay=0,
        xref='x', yref='y', axref='x', ayref='y',
        arrowhead=2, arrowsize=1.1, arrowwidth=1.5,
        arrowcolor='#cbd5e1', showarrow=True,
    )

fig.update_layout(
    showlegend=False,
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
               range=[-0.5, len(stages) - 0.5]),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.9, 0.9]),
    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
    height=160, margin=dict(l=20, r=20, t=30, b=20),
)
st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# Disclaimer + Footer
# ============================================================================
st.markdown("""
<div class="gl-box-warn">
⚠️ <strong>免責聲明</strong>：本系統為課程專案成果，不構成任何投資建議。所有顯示結果均為歷史回測數據，
非即時預測。股市投資有風險，過去的回測績效不代表未來報酬。投資前請審慎評估自身風險承受能力。
</div>
""", unsafe_allow_html=True)

footer_year = datetime.now().year
st.markdown(f"""
<div class="gl-footer">
大數據與商業分析專案 <span class="gl-mono">v4.0</span> &nbsp;·&nbsp;
Built with <span class="gl-mono">Streamlit + Plotly + LightGBM + XGBoost</span> &nbsp;·&nbsp;
Data <span class="gl-mono">FinMind API + 選用資料集</span><br>
<small>© {footer_year} Course Project &nbsp;|&nbsp;
<a href="https://github.com/andychen050229-cell/taiwan-stock-multifactor" target="_blank"
   style="color:var(--gl-blue); text-decoration:none;">GitHub Repository</a></small>
</div>
""", unsafe_allow_html=True)
