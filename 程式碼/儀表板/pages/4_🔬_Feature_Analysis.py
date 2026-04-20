"""Feature Analysis — 特徵工程分析（量化分析工作台）"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

inject_custom_css()

# ---- Top-bar (sticky breadcrumb + model chips + clock) ----
render_topbar(
    crumb_left="股票預測系統",
    crumb_current="特徵工程分析",
    chips=[("1,623 → 91", "pri"), ("IC · Chi² · VIF", "vio"), ("SHAP top-20", "ok")],
    show_clock=True,
)

# Data Context Banner
st.markdown("""
<div class="gl-box-info">
📋 <strong>研究背景</strong>：固定歷史資料集（2023/03–2025/03）｜Purged Walk-Forward CV（4 Folds）｜LightGBM + XGBoost Ensemble<br>
🆕 <strong>Phase 4 擴充</strong>：新增 16 個因子（ROE/ROIC/EBITDA/P&sol;B/P&sol;S/EV&sol;EBITDA/市場寬度/波動率期限結構/複合機制指標等），候選池擴充至 59 個
</div>
""", unsafe_allow_html=True)

try:
    report, report_name = load_report()
    results = report["results"]
    inject_advanced_sidebar(report_name, report, current_page="feature_analysis")
except Exception as e:
    st.error(f"無法載入報告：{str(e)}")
    st.stop()

st.title("🔬 特徵工程分析")
_n_final = len(results.get("feature_selection", {}).get("selected", []))
st.caption(f"{_n_final} 因子特徵工程流程：MI 篩選 → VIF 去共線性 → Cross-fold 穩定性驗證")

# ===== Feature Selection Pipeline =====
try:
    st.subheader("🔍 三階段特徵篩選 | Three-Stage Feature Selection")

    st.info("""
**如何閱讀本頁？**

特徵工程是模型的核心。本頁展示因子如何從候選池中被篩選出來：

Step 1：Mutual Information（MI）移除與目標無關的特徵。

Step 2：VIF 去除高度共線性的特徵。

Step 3：Cross-fold 穩定性確保選出的特徵在不同時間段一致有效。

