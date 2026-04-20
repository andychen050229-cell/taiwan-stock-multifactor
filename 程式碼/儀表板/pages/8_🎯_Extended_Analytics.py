"""Extended Analytics — Phase 3 擴充分析儀表板

展示四個核心擴充分析：
  A. Cost Sensitivity — 9 模型 × 3 成本情境
  B. Cross-Horizon   — 3 引擎 × 3 地平線
  C. Pillar Contribution — 特徵支柱貢獻
  D. Case Study — 個股（2330/2317/2454/2303）命中率
"""

import streamlit as st
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
load_phase3_analytics = _utils.load_phase3_analytics
figures_dir = _utils.figures_dir
glint_plotly_layout = _utils.glint_plotly_layout
glint_heatmap_colorscale = _utils.glint_heatmap_colorscale
glint_colorbar = _utils.glint_colorbar

inject_custom_css()

# ---- Top-bar (sticky breadcrumb + model chips + clock) ----
render_topbar(
    crumb_left="股票預測系統",
    crumb_current="延伸分析",
    chips=[("cost sensitivity", "pri"), ("cross-horizon", "vio"), ("case study", "ok")],
    show_clock=True,
)

# ---- Hero ---------------------------------------------------------------
st.markdown("""
<div class="gl-hero">
    <span class="gl-hero-eyebrow">PHASE 3 · 四項延伸診斷</span>
    <div class="gl-hero-title">延伸分析<span style="opacity:.55;font-weight:600;"> · 模型能賺錢嗎？</span></div>
    <div class="gl-hero-subtitle">
        從四個角度壓力測試我們的模型：<strong>成本</strong>、<strong>地平線</strong>、<strong>特徵</strong>、<strong>個股</strong>。
        綜合回答「實戰部署前還需要注意什麼」—— 這是走向 Phase 6 LOPO 深度驗證前的最後一站。
    </div>
    <div class="gl-chip-explain">
      <div class="item">
        <div class="head">A · 成本敏感度</div>
        <div class="desc">9 模型 × 3 手續費情境，看哪個組合在真實交易成本下仍有正報酬。</div>
      </div>
      <div class="item vio">
        <div class="head">B · 跨地平線穩定性</div>
        <div class="desc">比較 D+1 / D+5 / D+20 的 Rank IC 與 Sharpe，挑出最穩的持有期。</div>
      </div>
      <div class="item ok">
        <div class="head">C · 特徵支柱貢獻</div>
        <div class="desc">看 trend/fund/risk 等 9 個特徵支柱各貢獻多少預測力，驗證多因子設計是否分散。</div>
      </div>
      <div class="item warn">
        <div class="head">D · 龍頭個股實測</div>
        <div class="desc">2330/2317/2454/2303 的模型命中率對照基準上漲率，檢查訊號是否真能落地。</div>
      </div>
    </div>
    <div style="margin-top:14px; padding-top:12px; border-top:1px dashed rgba(37,99,235,0.18);">
        <span class="gl-chip danger">→ 想看更嚴格的 LOPO/Threshold/2454 月度拆解？跳到 <strong>Phase 6 深度驗證</strong></span>
    </div>
</div>
""", unsafe_allow_html=True)

# Load analytics
analytics_data = load_phase3_analytics()
if analytics_data[0] is None:
    st.warning(
        "尚未產生 Phase 3 擴充分析報告。請先執行：\n\n"
        "```bash\npython 程式碼/執行Phase3_分析擴充.py\n```"
    )
    st.stop()

analytics, analytics_name = analytics_data
st.caption(f"Source: `{analytics_name}` ｜ 基於 `{analytics.get('source_p2_report', 'n/a')}`")

results = analytics.get("results", {})
fig_dir = figures_dir()

# ----- A. Cost Sensitivity -----
st.header("A. Cost Sensitivity — 成本敏感度分析")
st.info(
    "9 個模型（3 引擎 × 3 地平線）在三種手續費情境下的績效對照：\n"
    "- **standard**：0.583% per rebalance（一般散戶）\n"
    "- **discount**：0.356%（VIP 折扣，法人實務基準）\n"
    "- **conservative**：0.732%（悲觀情境）\n"
)

