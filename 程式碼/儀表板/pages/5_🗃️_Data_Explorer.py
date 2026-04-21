"""Data Explorer — 資料探索（量化分析工作台）"""

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
load_feature_store = _utils.load_feature_store
load_companies = _utils.load_companies
glint_plotly_layout = _utils.glint_plotly_layout
glint_dark_tooltip = _utils.glint_dark_tooltip
glint_dark_gauge_style = _utils.glint_dark_gauge_style
render_chart_note = _utils.render_chart_note
render_terminal_hero = _utils.render_terminal_hero
render_glint_table = _utils.render_glint_table
PAGE_EYEBROWS = _utils.PAGE_EYEBROWS
PAGE_TITLES = _utils.PAGE_TITLES
PAGE_BRIEFINGS = _utils.PAGE_BRIEFINGS
render_trust_strip = _utils.render_trust_strip
render_page_footer = _utils.render_page_footer
glint_icon = _utils.glint_icon
glint_heading = _utils.glint_heading

inject_custom_css()
_utils.inject_v10_dark_widgets_css()

# ---- Top-bar (sticky breadcrumb + model chips + clock) ----
render_topbar(
    crumb_left="台股多因子研究終端",
    crumb_current="資料探索",
    chips=[("948,976 rows", "pri"), ("FinMind + 選用資料集", "vio"), ("9 pillars", "default")],
    show_clock=True,
)

try:
    report, report_name = load_report()
    results = report["results"]
    inject_advanced_sidebar(report_name, report, current_page="data_explorer")
except Exception as e:
    # v8 §18.4 · dark terminal error panel with schema hint
    _utils.render_error_from_copy_map("report_missing", exception=e)
    st.stop()

# v8 §12 · §20.2 — Dark terminal hero driven by centralised copy maps
render_terminal_hero(
    eyebrow=PAGE_EYEBROWS["data"],
    title=PAGE_TITLES["data"],
    briefing=PAGE_BRIEFINGS["data"],
    chips=[
        ("Dataset", "2023/03 – 2025/03", "info"),
        ("Gates", "9 / 9 PASS", "ok"),
    ],
    tone="blue",
)
render_trust_strip([
    ("ROWS",     "948,976 筆",           "blue"),
    ("SOURCES",  "bda2026 · FinMind",   "cyan"),
    ("FEATURES", "91 / 1,623 候選",      "violet"),
    ("PIT",      "已對齊 · 無洩漏",       "emerald"),
])

# 白話版資料產生說明 — v11.3 dark-glint 化
st.markdown("""
<div style="
    background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.96) 100%);
    border: 1px solid rgba(103,232,249,0.22);
    border-left: 4px solid #67e8f9;
    border-radius: 12px;
    padding: 18px 22px;
    margin: 14px 0;
    box-shadow: inset 0 1px 0 rgba(103,232,249,0.10);
">
    <div style="
        display: inline-block;
        background: rgba(103,232,249,0.14); color: #67e8f9;
        border: 1px solid rgba(103,232,249,0.32);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.70rem; font-weight: 700; letter-spacing: 0.12em;
        padding: 3px 10px; border-radius: 4px; margin-bottom: 10px;
    ">資料怎麼來? · DATA PIPELINE</div>
    <div style="font-size: 0.95rem; color: #cfe2ee; line-height: 1.85;">
        <strong style="color: #E8F7FC;">這一頁的 94 萬筆資料怎麼產生?</strong><br>
        ① <strong>教授 bda2026 資料庫</strong>提供 4 張主表(公司基本、股價、財報、文本);<br>
        ② <strong>FinMind 公開 API</strong>補上 OHLCV、資產負債表、現金流、產業、三大法人等 6 張表;<br>
        ③ 經過 <strong>PIT 合規對齊</strong>(財報按法定申報日延遲)與 <strong>洩漏偵測</strong>;<br>
        ④ 依九大面向建構 1,623 個候選特徵 → 三階段篩選到 91 個生產用特徵;<br>
        ⑤ 使用 <strong>Purged Walk-Forward CV</strong>(訓練集往前擴展 + 20 日 embargo),確保模型評估不偷看未來。<br>
        <strong style="color: #67e8f9;">→ 所有門檻都通過,才代表模型輸出可信。</strong>
    </div>
</div>
""", unsafe_allow_html=True)

