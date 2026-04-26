"""ICIR Analysis — 訊號穩定性分析（量化分析工作台）"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import importlib.util
import numpy as np
import json

_utils_path = Path(__file__).resolve().parent.parent / "utils.py"
_spec = importlib.util.spec_from_file_location("dashboard_utils", str(_utils_path))
_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils)
inject_custom_css = _utils.inject_custom_css
render_topbar = _utils.render_topbar
inject_advanced_sidebar = _utils.inject_advanced_sidebar
load_report = _utils.load_report
glint_plotly_layout = _utils.glint_plotly_layout
glint_styler_cmap = _utils.glint_styler_cmap
render_chart_note = _utils.render_chart_note
render_terminal_hero = _utils.render_terminal_hero
PAGE_EYEBROWS = _utils.PAGE_EYEBROWS
PAGE_TITLES = _utils.PAGE_TITLES
PAGE_BRIEFINGS = _utils.PAGE_BRIEFINGS
render_trust_strip = _utils.render_trust_strip
render_page_footer = _utils.render_page_footer
glint_icon = _utils.glint_icon
glint_heading = _utils.glint_heading

inject_custom_css()

# ---- Top-bar (sticky breadcrumb + model chips + clock) ----
render_topbar(
    crumb_left="多因子股票分析系統",
    crumb_current="ICIR 訊號穩定性",
    chips=[("Rank IC · 24 months", "pri"), ("purged WF · 4-fold", "vio"), ("IC > 0.015", "ok")],
    show_clock=True,
)

try:
    report, report_name = load_report()
    results = report["results"]
    inject_advanced_sidebar(report_name, report, current_page="icir_analysis")
except Exception as e:
    # v8 §18.4 · dark terminal error panel with schema hint
    _utils.render_error_from_copy_map("report_missing", exception=e)
    st.stop()

# v8 §12 · §20.3 — Dark terminal hero driven by centralised copy maps
render_terminal_hero(
    eyebrow=PAGE_EYEBROWS["icir"],
    title=PAGE_TITLES["icir"],
    briefing=PAGE_BRIEFINGS["icir"],
    chips=[
        ("ICIR usable", "> 0.5", "info"),
        ("ICIR excellent", "> 1.0", "ok"),
    ],
    tone="violet",
)
render_trust_strip([
    ("DATASET",  "2023/03 – 2025/03", "blue"),
    ("IC WINDOW", "≈ 500 交易日",      "cyan"),
    ("CV",        "Purged WF · 4 Folds", "violet"),
    ("TARGET",    "|ICIR| > 0.5",      "emerald"),
])

# 白話版資料產生說明
# v11 §4a — DATA PROVENANCE callout migrated from pastel teal to dark-glint.
st.markdown("""
<div style="
    background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(10,20,32,0.92) 100%);
    border: 1px solid rgba(103,232,249,0.32);
    border-left: 3px solid #67e8f9;
    border-radius: 12px;
    padding: 18px 22px;
    margin: 14px 0;
    box-shadow: 0 4px 14px rgba(2,6,23,0.28), inset 0 1px 0 rgba(103,232,249,0.12);
">
    <div style="
        display: inline-block; background: rgba(103,232,249,0.22); color: #67e8f9;
        border: 1px solid rgba(103,232,249,0.40);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem; font-weight: 800; letter-spacing: 0.16em;
        padding: 3px 10px; border-radius: 5px; margin-bottom: 10px;
        text-shadow: 0 0 8px rgba(103,232,249,0.35);
    ">資料怎麼來? · DATA PROVENANCE</div>
    <div style="font-size: 0.95rem; color: #cfe2ee; line-height: 1.85;">
        <strong style="color: #e8f7fc;">這一頁的 ICIR 數字怎麼算出來的?</strong><br>
        ① 先對每個交易日算出<strong style="color:#e8f7fc;">模型預測排序</strong>和<strong style="color:#e8f7fc;">實際報酬排序</strong>的相關性(Rank IC);<br>
        ② 把過去 ~500 個交易日的 Rank IC 收集起來,算出平均值與標準差;<br>
        ③ <code style="background:rgba(103,232,249,0.16);border:1px solid rgba(103,232,249,0.32);color:#cffafe;padding:1px 6px;border-radius:4px;font-family:'JetBrains Mono',monospace;">ICIR = 平均 / 標準差</code>,像「訊號的夏普比率」。<br>
        <strong style="color: #67e8f9;">|ICIR| &gt; 0.5 → 訊號穩定可用</strong>;&gt; 1.0 為優秀。<br>
        D+20 通常優於 D+1,因為日內價格雜訊比月頻趨勢大得多。
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander("如何閱讀本頁?", expanded=False, icon=":material/info:"):
    st.markdown("""
- **IC**（Information Coefficient）衡量模型預測排序與實際報酬排序的相關性。
- **ICIR** = IC 的平均值 / IC 的標準差，類似「訊號的夏普比率」。
- **|ICIR| > 0.5** 表示預測訊號穩定可用，**> 1.0** 為優秀。
- **D+20** 的 ICIR 通常優於 D+1，因為短期價格雜訊較大。
""")

