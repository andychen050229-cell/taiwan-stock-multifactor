"""Signal Monitor — 訊號監控儀表板（Phase 3）"""

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
glint_plotly_layout = _utils.glint_plotly_layout
glint_heatmap_colorscale = _utils.glint_heatmap_colorscale
glint_colorbar = _utils.glint_colorbar
render_degraded_banner = _utils.render_degraded_banner
render_terminal_hero = _utils.render_terminal_hero
PAGE_EYEBROWS = _utils.PAGE_EYEBROWS
PAGE_TITLES = _utils.PAGE_TITLES
PAGE_BRIEFINGS = _utils.PAGE_BRIEFINGS
render_trust_strip = _utils.render_trust_strip
render_page_footer = _utils.render_page_footer
render_section_title = _utils.render_section_title
glint_icon = _utils.glint_icon
glint_heading = _utils.glint_heading

inject_custom_css()

# ---- Top-bar (sticky breadcrumb + model chips + clock) ----
render_topbar(
    crumb_left="多因子股票分析系統",
    crumb_current="訊號監控",
    chips=[("live signal feed", "pri"), ("threshold sweep", "vio"), ("embargo=20", "default")],
    show_clock=True,
)

# v8 §12 · §20.9 — Dark terminal hero driven by centralised copy maps
render_terminal_hero(
    eyebrow=PAGE_EYEBROWS["signal"],
    title=PAGE_TITLES["signal"],
    briefing=PAGE_BRIEFINGS["signal"],
    chips=[
        ("Phase", "3 · Monitor", "info"),
        ("Drift", "PSI · KS", "info"),
        ("Embargo", "20 交易日", "warn"),
    ],
    tone="cyan",
)
render_trust_strip([
    ("PHASE",    "3 · Monitor",         "violet"),
    ("DRIFT",    "PSI · KS",             "cyan"),
    ("DECAY",    "Monthly IC · Half-Life", "blue"),
    ("EMBARGO",  "20 交易日",             "amber"),
])

with st.expander("ℹ️ 如何閱讀本頁？", expanded=False):
    st.markdown("""
- **PSI**（漂移指標）：< 0.1 ＝ 穩定；0.1–0.2 ＝ 輕微偏移；> 0.2 ＝ 顯著偏移。
- **ICIR**（訊號穩定性）：|ICIR| > 0.5 ＝ 強訊號。
- **半衰期**：預測能力多久會衰減一半，決定何時需要重新訓練。
""")


def _project_outputs_dir():
    """Find outputs/ regardless of cwd (Cloud shim chdir-safe)."""
    here = Path(__file__).resolve()
    for candidate in (
        here.parent.parent.parent.parent / "outputs",   # project_root/outputs  ← canonical
        here.parent.parent.parent / "outputs",          # 程式碼/outputs (legacy)
        Path.cwd() / "outputs",
        Path.cwd().parent / "outputs",
        Path.cwd().parent.parent / "outputs",
    ):
        if candidate.exists():
            return candidate
    return Path.cwd() / "outputs"


def _load_gov_json(filename):
    gov_dir = _project_outputs_dir() / "governance"
    fp = gov_dir / filename
    if fp.exists():
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


drift_data = _load_gov_json("drift_report.json")
decay_data = _load_gov_json("signal_decay_report.json")

if not drift_data and not decay_data:
    render_degraded_banner(
        title="摘要版模式 · 訊號監控尚未產生",
        reason="本機執行 `python run_phase3.py` 以產生漂移 / 衰減報告；Cloud 預覽會略過此區。",
        available=[
            ("頁面導覽", "頂部麵包屑與左側導覽可正常使用"),
            ("Model Card / DSR", "請至『模型治理』分頁檢視"),
        ],
        unavailable=[
            ("資料漂移偵測", "需要 outputs/governance/drift_report.json"),
            ("訊號衰減分析", "需要 outputs/governance/signal_decay_report.json"),
            ("再訓練建議", "依賴上述兩份報告"),
        ],
        tone="blue",
    )
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:10px;margin:0 0 10px 0;padding:10px 12px;
        background:linear-gradient(135deg,rgba(34,211,238,0.14),rgba(16,185,129,0.08));
        border:1px solid rgba(34,211,238,0.34);border-radius:8px;">
        <span style="color:#67e8f9;">{glint_icon('radar', 18, '#67e8f9')}</span>
        <span style="color:#e2e8f0;font-weight:700;letter-spacing:0.05em;font-size:0.95rem;">訊號監控</span>
        </div>""",
        unsafe_allow_html=True,
    )
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
render_section_title("資料漂移偵測", "Feature Drift · PSI / KS")

with st.expander("PSI（Population Stability Index）是什麼？", expanded=False, icon=":material/help_outline:"):
    st.markdown("""
