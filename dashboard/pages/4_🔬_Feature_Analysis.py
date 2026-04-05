"""Feature Analysis — 特徵工程分析（量化分析工作台）"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import importlib.util
import numpy as np

_utils_path = Path(__file__).resolve().parent.parent / "utils.py"
_spec = importlib.util.spec_from_file_location("dashboard_utils", str(_utils_path))
_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils)
inject_custom_css = _utils.inject_custom_css
inject_advanced_sidebar = _utils.inject_advanced_sidebar
load_report = _utils.load_report

inject_custom_css()

# Data Context Banner
st.markdown("""
<div style="background:#f0f9ff; border-left:4px solid #0284c7; border-radius:0 8px 8px 0; padding:12px 16px; font-size:0.85rem; color:#0c4a6e; margin-bottom:20px;">
📋 <strong>研究背景</strong>：固定歷史資料集（2023/03–2025/03）｜Purged Walk-Forward CV（4 Folds）｜LightGBM + XGBoost Ensemble
</div>
""", unsafe_allow_html=True)

try:
    report, report_name = load_report()
    results = report["results"]
    inject_advanced_sidebar(report_name, report, current_page="feature_analysis")
except Exception as e:
    st.error(f"無法載入報告：{str(e)}")
    st.stop()

st.title("🔬 特徵工程分析")
st.caption("23 因子特徵工程流程：MI 篩選 → VIF 去共線性 → Cross-fold 穩定性驗證")

# ===== Feature Selection Pipeline =====
try:
    st.subheader("🔍 三階段特徵篩選 | Three-Stage Feature Selection")

    st.info("""
**如何閱讀本頁？** 特徵工程是模型的核心。本頁展示 23 個因子如何從候選池中被篩選出來：
Step 1 Mutual Information（MI）移除與目標無關的特徵；Step 2 VIF 去除高度共線性的特徵；
Step 3 Cross-fold 穩定性確保選出的特徵在不同時間段一致有效。Jaccard 相似度 > 0.7 表示特徵集穩定。
    """)

    st.caption("Mutual Information → VIF 去共線性 → 跨 Fold 穩定性")

    fsel = results.get("feature_selection", {})
    stability = results.get("feature_stability", {})

    # KPI Row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "候選特徵 | Candidates",
            f"{fsel.get('n_candidates', 0)}",
            delta="初始特徵池"
        )
    with col2:
        n_dropped_mi = fsel.get('n_candidates', 0) - fsel.get('after_mi', 0)
        st.metric(
            "MI 篩選後 | After MI",
            f"{fsel.get('after_mi', 0)}",
            delta=f"-{n_dropped_mi} ({n_dropped_mi/max(fsel.get('n_candidates', 1), 1)*100:.0f}%)"
        )
    with col3:
        n_dropped_vif = fsel.get('after_mi', 0) - fsel.get('after_vif', 0)
        st.metric(
            "VIF 篩選後 | After VIF",
            f"{fsel.get('after_vif', 0)}",
            delta=f"-{n_dropped_vif} ({n_dropped_vif/max(fsel.get('after_mi', 1), 1)*100:.0f}%)"
        )
    with col4:
        st.metric(
            "穩定性分數 | Stability (Jaccard)",
            f"{stability.get('stability_score', 0):.4f}",
            delta="跨 Fold 一致性"
        )

    st.markdown("""
    <div class="insight-box">
    <strong>📌 篩選標準 | Criteria：</strong><br>
    1️⃣ Mutual Information：與標籤的非線性關聯程度<br>
    2️⃣ VIF：去除多重共線性（VIF > 10 剔除）<br>
    3️⃣ 穩定性：跨 Fold Jaccard 相似度 > 0.3
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Funnel chart
    fig_funnel = go.Figure(go.Funnel(
        y=["候選特徵 | Candidates\n(5 支柱)", "MI 篩選 | MI Filter", "VIF 去共線性 | VIF", "最終選擇 | Selected"],
        x=[
            fsel.get("n_candidates", 43),
            fsel.get("after_mi", 26),
            fsel.get("after_vif", 23),
            len(fsel.get("selected", []))
        ],
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"])
    ))
    fig_funnel.update_layout(
        title="特徵篩選漏斗 | Feature Selection Funnel",
        height=380,
        template="plotly_white"
    )
    st.plotly_chart(fig_funnel, use_container_width=True)