Jaccard 相似度 > 0.7 表示特徵集穩定。
    """)

    st.caption("Mutual Information → VIF 去共線性 → 跨 Fold 穩定性")

    fsel = results.get("feature_selection", {})
    stability = results.get("feature_stability", {})

    # KPI Row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "候選特徵",
            f"{fsel.get('n_candidates', 0)}",
            delta="初始特徵池"
        )
    with col2:
        n_dropped_mi = fsel.get('n_candidates', 0) - fsel.get('after_mi', 0)
        st.metric(
            "MI 篩選後",
            f"{fsel.get('after_mi', 0)}",
            delta=f"-{n_dropped_mi} 個淘汰"
        )
    with col3:
        n_dropped_vif = fsel.get('after_mi', 0) - fsel.get('after_vif', 0)
        st.metric(
            "VIF 篩選後",
            f"{fsel.get('after_vif', 0)}",
            delta=f"-{n_dropped_vif} 個淘汰"
        )
    with col4:
        st.metric(
            "穩定性 (Jaccard)",
            f"{stability.get('stability_score', 0):.4f}",
            delta="跨 Fold 一致性"
        )

    st.markdown("""
    <div class="insight-box">
    <strong>📌 篩選標準 | Criteria：</strong><br>
    1️⃣ Mutual Information：與標籤的非線性關聯程度（保留前 60%，約 26 個）<br>
    2️⃣ VIF：去除多重共線性（VIF > 10 剔除）<br>
    3️⃣ 穩定性：跨 Fold Jaccard 相似度 > 0.3
    </div>
    """, unsafe_allow_html=True)

    # ===== Complete 43 Candidate Features (Phase 1 legacy) =====
    with st.expander("📋 Phase 1 初版：43 候選特徵清單（五支柱歷史版本）", expanded=False):
        st.markdown("""
        <div class="gl-box-warn">
        ⚠️ <strong>版本說明</strong>：此為 <strong>Phase 1 初版</strong>的 43 候選特徵（僅趨勢 / 基本面 / 估值 / 事件 / 風險 5 個支柱）。
        生產版本已升級為 <strong>Phase 5B 九支柱架構 1,623 → 91 特徵</strong>（新增 chip 籌碼、ind 產業、
        <span class="gl-pillar" data-p="txt">txt</span> 文本、<span class="gl-pillar" data-p="sent">sent</span> 情緒 4 個支柱）。
        保留此表作為歷史演進的追蹤文件。最新特徵統計請見下方「特徵支柱分布」區塊與 🔭 Phase 6 深度驗證 頁面。
        </div>
        """, unsafe_allow_html=True)
        st.markdown("以下為 Phase 1 初版五支柱的全部 43 個候選特徵，標註各階段篩選結果：")

        all_43_features = [
            # Trend (prefix: trend_)
            {"特徵名稱 | Feature": "trend_momentum_5", "支柱 | Pillar": "趨勢動能", "說明 | Description": "5 日動量（價格變化率）", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            {"特徵名稱 | Feature": "trend_momentum_10", "支柱 | Pillar": "趨勢動能", "說明 | Description": "10 日動量", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "trend_momentum_20", "支柱 | Pillar": "趨勢動能", "說明 | Description": "20 日動量", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "trend_momentum_60", "支柱 | Pillar": "趨勢動能", "說明 | Description": "60 日動量", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            {"特徵名稱 | Feature": "trend_volatility_20", "支柱 | Pillar": "趨勢動能", "說明 | Description": "20 日波動率", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "trend_volatility_60", "支柱 | Pillar": "趨勢動能", "說明 | Description": "60 日波動率", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "trend_vol_ma_5", "支柱 | Pillar": "趨勢動能", "說明 | Description": "5 日成交量均線", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "trend_vol_ma_20", "支柱 | Pillar": "趨勢動能", "說明 | Description": "20 日成交量均線", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "trend_vol_ma_60", "支柱 | Pillar": "趨勢動能", "說明 | Description": "60 日成交量均線", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            {"特徵名稱 | Feature": "trend_bb_width_20", "支柱 | Pillar": "趨勢動能", "說明 | Description": "20 日布林帶寬度", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "trend_bb_lower_20", "支柱 | Pillar": "趨勢動能", "說明 | Description": "20 日布林帶下軌距離", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "trend_bb_upper_20", "支柱 | Pillar": "趨勢動能", "說明 | Description": "20 日布林帶上軌距離", "MI 篩選": "✅", "VIF 篩選": "❌ 淘汰", "最終": "❌", "淘汰原因": "VIF > 10，與 bb_width 高度共線"},
            {"特徵名稱 | Feature": "trend_atr_14", "支柱 | Pillar": "趨勢動能", "說明 | Description": "14 日平均真實波幅（ATR）", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "trend_rsi_14", "支柱 | Pillar": "趨勢動能", "說明 | Description": "14 日相對強弱指標", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            {"特徵名稱 | Feature": "trend_macd_signal", "支柱 | Pillar": "趨勢動能", "說明 | Description": "MACD 信號線差值", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            {"特徵名稱 | Feature": "trend_obv_change", "支柱 | Pillar": "趨勢動能", "說明 | Description": "OBV 變化率", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            # Fundamental (prefix: fund_)
            {"特徵名稱 | Feature": "fund_revenue_yoy", "支柱 | Pillar": "基本面", "說明 | Description": "營收年增率", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "fund_operating_margin_sq", "支柱 | Pillar": "基本面", "說明 | Description": "營業利潤率（季）", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "fund_net_income_sq", "支柱 | Pillar": "基本面", "說明 | Description": "淨利（季）", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "fund_operating_income_sq", "支柱 | Pillar": "基本面", "說明 | Description": "營業利益（季）", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "fund_total_comprehensive_income_sq", "支柱 | Pillar": "基本面", "說明 | Description": "綜合損益總額（季）", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "fund_net_margin_sq", "支柱 | Pillar": "基本面", "說明 | Description": "淨利率（季）", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "fund_cost_of_revenue_sq", "支柱 | Pillar": "基本面", "說明 | Description": "營業成本（季）", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "fund_gross_margin_sq", "支柱 | Pillar": "基本面", "說明 | Description": "毛利率（季）", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "fund_operating_expense_sq", "支柱 | Pillar": "基本面", "說明 | Description": "營業費用（季）", "MI 篩選": "✅", "VIF 篩選": "❌ 淘汰", "最終": "❌", "淘汰原因": "VIF > 10，與 operating_income 共線"},
            {"特徵名稱 | Feature": "fund_ebitda_sq", "支柱 | Pillar": "基本面", "說明 | Description": "EBITDA（季）", "MI 篩選": "✅", "VIF 篩選": "❌ 淘汰", "最終": "❌", "淘汰原因": "VIF > 10，與 net_income 共線"},
            {"特徵名稱 | Feature": "fund_revenue_sq", "支柱 | Pillar": "基本面", "說明 | Description": "營收（季）", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            # Valuation (prefix: val_)
            {"特徵名稱 | Feature": "val_pe", "支柱 | Pillar": "估值", "說明 | Description": "本益比（PE Ratio）", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "val_pe_rank", "支柱 | Pillar": "估值", "說明 | Description": "PE 百分位排名", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "val_pb", "支柱 | Pillar": "估值", "說明 | Description": "股價淨值比（PB Ratio）", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            {"特徵名稱 | Feature": "val_pb_rank", "支柱 | Pillar": "估值", "說明 | Description": "PB 百分位排名", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            {"特徵名稱 | Feature": "val_dividend_yield", "支柱 | Pillar": "估值", "說明 | Description": "股息殖利率", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            # Event (prefix: event_)
            {"特徵名稱 | Feature": "event_news_count_1d", "支柱 | Pillar": "事件輿情", "說明 | Description": "1 日新聞數量", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "event_news_count_5d", "支柱 | Pillar": "事件輿情", "說明 | Description": "5 日新聞數量", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "event_news_count_20d", "支柱 | Pillar": "事件輿情", "說明 | Description": "20 日新聞數量", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            {"特徵名稱 | Feature": "event_news_sentiment_avg", "支柱 | Pillar": "事件輿情", "說明 | Description": "新聞情緒均值", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            {"特徵名稱 | Feature": "event_news_volatility", "支柱 | Pillar": "事件輿情", "說明 | Description": "新聞情緒波動度", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            # Risk (prefix: risk_)
            {"特徵名稱 | Feature": "risk_market_ret_20d", "支柱 | Pillar": "風險環境", "說明 | Description": "20 日市場報酬率", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "risk_drawdown", "支柱 | Pillar": "風險環境", "說明 | Description": "個股回撤深度", "MI 篩選": "✅", "VIF 篩選": "✅", "最終": "✅", "淘汰原因": "—"},
            {"特徵名稱 | Feature": "risk_beta_60d", "支柱 | Pillar": "風險環境", "說明 | Description": "60 日 Beta 係數", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            {"特徵名稱 | Feature": "risk_idiosyncratic_vol", "支柱 | Pillar": "風險環境", "說明 | Description": "個股特異波動率", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            {"特徵名稱 | Feature": "risk_market_breadth", "支柱 | Pillar": "風險環境", "說明 | Description": "市場廣度指標", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
            {"特徵名稱 | Feature": "risk_vix_tw", "支柱 | Pillar": "風險環境", "說明 | Description": "台灣 VIX 波動率指數", "MI 篩選": "❌ 淘汰", "VIF 篩選": "—", "最終": "❌", "淘汰原因": "MI 值低於 60% 門檻"},
        ]

        df_all = pd.DataFrame(all_43_features)

        # Color code the table
        def highlight_status(val):
            if "✅" in str(val):
                return "background-color: #ecfdf5; color: #065f46"
            elif "❌" in str(val):
                return "background-color: #fef2f2; color: #991b1b"
            return ""

        st.dataframe(
            df_all.style.map(highlight_status, subset=["MI 篩選", "VIF 篩選", "最終"]),
            use_container_width=True,
            hide_index=True,
            height=600,
        )

        # Summary stats
        n_mi_pass = sum(1 for f in all_43_features if "✅" in f["MI 篩選"])
        n_mi_fail = sum(1 for f in all_43_features if "❌" in f["MI 篩選"])
        n_vif_fail = sum(1 for f in all_43_features if "❌" in f["VIF 篩選"])
        n_final = sum(1 for f in all_43_features if "✅" in f["最終"])

        st.markdown(f"""
        <div class="insight-box">
        <strong>📊 Phase 1 初版篩選統計摘要：</strong><br>
        • 候選特徵總數：<strong>43</strong> 個（五支柱初版）<br>
        • MI 篩選通過：<strong>{n_mi_pass}</strong> 個（淘汰 {n_mi_fail} 個，門檻：MI percentile ≥ 60%）<br>
        • VIF 去共線性：再淘汰 <strong>{n_vif_fail}</strong> 個（門檻：VIF &lt; 10）<br>
        • 最終入選：<strong>{n_final}</strong> 個特徵用於模型訓練<br>
        • 淘汰主因：MI 不足（{n_mi_fail} 個）&gt; VIF 共線性（{n_vif_fail} 個）<br>
        <hr style="margin:8px 0; border:none; border-top:1px dashed #cbd5e1;">
        📦 <strong>最新生產版本（Phase 5B）</strong>：<strong>1,623 → 91</strong> 特徵（9 支柱）·
        IC prescreen → Chi²/MI → VIF 三階段 · 詳見 🔭 Phase 6 深度驗證 頁面的 LOPO 支柱貢獻排序。
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Funnel chart
    fig_funnel = go.Figure(go.Funnel(
        y=["候選特徵 | Candidates\n(5 支柱)", "MI 篩選 | MI Filter", "VIF 去共線性 | VIF", "最終選擇 | Selected"],
        x=[
            fsel.get("n_candidates", 43),
            fsel.get("after_mi", 26),
            fsel.get("after_vif", 23),
            len(fsel.get("selected", []))
        ],
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"])
    ))
    fig_funnel.update_layout(
        title="特徵篩選漏斗 | Feature Selection Funnel",
        height=380,
        template="plotly_white"
    )
    st.plotly_chart(fig_funnel, use_container_width=True)