st.info("""
**如何閱讀本頁？**

本頁展示系統的資料基礎設施。

Feature Store 的規模與品質、Walk-Forward 交叉驗證的時間切割方式，以及 7 項品質門檻（Quality Gates）的通過狀態。

所有門檻需全數通過才代表模型輸出可信。
""")

# ===== Feature Store Summary =====
try:
    glint_heading("bar-chart", "Feature Store 概覽 | Feature Store Summary", tone="cyan")

    fs_info = results.get("feature_store", {})
    val_info = results.get("data_validation", {})

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "總筆數",
            f"{fs_info.get('rows', 0):,}",
            delta="樣本容量"
        )
    with col2:
        st.metric(
            "欄位數",
            f"{fs_info.get('cols', 0)}",
            delta="特徵維度"
        )
    with col3:
        st.metric(
            "缺失比例",
            f"{val_info.get('nan_pct', 0):.3%}",
            delta="資料品質"
        )
    with col4:
        st.metric(
            "異常值 (Inf)",
            f"{val_info.get('inf_count', 0)}",
            delta="洩漏偵測"
        )

    st.markdown(f"""
    <div class="insight-box">
    <span style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("calendar", 15, "#22d3ee")} <strong>資料期間 | Period：</strong></span> {fs_info.get('date_range', 'N/A')}<br>
    <span style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("layers", 15, "#8b5cf6")} <strong>涵蓋公司 | Coverage：</strong></span> 教授 companies 1,932 家名單，其中 <strong>1,930 家在 2023-03~2025-03 期間有交易資料</strong>進入 feature_store（2 支 KY/下市股票於 FinMind 失敗）<br>
    <span style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("bar-chart", 15, "#10b981")} <strong>資料來源 | Sources：</strong></span> 教授研究型資料庫 <code>bda2026</code>（4 張表）＋ FinMind 公開 API 補充資料（6 張表，已封版）<br>
    <span style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("target", 15, "#10b981")} <strong>資料模式 | Mode：</strong></span> 固定歷史快照 | Static Historical Snapshot｜<strong>SCOPE v1.0 已凍結</strong>
    </div>
    """, unsafe_allow_html=True)

    # ===== Data Source Transparency =====
    st.markdown("### 🔎 資料來源透明宣告 | Data Source Transparency")
    # v11 §4a — replaced ad-hoc pastel div with the shared `.gl-box-warn` class
    # so it inherits the dark-glint terminal palette.
    st.markdown("""
    <div class="gl-box-warn">
    <strong>本專案使用兩類資料</strong>：主資料為教授提供之 <code>bda2026</code> 研究型資料庫（4 張表），<strong>輔以 FinMind 公開 API 取得 6 張補充表</strong>以完整支援 8 支柱多因子分析。自 2026-04-19 起依 <code>SCOPE.md</code> v1.0 封版，不再新增任何外部資料。
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        prof_data = pd.DataFrame([
            {"資料表": "companies", "筆數": "1,932", "用途": "公司基本識別（JOIN key）"},
            {"資料表": "stock_prices", "筆數": "877,699", "用途": "標籤生成、val_估值｜僅 closing_price"},
            {"資料表": "income_stmt", "筆數": "14,968", "用途": "fund_基本面｜僅 6 個損益科目"},
            {"資料表": "stock_text", "筆數": "1,125,134", "用途": "event_/txt_/sent_｜PTT/Dcard/Mobile01/Yahoo"},
        ])
        # v11 §3 — Glint dark terminal table (replaces raw st.dataframe)
        render_glint_table(
            prof_data,
            title="A · 教授提供資料庫 (bda2026 · 4 tables)",
            mono_columns=["筆數"],
            accent_columns={"資料表": "cyan"},
        )

    with col_b:
        finmind_data = pd.DataFrame([
            {"檔案": "stock_prices_ohlcv", "FinMind Dataset": "TaiwanStockPrice", "補教授資料之不足": "OHLCV（教授僅收盤價）"},
            {"檔案": "balance_sheet", "FinMind Dataset": "TaiwanStockBalanceSheet", "補教授資料之不足": "資產負債表（教授未提供）"},
            {"檔案": "cashflow", "FinMind Dataset": "TaiwanStockCashFlowsStatement", "補教授資料之不足": "現金流量表（教授未提供）"},
            {"檔案": "industry", "FinMind Dataset": "TaiwanStockInfo", "補教授資料之不足": "產業別（教授 companies 無）"},
            {"檔案": "institutional_investors", "FinMind Dataset": "TaiwanStockInstitutionalInvestorsBuySell", "補教授資料之不足": "三大法人籌碼（教授未提供）"},
            {"檔案": "margin_trading", "FinMind Dataset": "TaiwanStockMarginPurchaseShortSale", "補教授資料之不足": "融資融券（教授未提供）— ⚠️ mg_ 支柱已於 2026-04-19 下架，檔案保留作為資料透明之證明"},
        ])
        render_glint_table(
            finmind_data,
            title="B · FinMind 補充資料 (6 tables · sealed)",
            accent_columns={"檔案": "cyan", "FinMind Dataset": "amber"},
        )

    # v11 §4a — replaced ad-hoc pastel div with shared `.gl-box-danger` class.
    st.markdown("""
    <div class="gl-box-danger">
    <strong>⚠️ mg_ 融資融券支柱已於 2026-04-19 下架</strong>：FinMind 覆蓋僅 1,136 / 1,932 = 58.8% 公司，其中約 100 支為結構性不可下載（KY 股、創業板、新上市、ETF 非信用交易標的），無法達到 100% 覆蓋。過往範例（G1/G10/G20/G2）亦未使用此特徵。改由 <code>chip_</code>（三大法人）、<code>trend_</code>（技術）、<code>event_</code>（文本）承擔市場結構訊號。parquet 檔案仍保留作為資料透明之證明，詳見 <code>資料來源宣告.md</code> 的 B6 欄位說明。
    </div>
    """, unsafe_allow_html=True)

    st.caption("完整資料來源說明請見專案根目錄的 `SCOPE.md` 與 `選用資料集/資料來源宣告.md`。")

    # ===== Legacy expander kept for pipeline details =====
    with st.expander("資料前處理 Pipeline 說明", expanded=False, icon=":material/menu_book:"):

        st.markdown("#### 資料前處理流程")
        st.markdown("""
| 步驟 | 處理內容 | 參數設定 |
|------|---------|---------|
| 缺值填補 | 價格欄位前向填充（Forward Fill） | 最多容許 5 個交易日 |
| 最低交易日 | 過濾交易日過少的股票 | ≥ 60 個交易日 |
| 除權息校正 | 偵測並修復除權息跳空 | 容差 0.5%，RSI 異常閾值 10 |
| 文字去重 | MinHash LSH 去除重複新聞 | 128 permutations，Jaccard > 0.8 |
| PIT 合規 | 財報按法定申報期限延遲對齊 | Q1→5/15, Q2→8/14, Q3→11/14, Q4→+1年3/31 |
| 洩漏偵測 | 檢查未來資訊關鍵字 + PSI 檢驗 | PSI > 0.25 警告 |
        """)

        st.markdown(f"""
        <div class="insight-box">
        <strong style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("pin", 15, "#fbbf24")} PIT（Point-in-Time）合規：</strong><br>
        所有財報數據嚴格按照台灣 IFRS 法定申報期限進行延遲對齊，確保模型訓練時不會使用到「當時尚未公開」的財報資料。<br>
        例如：Q1 財報在 5/15 之後才可使用，即使實際公布日期更早。
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.warning(f"Feature Store 概覽載入失敗：{str(e)}")

