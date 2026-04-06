"""
台灣股市多因子預測系統 — Landing Page
Fixed historical dataset interactive analysis & research showcase platform

兩條路徑：
  1. 投資解讀面板 → 簡單易懂的投資判讀與公司基本面
  2. 量化研究工作台 → 進階模型指標、回測績效、特徵分析
"""

import streamlit as st
from pathlib import Path
import plotly.graph_objects as go
import json
from datetime import datetime

# ===== Custom CSS (Landing Page Styling) =====
st.markdown("""
<style>
    /* Hero section */
    .hero-container {
        text-align: center;
        padding: 40px 20px 20px 20px;
    }
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #636EFA, #00CC96);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
        line-height: 1.2;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        color: #5a6577;
        margin-top: 0;
        margin-bottom: 30px;
        line-height: 1.5;
    }

    /* Pathway cards */
    .path-card {
        background: #ffffff;
        border: 2px solid #e0e4ea;
        border-radius: 20px;
        padding: 36px 28px;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
        min-height: 420px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: center;
        animation: slideInUp 0.6s ease-out;
    }
    .path-card-beginner {
        background: linear-gradient(135deg, #fffaf0 0%, #fff5eb 100%);
        border-color: #fed7aa;
    }
    .path-card-beginner:hover {
        border-color: #fb923c;
        box-shadow: 0 8px 30px rgba(251, 146, 60, 0.15);
        transform: translateY(-4px);
    }
    .path-card-advanced {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-color: #7dd3fc;
    }
    .path-card-advanced:hover {
        border-color: #0284c7;
        box-shadow: 0 8px 30px rgba(2, 132, 199, 0.15);
        transform: translateY(-4px);
    }
    @keyframes slideInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    .path-icon {
        font-size: 3.5rem;
        margin-bottom: 16px;
    }
    .path-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a1f36;
        margin-bottom: 12px;
    }
    .path-desc {
        font-size: 0.92rem;
        color: #5a6577;
        line-height: 1.6;
        margin-bottom: 20px;
        flex-grow: 1;
    }
    .path-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: center;
        margin-bottom: 20px;
    }
    .path-tag {
        background: #f0f2ff;
        color: #636EFA;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 5px 12px;
        border-radius: 20px;
        border: 1px solid #dde1eb;
    }
    .path-tag-green {
        background: #ecfdf5;
        color: #059669;
        border-color: #d1fae5;
    }

    /* System stats */
    .stat-row {
        display: flex;
        justify-content: center;
        gap: 40px;
        margin: 30px 0 10px 0;
        flex-wrap: wrap;
    }
    .stat-item {
        text-align: center;
    }
    .stat-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #636EFA;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #9ca3af;
        margin-top: 2px;
    }

    /* Data freshness notice */
    .freshness-box {
        background: #f0f9ff;
        border-left: 4px solid #0284c7;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        font-size: 0.85rem;
        color: #0c4a6e;
        margin: 20px 0;
    }
    .freshness-box strong { color: #0c4a6e; }

    /* Methodology section */
    .methodology-box {
        background: #f8f9fc;
        border: 1px solid #dde1eb;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 16px 0;
    }
    .methodology-title {
        font-size: 1rem;
        font-weight: 700;
        color: #1a1f36;
        margin-bottom: 12px;
    }
    .methodology-desc {
        font-size: 0.9rem;
        color: #5a6577;
        line-height: 1.5;
    }

    /* Footer */
    .landing-footer {
        text-align: center;
        padding: 20px 0;
        color: #9ca3af;
        font-size: 0.82rem;
        border-top: 1px solid #e0e4ea;
        margin-top: 40px;
    }

    /* Warning box for disclaimer */
    .warning-box {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        border-radius: 0 8px 8px 0;
        padding: 14px 18px;
        font-size: 0.85rem;
        color: #92400e;
        margin: 20px 0;
    }
    .warning-box strong { color: #92400e; }

    /* Streamlit button customization */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)


# ===== Hero Section =====
st.markdown("""
<div class="hero-container">
    <div class="hero-title">📈 台股多因子預測決策輔助系統</div>
    <div class="hero-subtitle">
        固定歷史資料集下的互動式分析與研究展示平台<br>
        <em>以 2023/03 - 2025/03 台股資料為基礎，提供多種視角的投資決策參考</em>
    </div>
</div>
""", unsafe_allow_html=True)


# ===== Helper: Load KPIs from Latest Report =====
@st.cache_data(ttl=3600)
def load_kpis_from_report():
    """Load KPIs from the latest phase2_report JSON with fallback to hardcoded values."""
    try:
        # Find the latest report
        report_dir = Path(__file__).parent.parent.parent / "outputs" / "reports"
        report_files = list(report_dir.glob("phase2_report_*.json"))
        if not report_files:
            raise FileNotFoundError("No phase2_report files found")

        latest_report = sorted(report_files, key=lambda p: p.stat().st_mtime, reverse=True)[0]

        with open(latest_report, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract KPIs
        rows = data.get("results", {}).get("feature_store", {}).get("rows", 948976)
        cols = data.get("results", {}).get("feature_store", {}).get("cols", 59)
        n_selected = len(data.get("results", {}).get("feature_selection", {}).get("selected", []))
        n_folds = data.get("results", {}).get("walk_forward", {}).get("n_folds", 4)

        quality_gates = data.get("quality_gates", {})
        gates_passed = sum(1 for v in quality_gates.values() if v is True or v == "True")
        total_gates = len(quality_gates)

        return {
            "rows": f"{rows:,}",
            "cols": cols,
            "n_selected": n_selected,
            "gates_passed": gates_passed,
            "total_gates": total_gates,
            "date_range": data.get("results", {}).get("feature_store", {}).get("date_range", "2023/03 - 2025/03"),
            "report_timestamp": data.get("timestamp", "")
        }
    except Exception as e:
        # Fallback to hardcoded values
        st.warning(f"Could not load report data: {e}. Using default values.")
        return {
            "rows": "948,976",
            "cols": 59,
            "n_selected": 23,
            "gates_passed": 7,
            "total_gates": 7,
            "date_range": "2023/03 - 2025/03",
            "report_timestamp": ""
        }


kpis = load_kpis_from_report()

# ===== System Stats =====
st.markdown(f"""
<div class="stat-row">
    <div class="stat-item">
        <div class="stat-value">{kpis['rows']}</div>
        <div class="stat-label">樣本資料點</div>
    </div>
    <div class="stat-item">
        <div class="stat-value">{kpis['n_selected']}</div>
        <div class="stat-label">篩選特徵因子</div>
    </div>
    <div class="stat-item">
        <div class="stat-value">3</div>
        <div class="stat-label">預測週期</div>
    </div>
    <div class="stat-item">
        <div class="stat-value">{kpis['gates_passed']}/{kpis['total_gates']}</div>
        <div class="stat-label">品質門控通過</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ===== Data Freshness Notice =====
st.markdown("""
<div class="freshness-box">
<strong>📅 資料時效說明</strong>：本平台為固定歷史資料集（2023/03 至 2025/03）下的互動式分析與研究展示系統，<br>可依不同日期與預測週期回看模型判讀與策略表現。非即時市場監控系統。
</div>
""", unsafe_allow_html=True)

st.markdown("")

# ===== Dual-Panel Narrative =====
st.markdown("""
#### 📚 兩種閱讀模式

本平台基於同一套台股多因子研究引擎，提供兩種閱讀模式：
- **投資解讀面板**：協助理解投資意涵的決策資訊呈現
- **量化研究工作台**：完整呈現模型指標、回測與研究證據的專業視角
""")

st.markdown("")

# ===== Two Pathway Cards with Navigation =====
col_left, col_space, col_right = st.columns([5, 1, 5])

with col_left:
    st.markdown("""
<div class="path-card path-card-beginner">
    <div class="path-icon">🌱</div>
    <div class="path-title">投資解讀面板</div>
    <div class="path-desc">
        將研究結果翻譯成投資人可理解的決策資訊。可回看不同日期、不同預測週期下的模型判讀與策略表現。
    </div>
    <div class="path-tags">
        <span class="path-tag">歷史判讀</span>
        <span class="path-tag">公司輪廓</span>
        <span class="path-tag">成本分析</span>
        <span class="path-tag">風險提示</span>
        <span class="path-tag">基本面</span>
    </div>
</div>
""", unsafe_allow_html=True)

    if st.button("🌱  進入投資解讀面板", use_container_width=True, type="primary"):
        st.switch_page("pages/0_🌱_投資解讀面板.py")

with col_right:
    st.markdown("""
<div class="path-card path-card-advanced">
    <div class="path-icon">⚙️</div>
    <div class="path-title">量化研究工作台</div>
    <div class="path-desc">
        面向教授、評審與量化研究者。完整呈現研究流程、方法論、模型指標與驗證結果。
    </div>
    <div class="path-tags">
        <span class="path-tag path-tag-green">模型指標</span>
        <span class="path-tag path-tag-green">ICIR 分析</span>
        <span class="path-tag path-tag-green">策略回測</span>
        <span class="path-tag path-tag-green">特徵工程</span>
        <span class="path-tag path-tag-green">資料探索</span>
        <span class="path-tag path-tag-green">模型治理</span>
        <span class="path-tag path-tag-green">信號監控</span>
    </div>
</div>
""", unsafe_allow_html=True)

    if st.button("⚙️  進入量化研究工作台", use_container_width=True, type="secondary"):
        st.switch_page("pages/1_📊_Model_Metrics.py")


# ===== Phase Boundary Section =====
st.markdown("")
st.divider()

st.markdown("#### 🎯 研究階段進展")

phase_col1, phase_col2, phase_col3 = st.columns(3)

with phase_col1:
    st.markdown("""
<div class="methodology-box" style="background: #f0fdf4; border-left: 4px solid #22c55e;">
    <div class="methodology-title">✅ Phase 1: 資料處理與特徵工程</div>
    <div class="methodology-desc" style="font-size: 0.85rem; color: #166534;">
        五支柱特徵工程 | 43 → 23 特徵篩選 | 已完成
    </div>
</div>
""", unsafe_allow_html=True)

with phase_col2:
    st.markdown("""
<div class="methodology-box" style="background: #f0fdf4; border-left: 4px solid #22c55e;">
    <div class="methodology-title">✅ Phase 2: 模型訓練與回測驗證</div>
    <div class="methodology-desc" style="font-size: 0.85rem; color: #166534;">
        雙引擎 | Purged Walk-Forward CV | 已完成
    </div>
</div>
""", unsafe_allow_html=True)

with phase_col3:
    st.markdown("""
<div class="methodology-box" style="background: #f0fdf4; border-left: 4px solid #22c55e;">
    <div class="methodology-title">✅ Phase 3: 模型治理與風控強化</div>
    <div class="methodology-desc" style="font-size: 0.85rem; color: #166534;">
        Model Card | 漂移偵測 | 信號監控 | DSR 驗證 | 已完成
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("")

# ===== Brief Methodology =====
st.divider()

st.markdown("#### 🔧 系統方法論")

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown("""
<div class="methodology-box">
    <div class="methodology-title">🎯 五支柱特徵工程</div>
    <div class="methodology-desc">
        趨勢動能 · 基本面 · 估值 · 事件輿情 · 風險環境，共 43 候選因子經三階段篩選至 23 個。
    </div>
</div>
""", unsafe_allow_html=True)

with m2:
    st.markdown("""
<div class="methodology-box">
    <div class="methodology-title">✅ 嚴謹的交叉驗證</div>
    <div class="methodology-desc">
        Purged Walk-Forward CV（4 折），Expanding Window + 20 日 Embargo 杜絕前瞻偏差。
    </div>
</div>
""", unsafe_allow_html=True)

with m3:
    st.markdown("""
<div class="methodology-box">
    <div class="methodology-title">⚡ 雙引擎 + 回測</div>
    <div class="methodology-desc">
        LightGBM / XGBoost 雙引擎加上等權 Ensemble，三種成本情境下的策略回測驗證。
    </div>
</div>
""", unsafe_allow_html=True)


# ===== Pipeline Flow Diagram =====
st.markdown("")
st.markdown("#### 📊 系統管道流程")

# Create a pipeline flow with Plotly and phase labels
fig = go.Figure()

# Define 6 pipeline stages with phase assignments
stages = [
    ("FinMind API", "Phase 1"),
    ("Feature Store", "Phase 1"),
    ("特徵篩選", "Phase 1"),
    ("模型訓練", "Phase 2"),
    ("策略回測", "Phase 2"),
    ("模型治理", "Phase 3"),
    ("儀表板", "用戶界面"),
]
x_positions = list(range(len(stages)))

# Color mapping for phases
phase_colors = {
    "Phase 1": "#10b981",
    "Phase 2": "#10b981",
    "Phase 3": "#f59e0b",
    "用戶界面": "#636EFA",
}

# Add stage nodes with phase colors
for i, (stage, phase) in enumerate(stages):
    color = phase_colors.get(phase, "#636EFA")
    fig.add_trace(go.Scatter(
        x=[i],
        y=[0],
        mode='markers+text',
        marker=dict(size=18, color=color),
        text=stage,
        textposition="top center",
        hoverinfo='text',
        hovertext=f"{stage} ({phase})",
        showlegend=False
    ))

# Add phase labels below
for i, (stage, phase) in enumerate(stages):
    fig.add_annotation(
        x=i,
        y=-0.4,
        text=phase,
        showarrow=False,
        font=dict(size=9, color='#6b7280'),
        xref='x',
        yref='y'
    )

# Add arrows between stages
for i in range(len(stages) - 1):
    fig.add_annotation(
        x=i + 0.65,
        y=0,
        ax=i + 0.35,
        ay=0,
        xref='x',
        yref='y',
        axref='x',
        ayref='y',
        arrowhead=2,
        arrowsize=1,
        arrowwidth=2,
        arrowcolor='#9ca3af',
        showarrow=True
    )

fig.update_layout(
    showlegend=False,
    hovermode='closest',
    xaxis=dict(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        range=[-0.5, len(stages) - 0.5]
    ),
    yaxis=dict(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        range=[-0.7, 1]
    ),
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    height=180,
    margin=dict(l=20, r=20, t=60, b=40)
)

st.plotly_chart(fig, use_container_width=True)


# ===== Disclaimer =====
st.markdown("""
<div class="warning-box">
⚠️ <strong>免責聲明</strong>：本系統為課程專案成果，不構成任何投資建議。所有顯示結果均為歷史回測數據，非即時預測。
股市投資有風險，過去的回測績效不代表未來報酬。投資前請審慎評估自身風險承受能力。
</div>
""", unsafe_allow_html=True)


# ===== Footer =====
footer_year = datetime.now().year
st.markdown(f"""
<div class="landing-footer">
    大數據與商業分析專案 (v2.0) &nbsp;|&nbsp; Built with Streamlit & Plotly &nbsp;|&nbsp;
    Data: FinMind API + 課堂數據集 &nbsp;|&nbsp; Models: LightGBM + XGBoost<br>
    <small>© {footer_year} Course Project &nbsp;|&nbsp;
    <a href="https://github.com/andychen050229-cell/taiwan-stock-multifactor" target="_blank" style="color: #636EFA; text-decoration: none;">GitHub Repository</a></small>
</div>
""", unsafe_allow_html=True)
