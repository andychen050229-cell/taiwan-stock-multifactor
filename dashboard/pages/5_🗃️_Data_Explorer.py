"""Data Explorer — 資料探索（量化分析工作台）"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import inject_custom_css, inject_advanced_sidebar, load_report

st.set_page_config(page_title="Data Explorer | 量化分析工作台", page_icon="🗃️", layout="wide")
inject_custom_css()

report, report_name = load_report()
results = report["results"]
inject_advanced_sidebar(report_name, report)

st.title("🗃️ 資料探索")
st.caption("Feature Store 概況、Walk-Forward CV 結構、品質門控、系統架構與原始資料")

# ===== Feature Store Summary =====
st.subheader("Feature Store 概覽")

fs_info = results.get("feature_store", {})
val_info = results.get("data_validation", {})

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("總筆數", f"{fs_info.get('rows', 0):,}")
with col2:
    st.metric("欄位數", fs_info.get("cols", 0))
with col3:
    st.metric("缺失比例", f"{val_info.get('nan_pct', 0):.2%}")
with col4:
    st.metric("Inf 值", val_info.get("inf_count", 0))

st.markdown(f"""
<div class="insight-box">
📅 <strong>資料期間：</strong> {fs_info.get('date_range', 'N/A')}<br>
🏢 <strong>涵蓋公司：</strong> 1,932 家上市櫃公司<br>
📊 <strong>資料來源：</strong> FinMind API (OHLCV + 損益表 + 新聞)
</div>
""", unsafe_allow_html=True)

# ===== Walk-Forward CV =====
st.divider()
st.subheader("Walk-Forward CV 結構")

st.markdown("""
<div class="insight-box">
<strong>Purged Walk-Forward CV：</strong>
使用 Expanding Window 訓練——每一折的訓練集包含所有歷史資料（而非固定視窗），
加上 20 日 Embargo 期隔離訓練與測試集，防止因交易日重疊造成的前瞻偏差。
</div>
""", unsafe_allow_html=True)

wf = results.get("walk_forward", {})
folds = wf.get("folds", [])

if folds:
    # Visual timeline
    fig = go.Figure()
    colors_train = ["#4361ee", "#3a86ff", "#4895ef", "#56cfe1"]
    colors_test = ["#2d6a4f", "#40916c", "#52b788", "#74c69d"]

    for fold in folds:
        fid = fold["fold_id"]
        fig.add_trace(go.Bar(
            y=[f"Fold {fid}"], x=[1], base=[0],
            orientation="h", name=f"Train" if fid == 0 else None,
            marker_color=colors_train[fid % len(colors_train)], showlegend=(fid == 0),
            text=[f"Train: {fold['train_period']}"],
            textposition="inside", width=0.5,
            hovertemplate=f"Train samples: {fold['n_train']:,}<extra>Fold {fid} Train</extra>",
        ))
        fig.add_trace(go.Bar(
            y=[f"Fold {fid}"], x=[0.3], base=[1.05],
            orientation="h", name=f"Test" if fid == 0 else None,
            marker_color=colors_test[fid % len(colors_test)], showlegend=(fid == 0),
            text=[f"Test: {fold['test_period']}"],
            textposition="inside", width=0.5,
            hovertemplate=f"Test samples: {fold['n_test']:,}<extra>Fold {fid} Test</extra>",
        ))

    fig.update_layout(
        title="Purged Walk-Forward CV Timeline",
        barmode="stack", height=280, template="plotly_white",
        xaxis_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Fold details table
    fold_rows = []
    for fold in folds:
        fold_rows.append({
            "Fold": fold["fold_id"],
            "Train Period": fold["train_period"],
            "Test Period": fold["test_period"],
            "N Train": f"{fold['n_train']:,}",
            "N Test": f"{fold['n_test']:,}",
            "Test Ratio": f"{fold['n_test']/(fold['n_train']+fold['n_test'])*100:.1f}%",
        })
    st.dataframe(pd.DataFrame(fold_rows), use_container_width=True, hide_index=True)

    mc1, mc2 = st.columns(2)
    with mc1:
        st.metric("Total Train Samples", f"{wf.get('total_train_samples', 0):,}")
    with mc2:
        st.metric("Total Test Samples", f"{wf.get('total_test_samples', 0):,}")

# ===== Quality Gates =====
st.divider()
st.subheader("品質門控詳情")

gates = report.get("quality_gates", {})
if gates:
    descriptions = {
        "all_models_trained": "所有模型（LGB + XGB × 3 horizons）均成功訓練",
        "auc_gate_pass": "所有模型 AUC 超過 0.52 門檻",
        "sufficient_folds": "CV Fold 數量 ≥ 2",
        "no_data_leakage": "Feature Store 無 Inf 值（資料洩漏代理指標）",
        "oof_predictions_valid": "所有 OOF 預測非全 NaN",
        "feature_stability": "跨 Fold 特徵 Jaccard 穩定性 ≥ 0.3",
        "best_model_ic_positive": "最佳模型的 Rank IC > 0",
    }
    gate_rows = []
    for gate, passed in gates.items():
        is_pass = passed is True or passed == "True"
        gate_rows.append({
            "Gate": gate.replace("_", " ").title(),
            "Status": "✅ PASS" if is_pass else "❌ FAIL",
            "Description": descriptions.get(gate, ""),
        })
    st.dataframe(pd.DataFrame(gate_rows), use_container_width=True, hide_index=True)

    # Visual summary
    n_pass = sum(1 for g in gates.values() if g is True or g == "True")
    n_total = len(gates)
    fig_gate = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=n_pass,
        delta={"reference": n_total},
        title={"text": "Quality Gates Passed"},
        gauge={
            "axis": {"range": [0, n_total]},
            "bar": {"color": "#059669" if n_pass == n_total else "#f59e0b"},
            "steps": [
                {"range": [0, n_total * 0.5], "color": "#fef2f2"},
                {"range": [n_total * 0.5, n_total * 0.8], "color": "#fef3c7"},
                {"range": [n_total * 0.8, n_total], "color": "#ecfdf5"},
            ],
        },
        number={"suffix": f" / {n_total}"},
    ))
    fig_gate.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_gate, use_container_width=True)

# ===== System Architecture =====
st.divider()
st.subheader("系統架構")

st.code("""
台灣股市多因子預測系統
├── run_phase1.py          # Phase 1: 資料擷取 → Feature Store
├── run_phase2.py          # Phase 2: 模型訓練 → 策略回測
├── dashboard/
│   ├── app.py             # Landing Page（分流入口）
│   └── pages/
│       ├── 0_投資新手看板  # 新手友善推薦儀表板
│       ├── 1_Model_Metrics # AUC / Per-Class AUC / Fold 穩定性
│       ├── 2_ICIR_Analysis # 信號穩定性分析
│       ├── 3_Backtest      # 多情境策略回測
│       ├── 4_Feature_Anal  # 特徵篩選 / SHAP / Quintile
│       └── 5_Data_Explorer # 資料探索 / 品質門控
├── src/
│   ├── data/              # 資料載入 / 清洗 / 標籤 / 洩漏偵測
│   ├── features/          # 五支柱特徵工程 + 三階段篩選
│   ├── models/            # LGB / XGB + Optuna HPO + Walk-Forward
│   ├── backtest/          # Horizon-aware 回測 + 績效指標
│   ├── visualization/     # 9 種圖表生成
│   └── utils/             # Config / Logger / Helpers
├── tests/                 # 99 個單元測試
└── outputs/
    ├── feature_store.parquet
    ├── figures/ (32+ charts)
    └── reports/ (JSON + DOCX)
""", language="text")

# ===== Raw JSON =====
st.divider()
with st.expander("📄 原始 JSON 報告"):
    st.json(report)

# ===== Footer =====
st.markdown('<div class="page-footer">量化分析工作台 — Data Explorer | 台灣股市多因子預測系統</div>', unsafe_allow_html=True)
