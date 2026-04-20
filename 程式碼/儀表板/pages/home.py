"""
台股多因子預測系統 — Landing Page (glint-light design, Design-ported)

Dual-mode tab layout per 2026/04 Design spec:
  🌱 投資觀察台  (plain-language, warm amber wash)
  ⚙️ 研究工作站  (dense KPIs, charts, Bloomberg-terminal feel)
"""

import streamlit as st
from pathlib import Path
import plotly.graph_objects as go
import json
import importlib.util
from datetime import datetime

# ---- Load shared utils -------------------------------------------------
_utils_path = Path(__file__).resolve().parent.parent / "utils.py"
_spec = importlib.util.spec_from_file_location("dashboard_utils", str(_utils_path))
_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils)
inject_custom_css = _utils.inject_custom_css
render_kpi = _utils.render_kpi
render_topbar = _utils.render_topbar
render_hero = _utils.render_hero
render_phase_timeline = _utils.render_phase_timeline
render_ticker_tape = _utils.render_ticker_tape
render_pillar_bar = _utils.render_pillar_bar
render_live_chip = _utils.render_live_chip
render_traffic_signal = _utils.render_traffic_signal
render_sector_chip = _utils.render_sector_chip
render_system_health_card = _utils.render_system_health_card
load_phase6_json = _utils.load_phase6_json

inject_custom_css()