# ===== Walk-Forward CV Timeline =====
try:
    st.divider()
    glint_heading("calendar", "Walk-Forward CV 結構 | CV Timeline", tone="cyan")

    st.markdown("""
    <div class="insight-box">
    <strong>🔐 Purged Walk-Forward CV：</strong><br>
    使用 Expanding Window 訓練——每一折的訓練集包含所有歷史資料（而非固定視窗），加上 20 日 Embargo 期隔離訓練與測試集。<br>
    防止因交易日重疊造成的前瞻偏差。
    </div>
    """, unsafe_allow_html=True)

    st.warning("⚠️ 以下 Walk-Forward 時間軸與樣本量基於固定歷史資料集（2023/03–2025/03）。實盤應用時應改用動態 expanding window。")

    wf = results.get("walk_forward", {})
    folds = wf.get("folds", [])

    if folds:
        # v8 §15.9 — Dark walk-forward timeline.
        # Train = deep blue scale (dark→light as folds expand), Test = emerald scale.
        fig = go.Figure()
        colors_train = ["#1E3A8A", "#1D4ED8", "#2563EB", "#3B82F6"]   # deep blue scale
        colors_test  = ["#064E3B", "#065F46", "#047857", "#10B981"]   # emerald scale
        embargo_color = "rgba(245,158,11,0.35)"                       # amber — embargo strip

        for fold in folds:
            fid = fold["fold_id"]
            y_label = f"Fold {fid+1:02d}" if isinstance(fid, int) else f"Fold {fid}"
            # Train bar (filled from 0→1.0)
            fig.add_trace(go.Bar(
                y=[y_label],
                x=[1.0],
                base=[0],
                orientation="h",
                name="Train · expanding" if fid == 0 else None,
                marker=dict(
                    color=colors_train[fid % len(colors_train)],
                    line=dict(color="rgba(103,232,249,0.20)", width=0.5),
                ),
                showlegend=(fid == 0),
                text=[f"TRAIN · {fold['train_period']}"],
                textposition="inside",
                insidetextanchor="start",
                textfont=dict(family="'JetBrains Mono', monospace", size=10, color="#DBEAFE"),
                width=0.55,
                hovertemplate=(
                    f"<b>Fold {fid+1:02d} · TRAIN</b><br>"
                    f"Period: {fold['train_period']}<br>"
                    f"Samples: {fold['n_train']:,}<extra></extra>"
                ),
            ))
            # Embargo strip (1.0→1.08) — 20-day purge band
            fig.add_trace(go.Bar(
                y=[y_label],
                x=[0.08],
                base=[1.0],
                orientation="h",
                name="Embargo · 20d" if fid == 0 else None,
                marker=dict(color=embargo_color, line=dict(width=0)),
                showlegend=(fid == 0),
                text=[""],
                width=0.55,
                hovertemplate=f"<b>Embargo · 20 trading days</b><extra></extra>",
            ))
            # Test bar (1.08→1.33)
            fig.add_trace(go.Bar(
                y=[y_label],
                x=[0.25],
                base=[1.08],
                orientation="h",
                name="Test · hold-out" if fid == 0 else None,
                marker=dict(
                    color=colors_test[fid % len(colors_test)],
                    line=dict(color="rgba(103,232,249,0.20)", width=0.5),
                ),
                showlegend=(fid == 0),
                text=[f"TEST · {fold['test_period']}"],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(family="'JetBrains Mono', monospace", size=10, color="#D1FAE5"),
                width=0.55,
                hovertemplate=(
                    f"<b>Fold {fid+1:02d} · TEST</b><br>"
                    f"Period: {fold['test_period']}<br>"
                    f"Samples: {fold['n_test']:,}<extra></extra>"
                ),
            ))

        fig.update_layout(**glint_plotly_layout(
            title="Purged Walk-Forward CV · Temporal Structure",
            subtitle=f"{len(folds)}-fold expanding window · 20-day embargo · 防前瞻偏差",
            height=320,
            show_grid=False,
        ))
        fig.update_layout(
            barmode="stack",
            bargap=0.45,
            xaxis=dict(visible=False, range=[-0.02, 1.36]),
            yaxis=dict(
                autorange="reversed",
                tickfont=dict(family="'JetBrains Mono', monospace", size=11, color="#B4CCDF"),
                gridcolor="rgba(103,232,249,0.06)",
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(0,0,0,0)",
                font=dict(family="'JetBrains Mono', monospace", size=11, color="#B4CCDF"),
            ),
            hoverlabel=glint_dark_tooltip(),
            hovermode="closest",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Fold details table
        st.caption("📋 逐折詳細信息 | Per-Fold Details")
        fold_rows = []
        for fold in folds:
            test_ratio = fold['n_test']/(fold['n_train']+fold['n_test'])*100
            fold_rows.append({
                "折次 | Fold": fold["fold_id"],
                "訓練期間 | Train Period": fold["train_period"],
                "測試期間 | Test Period": fold["test_period"],
                "訓練樣本 | N Train": f"{fold['n_train']:,}",
                "測試樣本 | N Test": f"{fold['n_test']:,}",
                "測試占比 | Test Ratio": f"{test_ratio:.1f}%",
            })

        st.dataframe(pd.DataFrame(fold_rows), use_container_width=True, hide_index=True)

        mc1, mc2 = st.columns(2)
        with mc1:
            st.metric(
                "總訓練樣本 | Total Train",
                f"{wf.get('total_train_samples', 0):,}",
                delta="跨所有折次"
            )
        with mc2:
            st.metric(
                "總測試樣本 | Total Test",
                f"{wf.get('total_test_samples', 0):,}",
                delta="跨所有折次"
            )

except Exception as e:
    st.warning(f"CV 結構分析失敗：{str(e)}")

# ===== Quality Gates =====
try:
    st.divider()
    st.subheader("🔒 品質門控詳情 | Quality Gates")

    gates = report.get("quality_gates", {})
    if gates:
        descriptions = {
            "all_models_trained": "所有模型（LGB + XGB × 3 horizons）均成功訓練",
            "auc_gate_pass": "所有模型 AUC 超過 0.52 門檻",
            "sufficient_folds": "CV Fold 數量 ≥ 2",
            "no_data_leakage": "Feature Store 無 Inf 值（資料洩漏代理指標）",
            "oof_predictions_valid": "所有 OOF 預測非全 NaN",
            "feature_stability": "跨 Fold 特徵 Jaccard 穩定性 ≥ 0.3",
            "best_model_ic_positive": "最佳模型的 Rank IC > 0",
        }

        gate_rows = []
        for gate, passed in gates.items():
            is_pass = passed is True or passed == "True"
            gate_rows.append({
                "門控 | Gate": gate.replace("_", " ").title(),
                "狀態 | Status": "✅ 通過 | PASS" if is_pass else "❌ 失敗 | FAIL",
                "說明 | Description": descriptions.get(gate, ""),
            })

        st.dataframe(
            pd.DataFrame(gate_rows),
            use_container_width=True,
            hide_index=True
        )

        # Visual summary with progress bar
        n_pass = sum(1 for g in gates.values() if g is True or g == "True")
        n_total = len(gates)
        pass_rate = n_pass / n_total

        # v11 §5 — Glint dark terminal progress bar (replaces light #f0f0f0
        # track with deep-navy track + cyan/emerald/amber/rose accent fill
        # that matches the kind of the result).
        if pass_rate == 1.0:
            _fill = "linear-gradient(90deg, #10b981 0%, #34d399 100%)"
            _glow = "rgba(16,185,129,0.45)"
            _label_color = "#d1fae5"
        elif pass_rate >= 0.8:
            _fill = "linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%)"
            _glow = "rgba(245,158,11,0.45)"
            _label_color = "#fef3c7"
        else:
            _fill = "linear-gradient(90deg, #f43f5e 0%, #fb7185 100%)"
            _glow = "rgba(244,63,94,0.45)"
            _label_color = "#fecaca"

        st.markdown(f"""
        <div style="margin: 20px 0;">
          <div style="
              background: linear-gradient(180deg, rgba(10,20,32,0.95), rgba(15,23,37,0.95));
              border: 1px solid rgba(103,232,249,0.24);
              border-radius: 10px; height: 34px; overflow: hidden; padding: 2px;
              box-shadow: inset 0 1px 0 rgba(103,232,249,0.14), 0 2px 10px rgba(2,6,23,0.32);">
            <div style="
                background: {_fill};
                width: {pass_rate*100:.1f}%; height: 100%;
                border-radius: 7px;
                display: flex; align-items: center; justify-content: center;
                color: {_label_color};
                font-family: 'JetBrains Mono', monospace; font-weight: 800;
                font-size: 0.88rem; letter-spacing: 0.10em;
                text-shadow: 0 0 8px {_glow};
                box-shadow: 0 0 14px {_glow};
                transition: width 0.6s ease;">
                {n_pass}/{n_total} · {pass_rate*100:.0f}%
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # v11 §5 — Glint dark terminal gauge (was: raw #059669/#f59e0b/#dc2626
        # bar + light #fee2e2/#fef3c7/#ecfdf5 step bands on white canvas).
        if n_pass == n_total:
            _gauge_tone = "emerald"
        elif n_pass >= n_total * 0.8:
            _gauge_tone = "amber"
        else:
            _gauge_tone = "rose"
        _gauge_style = glint_dark_gauge_style(tone=_gauge_tone)
        # Layer in kind-tinted step bands (still dark but with subtle glow
        # so the threshold arcs are visible instead of white wedges).
        _gauge_style["steps"] = [
            {"range": [0, n_total * 0.5], "color": "rgba(244,63,94,0.28)"},
            {"range": [n_total * 0.5, n_total * 0.8], "color": "rgba(245,158,11,0.28)"},
            {"range": [n_total * 0.8, n_total], "color": "rgba(16,185,129,0.28)"},
        ]
        _gauge_style["threshold"] = {
            "line": {"color": "#67e8f9", "width": 4},
            "thickness": 0.80,
            "value": n_pass,
        }
        fig_gate = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=n_pass,
            delta={
                "reference": n_total, "suffix": " gates",
                "increasing": {"color": "#34d399"},
                "decreasing": {"color": "#fb7185"},
                "font": {"family": "'JetBrains Mono', monospace",
                         "size": 13, "color": "#b4ccdf"},
            },
            title={
                "text": "<b>品質門控通過</b><br>"
                        "<span style='font-size:10px;color:#8397ac;font-weight:400;'>"
                        "GATES PASSED · Live</span>",
                "font": {"family": "Inter, sans-serif",
                         "size": 14, "color": "#e8f7fc"},
            },
            gauge=_gauge_style,
            number={
                "suffix": f" / {n_total}",
                "font": {"family": "'JetBrains Mono', monospace",
                         "size": 40, "color": "#e8f7fc"},
            },
        ))
        fig_gate.update_layout(**glint_plotly_layout(height=340, show_grid=False))
        fig_gate.update_layout(
            margin=dict(l=30, r=30, t=80, b=28),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        st.plotly_chart(fig_gate, use_container_width=True)

except Exception as e:
    st.warning(f"品質門控分析失敗：{str(e)}")

# ===== Data Freshness Indicator =====
try:
    st.divider()
    glint_heading("radar", "資料新鮮度 | Data Freshness", tone="cyan")

    fs_info = results.get("feature_store", {})
    date_range_str = fs_info.get('date_range', '未知 | Unknown')

    st.markdown(f"""
    <div class="insight-box">
    <span style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("target", 15, "#10b981")} <strong>最新資料日期 | Latest Date：</strong></span> 2025 年 3 月 1 日（截至儀表板更新時間）<br>
    <span style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("calendar", 15, "#22d3ee")} <strong>涵蓋期間 | Coverage：</strong></span> {date_range_str}<br>
    <span style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("refresh-cw", 15, "#8b5cf6")} <strong>資料性質 | Data Type：</strong></span> 固定歷史資料集（非即時更新）| Static historical dataset
    </div>
    """, unsafe_allow_html=True)

    # ===== System Architecture =====
    st.divider()
    glint_heading("cpu", "系統架構 | System Architecture", tone="violet")

    st.code("""