cs = results.get("cost_sensitivity", {})
if cs:
    models = cs.get("models", [])
    costs = cs.get("costs", [])
    ret_matrix = cs.get("return_matrix", {})

    rows = []
    for m in models:
        row_data = ret_matrix.get(m, [[]])[0]
        if len(row_data) >= 3:
            rows.append({
                "model": m,
                "standard": row_data[0],
                "discount": row_data[1],
                "conservative": row_data[2],
            })
    if rows:
        df = pd.DataFrame(rows).set_index("model")

        # Heatmap via Plotly — glint-themed
        fig = go.Figure(data=go.Heatmap(
            z=df.values,
            x=df.columns.tolist(),
            y=df.index.tolist(),
            text=[[f"{v:+.2%}" for v in row] for row in df.values],
            texttemplate="%{text}",
            textfont={"family": "JetBrains Mono", "size": 11, "color": "#0f172a"},
            colorscale=glint_heatmap_colorscale("diverging"),
            zmid=0,
            xgap=3, ygap=3,
            colorbar=glint_colorbar(title="Return", fmt=".0%"),
            hovertemplate="<b>%{y}</b><br>%{x}: <b>%{z:+.2%}</b><extra></extra>",
        ))
        fig.update_layout(**glint_plotly_layout(
            title="Total Return · 模型 × 成本情境",
            subtitle="綠色=正報酬,紅色=負報酬,色深=絕對值大",
            height=480, xlabel="Cost Scenario", ylabel="Model × Horizon",
        ))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        <div class="insight-box">
        <strong>觀察</strong>：D+1 在所有成本情境皆為負報酬（最差 -77.5%），
        D+5 僅 xgb 在 discount 接近打平，<strong>D+20 是唯一全情境皆正報酬的地平線</strong>
        （xgb discount +15.80%，即使 conservative 仍 +9.88%）。
        </div>
        """, unsafe_allow_html=True)

    # Static PNG fallback
    png = fig_dir / "phase3_cost_sensitivity_heatmap.png"
    if png.exists():
        with st.expander("📸 靜態 PNG（matplotlib 全指標版）", expanded=False):
            st.image(str(png), use_container_width=True)

# ----- B. Cross-Horizon -----
st.header("B. Cross-Horizon — 跨引擎 × 跨地平線")

ch = results.get("cross_horizon", {})
if ch:
    engines = ch.get("engines", [])
    horizons = ch.get("horizons", [])
    rank_ic = ch.get("rank_ic", [])
    sharpe = ch.get("sharpe", [])

    col1, col2 = st.columns(2)
    with col1:
        if rank_ic:
            fig = go.Figure(data=go.Heatmap(
                z=rank_ic,
                x=[f"D+{h}" for h in horizons],
                y=engines,
                text=[[f"{v:+.4f}" for v in row] for row in rank_ic],
                texttemplate="%{text}",
                textfont={"family": "JetBrains Mono", "size": 11, "color": "#0f172a"},
                colorscale=glint_heatmap_colorscale("diverging"),
                zmid=0, xgap=3, ygap=3,
                colorbar=glint_colorbar(title="Rank IC", fmt=".3f"),
                hovertemplate="<b>%{y}</b> · %{x}<br>Rank IC: <b>%{z:+.4f}</b><extra></extra>",
            ))
            fig.update_layout(**glint_plotly_layout(
                title="Rank IC", subtitle="截面排序相關,越高訊號越有效",
                height=340,
            ))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if sharpe:
            fig = go.Figure(data=go.Heatmap(
                z=sharpe,
                x=[f"D+{h}" for h in horizons],
                y=engines,
                text=[[f"{v:+.3f}" for v in row] for row in sharpe],
                texttemplate="%{text}",
                textfont={"family": "JetBrains Mono", "size": 11, "color": "#0f172a"},
                colorscale=glint_heatmap_colorscale("diverging"),
                zmid=0, xgap=3, ygap=3,
                colorbar=glint_colorbar(title="Sharpe", fmt=".2f"),
                hovertemplate="<b>%{y}</b> · %{x}<br>Sharpe: <b>%{z:+.3f}</b><extra></extra>",
            ))
            fig.update_layout(**glint_plotly_layout(
                title="Sharpe Ratio", subtitle="風險調整後報酬,>1 為優秀",
                height=340,
            ))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    <div class="insight-box">
    <strong>結論</strong>：D+20 在所有引擎皆呈現正 Sharpe（0.70 ~ 0.81），
    Rank IC 雖僅 +0.014 ~ +0.015，但已是三個地平線中唯一全正值。
    </div>
    """, unsafe_allow_html=True)

    png = fig_dir / "phase3_cross_horizon_heatmap.png"
    if png.exists():
        with st.expander("📸 完整三指標熱圖（AUC/IC/Sharpe）", expanded=False):
            st.image(str(png), use_container_width=True)

