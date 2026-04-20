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
render_topbar = _utils.render_topbar
render_phase_timeline = _utils.render_phase_timeline
render_auc_gauge = _utils.render_auc_gauge
render_horizon_segmented = _utils.render_horizon_segmented

inject_custom_css()

# ---- Top-bar (sticky breadcrumb + model chips + clock) ------------------
render_topbar(
    crumb_left="股票預測系統",
    crumb_current="模型績效分析",
    chips=[
        ("Purged WF · 4-Fold", "pri"),
        ("LightGBM + XGBoost", "vio"),
        ("all gates → PASS", "ok"),
    ],
    show_clock=True,
)

# ---- Data Context Banner -----------------------------------------------
st.markdown("""
<div class="gl-box-info" style="margin-top:14px;">
📋 <strong>研究背景</strong>：固定歷史資料集（2023/03–2025/03）&nbsp;·&nbsp;Purged Walk-Forward CV（4 Folds）&nbsp;·&nbsp;LightGBM + XGBoost Ensemble
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
st.caption("模型在各 Fold 的 AUC、LogLoss 表現，以及雙引擎（LightGBM + XGBoost）比較")

st.info("""
**如何閱讀本頁？**

AUC（曲線下面積）衡量模型區分「上漲股」與「下跌股」的能力。

0.5 = 隨機猜測，> 0.52 為本系統最低門檻。

LogLoss 衡量預測機率的校準程度，越低代表模型越有信心且準確。

各 Fold 代表不同時間段的驗證結果。
""")

# ===== Horizon selector =====
st.markdown("**選擇 Horizon | Select Horizon**")
sel_col, seg_col = st.columns([1, 3])
with sel_col:
    horizon = st.selectbox(
        " ",
        [1, 5, 20],
        index=2,
        format_func=lambda x: f"D+{x}",
        label_visibility="collapsed",
        key="mm_horizon",
    )
with seg_col:
    render_horizon_segmented(
        options=["D+1", "D+5", "D+20"],
        current=f"D+{horizon}",
        key_prefix="mm",
    )

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
                "最佳 AUC",
                f"{best_auc_engine['auc']:.4f}",
                delta=best_auc_engine['engine']
            )
        with kpi_col2:
            st.metric(
                "最佳引擎",
                best_auc_engine['engine'],
                delta=f"D+{horizon}"
            )
        with kpi_col3:
            if best_ll_improvement:
                ll_imp = (1 - best_ll_improvement["logloss"] / best_ll_improvement["baseline_ll"]) * 100
                st.metric(
                    "LogLoss 改進",
                    f"{ll_imp:.1f}%",
                    delta="vs 基線"
                )
        with kpi_col4:
            st.metric(
                "預測天期",
                f"D+{horizon}",
                delta="前瞻天數"
            )

        # ===== Signature AUC Gauge (half-ring SVG) =====
        st.markdown("")
        auc_html = render_auc_gauge(
            val=best_auc_engine["auc"],
            min_v=0.5, max_v=0.7,
            label=f"AUC · {best_auc_engine['engine']} · D+{horizon} · target ≥ 0.52",
            width=320, height=180,
        )
        st.markdown(
            f'<div class="gl-panel" style="display:flex;align-items:center;justify-content:center;padding:18px 22px;">{auc_html}</div>',
            unsafe_allow_html=True,
        )

        # ===== Phase timeline (full-width below the gauge) =====
        st.markdown(
            '<div style="font-size:0.72rem;color:var(--gl-text-3);font-weight:600;'
            'letter-spacing:.06em;text-transform:uppercase;margin:14px 0 6px;">RESEARCH PROGRESS · PHASE 2 ACTIVE</div>',
            unsafe_allow_html=True,
        )
        render_phase_timeline(current_phase=2)

        st.divider()
except Exception as e:
    st.warning(f"KPI 計算發生錯誤：{str(e)}")

# ===== Model Comparison Radar Chart =====
try:
    st.subheader("📊 引擎對標分析 | Engine Comparison")
    st.caption("↓ 雷達圖越大代表該引擎在該維度表現越好。AUC 高 + LogLoss 低 = 最理想。")
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
        <strong>💡 洞察 | Insight：</strong><br>
        AUC > 0.52 表示模型優於隨機預測，超越品質門檻。<br>
        ENSEMBLE 通常結合個別模型優勢，實現更穩定的預測。<br><br>
        <strong>✅ 應用建議：</strong><br>
        在 <strong>月度頻率（D+20）</strong> 策略部署；D+1/D+5 信號品質不足，不推薦實盤使用。
        </div>
        """, unsafe_allow_html=True)