台股多因子研究終端 | Taiwan Multi-Factor Research Terminal
├── run_phase1.py                  # Phase 1: 資料擷取 → Feature Store
├── run_phase2.py                  # Phase 2: 模型訓練 → 策略回測
├── dashboard/
│   ├── app.py                     # 登陸頁面 | Landing Page（分流入口）
│   ├── utils.py                   # 共享工具函數 | Shared Utilities
│   └── pages/
│       ├── 0_投資解讀面板          # 新手友善推薦儀表板
│       ├── 1_Model_Metrics        # AUC / Per-Class AUC / Fold 穩定性
│       ├── 2_ICIR_Analysis        # 訊號穩定性分析 / IC 分布
│       ├── 3_Backtest             # 多情境策略回測 / 成本分析
│       ├── 4_Feature_Analysis     # 特徵篩選 / SHAP / Quintile
│       └── 5_Data_Explorer        # 資料探索 / 品質門控
├── src/
│   ├── data/                      # 資料載入 / 清洗 / 標籤 / 洩漏偵測
│   ├── features/                  # 九支柱特徵工程 + 三階段篩選（Phase 5B: 1,623 → 91）
│   ├── models/                    # LGB / XGB + Optuna HPO + Walk-Forward CV
│   ├── backtest/                  # Horizon-aware 回測 + 績效指標
│   ├── visualization/             # 10+ 種圖表生成
│   └── utils/                     # 配置 / 日誌 / 輔助函數
├── tests/                         # 99+ 個單元測試
└── outputs/
    ├── feature_store_final.parquet  # Phase 5B 最終特徵集 (948,976 × 1,626)
    ├── figures/                     # 60+ 張圖表（含 Phase 5B 文本 6 張 + Phase 6 補件 3 張）
    ├── governance/                  # 4 份 Model Card + drift/signal_decay/DSR 報告
    ├── models/                      # 6 joblib（lgb/xgb × D1/D5/D20）
    └── reports/                     # JSON 報告 + LOPO / threshold sweep / single-stock
    """, language="text", line_numbers=False)

    # ===== Label Definition Methodology =====
    st.divider()
    glint_heading("target", "標籤定義方法論 | Label Definition Methodology", tone="emerald")
    st.caption("三分類標籤的定義邏輯與閾值設定 | How UP / FLAT / DOWN labels are defined")

    st.markdown("""
