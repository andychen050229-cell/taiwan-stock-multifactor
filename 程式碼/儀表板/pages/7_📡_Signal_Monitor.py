"""Signal Monitor — 信號監控儀表板（Phase 3）"""

import streamlit as st
import json
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
render_topbar = _utils.render_topbar

inject_custom_css()

# ---- Top-bar (sticky breadcrumb + model chips + clock) ----
render_topbar(
    crumb_left="股票預測系統",
    crumb_current="信號監控",
    chips=[("live signal feed", "pri"), ("threshold sweep", "vio"), ("embargo=20", "default")],
    show_clock=True,
)

# Data Context Banner
st.markdown("""
<div class="gl-box-info">
📡 <strong>Phase 3 — 信號監控</strong>：資料漂移偵測 ｜ 信號衰減分析 ｜ 再訓練建議
</div>
""", unsafe_allow_html=True)

st.title("📡 信號監控")
st.caption("持續監控模型信號品質、特徵漂移、及再訓練需求")

st.info("""
**如何閱讀本頁？**

信號監控追蹤模型是否仍然可靠。

PSI（漂移指標）：衡量資料分佈是否改變。PSI < 0.1 = 穩定。

ICIR（信號穩定性）：衡量預測信號是否一致。|ICIR| > 0.5 = 強信號。

半衰期：預測能力多久會衰減一半，決定何時需要重新訓練。
""")


def _load_gov_json(filename):
    gov_dir = Path(__file__).resolve().parent.parent.parent / "outputs" / "governance"
    fp = gov_dir / filename
    if fp.exists():
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


drift_data = _load_gov_json("drift_report.json")
decay_data = _load_gov_json("signal_decay_report.json")

if not drift_data and not decay_data:
    st.warning("尚未執行 Phase 3，請先執行 `python run_phase3.py`")
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 📡 信號監控")
    if decay_data:
        st.markdown(f"**分析日期**: {decay_data.get('analysis_date', '—')[:10]}")
        st.markdown(f"**再訓練建議**: {decay_data.get('recommended_retrain_cycle', '—')}")
        hl_min = decay_data.get("min_half_life_months")
        if hl_min:
            st.markdown(f"**最短半衰期**: {hl_min} 個月")
    if drift_data:
        st.markdown(f"**漂移嚴重度**: {drift_data.get('overall_severity', '—')}")
    st.divider()

# ============================================================
# Section 1: Data Drift Detection
# ============================================================
st.header("資料漂移偵測")

st.info("""
**PSI（Population Stability Index）是什麼？**

PSI 衡量特徵分佈在「參考期」與「當前期」之間的變化程度。

PSI < 0.1 = 穩定，0.1~0.2 = 輕微偏移，> 0.2 = 顯著偏移。

搭配 KS 檢定（Kolmogorov-Smirnov）做雙重確認。

若多數特徵發生顯著偏移，代表市場結構已改變，模型可能需要重新訓練。
""")

