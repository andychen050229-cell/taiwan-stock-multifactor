"""Backtest — 策略回測分析"""

import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Backtest Results", page_icon="💰", layout="wide")

@st.cache_data
def load_report():
    report_dir = Path(__file__).parent.parent.parent / "outputs" / "reports"
    reports = sorted(report_dir.glob("phase2_report_*.json"), reverse=True)
    with open(reports[0], "r", encoding="utf-8") as f:
        return json.load(f)

report = load_report()
results = report["results"]
benchmark = results.get("benchmark", {})

st.title("💰 策略回測分析")

# Controls
col_ctrl1, col_ctrl2 = st.columns(2)
with col_ctrl1:
    horizon = st.selectbox("Horizon", [1, 5, 20], index=2, format_func=lambda x: f"D+{x}")
with col_ctrl2:
    cost_model = st.selectbox("成本模型", ["discount", "standard", "conservative"])

# ===== Performance Table =====
st.subheader(f"D+{horizon} — {cost_model.title()} 成本情境")

bt_data = results.get(f"backtest_horizon_{horizon}", {})
rows = []
for eng, res in bt_data.items():
    scenario = res.get("cost_scenarios", {}).get(cost_model, {})
    if scenario:
        rows.append({
            "Engine": eng.upper(),
            "Ann. Return": scenario.get("annualized_return", 0),
            "Sharpe": scenario.get("sharpe_ratio", 0),
            "Sortino": scenario.get("sortino_ratio", 0),
            "MDD": scenario.get("max_drawdown", 0),
            "Calmar": scenario.get("calmar_ratio", 0),
            "Win Rate": scenario.get("win_rate", 0),
            "Daily Cost": scenario.get("daily_cost", 0),
            "Rebalances": scenario.get("n_rebalances", 0),
            "Avg Turnover": res.get("avg_turnover", 0),
        })

# Benchmark row
rows.append({
    "Engine": "BENCHMARK",
    "Ann. Return": benchmark.get("annualized_return", 0),
    "Sharpe": benchmark.get("sharpe_ratio", 0),
    "Sortino": benchmark.get("sortino_ratio", 0),
    "MDD": benchmark.get("max_drawdown", 0),
    "Calmar": benchmark.get("calmar_ratio", 0),
    "Win Rate": benchmark.get("win_rate", 0),
    "Daily Cost": 0,
    "Rebalances": 0,
    "Avg Turnover": 0,
})

if rows:
    df = pd.DataFrame(rows)

    # Format for display
    df_display = df.copy()
    for col in ["Ann. Return", "MDD", "Win Rate", "Daily Cost", "Avg Turnover"]:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: f"{x:.2%}" if x != 0 else "-")
    for col in ["Sharpe", "Sortino", "Calmar"]:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: f"{x:.3f}")

    st.dataframe(df_display, use_container_width=True, hide_index=True)

# ===== Return Comparison Bar Chart =====
st.subheader("回報率比較")

fig = go.Figure()
engines = [r["Engine"] for r in rows]
returns = [r["Ann. Return"] for r in rows]
colors = ["#00CC96" if r > 0 else "#EF553B" for r in returns]

fig.add_trace(go.Bar(x=engines, y=returns, marker_color=colors,
                     text=[f"{r:+.1%}" for r in returns], textposition="outside"))
fig.update_layout(
    title=f"D+{horizon} Annualized Return ({cost_model})",
    yaxis_title="Annualized Return", yaxis_tickformat=".1%",
    height=400, template="plotly_white"
)
fig.add_hline(y=0, line_color="gray")
st.plotly_chart(fig, use_container_width=True)

# ===== Cost Impact Analysis =====
st.divider()
st.subheader("交易成本影響分析")

cost_rows = []
for eng, res in bt_data.items():
    for cn in ["discount", "standard", "conservative"]:
        sc = res.get("cost_scenarios", {}).get(cn, {})
        if sc:
            cost_rows.append({
                "Engine": eng.upper(),
                "Cost Model": cn.title(),
                "Ann. Return": sc.get("annualized_return", 0),
                "Daily Cost": sc.get("daily_cost", 0),
            })