# ----- C. Pillar Contribution -----
st.header("C. Pillar Contribution — 特徵支柱貢獻")
st.caption("依 P2 報告 top_features 正規化重要度，跨 6 個模型（LGB/XGB × D1/D5/D20）平均")

pc = results.get("pillar_contribution", {})
if pc:
    avg = pc.get("pillar_average", {})
    if avg:
        df_avg = pd.DataFrame(
            sorted(avg.items(), key=lambda x: -x[1]),
            columns=["Pillar", "AvgContribution"],
        )
        df_avg["Pct"] = df_avg["AvgContribution"].apply(lambda v: f"{v:.2%}")

        col1, col2 = st.columns([2, 1])
        with col1:
            PILLAR_COLORS = _utils.PILLAR_COLORS
            colors = [PILLAR_COLORS.get(p, "#64748b") for p in df_avg["Pillar"]]
            fig = go.Figure(go.Bar(
                x=df_avg["Pillar"],
                y=df_avg["AvgContribution"],
                text=df_avg["Pct"],
                textposition="outside",
                textfont=dict(family="JetBrains Mono", size=11, color="#0f172a"),
                marker=dict(
                    color=colors,
                    line=dict(color="rgba(37,99,235,0.15)", width=1),
                ),
                hovertemplate="<b>%{x}</b><br>Contribution: <b>%{y:.2%}</b><extra></extra>",
            ))
            layout = glint_plotly_layout(
                title="九支柱貢獻分解 · 6 模型平均",
                subtitle="normalized importance 加總 = 100%,越高代表模型越依賴該支柱",
                height=420, ylabel="Normalized Importance",
            )
            layout["yaxis"]["tickformat"] = ".0%"
            fig.update_layout(**layout, bargap=0.35)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.dataframe(df_avg, use_container_width=True, hide_index=True)

        st.markdown("""
        <div class="warning-box">
        ⚠️ <strong>重要觀察</strong>：<strong>trend 46% + risk 36% = 82% 的模型依賴</strong>；
        其餘 fund / val / ind / chip / event / sent / txt 合計僅約 18%。
        文字與情緒因子雖在 MI 階段保留 37 個特徵，但樹模型實際 split 次數偏少，
        代表<strong>現階段文字支柱對月頻排序的邊際貢獻尚未展現</strong>，
        建議 Phase 5 以 Leave-One-Pillar-Out 回測量化真實效用。
        </div>
        """, unsafe_allow_html=True)

    png = fig_dir / "phase3_pillar_contribution.png"
    if png.exists():
        with st.expander("📸 分模型支柱明細（堆疊長條）", expanded=False):
            st.image(str(png), use_container_width=True)

# ----- D. Case Study -----
st.header("D. Case Study — 龍頭個股命中率")
st.caption("xgboost_D20 OOF predictions（2024-04 → 2025-03, n≈213 個交易日）")

