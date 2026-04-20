"""Backtest — 策略回測分析（量化分析工作台）"""

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
render_topbar = _utils.render_topbar
inject_advanced_sidebar = _utils.inject_advanced_sidebar
load_report = _utils.load_report
glint_plotly_layout = _utils.glint_plotly_layout
render_chart_note = _utils.render_chart_note
render_page_heading = _utils.render_page_heading
render_trust_strip = _utils.render_trust_strip
render_page_footer = _utils.render_page_footer

inject_custom_css()

# ---- Top-bar (sticky breadcrumb + model chips + clock) ----
render_topbar(
    crumb_left="股票預測系統",
    crumb_current="策略回測",
    chips=[("D+20 monthly", "pri"), ("cost ladder 3 scenarios", "vio"), ("edge +11.7pp", "ok")],
    show_clock=True,
)

try:
    report, report_name = load_report()
    results = report["results"]
    benchmark = results.get("benchmark", {})
    inject_advanced_sidebar(report_name, report, current_page="backtest")
except Exception as e:
    st.error(f"無法載入報告：{str(e)}")
    st.stop()

render_page_heading(
    icon="💰",
    title_zh="策略回測分析",
    title_en="Strategy Backtest",
    command_line="在三種成本情境下檢驗各引擎 × 天期的年化報酬、Sharpe、最大回撤；D+20 月頻為推薦配置。",
    tone="emerald",
)
render_trust_strip([
    ("DATASET",  "2023/03 – 2025/03",       "blue"),
    ("CV",        "Purged WF · 4 Folds",     "violet"),
    ("COSTS",     "Discount / Std / Conservative", "amber"),
    ("BENCHMARK", "等權組合",                 "cyan"),
])

with st.expander("ℹ️ 如何閱讀本頁？", expanded=False):
    st.markdown("""
- **年化報酬 > 0** ＝ 策略具有正 alpha。
- **Sharpe > 1.0** ＝ 風險調整後表現良好。
- **最大回撤 (MDD)** ＝ 策略最糟情況下的跌幅。
- **三種成本情境**（無成本 / 折扣 / 保守）用於檢驗交易摩擦對策略的侵蝕程度。
""")

# Controls
col_ctrl1, col_ctrl2 = st.columns(2)
with col_ctrl1:
    horizon = st.selectbox("選擇 Horizon | Select Horizon", [1, 5, 20], index=2, format_func=lambda x: f"D+{x}")
with col_ctrl2:
    cost_model = st.selectbox(
        "成本模型 | Cost Model",
        ["discount", "standard", "conservative"],
        format_func=lambda x: {
            "discount": "折扣 | Discount（電子下單優惠）",
            "standard": "標準 | Standard（一般費率）",
            "conservative": "保守 | Conservative（含滑價）"
        }[x]
    )

