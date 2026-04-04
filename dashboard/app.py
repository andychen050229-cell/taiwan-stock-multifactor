"""
台灣股市多因子預測系統 — Streamlit Dashboard
Taiwan Stock Multi-Factor Prediction System

啟動方式：
  streamlit run dashboard/app.py
"""

import streamlit as st
import json
from pathlib import Path

# ===== Page Config =====
st.set_page_config(
    page_title="台灣股市多因子預測系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Load Data =====
@st.cache_data
def load_report():
    """Load the latest Phase 2 report JSON."""
    report_dir = Path(__file__).parent.parent / "outputs" / "reports"
    # Find latest phase2 report
    reports = sorted(report_dir.glob("phase2_report_*.json"), reverse=True)
    if not reports:
        st.error("No Phase 2 report found. Please run `python run_phase2.py` first.")
        st.stop()
    with open(reports[0], "r", encoding="utf-8") as f:
        return json.load(f), reports[0].name

report, report_name = load_report()
results = report.get("results", {})

# ===== Sidebar =====
st.sidebar.image("https://img.icons8.com/fluency/96/stock-share.png", width=64)
st.sidebar.title("多因子預測系統")
st.sidebar.caption(f"Report: {report_name}")
st.sidebar.caption(f"Status: {'✅ ALL PASS' if report.get('overall_status') == 'PASS' else '⚠️ REVIEW'}")
st.sidebar.divider()

# Quality gates in sidebar
gates = report.get("quality_gates", {})
with st.sidebar.expander("🔒 Quality Gates", expanded=False):
    for gate, passed in gates.items():
        icon = "✅" if passed else "❌"
        st.write(f"{icon} {gate.replace('_', ' ').title()}")

st.sidebar.divider()
st.sidebar.markdown(
    "**Tech Stack**: LightGBM + XGBoost + Ensemble\n\n"
    "**CV**: Purged Walk-Forward (4 Folds)\n\n"
    "**Data**: 1,932 companies | 2023/3–2025/3"
)

# ===== Main Content =====
st.title("📈 台灣股市多因子預測系統")
st.caption("Taiwan Stock Multi-Factor Prediction System — Dashboard v1.0")

# ===== KPI Cards =====
best_model = results.get("best_model", "N/A")
benchmark = results.get("benchmark", {})
comparison = results.get("comparison", {})
icir_data = results.get("icir", {})

# Find best D+20 backtest
bt_d20 = results.get("backtest_horizon_20", {})
best_bt = None
best_bt_name = ""
for eng in ["xgboost", "ensemble", "lightgbm"]:
    if eng in bt_d20:
        best_bt = bt_d20[eng].get("cost_scenarios", {}).get("discount", {})
        best_bt_name = f"{eng} D+20"
        break

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Best Model",
        best_model.replace("_", " ").upper() if best_model else "N/A",
        help="Highest AUC model across all horizons"
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
        st.metric(
            f"D+20 Return",
            f"{ret:+.2%}",
            delta=f"{ret - bm_ret:+.2%} vs benchmark"
        )

with col5:
    if best_bt:
        st.metric(
            "Sharpe Ratio",
            f"{best_bt.get('sharpe_ratio', 0):.2f}",
            delta=f"{best_bt.get('sharpe_ratio', 0) - benchmark.get('sharpe_ratio', 0):.2f} vs benchmark"
        )

st.divider()

# ===== Overview Tabs =====
tab1, tab2, tab3 = st.tabs(["📊 模型總覽", "💰 回測摘要", "🔬 核心發現"])

with tab1:
    st.subheader("跨模型 × 跨 Horizon AUC 比較")
    import pandas as pd

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

with tab2:
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
    # Add benchmark
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

with tab3:
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
st.subheader("📸 關鍵圖表")

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

st.divider()
st.caption("Built with Streamlit | Data: FinMind API | Models: LightGBM + XGBoost")