cs_d = results.get("case_study", {})
if cs_d:
    rows = []
    for stock_id, info in cs_d.items():
        rows.append({
            "股票": stock_id,
            "簡稱": {"2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2303": "聯電"}.get(stock_id, ""),
            "有效天數": info.get("n_valid_days", 0),
            "平均上漲機率": info.get("avg_up_prob", 0),
            "上漲呼叫數": info.get("n_up_calls", 0),
            "命中次數": info.get("n_hits", 0),
            "命中率": info.get("hit_rate_when_up_called", 0),
            "基準上漲率": info.get("base_up_rate", 0),
            "邊際優勢": info.get("hit_rate_when_up_called", 0) - info.get("base_up_rate", 0),
        })
    df_cs = pd.DataFrame(rows)

    # Format display
    df_display = df_cs.copy()
    df_display["平均上漲機率"] = df_display["平均上漲機率"].apply(lambda v: f"{v:.3f}")
    df_display["命中率"] = df_display["命中率"].apply(lambda v: f"{v:.2%}")
    df_display["基準上漲率"] = df_display["基準上漲率"].apply(lambda v: f"{v:.2%}")
    df_display["邊際優勢"] = df_display["邊際優勢"].apply(lambda v: f"{v:+.2%}")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Bar chart of edge
    fig = go.Figure(go.Bar(
        x=df_cs["股票"] + " " + df_cs["簡稱"],
        y=df_cs["邊際優勢"],
        text=[f"{v:+.2%}" for v in df_cs["邊際優勢"]],
        textposition="outside",
        textfont=dict(family="JetBrains Mono", size=11, color="#0f172a"),
        marker=dict(
            color=["#10b981" if v > 0 else "#f43f5e" for v in df_cs["邊際優勢"]],
            line=dict(color="rgba(37,99,235,0.15)", width=1),
        ),
        hovertemplate="<b>%{x}</b><br>Edge: <b>%{y:+.2%}</b><extra></extra>",
    ))
    layout = glint_plotly_layout(
        title="命中率邊際優勢 · 模型命中率 − 基準上漲率",
        subtitle=">0 代表模型比隨機猜測有實質優勢",
        height=380, ylabel="Edge",
    )
    layout["yaxis"]["tickformat"] = ".1%"
    fig.update_layout(**layout, bargap=0.35)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    <div class="insight-box">
    <strong>關鍵洞察</strong>：<strong>2454 聯發科</strong>展現 +17.13% 的顯著命中率邊際（66% vs 基準 49%），
    但 2330 / 2317 / 2303 為負邊際。即便同為半導體與電子龍頭，
    模型的 alpha 並非均勻分佈，<strong>實戰部署需搭配個股過濾器與產業中性化</strong>。
    </div>
    """, unsafe_allow_html=True)

    png = fig_dir / "phase3_case_study.png"
    if png.exists():
        with st.expander("📸 四股合併圖（每日 up_prob vs 實現標籤）", expanded=False):
            st.image(str(png), use_container_width=True)

# ----- Phase 6 Cross-link -----
st.divider()
st.markdown("""
<div class="gl-panel gl-panel-tint" style="margin:16px 0;">
    <div style="display:flex; justify-content:space-between; align-items:center; gap:20px;">
        <div>
            <div style="font-size:0.72rem; color:var(--gl-text-3); font-weight:600; letter-spacing:.06em; text-transform:uppercase;">DEEPER VALIDATION</div>
            <div style="font-size:1.15rem; font-weight:700; color:var(--gl-text); margin-top:4px;">
                🔭 Phase 6 深度驗證
            </div>
            <div style="font-size:.88rem; color:var(--gl-text-2); margin-top:6px;">
                Phase 3 回答「有多大貢獻」，Phase 6 回答「<strong>拿掉會掉多少</strong>」——
                LOPO 嚴格量化、閾值敏感度逐點掃描、2454 聯發科月度拆解。
            </div>
        </div>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <span class="gl-chip primary">LOPO 9 支柱</span>
            <span class="gl-chip violet">Threshold 21 點</span>
            <span class="gl-chip ok">2454 月度</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

if st.button("🔭  前往 Phase 6 深度驗證", use_container_width=True, type="primary"):
    st.switch_page(str(Path(__file__).resolve().parent / "A_🔭_Phase6_深度驗證.py"))

# ----- Footer -----
st.markdown("""
<div class="gl-footer">
Phase 3 Extended Analytics · 基於 OOF predictions + P2 top_features · 大數據與商業分析專案 v4.0
</div>
""", unsafe_allow_html=True)