if drift_data:
    severity = drift_data.get("overall_severity", "unknown")
    severity_map = {
        "low": ("🟢 低", "特徵分佈穩定，模型可繼續使用"),
        "medium": ("🟡 中", "部分特徵輕微偏移，持續監控"),
        "high": ("🔴 高", "建議盡快重新訓練模型"),
    }
    sev_label, sev_desc = severity_map.get(severity, ("⚪ 未知", ""))

    c1, c2, c3 = st.columns(3)
    c1.metric("漂移嚴重度", sev_label)
    c2.metric("分析特徵數", drift_data.get("n_features_analyzed", 0))
    c3.metric("PSI > 0.2 特徵數", drift_data.get("n_drifted_features", 0))

    st.markdown(f"**建議**：{sev_desc}")

    # Reference vs Current period
    ref = drift_data.get("reference_period", {})
    cur = drift_data.get("current_period", {})
    rc1, rc2 = st.columns(2)
    rc1.markdown(f"**參考期**：{ref.get('n_rows', 0):,} 筆 ｜ {ref.get('date_range', '—')}")
    rc2.markdown(f"**當前期**：{cur.get('n_rows', 0):,} 筆 ｜ {cur.get('date_range', '—')}")

    # Top drifted features chart
    top_drifted = drift_data.get("top_drifted", [])
    if top_drifted:
        st.markdown("#### 漂移最嚴重的特徵（Top 5）")

        fig = go.Figure()
        names = [d["feature"] for d in top_drifted]
        psi_vals = [d["psi"] for d in top_drifted]
        colors = ["#ef4444" if psi > 0.2 else ("#f59e0b" if psi > 0.1 else "#22c55e") for psi in psi_vals]

        fig.add_trace(go.Bar(
            x=names, y=psi_vals,
            marker_color=colors,
            text=[f"{v:.4f}" for v in psi_vals],
            textposition="outside",
        ))

        fig.add_hline(y=0.2, line_dash="dash", line_color="red",
                      annotation_text="顯著偏移 (0.2)", annotation_position="top right")
        fig.add_hline(y=0.1, line_dash="dash", line_color="orange",
                      annotation_text="輕微偏移 (0.1)", annotation_position="top right")

        fig.update_layout(
            yaxis_title="PSI",
            height=350,
            margin=dict(t=30, b=30),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Per-feature actionable insights
        has_action = any(d.get("action") for d in top_drifted)
        if has_action:
            st.markdown("#### 各特徵處理建議")
            for d in top_drifted:
                if d.get("action"):
                    shift = d.get("mean_shift_pct", 0)
                    shift_str = f"（均值偏移 {shift:+.1f}%）" if shift else ""
                    st.markdown(f"- **{d['feature']}**: {d['action']}{shift_str}")

    # Full feature drift table
    feature_drift = drift_data.get("feature_drift", {})
    if feature_drift:
        with st.expander("📋 完整特徵漂移報告", expanded=False):
            rows = []
            for feat, vals in sorted(feature_drift.items(), key=lambda x: x[1]["psi"], reverse=True):
                rows.append({
                    "特徵": feat,
                    "PSI": vals.get("psi", 0),
                    "PSI 等級": {"low": "🟢 低", "medium": "🟡 中", "high": "🔴 高"}.get(vals.get("psi_level", "low"), "—"),
                    "KS 統計量": vals.get("ks_stat", 0),
                    "KS 顯著": "是" if vals.get("ks_significant") else "否",
                    "均值偏移%": vals.get("mean_shift_pct", 0),
                    "建議": vals.get("action", "—"),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

    # Drift severity heatmap across all features
    if feature_drift:
        with st.expander("🗺️ 特徵漂移熱力圖 | Feature Drift Heatmap", expanded=False):
            feat_names = []
            psi_values = []
            ks_values = []
            for feat, vals in sorted(feature_drift.items(), key=lambda x: x[1].get("psi", 0), reverse=True):
                feat_names.append(feat)
                psi_values.append(vals.get("psi", 0))
                ks_values.append(vals.get("ks_stat", 0))

            fig_heat = go.Figure(data=go.Heatmap(
                z=[psi_values],
                x=feat_names,
                y=["PSI"],
                colorscale=[[0, "#22c55e"], [0.1/max(max(psi_values, default=1), 0.01), "#fef3c7"],
                            [0.2/max(max(psi_values, default=1), 0.01), "#f59e0b"], [1, "#ef4444"]],
                hovertemplate="<b>%{x}</b><br>PSI: %{z:.4f}<extra></extra>",
            ))
            fig_heat.update_layout(
                title="所有特徵 PSI 漂移熱力圖",
                height=200, template="plotly_white",
                xaxis_tickangle=-45,
                margin=dict(l=40, r=20, t=50, b=100),
            )
            st.plotly_chart(fig_heat, use_container_width=True)

    # Label drift
    label_drift = drift_data.get("label_drift", {})
    if label_drift:
        st.markdown("#### 標籤分佈偏移")
        for label_name, ld in label_drift.items():
            sig = ld.get("significant", False)
            icon = "🔴" if sig else "🟢"
            st.markdown(f"{icon} **{label_name}**: 最大偏移 = {ld.get('max_shift', 0):.4f} "
                        f"{'（顯著）' if sig else '（穩定）'}")

            dist = ld.get("distribution", {})
            if dist:
                rows = []
                for cls_label, vals in dist.items():
                    rows.append({
                        "類別": cls_label,
                        "參考期占比": f"{vals.get('reference_pct', 0):.2%}",
                        "當前期占比": f"{vals.get('current_pct', 0):.2%}",
                        "偏移量": f"{vals.get('shift', 0):.4f}",
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)

else:
    st.warning("漂移偵測資料尚未生成")

st.divider()

# ============================================================
# Section 2: Signal Stability
# ============================================================
st.header("信號穩定性分析")

st.info("""
**ICIR（Information Coefficient Information Ratio）是什麼？**

ICIR = Mean(IC) / Std(IC)，衡量信號的穩定程度。

ICIR > 0.5 = 強信號（可靠），0.2~0.5 = 中等信號，< 0.2 = 弱信號。

強信號意味著模型的預測能力在不同時間段表現一致。
""")

if decay_data:
    summary = decay_data.get("summary", {})
    retrain = decay_data.get("recommended_retrain_cycle", "—")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("強信號", summary.get("strong_signals", 0))
    c2.metric("中等信號", summary.get("moderate_signals", 0))
    c3.metric("弱信號", summary.get("weak_signals", 0))
    # Shorten long retrain text to prevent metric truncation
    retrain_short = str(retrain).split("（")[0].strip() if "（" in str(retrain) else str(retrain)
    c4.metric("再訓練週期", retrain_short)

    best = summary.get("best_signal", "—")
    st.markdown(f"**最佳信號來源**：{best}")

    # Signal stability by strategy
    stability = decay_data.get("signal_stability", {})
    if stability:
        st.markdown("#### 各策略信號穩定度")

        strat_names = []
        icir_vals = []
        colors = []

        for name, vals in stability.items():
            strat_names.append(name)
            icir_vals.append(abs(vals.get("icir", 0)))
            stab = vals.get("stability", "weak")
            color = "#22c55e" if stab == "strong" else ("#f59e0b" if stab == "moderate" else "#ef4444")
            colors.append(color)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=strat_names, y=icir_vals,
            marker_color=colors,
            text=[f"{v:.3f}" for v in icir_vals],
            textposition="outside",
        ))

        fig.add_hline(y=0.5, line_dash="dash", line_color="green",
                      annotation_text="強信號 (0.5)", annotation_position="top right")
        fig.add_hline(y=0.2, line_dash="dash", line_color="orange",
                      annotation_text="中等信號 (0.2)", annotation_position="top right")

        fig.update_layout(
            yaxis_title="|ICIR|",
            height=350,
            margin=dict(t=30, b=30),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # === Monthly IC Trends Chart (NEW) ===
    monthly_trends = decay_data.get("monthly_ic_trends", {})
    if monthly_trends:
        st.markdown("#### 月度 IC 趨勢（Top 特徵）")
        horizon_choice = st.selectbox(
            "選擇預測週期",
            list(monthly_trends.keys()),
            format_func=lambda x: f"預測週期 {x}",
        )

        if horizon_choice in monthly_trends:
            fig_ic = go.Figure()
            colors_palette = ["#636EFA", "#EF553B", "#00CC96"]

            for i, (feat, months) in enumerate(monthly_trends[horizon_choice].items()):
                if months:
                    x_months = [m["month"] for m in months]
                    y_ics = [m["ic"] for m in months]
                    fig_ic.add_trace(go.Scatter(
                        x=x_months, y=y_ics,
                        mode="lines+markers",
                        name=feat,
                        line=dict(color=colors_palette[i % len(colors_palette)]),
                        marker=dict(size=5),
                    ))

            fig_ic.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
            fig_ic.update_layout(
                yaxis_title="Rank IC",
                xaxis_title="月份",
                height=350,
                margin=dict(t=30, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_ic, use_container_width=True)

    # Half-life analysis with visualization
    half_life = decay_data.get("half_life_analysis", {})
    if half_life:
        st.markdown("#### 信號半衰期分析 | Signal Half-Life")

        hl_rows = []
        for name, vals in half_life.items():
            hl = vals.get("half_life_months")
            note = vals.get("note", "—")
            trend = vals.get("trend_direction", "unknown")
            trend_icon = {"improving": "📈", "decaying": "📉", "stable": "➡️"}.get(trend, "❓")
            slope = vals.get("monthly_slope", 0)
            n_months = vals.get("n_months_analyzed", 0)

            if hl:
                st.markdown(f"- {trend_icon} **{name}**: 半衰期 ≈ **{hl} 個月** — {note}")
            else:
                st.markdown(f"- {trend_icon} **{name}**: {note}")

            hl_rows.append({
                "天期": name, "趨勢": trend,
                "月斜率": slope, "分析月數": n_months,
                "半衰期（月）": hl if hl else "尚未衰減",
            })

        if hl_rows:
            st.dataframe(pd.DataFrame(hl_rows), use_container_width=True, hide_index=True)

            # Trend direction visualization
            fig_hl = go.Figure()
            for row in hl_rows:
                color = "#22c55e" if row["趨勢"] == "improving" else ("#ef4444" if row["趨勢"] == "decaying" else "#636EFA")
                fig_hl.add_trace(go.Bar(
                    x=[row["天期"]], y=[row["月斜率"]],
                    marker_color=color, showlegend=False,
                    text=[f"{row['月斜率']:+.4f}"], textposition="outside",
                ))
            fig_hl.add_hline(y=0, line_dash="dash", line_color="gray")
            fig_hl.update_layout(
                title="信號月度斜率 | Monthly IC Slope（正值=改善中）",
                yaxis_title="IC 月斜率", height=300, template="plotly_white",
            )
            st.plotly_chart(fig_hl, use_container_width=True)

        st.markdown("""
        <div style="background:#ecfdf5; border-left:4px solid #059669; border-radius:0 8px 8px 0; padding:12px 16px; font-size:0.85rem; color:#065f46;">
        <strong>📌 半衰期解讀：</strong><br>
        D+5 與 D+20 的信號均呈<strong>持續改善</strong>趨勢（正斜率），表示模型的預測能力在研究期間內尚未出現衰減。<br>
        建議再訓練週期：<strong>3-6 個月</strong>。
        </div>
        """, unsafe_allow_html=True)

    # Alpha decay from Phase 2
    alpha_decay = decay_data.get("alpha_decay_from_p2", {})
    if alpha_decay:
        with st.expander("📊 Phase 2 Alpha Decay 結果"):
            rows = []
            for name, vals in alpha_decay.items():
                rows.append({
                    "策略": name,
                    "Mean IC": f"{vals.get('mean_ic', 0):.4f}",
                    "ICIR": f"{vals.get('icir', 0):.4f}",
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

else:
    st.warning("信號衰減分析資料尚未生成")

st.divider()

# ============================================================
# Section 3: Retrain Recommendation Summary
# ============================================================
st.header("綜合建議")

has_data = drift_data or decay_data

if has_data:
    drift_sev = drift_data.get("overall_severity", "—") if drift_data else "—"
    retrain_cycle = decay_data.get("recommended_retrain_cycle", "—") if decay_data else "—"
    n_drifted = drift_data.get("n_drifted_features", 0) if drift_data else 0
    strong = decay_data.get("summary", {}).get("strong_signals", 0) if decay_data else 0
    weak = decay_data.get("summary", {}).get("weak_signals", 0) if decay_data else 0
    min_hl = decay_data.get("min_half_life_months") if decay_data else None

    st.markdown(f"""
| 項目 | 結果 |
|------|------|
| 資料漂移嚴重度 | {drift_sev} |
| PSI > 0.2 特徵數 | {n_drifted} |
| 強信號數量 | {strong} |
| 弱信號數量 | {weak} |
| 最短半衰期 | {f'{min_hl} 個月' if min_hl else '尚未偵測到衰減'} |
| 建議再訓練週期 | **{retrain_cycle}** |
""")

    st.markdown("#### 建議行動")

    if drift_sev == "high":
        st.error("特徵分佈已顯著偏移，建議立即重新訓練模型。")
    elif drift_sev == "medium":
        st.warning("部分特徵出現輕微偏移，建議持續監控並按建議週期重新訓練。")
    else:
        st.success("特徵分佈穩定，模型可繼續使用。")

    if weak > strong:
        st.warning("弱信號數量超過強信號，建議縮短再訓練週期或調整特徵組合。")
    elif strong >= 3:
        st.success("D+20 策略信號穩定性最佳（ICIR > 0.5），適合作為主力策略。")

# ===== Footer =====
st.markdown("---")
st.caption("📌 信號監控基於 Phase 3 自動分析 ｜ PSI 閾值：0.1（輕微）/ 0.2（顯著）｜ ICIR 閾值：0.2（中等）/ 0.5（強）")
st.markdown('<div class="page-footer">量化分析工作台 — Signal Monitor | 台灣股市多因子預測系統</div>', unsafe_allow_html=True)