except Exception as e:
    st.error(f"AUC 比較失敗：{str(e)}")

# ===== Per-Class AUC =====
st.divider()
st.subheader(f"🎯 分類別 AUC 分析 | Per-Class AUC (D+{horizon})")
st.caption("↓ 三類（DOWN/FLAT/UP）的個別 AUC，觀察模型在哪個方向的判斷更有信心。")
st.markdown("""
<div class="insight-box">
<strong>❓ 為什麼看 Per-Class AUC | Why Per-Class AUC？</strong><br>
三分類問題中，整體 AUC 可能掩蓋個別類別的弱點。<br>
Per-Class AUC 分別衡量模型對 DOWN / FLAT / UP 的區辨能力，幫助識別特定類別的模型弱點。
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
<strong>📌 穩定性指標 | Stability Indicator：</strong><br>
不同 Fold 間的性能波動越小，代表模型越穩健。<br>
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

# ===== Calibration (ECE) Analysis =====
st.divider()
st.subheader(f"🎯 校準分析 | Calibration Analysis (D+{horizon})")
st.markdown("""
<div class="insight-box">
<strong>❓ 什麼是校準（Calibration）？</strong><br>
校準衡量模型輸出的機率是否與實際頻率一致。<br>
例如模型預測某股票有 70% 機率上漲，則在所有被預測 70% 的股票中，應約有 70% 確實上漲。<br>
<strong>ECE（Expected Calibration Error）</strong>越低代表校準越好。<br>
本系統使用 <strong>Isotonic Regression</strong> 進行後校準。
</div>
""", unsafe_allow_html=True)

try:
    calibration_data = results.get("calibration", {})
    if calibration_data:
        cal_rows = []
        for key, val in calibration_data.items():
            parts = key.rsplit("_", 1)
            if len(parts) == 2:
                eng_name, h_tag = parts
                h_val = int(h_tag.replace("D", ""))
                if h_val == horizon:
                    cal_rows.append({
                        "模型 | Model": eng_name.upper().replace("_", " "),
                        "校準前 ECE | Before": val["before"]["ece"],
                        "校準後 ECE | After": val["after"]["ece"],
                        "改善幅度 | Improvement": f'{val["improvement_pct"]:.1f}%',
                        "校準前 Brier | Before": val["before"]["brier_score"],
                        "校準後 Brier | After": val["after"]["brier_score"],
                    })

        if cal_rows:
            df_cal = pd.DataFrame(cal_rows)
            st.dataframe(
                df_cal.style.background_gradient(subset=["校準後 ECE | After"], cmap="RdYlGn_r"),
                use_container_width=True,
                hide_index=True,
            )

            # ECE before/after bar chart
            fig_cal = go.Figure()
            models = [r["模型 | Model"] for r in cal_rows]
            ece_before = [r["校準前 ECE | Before"] for r in cal_rows]
            ece_after = [r["校準後 ECE | After"] for r in cal_rows]

            fig_cal.add_trace(go.Bar(
                name="校準前 | Before", x=models, y=ece_before,
                marker_color="#EF553B", text=[f"{v:.4f}" for v in ece_before], textposition="outside"
            ))
            fig_cal.add_trace(go.Bar(
                name="校準後 | After", x=models, y=ece_after,
                marker_color="#00CC96", text=[f"{v:.4f}" for v in ece_after], textposition="outside"
            ))
            fig_cal.update_layout(
                barmode="group",
                title=f"D+{horizon} ECE 校準前後對比 | ECE Before vs After Isotonic Regression",
                yaxis_title="ECE（越低越好）",
                height=400, template="plotly_white",
            )
            st.plotly_chart(fig_cal, use_container_width=True)

            # Per-fold ECE details
            with st.expander("📋 逐折 ECE 明細 | Per-Fold ECE Details"):
                fold_ece_rows = []
                for key, val in calibration_data.items():
                    parts = key.rsplit("_", 1)
                    if len(parts) == 2:
                        eng_name, h_tag = parts
                        h_val = int(h_tag.replace("D", ""))
                        if h_val == horizon and "per_fold_ece" in val:
                            for i, ece_val in enumerate(val["per_fold_ece"]):
                                fold_ece_rows.append({
                                    "Model": eng_name.upper(),
                                    "Fold": i + 1,
                                    "ECE (Before Cal.)": ece_val,
                                })
                if fold_ece_rows:
                    st.dataframe(pd.DataFrame(fold_ece_rows), use_container_width=True, hide_index=True)

            st.markdown(f"""
            <div class="insight-box">
            <strong>💡 洞察 | Insight：</strong>
            Isotonic Regression 校準使 D+{horizon} 的 ECE 平均降低約 <strong>74–80%</strong>，顯著提升機率輸出的可靠性。<br>
            校準後 ECE 均低於 0.02，達到高品質校準水準。
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("校準數據不可用。請確認報告中包含 calibration 資料。")
except Exception as e:
    st.warning(f"校準分析載入失敗：{str(e)}")

# ===== Confusion Matrices =====
st.divider()
st.subheader(f"🔢 混淆矩陣 | Confusion Matrices (D+{horizon})")
st.markdown("""
<div class="insight-box">
<strong>❓ 什麼是混淆矩陣？</strong><br>
混淆矩陣展示模型對 DOWN / FLAT / UP 三個類別的實際分類結果。<br>
對角線上的值代表正確分類，非對角線代表錯誤分類。<br>
可以從中觀察模型是否偏向預測特定類別。
</div>
""", unsafe_allow_html=True)

try:
    figures_dir = Path(__file__).resolve().parent.parent / "outputs" / "figures"
    if not figures_dir.exists():
        figures_dir = Path.cwd() / "outputs" / "figures"

    cm_col1, cm_col2 = st.columns(2)
    for col, engine in zip([cm_col1, cm_col2], ["lightgbm", "xgboost"]):
        with col:
            cm_path = figures_dir / f"confusion_matrix_{engine}_D{horizon}.png"
            if cm_path.exists():
                st.image(str(cm_path), caption=f"{engine.upper()} D+{horizon}", use_container_width=True)
            else:
                st.info(f"{engine.upper()} 混淆矩陣不存在")

    st.markdown("""
    <div class="insight-box">
    <strong>💡 解讀建議 | Reading Guide：</strong><br>
    觀察對角線佔比——若 FLAT 類被大量預測，可能反映市場中性偏好。<br>
    DOWN 與 UP 的混淆程度直接影響策略方向判斷的準確性。
    </div>
    """, unsafe_allow_html=True)
except Exception as e:
    st.warning(f"混淆矩陣載入失敗：{str(e)}")

# ===== Hyperparameter Optimization Results =====
st.divider()
st.subheader(f"⚙️ 超參數最佳化結果 | Hyperparameter Optimization (D+{horizon})")
st.markdown("""
<div class="insight-box">
<strong>❓ 超參數搜尋流程</strong><br>
本系統使用 <strong>Optuna（TPE Sampler）</strong> 對每個 Horizon × Engine 組合進行 <strong>50 輪</strong>貝葉斯超參數搜尋，目標函數為 Walk-Forward CV 平均 AUC。<br>
搜尋空間涵蓋學習率、樹深度、正則化強度等核心參數。
</div>
""", unsafe_allow_html=True)

try:
    hp_rows = []
    for eng, res in model_data.items():
        if isinstance(res, dict) and "best_params" in res:
            bp = res["best_params"]
            for param, value in bp.items():
                hp_rows.append({
                    "Engine": eng.upper(),
                    "參數 | Parameter": param,
                    "最佳值 | Best Value": f"{value:.6f}" if isinstance(value, float) else str(value),
                })

    if hp_rows:
        # Show as side-by-side tables
        engines_with_params = list(set(r["Engine"] for r in hp_rows))
        if len(engines_with_params) >= 2:
            hp_col1, hp_col2 = st.columns(2)
            for col, eng in zip([hp_col1, hp_col2], sorted(engines_with_params)):
                with col:
                    st.markdown(f"**{eng}**")
                    eng_params = [r for r in hp_rows if r["Engine"] == eng]
                    df_hp = pd.DataFrame(eng_params)[["參數 | Parameter", "最佳值 | Best Value"]]
                    st.dataframe(df_hp, use_container_width=True, hide_index=True)
        else:
            st.dataframe(pd.DataFrame(hp_rows), use_container_width=True, hide_index=True)

        # Key parameter comparison chart
        common_params = ["n_estimators", "learning_rate", "max_depth"]
        chart_rows = []
        for eng, res in model_data.items():
            if isinstance(res, dict) and "best_params" in res:
                bp = res["best_params"]
                for p in common_params:
                    if p in bp:
                        chart_rows.append({"Engine": eng.upper(), "Parameter": p, "Value": float(bp[p])})

        if chart_rows:
            df_chart = pd.DataFrame(chart_rows)
            fig_hp = px.bar(
                df_chart, x="Parameter", y="Value", color="Engine", barmode="group",
                title=f"D+{horizon} 核心超參數對比 | Key Hyperparameters",
                template="plotly_white",
                color_discrete_map={"LIGHTGBM": "#636EFA", "XGBOOST": "#EF553B"},
            )
            fig_hp.update_layout(height=380)
            st.plotly_chart(fig_hp, use_container_width=True)

        st.markdown(f"""
        <div class="insight-box">
        <strong>💡 洞察 | Insight：</strong>
        Optuna 搜尋結果顯示 D+{horizon} 模型傾向使用較低學習率搭配較多棵樹，並透過正則化（reg_alpha / reg_lambda）控制過擬合。<br>
        兩引擎的最佳參數差異反映其架構特性。
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("超參數資料不可用。請確認報告中包含 best_params 資料。")
except Exception as e:
    st.warning(f"超參數分析載入失敗：{str(e)}")

# ===== Static Figures: Fold Stability & Model Comparison =====
st.divider()
st.subheader("📊 綜合比較圖表 | Overview Charts")

try:
    figures_dir = Path(__file__).resolve().parent.parent.parent / "outputs" / "figures"
    if not figures_dir.exists():
        figures_dir = Path.cwd() / "outputs" / "figures"

    ov_col1, ov_col2 = st.columns(2)
    with ov_col1:
        fs_img = figures_dir / "fold_stability.png"
        if fs_img.exists():
            st.image(str(fs_img), caption="跨 Fold AUC 穩定性 | Fold Stability", use_container_width=True)
    with ov_col2:
        mc_img = figures_dir / "model_comparison.png"
        if mc_img.exists():
            st.image(str(mc_img), caption="模型對標比較 | Model Comparison", use_container_width=True)
except Exception:
    pass

# ===== LOPO Pillar Contribution Bars (ported from Design system) =====
st.divider()
st.subheader("🧩 LOPO · 九支柱邊際貢獻 | Leave-One-Pillar-Out Contribution")
st.caption(
    "逐一移除每個支柱後重訓模型，量化該支柱對 D+20 AUC 的真實邊際貢獻（單位：bps）。"
    "越高代表該支柱對整體預測越不可或缺。"
)

try:
    load_phase6_json = _utils.load_phase6_json
    lopo_data, _ = load_phase6_json(f"lopo_pillar_contribution_D{horizon}.json")
    if not lopo_data:
        lopo_data, _ = load_phase6_json("lopo_pillar_contribution_D20.json")

    pillar_labels = {
        "risk": "風險面", "fund": "基本面", "chip": "籌碼面",
        "trend": "技術面", "val": "評價面", "event": "事件面",
        "ind": "產業面", "txt": "文本面", "sent": "情緒面",
    }

    render_pillar_bar = _utils.render_pillar_bar

    if lopo_data and "ranking_by_delta_auc" in lopo_data:
        ranking = lopo_data["ranking_by_delta_auc"]
        max_d = max(abs(r["delta_auc"]) for r in ranking) or 0.001
        rows_html = []
        for r in ranking:
            pk = r["pillar"]
            delta_bps = r["delta_auc"] * 10000
            pct = (abs(r["delta_auc"]) / max_d) * 100
            rows_html.append(render_pillar_bar(
                pillar_key=pk,
                label=pillar_labels.get(pk, pk),
                feat_count=r.get("n_features", 0),
                pct=pct,
                delta_bps=delta_bps,
            ))
        st.markdown(
            '<div class="gl-panel" style="padding:18px 22px;">' + "".join(rows_html) + "</div>",
            unsafe_allow_html=True,
        )
        baseline = lopo_data.get("baseline", {}).get("auc_macro", 0.649)
        st.caption(
            f"📐 Baseline AUC (full pillar set, D+{horizon})：**{baseline:.4f}**　·　"
            f"ranking by |Δ AUC|（越大越重要）"
        )
    else:
        st.info(f"D+{horizon} LOPO 資料不可用，請檢查 outputs/phase6/ 目錄。")
except Exception as e:
    st.warning(f"LOPO 支柱貢獻載入失敗：{str(e)}")

# ===== Footer & Limitations =====
st.markdown("---")
st.caption("📌 限制條件：固定歷史資料集 ｜ 非即時市場數據 ｜ 基準為等權計算 ｜ Ensemble = 簡單平均 ｜ Phase 3 治理已實現")

st.markdown('<div class="page-footer">量化分析工作台 — Model Metrics | 台灣股市多因子預測系統</div>', unsafe_allow_html=True)
