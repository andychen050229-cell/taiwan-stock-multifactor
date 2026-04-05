"""Model Metrics — 模型指標分析（量化分析工作台）"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import inject_custom_css, inject_advanced_sidebar, load_report

st.set_page_config(page_title="Model Metrics | 量化分析工作台", page_icon="📊", layout="wide")
inject_custom_css()

report, report_name = load_report()
results = report["results"]
inject_advanced_sidebar(report_name, report)

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

    # Visual AUC bar chart
    fig_auc = go.Figure()
    colors = {"LIGHTGBM": "#636EFA", "XGBOOST": "#EF553B", "ENSEMBLE": "#00CC96"}
    for r in rows:
        fig_auc.add_trace(go.Bar(
            x=[r["Engine"]], y=[r["AUC"]],
            marker_color=colors.get(r["Engine"], "#AB63FA"),
            text=[f"{r['AUC']:.4f}"], textposition="outside",
            showlegend=False,
        ))
    fig_auc.update_layout(
        title=f"D+{horizon} AUC-ROC",
        yaxis_title="AUC", yaxis_range=[0.48, max(r["AUC"] for r in rows) + 0.02],
        height=350, template="plotly_white",
    )
    fig_auc.add_hline(y=0.5, line_dash="dash", line_color="gray", annotation_text="Random Baseline")
    st.plotly_chart(fig_auc, use_container_width=True)

# ===== Per-Class AUC =====
st.divider()
st.subheader(f"D+{horizon} — Per-Class AUC 分析")
st.markdown("""
<div class="insight-box">
<strong>為什麼看 Per-Class AUC？</strong>
三分類問題中，整體 AUC 可能掩蓋個別類別的弱點。
Per-Class AUC 分別衡量模型對 DOWN / FLAT / UP 的區辨能力。
</div>
""", unsafe_allow_html=True)

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

    with st.expander("📋 Per-Class AUC 逐 Fold 明細"):
        st.dataframe(df_pc.style.background_gradient(subset=["DOWN AUC", "FLAT AUC", "UP AUC"], cmap="RdYlGn"),
                     use_container_width=True, hide_index=True)

# ===== Fold Stability =====
st.divider()
st.subheader(f"D+{horizon} — Fold 穩定性趨勢")

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

    f1, f2 = st.columns(2)
    with f1:
        fig2 = px.line(df_fold, x="Fold", y="AUC", color="Engine", markers=True,
                       title=f"D+{horizon} AUC across Folds", template="plotly_white",
                       color_discrete_map={"LIGHTGBM": "#636EFA", "XGBOOST": "#EF553B"})
        fig2.add_hline(y=0.52, line_dash="dash", line_color="red", annotation_text="Quality Gate (0.52)")
        fig2.update_layout(height=350)
        st.plotly_chart(fig2, use_container_width=True)

    with f2:
        fig3 = px.line(df_fold, x="Fold", y="LogLoss", color="Engine", markers=True,
                       title=f"D+{horizon} LogLoss across Folds", template="plotly_white",
                       color_discrete_map={"LIGHTGBM": "#636EFA", "XGBOOST": "#EF553B"})
        fig3.update_layout(height=350)
        st.plotly_chart(fig3, use_container_width=True)

    with st.expander("📋 Fold 明細"):
        st.dataframe(df_fold, use_container_width=True, hide_index=True)

# ===== Feature Importance =====
st.divider()
st.subheader(f"D+{horizon} — Top 特徵重要度")

available_engines = [e for e in model_data.keys() if isinstance(model_data.get(e), dict) and "avg_metrics" in model_data.get(e, {})]
if available_engines:
    engine_sel = st.radio("Engine", available_engines, horizontal=True)
    top_feats = model_data.get(engine_sel, {}).get("top_features", {})
    if top_feats:
        df_feat = pd.DataFrame(list(top_feats.items()), columns=["Feature", "Importance"])
        df_feat = df_feat.sort_values("Importance", ascending=True).tail(15)

        fig4 = px.bar(df_feat, x="Importance", y="Feature", orientation="h",
                      color="Importance", color_continuous_scale="Blues",
                      title=f"{engine_sel.upper()} D+{horizon} Top-15 Features",
                      template="plotly_white")
        fig4.update_layout(height=500, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig4, use_container_width=True)

# ===== Footer =====
st.markdown('<div class="page-footer">量化分析工作台 — Model Metrics | 台灣股市多因子預測系統</div>', unsafe_allow_html=True)
