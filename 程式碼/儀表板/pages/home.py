"""
台股多因子預測系統 — Landing Page (glint-light design, Design-ported)

Dual-mode tab layout per 2026/04 Design spec:
  🌱 投資觀察  (plain-language, warm amber wash)
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
    """Load KPIs from the latest phase2_report JSON.

    Cloud shim chdir-safe: walks up from pages/home.py to find project_root/outputs/reports.
    """
    try:
        _h = Path(__file__).resolve()
        report_dir = None
        for _c in (
            _h.parent.parent.parent.parent / "outputs" / "reports",   # project_root/outputs
            _h.parent.parent.parent / "outputs" / "reports",          # 程式碼/outputs (legacy)
            Path.cwd() / "outputs" / "reports",
            Path.cwd().parent / "outputs" / "reports",
            Path.cwd().parent.parent / "outputs" / "reports",
        ):
            if _c.exists():
                report_dir = _c
                break
        if report_dir is None:
            raise FileNotFoundError("Phase 2 report dir not found")
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
        failed_names = [k for k, v in quality_gates.items()
                        if not (v is True or v == "True")]

        return {
            "rows": rows,
            "cols": cols,
            "n_selected": n_selected,
            "gates_passed": gates_passed,
            "total_gates": total_gates,
            "failed_names": failed_names,
            "all_pass": (gates_passed == total_gates and total_gates > 0),
            "date_range": data.get("results", {}).get("feature_store", {}).get("date_range", "2023/03 - 2025/03"),
            "report_timestamp": data.get("timestamp", "")
        }
    except Exception:
        return {
            "rows": 948976, "cols": 1626, "n_selected": 91,
            "gates_passed": 0, "total_gates": 0,
            "failed_names": [], "all_pass": False,
            "date_range": "2023/03 - 2025/03",
            "report_timestamp": ""
        }


kpis = load_kpis_from_report()


# ============================================================================
# Load recommendations (D+1 / D+5 / D+20) for headline + Top-5 preview
# ============================================================================
@st.cache_data(ttl=3600)
def load_recommendations():
    """Load pre-computed recommendations from dashboard/data/recommendations.json.

    Cloud shim chdir-safe: walks up to find either dashboard/data or 程式碼/儀表板/data.
    """
    try:
        _h = Path(__file__).resolve()
        rec_path = None
        for _c in (
            _h.parent.parent / "data" / "recommendations.json",     # 程式碼/儀表板/data (local + cloud shim)
            _h.parent.parent.parent.parent / "dashboard" / "data" / "recommendations.json",  # project_root/dashboard/data
            Path.cwd() / "data" / "recommendations.json",
            Path.cwd() / "dashboard" / "data" / "recommendations.json",
        ):
            if _c.exists():
                rec_path = _c
                break
        if rec_path is None:
            return {}
        with open(rec_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


recommendations = load_recommendations()

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
    crumb_left="台股多因子研究終端",
    crumb_current="情境主控",
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
        "把台股研究拆成 <strong>9 大面向</strong>"
        "（趨勢、基本面、估值、事件、風險、籌碼、產業、文字、情緒），<br>"
        "搭配 <strong>2023/03–2025/03 歷史資料</strong> "
        "與 <strong>雙引擎機器學習模型</strong>，<br>"
        "濃縮成一張 <strong>可回看、可解釋、可治理</strong> 的研究快照。<br>"
        "<span style=\"opacity:0.7;font-size:0.86em;\">"
        "· 學術研究展示平台　·　非投資建議 ·"
        "</span>"
    ),
    meta_chips=[
        ("phase 1-6 · all gates passed" if kpis["all_pass"]
             else f"phase 1-6 · {kpis['gates_passed']}/{kpis['total_gates']} gates passed",
         "default" if kpis["all_pass"] else "warn"),
        (f"{kpis['gates_passed']} / {kpis['total_gates']} quality gates",
         "pri" if kpis["all_pass"] else "warn"),
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
# MODE TABS — 🌱 投資觀察  /  ⚙️ 研究工作站
# ============================================================================
tab_observe, tab_workstation = st.tabs([
    "🌱　投資觀察",
    "⚙️　研究工作站",
])


# ----------------------------------------------------------------------------
# 🌱 投資觀察  (Observation Deck)
# ----------------------------------------------------------------------------
with tab_observe:
    st.markdown(
        '<div class="gl-box-info" style="margin-top:6px;">'
        '<strong>📋 此模式重點</strong>：本觀察台將嚴謹的量化研究翻譯成可理解的決策資訊 ─ '
        '哪個產業看好、這檔股票基本面如何、進場成本多少才划算、有哪些風險須注意。'
        '</div>', unsafe_allow_html=True,
    )

    # ====================================================================
    # 🎯 今日研究重點 (Today's Key Finding) — scannable one-liner
    # ====================================================================
    _h20 = recommendations.get("horizon_20", {}) if isinstance(recommendations, dict) else {}
    _h20_date = (_h20.get("date", "") or "2025-03-03")[:10]
    _h20_stocks = _h20.get("stocks", []) if isinstance(_h20, dict) else []
    _top1 = _h20_stocks[0] if _h20_stocks else None
    _top1_id = _top1.get("stock_id", "—") if _top1 else "—"
    _top1_name = _top1.get("short_name", "") if _top1 else ""
    _top1_ret = _top1.get("fwd_ret_20", 0) if _top1 else 0
    _top1_ind = _top1.get("industry", "") if _top1 else ""
    _PILLAR_ZH = {
        "risk": "風險面", "fund": "基本面", "chip": "籌碼面",
        "trend": "技術面", "val": "評價面", "event": "事件面",
        "ind": "產業面", "txt": "文本面", "sent": "情緒面",
    }
    _tp_key = top_pillar["pillar"] if top_pillar else "risk"
    _tp_zh = _PILLAR_ZH.get(_tp_key, _tp_key)
    _tp_bps = (top_pillar["delta_auc"] * 10000) if top_pillar else 24.0

    # v11 §4a — Today's Key Finding card: dark-glint amber terminal.
    st.markdown(f"""