if cost_rows:
    df_cost = pd.DataFrame(cost_rows)
    import plotly.express as px
    fig2 = px.bar(df_cost, x="Engine", y="Ann. Return", color="Cost Model",
                  barmode="group", text_auto=".1%",
                  color_discrete_map={"Discount": "#00CC96", "Standard": "#636EFA", "Conservative": "#EF553B"},
                  template="plotly_white", title=f"D+{horizon} Return by Cost Scenario")
    fig2.update_layout(height=400, yaxis_tickformat=".1%")
    fig2.add_hline(y=0, line_color="gray", line_dash="dash")
    st.plotly_chart(fig2, use_container_width=True)

# ===== Turnover Analysis =====
st.divider()
st.subheader("換手率與成本結構")

turnover_data = []
for h in [1, 5, 20]:
    bt_h = results.get(f"backtest_horizon_{h}", {})
    for eng, res in bt_h.items():
        disc = res.get("cost_scenarios", {}).get("discount", {})
        turnover_data.append({
            "Strategy": f"{eng} D+{h}",
            "Horizon": h,
            "Avg Turnover": res.get("avg_turnover", 0),
            "Rebalances/Year": disc.get("n_rebalances", 0),
            "Daily Cost": disc.get("daily_cost", 0),
            "Ann. Return": disc.get("annualized_return", 0),
        })

if turnover_data:
    df_to = pd.DataFrame(turnover_data)
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=df_to["Daily Cost"], y=df_to["Ann. Return"],
        mode="markers+text", text=df_to["Strategy"],
        textposition="top center", marker=dict(size=12, color=df_to["Horizon"], colorscale="Viridis"),
    ))
    fig3.update_layout(
        title="Daily Cost vs Return (All Strategies)",
        xaxis_title="Daily Cost", yaxis_title="Annualized Return",
        yaxis_tickformat=".1%", xaxis_tickformat=".4f",
        height=450, template="plotly_white"
    )
    fig3.add_hline(y=0, line_color="gray", line_dash="dash")
    st.plotly_chart(fig3, use_container_width=True)

# ===== Charts =====
st.divider()
st.subheader("回測圖表")

fig_dir = Path(__file__).parent.parent.parent / "outputs" / "figures"
c1, c2 = st.columns(2)

with c1:
    img = fig_dir / f"cumulative_returns_D{horizon}.png"
    if img.exists():
        st.image(str(img), caption=f"D+{horizon} 累積報酬", use_container_width=True)

    img2 = fig_dir / f"monthly_returns_ensemble_D{horizon}.png"
    if img2.exists():
        st.image(str(img2), caption=f"D+{horizon} 月報酬熱力圖", use_container_width=True)

with c2:
    img3 = fig_dir / f"drawdown_D{horizon}.png"
    if img3.exists():
        st.image(str(img3), caption=f"D+{horizon} 回撤走勢", use_container_width=True)

# ===== Bootstrap CI =====
bootstrap_data = results.get("bootstrap_ci", {})
if bootstrap_data:
    st.divider()
    st.subheader("Bootstrap 95% 信賴區間")
    ci_rows = []
    for key, val in bootstrap_data.items():
        ci_rows.append({
            "Strategy": key,
            "Return Point": f"{val.get('return_point', 0):+.2%}",
            "Return 95% CI": f"[{val.get('return_ci_lower', 0):+.2%}, {val.get('return_ci_upper', 0):+.2%}]",
            "Sharpe Point": f"{val.get('sharpe_point', 0):.2f}",
            "Sharpe 95% CI": f"[{val.get('sharpe_ci_lower', 0):.2f}, {val.get('sharpe_ci_upper', 0):.2f}]",
        })
    if ci_rows:
        st.dataframe(pd.DataFrame(ci_rows), use_container_width=True, hide_index=True)

# ===== Drawdown Analysis =====
dd_data = results.get("drawdown_analysis", {})
if dd_data:
    st.divider()
    st.subheader("條件回撤分析")
    dd_rows = []
    for key, val in dd_data.items():
        dd_rows.append({
            "Strategy": key,
            "CDaR 95%": f"{val.get('cdar_95', 0):.2%}",
            "Avg Recovery": f"{val.get('avg_recovery_days', 0)} days",
            "Episodes": val.get("n_episodes", 0),
        })
    if dd_rows:
        st.dataframe(pd.DataFrame(dd_rows), use_container_width=True, hide_index=True)
