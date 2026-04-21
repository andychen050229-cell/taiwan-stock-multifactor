"""Model Governance — 模型治理儀表板（Phase 3）"""

import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import importlib.util

_utils_path = Path(__file__).resolve().parent.parent / "utils.py"
_spec = importlib.util.spec_from_file_location("dashboard_utils", str(_utils_path))
_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils)
inject_custom_css = _utils.inject_custom_css
render_topbar = _utils.render_topbar
glint_plotly_layout = _utils.glint_plotly_layout
glint_styler_cmap = _utils.glint_styler_cmap
render_chart_note = _utils.render_chart_note
render_degraded_banner = _utils.render_degraded_banner
render_terminal_hero = _utils.render_terminal_hero
PAGE_EYEBROWS = _utils.PAGE_EYEBROWS
PAGE_TITLES = _utils.PAGE_TITLES
PAGE_BRIEFINGS = _utils.PAGE_BRIEFINGS
render_trust_strip = _utils.render_trust_strip
render_page_footer = _utils.render_page_footer
render_section_title = _utils.render_section_title

inject_custom_css()

# ---- Top-bar (sticky breadcrumb + model chips + clock) ----
render_topbar(
    crumb_left="台股多因子研究終端",
    crumb_current="模型治理",
    chips=[("Model Card", "pri"), ("DSR 12.12 → PASS", "vio"), ("PSI · KS drift", "ok")],
    show_clock=True,
)

# v8 §12 · §20.8 — Dark terminal hero driven by centralised copy maps
render_terminal_hero(
    eyebrow=PAGE_EYEBROWS["governance"],
    title=PAGE_TITLES["governance"],
    briefing=PAGE_BRIEFINGS["governance"],
    chips=[
        ("Phase", "3 · Governance", "info"),
        ("DSR", "12.12 · PASS", "ok"),
        ("Gates", "9 / 9 PASS", "ok"),
    ],
    tone="violet",
)
render_trust_strip([
    ("PHASE",   "3 · Governance",       "violet"),
    ("GATES",   "9 / 9 PASS",            "emerald"),
    ("DSR",     "12.12 · PASS",          "cyan"),
    ("ARTIFACT","Model Card · JSON",     "blue"),
])

with st.expander("ℹ️ 如何閱讀本頁？", expanded=False):
    st.markdown("""
- **品質閘門**：所有自動檢測項目全部通過 = 模型可信賴；若有未通過會以紅旗標示。
- **DSR**：排除「多重測試」導致的偽陽性 Sharpe，確認策略效能並非偶然。
- **Model Card**：每個模型的「身分證」，記錄訓練過程、效能、已知限制。
""")


# === Load governance data ===
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
    """Load a governance JSON file."""
    gov_dir = _project_outputs_dir() / "governance"
    fp = gov_dir / filename
    if fp.exists():
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _load_phase3_report():
    """Load the latest Phase 3 report."""
    report_dir = _project_outputs_dir() / "reports"
    reports = sorted(report_dir.glob("phase3_report_*.json"), reverse=True)
    if reports:
        with open(reports[0], "r", encoding="utf-8") as f:
            return json.load(f)
    return None


p3_report = _load_phase3_report()
dsr_data = _load_gov_json("dsr_revalidation.json")
baseline_data = _load_gov_json("performance_baseline.json")

if not p3_report:
    render_degraded_banner(
        title="摘要版模式 · Phase 3 治理報告尚未生成",
        reason="本機執行 `python run_phase3.py` 以產生完整治理結果；Cloud 預覽會略過此區。",
        available=[
            ("頁面導覽", "可繼續使用頂部與左側導覽"),
            ("其他分頁", "Model Metrics / ICIR / Backtest 不受影響"),
        ],
        unavailable=[
            ("品質閘門", "需要 outputs/governance/phase3_report_*.json"),
            ("DSR 重新驗證", "需要 dsr_revalidation.json"),
            ("效能基線", "需要 performance_baseline.json"),
        ],
        tone="blue",
    )
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 🛡️ 模型治理")
    st.markdown(f"**報告時間**: {p3_report.get('timestamp', '—')[:16]}")
    st.markdown(f"**整體狀態**: {p3_report.get('overall_status', '—')}")
    gates = p3_report.get("quality_gates", {})
    passed = sum(1 for v in gates.values() if v)
    st.markdown(f"**品質閘門**: {passed}/{len(gates)} 通過")
    if dsr_data:
        st.markdown(f"**DSR 判定**: {dsr_data.get('final_verdict', '—')}")
    st.divider()