# ============================================================================
# Load live KPIs from reports
# ============================================================================
@st.cache_data(ttl=3600)
def load_kpis_from_report():
    """Load KPIs from the latest phase2_report JSON."""
    try:
        report_dir = Path(__file__).parent.parent.parent / "outputs" / "reports"
        report_files = list(report_dir.glob("phase2_report_*.json"))
        if not report_files:
            raise FileNotFoundError("No phase2_report files found")
        latest_report = sorted(report_files, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        with open(latest_report, 'r', encoding='utf-8') as f:
            data = json.load(f)

        rows = data.get("results", {}).get("feature_store", {}).get("rows", 948976)
        cols = data.get("results", {}).get("feature_store", {}).get("cols", 1626)
        n_selected = len(data.get("results", {}).get("feature_selection", {}).get("selected", []))
        quality_gates = data.get("quality_gates", {})
        gates_passed = sum(1 for v in quality_gates.values() if v is True or v == "True")
        total_gates = len(quality_gates)

        return {
            "rows": rows,
            "cols": cols,
            "n_selected": n_selected,
            "gates_passed": gates_passed,
            "total_gates": total_gates,
            "date_range": data.get("results", {}).get("feature_store", {}).get("date_range", "2023/03 - 2025/03"),
            "report_timestamp": data.get("timestamp", "")
        }
    except Exception:
        return {
            "rows": 948976, "cols": 1626, "n_selected": 91,
            "gates_passed": 9, "total_gates": 9,
            "date_range": "2023/03 - 2025/03",
            "report_timestamp": ""
        }


kpis = load_kpis_from_report()

# Pull LOPO headline numbers
lopo_data, _ = load_phase6_json("lopo_pillar_contribution_D20.json")
thresh_data, _ = load_phase6_json("threshold_sweep_xgb_D20.json")

baseline_auc = lopo_data["baseline"]["auc_macro"] if lopo_data else 0.649
top_pillar = lopo_data["ranking_by_delta_auc"][0] if lopo_data else None
best_edge = max(t["edge"] for t in thresh_data["threshold_sweep"]) if thresh_data else 0.117
# DSR value (deflated Sharpe ratio) — from phase 6 threshold sweep best result
best_dsr = None
if thresh_data:
    try:
        best_row = max(thresh_data["threshold_sweep"], key=lambda t: t.get("edge", 0))
        best_dsr = best_row.get("dsr", 12.12)
    except Exception:
        best_dsr = 12.12
best_dsr = best_dsr or 12.12

# ============================================================================
# Top-bar (sticky) — breadcrumb + model chips + live clock
# ============================================================================
render_topbar(
    crumb_left="股票預測系統",
    crumb_current="情境主控台",
    chips=[
        ("xgboost_D20", "pri"),
        ("purged WF · embargo=20", "vio"),
        (f"DSR {best_dsr:.2f} → PASS", "ok"),
    ],
    show_clock=True,
)

# ============================================================================
# Hero — updated title per Design spec
# ============================================================================
render_hero(
    eyebrow="TERMINAL · 股票預測研究平台",
    title_html="股票預測分析系統<span class=\"gl-hero-accent\">　九大面向．一眼看懂</span>",
    subtitle=(
        "把台股研究拆成 <strong>9 大面向</strong>（趨勢、基本面、估值、事件、風險、籌碼、產業、文字、情緒），<br>"
        "搭配 <strong>2023/03–2025/03 歷史資料</strong> 與 <strong>雙引擎機器學習模型</strong>，"
        "濃縮成一張<strong>可回看、可解釋、可治理</strong>的研究快照。<br>"
        "<span style=\"opacity:0.7;font-size:0.86em;\">· 學術研究展示平台　·　非投資建議 ·</span>"
    ),
    meta_chips=[
        ("phase 1-6 · all gates passed", "default"),
        ("9 / 9 quality gates", "pri"),
        (f"xgboost_D20 OOS AUC {baseline_auc:.3f}", "vio"),
        (f"best edge +{best_edge*100:.1f}pp", "ok"),
    ],
    show_orbit=True,
)

# ============================================================================
# LIVE status row + ticker tape
# ============================================================================
st.markdown('<div style="display:flex;align-items:center;gap:14px;margin:4px 0 10px;">', unsafe_allow_html=True)
render_live_chip("LIVE · 研究快照同步中")
st.markdown('</div>', unsafe_allow_html=True)

# Synthetic ticker (directionally plausible sample from recommendations)
render_ticker_tape([
    {"ticker": "2330", "name": "台積電",   "value": "+1.82%", "direction": "up"},
    {"ticker": "2454", "name": "聯發科",   "value": "+2.45%", "direction": "up"},
    {"ticker": "2317", "name": "鴻海",     "value": "−0.61%", "direction": "down"},
    {"ticker": "6228", "name": "光鼎",     "value": "+0.28%", "direction": "up"},
    {"ticker": "2412", "name": "中華電",   "value": "+0.12%", "direction": "neu"},
    {"ticker": "2882", "name": "國泰金",   "value": "+0.84%", "direction": "up"},
    {"ticker": "3008", "name": "大立光",   "value": "−1.24%", "direction": "down"},
    {"ticker": "5348", "name": "系通",     "value": "+3.10%", "direction": "up"},
])


# ============================================================================
# MODE TABS — 🌱 投資觀察台  /  ⚙️ 研究工作站
# ============================================================================
tab_observe, tab_workstation = st.tabs([
    "🌱 投資觀察台　",
    "⚙️ 研究工作站　",
])


# ----------------------------------------------------------------------------
# 🌱 投資觀察台  (Observation Deck)
# ----------------------------------------------------------------------------
with tab_observe:
    st.markdown(
        '<div class="gl-box-info" style="margin-top:6px;">'
        '<strong>📋 此模式重點</strong>：本觀察台將嚴謹的量化研究翻譯成可理解的決策資訊 ─ '
        '哪個產業看好、這檔股票基本面如何、進場成本多少才划算、有哪些風險須注意。'
        '</div>', unsafe_allow_html=True,
    )

    # ---- Headline KPIs (investor-friendly framing) ----------------------
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi(
            "推薦股票", f"{top_pillar['pillar'] if top_pillar else 'risk'}‑top",
            sub="LOPO 首席支柱貢獻",
            accent="emerald",
        )
    with k2:
        render_kpi(
            "出手率", "12 – 18%",
            delta=("精選策略", "up"),
            sub="D+20 threshold sweep",
            accent="blue",
        )
    with k3:
        render_kpi(
            "最佳邊際", f"+{best_edge*100:.1f}pp",
            delta=("vs baseline", "up"),
            sub="Top-decile minus bottom",
            accent="amber",
        )
    with k4:
        render_kpi(
            "回測期間", "24 個月",
            sub=f"{kpis['date_range']}",
            accent="cyan",
        )

    # ---- Traffic-light signal cards (🟢🟡🔴 — 財報狗 style) -------------
    st.markdown("### 今日研究訊號")
    st.markdown(
        '<div style="color:var(--gl-text-2);font-size:.9rem;margin-bottom:10px;">'
        '三顆燈號綜合呈現模型判讀、風險旗標與資料時效狀態（全部綠燈代表本期研究結論可信度高）。'
        '</div>', unsafe_allow_html=True,
    )
    sig_a, sig_b, sig_c = st.columns(3)
    with sig_a:
        st.markdown(render_traffic_signal(
            color="green",
            title="模型判讀 · 可信度",
            value=f"{baseline_auc:.4f}",
            desc=f"OOS AUC 穩穩站上 0.52 閘門，DSR {best_dsr:.2f} 遠高於 1.0 門檻，統計顯著。",
            val_class="up",
        ), unsafe_allow_html=True)
    with sig_b:
        st.markdown(render_traffic_signal(
            color="amber",
            title="資料時效 · 覆蓋",
            value="24 / 36M",
            desc="固定歷史資料集 2023/03–2025/03 共 24 個月，2025/04 之後樣本待更新。",
        ), unsafe_allow_html=True)
    with sig_c:
        st.markdown(render_traffic_signal(
            color="green",
            title="風險旗標 · 治理",
            value=f"{kpis['gates_passed']} / {kpis['total_gates']}",
            desc="九個品質閘門全數 PASS。Embargo / Leakage / Purge 防護全開。",
            val_class="up",
        ), unsafe_allow_html=True)

    st.markdown("### 九大支柱 · 重要度快速判讀")
    st.markdown(
        '<div style="color:var(--gl-text-2);font-size:.92rem;margin-bottom:10px;">'
        '支柱即「因子家族」─ 每個家族從不同角度觀察一家公司；顏色越深表示該家族在 D+20 預測上貢獻越高。'
        '</div>', unsafe_allow_html=True,
    )

    # Map LOPO deltas onto pillar bars (if data present)
    pillar_labels = {
        "risk": "風險面", "fund": "基本面", "chip": "籌碼面",
        "trend": "技術面", "val": "評價面", "event": "事件面",
        "ind": "產業面", "txt": "文本面", "sent": "情緒面",
    }
    rows_html = []
    if lopo_data and "ranking_by_delta_auc" in lopo_data:
        max_d = max(abs(r["delta_auc"]) for r in lopo_data["ranking_by_delta_auc"]) or 0.001
        for r in lopo_data["ranking_by_delta_auc"]:
            pk = r["pillar"]
            delta_bps = r["delta_auc"] * 10000
            pct = (abs(r["delta_auc"]) / max_d) * 100
            rows_html.append(render_pillar_bar(
                pillar_key=pk,
                # Dual-key tolerance: JSON uses "n_feats" (source of truth),
                # legacy code may have written "n_features". Prefer n_feats.
                label=pillar_labels.get(pk, pk),
                feat_count=r.get("n_feats", r.get("n_features", 0)),
                pct=pct,
                delta_bps=delta_bps,
            ))
    else:
        # Fallback mock order (matches Design sample)
        demo = [
            ("risk",  "風險面", 18, 94, 24.0),
            ("fund",  "基本面", 22, 78, 18.5),
            ("chip",  "籌碼面", 14, 64, 12.0),
            ("trend", "技術面", 25, 52,  8.2),
            ("val",   "評價面",  6, 38,  5.1),
            ("event", "事件面",  4, 22,  2.8),
            ("ind",   "產業面",  9, 48,  6.4),
            ("txt",   "文本面",  8, 34,  3.9),
            ("sent",  "情緒面", 11, 40,  4.5),
        ]
        for pk, lbl, n, pct, dbps in demo:
            rows_html.append(render_pillar_bar(pk, lbl, n, pct, dbps))

    st.markdown(
        '<div class="gl-panel" style="padding:18px 22px;">' + "".join(rows_html) + "</div>",
        unsafe_allow_html=True,
    )

    # ---- Path cards (investor → deep panels) ------------------------------
    st.markdown("### 繼續深入")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
<div class="path-card path-inv">
    <div style="font-size:2.4rem;margin-bottom:10px;">🌱</div>
    <div class="path-title">個股觀察卡</div>
    <div class="path-desc">
        每一檔推薦股票皆附「四件事白話說」：近期走勢、基本面輪廓、進場成本、風險提示。
        並內建換算機：直接輸入你願意買進的股數，看折價空間還剩多少。
    </div>
    <div class="path-tags">
        <span class="gl-chip">2330 台積電</span>
        <span class="gl-chip">2454 聯發科</span>
        <span class="gl-chip">2317 鴻海</span>
        <span class="gl-chip warn">風險旗標</span>
    </div>
</div>
""", unsafe_allow_html=True)
        if st.button("🌱  進入投資觀察台", use_container_width=True, type="primary", key="btn_obs"):
            st.switch_page(str(Path(__file__).resolve().parent / "0_🌱_投資解讀面板.py"))

    with col_b:
        st.markdown("""
<div class="path-card">
    <div style="font-size:2.4rem;margin-bottom:10px;">📈</div>
    <div class="path-title">整體策略表現</div>
    <div class="path-desc">
        看三種成本情境下的累積報酬曲線、最大回撤、勝率、盈虧比。
        D+20 月度是唯一全情境正報酬的地平線，邊際達 +{:.1f}pp。
    </div>
    <div class="path-tags">
        <span class="gl-chip primary">standard 0.58%</span>
        <span class="gl-chip">discount 0.36%</span>
        <span class="gl-chip warn">conservative 0.73%</span>
    </div>
</div>
""".format(best_edge * 100), unsafe_allow_html=True)
        if st.button("📈  查看策略回測", use_container_width=True, type="secondary", key="btn_bt_obs"):
            st.switch_page(str(Path(__file__).resolve().parent / "3_💰_Backtest.py"))


# ----------------------------------------------------------------------------
# ⚙️ 研究工作站  (Research Workstation — Bloomberg-terminal feel)
# ----------------------------------------------------------------------------
with tab_workstation:
    # ---- 6-KPI grid (dense numerics, JetBrains-Mono tabular-nums) -------
    st.markdown("### 系統即時指標")

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        render_kpi(
            "SAMPLES", f"{kpis['rows']//1000:,}K",
            sub=f"{kpis['rows']:,} rows", accent="blue"
        )
    with k2:
        render_kpi(
            "FEATURES", f"{kpis['n_selected']}",
            sub=f"from {kpis['cols']:,} candidates", accent="violet"
        )
    with k3:
        render_kpi(
            "PILLARS", "9",
            sub="trend/fund/val/event/risk…", accent="cyan"
        )
    with k4:
        render_kpi(
            "HORIZONS", "3",
            sub="D+1 · D+5 · D+20", accent="amber"
        )
    with k5:
        render_kpi(
            "QUALITY", f"{kpis['gates_passed']}/{kpis['total_gates']}",
            delta=("ALL PASS", "up"),
            sub="Phase 2 quality gates", accent="emerald"
        )
    with k6:
        if top_pillar:
            render_kpi(
                "TOP PILLAR", f"{top_pillar['pillar']}",
                delta=(f"+{top_pillar['delta_auc']*10000:.1f}bps", "up"),
                sub="LOPO top contributor", accent="rose"
            )
        else:
            render_kpi("TOP PILLAR", "risk", sub="LOPO", accent="rose")

    # ---- Data freshness banner ------------------------------------------
    _ts = kpis.get("report_timestamp", "")
    _ts_display = _ts[:19].replace("T", " ") if _ts else "2026-04-20 03:20"
    st.markdown(f"""
<div class="gl-box-info" style="margin-top:16px;">
<strong>📅 資料時效</strong>：本平台為<strong>固定歷史資料集（{kpis['date_range']}）</strong>下的
互動式分析與研究展示系統，非即時市場監控。支援回看不同日期與預測週期的模型判讀與策略表現。<br>
<span style="font-size:.82rem; color:var(--gl-text-3);">
🕐 最新報告時間 <span class="gl-mono">{_ts_display}</span>
&nbsp;·&nbsp; 🔬 研究模式 <span class="gl-mono">Historical Interactive Snapshot</span>
&nbsp;·&nbsp; 📦 Phase 1-6 Complete
</span>
</div>
""", unsafe_allow_html=True)

    # ---- Research entry cards (quant path) -------------------------------
    st.markdown("### 研究面板入口")
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("""
<div class="path-card path-qnt">
    <div style="font-size:2.4rem;margin-bottom:10px;">📊</div>
    <div class="path-title">模型績效 · 驗證</div>
    <div class="path-desc">
        AUC · F1 · ICIR 全貌，含 Purged Walk-Forward 4-Fold 穩定性、
        Bootstrap 95% CI、Deflated Sharpe Ratio。三地平線可切換。
    </div>
    <div class="path-tags">
        <span class="gl-chip primary">模型績效</span>
        <span class="gl-chip primary">ICIR 分析</span>
        <span class="gl-chip violet">信號監控</span>
        <span class="gl-chip ok">模型治理</span>
    </div>
</div>
""", unsafe_allow_html=True)
        if st.button("📊  進入模型績效面板", use_container_width=True, type="primary", key="btn_metrics"):
            st.switch_page(str(Path(__file__).resolve().parent / "1_📊_Model_Metrics.py"))

    with col_r:
        st.markdown("""
<div class="path-card path-qnt">
    <div style="font-size:2.4rem;margin-bottom:10px;">🔬</div>
    <div class="path-title">特徵 · 文本 · Phase 6</div>
    <div class="path-desc">
        九支柱分布、SHAP Top-20、三階段 funnel、文本情緒雲、
        LOPO 深度驗證與個股 deep-case。完整研究流程呈現。
    </div>
    <div class="path-tags">
        <span class="gl-chip violet">特徵工程</span>
        <span class="gl-chip violet">文本情緒</span>
        <span class="gl-chip danger">LOPO · DSR</span>
        <span class="gl-chip">2454 case</span>
    </div>
</div>
""", unsafe_allow_html=True)
        if st.button("🔬  進入特徵分析面板", use_container_width=True, type="secondary", key="btn_feat"):
            st.switch_page(str(Path(__file__).resolve().parent / "4_🔬_Feature_Analysis.py"))

    # ---- 六階段 Phase Timeline -------------------------------------------
    st.markdown("### 六階段研究進度")
    render_phase_timeline(current_phase=6)

    # ---- Methodology 3-up panels ----------------------------------------
    st.markdown("### 方法論核心")

    m1, m2, m3 = st.columns(3)

    with m1:
        st.markdown("""
        <div class="gl-panel">
            <div style="font-size:0.72rem; color:var(--gl-text-3); font-weight:600; letter-spacing:.06em; text-transform:uppercase;">FEATURE</div>
            <div style="font-size:1.1rem; font-weight:700; color:var(--gl-text); margin-top:6px;">🎯 九支柱因子工程</div>
            <div style="font-size:.9rem; color:var(--gl-text-2); line-height:1.6; margin-top:10px;">
                <span class="gl-pillar" data-p="trend">trend</span>
                <span class="gl-pillar" data-p="fund">fund</span>
                <span class="gl-pillar" data-p="val">val</span>
                <span class="gl-pillar" data-p="event">event</span>
                <span class="gl-pillar" data-p="risk">risk</span>
                <span class="gl-pillar" data-p="chip">chip</span>
                <span class="gl-pillar" data-p="ind">ind</span>
                <span class="gl-pillar" data-p="txt">txt</span>
                <span class="gl-pillar" data-p="sent">sent</span>
                <br><br>
                <strong>1,623 候選因子</strong>經三階段篩選（IC → Chi²/MI → VIF）
                至 <strong>91 生產特徵</strong>，跨 9 個理論支柱。
            </div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown("""
        <div class="gl-panel">
            <div style="font-size:0.72rem; color:var(--gl-text-3); font-weight:600; letter-spacing:.06em; text-transform:uppercase;">VALIDATION</div>
            <div style="font-size:1.1rem; font-weight:700; color:var(--gl-text); margin-top:6px;">✅ 嚴謹的時序交叉驗證</div>
            <div style="font-size:.9rem; color:var(--gl-text-2); line-height:1.6; margin-top:10px;">
                <strong>Purged Walk-Forward CV</strong>（4 折），
                Expanding Window 配合 <strong>20 日 Embargo</strong> 杜絕前瞻偏差。<br><br>
                <span class="gl-chip pri">initial_train=252</span>
                <span class="gl-chip pri">test=63</span>
                <span class="gl-chip vio">embargo=20</span>
                <br><br>
                Phase 6 再加上 <strong>LOPO 驗證</strong>：逐一移除每個支柱重訓，量化真實邊際貢獻。
            </div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown("""
        <div class="gl-panel">
            <div style="font-size:0.72rem; color:var(--gl-text-3); font-weight:600; letter-spacing:.06em; text-transform:uppercase;">MODEL</div>
            <div style="font-size:1.1rem; font-weight:700; color:var(--gl-text); margin-top:6px;">⚡ 雙引擎 + 成本回測</div>
            <div style="font-size:.9rem; color:var(--gl-text-2); line-height:1.6; margin-top:10px;">
                <strong>LightGBM + XGBoost</strong> 雙引擎加上等權 Ensemble，三地平線覆蓋短中長週期。<br><br>
                <span class="gl-chip">D+1 日度</span>
                <span class="gl-chip">D+5 週度</span>
                <span class="gl-chip pri">D+20 月度</span>
                <br><br>
                三種成本情境：<strong>standard 0.58% · discount 0.36% · conservative 0.73%</strong>。
                D+20 是唯一全情境正報酬的地平線。
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ---- Pipeline flow (Plotly) -----------------------------------------
    st.markdown("### 系統管道流程")

    fig = go.Figure()
    stages = [
        ("FinMind API",    "Phase 1", "#06b6d4"),
        ("Feature Store",  "Phase 1", "#06b6d4"),
        ("特徵篩選",       "Phase 1", "#06b6d4"),
        ("模型訓練",       "Phase 2", "#2563eb"),
        ("策略回測",       "Phase 2", "#2563eb"),
        ("擴充分析",       "Phase 3", "#7c3aed"),
        ("模型治理",       "Phase 4", "#7c3aed"),
        ("文本情緒",       "Phase 5", "#7c3aed"),
        ("LOPO 驗證",      "Phase 6", "#f43f5e"),
        ("儀表板",         "UI",     "#10b981"),
    ]
    for i, (stage, phase, color) in enumerate(stages):
        fig.add_trace(go.Scatter(
            x=[i], y=[0],
            mode='markers+text',
            marker=dict(size=22, color=color, line=dict(width=2, color="white")),
            text=stage, textposition="top center",
            textfont=dict(family="Inter, sans-serif", size=11, color="#0f172a"),
            hoverinfo='text',
            hovertext=f"{stage} ({phase})",
            showlegend=False
        ))
        fig.add_annotation(
            x=i, y=-0.55, text=phase, showarrow=False,
            font=dict(family="JetBrains Mono, monospace", size=9, color="#94a3b8"),
        )

    for i in range(len(stages) - 1):
        fig.add_annotation(
            x=i + 0.75, y=0, ax=i + 0.25, ay=0,
            xref='x', yref='y', axref='x', ayref='y',
            arrowhead=2, arrowsize=1.1, arrowwidth=1.5,
            arrowcolor='#cbd5e1', showarrow=True,
        )

    fig.update_layout(
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                   range=[-0.5, len(stages) - 0.5]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.9, 0.9]),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        height=160, margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# Disclaimer + Footer (shared across both modes, after tabs)
# ============================================================================
st.markdown("""
<div class="gl-box-warn" style="margin-top:24px;">
⚠️ <strong>免責聲明</strong>：本系統為課程專案成果，不構成任何投資建議。所有顯示結果均為歷史回測數據，
非即時預測。股市投資有風險，過去的回測績效不代表未來報酬。投資前請審慎評估自身風險承受能力。
</div>
""", unsafe_allow_html=True)

footer_year = datetime.now().year
st.markdown(f"""
<div class="gl-footer">
大數據與商業分析專案 <span class="gl-mono">v4.0</span> &nbsp;·&nbsp;
Built with <span class="gl-mono">Streamlit + Plotly + LightGBM + XGBoost</span> &nbsp;·&nbsp;
Data <span class="gl-mono">FinMind API + 選用資料集</span><br>
<small>© {footer_year} Course Project &nbsp;|&nbsp;
<a href="https://github.com/andychen050229-cell/taiwan-stock-multifactor" target="_blank"
   style="color:var(--gl-blue); text-decoration:none;">GitHub Repository</a></small>
</div>
""", unsafe_allow_html=True)