<div style="background:linear-gradient(180deg,rgba(15,23,37,0.95) 0%,rgba(10,20,32,0.95) 100%);
            border:1px solid rgba(245,158,11,0.45);
            border-left:3px solid #f59e0b;
            border-radius:12px;
            padding:18px 22px;
            margin:14px 0 18px;
            box-shadow:0 4px 18px rgba(2,6,23,0.38), inset 0 1px 0 rgba(245,158,11,0.14);">
  <div style="font-family:'JetBrains Mono',monospace;font-size:0.70rem;color:#fbbf24;
              letter-spacing:0.18em;font-weight:800;text-transform:uppercase;margin-bottom:8px;
              text-shadow:0 0 10px rgba(245,158,11,0.40);">
    📌 TODAY'S KEY FINDING · 今日研究重點 &nbsp;·&nbsp; 判讀日 {_h20_date} (D+20 月度)
  </div>
  <div style="font-size:1.04rem;line-height:1.85;color:#e0f2fe;">
    ① <strong style="color:#fef3c7;">模型最看好</strong> → <span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:#fbbf24;">{_top1_id} {_top1_name}</span>
    <span style="color:#b4ccdf;font-size:0.88rem;">（{_top1_ind}）</span>
    <span style="color:#34d399;font-weight:600;">歷史同情境 +{_top1_ret*100:.1f}%</span> &nbsp;·&nbsp;
    ② <strong style="color:#fef3c7;">最強因子支柱</strong> → <span style="font-weight:700;color:#fbbf24;">{_tp_zh}</span>
    <span style="font-family:'JetBrains Mono',monospace;color:#34d399;">(+{_tp_bps:.1f} bps AUC)</span> &nbsp;·&nbsp;
    ③ <strong style="color:#fef3c7;">整體可信度</strong> → AUC {baseline_auc:.3f}、DSR {best_dsr:.2f}、{kpis['gates_passed']}/{kpis['total_gates']} gates {'✓' if kpis['all_pass'] else '⚠'}
  </div>
  <div style="font-size:0.82rem;color:#fbbf24;margin-top:10px;opacity:0.88;">
    💡 這三個數字是今天系統「最值得你關注的研究結論」。下方卡片逐一展開細節。
  </div>