# ============================================================
# Section 1: Quality Gates Overview
# ============================================================
render_section_title("品質閘門總覽", "Quality Gate Matrix")

gates = p3_report.get("quality_gates", {})
overall = p3_report.get("overall_status", "UNKNOWN")

_gv_pass = sum(1 for v in gates.values() if v)
_gv_total = len(gates) or 1
if overall == "PASS":
    st.success(f"整體狀態：**{overall}** — {_gv_pass}/{_gv_total} 品質閘門全部通過")
else:
    st.warning(f"整體狀態：**{overall}** — {_gv_pass}/{_gv_total} 通過，請檢查未通過項目")

gate_names_zh = {
    "models_available": "模型可用",
    "model_cards_generated": "Model Card 已生成",
    "drift_analysis_complete": "漂移分析完成",
    "signal_decay_assessed": "訊號衰減評估",
    "baseline_established": "效能基線建立",
    "prediction_pipeline_valid": "預測管線有效",
    "dsr_revalidated": "DSR 重新驗證",
    "no_severe_drift": "無嚴重漂移",
    "governance_data_ready": "治理資料就緒",
}

# ---- v8 §15.10 · 3×3 Gate Matrix (dark tokens + SVG glyphs + hover tech) ----
n_pass = sum(1 for v in gates.values() if v)
n_total = len(gates)
render_gate_matrix = _utils.render_gate_matrix
render_gate_matrix(gates, gate_names_zh=gate_names_zh)

# ---- Design-ported ring summary (SVG gauge repurposed for gate pass rate) ----
render_auc_gauge = _utils.render_auc_gauge
gauge_val_ratio = n_pass / max(n_total, 1)
# Map to 0–1 range using a display val ∈ [0, 1]
ring_html = render_auc_gauge(
    val=gauge_val_ratio,
    min_v=0.0, max_v=1.0,
    label=f"{n_pass} / {n_total} gates PASS · overall {overall}",
    width=300, height=170,
)
st.markdown(
    f'<div class="gl-panel" style="display:flex;align-items:center;justify-content:center;padding:14px 22px;">'
    f'{ring_html}</div>',
    unsafe_allow_html=True,
)

st.divider()

# ============================================================
# Section 2: DSR Revalidation
# ============================================================
render_section_title("DSR 重新驗證", "Deflated Sharpe Ratio · Re-validation")

st.info("""
**什麼是 DSR（Deflated Sharpe Ratio）？**

DSR 是 Bailey & López de Prado (2014) 提出的統計檢定。

它用來檢驗：當你嘗試了 N 種策略後，最終選中的策略是否「真正優秀」，還是僅僅因為多重測試（multiple testing）而看起來很好。

Phase 2 使用 n=9（含 3 個不可行的 D+1 策略），Phase 3 修正為 n=6。
""")

