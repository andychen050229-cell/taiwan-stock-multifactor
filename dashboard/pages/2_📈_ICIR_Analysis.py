"""ICIR Analysis — 信號穩定性分析（量化分析工作台）"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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

st.set_page_config(page_title="ICIR Analysis | 量化分析工作台", page_icon="📈", layout="wide")
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
    inject_advanced_sidebar(report_name, report, current_page="icir_analysis")
except Exception as e:
    st.error(f"無法載入報告：{str(e)}")
    st.stop()

st.title("📈 ICIR 信號穩定性分析")
st.caption("ICIR Analysis | ICIR = mean(daily Rank IC) / std(daily Rank IC) — 衡量因子選股能力的穩定性與可靠性")

st.markdown("""
<div class="insight-box">
<strong>❓ 什麼是 ICIR | What is ICIR？</strong><br>
ICIR 本質上是 IC 的 t-statistic。|ICIR| > 0.5 為良好信號，> 1.0 為優秀。
即使 IC 不高，只要足夠穩定，ICIR 也可以很高——這正是長期超額收益的基礎。
</div>
""", unsafe_allow_html=True)

try:
    icir_data = results.get("icir", {})

    # ===== ICIR Summary KPIs =====
    icir_rows = []
    for key, val in icir_data.items():
        parts = key.rsplit("_D", 1)
        eng = parts[0] if len(parts) == 2 else key
        horizon = parts[1] if len(parts) == 2 else "?"
        icir_rows.append({
            "Model": key,
            "Engine": eng.upper(),
            "Horizon": f"D+{horizon}",
            "Mean IC": val.get("mean_ic", 0),
            "Std IC": val.get("std_ic", 0),
            "ICIR": val.get("icir", 0),
        })

    if icir_rows:
        df_icir = pd.DataFrame(icir_rows)

        # KPI Row
        st.markdown("### 🎯 關鍵績效指標 | Key Metrics")
        best_icir_row = max(icir_rows, key=lambda x: x["ICIR"])
        d20_rows = [r for r in icir_rows if "D+20" in r["Horizon"]]
        best_d20 = max(d20_rows, key=lambda x: x["ICIR"]) if d20_rows else None

        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        with kpi_col1:
            st.metric(
                "最佳 ICIR | Best ICIR",
                f"{best_icir_row['ICIR']:.4f}",
                delta=best_icir_row["Engine"]
            )
        with kpi_col2:
            st.metric(
                "最佳天期 | Best Horizon",
                best_icir_row["Horizon"],
                delta="預測能力最強"
            )
        with kpi_col3:
            if best_d20:
                st.metric(
                    "D+20 ICIR | Monthly Signal",
                    f"{best_d20['ICIR']:.4f}",
                    delta="長期信號品質"
                )
        with kpi_col4:
            icir_threshold = 0.5
            above_threshold = sum(1 for r in icir_rows if r["ICIR"] > icir_threshold)
            st.metric(
                "超優質信號 | Premium Signals",
                f"{above_threshold}/{len(icir_rows)}",
                delta="ICIR > 0.5"
            )

        st.divider()

        # ===== ICIR 全景視圖 =====
        st.subheader("📊 ICIR 全景視圖 | ICIR Overview")

        fig_main = go.Figure()
        for h, color in [("D+1", "#EF553B"), ("D+5", "#FFA15A"), ("D+20", "#00CC96")]:
            subset = df_icir[df_icir["Horizon"] == h]
            fig_main.add_trace(go.Bar(
                name=h,
                x=subset["Engine"],
                y=subset["ICIR"],
                marker_color=color,
                text=subset["ICIR"].apply(lambda x: f"{x:.4f}"),
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>ICIR: %{y:.4f}<extra></extra>"
            ))

        fig_main.update_layout(
            barmode="group",
            title="各引擎×天期 ICIR 對標 | ICIR by Engine × Horizon",
            yaxis_title="ICIR",
            height=450,
            template="plotly_white",
            hovermode="x unified",
        )
        fig_main.add_hline(y=0.5, line_dash="dash", line_color="green", annotation_text="優質閾值 | Good (0.5)")
        fig_main.add_hline(y=1.0, line_dash="dash", line_color="darkgreen", annotation_text="優秀閾值 | Excellent (1.0)")
        fig_main.add_hline(y=0, line_dash="dot", line_color="gray")
        st.plotly_chart(fig_main, use_container_width=True)

        st.dataframe(
            df_icir.style.background_gradient(subset=["ICIR"], cmap="RdYlGn"),
            use_container_width=True,
            hide_index=True
        )

        # ===== IC Distribution Histograms =====
        st.divider()
        st.subheader("📈 IC 分布直方圖 | IC Distribution")
        st.caption("Daily Rank IC 分佈特徵 — 評估信號的穩定性與偏度")

        st.warning("⚠️ 以下圖表使用模擬數據（np.random）作為示意，非正式回測輸出。正式 IC/ICIR 數據請參考 Phase 2 報告。")

        dist_col1, dist_col2 = st.columns(2)

        # Simulated IC distribution (in real case, would load from data)
        with dist_col1:
            # D+1 vs D+20 distribution comparison
            np.random.seed(42)
            d1_ic = np.random.normal(-0.001, 0.025, 200)  # Noisy
            d20_ic = np.random.normal(0.008, 0.012, 200)  # Clean

            fig_dist = go.Figure()
            fig_dist.add_trace(go.Histogram(
                x=d1_ic,
                name="D+1 IC",
                nbinsx=30,
                marker_color="#EF553B",
                opacity=0.7
            ))
            fig_dist.add_trace(go.Histogram(
                x=d20_ic,
                name="D+20 IC",
                nbinsx=30,
                marker_color="#00CC96",
                opacity=0.7
            ))
            fig_dist.update_layout(
                title="短期 vs 長期 IC 分布 | D+1 vs D+20 Distribution",
                xaxis_title="Daily Rank IC",
                yaxis_title="頻次 | Frequency",
                barmode="overlay",
                height=400,
                template="plotly_white"
            )
            st.plotly_chart(fig_dist, use_container_width=True)

        with dist_col2:
            # Q-Q plot style visualization
            fig_qq = go.Figure()

            # Percentile comparison
            percentiles = np.linspace(0, 100, 21)
            d1_perc = np.percentile(d1_ic, percentiles)
            d20_perc = np.percentile(d20_ic, percentiles)

            fig_qq.add_trace(go.Scatter(
                x=d1_perc,
                y=d20_perc,
                mode="lines+markers",
                name="D+1 vs D+20",
                line=dict(color="#636EFA", width=2),
                marker=dict(size=8)
            ))

            # Diagonal reference line
            min_val = min(d1_perc.min(), d20_perc.min())
            max_val = max(d1_perc.max(), d20_perc.max())
            fig_qq.add_trace(go.Scatter(
                x=[min_val, max_val],
                y=[min_val, max_val],
                mode="lines",
                name="Reference (equal)",
                line=dict(color="gray", dash="dash")
            ))

            fig_qq.update_layout(
                title="分位數比較 | Quantile-Quantile Plot",
                xaxis_title="D+1 IC Percentile",
                yaxis_title="D+20 IC Percentile",
                height=400,
                template="plotly_white"
            )
            st.plotly_chart(fig_qq, use_container_width=True)

        # ===== Rolling ICIR (Simulated) =====
        st.divider()
        st.subheader("⏰ 滾動 ICIR 趨勢 | Rolling ICIR Evolution")
        st.caption("ICIR 在時間上的變化 — 反映信號穩定性的動態")

        st.warning("⚠️ 以下滾動趨勢圖使用模擬數據（np.random）作為示意，非正式回測輸出。正式 IC/ICIR 數據請參考 Phase 2 報告。")

        # Simulate rolling ICIR
        dates = pd.date_range('2023-03-01', '2025-03-01', freq='D')
        rolling_icir_d1 = pd.Series(
            0.02 + np.random.normal(0, 0.03, len(dates)),
            index=dates
        ).rolling(30).mean()
        rolling_icir_d20 = pd.Series(
            0.75 + np.random.normal(0, 0.05, len(dates)),
            index=dates
        ).rolling(30).mean()

        fig_rolling = go.Figure()
        fig_rolling.add_trace(go.Scatter(
            x=rolling_icir_d1.index,
            y=rolling_icir_d1.values,
            name="D+1 ICIR (30d MA)",
            line=dict(color="#EF553B", width=2),
            hovertemplate="<b>D+1</b><br>Date: %{x|%Y-%m-%d}<br>ICIR: %{y:.4f}<extra></extra>"
        ))
        fig_rolling.add_trace(go.Scatter(
            x=rolling_icir_d20.index,
            y=rolling_icir_d20.values,
            name="D+20 ICIR (30d MA)",
            line=dict(color="#00CC96", width=2),
            hovertemplate="<b>D+20</b><br>Date: %{x|%Y-%m-%d}<br>ICIR: %{y:.4f}<extra></extra>"
        ))

        fig_rolling.update_layout(
            title="30 日滾動 ICIR 趨勢 | 30-Day Rolling ICIR",
            xaxis_title="時間 | Date",
            yaxis_title="ICIR",
            height=400,
            template="plotly_white",
            hovermode="x unified"
        )
        fig_rolling.add_hline(y=0.5, line_dash="dash", line_color="green", annotation_text="優質閾值")
        st.plotly_chart(fig_rolling, use_container_width=True)

        # ===== 頻率結構與實務建議 =====
        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🎯 頻率結構分析 | Frequency Structure")
            freq_data = pd.DataFrame({
                "天期 | Horizon": ["D+1", "D+5", "D+20"],
                "ICIR 範圍": ["-0.02~0.06", "0.06~0.07", "0.74~0.77"],
                "信號品質": ["❌ 噪音主導", "⚠️ 微弱信號", "✅ 優秀信號"],
                "可行性 | Feasibility": ["❌ 不可行", "⚠️ 邊際", "✅ 推薦"],
            })
            st.dataframe(freq_data, use_container_width=True, hide_index=True)

            st.markdown("""
            <div class="success-box">
            <strong>✅ 核心結論 | Key Finding：</strong><br>
            Alpha 信號在月度頻率（D+20）真實且穩定，ICIR 達 0.74–0.77，遠超 0.5 門檻。
            日頻（D+1）與週頻（D+5）的信噪比過低，不適合實際交易部署。
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.subheader("📐 D+20 IC 關鍵統計 | D+20 Stats")
            if d20_rows:
                for row in d20_rows:
                    st.metric(
                        f"{row['Engine']} D+20 ICIR",
                        f"{row['ICIR']:.4f}",
                        delta=f"Mean IC: {row['Mean IC']:.4f} | Std: {row['Std IC']:.4f}"
                    )

            # Best ICIR gauge
            if icir_rows:
                best_icir = max(r["ICIR"] for r in icir_rows)
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=best_icir,
                    title={"text": "最佳 ICIR | Best ICIR"},
                    gauge={
                        "axis": {"range": [0, 1.5]},
                        "steps": [
                            {"range": [0, 0.3], "color": "#fef2f2"},
                            {"range": [0.3, 0.5], "color": "#fef3c7"},
                            {"range": [0.5, 1.0], "color": "#ecfdf5"},
                            {"range": [1.0, 1.5], "color": "#d1fae5"},
                        ],
                        "bar": {"color": "#059669"},
                        "threshold": {"line": {"color": "#059669", "width": 3}, "value": best_icir},
                    }
                ))
                fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
                st.plotly_chart(fig_gauge, use_container_width=True)

        # ===== IC Time Series Charts =====
        st.divider()
        st.subheader("📊 IC 時間序列圖表 | IC Time Series")

        fig_dir = Path(__file__).parent.parent.parent / "outputs" / "figures"
        ic_charts = sorted(fig_dir.glob("ic_timeseries_*.png"))
        if ic_charts:
            cols = st.columns(min(len(ic_charts), 3))
            for i, chart in enumerate(ic_charts):
                with cols[i % 3]:
                    st.image(str(chart), caption=chart.stem.replace("ic_timeseries_", "IC: "), use_container_width=True)
        else:
            st.info("💡 IC 時間序列圖表尚未生成。請執行 run_phase2.py 產生。")

        # ===== Alpha Decay =====
        st.divider()
        alpha_decay = results.get("alpha_decay", {})
        if alpha_decay:
            st.subheader("📉 Alpha 衰減分析 | Alpha Decay")
            st.caption("使用 D+5 模型的預測分數，檢測其對不同 horizon 報酬的預測力衰減")

            for eng, metrics in alpha_decay.items():
                decay_rows = []
                for ret_col, vals in metrics.items():
                    decay_rows.append({
                        "Return Horizon": ret_col,
                        "Mean IC": f"{vals.get('mean_ic', 0):.4f}",
                        "ICIR": f"{vals.get('icir', 0):.4f}",
                    })
                if decay_rows:
                    with st.expander(f"🔍 {eng.upper()} Alpha 衰減", expanded=False):
                        st.dataframe(pd.DataFrame(decay_rows), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"ICIR 分析發生錯誤：{str(e)}")

# ===== Footer & Limitations =====
st.markdown("---")
st.caption("📌 限制條件：固定歷史資料集 ｜ 非即時市場數據 ｜ 基準為等權計算 ｜ Ensemble = 簡單平均 ｜ 部分治理功能屬 Phase 3 規劃")

st.markdown('<div class="page-footer">量化分析工作台 — ICIR Analysis | 台灣股市多因子預測系統</div>', unsafe_allow_html=True)
