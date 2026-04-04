"""Model Metrics — 模型指標分析"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import inject_custom_css, load_report

st.set_page_config(page_title="Model Metrics", page_icon="📊", layout="wide")
inject_custom_css()

report = load_report()
results = report["results"]

st.title("📊 模型指標分析")
st.caption("各模型在不同預測天期的 AUC、Per-Class AUC、Fold 穩定性與特徵重要度")

# Horizon selector
horizon = st.selectbox("選擇 Horizon", [1, 5, 20], index=2, format_func=lambda x: f"D+{x}")

# ===== AUC Comparison =====
st.subheader(f"D+{horizon} — AUC-ROC 比較")

model_data = results.get(f"model_horizon_{horizon}", {})

rows = []
for eng, res in model_data.items():
    if isinstance(res, dict) and "avg_metrics" in res:
        m = res["avg_metrics"]
        rows.append({
            "Engine": eng.upper(),
            "AUC": m.get("auc", 0),
            "LogLoss": m.get("log_loss", 0),
            "Accuracy": m.get("accuracy", 0),
            "Balanced Acc": m.get("balanced_accuracy", 0),
            "Baseline LL": m.get("baseline_logloss", 0),
            "LL Improvement": f"{(1 - m.get('log_loss', 1) / m.get('baseline_logloss', 1)) * 100:.1f}%" if m.get("baseline_logloss") else "N/A",
        })

# Add ensemble from comparison
comp = results.get("comparison", {})
ens_key = f"ensemble_D{horizon}"
if ens_key in comp:
    ens = comp[ens_key]
    rows.append({
        "Engine": "ENSEMBLE",
        "AUC": ens.get("auc", 0),
        "LogLoss": 0,
        "Accuracy": ens.get("accuracy", 0),
        "Balanced Acc": ens.get("balanced_accuracy", 0),
        "Baseline LL": 0,
        "LL Improvement": "N/A",
    })

if rows:
    df = pd.DataFrame(rows)
    st.dataframe(df.style.background_gradient(subset=["AUC"], cmap="YlGn"), use_container_width=True, hide_index=True)

# ===== Per-Class AUC =====
st.subheader(f"D+{horizon} — Per-Class AUC 分析")

per_class_rows = []
for eng, res in model_data.items():
    if isinstance(res, dict) and "fold_metrics" in res:
        for fm in res.get("fold_metrics", []):
            pc = fm.get("per_class_auc", {})
            if pc:
                per_class_rows.append({
                    "Engine": eng.upper(),
                    "Fold": fm.get("fold_id", 0),
                    "DOWN AUC": pc.get("DOWN", 0),
                    "FLAT AUC": pc.get("FLAT", 0),
                    "UP AUC": pc.get("UP", 0),
                })

if per_class_rows:
    df_pc = pd.DataFrame(per_class_rows)

    fig = go.Figure()
    for cls, color in [("DOWN AUC", "#EF553B"), ("FLAT AUC", "#636EFA"), ("UP AUC", "#00CC96")]:
        avg_by_eng = df_pc.groupby("Engine")[cls].mean()
        fig.add_trace(go.Bar(name=cls.replace(" AUC", ""), x=avg_by_eng.index, y=avg_by_eng.values,
                             marker_color=color, text=avg_by_eng.values.round(4), textposition="outside"))
    fig.update_layout(barmode="group", title=f"D+{horizon} Per-Class AUC (Fold Average)",
                      yaxis_title="AUC", yaxis_range=[0.45, 0.75],
                      height=400, template="plotly_white")
    fig.add_hline(y=0.5, line_dash="dash", line_color="gray", annotation_text="Random")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Per-Class AUC 明細"):
        st.dataframe(df_pc.style.background_gradient(subset=["DOWN AUC", "FLAT AUC", "UP AUC"], cmap="RdYlGn"),
                     use_container_width=True, hide_index=True)

# ===== Fold Stability =====
st.subheader(f"D+{horizon} — Fold 穩定性")

fold_rows = []
for eng, res in model_data.items():
    if isinstance(res, dict) and "fold_metrics" in res:
        for fm in res.get("fold_metrics", []):
            fold_rows.append({
                "Engine": eng.upper(),
                "Fold": fm.get("fold_id", 0),
                "AUC": fm.get("auc", 0),
                "LogLoss": fm.get("log_loss", 0),
                "N_train": fm.get("n_train", 0),
                "N_test": fm.get("n_test", 0),
            })

if fold_rows:
    df_fold = pd.DataFrame(fold_rows)
    fig2 = px.line(df_fold, x="Fold", y="AUC", color="Engine", markers=True,
                   title=f"D+{horizon} AUC across Folds", template="plotly_white")
    fig2.add_hline(y=0.52, line_dash="dash", line_color="red", annotation_text="Quality Gate (0.52)")
    fig2.update_layout(height=350)
    st.plotly_chart(fig2, use_container_width=True)

# ===== Feature Importance =====
st.subheader(f"D+{horizon} — Top 特徵重要度")

available_engines = [e for e in model_data.keys() if isinstance(model_data.get(e), dict) and "avg_metrics" in model_data.get(e, {})]
if available_engines:
    engine_sel = st.radio("Engine", available_engines, horizontal=True)
    top_feats = model_data.get(engine_sel, {}).get("top_features", {})
    if top_feats:
        df_feat = pd.DataFrame(list(top_feats.items()), columns=["Feature", "Importance"])
        df_feat = df_feat.sort_values("Importance", ascending=True).tail(15)

        fig3 = px.bar(df_feat, x="Importance", y="Feature", orientation="h",
                      color="Importance", color_continuous_scale="Blues",
                      title=f"{engine_sel.upper()} D+{horizon} Top-15 Features",
                      template="plotly_white")
        fig3.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)