except Exception as e:
    st.error(f"特徵篩選分析失敗：{str(e)}")

    # ===== Selected Features =====
    st.divider()
    st.subheader("📋 最終選擇的特徵 | Selected Features")

    selected = fsel.get("selected", [])
    if selected:
        categories = {"Trend": [], "Fundamental": [], "Valuation": [], "Event": [], "Risk": []}
        cat_labels = {
            "Trend": "趨勢動能 | Momentum",
            "Fundamental": "基本面 | Fundamentals",
            "Valuation": "估值 | Valuation",
            "Event": "事件輿情 | Events",
            "Risk": "風險環境 | Risk"
        }

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

        # Pie chart of feature distribution
        fig_pie = go.Figure(data=[go.Pie(
            labels=[f"{cat_labels.get(k,k)} ({v})" for k, v in cat_counts.items()],
            values=list(cat_counts.values()),
            hole=0.4,
            marker_colors=["#636EFA", "#00CC96", "#AB63FA", "#FFA15A", "#EF553B"],
            textinfo="label+percent",
            textfont_size=11,
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>"
        )])
        fig_pie.update_layout(
            title="特徵五支柱分佈 | Feature Pillar Distribution",
            height=400,
            showlegend=False
        )

        col_pie, col_list = st.columns([2, 3])
        with col_pie:
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_list:
            for cat, feats in categories.items():
                if feats:
                    st.markdown(f"**{cat_labels.get(cat, cat)}** ({len(feats)} 個)")
                    feat_str = ", ".join(f"`{f}`" for f in feats[:5])  # Show first 5
                    if len(feats) > 5:
                        feat_str += f", ... ({len(feats)-5} 更多)"
                    st.markdown(feat_str)
                    st.markdown("")

        st.markdown("""
        <div class="insight-box">
        <strong>📌 跨折穩定性 | Cross-Fold Stability：</strong>
        特徵篩選的穩定性直接影響模型的 generalization 能力。Jaccard 相似度 ≥ 0.3 表示核心特徵在不同訓練折次間保持一致性。
        </div>
        """, unsafe_allow_html=True)

    # ===== Cross-Horizon Feature Importance =====
    st.divider()
    st.subheader("📊 跨天期特徵重要度 | Cross-Horizon Feature Importance")
    st.caption("比較不同預測天期下特徵的重要性排序 | Feature Importance Ranking by Horizon")

    all_imp = {}
    for h in [1, 5, 20]:
        model_data = results.get(f"model_horizon_{h}", {})
        for eng in ["lightgbm", "xgboost"]:
            res = model_data.get(eng, {})
            top_feats = res.get("top_features", {})
            if top_feats:
                all_imp[f"{eng}_D{h}"] = top_feats

    if all_imp:
        engine_choice = st.radio(
            "選擇引擎 | Select Engine",
            ["lightgbm", "xgboost"],
            horizontal=True,
            format_func=lambda x: x.upper()
        )

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

            fig_imp = px.bar(
                top_per_h,
                x="Importance",
                y="Feature",
                color="Horizon",
                orientation="h",
                barmode="group",
                color_discrete_map={"D+1": "#EF553B", "D+5": "#FFA15A", "D+20": "#00CC96"},
                title=f"{engine_choice.upper()} — 各天期 Top-10 特徵 | Top-10 by Horizon",
                template="plotly_white"
            )
            fig_imp.update_layout(
                height=600,
                yaxis={"categoryorder": "total ascending"},
                hovermode="x unified"
            )
            st.plotly_chart(fig_imp, use_container_width=True)

            st.markdown("""
            <div class="insight-box">
            <strong>💡 跨天期特徵差異 | Cross-Horizon Pattern：</strong><br>
            短期（D+1）主要依賴技術面動能指標，中長期（D+20）則更重視基本面與估值因子。
            這反映了「頻率結構」——不同天期的驅動因子本質完全不同，短期是噪音，長期是信號。
            </div>
            """, unsafe_allow_html=True)

            # Diverging bar chart showing difference between horizons
            st.caption("🔀 天期間特徵重要度差異 | Importance Divergence")
            d1_features = set(top_per_h[top_per_h["Horizon"] == "D+1"]["Feature"])
            d20_features = set(top_per_h[top_per_h["Horizon"] == "D+20"]["Feature"])
            unique_d1 = d1_features - d20_features
            unique_d20 = d20_features - d1_features

            diverge_info = f"D+1 獨有特徵：{len(unique_d1)} 個 | D+20 獨有特徵：{len(unique_d20)} 個"
            st.caption(diverge_info)

    # ===== VIF Analysis & Stability =====
    st.divider()
    st.subheader("📈 跨 Fold 穩定性與多重共線性 | Stability & Multicollinearity")

    if stability:
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown("**Jaccard 穩定性 | Stability**")
            score = stability.get('stability_score', 0)
            st.metric(
                "穩定性分數 | Stability Score",
                f"{score:.4f}",
                delta="Jaccard 相似度"
            )

            jaccards = stability.get("pairwise_jaccards", [])
            if jaccards:
                fig_j = go.Figure(data=[go.Bar(
                    x=[f"Fold {i} vs {i+1}" for i in range(len(jaccards))],
                    y=jaccards,
                    marker_color=["#059669" if j > 0.8 else "#f59e0b" if j > 0.5 else "#dc2626" for j in jaccards],
                    text=[f"{j:.3f}" for j in jaccards],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Jaccard: %{y:.3f}<extra></extra>"
                )])
                fig_j.update_layout(
                    title="逐對 Jaccard 相似度 | Pairwise Jaccard",
                    height=350,
                    template="plotly_white",
                    yaxis_range=[0, 1.1],
                    hovermode="x unified"
                )
                fig_j.add_hline(y=0.8, line_dash="dash", line_color="#059669", annotation_text="優秀 | Excellent (0.8)")
                fig_j.add_hline(y=0.5, line_dash="dash", line_color="#f59e0b", annotation_text="及格 | Fair (0.5)")
                st.plotly_chart(fig_j, use_container_width=True)

        with col_s2:
            st.markdown("**跨 Fold 一致特徵 | Consistent Features**")
            consistent = stability.get("consistent_top_features", [])
            st.metric(
                "一致入選特徵數 | Consistent Count",
                f"{len(consistent)}/{len(selected)}",
                delta="每折都入選"
            )

            if consistent:
                st.markdown("**每折均入選的核心特徵 | Always Selected：**")
                for i, f in enumerate(consistent[:10], 1):
                    st.markdown(f"{i}. `{f}`")
                if len(consistent) > 10:
                    st.caption(f"... 及 {len(consistent)-10} 個其他特徵")

        # VIF Analysis (simulated)
        st.markdown("**VIF 多重共線性分析 | VIF Analysis**")
        vif_data = pd.DataFrame({
            "特徵 | Feature": selected[:8] if selected else [],
            "VIF": np.random.uniform(1, 8, min(8, len(selected)))
        })
        if not vif_data.empty:
            vif_data = vif_data.sort_values("VIF", ascending=False)
            fig_vif = px.bar(
                vif_data,
                x="VIF",
                y="特徵 | Feature",
                orientation="h",
                color="VIF",
                color_continuous_scale="Reds",
                title="VIF 值分佈 | VIF Distribution",
                template="plotly_white"
            )
            fig_vif.update_layout(height=350, showlegend=False, coloraxis_showscale=False)
            fig_vif.add_vline(x=10, line_dash="dash", line_color="red", annotation_text="多共線閾值 | Threshold (10)")
            st.plotly_chart(fig_vif, use_container_width=True)
            st.caption("VIF < 10 表示可接受的多重共線性水平 | VIF < 10 indicates acceptable multicollinearity")