PSI 衡量特徵分佈在「參考期」與「當前期」之間的變化程度。

PSI < 0.1 = 穩定，0.1 ~ 0.2 = 輕微偏移，> 0.2 = 顯著偏移。

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
        colors = ["#ef4444" if psi > 0.2 else ("#a78bfa" if psi > 0.1 else "#22c55e") for psi in psi_vals]

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

        fig.update_layout(**glint_plotly_layout(
            title="Top 10 漂移特徵 · PSI 排序",
            subtitle="PSI > 0.2 = 分佈顯著偏移,需要立即處理",
            height=360, ylabel="PSI",
        ), showlegend=False)
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
        with st.expander("📋 完整特徵漂移報告(含欄位說明)", expanded=False):
            # 欄位說明
            st.markdown("""
            <div style="
                background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.95) 100%);
                border: 1px solid rgba(103,232,249,0.28); border-radius: 10px;
                padding: 12px 16px; margin-bottom: 10px;
                font-size: 0.86rem; color: #cfe2ee; line-height: 1.75;
                box-shadow: inset 0 1px 0 rgba(103,232,249,0.12);
            ">
                <strong style="color: #67e8f9; letter-spacing: 0.04em;">📘 欄位說明</strong><br>
                <strong>特徵</strong>:被檢查的特徵欄位名稱<br>
                <strong>PSI</strong>:分佈差異量化指標(數字越大 = 變化越大)<br>
                <strong>PSI 等級</strong>:🟢&lt;0.1(穩定) / 🟡 0.1~0.2(輕微偏移) / 🔴&gt;0.2(顯著偏移)<br>
                <strong>KS 統計量</strong>:另一種分佈差異量測(Kolmogorov-Smirnov)<br>
                <strong>KS 顯著</strong>:這個偏移在統計上是否達到顯著水準<br>
                <strong>均值偏移%</strong>:平均值相對參考期的變化百分比<br>
                <strong>建議</strong>:系統自動給出的處理建議(例如 retrain / monitor / keep)
            </div>
            """, unsafe_allow_html=True)
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
                colorscale=[[0, "#22c55e"], [0.1/max(max(psi_values, default=1), 0.01), "#ede9fe"],
                            [0.2/max(max(psi_values, default=1), 0.01), "#a78bfa"], [1, "#ef4444"]],
                hovertemplate="<b>%{x}</b><br>PSI: %{z:.4f}<extra></extra>",
            ))
            _layout = glint_plotly_layout(
                title="所有特徵 PSI 漂移熱力圖",
                subtitle="綠=穩定 黃=輕微偏移 紅=顯著偏移",
                height=220,
            )
            _layout["xaxis"]["tickangle"] = -45
            _layout["margin"] = dict(l=40, r=20, t=70, b=110)
            fig_heat.update_layout(**_layout)
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
render_section_title("訊號穩定性分析", "Signal Stability · Half-Life")

with st.expander("ICIR（Information Coefficient Information Ratio）是什麼？", expanded=False, icon=":material/help_outline:"):
    st.markdown("""
ICIR = Mean(IC) / Std(IC)，衡量訊號的穩定程度。

ICIR > 0.5 = 強訊號（可靠），0.2 ~ 0.5 = 中等訊號，< 0.2 = 弱訊號。

強訊號意味著模型的預測能力在不同時間段表現一致。
""")