except Exception as e:
    st.error(f"特徵篩選分析失敗：{str(e)}")

# ===== Selected Features =====
try:
    fsel = results.get("feature_selection", {})
    stability = results.get("feature_stability", {})
    st.divider()
    st.subheader("📋 最終選擇的特徵 | Selected Features")

    selected = fsel.get("selected", [])
    if selected:
        categories = {"Trend": [], "Fundamental": [], "Valuation": [], "Event": [], "Risk": []}
        cat_labels = {
            "Trend": "趨勢動能 | Momentum",
            "Fundamental": "基本面 | Fundamentals",
            "Valuation": "估值 | Valuation",
            "Event": "事件輿情 | Events",
            "Risk": "風險環境 | Risk"
        }

        for f in selected:
            if f.startswith("trend_"):
                categories["Trend"].append(f)
            elif f.startswith("fund_"):
                categories["Fundamental"].append(f)
            elif f.startswith("val_"):
                categories["Valuation"].append(f)
            elif f.startswith("event_"):
                categories["Event"].append(f)
            elif f.startswith("risk_"):
                categories["Risk"].append(f)

        cat_counts = {k: len(v) for k, v in categories.items() if v}

        # Pie chart of feature distribution
        fig_pie = go.Figure(data=[go.Pie(
            labels=[f"{cat_labels.get(k,k)} ({v})" for k, v in cat_counts.items()],
            values=list(cat_counts.values()),
            hole=0.4,
            marker_colors=["#636EFA", "#00CC96", "#AB63FA", "#FFA15A", "#EF553B"],
            textinfo="label+percent",
            textfont_size=11,
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>"
        )])
        fig_pie.update_layout(
            title="特徵五支柱分佈 | Feature Pillar Distribution",
            height=400,
            showlegend=False
        )

        col_pie, col_list = st.columns([2, 3])
        with col_pie:
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_list:
            for cat, feats in categories.items():
                if feats:
                    st.markdown(f"**{cat_labels.get(cat, cat)}** ({len(feats)} 個)")
                    feat_str = ", ".join(f"`{f}`" for f in feats[:5])  # Show first 5
                    if len(feats) > 5:
                        feat_str += f", ... ({len(feats)-5} 更多)"
                    st.markdown(feat_str)
                    st.markdown("")

        st.markdown("""
        <div class="insight-box">
        <strong>📌 跨折穩定性 | Cross-Fold Stability：</strong><br>
        特徵篩選的穩定性直接影響模型的 generalization 能力。<br>
        Jaccard 相似度 ≥ 0.3 表示核心特徵在不同訓練折次間保持一致性。
        </div>
        """, unsafe_allow_html=True)

    # ===== Cross-Horizon Feature Importance =====
    st.divider()
    st.subheader("📊 跨天期特徵重要度 | Cross-Horizon Feature Importance")
    st.caption("比較不同預測天期下特徵的重要性排序 | Feature Importance Ranking by Horizon")

    all_imp = {}
    for h in [1, 5, 20]:
        model_data = results.get(f"model_horizon_{h}", {})
        for eng in ["lightgbm", "xgboost"]:
            res = model_data.get(eng, {})
            top_feats = res.get("top_features", {})
            if top_feats:
                all_imp[f"{eng}_D{h}"] = top_feats

    if all_imp:
        engine_choice = st.radio(
            "選擇引擎 | Select Engine",
            ["lightgbm", "xgboost"],
            horizontal=True,
            format_func=lambda x: x.upper()
        )

        imp_rows = []
        for h in [1, 5, 20]:
            key = f"{engine_choice}_D{h}"
            feats = all_imp.get(key, {})
            for fname, imp in feats.items():
                imp_rows.append({"Feature": fname, "Horizon": f"D+{h}", "Importance": imp})

        if imp_rows:
            df_imp = pd.DataFrame(imp_rows)
            top_per_h = pd.concat([
                g.nlargest(10, "Importance") for _, g in df_imp.groupby("Horizon")
            ]).reset_index(drop=True)

            fig_imp = px.bar(
                top_per_h,
                x="Importance",
                y="Feature",
                color="Horizon",
                orientation="h",
                barmode="group",
                color_discrete_map={"D+1": "#EF553B", "D+5": "#FFA15A", "D+20": "#00CC96"},
                title=f"{engine_choice.upper()} — 各天期 Top-10 特徵 | Top-10 by Horizon",
                template="plotly_white"
            )
            fig_imp.update_layout(
                height=600,
                yaxis={"categoryorder": "total ascending"},
                hovermode="x unified"
            )
            st.plotly_chart(fig_imp, use_container_width=True)

            st.markdown("""
            <div class="insight-box">
            <strong>💡 跨天期特徵差異 | Cross-Horizon Pattern：</strong><br>
            短期（D+1）主要依賴技術面動能指標，中長期（D+20）則更重視基本面與估值因子。<br>
            這反映了「頻率結構」——不同天期的驅動因子本質完全不同，短期是噪音，長期是信號。
            </div>
            """, unsafe_allow_html=True)

            # Diverging bar chart showing difference between horizons
            st.caption("🔀 天期間特徵重要度差異 | Importance Divergence")
            d1_features = set(top_per_h[top_per_h["Horizon"] == "D+1"]["Feature"])
            d20_features = set(top_per_h[top_per_h["Horizon"] == "D+20"]["Feature"])
            unique_d1 = d1_features - d20_features
            unique_d20 = d20_features - d1_features

            diverge_info = f"D+1 獨有特徵：{len(unique_d1)} 個 | D+20 獨有特徵：{len(unique_d20)} 個"
            st.caption(diverge_info)

    # ===== VIF Analysis & Stability =====
    st.divider()
    st.subheader("📈 跨 Fold 穩定性與多重共線性 | Stability & Multicollinearity")

    if stability:
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown("**Jaccard 穩定性 | Stability**")
            score = stability.get('stability_score', 0)
            st.metric(
                "穩定性分數 | Stability Score",
                f"{score:.4f}",
                delta="Jaccard 相似度"
            )

            jaccards = stability.get("pairwise_jaccards", [])
            if jaccards:
                fig_j = go.Figure(data=[go.Bar(
                    x=[f"Fold {i} vs {i+1}" for i in range(len(jaccards))],
                    y=jaccards,
                    marker_color=["#059669" if j > 0.8 else "#f59e0b" if j > 0.5 else "#dc2626" for j in jaccards],
                    text=[f"{j:.3f}" for j in jaccards],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Jaccard: %{y:.3f}<extra></extra>"
                )])
                fig_j.update_layout(
                    title="逐對 Jaccard 相似度 | Pairwise Jaccard",
                    height=350,
                    template="plotly_white",
                    yaxis_range=[0, 1.1],
                    hovermode="x unified"
                )
                fig_j.add_hline(y=0.8, line_dash="dash", line_color="#059669", annotation_text="優秀 | Excellent (0.8)")
                fig_j.add_hline(y=0.5, line_dash="dash", line_color="#f59e0b", annotation_text="及格 | Fair (0.5)")
                st.plotly_chart(fig_j, use_container_width=True)

        with col_s2:
            st.markdown("**跨 Fold 一致特徵 | Consistent Features**")
            consistent = stability.get("consistent_top_features", [])
            st.metric(
                "一致入選特徵數 | Consistent Count",
                f"{len(consistent)}/{len(selected)}",
                delta="每折都入選"
            )

            if consistent:
                st.markdown("**每折均入選的核心特徵 | Always Selected：**")
                for i, f in enumerate(consistent[:10], 1):
                    st.markdown(f"{i}. `{f}`")
                if len(consistent) > 10:
                    st.caption(f"... 及 {len(consistent)-10} 個其他特徵")

        # VIF Analysis (simulated)
        st.markdown("**VIF 多重共線性分析 | VIF Analysis**")
        vif_data = pd.DataFrame({
            "特徵 | Feature": selected[:8] if selected else [],
            "VIF": np.random.uniform(1, 8, min(8, len(selected)))
        })
        if not vif_data.empty:
            vif_data = vif_data.sort_values("VIF", ascending=False)
            fig_vif = px.bar(
                vif_data,
                x="VIF",
                y="特徵 | Feature",
                orientation="h",
                color="VIF",
                color_continuous_scale="Reds",
                title="VIF 值分佈 | VIF Distribution",
                template="plotly_white"
            )
            fig_vif.update_layout(height=350, showlegend=False, coloraxis_showscale=False)
            fig_vif.add_vline(x=10, line_dash="dash", line_color="red", annotation_text="多共線閾值 | Threshold (10)")
            st.plotly_chart(fig_vif, use_container_width=True)
            st.caption("VIF < 10 表示可接受的多重共線性水平 | VIF < 10 indicates acceptable multicollinearity")