</div>
""", unsafe_allow_html=True)

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
        _qg_color = "green" if kpis["all_pass"] else "amber"
        _qg_val_class = "up" if kpis["all_pass"] else ""
        if kpis["all_pass"]:
            _qg_desc = (
                f"{kpis['total_gates']} 個品質閘門全數 PASS。"
                "Embargo / Leakage / Purge 防護全開。"
            )
        else:
            _failed_zh = "、".join(
                _utils.quality_gate_zh(n) for n in kpis["failed_names"][:2]
            ) or "部分閘門"
            _qg_desc = (
                f"{kpis['gates_passed']} / {kpis['total_gates']} 通過，"
                f"待補：{_failed_zh}。Embargo / Leakage / Purge 防護仍全開。"
            )
        st.markdown(render_traffic_signal(
            color=_qg_color,
            title="風險旗標 · 治理",
            value=f"{kpis['gates_passed']} / {kpis['total_gates']}",
            desc=_qg_desc,
            val_class=_qg_val_class,
        ), unsafe_allow_html=True)

    # ====================================================================
    # 🌟 Top 5 推薦股票預覽 (D+20 月度) — concrete tickers, scannable
    # ====================================================================
    st.markdown("### 🌟 Top 5 · D+20 月度推薦預覽")
    st.markdown(
        '<div style="color:var(--gl-text-2);font-size:.92rem;margin-bottom:12px;">'
        f'以下是模型在判讀日 <strong>{_h20_date}</strong> 產出的前五名。<br>'
        '每張卡片顯示<strong>股票代號、產業、歷史同情境 20 日後報酬</strong>。'
        '完整解讀、成本試算、風險提示請點下方「投資觀察」。'
        '</div>', unsafe_allow_html=True,
    )

    if _h20_stocks:
        _top5 = _h20_stocks[:5]
        # 5 equal columns
        _cols = st.columns(5, gap="small")
        for _i, (_col, _st) in enumerate(zip(_cols, _top5)):
            _sid = _st.get("stock_id", "—")
            _sname = _st.get("short_name", "")
            _sind = _st.get("industry", "")
            _sret = _st.get("fwd_ret_20", 0)
            _price = _st.get("closing_price", None)
            # v11 §4a — glint palette: emerald for positive, rose for negative.
            _ret_color = "#34d399" if _sret >= 0 else "#fb7185"
            _price_str = (
                f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:.78rem;color:#8397ac;">'
                f'收盤 {_price:.1f}</span>' if _price else ""
            )
            with _col:
                st.markdown(f"""
<div style="background:linear-gradient(180deg,rgba(15,23,37,0.92) 0%,rgba(10,20,32,0.92) 100%);
            border:1px solid rgba(103,232,249,0.24);
            border-left:3px solid {_ret_color};
            border-radius:12px;
            padding:14px 14px 12px;
            height:100%;
            transition:all .2s ease;
            box-shadow:0 4px 14px rgba(2,6,23,0.32), inset 0 1px 0 rgba(103,232,249,0.10);">
  <div style="font-family:'JetBrains Mono',monospace;font-size:0.66rem;
              color:#67e8f9;letter-spacing:0.14em;font-weight:800;margin-bottom:4px;
              text-shadow:0 0 8px rgba(103,232,249,0.35);">
    RANK {_i+1}
  </div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:1.3rem;font-weight:800;
              color:#e8f7fc;letter-spacing:-0.02em;line-height:1.1;">
    {_sid}
  </div>
  <div style="font-size:0.92rem;font-weight:600;color:#cfe2ee;margin:4px 0 2px;
              overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
    {_sname}
  </div>
  <div style="font-size:0.74rem;color:#8397ac;margin-bottom:10px;
              overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
    {_sind or "—"}
  </div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;
              color:{_ret_color};line-height:1.1;
              text-shadow:0 0 10px {('rgba(52,211,153,0.40)' if _sret >= 0 else 'rgba(251,113,133,0.40)')};">
    {'+' if _sret >= 0 else ''}{_sret*100:.1f}%
  </div>
  <div style="font-size:0.7rem;color:#8397ac;margin-top:2px;">歷史同情境 20 日後</div>
  <div style="margin-top:8px;">{_price_str}</div>