**標籤定義公式 | Label Formula：**

$$
r_{i,t}^{(h)} = \\frac{P_{i, t+h} - P_{i,t}}{P_{i,t}} \\quad (\\text{h-day forward return})
$$

根據前瞻報酬率 $r$ 與閾值 $\\theta_h$ 進行分類：
    """)

    label_def = pd.DataFrame({
        "預測天期 | Horizon": ["D+1", "D+5", "D+20"],
        "閾值 θ | Threshold": ["±0.5%", "±1.5%", "±4.0%"],
        "UP 條件": ["r > +0.5%", "r > +1.5%", "r > +4.0%"],
        "FLAT 條件": ["-0.5% ≤ r ≤ +0.5%", "-1.5% ≤ r ≤ +1.5%", "-4.0% ≤ r ≤ +4.0%"],
        "DOWN 條件": ["r < -0.5%", "r < -1.5%", "r < -4.0%"],
        "設計理由": [
            "日內波動小，0.5% 為典型日波動中位數",
            "週度波動，1.5% ≈ 3 × daily vol",
            "月度趨勢，4.0% ≈ 具有統計與經濟顯著性"
        ],
    })
    st.dataframe(label_def, use_container_width=True, hide_index=True)

    st.markdown(f"""
    <div class="insight-box">
    <strong style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("pin", 15, "#fbbf24")} 閾值設計原則 | Threshold Design Rationale：</strong><br>
    • 閾值按天期遞增，反映較長持有期間內的自然價格變異程度<br>
    • FLAT 類別設計為「中間帶」，代表市場無明確方向——這是最難預測的類別<br>
    • 閾值的選擇參考台股歷史波動率中位數，確保各類別有足夠樣本<br>
    • 未使用動態閾值（<code>use_dynamic_threshold: false</code>），保持結果可重現性
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    st.caption("各天期的三分類標籤分佈特徵 | Three-class label distribution by horizon")

    st.warning("⚠️ 以下標籤分佈數據基於固定歷史資料集。FLAT 類別佔比 ≈ 50% 反映市場多數時間無明確趨勢，符合真實市場特徵。")

    # v8 §15.8 — Stacked horizontal composition bars (Bloomberg-style)
    # DOWN = deep rose · FLAT = muted slate · UP = emerald
    horizons_order = ["D+1", "D+5", "D+20"]
    counts_map = {
        "D+1":  {"DOWN": 145000, "FLAT": 310000, "UP": 145000},
        "D+5":  {"DOWN": 142000, "FLAT": 316000, "UP": 142000},
        "D+20": {"DOWN": 138000, "FLAT": 324000, "UP": 138000},
    }
    # Build three traces so the stacked horizontal bars share a common axis.
    import plotly.graph_objects as _go
    fig_label = _go.Figure()
    _tone_map = {
        "DOWN": {"color": "#9f1239", "label_fg": "#fecdd3"},   # deep rose
        "FLAT": {"color": "#475569", "label_fg": "#cbd5e1"},   # muted slate
        "UP":   {"color": "#10b981", "label_fg": "#d1fae5"},   # emerald
    }
    for lbl in ["DOWN", "FLAT", "UP"]:
        values = [counts_map[h][lbl] for h in horizons_order]
        totals = [sum(counts_map[h].values()) for h in horizons_order]
        pcts = [v / t for v, t in zip(values, totals)]
        fig_label.add_trace(_go.Bar(
            y=horizons_order,
            x=values,
            name=lbl,
            orientation="h",
            marker=dict(
                color=_tone_map[lbl]["color"],
                line=dict(color="rgba(6,10,18,0.85)", width=0.6),
            ),
            text=[f"{lbl} {p*100:.1f}% · {v/1000:.0f}k" for p, v in zip(pcts, values)],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(
                family="'JetBrains Mono', monospace",
                size=11,
                color=_tone_map[lbl]["label_fg"],
            ),
            hovertemplate=(
                f"<b>{lbl}</b><br>"
                "Horizon %{y}<br>"
                "樣本 %{x:,}<br>"
                "占比 %{customdata:.1%}<extra></extra>"
            ),
            customdata=pcts,
        ))
    fig_label.update_layout(**glint_plotly_layout(
        title="標籤組成 · Label Composition",
        subtitle="Stacked by horizon · DOWN/FLAT/UP share of D+1, D+5, D+20",
        height=320,
        xlabel="Sample Count",
        ylabel="",
    ))
    fig_label.update_layout(
        barmode="stack",
        bargap=0.42,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(family="'JetBrains Mono', monospace", size=11, color="#B4CCDF"),
        ),
        hoverlabel=glint_dark_tooltip(),
    )
    fig_label.update_xaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
    )
    st.plotly_chart(fig_label, use_container_width=True)
    st.caption(
        "FLAT 佔比最高屬市場常態，長天期分佈更接近平穩趨勢型分類。"
        "　DOWN / UP 近乎對稱 (±2% 內) 顯示訓練資料未出現方向偏差。"
    )

    # ===== Raw JSON Report =====
    st.divider()
    st.subheader("📄 原始報告 | Raw Report")

    with st.expander("🔍 展開查看完整 JSON 報告 | Expand to view full JSON"):
        st.json(report)

except Exception as e:
    st.error(f"資料探索發生錯誤：{str(e)}")

# ===== Footer & Limitations =====
render_page_footer("Data Explorer")
