"""Feature Analysis — 特徵工程分析"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import inject_custom_css, load_report

st.set_page_config(page_title="Feature Analysis", page_icon="🔬", layout="wide")
inject_custom_css()

report = load_report()
results = report["results"]

st.title("🔬 特徵工程分析")
st.caption("三階段特徵篩選流程、五支柱分佈、跨天期重要度比較與 SHAP 可解釋性")

# ===== Feature Selection Pipeline =====
st.subheader("三階段特徵篩選")

fsel = results.get("feature_selection", {})
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("候選特徵", fsel.get("n_candidates", 0))
with col2:
    st.metric("MI 篩選後", fsel.get("after_mi", 0), delta=f"-{fsel.get('n_candidates', 0) - fsel.get('after_mi', 0)}")
with col3:
    st.metric("VIF 篩選後", fsel.get("after_vif", 0), delta=f"-{fsel.get('after_mi', 0) - fsel.get('after_vif', 0)}")
with col4:
    stability = results.get("feature_stability", {})
    st.metric("穩定性 (Jaccard)", f"{stability.get('stability_score', 0):.3f}")

# Funnel chart
fig_funnel = go.Figure(go.Funnel(
    y=["候選特徵 (5 支柱)", "MI 篩選", "VIF 去共線性", "最終選擇"],
    x=[fsel.get("n_candidates", 43), fsel.get("after_mi", 26), fsel.get("after_vif", 23), len(fsel.get("selected", []))],
    textposition="inside", textinfo="value+percent initial",
    marker=dict(color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"])
))
fig_funnel.update_layout(title="特徵篩選漏斗", height=350, template="plotly_white")
st.plotly_chart(fig_funnel, use_container_width=True)

# ===== Selected Features =====
st.subheader("最終選擇的特徵")

selected = fsel.get("selected", [])
if selected:
    categories = {"Trend": [], "Fundamental": [], "Valuation": [], "Event": [], "Risk": []}
    for f in selected:
        if f.startswith("trend_"):
            categories["Trend"].append(f)
        elif f.startswith("fund_"):
            categories["Fundamental"].append(f)
        elif f.startswith("val_"):
            categories["Valuation"].append(f)
        elif f.startswith("event_"):
            categories["Event"].append(f)
        elif f.startswith("risk_"):
            categories["Risk"].append(f)

    cat_counts = {k: len(v) for k, v in categories.items() if v}
    fig_pie = px.pie(names=list(cat_counts.keys()), values=list(cat_counts.values()),
                     title="特徵五支柱分佈", color_discrete_sequence=px.colors.qualitative.Set2,
                     hole=0.4)
    fig_pie.update_layout(height=350)

    col_pie, col_list = st.columns([1, 2])
    with col_pie:
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_list:
        for cat, feats in categories.items():
            if feats:
                st.markdown(f"**{cat}** ({len(feats)}): `{'`, `'.join(feats)}`")

# ===== Cross-Horizon Feature Importance =====
st.divider()
st.subheader("跨 Horizon 特徵重要度比較")

all_imp = {}
for h in [1, 5, 20]:
    model_data = results.get(f"model_horizon_{h}", {})
    for eng in ["lightgbm", "xgboost"]:
        res = model_data.get(eng, {})
        top_feats = res.get("top_features", {})
        if top_feats:
            all_imp[f"{eng}_D{h}"] = top_feats

if all_imp:
    engine_choice = st.radio("選擇引擎", ["lightgbm", "xgboost"], horizontal=True)

    imp_rows = []
    for h in [1, 5, 20]:
        key = f"{engine_choice}_D{h}"
        feats = all_imp.get(key, {})
        for fname, imp in feats.items():
            imp_rows.append({"Feature": fname, "Horizon": f"D+{h}", "Importance": imp})

    if imp_rows:
        df_imp = pd.DataFrame(imp_rows)
        top_per_h = df_imp.groupby("Horizon").apply(
            lambda x: x.nlargest(10, "Importance"), include_groups=False
        ).reset_index(drop=True)

        fig_imp = px.bar(top_per_h, x="Importance", y="Feature", color="Horizon",
                         orientation="h", barmode="group",
                         color_discrete_map={"D+1": "#EF553B", "D+5": "#FFA15A", "D+20": "#00CC96"},
                         title=f"{engine_choice.upper()} — Top-10 Features per Horizon",
                         template="plotly_white")
        fig_imp.update_layout(height=600, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_imp, use_container_width=True)

# ===== Stability =====
st.divider()
st.subheader("跨 Fold 穩定性")

stability = results.get("feature_stability", {})
if stability:
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.metric("Stability Score (Jaccard)", f"{stability.get('stability_score', 0):.4f}")
        jaccards = stability.get("pairwise_jaccards", [])
        if jaccards:
            st.markdown(f"Pairwise Jaccard: {', '.join(f'{j:.3f}' for j in jaccards)}")
    with col_s2:
        consistent = stability.get("consistent_top_features", [])
        st.metric("一致入選特徵數", f"{len(consistent)} / {len(selected)}")
        if consistent:
            st.markdown(f"**一致特徵**: {', '.join(consistent[:10])}{'...' if len(consistent) > 10 else ''}")

# ===== SHAP =====
st.divider()
st.subheader("SHAP 可解釋性分析")

fig_dir = Path(__file__).parent.parent.parent / "outputs" / "figures"
shap_charts = sorted(fig_dir.glob("shap_summary_*.png"))

if shap_charts:
    horizon_sel = st.selectbox("SHAP Horizon", [1, 5, 20], index=2, format_func=lambda x: f"D+{x}", key="shap_h")
    relevant = [c for c in shap_charts if f"D{horizon_sel}" in c.name]
    if relevant:
        cols = st.columns(min(len(relevant), 2))
        for i, chart in enumerate(relevant):
            with cols[i % 2]:
                st.image(str(chart), caption=chart.stem.replace("shap_summary_", "SHAP: "),
                         use_container_width=True)
else:
    st.info("SHAP 圖表尚未生成。")

# ===== Quintile =====
quintile_data = results.get("quintile_analysis", {})
if quintile_data:
    st.divider()
    st.subheader("Quintile 因子分組分析")

    for key, val in quintile_data.items():
        st.markdown(f"**{key}**")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Long-Short Spread", f"{val.get('long_short_spread', 0):+.2%}")
        with c2:
            st.metric("Monotonicity", f"{val.get('monotonicity', 0):.3f}")

        qr = val.get("quintile_returns", {})
        if qr:
            fig_q = go.Figure(go.Bar(
                x=list(qr.keys()), y=list(qr.values()),
                marker_color=["#EF553B", "#FFA15A", "#636EFA", "#AB63FA", "#00CC96"],
                text=[f"{v:+.1%}" for v in qr.values()], textposition="outside"
            ))
            fig_q.update_layout(
                title=f"{key} Quintile Returns",
                xaxis_title="Quintile (1=Lowest, 5=Highest)",
                yaxis_title="Annualized Return", yaxis_tickformat=".1%",
                height=350, template="plotly_white"
            )
            st.plotly_chart(fig_q, use_container_width=True)
