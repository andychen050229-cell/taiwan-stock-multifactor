"""Data Explorer — 資料探索"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import inject_custom_css, load_report

st.set_page_config(page_title="Data Explorer", page_icon="🗃️", layout="wide")
inject_custom_css()

report = load_report()
results = report["results"]

st.title("🗃️ 資料探索")
st.caption("Feature Store 概況、CV 結構、品質門控、系統架構與原始資料")

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

st.info(f"📅 資料期間: {fs_info.get('date_range', 'N/A')}")

# ===== Walk-Forward CV =====
st.divider()
st.subheader("Walk-Forward CV 結構")

wf = results.get("walk_forward", {})
folds = wf.get("folds", [])

if folds:
    fig = go.Figure()
    for fold in folds:
        fid = fold["fold_id"]
        fig.add_trace(go.Bar(
            y=[f"Fold {fid}"], x=[1], base=[0],
            orientation="h", name=f"Train" if fid == 0 else None,
            marker_color="#636EFA", showlegend=(fid == 0),
            text=[f"Train: {fold['train_period']}"],
            textposition="inside", width=0.6,
        ))
        fig.add_trace(go.Bar(
            y=[f"Fold {fid}"], x=[0.3], base=[1.05],
            orientation="h", name=f"Test" if fid == 0 else None,
            marker_color="#00CC96", showlegend=(fid == 0),
            text=[f"Test: {fold['test_period']}"],
            textposition="inside", width=0.6,
        ))

    fig.update_layout(
        title="Purged Walk-Forward CV Timeline",
        barmode="stack", height=300, template="plotly_white",
        xaxis_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

    fold_rows = []
    for fold in folds:
        fold_rows.append({
            "Fold": fold["fold_id"],
            "Train Period": fold["train_period"],
            "Test Period": fold["test_period"],
            "N Train": f"{fold['n_train']:,}",
            "N Test": f"{fold['n_test']:,}",
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

# ===== System Architecture =====
st.divider()
st.subheader("系統架構")

st.code("""
台灣股市多因子預測系統
├── run_phase1.py          # Phase 1: 資料擷取 → Feature Store
├── run_phase2.py          # Phase 2: 模型訓練 → 策略回測
├── dashboard/app.py       # Streamlit 儀表板
├── src/
│   ├── data/              # 資料載入/清洗/標籤
│   ├── features/          # 五支柱特徵工程 + 三階段篩選
│   ├── models/            # LGB/XGB + Optuna HPO + Walk-Forward
│   ├── backtest/          # Horizon-aware 回測 + 績效指標
│   ├── visualization/     # 9 種圖表生成
│   └── utils/             # Config/Logger/Helpers
├── tests/                 # 99 個單元測試
└── outputs/
    ├── feature_store.parquet
    ├── figures/ (32+ charts)
    ├── models/ (serialized)
    └── reports/ (JSON + DOCX)
""", language="text")

# ===== Raw JSON =====
st.divider()
with st.expander("📄 原始 JSON 報告"):
    st.json(report)