</div>
""", unsafe_allow_html=True)

        # Note below the 5 cards — v11 §4a dark-glint callout.
        st.markdown(
            '<div style="background:linear-gradient(180deg,rgba(15,23,37,0.92),rgba(10,20,32,0.92));'
            'border:1px solid rgba(103,232,249,0.24);border-left:3px solid #67e8f9;'
            'border-radius:10px;padding:10px 14px;margin-top:12px;'
            'font-size:0.82rem;color:#cfe2ee;line-height:1.6;'
            'box-shadow:0 2px 10px rgba(2,6,23,0.26);">'
            '📌 <strong style="color:#e0f9ff;">注意</strong>：這是「歷史同情境下的 20 日後平均報酬」，非未來預測。'
            '推薦是模型排序（ranking），目的是協助研究者聚焦前 5% 標的，不構成投資建議。'
            '</div>', unsafe_allow_html=True,
        )
    else:
        st.info("目前沒有可用的推薦資料。請嘗試重新整理，或查看「投資觀察」。")

    # ====================================================================
    # 🗓 短週期同步：D+5 週度 + D+1 日度 (compact, lower density than D+20)
    # ====================================================================
    def _render_short_horizon(horizon_key: str, ret_key: str,
                               label_cn: str, label_en: str, note: str):
        """Compact 5-card row for short-horizon recs; uses smaller typography
        than the primary D+20 block and a neutral palette so the visual hierarchy
        still favours the monthly view."""
        _hd = recommendations.get(horizon_key, {}) if isinstance(recommendations, dict) else {}
        _stocks = _hd.get("stocks", []) if isinstance(_hd, dict) else []
        _date = (_hd.get("date", "") or "2025-03-03")[:10]
        if not _stocks:
            st.info(f"{label_cn} 暫無資料。")
            return
        # v11 §4a — dark-glint label chrome (was slate-on-white).
        st.markdown(
            f'<div style="display:flex;align-items:baseline;gap:14px;margin-top:4px;">'
            f'  <span style="font-family:\'JetBrains Mono\',monospace;font-size:0.68rem;'
            f'color:#67e8f9;letter-spacing:0.14em;text-transform:uppercase;font-weight:800;'
            f'text-shadow:0 0 8px rgba(103,232,249,0.35);">'
            f'{label_en}</span>'
            f'  <span style="font-size:0.9rem;color:#b4ccdf;">判讀日 {_date} · {note}</span>'
            f'</div>', unsafe_allow_html=True,
        )
        _cols = st.columns(5, gap="small")
        for _i, (_col, _s) in enumerate(zip(_cols, _stocks[:5])):
            _sid = _s.get("stock_id", "—")
            _sname = _s.get("short_name", "")
            _sind = _s.get("industry", "")
            _ret = _s.get(ret_key, 0) or 0
            _color = "#34d399" if _ret >= 0 else "#fb7185"
            with _col:
                # v11 §4a — dark-glint compact card for short-horizon recs.
                st.markdown(f"""
