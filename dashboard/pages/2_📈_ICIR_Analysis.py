"""ICIR Analysis — 信號穩定性分析（量化分析工作台）"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import inject_custom_css, inject_advanced_sidebar, load_report

st.set_page_config(page_title="ICIR Analysis | 量化分析工作台", page_icon="📈", layout="wide")
inject_custom_css()

report, report_name = load_report()
results = report["results"]
inject_advanced_sidebar(report_name, report)

icir_data = results.get("icir", {})

st.title("📈 ICIR 信號穩定性分析")
st.caption("ICIR = mean(daily Rank IC) / std(daily Rank IC) — 衡量因子選股能力的穩定性")

st.markdown("""
<div class="insight-box">
<strong>ICIR 解讀標準：</strong>
|ICIR| > 0.5 為良好信號，> 1.0 為優秀。
ICIR 本質上是 IC 的 t-statistic：即使 IC 不高，只要足夠穩定，ICIR 也可以很高。
</div>
""", unsafe_allow_html=True)

# ===== ICIR Dashboard =====
st.subheader("全模型 ICIR 總覽")

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

    fig = go.Figure()
    for h, color in [("D+1", "#EF553B"), ("D+5", "#FFA15A"), ("D+20", "#00CC96")]:
        subset = df_icir[df_icir["Horizon"] == h]
        fig.add_trace(go.Bar(
            name=h, x=subset["Engine"], y=subset["ICIR"],
            marker_color=color, text=subset["ICIR"].apply(lambda x: f"{x:.3f}"),
            textposition="outside"
        ))

    fig.update_layout(
        barmode="group", title="ICIR by Engine × Horizon",
        yaxis_title="ICIR", height=450, template="plotly_white",
    )
    fig.add_hline(y=0.5, line_dash="dash", line_color="green", annotation_text="Good (0.5)")
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df_icir.style.background_gradient(subset=["ICIR"], cmap="RdYlGn"),
        use_container_width=True, hide_index=True
    )

# ===== Key Insight =====
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("🎯 頻率結構分析")
    freq_data = pd.DataFrame({
        "Horizon": ["D+1", "D+5", "D+20"],
        "ICIR 範圍": ["-0.02 ~ 0.06", "0.06 ~ 0.07", "0.74 ~ 0.77"],
        "信號品質": ["❌ 噪音主導", "⚠️ 微弱", "✅ 極穩定"],
        "實務可行性": ["不可行", "邊際", "推薦"],
    })
    st.dataframe(freq_data, use_container_width=True, hide_index=True)

    st.markdown("""
<div class="insight-box">
<strong>核心結論：</strong>
Alpha 信號在月度頻率（D+20）真實且穩定，ICIR 達 0.74–0.77，遠超 0.5 門檻。
日頻和週頻的信噪比過低，不適合實際交易部署。
</div>
""", unsafe_allow_html=True)

with col2:
    st.subheader("📐 D+20 IC 統計量")
    if icir_rows:
        d20 = df_icir[df_icir["Horizon"] == "D+20"]
        if not d20.empty:
            for _, row in d20.iterrows():
                st.metric(
                    f"{row['Engine']} D+20",
                    f"ICIR = {row['ICIR']:.3f}",
                    delta=f"IC = {row['Mean IC']:.4f} (std={row['Std IC']:.4f})"
                )

    # Visual gauge for best ICIR
    if icir_rows:
        best_icir = max(r["ICIR"] for r in icir_rows)
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=best_icir,
            title={"text": "Best ICIR"},
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
        fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

# ===== IC Time Series Charts =====
st.divider()
st.subheader("IC 時間序列圖表")

fig_dir = Path(__file__).parent.parent.parent / "outputs" / "figures"
ic_charts = sorted(fig_dir.glob("ic_timeseries_*.png"))
if ic_charts:
    cols = st.columns(min(len(ic_charts), 3))
    for i, chart in enumerate(ic_charts):
        with cols[i % 3]:
            st.image(str(chart), caption=chart.stem.replace("ic_timeseries_", "IC: "), use_container_width=True)
else:
    st.info("IC 時間序列圖表尚未生成。請執行 `python run_phase2.py` 產生。")

# ===== Alpha Decay =====
alpha_decay = results.get("alpha_decay", {})
if alpha_decay:
    st.divider()
    st.subheader("Alpha 衰減分析")
    st.caption("使用 D+5 模型的預測分數，檢測其對不同 horizon 報酬的預測力衰減。")

    for eng, metrics in alpha_decay.items():
        decay_rows = []
        for ret_col, vals in metrics.items():
            decay_rows.append({
                "Return Column": ret_col,
                "Mean IC": vals.get("mean_ic", 0),
                "ICIR": vals.get("icir", 0),
            })
        if decay_rows:
            st.write(f"**{eng.upper()}**")
            st.dataframe(pd.DataFrame(decay_rows), use_container_width=True, hide_index=True)

# ===== Footer =====
st.markdown('<div class="page-footer">量化分析工作台 — ICIR Analysis | 台灣股市多因子預測系統</div>', unsafe_allow_html=True)