if decay_data:
    summary = decay_data.get("summary", {})
    retrain = decay_data.get("recommended_retrain_cycle", "—")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("強訊號", summary.get("strong_signals", 0))
    c2.metric("中等訊號", summary.get("moderate_signals", 0))
    c3.metric("弱訊號", summary.get("weak_signals", 0))
    # Shorten long retrain text to prevent metric truncation
    retrain_short = str(retrain).split("（")[0].strip() if "（" in str(retrain) else str(retrain)
    c4.metric("再訓練週期", retrain_short)

    best = summary.get("best_signal", "—")
    st.markdown(f"**最佳訊號來源**：{best}")

    # Signal stability by strategy
    stability = decay_data.get("signal_stability", {})
    if stability:
        st.markdown("#### 各策略訊號穩定度")

        strat_names = []
        icir_vals = []
        colors = []

        for name, vals in stability.items():
            strat_names.append(name)
            icir_vals.append(abs(vals.get("icir", 0)))
            stab = vals.get("stability", "weak")
            color = "#22c55e" if stab == "strong" else ("#a78bfa" if stab == "moderate" else "#ef4444")
            colors.append(color)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=strat_names, y=icir_vals,
            marker_color=colors,
            text=[f"{v:.3f}" for v in icir_vals],
            textposition="outside",
        ))

        fig.add_hline(y=0.5, line_dash="dash", line_color="green",
                      annotation_text="強訊號 (0.5)", annotation_position="top right")
        fig.add_hline(y=0.2, line_dash="dash", line_color="orange",
                      annotation_text="中等訊號 (0.2)", annotation_position="top right")

        fig.update_layout(**glint_plotly_layout(
            title="各策略訊號穩定度 · |ICIR|",
            subtitle="|ICIR| > 0.5 = 強訊號,可靠;0.2~0.5 = 中等;< 0.2 = 弱",
            height=360, ylabel="|ICIR|",
        ), showlegend=False)
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
            colors_palette = ["#2563eb", "#7c3aed", "#06b6d4"]

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

            fig_ic.add_hline(y=0, line_dash="dash", line_color="rgba(148,163,184,0.5)", line_width=1)
            _lay_ic = glint_plotly_layout(
                title="月度 Rank IC · 前 3 強特徵",
                subtitle="正值區間越多,該特徵預測力越穩定",
                height=360, xlabel="月份", ylabel="Rank IC",
            )
            _lay_ic["legend"].update(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            fig_ic.update_layout(**_lay_ic)
            st.plotly_chart(fig_ic, use_container_width=True)

    # Half-life analysis with visualization
    half_life = decay_data.get("half_life_analysis", {})
    if half_life:
        st.markdown("#### 訊號半衰期分析 | Signal Half-Life")

        hl_rows = []
        _trend_map = {
            "improving": ("trending-up", "#10b981"),
            "decaying":  ("activity",    "#f43f5e"),
            "stable":    ("line-chart",  "#22d3ee"),
        }
        for name, vals in half_life.items():
            hl = vals.get("half_life_months")
            note = vals.get("note", "—")
            trend = vals.get("trend_direction", "unknown")
            _ic_name, _ic_color = _trend_map.get(trend, ("target", "#94a3b8"))
            trend_svg = glint_icon(_ic_name, 14, _ic_color)
            slope = vals.get("monthly_slope", 0)
            n_months = vals.get("n_months_analyzed", 0)

            if hl:
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:8px;margin:4px 0;'>{trend_svg}"
                    f"<span><strong>{name}</strong>：半衰期 ≈ <strong>{hl} 個月</strong> — {note}</span></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:8px;margin:4px 0;'>{trend_svg}"
                    f"<span><strong>{name}</strong>：{note}</span></div>",
                    unsafe_allow_html=True,
                )

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
                color = "#10b981" if row["趨勢"] == "improving" else ("#f43f5e" if row["趨勢"] == "decaying" else "#2563eb")
                fig_hl.add_trace(go.Bar(
                    x=[row["天期"]], y=[row["月斜率"]],
                    marker_color=color, showlegend=False,
                    text=[f"{row['月斜率']:+.4f}"], textposition="outside",
                ))
            fig_hl.add_hline(y=0, line_dash="dash", line_color="rgba(148,163,184,0.5)")
            fig_hl.update_layout(**glint_plotly_layout(
                title="訊號月度斜率 · Monthly IC Slope",
                subtitle="正值=預測力持續改善,負值=衰退中",
                height=320, ylabel="IC 月斜率",
            ))
            st.plotly_chart(fig_hl, use_container_width=True)

        # v11 §4a — migrated inline pastel div → shared `.gl-box-ok` dark card.
        st.markdown(f"""
        <div class="gl-box-ok">
        <strong style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("pin", 15, "#10b981")} 半衰期解讀：</strong><br>
        D+5 與 D+20 的訊號均呈<strong>持續改善</strong>趨勢（正斜率），表示模型的預測能力在研究期間內尚未出現衰減。<br>
        建議再訓練週期：<strong>3-6 個月</strong>。
        </div>
        """, unsafe_allow_html=True)

    # Alpha decay from Phase 2
    alpha_decay = decay_data.get("alpha_decay_from_p2", {})
    if alpha_decay:
        with st.expander("Phase 2 Alpha Decay 結果", icon=":material/bar_chart:"):
            rows = []
            for name, vals in alpha_decay.items():
                rows.append({
                    "策略": name,
                    "Mean IC": f"{vals.get('mean_ic', 0):.4f}",
                    "ICIR": f"{vals.get('icir', 0):.4f}",
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

else:
    st.warning("訊號衰減分析資料尚未生成")

st.divider()

# ============================================================
# Section 3: Retrain Recommendation Summary
# ============================================================
render_section_title("綜合建議", "Integrated Recommendation")

has_data = drift_data or decay_data

if has_data:
    drift_sev = drift_data.get("overall_severity", "—") if drift_data else "—"
    retrain_cycle = decay_data.get("recommended_retrain_cycle", "—") if decay_data else "—"
    n_drifted = drift_data.get("n_drifted_features", 0) if drift_data else 0
    _decay_summary = decay_data.get("summary", {}) if decay_data else {}
    strong = _decay_summary.get("strong_signals", 0)
    moderate = _decay_summary.get("moderate_signals", 0)
    weak = _decay_summary.get("weak_signals", 0)
    min_hl = decay_data.get("min_half_life_months") if decay_data else None

    st.markdown(f"""
| 項目 | 結果 |
|------|------|
| 資料漂移嚴重度 | {drift_sev} |
| PSI > 0.2 特徵數 | {n_drifted} |
| 強訊號數量 | {strong} |
| 弱訊號數量 | {weak} |
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
        st.warning("弱訊號數量超過強訊號,建議縮短再訓練週期或調整特徵組合。")
    elif strong >= 3:
        st.success("D+20 策略訊號穩定性最佳(ICIR > 0.5),適合作為主力策略。")

    # === 白話一句話總結(給非技術使用者) ===
    _traffic = "🟢 綠燈" if drift_sev in ("low", "—") and weak <= strong else (
        "🔴 紅燈" if drift_sev == "high" else "🟡 黃燈"
    )
    _status_txt = {
        "🟢 綠燈": "可以繼續使用,定期追蹤即可。",
        "🟡 黃燈": "模型還能用,但請注意部分特徵有變化。",
        "🔴 紅燈": "請立即重新訓練,部分特徵已顯著偏移。",
    }[_traffic]

    st.markdown(f"""
    <div style="
        background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.96) 100%);
        border: 1px solid rgba(103,232,249,0.22);
        border-left: 4px solid #67e8f9;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 18px 0 4px 0;
        box-shadow: inset 0 1px 0 rgba(103,232,249,0.10);
    ">
        <div style="
            display: inline-block;
            background: rgba(103,232,249,0.14); color: #67e8f9;
            border: 1px solid rgba(103,232,249,0.32);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.70rem; font-weight: 700; letter-spacing: 0.12em;
            padding: 3px 10px; border-radius: 4px; margin-bottom: 10px;
        ">目前狀態 · HEALTH SNAPSHOT</div>
        <div style="font-size: 1.3rem; font-weight: 800; color: #E8F7FC; margin-bottom: 6px;">
            {_traffic} · {_status_txt}
        </div>
        <div style="font-size: 0.92rem; color: #cfe2ee; line-height: 1.85; margin-top: 8px;">
            漂移 <strong style="color:#E8F7FC;">{drift_sev}</strong> ·
            PSI&gt;0.2 特徵 <strong style="color:#E8F7FC;">{n_drifted}</strong> 個 ·
            強/中/弱訊號 <strong style="color:#E8F7FC;">{strong}</strong>/<strong style="color:#E8F7FC;">{moderate}</strong>/<strong style="color:#E8F7FC;">{weak}</strong> ·
            最短半衰期 <strong style="color:#E8F7FC;">{f'{min_hl} 月' if min_hl else '未衰減'}</strong><br>
            <strong style="color: #6ee7b7;">→ 建議 {retrain_cycle}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.warning("""
    ⚠️ **尚無監控資料**

    此段需要 `outputs/governance/drift_report.json` 與 `outputs/governance/signal_decay_report.json`。
    若 Cloud 部署後看到此訊息,代表這兩個檔案未成功上傳或路徑對不上。
    請執行 `python run_phase3.py` 產生,或在部署端檢查檔案路徑。
    """)

# ===== Footer =====
render_page_footer(
    "Signal Monitor",
    limits_note=(
        "訊號監控基於 Phase 3 自動分析 ｜ PSI 閾值：0.1（輕微）/ 0.2（顯著）"
        "｜ ICIR 閾值：0.2（中等）/ 0.5（強）"
    ),
)