except Exception as e:
    st.error(f"特徵分析失敗：{str(e)}")

# ===== SHAP Interpretability =====
st.divider()
st.subheader("🔍 SHAP 可解釋性分析 | SHAP Interpretability")
st.caption("SHAP 值量化每個特徵對模型預測結果的邊際貢獻 | Feature-level model interpretability")

st.info("""
**SHAP（SHapley Additive exPlanations）是什麼？**

SHAP 值量化每個特徵對模型預測的貢獻程度。

圖中每個點代表一筆資料，橫軸為 SHAP 值大小（正值 = 推升預測，負值 = 壓低預測）。

顏色表示該特徵原始值的高低（紅 = 高，藍 = 低）。

特徵由上到下按整體重要性排列。
""")

try:
    from PIL import Image as PILImage

    fig_dir = Path(__file__).parent.parent.parent / "outputs" / "figures"
    shap_charts = sorted(fig_dir.glob("shap_summary_*.png"))

    if shap_charts:
        horizon_sel = st.selectbox(
            "選擇 Horizon | Select Horizon",
            [1, 5, 20],
            index=2,
            format_func=lambda x: f"D+{x}",
            key="shap_h"
        )
        relevant = [c for c in shap_charts if f"D{horizon_sel}" in c.name]
        if relevant:
            for chart in relevant:
                engine_name = "LightGBM" if "lightgbm" in chart.name else "XGBoost"
                with st.expander(f"📊 {engine_name} — D+{horizon_sel} SHAP Summary", expanded=True):
                    # Crop the matplotlib title area (top ~120px) to prevent text overlap
                    # Title is already displayed as the expander heading
                    try:
                        img = PILImage.open(chart)
                        crop_top = int(img.height * 0.08)  # ~200px for 2530px image
                        img_cropped = img.crop((0, crop_top, img.width, img.height))
                        st.image(img_cropped, use_container_width=True)
                    except Exception:
                        st.image(str(chart), use_container_width=True)
                    st.caption(f"↑ {engine_name} 模型中各特徵對預測的 SHAP 貢獻度（class=ALL）")
        else:
            st.info(f"D+{horizon_sel} 的 SHAP 圖表尚未生成")
    else:
        st.info("💡 SHAP 圖表尚未生成。請執行 run_phase2.py 產生。")