st.markdown(f"""
<div class="insight-box">
<strong style="display:inline-flex;align-items:center;gap:6px;color:var(--gl-violet);">
  {glint_icon("book-open", 15)} 什麼是 ICIR | What is ICIR？</strong><br><br>
ICIR 本質上是 IC 的 t-statistic。<br>
|ICIR| > 0.5 為良好訊號，> 1.0 為優秀。<br><br>
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
        glint_heading("target", "關鍵績效指標", "Key Metrics", tone="cyan")
        best_icir_row = max(icir_rows, key=lambda x: x["ICIR"])
        d20_rows = [r for r in icir_rows if "D+20" in r["Horizon"]]
        best_d20 = max(d20_rows, key=lambda x: x["ICIR"]) if d20_rows else None

        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        with kpi_col1:
            st.metric(
                "最佳 ICIR",
                f"{best_icir_row['ICIR']:.4f}",
                delta=best_icir_row["Engine"]
            )
        with kpi_col2:
            st.metric(
                "最佳天期",
                best_icir_row["Horizon"],
                delta="預測力最強"
            )
        with kpi_col3:
            if best_d20:
                st.metric(
                    "D+20 月度訊號",
                    f"{best_d20['ICIR']:.4f}",
                    delta="長期品質"
                )
        with kpi_col4:
            icir_threshold = 0.5
            above_threshold = sum(1 for r in icir_rows if r["ICIR"] > icir_threshold)
            st.metric(
                "優質訊號",
                f"{above_threshold}/{len(icir_rows)}",
                delta="ICIR > 0.5"
            )

        st.divider()

        # ===== ICIR 全景視圖 =====
        glint_heading("grid", "ICIR 全景視圖", "ICIR Overview", tone="blue")

        fig_main = go.Figure()
        for h, color in [("D+1", "#f43f5e"), ("D+5", "#a78bfa"), ("D+20", "#10b981")]:
            subset = df_icir[df_icir["Horizon"] == h]
            fig_main.add_trace(go.Bar(
                name=h,
                x=subset["Engine"],
                y=subset["ICIR"],
                marker_color=color,
                text=subset["ICIR"].apply(lambda x: f"{x:.4f}"),
                textposition="outside",
                textfont=dict(family="JetBrains Mono, monospace", size=11),
                hovertemplate="<b>%{x}</b><br>ICIR: %{y:.4f}<extra></extra>"
            ))

        fig_main.update_layout(**glint_plotly_layout(
            title="各引擎×天期 ICIR 對標",
            subtitle="ICIR by Engine × Horizon",
            height=460,
            ylabel="ICIR",
        ))
        fig_main.update_layout(barmode="group", hovermode="x unified")
        fig_main.add_hline(y=0.5, line_dash="dash", line_color="#10b981",
                           annotation_text="優質閾值 Good (0.5)",
                           annotation_font=dict(family="JetBrains Mono, monospace", size=10, color="#10b981"))
        fig_main.add_hline(y=1.0, line_dash="dash", line_color="#065f46",
                           annotation_text="優秀閾值 Excellent (1.0)",
                           annotation_font=dict(family="JetBrains Mono, monospace", size=10, color="#065f46"))
        fig_main.add_hline(y=0, line_dash="dot", line_color="rgba(103,232,249,0.40)")
        st.plotly_chart(fig_main, use_container_width=True)
        render_chart_note(
            "關鍵訊號：僅 <b>D+20</b> 地平線（綠柱）穩定站上零軸，<b>D+1/D+5</b>（紅/橘）普遍落於負區——驗證月頻才是可交易尺度。",
            tone="emerald",
        )

        st.dataframe(
            df_icir.style.background_gradient(
                subset=["ICIR"], cmap=glint_styler_cmap("diverging"), vmin=-0.15, vmax=0.10,
            ),
            use_container_width=True,
            hide_index=True
        )

        # ===== IC Distribution Histograms =====
        st.divider()
        glint_heading("bar-chart", "IC 分布直方圖", "IC Distribution", tone="violet")
        st.caption("Daily Rank IC 分佈特徵 — 評估訊號的穩定性與偏度")

        st.warning("⚠️ 以下圖表使用模擬數據（np.random）作為示意，非正式回測輸出。正式 IC/ICIR 數據請參考 Phase 2 報告。")

        dist_col1, dist_col2 = st.columns(2)

        # Simulated IC distribution (in real case, would load from data)
        with dist_col1:
            # D+1 vs D+20 distribution comparison
            np.random.seed(42)
            d1_ic = np.random.normal(-0.001, 0.025, 200)  # Noisy
            d20_ic = np.random.normal(0.008, 0.012, 200)  # Clean

            # v10 §10.1 · histograms go through glint_dark_hist_style — no
            # free-hex marker_color, so the two overlays share the canonical
            # dark terminal palette (secondary violet vs primary cyan).
            fig_dist = go.Figure()
            fig_dist.add_trace(go.Histogram(
                x=d1_ic,
                name="D+1 IC",
                nbinsx=30,
                marker=_utils.glint_dark_hist_style("secondary", opacity=0.60),
            ))
            fig_dist.add_trace(go.Histogram(
                x=d20_ic,
                name="D+20 IC",
                nbinsx=30,
                marker=_utils.glint_dark_hist_style("primary", opacity=0.60),
            ))
            fig_dist.update_layout(**glint_plotly_layout(
                title="短期 vs 長期 IC 分布",
                subtitle="D+1 vs D+20 Distribution · 模擬示意",
                height=400,
                xlabel="Daily Rank IC",
                ylabel="頻次 Frequency",
            ))
            fig_dist.update_layout(barmode="overlay",
                                   legend=_utils.glint_dark_legend("h", "bottom"))
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
                line=dict(color="#2563eb", width=2),
                marker=dict(size=7, color="#2563eb")
            ))

            # Diagonal reference line
            min_val = min(d1_perc.min(), d20_perc.min())
            max_val = max(d1_perc.max(), d20_perc.max())
            fig_qq.add_trace(go.Scatter(
                x=[min_val, max_val],
                y=[min_val, max_val],
                mode="lines",
                name="Reference (equal)",
                line=dict(color="rgba(103,232,249,0.45)", dash="dash")
            ))

            fig_qq.update_layout(**glint_plotly_layout(
                title="分位數比較",
                subtitle="Quantile-Quantile Plot",
                height=400,
                xlabel="D+1 IC Percentile",
                ylabel="D+20 IC Percentile",
            ))
            st.plotly_chart(fig_qq, use_container_width=True)

        # ===== Rolling ICIR (Simulated) =====
        st.divider()
        st.subheader("⏰ 滾動 ICIR 趨勢 | Rolling ICIR Evolution")
        st.caption("ICIR 在時間上的變化 — 反映訊號穩定性的動態")

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
            line=dict(color="#f43f5e", width=2),
            hovertemplate="<b>D+1</b><br>Date: %{x|%Y-%m-%d}<br>ICIR: %{y:.4f}<extra></extra>"
        ))
        fig_rolling.add_trace(go.Scatter(
            x=rolling_icir_d20.index,
            y=rolling_icir_d20.values,
            name="D+20 ICIR (30d MA)",
            line=dict(color="#10b981", width=2),
            hovertemplate="<b>D+20</b><br>Date: %{x|%Y-%m-%d}<br>ICIR: %{y:.4f}<extra></extra>"
        ))

        fig_rolling.update_layout(**glint_plotly_layout(
            title="30 日滾動 ICIR 趨勢",
            subtitle="30-Day Rolling ICIR · 模擬示意",
            height=400,
            xlabel="時間 Date",
            ylabel="ICIR",
        ))
        fig_rolling.update_layout(hovermode="x unified")
        fig_rolling.add_hline(y=0.5, line_dash="dash", line_color="#10b981",
                              annotation_text="優質閾值 0.5",
                              annotation_font=dict(family="JetBrains Mono, monospace", size=10, color="#10b981"))
        st.plotly_chart(fig_rolling, use_container_width=True)

        # ===== 頻率結構與實務建議 =====
        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            glint_heading("layers", "頻率結構分析", "Frequency Structure", tone="emerald")
            freq_data = pd.DataFrame({
                "天期 | Horizon": ["D+1", "D+5", "D+20"],
                "Rank IC 範圍": ["-0.006 ~ -0.001", "+0.008 ~ +0.025", "+0.013 ~ +0.015"],
                "ICIR 範圍": ["-0.124 ~ -0.094", "-0.126 ~ -0.071", "-0.035 ~ +0.036"],
                "AUC_macro (OOS)": ["~0.52", "~0.58", "0.64-0.65"],
                "訊號品質": ["❌ 噪音主導", "⚠️ 正向但薄弱", "✅ 月頻可用"],
                "可行性 | Feasibility": ["❌ 不可行", "⚠️ 邊際", "✅ 推薦（配合閾值過濾）"],
            })
            st.dataframe(freq_data, use_container_width=True, hide_index=True)

            st.markdown(f"""
            <div class="success-box">
            <strong style="display:inline-flex;align-items:center;gap:6px;color:var(--gl-emerald);">
              {glint_icon("target", 15)} 核心結論 | Key Finding（2026-04-19 嚴格 PIT 版）：</strong><br><br>
            月度頻率 <strong>D+20</strong> 是唯一 Rank IC 穩定為正的地平線
            （<span class="gl-mono">+0.013 ~ +0.015</span>），ICIR 雖因 std 較大而接近 0，
            但 AUC_macro 達 <span class="gl-mono">0.649</span>、
            Top 0.1% 精度 <span class="gl-mono">45.8%（edge +19.5pp）</span>，
            顯示分類訊號真實且可用。<br><br>
            日頻（D+1）與週頻（D+5）Rank IC 為負或接近零，信噪比不足以實際交易。
            </div>
            """, unsafe_allow_html=True)

        with col2:
            glint_heading("radar", "D+20 IC 關鍵統計", "D+20 Stats", tone="cyan", level=4)
            if d20_rows:
                for row in d20_rows:
                    st.metric(
                        f"{row['Engine']} D+20 ICIR",
                        f"{row['ICIR']:.4f}",
                        delta=f"IC={row['Mean IC']:.4f}"
                    )
                    st.caption(f"Std IC: {row['Std IC']:.4f}")

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
                            {"range": [0.3, 0.5], "color": "#ede9fe"},
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
        glint_heading("line-chart", "IC 時間序列圖表", "IC Time Series", tone="cyan")

        # Cloud shim chdir-safe: walk up 4 levels first (pages → 儀表板 → 程式碼 → project_root)
        _fig_here = Path(__file__).resolve()
        fig_dir = None
        for _c in (
            _fig_here.parent.parent.parent.parent / "outputs" / "figures",
            _fig_here.parent.parent.parent / "outputs" / "figures",
            Path.cwd() / "outputs" / "figures",
            Path.cwd().parent / "outputs" / "figures",
        ):
            if _c.exists():
                fig_dir = _c
                break
        fig_dir = fig_dir or (_fig_here.parent.parent.parent / "outputs" / "figures")
        ic_charts = sorted(fig_dir.glob("ic_timeseries_*.png"))
        if ic_charts:
            # Display each chart full-width inside an expander for clarity
            for chart in ic_charts:
                label = chart.stem.replace("ic_timeseries_", "IC: ").replace("_", " ")
                with st.expander(f"{label}", expanded=False, icon=":material/trending_up:"):
                    st.image(str(chart), use_container_width=True)
        else:
            st.info("IC 時間序列圖表尚未生成。請執行 run_phase2.py 產生。",
                    icon=":material/lightbulb:")

        # ===== Phase 3 Signal Stability Integration =====
        st.divider()
        glint_heading("target", "Phase 3 訊號穩定性評估", "Signal Stability Assessment", tone="emerald")
        st.caption("Phase 3 治理模組自動評估的訊號品質等級")

        try:
            _here = Path(__file__).resolve()
            _p3_report_dir = None
            for _c in (
                _here.parent.parent.parent.parent / "outputs" / "reports",  # project_root/outputs
                _here.parent.parent.parent / "outputs" / "reports",         # 程式碼/outputs (legacy)
                Path.cwd() / "outputs" / "reports",
                Path.cwd().parent / "outputs" / "reports",
                Path.cwd().parent.parent / "outputs" / "reports",
            ):
                if _c.exists():
                    _p3_report_dir = _c
                    break
            _p3_files = sorted(_p3_report_dir.glob("phase3_report_*.json"), reverse=True) if _p3_report_dir else []
            if _p3_files:
                with open(_p3_files[0], "r", encoding="utf-8") as _f:
                    _p3 = json.load(_f)
                _sig_stability = _p3.get("results", {}).get("step4_signal_decay", {}).get("signal_stability", {})
                _hl_data = _p3.get("results", {}).get("step4_signal_decay", {}).get("half_life_analysis", {})
                _retrain = _p3.get("results", {}).get("step4_signal_decay", {}).get("recommended_retrain_cycle", "—")

                if _sig_stability:
                    stab_rows = []
                    for name, vals in _sig_stability.items():
                        stab = vals.get("stability", "weak")
                        stab_icon = {"strong": "🟢 強", "moderate": "🟡 中", "weak": "🔴 弱"}.get(stab, "⚪")
                        stab_rows.append({
                            "策略 | Strategy": name,
                            "|ICIR|": abs(vals.get("icir", 0)),
                            "穩定性等級 | Stability": stab_icon,
                        })

                    df_stab = pd.DataFrame(stab_rows)
                    strong_ct = sum(1 for r in stab_rows if "強" in r["穩定性等級 | Stability"])

                    s_kpi1, s_kpi2 = st.columns(2)
                    with s_kpi1:
                        st.metric("強訊號數量", f"{strong_ct}/{len(stab_rows)}")
                    with s_kpi2:
                        # Shorten long retrain text for metric display
                        retrain_short = str(_retrain).split("（")[0].strip() if "（" in str(_retrain) else str(_retrain)
                        st.metric("再訓練週期", retrain_short)

                    st.dataframe(df_stab, use_container_width=True, hide_index=True)

                    # Half-life summary
                    if _hl_data:
                        _trend_icons = {
                            "improving": ("trending-up", "var(--gl-emerald)"),
                            "decaying":  ("activity",    "var(--gl-rose)"),
                            "stable":    ("line-chart",  "var(--gl-cyan)"),
                        }
                        for h_name, h_vals in _hl_data.items():
                            trend = h_vals.get("trend_direction", "unknown")
                            slope = h_vals.get("monthly_slope", 0)
                            note = h_vals.get("note", "")
                            _ico, _col = _trend_icons.get(trend, ("radar", "var(--gl-text-3)"))
                            st.markdown(
                                f'<div style="display:flex;align-items:center;gap:8px;'
                                f'margin:4px 0;color:var(--gl-text-2);">'
                                f'<span style="color:{_col};">{glint_icon(_ico, 16)}</span>'
                                f'<span><strong style="color:var(--gl-text);">{h_name}</strong>：'
                                f'月斜率 = {slope:+.4f} — {note}</span></div>',
                                unsafe_allow_html=True,
                            )
        except Exception:
            pass  # Phase 3 data is optional

        # ===== Alpha Decay =====
        st.divider()
        alpha_decay = results.get("alpha_decay", {})
        if alpha_decay:
            glint_heading("activity", "Alpha 衰減分析", "Alpha Decay", tone="amber")
            st.caption("↓ Alpha 衰減分析：隨著預測天數拉長，模型的預測力如何變化。曲線越平緩代表訊號越持久。")
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
render_page_footer("ICIR Analysis")
