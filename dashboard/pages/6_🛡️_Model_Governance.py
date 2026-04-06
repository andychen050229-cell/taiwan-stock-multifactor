"""Model Governance — 模型治理儀表板（Phase 3）"""

import streamlit as st
import json
from pathlib import Path
import importlib.util

_utils_path = Path(__file__).resolve().parent.parent / "utils.py"
_spec = importlib.util.spec_from_file_location("dashboard_utils", str(_utils_path))
_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils)
inject_custom_css = _utils.inject_custom_css

inject_custom_css()

# Data Context Banner
st.markdown("""
<div style="background:#f0f9ff; border-left:4px solid #0284c7; border-radius:0 8px 8px 0; padding:12px 16px; font-size:0.85rem; color:#0c4a6e; margin-bottom:20px;">
🛡️ <strong>Phase 3 — 模型治理</strong>：Model Card ｜ DSR 重新驗證 ｜ 效能基線 ｜ 預測管線驗證
</div>
""", unsafe_allow_html=True)

st.title("🛡️ 模型治理報告")
st.caption("Phase 3 自動生成的治理文件與品質驗證結果")


# === Load governance data ===
def _load_gov_json(filename):
    """Load a governance JSON file."""
    gov_dir = Path(__file__).resolve().parent.parent.parent / "outputs" / "governance"
    fp = gov_dir / filename
    if fp.exists():
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _load_phase3_report():
    """Load the latest Phase 3 report."""
    report_dir = Path(__file__).resolve().parent.parent.parent / "outputs" / "reports"
    reports = sorted(report_dir.glob("phase3_report_*.json"), reverse=True)
    if reports:
        with open(reports[0], "r", encoding="utf-8") as f:
            return json.load(f)
    return None


p3_report = _load_phase3_report()
dsr_data = _load_gov_json("dsr_revalidation.json")
baseline_data = _load_gov_json("performance_baseline.json")

if not p3_report:
    st.warning("尚未執行 Phase 3，請先執行 `python run_phase3.py`")
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
st.header("品質閘門總覽")

gates = p3_report.get("quality_gates", {})
overall = p3_report.get("overall_status", "UNKNOWN")

if overall == "PASS":
    st.success(f"整體狀態：**{overall}** — 9/9 品質閘門全部通過")
else:
    st.warning(f"整體狀態：**{overall}** — 請檢查未通過項目")

cols = st.columns(3)
gate_names_zh = {
    "models_available": "模型可用",
    "model_cards_generated": "Model Card 已生成",
    "drift_analysis_complete": "漂移分析完成",
    "signal_decay_assessed": "信號衰減評估",
    "baseline_established": "效能基線建立",
    "prediction_pipeline_valid": "預測管線有效",
    "dsr_revalidated": "DSR 重新驗證",
    "no_severe_drift": "無嚴重漂移",
    "governance_data_ready": "治理資料就緒",
}

for i, (gate_key, passed) in enumerate(gates.items()):
    col = cols[i % 3]
    icon = "✅" if passed else "❌"
    label = gate_names_zh.get(gate_key, gate_key)
    col.markdown(f"{icon} **{label}**")

st.divider()

# ============================================================
# Section 2: DSR Revalidation
# ============================================================
st.header("DSR 重新驗證")

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
st.header("效能基線")

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
st.header("Model Cards")

st.info("""
**Model Card 是什麼？**

Model Card 是 Google 提出的模型透明度標準文件。

它記錄了模型的用途、訓練數據、效能指標、已知限制等資訊。

這確保每個模型都有完整的治理記錄，方便審計與復現。
""")

gov_dir = Path(__file__).resolve().parent.parent.parent / "outputs" / "governance"
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
else:
    st.warning("尚未生成 Model Card")

st.divider()

# ============================================================
# Section 5: Prediction Pipeline Validation
# ============================================================
st.header("預測管線驗證")

pipeline = p3_report.get("results", {}).get("step6_pipeline", {})
if pipeline:
    valid = pipeline.get("valid", False)
    if valid:
        st.success("所有模型預測管線驗證通過：輸出為 3 類機率、加總為 1、無 NaN")
    else:
        st.error("部分模型預測管線驗證失敗")

    results = pipeline.get("results", {})
    for name, res in results.items():
        status = res.get("status", "unknown")
        icon = "✅" if status == "pass" else ("⏭️" if status == "skip" else "❌")
        detail = f"avg UP prob = {res.get('avg_up_prob', 0):.4f}" if status == "pass" else res.get("reason", res.get("error", ""))
        st.markdown(f"{icon} **{name}**: {detail}")