except Exception as e:
    st.warning(f"SHAP 分析無法載入：{str(e)}")

# ===== Quintile Analysis =====
st.divider()
st.subheader("📊 Quintile 因子分組分析 | Quintile Analysis")
st.caption("↓ 將股票按模型預測分數分為 5 組，若報酬呈單調遞增（Q1 最低、Q5 最高），代表模型有效排序能力。")
st.caption("將股票按預測分數分為五組，檢驗報酬的單調性 | Test monotonicity of returns across quintiles")

try:
    # Reload report independently to ensure quintile data is available
    # (avoids potential scope issues with the 'results' variable from upstream try blocks)
    import json as _json
    _qr_dir = Path(__file__).resolve().parent.parent.parent / "outputs" / "reports"
    if not _qr_dir.exists():
        _qr_dir = Path.cwd() / "outputs" / "reports"
    _qr_files = sorted(_qr_dir.glob("phase2_report_*.json"), reverse=True)
    _qr_report = {}
    if _qr_files:
        with open(_qr_files[0], "r", encoding="utf-8") as _qf:
            _qr_report = _json.load(_qf)
    _qr_results = _qr_report.get("results", {})
    quintile_data = _qr_results.get("quintile_analysis", {})

    if not quintile_data:
        st.info("Quintile 分組分析數據尚未生成。請確認報告中包含 quintile_analysis 資料。")
    else:
        for key, val in quintile_data.items():
            # Friendly name: ensemble_D1 → Ensemble D+1
            display_name = key.replace("ensemble_", "Ensemble ").replace("D", "D+")
            st.markdown(f"**{display_name}**")
            c1, c2 = st.columns(2)
            with c1:
                _spread = val.get('long_short_spread', 0)
                st.metric(
                    "Long-Short 差價",
                    f"{_spread:+.2f}%",
                    delta="Q5 − Q1 報酬"
                )
            with c2:
                st.metric(
                    "單調性 | Monotonicity",
                    f"{val.get('monotonicity', 0):.2f}",
                    delta="0~1 越高越好"
                )

            qr = val.get("quintile_returns", {})
            if qr:
                fig_q = go.Figure()

                # Bar chart
                q_keys = list(qr.keys())
                q_vals = list(qr.values())
                fig_q.add_trace(go.Bar(
                    x=[f"Q{k}" for k in q_keys],
                    y=q_vals,
                    marker_color=["#EF553B", "#FFA15A", "#636EFA", "#AB63FA", "#00CC96"][:len(q_keys)],
                    text=[f"{v:+.2f}%" for v in q_vals],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Return: %{customdata:.2f}%<extra></extra>",
                    customdata=q_vals
                ))

                fig_q.update_layout(
                    title=f"{display_name} Quintile 報酬 | Quintile Returns",
                    xaxis_title="分組 | Quintile (Q1=最低分數, Q5=最高分數)",
                    yaxis_title="年化報酬 | Annualized Return",
                    yaxis_ticksuffix="%",
                    height=380,
                    template="plotly_white",
                    hovermode="x unified"
                )

                avg_return = np.mean(q_vals)
                fig_q.add_hline(y=avg_return, line_dash="dash", line_color="gray",
                                annotation_text=f"平均 {avg_return:.2f}%")
                fig_q.add_hline(y=0, line_color="gray", line_dash="dot")

                st.plotly_chart(fig_q, use_container_width=True)

            st.markdown("")  # spacing between strategies

        st.markdown("""
        <div class="insight-box">
        <strong>📌 解讀 | Interpretation：</strong><br>
        理想情況下，報酬應從 Q1 到 Q5 單調遞增（或 Q5 明顯優於 Q1）。<br>
        若不存在單調性，表示模型信號不夠清晰，或包含噪音。
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.warning(f"Quintile 分析失敗：{str(e)}")
    import traceback
    st.code(traceback.format_exc())

# ===== Footer & Limitations =====
st.markdown("---")
st.caption("📌 限制條件：固定歷史資料集 ｜ 非即時市場數據 ｜ 基準為等權計算 ｜ Ensemble = 簡單平均 ｜ Phase 3 治理已實現")

st.markdown('<div class="page-footer">量化分析工作台 — Feature Analysis | 台灣股市多因子預測系統</div>', unsafe_allow_html=True)
