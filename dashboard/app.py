"""
台灣股市多因子預測系統 — Streamlit Dashboard
Taiwan Stock Multi-Factor Prediction System

啟動方式：
  streamlit run dashboard/app.py
"""

import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

# ===== Page Config =====
st.set_page_config(
    page_title="台灣股市多因子預測系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Custom CSS =====
st.markdown("""
<style>
    /* KPI card styling */
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
    section[data-testid="stSidebar"] .stMetric label,
    section[data-testid="stSidebar"] .stMetric div {
        color: #e0e6f0 !important;
    }
    /* Overview card */
    .overview-card {
        background: #ffffff;
        border: 1px solid #e0e4ea;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.04);
    }
    .guide-step {
        display: flex;
        align-items: flex-start;
        gap: 14px;
        padding: 14px 0;
        border-bottom: 1px solid #f0f2f5;
    }
    .guide-step:last-child { border-bottom: none; }
    .step-number {
        background: #636EFA;
        color: white !important;
        border-radius: 50%;
        width: 32px; height: 32px;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 0.9rem;
        flex-shrink: 0;
    }
    .step-content h4 { margin: 0 0 4px 0; font-size: 1rem; }
    .step-content p { margin: 0; font-size: 0.88rem; color: #5a6577; }
    .highlight-box {
        background: linear-gradient(135deg, #eef2ff 0%, #e0f2fe 100%);
        border-left: 4px solid #636EFA;
        border-radius: 0 8px 8px 0;
        padding: 16px 20px;
        margin: 12px 0;
    }
</style>
""", unsafe_allow_html=True)

# ===== Load Data =====
@st.cache_data
def load_report():
    """Load the latest Phase 2 report JSON."""
    report_dir = Path(__file__).parent.parent / "outputs" / "reports"
    reports = sorted(report_dir.glob("phase2_report_*.json"), reverse=True)
    if not reports:
        st.error("找不到 Phase 2 報告。請先執行 `python run_phase2.py` 以產生資料。")
        st.stop()
    with open(reports[0], "r", encoding="utf-8") as f:
        return json.load(f), reports[0].name

report, report_name = load_report()
results = report.get("results", {})

# ===== Sidebar =====
st.sidebar.markdown("### 📈 多因子預測系統")
st.sidebar.caption(f"Report: `{report_name}`")
status_icon = "✅" if report.get("overall_status") == "PASS" else "⚠️"
st.sidebar.caption(f"Status: {status_icon} {'ALL PASS' if report.get('overall_status') == 'PASS' else 'REVIEW NEEDED'}")
st.sidebar.divider()

# Quality gates in sidebar
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
st.sidebar.caption("Built with Streamlit & Plotly")

# ===== Hero Section =====
st.markdown("""
<div style="text-align:center; padding: 10px 0 6px 0;">
    <h1 style="font-size:2.2rem; margin-bottom:2px;">📈 台灣股市多因子預測系統</h1>
    <p style="font-size:1.05rem; color:#5a6577; margin-top:0;">
        Taiwan Stock Multi-Factor Prediction System — Interactive Dashboard
    </p>
</div>
""", unsafe_allow_html=True)

# ===== KPI Cards =====
best_model = results.get("best_model", "N/A")
benchmark = results.get("benchmark", {})
comparison = results.get("comparison", {})
icir_data = results.get("icir", {})

bt_d20 = results.get("backtest_horizon_20", {})
best_bt = None
for eng in ["xgboost", "ensemble", "lightgbm"]:
    if eng in bt_d20:
        best_bt = bt_d20[eng].get("cost_scenarios", {}).get("discount", {})
        break

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Best Model",
        best_model.replace("_", " ").upper() if best_model else "N/A",
        help="AUC 最高之模型"
    )
with col2:
    best_auc = comparison.get(best_model, {}).get("auc", 0)
    st.metric("Best AUC", f"{best_auc:.4f}", delta=f"+{best_auc - 0.5:.4f} vs random")
with col3:
    best_icir = max((v.get("icir", 0) for v in icir_data.values()), default=0)
    st.metric("Best ICIR", f"{best_icir:.3f}", delta="Excellent" if best_icir > 0.5 else "Moderate")
with col4:
    if best_bt:
        ret = best_bt.get("annualized_return", 0)
        bm_ret = benchmark.get("annualized_return", 0)
        st.metric("D+20 Return", f"{ret:+.2%}", delta=f"{ret - bm_ret:+.2%} vs benchmark")
    else:
        st.metric("D+20 Return", "N/A")