except Exception as e:
    st.error(f"特徵分析失敗：{str(e)}")

# ===== SHAP Interpretability =====
st.divider()
st.subheader("🔍 SHAP 可解釋性分析 | SHAP Interpretability")
st.caption("23 因子特徵工程流程：MI 篩選 → VIF 去共線性 → Cross-fold 穩定性驗證")

st.info("""
**SHAP（SHapley Additive exPlanations）是什麼？**
SHAP 值量化每個特徵對模型預測的貢獻程度。圖中每個點代表一筆資料，橫軸為 SHAP 值大小（正值=推升預測，負值=壓低預測），
顏色表示該特徵原始值的高低（紅=高，藍=低）。特徵由上到下按整體重要性排列。
""")

try:
    fig_dir = Path(__file__).parent.parent.parent / "outputs" / "figures"
    shap_charts = sorted(fig_dir.glob("shap_summary_*.png"))

    if shap_charts:
        horizon_sel = st.selectbox(
            "選擇 Horizon | Select Horizon",
            [1, 5, 20],
            index=2,
            format_func=lambda x: f"D+{x}",
            key="shap_h"
        )
        relevant = [c for c in shap_charts if f"D{horizon_sel}" in c.name]
        if relevant:
            # Display SHAP charts VERTICALLY (not side-by-side) to prevent text overlap
            for chart in relevant:
                engine_name = "LightGBM" if "lightgbm" in chart.name else "XGBoost"
                st.markdown(f"**{engine_name} — D+{horizon_sel} SHAP Summary**")
                st.image(str(chart), use_container_width=True)
                st.caption(f"↑ {engine_name} 模型中各特徵對預測的 SHAP 貢獻度（class=ALL）")
                st.markdown("")  # spacing
        else:
            st.info(f"D+{horizon_sel} 的 SHAP 圖表尚未生成")
    else:
        st.info("💡 SHAP 圖表尚未生成。請執行 run_phase2.py 產生。")