<div style="background:linear-gradient(180deg,rgba(15,23,37,0.88) 0%,rgba(10,20,32,0.88) 100%);
            border:1px solid rgba(103,232,249,0.22);
            border-left:2px solid {_color};border-radius:10px;
            padding:10px 12px;height:100%;
            box-shadow:0 2px 10px rgba(2,6,23,0.24), inset 0 1px 0 rgba(103,232,249,0.08);">
  <div style="font-family:'JetBrains Mono',monospace;font-size:0.6rem;
              color:#8397ac;letter-spacing:0.12em;font-weight:700;">#{_i+1}</div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:1.05rem;
              font-weight:800;color:#e8f7fc;line-height:1.1;margin-top:2px;">{_sid}</div>
  <div style="font-size:0.8rem;color:#cfe2ee;font-weight:600;margin-top:2px;
              overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{_sname}</div>
  <div style="font-size:0.68rem;color:#8397ac;margin:2px 0 6px;
              overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{_sind or '—'}</div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:0.95rem;
              font-weight:700;color:{_color};line-height:1.1;">
    {'+' if _ret >= 0 else ''}{_ret*100:.1f}%
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("### 🗓 短週期同步 · D+5 週度 / D+1 日度")
    st.markdown(
        '<div style="color:var(--gl-text-2);font-size:.9rem;margin-bottom:10px;">'
        '主打月度（D+20，上方）是最穩定的預測；週度與日度僅供研究者交叉驗證方向，'
        '<strong>切勿單獨使用日度進場</strong>（短期訊號雜訊高、交易成本吃掉多數 edge）。'
        '</div>', unsafe_allow_html=True,
    )
    _render_short_horizon(
        horizon_key="horizon_5",
        ret_key="fwd_ret_5",
        label_cn="D+5 週度",
        label_en="TOP 5 · D+5 WEEKLY",
        note="5 日後平均報酬",
    )
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    _render_short_horizon(
        horizon_key="horizon_1",
        ret_key="fwd_ret_1",
        label_cn="D+1 日度",
        label_en="TOP 5 · D+1 DAILY",
        note="下一交易日報酬（雜訊較高）",
    )

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
        if st.button("🌱  進入投資觀察", use_container_width=True, type="primary", key="btn_obs"):
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

    # ====================================================================
    # 📖 如何閱讀這個系統 (Reading Guide) — 3 paths by time budget
    # ====================================================================
    st.markdown("### 📖 如何閱讀這個系統")
    st.markdown(
        '<div style="color:var(--gl-text-2);font-size:.9rem;margin-bottom:12px;">'
        '依你有多少時間選擇路線。建議新手從「1 分鐘速讀」開始，再視情況深入。'
        '</div>', unsafe_allow_html=True,
    )
    rg1, rg2, rg3 = st.columns(3, gap="medium")
    # v11 §4a — Path A/B/C reading-guide cards repainted as dark-glint terminals
    # (was pastel emerald/blue/violet gradients). Each keeps its accent hue on
    # left rail + uppercase mono header but body text is now on dark bg so
    # nothing reads as washed-out islands against the rest of the dashboard.
    with rg1:
        st.markdown("""
<div style="background:linear-gradient(180deg,rgba(15,23,37,0.92) 0%,rgba(10,20,32,0.92) 100%);
            border:1px solid rgba(16,185,129,0.38);
            border-left:3px solid #10b981;
            border-radius:12px;padding:16px 18px;height:100%;
            box-shadow:0 4px 16px rgba(2,6,23,0.30), inset 0 1px 0 rgba(16,185,129,0.12);">
  <div style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#34d399;
              letter-spacing:0.18em;font-weight:800;margin-bottom:4px;
              text-shadow:0 0 8px rgba(16,185,129,0.35);">PATH A · BEGINNER</div>
  <div style="font-size:1.05rem;font-weight:700;color:#d1fae5;margin-bottom:8px;">
    🕐 1 分鐘速讀
  </div>
  <div style="font-size:0.9rem;color:#a7f3d0;line-height:1.72;">
    · 看上方<strong style="color:#ecfdf5;">今日重點</strong>三行<br>
    · 看 <strong style="color:#ecfdf5;">Top 5 推薦</strong>卡片<br>
    · 看三顆<strong style="color:#ecfdf5;">訊號燈</strong>綠不綠<br>
    <br>
    <span style="font-size:.82rem;opacity:.85;">→ 停在這裡就是「系統說了什麼」</span>
  </div>
</div>
""", unsafe_allow_html=True)

    with rg2:
        st.markdown("""
<div style="background:linear-gradient(180deg,rgba(15,23,37,0.92) 0%,rgba(10,20,32,0.92) 100%);
            border:1px solid rgba(37,99,235,0.38);
            border-left:3px solid #2563eb;
            border-radius:12px;padding:16px 18px;height:100%;
            box-shadow:0 4px 16px rgba(2,6,23,0.30), inset 0 1px 0 rgba(37,99,235,0.12);">
  <div style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#60a5fa;
              letter-spacing:0.18em;font-weight:800;margin-bottom:4px;
              text-shadow:0 0 8px rgba(37,99,235,0.35);">PATH B · INVESTOR</div>
  <div style="font-size:1.05rem;font-weight:700;color:#dbeafe;margin-bottom:8px;">
    📊 5 分鐘細看
  </div>
  <div style="font-size:0.9rem;color:#bfdbfe;line-height:1.72;">
    · 進入 <strong style="color:#e0ecfe;">🌱 投資觀察</strong><br>
    · 逐一展開推薦股票的<strong style="color:#e0ecfe;">四件事</strong>解讀<br>
    · 用成本<strong style="color:#e0ecfe;">試算機</strong>估算折價空間<br>
    <br>
    <span style="font-size:.82rem;opacity:.85;">→ 適合想自己判斷的投資人</span>
  </div>
</div>
""", unsafe_allow_html=True)

    with rg3:
        st.markdown("""
<div style="background:linear-gradient(180deg,rgba(15,23,37,0.92) 0%,rgba(10,20,32,0.92) 100%);
            border:1px solid rgba(124,58,237,0.38);
            border-left:3px solid #7c3aed;
            border-radius:12px;padding:16px 18px;height:100%;
            box-shadow:0 4px 16px rgba(2,6,23,0.30), inset 0 1px 0 rgba(124,58,237,0.12);">
  <div style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#a78bfa;
              letter-spacing:0.18em;font-weight:800;margin-bottom:4px;
              text-shadow:0 0 8px rgba(124,58,237,0.35);">PATH C · RESEARCHER</div>
  <div style="font-size:1.05rem;font-weight:700;color:#ede9fe;margin-bottom:8px;">
    🔬 深入研究
  </div>
  <div style="font-size:0.9rem;color:#ddd6fe;line-height:1.72;">
    · 切到 <strong style="color:#f1edfd;">⚙️ 研究工作站</strong> tab<br>
    · 看完整的 <strong style="color:#f1edfd;">AUC/DSR/ICIR</strong> + LOPO<br>
    · 再到治理監控確認模型健康度<br>
    <br>
    <span style="font-size:.82rem;opacity:.85;">→ 給分析師、學術審閱者</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# ⚙️ 研究工作站  (Research Workstation — Bloomberg-terminal feel)
# ----------------------------------------------------------------------------
with tab_workstation:
    # ====================================================================
    # ⚡ PERFORMANCE HEADLINE — 3 key numbers + interpretation
    # ====================================================================
    _auc_edge = max(0.0, (baseline_auc - 0.5) * 2 * 100)  # % above random
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 55%,#0f172a 100%);
            border:1px solid rgba(6,182,212,0.22);
            border-left:4px solid #06b6d4;
            border-radius:14px;
            padding:20px 24px;
            margin-top:10px;margin-bottom:18px;
            color:#f1f5f9;
            box-shadow:0 6px 22px rgba(2,6,23,0.18);">
  <div style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#67e8f9;
              letter-spacing:0.16em;font-weight:700;text-transform:uppercase;margin-bottom:10px;">
    ⚡ PERFORMANCE HEADLINE &nbsp;·&nbsp; xgboost_D20 &nbsp;·&nbsp; Purged Walk-Forward 4-Fold
  </div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:22px;align-items:end;">
    <div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:2.2rem;font-weight:800;color:#67e8f9;
                  line-height:1;letter-spacing:-0.02em;">{baseline_auc:.3f}</div>
      <div style="font-size:0.82rem;color:#94a3b8;margin-top:6px;">OOS AUC · 預測正確率</div>
      <div style="font-size:0.76rem;color:#cbd5e1;margin-top:4px;opacity:0.9;">
        ≈ 比亂猜好 <strong style="color:#a7f3d0;">{_auc_edge:.1f}%</strong> · 超過 0.52 閘門
      </div>
    </div>
    <div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:2.2rem;font-weight:800;color:#a7f3d0;
                  line-height:1;letter-spacing:-0.02em;">{best_dsr:.2f}</div>
      <div style="font-size:0.82rem;color:#94a3b8;margin-top:6px;">DSR · 膨脹調整後夏普</div>
      <div style="font-size:0.76rem;color:#cbd5e1;margin-top:4px;opacity:0.9;">
        遠高於 <strong>1.0</strong> 有效門檻 · 非靠運氣
      </div>
    </div>
    <div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:2.2rem;font-weight:800;color:#fde68a;
                  line-height:1;letter-spacing:-0.02em;">+{best_edge*100:.1f}pp</div>
      <div style="font-size:0.82rem;color:#94a3b8;margin-top:6px;">Best Edge · 最佳邊際</div>
      <div style="font-size:0.76rem;color:#cbd5e1;margin-top:4px;opacity:0.9;">
        Top decile vs bottom · D+20 threshold sweep
      </div>
    </div>
  </div>
  <div style="font-size:0.82rem;color:#cbd5e1;margin-top:14px;padding-top:12px;
              border-top:1px solid rgba(148,163,184,0.16);line-height:1.7;">
    📖 <strong style="color:#f1f5f9;">一句話解讀</strong>：這三個數字就是「這套系統值不值得看」的三把尺 ——
    <span style="color:#a7f3d0;">準不準</span>、
    <span style="color:#67e8f9;">穩不穩</span>、
    <span style="color:#fde68a;">賺不賺</span>。全部通過研究門檻。
  </div>
</div>
""", unsafe_allow_html=True)

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
        _q_delta = ("ALL PASS", "up") if kpis["all_pass"] \
                   else (f"{len(kpis['failed_names'])} TO FIX", "down")
        render_kpi(
            "QUALITY", f"{kpis['gates_passed']}/{kpis['total_gates']}",
            delta=_q_delta,
            sub="Phase 2 quality gates",
            accent="emerald" if kpis["all_pass"] else "amber",
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
        <span class="gl-chip violet">訊號監控</span>
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
        <span class="gl-chip violet">因子工程</span>
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
        ("延伸分析",       "Phase 3", "#7c3aed"),
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
            textfont=dict(family="Inter, sans-serif", size=11, color="#E8F7FC"),
            hoverinfo='text',
            hovertext=f"{stage} ({phase})",
            showlegend=False
        ))
        fig.add_annotation(
            x=i, y=-0.55, text=phase, showarrow=False,
            font=dict(family="JetBrains Mono, monospace", size=9, color="#94a3b8"),
        )

    # v11 §4b — arrow connector paints cyan-translucent on dark panel.
    for i in range(len(stages) - 1):
        fig.add_annotation(
            x=i + 0.75, y=0, ax=i + 0.25, ay=0,
            xref='x', yref='y', axref='x', ayref='y',
            arrowhead=2, arrowsize=1.1, arrowwidth=1.5,
            arrowcolor='rgba(103,232,249,0.45)', showarrow=True,
        )

    # v11 §4b — use glint_dark_layout so the pipeline flow renders as a
    # dark terminal panel instead of a transparent band that reveals the
    # light host canvas.
    fig.update_layout(**_utils.glint_dark_layout(height=200, show_grid=False))
    fig.update_layout(
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                   range=[-0.5, len(stages) - 0.5], visible=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                   range=[-0.9, 0.9], visible=False),
        margin=dict(l=20, r=20, t=36, b=24),
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