with col5:
    if best_bt:
        sr = best_bt.get("sharpe_ratio", 0)
        bm_sr = benchmark.get("sharpe_ratio", 0)
        st.metric("Sharpe Ratio", f"{sr:.2f}", delta=f"{sr - bm_sr:+.2f} vs benchmark")
    else:
        st.metric("Sharpe Ratio", "N/A")

st.divider()

# ═══════════════════════════════════════════════
#  OVERVIEW / 使用者導覽
# ═══════════════════════════════════════════════

tab_guide, tab_model, tab_backtest, tab_findings = st.tabs(
    ["🏠 系統導覽", "📊 模型總覽", "💰 回測摘要", "🔬 核心發現"]
)

# ---- Tab: 系統導覽 ----
with tab_guide:
    st.markdown("## 歡迎使用本系統")

    st.markdown("""
<div class="highlight-box">
<strong>本儀表板是什麼？</strong><br>
這是一套以機器學習驅動的<strong>台灣上市櫃股票多因子選股分析系統</strong>。
系統從 FinMind API 擷取 1,932 家公司的歷史資料，透過五支柱特徵工程、Purged Walk-Forward 交叉驗證、
以及 LightGBM / XGBoost 雙引擎模型，自動產出選股信號並進行策略回測。
此儀表板以互動式圖表呈現所有分析結果，協助您快速評估模型品質與策略可行性。
</div>
""", unsafe_allow_html=True)

    st.markdown("")

    # ---- Navigation Guide ----
    st.markdown("### 🗺️ 頁面導覽")

    guide_cols = st.columns(2)

    with guide_cols[0]:
        st.markdown("""
<div class="overview-card">
<div class="guide-step">
    <div class="step-number">1</div>
    <div class="step-content">
        <h4>📊 Model Metrics — 模型指標分析</h4>
        <p>查看各模型在不同預測天期（D+1/D+5/D+20）的 AUC、Balanced Accuracy、Per-Class AUC，
        以及每個 Fold 的穩定性趨勢和特徵重要度排名。</p>
    </div>
</div>
<div class="guide-step">
    <div class="step-number">2</div>
    <div class="step-content">
        <h4>📈 ICIR Analysis — 信號穩定性</h4>
        <p>檢視 Information Coefficient Information Ratio，了解模型在不同頻率下的
        選股信號品質。ICIR &gt; 0.5 表示信號穩定，適合實戰部署。</p>
    </div>
</div>
<div class="guide-step">
    <div class="step-number">3</div>
    <div class="step-content">
        <h4>💰 Backtest — 策略回測</h4>
        <p>比較不同成本假設（優惠/標準/保守）下的年化報酬、Sharpe Ratio、最大回撤，
        並檢視換手率與交易成本的影響。</p>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

    with guide_cols[1]:
        st.markdown("""
<div class="overview-card">
<div class="guide-step">
    <div class="step-number">4</div>
    <div class="step-content">
        <h4>🔬 Feature Analysis — 特徵工程</h4>
        <p>探索三階段特徵篩選（MI → VIF → Cross-Fold 穩定性）的過程，
        查看五支柱分佈、跨天期特徵重要度差異，以及 SHAP 可解釋性分析。</p>
    </div>
</div>
<div class="guide-step">
    <div class="step-number">5</div>
    <div class="step-content">
        <h4>🗃️ Data Explorer — 資料探索</h4>
        <p>瀏覽 Feature Store 概況、Walk-Forward CV 時間切分結構、
        品質門控詳情、系統架構圖，以及原始 JSON 報告資料。</p>
    </div>
</div>
<div class="guide-step" style="border-bottom:none;">
    <div class="step-number" style="background:#00CC96;">💡</div>
    <div class="step-content">
        <h4>快速建議</h4>
        <p>先從 <b>模型總覽</b>（下方分頁）確認整體指標，接著到 <b>ICIR Analysis</b> 頁面
        驗證信號品質，最後在 <b>Backtest</b> 頁面評估實際可行的策略方案。</p>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

    # ---- Methodology Overview ----
    st.markdown("### 🔧 方法論概述")

    meth_cols = st.columns(3)

    with meth_cols[0]:
        st.markdown("""
<div class="overview-card" style="text-align:center;">
<h4>🏗️ 五支柱特徵工程</h4>
<p style="font-size:2rem; font-weight:700; color:#636EFA; margin:8px 0;">43 → 23</p>
<p style="font-size:0.85rem; color:#5a6577;">
Trend (10) · Fundamental (8)<br>
Valuation (2) · Event (2) · Risk (3)<br><br>
三階段篩選: MI → VIF → 穩定性<br>
Jaccard Score = 0.937
</p>
</div>
""", unsafe_allow_html=True)

    with meth_cols[1]:
        st.markdown("""
<div class="overview-card" style="text-align:center;">
<h4>🔄 Purged Walk-Forward CV</h4>
<p style="font-size:2rem; font-weight:700; color:#00CC96; margin:8px 0;">4 Folds</p>
<p style="font-size:0.85rem; color:#5a6577;">
Expanding Window 訓練<br>
20-day Embargo 防止洩漏<br><br>
LightGBM + XGBoost 雙引擎<br>
等權 Ensemble 組合
</p>
</div>
""", unsafe_allow_html=True)

    with meth_cols[2]:
        st.markdown("""
<div class="overview-card" style="text-align:center;">
<h4>📐 多維度評估</h4>
<p style="font-size:2rem; font-weight:700; color:#EF553B; margin:8px 0;">7 Gates</p>
<p style="font-size:0.85rem; color:#5a6577;">
AUC + Per-Class AUC + ICIR<br>
三階梯成本回測<br><br>
Bootstrap CI · CDaR · Alpha Decay<br>
Quintile Factor Analysis
</p>
</div>
""", unsafe_allow_html=True)

    # ---- Data pipeline graphic ----
    st.markdown("### ⚡ 資料處理流程")

    flow_fig = go.Figure()
    stages = ["FinMind API\n資料擷取", "Feature Store\n五支柱工程", "三階段\n特徵篩選",
              "Walk-Forward\n模型訓練", "多 Horizon\n策略回測", "互動式\n儀表板"]
    x_pos = list(range(len(stages)))
    colors = ["#636EFA", "#AB63FA", "#EF553B", "#FFA15A", "#00CC96", "#19D3F3"]

    for i, (stage, color) in enumerate(zip(stages, colors)):
        flow_fig.add_trace(go.Scatter(
            x=[i], y=[0.5], mode="markers+text",
            marker=dict(size=60, color=color, opacity=0.9,
                        line=dict(width=2, color="white")),
            text=[stage], textposition="bottom center",
            textfont=dict(size=11), showlegend=False,
            hoverinfo="skip",
        ))
        if i < len(stages) - 1:
            flow_fig.add_annotation(
                x=i + 0.65, y=0.5, ax=i + 0.35, ay=0.5,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=3, arrowsize=1.5,
                arrowcolor="#9ca3af", arrowwidth=2,
            )

    flow_fig.update_layout(
        height=200, template="plotly_white",
        xaxis=dict(visible=False, range=[-0.5, len(stages) - 0.5]),
        yaxis=dict(visible=False, range=[-0.3, 1.2]),
        margin=dict(l=20, r=20, t=10, b=60),
    )
    st.plotly_chart(flow_fig, use_container_width=True)

    # ---- Quick Start for Developers ----
    with st.expander("🛠️ 開發者快速入門", expanded=False):
        st.code("""
# 1. 安裝依賴
pip install -r requirements_app.txt

# 2. 執行 Phase 1: 資料擷取 → Feature Store
python run_phase1.py

# 3. 執行 Phase 2: 模型訓練 → 回測 → 報告
python run_phase2.py

# 4. 啟動儀表板
streamlit run dashboard/app.py

# 5. 執行測試（99 個單元測試）
python -m pytest tests/ -v
""", language="bash")

# ---- Tab: 模型總覽 ----
with tab_model:
    st.subheader("跨模型 × 跨 Horizon AUC 比較")

    comp_rows = []
    for key, val in comparison.items():
        comp_rows.append({
            "Model": key,
            "Horizon": f"D+{val['horizon']}",
            "Engine": val["engine"],
            "AUC": val["auc"],
            "BalAcc": val.get("balanced_accuracy", 0),
            "ICIR": val.get("icir", 0),
            "Rank IC": val.get("rank_ic", 0),
            "Gate": "✅" if val.get("pass_auc_gate") else "❌",
        })
    if comp_rows:
        df_comp = pd.DataFrame(comp_rows)
        st.dataframe(
            df_comp.style.background_gradient(subset=["AUC", "ICIR"], cmap="YlGn"),
            use_container_width=True,
            hide_index=True,
        )

    # AUC heatmap-style chart
    if comp_rows:
        fig_auc = go.Figure()
        for h, color in [(1, "#EF553B"), (5, "#FFA15A"), (20, "#00CC96")]:
            subset = [r for r in comp_rows if r["Horizon"] == f"D+{h}"]
            fig_auc.add_trace(go.Bar(
                name=f"D+{h}",
                x=[r["Engine"] for r in subset],
                y=[r["AUC"] for r in subset],
                marker_color=color,
                text=[f"{r['AUC']:.4f}" for r in subset],
                textposition="outside",
            ))
        fig_auc.update_layout(
            barmode="group", title="AUC by Engine × Horizon",
            yaxis_title="AUC", yaxis_range=[0.48, max(r["AUC"] for r in comp_rows) + 0.02],
            height=400, template="plotly_white",
        )
        fig_auc.add_hline(y=0.5, line_dash="dash", line_color="gray", annotation_text="Random Baseline")
        st.plotly_chart(fig_auc, use_container_width=True)

# ---- Tab: 回測摘要 ----
with tab_backtest:
    st.subheader("策略回測績效（Discount 成本情境）")
    bt_rows = []
    for h in [1, 5, 20]:
        bt_h = results.get(f"backtest_horizon_{h}", {})
        for eng, bt_res in bt_h.items():
            disc = bt_res.get("cost_scenarios", {}).get("discount", {})
            if disc:
                bt_rows.append({
                    "Strategy": f"{eng} D+{h}",
                    "Return": f"{disc.get('annualized_return', 0):+.2%}",
                    "Sharpe": f"{disc.get('sharpe_ratio', 0):.2f}",
                    "Sortino": f"{disc.get('sortino_ratio', 0):.2f}",
                    "MDD": f"{disc.get('max_drawdown', 0):.2%}",
                    "Win Rate": f"{disc.get('win_rate', 0):.1%}",
                    "Turnover": f"{bt_res.get('avg_turnover', 0):.1%}",
                })
    bt_rows.append({
        "Strategy": "Benchmark (等權大盤)",
        "Return": f"{benchmark.get('annualized_return', 0):+.2%}",
        "Sharpe": f"{benchmark.get('sharpe_ratio', 0):.2f}",
        "Sortino": f"{benchmark.get('sortino_ratio', 0):.2f}",
        "MDD": f"{benchmark.get('max_drawdown', 0):.2%}",
        "Win Rate": f"{benchmark.get('win_rate', 0):.1%}",
        "Turnover": "-",
    })
    if bt_rows:
        st.dataframe(pd.DataFrame(bt_rows), use_container_width=True, hide_index=True)

# ---- Tab: 核心發現 ----
with tab_findings:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🎯 核心發現")
        st.markdown("""
1. **D+20 ICIR 0.74–0.77** — 月度信號極為穩定，遠超量化研究 0.5 良好門檻
2. **FLAT 類別辨識最強** — Per-class AUC 達 0.65–0.69，模型擅長識別盤整期
3. **D+1 策略不可行** — 高換手率（64–68%）累積成本吞噬所有 alpha
4. **XGBoost D+20 最佳** — 最保守成本下仍有 +8.5% 年化報酬
""")
    with c2:
        st.markdown("### ⚙️ 系統規格")
        fs = results.get("feature_store", {})
        wf = results.get("walk_forward", {})
        fsel = results.get("feature_selection", {})
        st.markdown(f"""
- **資料規模**: {fs.get('rows', 0):,} rows × {fs.get('cols', 0)} cols
- **資料期間**: {fs.get('date_range', 'N/A')}
- **候選特徵**: {fsel.get('n_candidates', 0)} → 篩選後 {len(fsel.get('selected', []))}
- **CV Folds**: {wf.get('n_folds', 0)} (Purged Walk-Forward)
- **模型引擎**: LightGBM + XGBoost + Ensemble
- **品質門控**: {sum(1 for v in gates.values() if v)}/{len(gates)} PASS
""")

# ===== Chart Gallery =====
st.divider()
st.subheader("📸 關鍵圖表預覽")

fig_dir = Path(__file__).parent.parent / "outputs" / "figures"

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    cum_ret = fig_dir / "cumulative_returns_D20.png"
    if cum_ret.exists():
        st.image(str(cum_ret), caption="D+20 累積報酬 vs 基準", use_container_width=True)

    model_comp = fig_dir / "model_comparison.png"
    if model_comp.exists():
        st.image(str(model_comp), caption="模型比較總覽", use_container_width=True)

with chart_col2:
    ic_ts = fig_dir / "ic_timeseries_ensemble_D20.png"
    if ic_ts.exists():
        st.image(str(ic_ts), caption="D+20 IC 時間序列", use_container_width=True)

    dd = fig_dir / "drawdown_D20.png"
    if dd.exists():
        st.image(str(dd), caption="D+20 回撤走勢", use_container_width=True)

# ===== Footer =====
st.divider()
st.markdown("""
<div style="text-align:center; padding:10px 0; color:#9ca3af; font-size:0.85rem;">
    Built with Streamlit & Plotly &nbsp;|&nbsp; Data: FinMind API &nbsp;|&nbsp;
    Models: LightGBM + XGBoost &nbsp;|&nbsp; 大數據與商業分析專案
</div>
""", unsafe_allow_html=True)