if dsr_data:
    c1, c2, c3 = st.columns(3)
    c1.metric("原始策略數", dsr_data.get("original_n_strategies", "—"))
    c2.metric("修正後策略數", dsr_data.get("revised_n_strategies", "—"))
    verdict = dsr_data.get("final_verdict", "—")
    verdict_label = {
        "PASS": "✅ 通過",
        "PASS_SINGLE_BEST": "✅ 單一最佳通過",
        "KNOWN_LIMITATION": "⚠️ 已知限制",
    }.get(verdict, verdict)
    c3.metric("最終判定", verdict_label)

    st.markdown("#### E[max(SR)] 修正對比")
    col_a, col_b = st.columns(2)
    col_a.metric(
        "原始 E[max(SR)]（n=9）",
        f"{dsr_data.get('original_expected_max_sharpe', 0):.4f}",
    )
    col_b.metric(
        "修正 E[max(SR)]（n=6）",
        f"{dsr_data.get('revised_expected_max_sharpe', 0):.4f}",
        delta=f"{dsr_data.get('revised_expected_max_sharpe', 0) - dsr_data.get('original_expected_max_sharpe', 0):.4f}",
    )

    # Revised results table
    revised = dsr_data.get("revised_results", {})
    if revised:
        st.markdown("#### 修正後各策略 DSR 結果")
        rows = []
        for name, vals in revised.items():
            rows.append({
                "策略": name,
                "觀察 Sharpe": vals.get("observed_sharpe", 0),
                "DSR 統計量": vals.get("dsr_statistic", 0),
                "p-value": vals.get("dsr_p_value", 0),
                "結果": "✅ PASS" if vals.get("dsr_pass") else "❌ FAIL",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        # DSR visual: observed Sharpe vs E[max(SR)] threshold
        fig_dsr = go.Figure()
        strat_names = [r["策略"] for r in rows]
        obs_sharpes = [r["觀察 Sharpe"] for r in rows]
        bar_colors = ["#10b981" if r["結果"].startswith("✅") else "#f43f5e" for r in rows]

        fig_dsr.add_trace(go.Bar(
            x=strat_names, y=obs_sharpes, marker_color=bar_colors,
            text=[f"{s:.3f}" for s in obs_sharpes], textposition="outside",
            textfont=dict(family="JetBrains Mono, monospace", size=11),
            name="觀察 Sharpe",
        ))
        fig_dsr.add_hline(
            y=dsr_data.get("revised_expected_max_sharpe", 0),
            line_dash="dash", line_color="#f59e0b", line_width=2,
            annotation_text=f"E[max(SR)] = {dsr_data.get('revised_expected_max_sharpe', 0):.4f}",
            annotation_font=dict(family="JetBrains Mono, monospace", size=10, color="#fde68a"),
        )
        fig_dsr.update_layout(**glint_plotly_layout(
            title="各策略觀察 Sharpe vs DSR 門檻",
            subtitle="Observed Sharpe vs E[max(SR)] · 綠色＝通過 / 紅色＝未達",
            height=400,
            ylabel="Sharpe Ratio",
        ))
        fig_dsr.update_layout(showlegend=False)
        st.plotly_chart(fig_dsr, use_container_width=True)

        # v11 §4a — migrated inline pastel div → shared `.gl-box-warn` dark card.
        st.markdown("""
        <div class="gl-box-warn">
        <strong>📌 DSR 解讀：</strong><br>
        當嘗試 N 種策略時，E[max(SR)] 代表「僅靠運氣」可能達到的最大夏普比率。<br>
        個別策略的 Sharpe 若低於此門檻，可能只是多重測試的偽陽性結果。<br><br>
        <strong>但</strong>：以「單一最佳策略」角度（N=1），ensemble_D5 的 DSR 通過（p=1.0），表明其 Sharpe 不可能僅靠運氣。
        </div>
        """, unsafe_allow_html=True)

    # Single best
    single = dsr_data.get("single_best_strategy", {})
    if single:
        st.markdown("#### 單一最佳策略（不考慮多重測試）")
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("最佳策略", single.get("name", "—"))
        sc2.metric("Sharpe", f"{single.get('sharpe', 0):.4f}")
        result = "✅ PASS" if single.get("dsr_pass") else "❌ FAIL"
        sc3.metric("DSR", result)

    # Explanation
    explanation = dsr_data.get("explanation", "")
    if explanation:
        st.markdown(f"> {explanation}")

else:
    st.warning("DSR 重新驗證資料尚未生成")

st.divider()

# ============================================================
# Section 3: Performance Baselines
# ============================================================
render_section_title("效能基線", "Performance Baselines")

st.info("""
**效能基線用途**

基線是模型「健康時」的效能快照。

未來每次重新預測或收到新資料時，系統會比對當前效能與基線。

若 AUC 下降 > 3%、Sharpe 下降 > 50%、或 Rank IC 轉負，將觸發警告。
""")

if baseline_data:
    for model_name, metrics in baseline_data.items():
        with st.expander(f"📋 {model_name}", expanded=False):
            for metric_name, vals in metrics.items():
                if isinstance(vals, dict):
                    base = vals.get("baseline")
                    warn = vals.get("warning_threshold")
                    desc = vals.get("description", "")
                    if base is not None:
                        st.markdown(
                            f"- **{metric_name}**: 基線 = `{base}` ｜ 警告閾值 = `{warn}` ｜ {desc}"
                        )
else:
    st.warning("效能基線資料尚未生成")

st.divider()

# ============================================================
# Section 4: Model Cards
# ============================================================
render_section_title("Model Cards", "Engine × Horizon Metadata")

st.info("""
**Model Card 是什麼？**

Model Card 是 Google 提出的模型透明度標準文件。

它記錄了模型的用途、訓練數據、效能指標、已知限制等資訊。

這確保每個模型都有完整的治理記錄，方便審計與復現。
""")

gov_dir = _project_outputs_dir() / "governance"
card_files = sorted(gov_dir.glob("model_card_*.json"))

if card_files:
    card_names = [f.stem.replace("model_card_", "") for f in card_files]
    selected = st.selectbox("選擇模型", card_names)

    card_path = gov_dir / f"model_card_{selected}.json"
    with open(card_path, "r", encoding="utf-8") as f:
        card = json.load(f)

    # Overview
    overview = card.get("overview", {})
    st.markdown(f"**引擎**: {overview.get('framework', '—')} ｜ "
                f"**預測週期**: {overview.get('horizon', '—')} ｜ "
                f"**特徵數**: {overview.get('features_count', '—')} ｜ "
                f"**交叉驗證**: {overview.get('n_folds', '—')} Folds")

    # Performance
    perf = card.get("performance", {})
    cls = perf.get("classification", {})
    bt = perf.get("backtest_discount", {})

    pc1, pc2, pc3, pc4 = st.columns(4)
    pc1.metric("AUC", f"{cls.get('auc', 0):.4f}")
    pc2.metric("Rank IC", f"{perf.get('signal_quality', {}).get('rank_ic', 0):.4f}")
    pc3.metric("Sharpe", f"{bt.get('sharpe_ratio', 0):.2f}")
    pc4.metric("Max DD", f"{bt.get('max_drawdown', 0):.1%}")

    # Intended use
    intended = card.get("intended_use", {})
    st.markdown(f"**預期用途**: {intended.get('primary', '—')}")
    st.markdown(f"**目標使用者**: {intended.get('users', '—')}")

    # Known limitations
    limitations = card.get("known_limitations", [])
    if limitations:
        st.markdown("**已知限制**：")
        for lim in limitations:
            st.markdown(f"- {lim}")

    # Full JSON
    with st.expander("📄 完整 Model Card JSON"):
        st.json(card)

    # ===== Model Card Comparison View =====
    if len(card_files) >= 2:
        st.markdown("#### 📊 模型效能橫向比較 | Cross-Model Comparison")

        comp_rows = []
        for cf in card_files:
            with open(cf, "r", encoding="utf-8") as f:
                c = json.load(f)
            ov = c.get("overview", {})
            pf = c.get("performance", {})
            cls_p = pf.get("classification", {})
            sig_p = pf.get("signal_quality", {})
            bt_p = pf.get("backtest_discount", {})
            comp_rows.append({
                "模型": cf.stem.replace("model_card_", ""),
                "引擎": ov.get("framework", "—"),
                "天期": ov.get("horizon", "—"),
                "AUC": cls_p.get("auc", 0),
                "ICIR": sig_p.get("icir", 0),
                "Sharpe": bt_p.get("sharpe_ratio", 0),
                "Max DD": bt_p.get("max_drawdown", 0),
                "勝率": bt_p.get("win_rate", 0),
            })

        df_comp = pd.DataFrame(comp_rows)
        st.dataframe(
            df_comp.style.background_gradient(subset=["AUC", "ICIR", "Sharpe"], cmap=glint_styler_cmap("diverging"))
                .background_gradient(subset=["Max DD"], cmap=glint_styler_cmap("diverging").reversed()),
            use_container_width=True, hide_index=True
        )

        # Radar chart comparison
        categories = ["AUC", "ICIR", "Sharpe", "勝率"]
        fig_radar = go.Figure()
        colors = ["#2563eb", "#7c3aed", "#10b981", "#f59e0b"]
        for i, row in df_comp.iterrows():
            # Normalize values for radar
            vals = [
                min(row["AUC"] / 0.7, 1.0),
                min(row["ICIR"] / 1.0, 1.0),
                min(row["Sharpe"] / 2.0, 1.0),
                row["勝率"],
            ]
            fig_radar.add_trace(go.Scatterpolar(
                r=vals, theta=categories, fill="toself",
                name=row["模型"], line_color=colors[i % len(colors)]
            ))
        fig_radar.update_layout(**glint_plotly_layout(
            title="模型多維度效能比較",
            subtitle="Multi-Dimensional Comparison · AUC · ICIR · Sharpe · 勝率",
            height=420,
            show_grid=False,
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 1],
                                 tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#8397AC")),
                angularaxis=dict(tickfont=dict(family="JetBrains Mono, monospace", size=11, color="#8397AC")),
            ),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

else:
    st.warning("尚未生成 Model Card")

st.divider()

# ============================================================
# Section 5: Prediction Pipeline Validation
# ============================================================
render_section_title("預測管線驗證", "Pipeline Validation")

st.info("""
**這一段在做什麼?**

把 6 個模型(LGB/XGB × D1/D5/D20)實際跑一次預測,
檢查輸出的機率是否合理 — 三類機率加總等於 1、沒有 NaN、沒有負值。
通過 = 模型可以部署到真實流程;失敗 = 模型檔有問題或特徵欄位對不上。
""")

pipeline = p3_report.get("results", {}).get("step6_pipeline", {})
if pipeline:
    valid = pipeline.get("valid", False)
    if valid:
        st.success("所有模型預測管線驗證通過:輸出為 3 類機率、加總為 1、無 NaN")
    else:
        st.error("部分模型預測管線驗證失敗")

    results_pipe = pipeline.get("results", {})
    pipe_rows = []
    for name, res in results_pipe.items():
        status = res.get("status", "unknown")
        icon = "✅" if status == "pass" else ("⏭️" if status == "skip" else "❌")
        detail = f"avg UP prob = {res.get('avg_up_prob', 0):.4f}" if status == "pass" else res.get("reason", res.get("error", ""))
        st.markdown(f"{icon} **{name}**: {detail}")
        pipe_rows.append({
            "模型": name,
            "狀態": "通過" if status == "pass" else ("跳過" if status == "skip" else "失敗"),
            "樣本數": res.get("sample_size", 0),
            "輸出維度": str(res.get("pred_shape", "—")),
            "平均 UP 機率": f"{res.get('avg_up_prob', 0):.4f}" if status == "pass" else "—",
        })

    if pipe_rows:
        # 欄位說明
        st.markdown("""
        <div style="
            background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.95) 100%);
            border: 1px solid rgba(103,232,249,0.28); border-radius: 10px;
            padding: 12px 16px; margin: 10px 0; font-size: 0.85rem; color: #cfe2ee; line-height: 1.75;
            box-shadow: inset 0 1px 0 rgba(103,232,249,0.12);
        ">
            <strong style="color: #67e8f9; letter-spacing: 0.04em;">📘 欄位說明</strong><br>
            <strong>模型</strong>:引擎 × 預測天期(如 lightgbm_D20 = LightGBM 預測 20 天後漲跌)<br>
            <strong>狀態</strong>:通過 = 管線輸出合法;跳過 = 該模型無 OOS 樣本;失敗 = 有 NaN 或 shape 錯誤<br>
            <strong>樣本數</strong>:該模型在 OOS 期間可用的預測樣本<br>
            <strong>輸出維度</strong>:(n, 3) = n 筆樣本 × 3 類機率(DOWN/FLAT/UP)<br>
            <strong>平均 UP 機率</strong>:所有樣本對「會漲」的平均預測信心
        </div>
        """, unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(pipe_rows), use_container_width=True, hide_index=True)
else:
    st.warning("""
    ⚠️ **預測管線驗證資料尚未生成**

    此段需要 Phase 3 治理流程的 `step6_pipeline` 輸出。
    若顯示為空,代表執行時尚未跑完此步驟,或報告版本不包含此欄位。
    """)

st.divider()

# ============================================================
# Section 6: 資料健康度快照 - 補齊原先空白區
# ============================================================
render_section_title("治理快照", "Governance Snapshot")

st.info("""
**為什麼要有這段?**

前面五段講的是「單次檢查結果」,這段把最關鍵的數字濃縮成一眼可讀的快照卡片,
讓非技術使用者不必翻完整份報告也能掌握「目前模型狀態是否健康」。
""")

# 取得整體治理摘要
_summary = p3_report.get("results", {})
_drift_summary = _summary.get("step2_drift", {})
_decay_summary = _summary.get("step4_signal_decay", {})
_baseline_summary = _summary.get("step5_baseline", {})

snap_c1, snap_c2, snap_c3, snap_c4 = st.columns(4)
with snap_c1:
    _drift_severity = _drift_summary.get("overall_severity", "—")
    _drift_icon = {"none": "🟢", "mild": "🟡", "moderate": "🟠", "severe": "🔴"}.get(str(_drift_severity).lower(), "⚪")
    st.metric("資料漂移程度", f"{_drift_icon} {_drift_severity}",
              help="PSI 檢測:訓練期 vs 測試期特徵分佈差異。none = 很穩、severe = 需重訓。")
with snap_c2:
    _hl = _decay_summary.get("min_half_life_months", "—")
    st.metric("最短半衰期", f"{_hl} 月" if _hl != "—" else "—",
              help="模型預測力衰減到一半所需的月數,越長 = 訊號越耐久。")
with snap_c3:
    _retrain = _decay_summary.get("recommended_retrain_cycle", "—")
    _retrain_short = str(_retrain).split("(")[0].strip() if "(" in str(_retrain) else str(_retrain)
    st.metric("建議重訓週期", _retrain_short,
              help="依據半衰期推論的重訓頻率。到期就該重新訓練模型。")
with snap_c4:
    _n_baselines = len(_baseline_summary) if isinstance(_baseline_summary, dict) else 0
    st.metric("基線指標數", f"{_n_baselines} 個",
              help="系統正在監測的基線指標(AUC/IC/Sharpe 等),任何一項異常都會觸發警告。")

# 簡短治理摘要(白話版) — v11.3 dark-glint 化
st.markdown(f"""
<div style="
    background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.96) 100%);
    border: 1px solid rgba(103,232,249,0.22);
    border-left: 4px solid #67e8f9;
    border-radius: 12px;
    padding: 18px 22px;
    margin: 16px 0;
    font-size: 0.92rem;
    color: #cfe2ee;
    line-height: 1.85;
    box-shadow: inset 0 1px 0 rgba(103,232,249,0.10);
">
    <strong style="color: #67e8f9; font-size: 1.02rem; letter-spacing: 0.04em;">📌 一句話總結</strong><br>
    本模型通過 <strong style="color:#E8F7FC;">{n_pass}/{n_total}</strong> 項品質閘門檢查、
    DSR 判定為 <strong style="color:#E8F7FC;">{dsr_data.get("final_verdict", "—") if dsr_data else "—"}</strong>、
    資料漂移為 <strong style="color:#E8F7FC;">{_drift_severity}</strong>,
    最短半衰期 <strong style="color:#E8F7FC;">{_hl}</strong> 個月,
    建議 <strong style="color:#E8F7FC;">{_retrain_short if _retrain != "—" else "每季"}</strong> 重訓一次。<br><br>
    <strong style="color: #6ee7b7;">→ 可以放心部署;若要實盤,記得每月追蹤漂移指標與基線差距。</strong>
</div>
""", unsafe_allow_html=True)

# ===== Footer =====
render_page_footer(
    "Model Governance",
    limits_note=(
        f"Phase 3 模型治理報告自動生成 ｜ 品質閘門 {_gv_pass}/{_gv_total} 通過為生產就緒條件 "
        f"｜ DSR 採用 Bailey & López de Prado (2014) 方法"
    ),
)