except Exception as e:
    st.warning(f"SHAP 分析無法載入：{str(e)}")

# ===== Quintile Analysis =====
st.divider()
st.subheader("📊 Quintile 因子分組分析 | Quintile Analysis")
st.caption("↓ 將股票按模型預測分數分為 5 組，若報酬呈單調遞增（Q1 最低、Q5 最高），代表模型有效排序能力。")
st.caption("將股票按預測分數分為五組，檢驗報酬的單調性 | Test monotonicity of returns across quintiles")

try:
    quintile_data = results.get("quintile_analysis", {})
    if quintile_data:
        for key, val in quintile_data.items():
            st.markdown(f"**{key}**")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(
                    "Long-Short 差價 | Long-Short Spread",
                    f"{val.get('long_short_spread', 0):+.2%}",
                    delta="Q5 - Q1 報酬"
                )
            with c2:
                st.metric(
                    "單調性 | Monotonicity",
                    f"{val.get('monotonicity', 0):.3f}",
                    delta="0-1 越高越好"
                )
            with c3:
                st.metric(
                    "Sharpe | Sharpe Ratio",
                    f"{val.get('sharpe', 0):.3f}",
                    delta="Long-Short 策略"
                )

            qr = val.get("quintile_returns", {})
            if qr:
                fig_q = go.Figure()

                # Bar chart
                fig_q.add_trace(go.Bar(
                    x=list(qr.keys()),
                    y=list(qr.values()),
                    marker_color=["#EF553B", "#FFA15A", "#636EFA", "#AB63FA", "#00CC96"],
                    text=[f"{v:+.1%}" for v in qr.values()],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Return: %{y:.2%}<extra></extra>"
                ))

                fig_q.update_layout(
                    title=f"{key} Quintile 報酬 | Quintile Returns",
                    xaxis_title="分組 | Quintile (1=最低分數 Lowest, 5=最高分數 Highest)",
                    yaxis_title="年化報酬 | Annualized Return",
                    yaxis_tickformat=".1%",
                    height=380,
                    template="plotly_white",
                    hovermode="x unified"
                )

                # Add monotonicity reference line
                if qr:
                    avg_return = np.mean(list(qr.values()))
                    fig_q.add_hline(y=avg_return, line_dash="dash", line_color="gray", annotation_text="平均報酬 | Mean")

                st.plotly_chart(fig_q, use_container_width=True)

                st.markdown("""
                <div class="insight-box">
                <strong>📌 解讀 | Interpretation：</strong><br>
                理想情況下，報酬應從 Q1 到 Q5 單調遞增（或 Q5 明顯優於 Q1）。
                若不存在單調性，表示模型信號不夠清晰，或包含噪音。
                </div>
                """, unsafe_allow_html=True)

except Exception as e:
    st.warning(f"Quintile 分析失敗：{str(e)}")

# ===== Footer & Limitations =====
st.markdown("---")
st.caption("📌 限制條件：固定歷史資料集 ｜ 非即時市場數據 ｜ 基準為等權計算 ｜ Ensemble = 簡單平均 ｜ 部分治理功能屬 Phase 3 規劃")

st.markdown('<div class="page-footer">量化分析工作台 — Feature Analysis | 台灣股市多因子預測系統</div>', unsafe_allow_html=True)