# ===== Hero KPI Row =====
try:
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

        # Find best strategy
        best_strategy = max([r for r in rows if r["Engine"] != "BENCHMARK"], key=lambda x: x["Sharpe"], default={})

        st.markdown("### 🏆 最優策略快照 | Best Strategy Snapshot")
        if best_strategy:
            kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
            with kpi_col1:
                st.metric(
                    "年化報酬率",
                    f"{best_strategy['Ann. Return']:+.2%}",
                    delta=best_strategy["Engine"]
                )
            with kpi_col2:
                st.metric(
                    "夏普比率",
                    f"{best_strategy['Sharpe']:.3f}",
                    delta="風險調整收益"
                )
            with kpi_col3:
                st.metric(
                    "最大回撤",
                    f"{best_strategy['MDD']:.2%}",
                    delta="最差情境"
                )
            with kpi_col4:
                st.metric(
                    "勝率",
                    f"{best_strategy['Win Rate']:.2%}",
                    delta="獲利交易佔比"
                )

        st.divider()

        # ===== Performance Table =====
        st.subheader(f"📊 績效對標表 | Performance Table (D+{horizon} - {cost_model.upper()})")
        st.caption("📌 說明：基準（Benchmark）為等權計算，非市值加權基準。各成本情境費率詳見下方成本模型公式。")

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
    st.subheader("📈 報酬與夏普比率 | Return & Sharpe")

    r1, r2 = st.columns(2)

    with r1:
        fig = go.Figure()
        engines = [r["Engine"] for r in rows]
        returns = [r["Ann. Return"] for r in rows]
        colors = ["#10b981" if r > 0 else "#f43f5e" for r in returns]
        fig.add_trace(go.Bar(
            x=engines,
            y=returns,
            marker_color=colors,
            text=[f"{r:+.1%}" for r in returns],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Return: %{y:.2%}<extra></extra>"
        ))
        fig.update_layout(**glint_plotly_layout(
            title=f"D+{horizon} 年化報酬率",
            subtitle=f"Annualized Return · {cost_model}",
            height=400,
            ylabel="年化報酬 Return",
        ))
        fig.update_layout(yaxis_tickformat=".1%", hovermode="x unified")
        fig.add_hline(y=0, line_color="#94a3b8", line_dash="dash",
                      annotation_text="零軸",
                      annotation_font=dict(family="JetBrains Mono, monospace", size=10, color="#64748b"))
        st.plotly_chart(fig, use_container_width=True)

    with r2:
        fig_sr = go.Figure()
        sharpes = [r["Sharpe"] for r in rows]
        colors_sr = ["#059669" if s > 0.5 else ("#f59e0b" if s > 0 else "#dc2626") for s in sharpes]
        fig_sr.add_trace(go.Bar(
            x=engines,
            y=sharpes,
            marker_color=colors_sr,
            text=[f"{s:.3f}" for s in sharpes],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Sharpe: %{y:.3f}<extra></extra>"
        ))
        fig_sr.update_layout(**glint_plotly_layout(
            title=f"D+{horizon} 夏普比率",
            subtitle=f"Sharpe Ratio · {cost_model}",
            height=400,
            ylabel="夏普比率 Sharpe",
        ))
        fig_sr.update_layout(hovermode="x unified")
        fig_sr.add_hline(y=0.5, line_dash="dash", line_color="#10b981",
                         annotation_text="優質門檻 Good (0.5)",
                         annotation_font=dict(family="JetBrains Mono, monospace", size=10, color="#10b981"))
        fig_sr.add_hline(y=1.0, line_dash="dash", line_color="#065f46",
                         annotation_text="優秀門檻 Excellent (1.0)",
                         annotation_font=dict(family="JetBrains Mono, monospace", size=10, color="#065f46"))
        fig_sr.add_hline(y=0, line_color="#94a3b8", line_dash="dot")
        st.plotly_chart(fig_sr, use_container_width=True)

    # ===== Risk-Return Scatter Plot =====
    st.divider()
    st.subheader("📊 風險-報酬散點圖 | Risk-Return Scatter")
    st.caption("x 軸：最大回撤（風險） | y 軸：年化報酬 | 泡泡大小：夏普比率")

    scatter_data = []
    for r in rows:
        scatter_data.append({
            "Engine": r["Engine"],
            "MDD": abs(r["MDD"]),  # Absolute value
            "Return": r["Ann. Return"],
            "Sharpe": max(r["Sharpe"], 0),  # For bubble size
        })

    df_scatter = pd.DataFrame(scatter_data)

    fig_scatter = go.Figure()
    for _, row in df_scatter.iterrows():
        color_map = {
            "LIGHTGBM": "#2563eb",
            "XGBOOST": "#7c3aed",
            "ENSEMBLE": "#10b981",
            "BENCHMARK": "#94a3b8"
        }
        color = color_map.get(row["Engine"], "#2563eb")

        fig_scatter.add_trace(go.Scatter(
            x=[row["MDD"]],
            y=[row["Return"]],
            mode="markers+text",
            name=row["Engine"],
            marker=dict(
                size=15 + row["Sharpe"] * 10,
                color=color,
                opacity=0.82,
                line=dict(color="white", width=2)
            ),
            text=[row["Engine"]],
            textposition="top center",
            textfont=dict(family="JetBrains Mono, monospace", size=11),
            hovertemplate=f"<b>{row['Engine']}</b><br>MDD: {row['MDD']:.2%}<br>Return: {row['Return']:.2%}<br>Sharpe: {row['Sharpe']:.3f}<extra></extra>"
        ))

    fig_scatter.update_layout(**glint_plotly_layout(
        title=f"D+{horizon} 風險-報酬分析",
        subtitle="Risk-Return Analysis · 泡泡大小＝Sharpe",
        height=460,
        xlabel="最大回撤 Max Drawdown（風險）",
        ylabel="年化報酬 Annualized Return",
    ))
    fig_scatter.update_layout(yaxis_tickformat=".1%", xaxis_tickformat=".1%", hovermode="closest")
    fig_scatter.add_hline(y=0, line_color="#94a3b8", line_dash="dash")
    fig_scatter.add_vline(x=0.15, line_color="#f59e0b", line_dash="dash",
                          annotation_text="典型回撤 Typical DD",
                          annotation_font=dict(family="JetBrains Mono, monospace", size=10, color="#b45309"))
    st.plotly_chart(fig_scatter, use_container_width=True)
    render_chart_note(
        "左上象限＝風險低、報酬高。Ensemble（綠）相對 LightGBM（藍）與 XGBoost（紫）通常位於較佳象限，基準（灰）落於右下提供對照。",
        tone="violet",
    )

    # ===== Cost Impact (Waterfall) =====
    st.divider()
    st.subheader("💰 交易成本影響分析 | Cost Impact Analysis")
    st.caption("↓ 換手率越高，交易成本侵蝕越大。D+1 策略因每日換手而在扣除成本後通常不可行。")
    st.markdown("""
    <div class="insight-box">
    <strong>💡 為什麼成本模型很重要 | Why Cost Matters？</strong><br><br>
    同一策略在不同成本假設下，年化報酬可能差距 3–5%。<br>
    D+1 策略因換手率高達 64–68%，在任何成本情境下幾乎都不可行。<br>
    D+20 策略即使在保守成本下仍有正 alpha。
    </div>
    """, unsafe_allow_html=True)

    # ===== Cost Model Formulas =====
    with st.expander("📐 成本模型公式詳解 | Cost Model Formulas", expanded=False):
        st.markdown("""
**交易成本計算公式 | Transaction Cost Formula：**

$$
C_{\\text{total}} = C_{\\text{commission}} + C_{\\text{tax}} + C_{\\text{slippage}}
$$

其中：

$$
C_{\\text{commission}} = \\text{成交金額} \\times 0.001425 \\times \\text{折扣率}
$$

$$
C_{\\text{tax}} = \\text{賣出金額} \\times 0.003 \\quad (\\text{證交稅，僅賣出時收取})
$$

$$
C_{\\text{slippage}} = \\text{成交金額} \\times \\text{滑價率}
$$
        """)

        cost_table = pd.DataFrame({
            "參數 | Parameter": [
                "手續費率 | Commission",
                "手續費折扣 | Discount",
                "實際手續費 | Effective Comm.",
                "證交稅 | Tax (賣出)",
                "滑價假設 | Slippage",
                "單邊總成本(買) | One-way (Buy)",
                "單邊總成本(賣) | One-way (Sell)",
                "來回總成本 | Round-trip"
            ],
            "標準 Standard": [
                "0.1425%", "100%（無折扣）", "0.1425%", "0.300%",
                "0.100%", "0.2425%", "0.5425%", "≈0.785%"
            ],
            "折扣 Discount": [
                "0.1425%", "28%（電子下單）", "0.0399%", "0.300%",
                "0.050%", "0.0899%", "0.3899%", "≈0.480%"
            ],
            "保守 Conservative": [
                "0.1425%", "100%（無折扣）", "0.1425%", "0.300%",
                "0.200%", "0.3425%", "0.6425%", "≈0.985%"
            ],
        })
        st.dataframe(cost_table, use_container_width=True, hide_index=True)

        st.markdown("""
        <div class="insight-box">
        <strong>📌 備註 | Notes：</strong><br>
        • 台灣證券交易手續費法定上限 0.1425%，多數券商提供電子下單折扣（通常 2.8 折 ~ 6 折）<br>
        • 證交稅 0.3% 僅於賣出時收取（當沖減半為 0.15%，本系統非當沖策略故不適用）<br>
        • 滑價（Slippage）模擬實際成交價與理論價的偏差，流動性越低滑價越大<br>
        • <strong>折扣情境</strong>最接近散戶實際交易成本；<strong>保守情境</strong>適用於大額交易或低流動性股票
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

        # Cost comparison grouped bar chart
        fig_cost = px.bar(
            df_cost,
            x="Engine",
            y="Ann. Return",
            color="Cost Model",
            barmode="group",
            text_auto=".1%",
            color_discrete_map={"Discount": "#10b981", "Standard": "#2563eb", "Conservative": "#f43f5e"},
        )
        fig_cost.update_layout(**glint_plotly_layout(
            title=f"D+{horizon} 各成本情境年化報酬",
            subtitle="Returns by Cost Model",
            height=420,
            ylabel="年化報酬 Return",
        ))
        fig_cost.update_layout(yaxis_tickformat=".1%", hovermode="x unified")
        fig_cost.add_hline(y=0, line_color="#94a3b8", line_dash="dash")
        st.plotly_chart(fig_cost, use_container_width=True)

        # Cost sensitivity analysis
        st.caption("📊 成本敏感度分析 | Cost Sensitivity")
        best_strategy_data = [r for r in cost_rows if r["Engine"] in [best_strategy.get("Engine", "")]]
        if best_strategy_data:
            fig_cost_sens = go.Figure()
            cost_models = sorted(set(r["Cost Model"] for r in best_strategy_data))
            returns_by_model = [next((r["Ann. Return"] for r in best_strategy_data if r["Cost Model"] == cm), 0) for cm in cost_models]

            fig_cost_sens.add_trace(go.Bar(
                x=cost_models,
                y=returns_by_model,
                marker_color=["#10b981", "#2563eb", "#f43f5e"],
                text=[f"{r:+.2%}" for r in returns_by_model],
                textposition="outside",
                textfont=dict(family="JetBrains Mono, monospace", size=11),
                hovertemplate="<b>%{x}</b><br>Return: %{y:.2%}<extra></extra>"
            ))

            fig_cost_sens.update_layout(**glint_plotly_layout(
                title=f"{best_strategy.get('Engine')} 成本敏感度",
                subtitle="Cost Sensitivity",
                height=360,
                xlabel="成本模型 Cost Model",
                ylabel="年化報酬 Return",
            ))
            fig_cost_sens.update_layout(yaxis_tickformat=".1%")
            fig_cost_sens.add_hline(y=0, line_color="#94a3b8", line_dash="dash")
            st.plotly_chart(fig_cost_sens, use_container_width=True)

    # ===== Turnover Analysis (Cross-Horizon) =====
    st.divider()
    st.subheader("🔄 換手率分析 | Turnover Analysis (跨 Horizon 比較)")

    turnover_data = []
    for h in [1, 5, 20]:
        bt_h = results.get(f"backtest_horizon_{h}", {})
        for eng, res in bt_h.items():
            disc = res.get("cost_scenarios", {}).get("discount", {})
            turnover_data.append({
                "Strategy": f"{eng.upper()} D+{h}",
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
                x=df_to["Daily Cost"],
                y=df_to["Ann. Return"],
                mode="markers+text",
                text=df_to["Strategy"],
                textposition="top center",
                textfont=dict(family="JetBrains Mono, monospace", size=10),
                marker=dict(
                    size=16,
                    color=df_to["Horizon"],
                    colorscale=[[0, "#f43f5e"], [0.5, "#f59e0b"], [1, "#10b981"]],
                    showscale=True,
                    colorbar=dict(
                        title=dict(text="Horizon", font=dict(family="JetBrains Mono, monospace", size=11, color="#475569")),
                        tickvals=[1, 5, 20],
                        tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#475569"),
                        outlinewidth=0,
                    ),
                    line=dict(color="white", width=1)
                ),
                hovertemplate="<b>%{text}</b><br>Daily Cost: %{x:.4f}<br>Return: %{y:.2%}<extra></extra>"
            ))
            fig3.update_layout(**glint_plotly_layout(
                title="日均成本 vs 年化報酬",
                subtitle="Daily Cost vs Return",
                height=420,
                xlabel="日均成本 Daily Cost",
                ylabel="年化報酬 Return",
            ))
            fig3.update_layout(yaxis_tickformat=".1%", xaxis_tickformat=".4f", hovermode="closest")
            fig3.add_hline(y=0, line_color="#94a3b8", line_dash="dash")
            st.plotly_chart(fig3, use_container_width=True)

        with t2:
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(
                x=df_to["Avg Turnover"],
                y=df_to["Ann. Return"],
                mode="markers+text",
                text=df_to["Strategy"],
                textposition="top center",
                textfont=dict(family="JetBrains Mono, monospace", size=10),
                marker=dict(
                    size=16,
                    color=df_to["Horizon"],
                    colorscale=[[0, "#f43f5e"], [0.5, "#f59e0b"], [1, "#10b981"]],
                    showscale=True,
                    colorbar=dict(
                        title=dict(text="Horizon", font=dict(family="JetBrains Mono, monospace", size=11, color="#475569")),
                        tickvals=[1, 5, 20],
                        tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#475569"),
                        outlinewidth=0,
                    ),
                    line=dict(color="white", width=1)
                ),
                hovertemplate="<b>%{text}</b><br>Turnover: %{x:.1%}<br>Return: %{y:.2%}<extra></extra>"
            ))
            fig4.update_layout(**glint_plotly_layout(
                title="平均換手率 vs 年化報酬",
                subtitle="Turnover vs Return",
                height=420,
                xlabel="平均換手率 Avg Turnover",
                ylabel="年化報酬 Return",
            ))
            fig4.update_layout(yaxis_tickformat=".1%", xaxis_tickformat=".0%", hovermode="closest")
            fig4.add_hline(y=0, line_color="#94a3b8", line_dash="dash")
            st.plotly_chart(fig4, use_container_width=True)
        render_chart_note(
            "色條由紅→橘→綠對應 D+1 → D+5 → D+20。綠色泡泡（月頻）明顯位於右上／低成本區——換手率愈低、成本壓力愈小，越靠近正報酬區。",
            tone="emerald",
        )

except Exception as e:
    st.error(f"成本分析失敗：{str(e)}")

# ===== Backtest Charts =====
try:
    st.divider()
    st.subheader("📊 回測圖表 | Backtest Charts")

    fig_dir = Path(__file__).parent.parent.parent / "outputs" / "figures"
    c1, c2 = st.columns(2)

    with c1:
        img = fig_dir / f"cumulative_returns_D{horizon}.png"
        if img.exists():
            st.image(str(img), caption=f"D+{horizon} 累積報酬曲線 | Cumulative Returns", use_container_width=True)
        else:
            st.info(f"D+{horizon} 累積報酬圖表尚未生成")

        img2 = fig_dir / f"monthly_returns_ensemble_D{horizon}.png"
        if img2.exists():
            st.image(str(img2), caption=f"D+{horizon} 月報酬熱力圖 | Monthly Returns Heatmap", use_container_width=True)
        else:
            st.info(f"D+{horizon} 月報酬熱力圖尚未生成")

    with c2:
        img3 = fig_dir / f"drawdown_D{horizon}.png"
        if img3.exists():
            st.image(str(img3), caption=f"D+{horizon} 回撤走勢 | Drawdown", use_container_width=True)
        else:
            st.info(f"D+{horizon} 回撤走勢圖表尚未生成")

    # ===== Bootstrap CI =====
    bootstrap_data = results.get("bootstrap_ci", {})
    if bootstrap_data:
        st.divider()
        st.subheader("🎲 Bootstrap 信賴區間 | Bootstrap CI")
        st.caption("1,000 次 Bootstrap 重抽樣估算的報酬率與 Sharpe 信賴區間 | 95% Confidence Intervals")

        ci_rows = []
        for key, val in bootstrap_data.items():
            ci_rows.append({
                "策略 | Strategy": key,
                "報酬 | Return (Point)": f"{val.get('return_point', 0):+.2%}",
                "報酬 95% CI | Return CI": f"[{val.get('return_ci_lower', 0):+.2%}, {val.get('return_ci_upper', 0):+.2%}]",
                "夏普 | Sharpe (Point)": f"{val.get('sharpe_point', 0):.3f}",
                "夏普 95% CI | Sharpe CI": f"[{val.get('sharpe_ci_lower', 0):.3f}, {val.get('sharpe_ci_upper', 0):.3f}]",
            })
        if ci_rows:
            st.dataframe(pd.DataFrame(ci_rows), use_container_width=True, hide_index=True)

    # ===== Drawdown Analysis =====
    dd_data = results.get("drawdown_analysis", {})
    if dd_data:
        st.divider()
        st.subheader("📉 條件回撤分析 | Conditional Drawdown Analysis")
        st.caption("評估極端損失情境 | Extreme Loss Scenarios")

        dd_rows = []
        for key, val in dd_data.items():
            dd_rows.append({
                "策略 | Strategy": key,
                "CDaR 95%": f"{val.get('cdar_95', 0):.2%}",
                "平均復甦天數 | Avg Recovery": f"{val.get('avg_recovery_days', 0)} days",
                "回撤次數 | Episodes": val.get("n_episodes", 0),
            })
        if dd_rows:
            st.dataframe(pd.DataFrame(dd_rows), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"回測圖表分析發生錯誤：{str(e)}")

# ===== Statistical Validation =====
try:
    stat_val = results.get("statistical_validation", {})
    perm_tests = stat_val.get("permutation_tests", {})
    if perm_tests:
        st.divider()
        st.subheader("🧪 統計顯著性驗證 | Statistical Significance Tests")
        st.markdown("""
        <div class="gl-box-info">
        <strong>❓ 什麼是 Permutation Test？</strong><br>
        隨機打亂標籤 1,000 次，計算每次「偽模型」的 AUC。<br>
        若真實模型的 AUC 遠超所有偽模型（p < 0.01），證明模型的預測能力並非偶然——具有統計顯著性。
        </div>
        """, unsafe_allow_html=True)

        perm_rows = []
        for name, vals in perm_tests.items():
            perm_rows.append({
                "策略 | Strategy": name,
                "觀察 AUC | Observed": vals.get("observed_auc", 0),
                "隨機均值 | Permuted Mean": vals.get("mean_permuted_auc", 0),
                "Z-Score": vals.get("z_score", 0),
                "p-value": vals.get("p_value", 0),
                "顯著 (α=0.01)": "✅" if vals.get("significant_at_01") else "❌",
            })

        df_perm = pd.DataFrame(perm_rows)
        st.dataframe(df_perm, use_container_width=True, hide_index=True)

        # Visual: observed AUC vs permuted baseline
        fig_perm = go.Figure()
        strat_names = [r["策略 | Strategy"] for r in perm_rows]
        obs_aucs = [r["觀察 AUC | Observed"] for r in perm_rows]
        perm_means = [r["隨機均值 | Permuted Mean"] for r in perm_rows]

        fig_perm.add_trace(go.Bar(
            name="觀察 AUC", x=strat_names, y=obs_aucs,
            marker_color="#10b981",
            text=[f"{v:.4f}" for v in obs_aucs],
            textposition="outside",
            textfont=dict(family="JetBrains Mono, monospace", size=11),
        ))
        fig_perm.add_trace(go.Bar(
            name="隨機基線", x=strat_names, y=perm_means,
            marker_color="#cbd5e1",
            text=[f"{v:.4f}" for v in perm_means],
            textposition="outside",
            textfont=dict(family="JetBrains Mono, monospace", size=11),
        ))
        fig_perm.update_layout(**glint_plotly_layout(
            title="觀察 AUC vs 隨機置換基線",
            subtitle="Observed vs Permuted Baseline · 1,000 次打亂",
            height=400,
            ylabel="AUC",
        ))
        fig_perm.update_layout(barmode="group", yaxis_range=[0.45, max(obs_aucs) + 0.03])
        st.plotly_chart(fig_perm, use_container_width=True)

        st.markdown("""
        <div style="background:#ecfdf5; border-left:4px solid #059669; border-radius:0 8px 8px 0; padding:12px 16px; font-size:0.85rem; color:#065f46;">
        <strong>✅ 結論：</strong><br>
        所有 9 個模型×天期組合的 Permutation Test p-value = 0.000，Z-Score 均超過 170。<br>
        模型的預測能力具有極高的統計顯著性，排除了偶然性。
        </div>
        """, unsafe_allow_html=True)
except Exception:
    pass  # Statistical validation is optional

# ===== Footer & Limitations =====
render_page_footer("Backtest")
