"""Model Metrics — 模型指標分析（量化分析工作台）"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import importlib.util

_utils_path = Path(__file__).resolve().parent.parent / "utils.py"
_spec = importlib.util.spec_from_file_location("dashboard_utils", str(_utils_path))
_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils)
inject_custom_css = _utils.inject_custom_css
inject_advanced_sidebar = _utils.inject_advanced_sidebar
load_report = _utils.load_report

st.set_page_config(page_title="Model Metrics | 量化分析工作台", page_icon="📊", layout="wide")
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
    inject_advanced_sidebar(report_name, report, current_page="model_metrics")
except Exception as e:
    st.error(f"無法載入報告：{str(e)}")
    st.stop()

st.title("📊 模型指標分析")
st.caption("Model Metrics Analysis | 各模型在不同預測天期的 AUC、Per-Class AUC、Fold 穩定性與特徵重要度")

# Horizon selector
col_ctrl = st.columns([1, 4])
with col_ctrl[0]:
    horizon = st.selectbox("選擇 Horizon | Select Horizon", [1, 5, 20], index=2, format_func=lambda x: f"D+{x}")

# ===== Summary KPI Row =====
try:
    model_data = results.get(f"model_horizon_{horizon}", {})
    kpi_rows = []

    for eng, res in model_data.items():
        if isinstance(res, dict) and "avg_metrics" in res:
            m = res["avg_metrics"]
            kpi_rows.append({
                "engine": eng.upper(),
                "auc": m.get("auc", 0),
                "logloss": m.get("log_loss", 0),
                "baseline_ll": m.get("baseline_logloss", 1),
                "horizon": horizon,
            })

    # Add ensemble
    comp = results.get("comparison", {})
    ens_key = f"ensemble_D{horizon}"
    if ens_key in comp:
        ens = comp[ens_key]
        kpi_rows.append({
            "engine": "ENSEMBLE",
            "auc": ens.get("auc", 0),
            "logloss": 0,
            "baseline_ll": 1,
            "horizon": horizon,
        })

    if kpi_rows:
        best_auc_engine = max(kpi_rows, key=lambda x: x["auc"])
        best_ll_improvement = max(
            [r for r in kpi_rows if r["logloss"] > 0],
            key=lambda x: (1 - x["logloss"] / x["baseline_ll"]),
            default={}
        )

        st.markdown("### 🎯 關鍵績效指標 | Key Performance Indicators")

        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        with kpi_col1:
            st.metric(
                "最佳 AUC | Best AUC",
                f"{best_auc_engine['auc']:.4f}",
                delta=f"{best_auc_engine['engine']}"
            )
        with kpi_col2:
            st.metric(
                "最佳引擎 | Best Engine",
                best_auc_engine['engine'],
                delta="當前 Horizon"
            )
        with kpi_col3:
            if best_ll_improvement:
                ll_imp = (1 - best_ll_improvement["logloss"] / best_ll_improvement["baseline_ll"]) * 100
                st.metric(
                    "LogLoss 改進 | LL Improvement",
                    f"{ll_imp:.1f}%",
                    delta=f"相對基線 | vs Baseline"
                )
        with kpi_col4:
            st.metric(
                "當前預測天期 | Prediction Horizon",
                f"D+{horizon}",
                delta="前瞻預測天數"
            )

        st.divider()
except Exception as e:
    st.warning(f"KPI 計算發生錯誤：{str(e)}")

# ===== Model Comparison Radar Chart =====
try:
    st.subheader("📊 引擎對標分析 | Engine Comparison")
    st.caption("LightGBM vs XGBoost | 跨多維度性能指標的側面對比")

    radar_rows = []
    for eng, res in model_data.items():
        if isinstance(res, dict) and "avg_metrics" in res:
            m = res["avg_metrics"]
            # Normalize to 0-1 scale for radar
            radar_rows.append({
                "Engine": eng.upper(),
                "AUC": min(m.get("auc", 0) / 0.7, 1.0),  # normalize
                "Accuracy": m.get("accuracy", 0),
                "Balanced Acc": m.get("balanced_accuracy", 0),
                "LogLoss": max(0.5 - m.get("log_loss", 0.5), 0),  # inverse scale
            })

    if len(radar_rows) >= 2:
        categories = ["AUC", "Accuracy", "Balanced Acc", "LogLoss"]
        fig_radar = go.Figure()

        colors = {"LIGHTGBM": "#636EFA", "XGBOOST": "#EF553B"}
        for row in radar_rows:
            fig_radar.add_trace(go.Scatterpolar(
                r=[row[cat] for cat in categories],
                theta=categories,
                fill='toself',
                name=row['Engine'],
                marker_color=colors.get(row['Engine'], '#AB63FA'),
                line_color=colors.get(row['Engine'], '#AB63FA'),
            ))

        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=True,
            height=450,
            template="plotly_white",
        )
        st.plotly_chart(fig_radar, use_container_width=True)
except Exception as e:
    st.warning(f"Radar 圖表生成失敗：{str(e)}")

# ===== AUC Comparison =====
st.divider()
st.subheader(f"📈 AUC-ROC 比較 | AUC Comparison (D+{horizon})")

try:
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

    # Add ensemble
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
        st.dataframe(
            df.style.background_gradient(subset=["AUC"], cmap="RdYlGn"),
            use_container_width=True,
            hide_index=True
        )

        # Visual AUC bar chart
        fig_auc = go.Figure()
        colors = {"LIGHTGBM": "#636EFA", "XGBOOST": "#EF553B", "ENSEMBLE": "#00CC96"}

        for r in sorted(rows, key=lambda x: x["AUC"]):
            fig_auc.add_trace(go.Bar(
                x=[r["Engine"]],
                y=[r["AUC"]],
                marker_color=colors.get(r["Engine"], "#AB63FA"),
                text=[f"{r['AUC']:.4f}"],
                textposition="outside",
                showlegend=False,
                hovertemplate=f"<b>{r['Engine']}</b><br>AUC: {r['AUC']:.4f}<extra></extra>"
            ))

        fig_auc.update_layout(
            title=f"D+{horizon} AUC-ROC 得分 | Score Comparison",
            yaxis_title="AUC",
            yaxis_range=[0.48, max(r["AUC"] for r in rows) + 0.02],
            height=400,
            template="plotly_white",
            hovermode="x unified",
        )
        fig_auc.add_hline(y=0.5, line_dash="dash", line_color="gray", annotation_text="隨機基線 | Random Baseline")
        fig_auc.add_hline(y=0.52, line_dash="dash", line_color="red", annotation_text="品質門檻 | Quality Gate")
        st.plotly_chart(fig_auc, use_container_width=True)

        st.markdown("""
        <div class="insight-box">
        <strong>💡 洞察 | Insight：</strong>
        AUC > 0.52 表示模型優於隨機預測，超越品質門檻。ENSEMBLE 通常結合個別模型優勢，實現更穩定的預測。<br>
        <strong>✅ 應用建議：</strong> 在 <strong>月度頻率（D+20）</strong> 策略部署；D+1/D+5 信號品質不足，不推薦實盤使用。
        </div>
        """, unsafe_allow_html=True)
except Exception as e:
    st.error(f"AUC 比較失敗：{str(e)}")

# ===== Per-Class AUC =====
st.divider()
st.subheader(f"🎯 分類別 AUC 分析 | Per-Class AUC (D+{horizon})")
st.markdown("""
<div class="insight-box">
<strong>❓ 為什麼看 Per-Class AUC | Why Per-Class AUC？</strong><br>
三分類問題中，整體 AUC 可能掩蓋個別類別的弱點。Per-Class AUC 分別衡量模型對 DOWN / FLAT / UP 的區辨能力，
幫助識別特定類別的模型弱點。
</div>
""", unsafe_allow_html=True)

try:
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

        # Create grouped bar chart
        fig = go.Figure()
        for cls, color in [("DOWN AUC", "#EF553B"), ("FLAT AUC", "#636EFA"), ("UP AUC", "#00CC96")]:
            avg_by_eng = df_pc.groupby("Engine")[cls].mean()
            fig.add_trace(go.Bar(
                name=cls.replace(" AUC", ""),
                x=avg_by_eng.index,
                y=avg_by_eng.values,
                marker_color=color,
                text=avg_by_eng.values.round(4),
                textposition="outside"
            ))

        fig.update_layout(
            barmode="group",
            title=f"D+{horizon} 按類別平均 AUC | Per-Class AUC (Fold Average)",
            yaxis_title="AUC",
            yaxis_range=[0.45, 0.75],
            height=420,
            template="plotly_white",
            hovermode="x unified",
        )
        fig.add_hline(y=0.5, line_dash="dash", line_color="gray", annotation_text="隨機基線")
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 逐折明細 | Per-Fold Details"):
            st.dataframe(
                df_pc.style.background_gradient(subset=["DOWN AUC", "FLAT AUC", "UP AUC"], cmap="RdYlGn"),
                use_container_width=True,
                hide_index=True
            )

        # Heatmap option
        st.caption("📊 熱力圖視圖 | Heatmap View")
        heatmap_data = df_pc.pivot_table(
            index="Engine",
            columns="Fold",
            values="UP AUC",
            aggfunc="mean"
        )
        if not heatmap_data.empty:
            fig_heat = go.Figure(data=go.Heatmap(
                z=heatmap_data.values,
                x=[f"Fold {c}" for c in heatmap_data.columns],
                y=heatmap_data.index,
                colorscale="RdYlGn",
                zmid=0.52,
                hovertemplate="<b>%{y}</b><br>%{x}<br>AUC: %{z:.4f}<extra></extra>"
            ))
            fig_heat.update_layout(
                title=f"D+{horizon} UP 類別 AUC 熱力圖",
                height=300,
                template="plotly_white"
            )
            st.plotly_chart(fig_heat, use_container_width=True)
except Exception as e:
    st.warning(f"Per-Class AUC 分析失敗：{str(e)}")

# ===== Fold Stability =====
st.divider()
st.subheader(f"📉 Fold 穩定性趨勢 | Fold Stability (D+{horizon})")
st.markdown("""
<div class="insight-box">
<strong>📌 穩定性指標 | Stability Indicator：</strong>不同 Fold 間的性能波動越小，代表模型越穩健。
持續跌破品質門檻的模型可能存在資料或特徵洩漏。
</div>
""", unsafe_allow_html=True)

try:
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
            fig2 = px.line(
                df_fold,
                x="Fold",
                y="AUC",
                color="Engine",
                markers=True,
                title=f"D+{horizon} AUC 跨 Fold 演進 | AUC Across Folds",
                template="plotly_white",
                color_discrete_map={"LIGHTGBM": "#636EFA", "XGBOOST": "#EF553B"}
            )
            fig2.add_hline(y=0.52, line_dash="dash", line_color="red", annotation_text="品質門檻 | Quality Gate (0.52)")
            fig2.update_layout(height=350, hovermode="x unified")
            st.plotly_chart(fig2, use_container_width=True)

        with f2:
            fig3 = px.line(
                df_fold,
                x="Fold",
                y="LogLoss",
                color="Engine",
                markers=True,
                title=f"D+{horizon} LogLoss 跨 Fold 演進 | LogLoss Across Folds",
                template="plotly_white",
                color_discrete_map={"LIGHTGBM": "#636EFA", "XGBOOST": "#EF553B"}
            )
            fig3.update_layout(height=350, hovermode="x unified")
            st.plotly_chart(fig3, use_container_width=True)

        with st.expander("📋 逐折詳細數據 | Fold Details"):
            st.dataframe(df_fold, use_container_width=True, hide_index=True)
except Exception as e:
    st.warning(f"Fold 穩定性分析失敗：{str(e)}")

# ===== Feature Importance (Dual Engine) =====
st.divider()
st.subheader(f"🔝 特徵重要度對比 | Feature Importance (D+{horizon})")

try:
    available_engines = [
        e for e in model_data.keys()
        if isinstance(model_data.get(e), dict) and "avg_metrics" in model_data.get(e, {})
    ]

    if available_engines:
        st.caption("📊 並排比較 | Side-by-Side Comparison")

        if len(available_engines) >= 2:
            # Dual engine comparison
            eng_cols = st.columns(2)
            for col_idx, engine_sel in enumerate(available_engines[:2]):
                with eng_cols[col_idx]:
                    top_feats = model_data.get(engine_sel, {}).get("top_features", {})
                    if top_feats:
                        df_feat = pd.DataFrame(list(top_feats.items()), columns=["Feature", "Importance"])
                        df_feat = df_feat.sort_values("Importance", ascending=True).tail(12)

                        fig_feat = px.bar(
                            df_feat,
                            x="Importance",
                            y="Feature",
                            orientation="h",
                            color="Importance",
                            color_continuous_scale="Blues",
                            title=f"{engine_sel.upper()} D+{horizon} 特徵重要度 | Top-12",
                            template="plotly_white"
                        )
                        fig_feat.update_layout(height=450, showlegend=False, coloraxis_showscale=False)
                        st.plotly_chart(fig_feat, use_container_width=True)
        else:
            # Single engine
            engine_sel = available_engines[0]
            top_feats = model_data.get(engine_sel, {}).get("top_features", {})
            if top_feats:
                df_feat = pd.DataFrame(list(top_feats.items()), columns=["Feature", "Importance"])
                df_feat = df_feat.sort_values("Importance", ascending=True).tail(15)

                fig_feat = px.bar(
                    df_feat,
                    x="Importance",
                    y="Feature",
                    orientation="h",
                    color="Importance",
                    color_continuous_scale="Viridis",
                    title=f"{engine_sel.upper()} D+{horizon} 特徵重要度 | Top-15",
                    template="plotly_white"
                )
                fig_feat.update_layout(height=500, showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig_feat, use_container_width=True)
except Exception as e:
    st.warning(f"特徵重要度分析失敗：{str(e)}")

# ===== Footer & Limitations =====
st.markdown("---")
st.caption("📌 限制條件：固定歷史資料集 ｜ 非即時市場數據 ｜ 基準為等權計算 ｜ Ensemble = 簡單平均 ｜ 部分治理功能屬 Phase 3 規劃")

st.markdown('<div class="page-footer">量化分析工作台 — Model Metrics | 台灣股市多因子預測系統</div>', unsafe_allow_html=True)
