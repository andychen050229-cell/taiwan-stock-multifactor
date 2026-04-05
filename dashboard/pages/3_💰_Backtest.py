"""Backtest — 策略回測分析（量化分析工作台）"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import inject_custom_css, inject_advanced_sidebar, load_report

st.set_page_config(page_title="Backtest | 量化分析工作台", page_icon="💰", layout="wide")
inject_custom_css()

report, report_name = load_report()
results = report["results"]
benchmark = results.get("benchmark", {})
inject_advanced_sidebar(report_name, report)

st.title("💰 策略回測分析")
st.caption("比較不同成本假設下各策略的績效，評估實際可行的交易方案")

# Controls
col_ctrl1, col_ctrl2 = st.columns(2)
with col_ctrl1:
    horizon = st.selectbox("Horizon", [1, 5, 20], index=2, format_func=lambda x: f"D+{x}")
with col_ctrl2:
    cost_model = st.selectbox("成本模型", ["discount", "standard", "conservative"],
                              format_func=lambda x: {"discount": "Discount（電子下單優惠）", "standard": "Standard（一般費率）", "conservative": "Conservative（含滑價）"}[x])

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
    df_display = df.copy()
    for col in ["Ann. Return", "MDD", "Win Rate", "Daily Cost", "Avg Turnover"]:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: f"{x:.2%}" if x != 0 else "-")
    for col in ["Sharpe", "Sortino", "Calmar"]:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: f"{x:.3f}")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

# ===== Return & Sharpe Side-by-Side =====
st.divider()

r1, r2 = st.columns(2)

with r1:
    fig = go.Figure()
    engines = [r["Engine"] for r in rows]
    returns = [r["Ann. Return"] for r in rows]
    colors = ["#00CC96" if r > 0 else "#EF553B" for r in returns]
    fig.add_trace(go.Bar(x=engines, y=returns, marker_color=colors,
                         text=[f"{r:+.1%}" for r in returns], textposition="outside"))
    fig.update_layout(
        title=f"D+{horizon} 年化報酬率 ({cost_model})",
        yaxis_title="Annualized Return", yaxis_tickformat=".1%",
        height=400, template="plotly_white"
    )
    fig.add_hline(y=0, line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

with r2:
    fig_sr = go.Figure()
    sharpes = [r["Sharpe"] for r in rows]
    colors_sr = ["#636EFA" if s > 0.5 else ("#FFA15A" if s > 0 else "#EF553B") for s in sharpes]
    fig_sr.add_trace(go.Bar(x=engines, y=sharpes, marker_color=colors_sr,
                            text=[f"{s:.2f}" for s in sharpes], textposition="outside"))
    fig_sr.update_layout(
        title=f"D+{horizon} 夏普比率 ({cost_model})",
        yaxis_title="Sharpe Ratio",
        height=400, template="plotly_white"
    )
    fig_sr.add_hline(y=0.5, line_dash="dash", line_color="green", annotation_text="Good (0.5)")
    fig_sr.add_hline(y=0, line_color="gray")
    st.plotly_chart(fig_sr, use_container_width=True)

# ===== Cost Impact =====
st.divider()
st.subheader("交易成本影響分析")
st.markdown("""
<div class="insight-box">
<strong>為什麼成本模型很重要？</strong>
同一策略在不同成本假設下，年化報酬可能差距 3–5%。
D+1 策略因換手率高達 64–68%，在任何成本情境下幾乎都不可行。
D+20 策略即使在保守成本下仍有正 alpha。
</div>
""", unsafe_allow_html=True)

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
    fig2 = px.bar(df_cost, x="Engine", y="Ann. Return", color="Cost Model",
                  barmode="group", text_auto=".1%",
                  color_discrete_map={"Discount": "#00CC96", "Standard": "#636EFA", "Conservative": "#EF553B"},
                  template="plotly_white", title=f"D+{horizon} 各成本情境年化報酬")
    fig2.update_layout(height=400, yaxis_tickformat=".1%")
    fig2.add_hline(y=0, line_color="gray", line_dash="dash")
    st.plotly_chart(fig2, use_container_width=True)

# ===== Turnover Analysis =====
st.divider()
st.subheader("換手率與成本結構（跨 Horizon 比較）")

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

    t1, t2 = st.columns(2)
    with t1:
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=df_to["Daily Cost"], y=df_to["Ann. Return"],
            mode="markers+text", text=df_to["Strategy"],
            textposition="top center",
            marker=dict(size=16, color=df_to["Horizon"],
                        colorscale=[[0, "#EF553B"], [0.5, "#FFA15A"], [1, "#00CC96"]],
                        showscale=True,
                        colorbar=dict(title="Horizon", tickvals=[1, 5, 20])),
        ))
        fig3.update_layout(
            title="Daily Cost vs Return",
            xaxis_title="Daily Cost", yaxis_title="Annualized Return",
            yaxis_tickformat=".1%", xaxis_tickformat=".4f",
            height=400, template="plotly_white"
        )
        fig3.add_hline(y=0, line_color="gray", line_dash="dash")
        st.plotly_chart(fig3, use_container_width=True)

    with t2:
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=df_to["Avg Turnover"], y=df_to["Ann. Return"],
            mode="markers+text", text=df_to["Strategy"],
            textposition="top center",
            marker=dict(size=16, color=df_to["Horizon"],
                        colorscale=[[0, "#EF553B"], [0.5, "#FFA15A"], [1, "#00CC96"]],
                        showscale=True,
                        colorbar=dict(title="Horizon", tickvals=[1, 5, 20])),
        ))
        fig4.update_layout(
            title="Turnover vs Return",
            xaxis_title="Avg Turnover", yaxis_title="Annualized Return",
            yaxis_tickformat=".1%", xaxis_tickformat=".0%",
            height=400, template="plotly_white"
        )
        fig4.add_hline(y=0, line_color="gray", line_dash="dash")
        st.plotly_chart(fig4, use_container_width=True)

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
    st.caption("1,000 次 Bootstrap 重抽樣估算的報酬率與 Sharpe 信賴區間")
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

# ===== Footer =====
st.markdown('<div class="page-footer">量化分析工作台 — Backtest | 台灣股市多因子預測系統</div>', unsafe_allow_html=True)
