"""驗證壓力測試 — Validation Lab

展示三項壓力測試補件分析：
  §1. LOPO 支柱貢獻（Leave-One-Pillar-Out）
  §2. 閾值敏感度（Threshold Sweep / Top-K Precision）
  §3. 個股深度案例（2454 聯發科月度命中）
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import importlib.util

# ---- Load shared utils -------------------------------------------------
_utils_path = Path(__file__).resolve().parent.parent / "utils.py"
_spec = importlib.util.spec_from_file_location("dashboard_utils", str(_utils_path))
_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils)
inject_custom_css = _utils.inject_custom_css
render_topbar = _utils.render_topbar
load_phase6_json = _utils.load_phase6_json
figures_dir = _utils.figures_dir
render_kpi = _utils.render_kpi
glint_plotly_layout = _utils.glint_plotly_layout
glint_heatmap_colorscale = _utils.glint_heatmap_colorscale
glint_colorbar = _utils.glint_colorbar
GLINT_SEQUENTIAL_COOL = _utils.GLINT_SEQUENTIAL_COOL
glint_icon = _utils.glint_icon
glint_heading = _utils.glint_heading

inject_custom_css()

# ---- Top-bar (sticky breadcrumb + model chips + clock) ----
render_topbar(
    crumb_left="多因子股票分析系統",
    crumb_current="驗證壓測",
    chips=[("LOPO ablation", "pri"), ("threshold sweep", "vio"), ("2454 deep-case", "ok")],
    show_clock=True,
)

# ============================================================================
# Hero — v4 §6.3 Validation Lab spec
# ============================================================================
# v8 §12 · §20.7 — Dark terminal hero driven by centralised copy maps
_utils.render_terminal_hero(
    eyebrow=_utils.PAGE_EYEBROWS["phase6"],
    title=_utils.PAGE_TITLES["phase6"],
    briefing=_utils.PAGE_BRIEFINGS["phase6"],
    chips=[
        ("Model", "xgboost_D20", "info"),
        ("OOS", "404,724", "info"),
        ("Stress tests", "3", "ok"),
    ],
    tone="violet",
)

_utils.render_trust_strip([
    ("模型", "xgboost_D20", "info"),
    ("OOS 樣本", "404,724", "neutral"),
    ("支柱 / 特徵", "9 / 91", "neutral"),
    ("壓力測試", "3 項", "ok"),
])

# ============================================================================
# 白話導讀 — v11.5.13 · 摺疊化（不熟悉壓測邏輯者可展開閱讀）
# ============================================================================
with st.expander(
    "白話導讀 · PLAIN-LANGUAGE GUIDE — 三道壓測各在問什麼",
    expanded=False,
    icon=":material/menu_book:",
):
    # ---- Intro paragraph ----------------------------------------------------
    st.markdown("""
    <div style="
        background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.96) 100%);
        border: 1px solid rgba(103,232,249,0.22);
        border-left: 4px solid #67e8f9;
        border-radius: 14px;
        padding: 18px 22px;
        margin: 6px 0 14px 0;
        box-shadow: inset 0 1px 0 rgba(103,232,249,0.12);
    ">
        <div style="font-size: 1.08rem; font-weight: 700; color: #E8F7FC; line-height: 1.55; margin-bottom: 6px;">
            高 AUC 不等於有用。
        </div>
        <div style="font-size: 0.98rem; font-weight: 600; color: #67e8f9; line-height: 1.65; margin-bottom: 10px;">
            用三道獨立壓測，把結構性能力從樣本偶然中剝出來。
        </div>
        <div style="font-size: 0.88rem; color: #b4ccdf; line-height: 1.7;">
            三道測試互不依賴，全部通過，訊號才算站得住。
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Three explanatory cards -------------------------------------------
    col_g1, col_g2, col_g3 = st.columns(3, gap="medium")

    with col_g1:
        st.markdown("""
        <div style="
            background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.96) 100%);
            border: 1px solid rgba(103,232,249,0.22);
            border-top: 3px solid #67e8f9;
            border-radius: 12px;
            padding: 20px;
            height: 100%;
            box-shadow: 0 6px 20px rgba(0,0,0,0.35), inset 0 1px 0 rgba(103,232,249,0.10);
        ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                <span style="color:#67e8f9;display:inline-flex;">""" + glint_icon("microscope", 22, "#67e8f9") + """</span>
                <span style="
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.7rem; font-weight: 700; color: #67e8f9;
                    letter-spacing: 0.08em; text-transform: uppercase;
                ">§1 LOPO · 逐一抽離支柱</span>
            </div>
            <div style="font-size: 1.0rem; font-weight: 700; color: #E8F7FC; margin-bottom: 8px;">
                誰是骨幹，誰可以省？
            </div>
            <div style="font-size: 0.88rem; color: #cfe2ee; line-height: 1.75;">
                依序把 <strong>9 個支柱</strong>（技術、風險、基本、籌碼……）整組移除重訓，
                記錄 AUC 掉幅。<br><br>
                掉越多，該面向就越無法被其他支柱替代；掉幅趨近於零者，模型少了它也走得動。<br><br>
                <span style="color: #67e8f9; font-weight:600;">排序靠前者，才是真正的骨幹。</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_g2:
        st.markdown("""
        <div style="
            background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.96) 100%);
            border: 1px solid rgba(167,139,250,0.28);
            border-top: 3px solid #a78bfa;
            border-radius: 12px;
            padding: 20px;
            height: 100%;
            box-shadow: 0 6px 20px rgba(0,0,0,0.35), inset 0 1px 0 rgba(167,139,250,0.10);
        ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                <span style="color:#a78bfa;display:inline-flex;">""" + glint_icon("target", 22, "#a78bfa") + """</span>
                <span style="
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.7rem; font-weight: 700; color: #a78bfa;
                    letter-spacing: 0.08em; text-transform: uppercase;
                ">§2 閾值敏感度 · 訊號分級</span>
            </div>
            <div style="font-size: 1.0rem; font-weight: 700; color: #E8F7FC; margin-bottom: 8px;">
                多高的機率，才值得下注？
            </div>
            <div style="font-size: 0.88rem; color: #cfe2ee; line-height: 1.75;">
                把門檻從 <span class="gl-mono" style="color:#ddd6fe;">t = 0.30</span> 逐步拉到 0.50，
                追蹤 <strong>出手率</strong> 與 <strong>命中率</strong> 的同步變化。<br><br>
                越嚴越準、越寬越頻，兩者必然互斥——alpha 與交易頻率之間，只能取捨。<br><br>
                <span style="color: #a78bfa; font-weight:600;">找到兩邊交會的可執行門檻。</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_g3:
        st.markdown("""
        <div style="
            background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.96) 100%);
            border: 1px solid rgba(110,231,183,0.28);
            border-top: 3px solid #6ee7b7;
            border-radius: 12px;
            padding: 20px;
            height: 100%;
            box-shadow: 0 6px 20px rgba(0,0,0,0.35), inset 0 1px 0 rgba(110,231,183,0.10);
        ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                <span style="color:#6ee7b7;display:inline-flex;">""" + glint_icon("trending-up", 22, "#6ee7b7") + """</span>
                <span style="
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.7rem; font-weight: 700; color: #6ee7b7;
                    letter-spacing: 0.08em; text-transform: uppercase;
                ">§3 個股回放 · 2454 聯發科</span>
            </div>
            <div style="font-size: 1.0rem; font-weight: 700; color: #E8F7FC; margin-bottom: 8px;">
                紙上 OK，真實盤面頂得住？
            </div>
            <div style="font-size: 0.88rem; color: #cfe2ee; line-height: 1.75;">
                取 <strong>2454 聯發科</strong> 最近一年 OOS 資料逐日回放，
                對照模型機率與當日漲跌。<br><br>
                關鍵不在命中率高低，而在節奏——行情來臨時機率先升溫、盤整期閉得住嘴。<br><br>
                <span style="color: #6ee7b7; font-weight:600;">會出手、也懂收手，才是選時能力的樣貌。</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ---- Persistent nav hint (always visible even when 白話 collapsed) ---------
st.markdown("""
<div style="
    background: linear-gradient(180deg, rgba(37,25,12,0.92) 0%, rgba(22,14,5,0.96) 100%);
    border: 1px solid rgba(167,139,250,0.32);
    border-left: 4px solid #a78bfa;
    border-radius: 10px;
    padding: 10px 16px;
    margin: 14px 0 18px 0;
    font-size: 0.85rem;
    color: #ddd6fe;
    line-height: 1.65;
">
    <strong style="display:inline-flex;align-items:center;gap:6px;">""" + glint_icon("lightbulb", 15, "#c4b5fd") + """ 閱讀指引</strong>
    ：下方三個分頁對應三道壓測，結論直接看
    <strong style="color:#ede9fe;">「關鍵洞察」</strong>；細節收在「方法論」與欄位對照中。
</div>
""", unsafe_allow_html=True)

fig_dir = figures_dir()

# ============================================================================
# Load artefacts
# ============================================================================
lopo_data, lopo_path = load_phase6_json("lopo_pillar_contribution_D20.json")
thresh_data, thresh_path = load_phase6_json("threshold_sweep_xgb_D20.json")
case_data, case_path = load_phase6_json("single_stock_2454_mediatek.json")

missing = []
if lopo_data is None:   missing.append("lopo_pillar_contribution_D20.json")
if thresh_data is None: missing.append("threshold_sweep_xgb_D20.json")
if case_data is None:   missing.append("single_stock_2454_mediatek.json")

if missing:
    _utils.render_degraded_banner(
        title="壓力測試報告缺件",
        reason=f"找不到以下驗證報告：`{', '.join(missing)}`",
        available="Hero、白話導讀、方法論區塊仍可閱讀。",
        unavailable="LOPO 排名、閾值敏感度曲線、2454 個股命中分析需重跑報告才能呈現。",
        tone="warn",
    )
    st.caption(
        "重跑指令：`python 程式碼/執行Phase6_LOPO驗證.py` 及 "
        "`python 程式碼/執行Phase6_閾值敏感度與個股.py`"
    )
    st.stop()

# ============================================================================
# Tab layout
# ============================================================================
tab1, tab2, tab3 = st.tabs([
    "§1. LOPO 支柱貢獻",
    "§2. 閾值敏感度",
    "§3. 2454 個股深度案例",
])

# ============================================================================
# §1. LOPO
# ============================================================================
with tab1:
    baseline = lopo_data["baseline"]
    ranking = lopo_data["ranking_by_delta_auc"]
    pillar_counts = lopo_data["pillar_counts"]

    st.markdown("### 方法論 · LOPO 三層拆解")
    st.markdown("""
    <div class="gl-box-info">
    <strong>問題：</strong>拿掉這個支柱，模型會退步多少？<br>
    <strong>量法：</strong>依次移除 9 個支柱的所有因子並重訓，計算
    <span class="gl-mono">ΔAUC = baseline − LOPO</span>；ΔAUC 越大，代表該支柱越不可取代。<br>
    <strong>判讀：</strong>ΔAUC &gt; 50 bps 為強必要（不可抽）、20–50 bps 為中度必要、
    &lt; 20 bps 為可替代（可考慮瘦身）。
    </div>
    """, unsafe_allow_html=True)

    with st.expander("為什麼用 Leave-One-Pillar-Out，不用 permutation importance？", expanded=False, icon=":material/search:"):
        st.markdown("""
        兩者回答的問題不同：

        - **Permutation importance**：對既訓練好的模型打亂某一欄位後觀察 AUC 下降，
          衡量「該因子被模型用了多少」。對共線因子會嚴重低估——兩個相關因子可以互相頂替。
        - **LOPO（本頁採用）**：整組支柱移除後重訓。若 fund 支柱被拿掉，trend / val / risk
          可以重新瓜分訊號空間；衡量的是「**這個支柱有沒有其他支柱無法取代的獨立資訊**」。

        多因子壓測需要的是後者——LOPO 更嚴格、也更誠實。
        """)

    # KPI row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi("BASELINE AUC", f"{baseline['auc_macro']:.4f}",
                   sub=f"macro · all 9 pillars", accent="blue")
    with k2:
        render_kpi("BASELINE AUC_UP", f"{baseline['auc_up']:.4f}",
                   sub="class 'up' only", accent="violet")
    with k3:
        render_kpi("BASELINE IC_UP", f"{baseline['ic_up']:+.4f}",
                   sub="pearson corr vs label", accent="emerald")
    with k4:
        render_kpi("FEATURES", f"{lopo_data['n_selected_features']}",
                   sub="across 9 pillars", accent="cyan")

    st.markdown("### 各支柱 ΔAUC 貢獻排序")

    # Design-ported pillar-bar quick-scan summary (color-coded per pillar)
    render_pillar_bar = _utils.render_pillar_bar
    pillar_labels = {
        "risk": "風險面", "fund": "基本面", "chip": "籌碼面",
        "trend": "技術面", "val": "評價面", "event": "事件面",
        "ind": "產業面", "txt": "文本面", "sent": "情緒面",
    }
    max_d = max(abs(r["delta_auc"]) for r in ranking) or 0.001
    rows_html = []
    for r in ranking:
        pk = r["pillar"]
        delta_bps = r["delta_auc"] * 10000
        pct = (abs(r["delta_auc"]) / max_d) * 100
        rows_html.append(render_pillar_bar(
            pillar_key=pk,
            label=pillar_labels.get(pk, r.get("zh", pk)),
            feat_count=r.get("n_feats", r.get("n_features", 0)),
            pct=pct,
            delta_bps=delta_bps,
        ))
    st.markdown(
        '<div class="gl-panel" style="padding:18px 22px;margin-bottom:14px;">'
        + "".join(rows_html) + "</div>",
        unsafe_allow_html=True,
    )

    # PNG (static) — keep for fidelity with paper/report
    png = fig_dir / "lopo_pillar_contribution_D20.png"
    if png.exists():
        with st.expander("靜態 PNG（論文/報告用）", expanded=False, icon=":material/photo_library:"):
            st.image(str(png), use_container_width=True)

    # Interactive bar chart
    df_rank = pd.DataFrame(ranking)
    df_rank["ΔAUC (bps)"] = df_rank["delta_auc"] * 10000
    df_rank["ΔAUC_up (bps)"] = df_rank["delta_auc_up"] * 10000
    df_rank["ΔIC_up"] = df_rank["delta_ic"]

    colors = []
    for d in df_rank["delta_auc"]:
        if d > 0.005:    colors.append("#2563eb")  # blue — strong contributor
        elif d > 0:      colors.append("#7c3aed")  # violet — positive
        elif d > -0.002: colors.append("#94a3b8")  # grey — neutral
        else:            colors.append("#f43f5e")  # rose — hurts

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_rank["zh"],
        y=df_rank["ΔAUC (bps)"],
        text=[f"{v:+.1f}bps<br>n={n}" for v, n in zip(df_rank["ΔAUC (bps)"], df_rank["n_feats"])],
        textposition="outside",
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>ΔAUC: %{y:+.2f} bps<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(148,163,184,0.5)", line_width=1)
    fig.update_layout(**glint_plotly_layout(
        title="LOPO ΔAUC · 支柱抽離後的準度跌幅",
        subtitle="跌幅越大，該支柱越不可取代（單位：bps）",
        height=460, xlabel="特徵支柱（依 ΔAUC 排序）", ylabel="ΔAUC (bps)",
    ), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # Key insight
    top = ranking[0]
    second = ranking[1]
    st.markdown(f"""
    <div class="success-box">
    <strong style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("pin", 15, "#c4b5fd")} 關鍵洞察</strong>：
    <strong>{top['zh']}</strong> 排名第一（ΔAUC <span class="gl-mono">+{top['delta_auc']*10000:.1f} bps</span>、
    ΔAUC_up <span class="gl-mono">+{top['delta_auc_up']*10000:.1f} bps</span>），
    僅憑 <span class="gl-mono">{top['n_feats']}</span> 個特徵就撐起最大 upside 貢獻；
    <strong>{second['zh']}</strong> 緊跟其後（<span class="gl-mono">+{second['delta_auc']*10000:.1f} bps</span>）。
    結論：<strong>防守側資訊的邊際價值，遠高於單邊看多</strong>——模型的根基來自風險辨識，不是追漲。
    </div>
    """, unsafe_allow_html=True)

    # Detailed table
    st.markdown("### 完整結果表")

    # 欄位說明 — v11.2 dark-glint 化
    st.markdown("""
    <div style="
        background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.95) 100%);
        border: 1px solid rgba(103,232,249,0.28);
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
        font-size: 0.86rem;
        color: #cfe2ee;
        line-height: 1.75;
        box-shadow: inset 0 1px 0 rgba(103,232,249,0.12);
    ">
        <div style="font-family:'JetBrains Mono',monospace;font-weight: 700; color: #67e8f9; margin-bottom: 8px; letter-spacing: 0.10em; font-size:0.78rem;">
            欄位對照 · COLUMN REFERENCE
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 6px 20px;">
            <div><strong style="color: #67e8f9;">支柱代碼 / 中文名稱</strong>　因子的 9 個歸類面向</div>
            <div><strong style="color: #a78bfa;">特徵數</strong>　該支柱納入模型的因子數</div>
            <div><strong style="color: #6ee7b7;">ΔAUC (bps)</strong>　整體準度跌幅，越大越關鍵</div>
            <div><strong style="color: #ddd6fe;">ΔAUC_up (bps)</strong>　上漲判別的跌幅</div>
            <div><strong style="color: #fda4af;">ΔIC_up</strong>　機率與真實報酬的相關性變化</div>
        </div>
        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed rgba(103,232,249,0.22); font-size: 0.80rem; color: #b4ccdf;">
            bps = 0.01%；AUC 越接近 1，分類能力越精準。
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_display = df_rank.copy()
    df_display["pillar"] = df_display.apply(
        lambda r: f'<span class="gl-pillar" data-p="{r["pillar"]}">{r["pillar"]}</span>',
        axis=1
    )
    df_display = df_display[["pillar", "zh", "n_feats", "ΔAUC (bps)", "ΔAUC_up (bps)", "ΔIC_up"]]
    df_display.columns = ["支柱代碼", "中文名稱", "特徵數", "ΔAUC (bps)", "ΔAUC_up (bps)", "ΔIC_up"]

    # Format for display
    df_fmt = df_display.copy()
    df_fmt["ΔAUC (bps)"] = df_fmt["ΔAUC (bps)"].apply(lambda v: f"{v:+.2f}")
    df_fmt["ΔAUC_up (bps)"] = df_fmt["ΔAUC_up (bps)"].apply(lambda v: f"{v:+.2f}")
    df_fmt["ΔIC_up"] = df_fmt["ΔIC_up"].apply(lambda v: f"{v:+.4f}")

    # Render as HTML to preserve pillar chips
    html_table = df_fmt.to_html(escape=False, index=False, classes="gl-table")
    st.markdown(
        f"""
        <style>
        .gl-table {{ width:100%; border-collapse: collapse; font-family: var(--gl-font-sans);
                    background: rgba(8,16,32,0.55); border: 1px solid rgba(103,232,249,0.20);
                    border-radius: 8px; overflow: hidden; }}
        .gl-table th {{
            background: rgba(103,232,249,0.08); color: #67e8f9; font-weight:700;
            padding:10px 12px; text-align:left; border-bottom:1px solid rgba(103,232,249,0.32);
            font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.06em;
            font-family: var(--gl-font-mono);
        }}
        .gl-table td {{
            padding:10px 12px; border-bottom:1px solid rgba(103,232,249,0.12);
            font-family: var(--gl-font-mono); font-size: 0.86rem; color: #cfe2ee;
        }}
        .gl-table tbody tr:hover {{ background: rgba(103,232,249,0.06); }}
</style>
        {html_table}
        """, unsafe_allow_html=True
    )

    # Pillar feature-count breakdown
    with st.expander("各支柱特徵數分布", expanded=False, icon=":material/bar_chart:"):
        df_counts = pd.DataFrame([
            {"pillar": p, "n_features": n} for p, n in pillar_counts.items()
        ]).sort_values("n_features", ascending=False)
        fig2 = px.bar(
            df_counts, x="pillar", y="n_features",
            color="n_features", color_continuous_scale=GLINT_SEQUENTIAL_COOL,
        )
        fig2.update_layout(**glint_plotly_layout(
            title="9 支柱 · 特徵數分布",
            subtitle="生產版 91 個因子的分攤狀況",
            height=340, xlabel="Pillar", ylabel="Feature count",
        ), showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)


# ============================================================================
# §2. Threshold Sweep
# ============================================================================
with tab2:
    sweep = pd.DataFrame(thresh_data["threshold_sweep"])
    topk = pd.DataFrame(thresh_data["top_k_precision"])
    highlighted = thresh_data["highlighted_thresholds"]
    base_rate = thresh_data["base_up_rate"]
    oos_n = thresh_data["oos_n"]

    st.markdown("### 方法論")
    st.markdown(f"""
    <div class="gl-box-info">
    <strong>問題：</strong>多高的機率才值得出手？<br>
    <strong>量法：</strong>將機率門檻 <span class="gl-mono">t ∈ [0.30, 0.50]</span> 逐步掃描，
    觀察 <strong>出手率 (call rate)</strong>、<strong>命中率 (hit rate)</strong> 以及
    <strong>邊際優勢 (edge = hit − base)</strong> 三者的 trade-off。<br>
    <strong>樣本：</strong>OOS n = <span class="gl-mono">{oos_n:,}</span>，基準上漲率 <span class="gl-mono">{base_rate:.2%}</span>。
    </div>
    """, unsafe_allow_html=True)

    # Highlighted KPIs
    c = highlighted["conservative_0.40"]
    b = highlighted["balanced_0.35"]
    a = highlighted["aggressive_0.30"]

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi("BASE UP RATE", f"{base_rate:.2%}",
                   sub=f"OOS n={oos_n:,}", accent="cyan")
    with k2:
        render_kpi("CONSERVATIVE t=0.40",
                   f"{c['hit_rate']:.1%}",
                   delta=(f"+{c['edge']*100:.2f}pp edge", "up"),
                   sub=f"call {c['call_rate']:.1%}", accent="blue")
    with k3:
        render_kpi("BALANCED t=0.35",
                   f"{b['hit_rate']:.1%}",
                   delta=(f"+{b['edge']*100:.2f}pp edge", "up"),
                   sub=f"call {b['call_rate']:.1%}", accent="violet")
    with k4:
        render_kpi("AGGRESSIVE t=0.30",
                   f"{a['hit_rate']:.1%}",
                   delta=(f"+{a['edge']*100:.2f}pp edge", "up"),
                   sub=f"call {a['call_rate']:.1%}", accent="amber")

    st.markdown("### 閾值掃描 · 命中 vs. 出手")

    png = fig_dir / "threshold_sweep_xgb_D20.png"
    if png.exists():
        with st.expander("靜態 PNG（論文/報告用）", expanded=False, icon=":material/photo_library:"):
            st.image(str(png), use_container_width=True)

    # Interactive dual-axis chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sweep["threshold"],
        y=sweep["hit_rate"] * 100,
        mode="lines+markers",
        name="Hit Rate (%)",
        line=dict(color="#2563eb", width=3),
        marker=dict(size=8, color="#2563eb"),
        hovertemplate="t=%{x:.2f}<br>Hit %{y:.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=sweep["threshold"],
        y=sweep["call_rate"] * 100,
        mode="lines+markers",
        name="Call Rate (%)",
        line=dict(color="#a78bfa", width=3, dash="dot"),
        marker=dict(size=8, color="#a78bfa"),
        yaxis="y2",
        hovertemplate="t=%{x:.2f}<br>Call %{y:.2f}%<extra></extra>",
    ))
    fig.add_hline(y=base_rate * 100, line_dash="dash", line_color="rgba(148,163,184,0.5)",
                  annotation_text=f"Base rate {base_rate:.1%}",
                  annotation_position="top left")
    _lay = glint_plotly_layout(
        title="閾值掃描 · 命中率 vs. 出手率",
        subtitle="拉高門檻 → 命中上升、出手下降（兩者永遠互斥）",
        height=460, xlabel="Probability Threshold t", ylabel="Hit Rate (%)",
    )
    _lay["yaxis"]["tickfont"] = dict(family="JetBrains Mono", color="#2563eb", size=10)
    fig.update_layout(**_lay,
        yaxis2=dict(title=dict(text="Call Rate (%)", font=dict(family="JetBrains Mono", size=10, color="#a78bfa")),
                    overlaying="y", side="right",
                    tickfont=dict(family="JetBrains Mono", color="#a78bfa", size=10),
                    gridcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    fig.update_layout(legend=dict(x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.9)", bordercolor="rgba(37,99,235,0.18)"))
    st.plotly_chart(fig, use_container_width=True)

    # Edge curve
    st.markdown("### Edge 曲線 · 相對基準的超額命中")
    fig_edge = go.Figure()
    fig_edge.add_trace(go.Scatter(
        x=sweep["threshold"],
        y=sweep["edge"] * 100,
        mode="lines+markers",
        fill="tozeroy",
        line=dict(color="#10b981", width=3),
        marker=dict(size=8, color="#10b981"),
        fillcolor="rgba(16,185,129,0.1)",
        hovertemplate="t=%{x:.2f}<br>Edge +%{y:.2f}pp<extra></extra>",
    ))
    fig_edge.add_hline(y=0, line_dash="dash", line_color="rgba(148,163,184,0.5)")
    fig_edge.update_layout(**glint_plotly_layout(
        title="Edge 曲線 · 相對基準的超額命中",
        subtitle="正值 = 勝過隨機；曲線越陡，alpha 越集中",
        height=360, xlabel="Probability Threshold t", ylabel="Edge (pp)",
    ))
    st.plotly_chart(fig_edge, use_container_width=True)

    st.markdown(f"""
    <div class="success-box">
    <strong style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("pin", 15, "#c4b5fd")} 關鍵洞察</strong>：
    Edge 單調遞增，於 <span class="gl-mono">t = 0.50</span> 達 <strong>+{sweep['edge'].max()*100:.2f}pp</strong>
    （命中率 {sweep.loc[sweep['edge'].idxmax(), 'hit_rate']:.1%} vs. 基準 {base_rate:.1%}），
    但出手率僅 <span class="gl-mono">{sweep.loc[sweep['edge'].idxmax(), 'call_rate']:.2%}</span>——
    統計上顯著，執行上罕見。
    <strong>實務收在 t = 0.40</strong>：edge +3.14pp、出手率 8.83%，是次數與準度的交會點。
    </div>
    """, unsafe_allow_html=True)

    # Top-K Precision
    st.markdown("### Top-K Precision · 高信心訊號的命中率")
    topk_display = topk.copy()
    topk_display["top_pct_fmt"] = topk_display["top_pct"].apply(lambda v: f"Top {v*100:.1f}%")
    topk_display["hit_rate_fmt"] = topk_display["hit_rate"].apply(lambda v: f"{v:.2%}")
    topk_display["edge_fmt"] = topk_display["edge"].apply(lambda v: f"+{v*100:.2f}pp")

    fig_topk = go.Figure()
    fig_topk.add_trace(go.Bar(
        x=topk_display["top_pct_fmt"],
        y=topk_display["hit_rate"] * 100,
        text=topk_display["hit_rate_fmt"] + "<br>" + topk_display["edge_fmt"],
        textposition="outside",
        marker=dict(
            color=topk_display["edge"] * 100,
            colorscale=[[0, "#10b981"], [1, "#2563eb"]],
            showscale=False,
        ),
        hovertemplate="%{x}<br>n=%{customdata[0]:,}<br>Hit %{y:.2f}%<extra></extra>",
        customdata=topk[["n_picks"]].values,
    ))
    fig_topk.add_hline(y=base_rate * 100, line_dash="dash", line_color="rgba(148,163,184,0.5)",
                       annotation_text=f"Base {base_rate:.1%}")
    fig_topk.update_layout(**glint_plotly_layout(
        title="Top-K Precision · 高信心訊號的命中率",
        subtitle="K 越小 = 條件越嚴，越該展現 alpha",
        height=380, ylabel="Hit Rate (%)",
    ))
    st.plotly_chart(fig_topk, use_container_width=True)

    best = topk.iloc[0]
    st.markdown(f"""
    <div class="gl-box-info">
    <strong style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("pin", 15, "#22d3ee")} Top 0.1% 信心帶</strong>
    （<span class="gl-mono">n = {int(best['n_picks'])}</span> 筆最有把握的預測）命中率 <strong>{best['hit_rate']:.2%}</strong>、
    edge <strong>+{best['edge']*100:.2f}pp</strong>。精度隨 K 放寬而單調下降——代表 <strong>排序可信、非偶然集中</strong>。
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# §3. Single-stock case study — 2454 聯發科
# ============================================================================
with tab3:
    monthly = pd.DataFrame(case_data["monthly"])
    top10 = pd.DataFrame(case_data["top10_probability_days"])

    st.markdown("### 個案資訊")
    st.markdown(f"""
    <div class="gl-box-info">
    <strong>{case_data['stock_id']} {case_data['stock_name']}</strong> ·
    模型 <span class="gl-mono">{case_data['model']}</span> ·
    OOS 期間 <span class="gl-mono">{case_data['oos_range']['start']} → {case_data['oos_range']['end']}</span>
    （{case_data['oos_range']['n_days']} 個交易日）·
    使用閾值 <span class="gl-mono">t = {case_data['threshold']}</span>
    </div>
    """, unsafe_allow_html=True)

    # KPI row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi("OOS 交易日", f"{case_data['oos_range']['n_days']}",
                   sub="2024-04 → 2025-03", accent="cyan")
    with k2:
        render_kpi("出手次數", f"{case_data['n_calls']}",
                   sub=f"@ t={case_data['threshold']}", accent="violet")
    with k3:
        render_kpi("命中率", f"{case_data['overall_hit_rate']:.2%}",
                   delta=(f"+{case_data['edge_vs_base']*100:.2f}pp vs base", "up"),
                   sub=f"base {case_data['base_up_rate']:.2%}",
                   accent="emerald")
    with k4:
        render_kpi("BASE UP RATE", f"{case_data['base_up_rate']:.2%}",
                   sub="2454 OOS 上漲比率", accent="blue")

    st.markdown("### 月度信心 vs. 實戰命中")

    png = fig_dir / "single_stock_2454_mediatek.png"
    if png.exists():
        with st.expander("靜態 PNG（論文/報告用）", expanded=False, icon=":material/photo_library:"):
            st.image(str(png), use_container_width=True)

    # Monthly chart — dual axis: avg_up_prob + hit_rate_when_called
    monthly["hit_rate_safe"] = monthly["hit_rate_when_called"].fillna(0)
    monthly["has_calls"] = monthly["n_calls"] > 0

    fig_m = go.Figure()
    # Average up_prob as line
    fig_m.add_trace(go.Scatter(
        x=monthly["ym"], y=monthly["avg_up_prob"] * 100,
        mode="lines+markers",
        name="Avg Up Prob (%)",
        line=dict(color="#2563eb", width=3),
        marker=dict(size=10, color="#2563eb"),
        hovertemplate="%{x}<br>avg prob %{y:.2f}%<extra></extra>",
    ))
    # Threshold line
    fig_m.add_hline(y=case_data["threshold"] * 100, line_dash="dash", line_color="#f43f5e",
                    annotation_text=f"threshold t={case_data['threshold']}",
                    annotation_position="top right")
    # Hit rate when called (only months with calls)
    called = monthly[monthly["has_calls"]].copy()
    if not called.empty:
        fig_m.add_trace(go.Bar(
            x=called["ym"], y=called["hit_rate_when_called"] * 100,
            name="Hit Rate When Called (%)",
            marker=dict(
                color=called["hit_rate_when_called"] * 100,
                colorscale=[[0, "#f43f5e"], [0.5, "#a78bfa"], [1, "#10b981"]],
                showscale=False,
            ),
            yaxis="y2",
            opacity=0.72,
            hovertemplate="%{x}<br>hit %{y:.1f}%<br>calls %{customdata}<extra></extra>",
            customdata=called["n_calls"],
        ))
    _lay_m = glint_plotly_layout(
        title="2454 · 月度信心 vs. 實戰命中",
        subtitle="藍線 = 模型平均機率｜綠柱 = 當月出手命中率",
        height=460, xlabel="Month", ylabel="Avg Up Prob (%)",
    )
    _lay_m["yaxis"]["tickfont"] = dict(family="JetBrains Mono", color="#2563eb", size=10)
    fig_m.update_layout(**_lay_m,
        yaxis2=dict(title=dict(text="Hit Rate When Called (%)", font=dict(family="JetBrains Mono", size=10, color="#10b981")),
                    overlaying="y", side="right", range=[0, 100],
                    tickfont=dict(family="JetBrains Mono", color="#10b981", size=10),
                    gridcolor="rgba(0,0,0,0)"),
    )
    fig_m.update_layout(legend=dict(x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.9)", bordercolor="rgba(37,99,235,0.18)"))
    st.plotly_chart(fig_m, use_container_width=True)

    st.markdown(f"""
    <div class="success-box">
    <strong style="display:inline-flex;align-items:center;gap:6px;">{glint_icon("pin", 15, "#c4b5fd")} 關鍵洞察</strong>：
    <strong>2024 Q4 – 2025 Q1</strong>（AI 族群主升段）平均機率明顯升溫、突破 t = 0.35，出手集中於此段；
    <strong>2025-01 命中率 81.8%</strong>（11 次出手 9 中）。
    反觀 <strong>2024 Q2 – Q3</strong> 盤整期，機率被壓低、出手趨近於零——
    會出手、也懂得收手，正是選時能力的型態。
    </div>
    """, unsafe_allow_html=True)

    # Monthly table
    st.markdown("### 月度明細表")

    st.markdown("""
    <div style="
        background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.95) 100%);
        border: 1px solid rgba(103,232,249,0.28);
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
        font-size: 0.86rem;
        color: #cfe2ee;
        line-height: 1.75;
        box-shadow: inset 0 1px 0 rgba(103,232,249,0.12);
    ">
        <div style="font-family:'JetBrains Mono',monospace;font-weight: 700; color: #67e8f9; margin-bottom: 8px; letter-spacing: 0.10em; font-size:0.78rem;">
            欄位對照 · COLUMN REFERENCE
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 6px 20px;">
            <div><strong style="color: #67e8f9;">月份 / 交易日</strong>　OOS 月份與月內交易日數</div>
            <div><strong style="color: #6ee7b7;">實際上漲天數</strong>　當月真正上漲的天數</div>
            <div><strong style="color: #a78bfa;">出手次數</strong>　機率 ≥ 門檻的日數</div>
            <div><strong style="color: #6ee7b7;">命中次數</strong>　出手後實際上漲的日數</div>
            <div><strong style="color: #ddd6fe;">平均上漲機率</strong>　該月模型平均信心</div>
            <div><strong style="color: #ddd6fe;">當月上漲率</strong>　上漲天數 ÷ 交易日</div>
            <div><strong style="color: #fda4af;">出手率</strong>　出手次數 ÷ 交易日</div>
            <div><strong style="color: #6ee7b7;">出手命中率</strong>　命中 ÷ 出手（&gt; 當月上漲率即具選時力）</div>
        </div>
        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed rgba(103,232,249,0.22); font-size: 0.80rem; color: #b4ccdf;">
            讀法：平均機率在行情前升溫、出手命中率 &gt; 當月上漲率 = 選時能力。
        </div>
    </div>
    """, unsafe_allow_html=True)

    m_display = monthly.copy()
    m_display["avg_up_prob"] = m_display["avg_up_prob"].apply(lambda v: f"{v:.3f}")
    m_display["up_rate"] = m_display["up_rate"].apply(lambda v: f"{v:.2%}")
    m_display["call_rate"] = m_display["call_rate"].apply(lambda v: f"{v:.2%}")
    m_display["hit_rate_when_called"] = m_display["hit_rate_when_called"].apply(
        lambda v: f"{v:.2%}" if pd.notna(v) and v > 0 else "—"
    )
    m_display = m_display.rename(columns={
        "ym": "月份",
        "n_days": "交易日",
        "n_up": "實際上漲天數",
        "n_calls": "出手次數",
        "n_correct_calls": "命中次數",
        "avg_up_prob": "平均上漲機率",
        "up_rate": "當月上漲率",
        "call_rate": "出手率",
        "hit_rate_when_called": "出手命中率",
    })
    st.dataframe(m_display, use_container_width=True, hide_index=True)

    # Top-10 probability days — v11.5.13 redesigned presentation block
    st.markdown("""
    <div style="margin:26px 0 12px 0;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;
                         font-weight:700;letter-spacing:0.16em;color:#c4b5fd;
                         text-transform:uppercase;
                         background:rgba(167,139,250,0.12);
                         border:1px solid rgba(167,139,250,0.32);
                         padding:3px 10px;border-radius:4px;">
                HIGH-CONVICTION DAYS · 模型下注最重
            </span>
            <span style="height:1px;flex:1;background:linear-gradient(90deg,
                         rgba(167,139,250,0.32) 0%,transparent 100%);"></span>
        </div>
        <h3 style="margin:4px 0 6px 0;font-weight:700;color:#E8F7FC;">
            Top-10 機率最高交易日
        </h3>
        <div style="font-size:0.9rem;color:#b4ccdf;line-height:1.7;
                    border-left:2px solid rgba(167,139,250,0.32);padding-left:12px;">
            依 <span class="gl-mono" style="color:#ddd6fe;">up_prob</span> 由高至低排序的 10 個點位——
            模型在這 10 天投入了最多信心分量。
            高信心預測的實戰表現，是機率校準能力最直接的檢驗。
        </div>
    </div>
    """, unsafe_allow_html=True)
    t_display = top10.copy()
    t_display["up_prob"] = t_display["up_prob"].apply(lambda v: f"{v:.3f}")
    st.dataframe(t_display, use_container_width=True, hide_index=True)


# ============================================================================
# Footer
# ============================================================================
st.divider()
st.markdown(f"""
<div class="gl-footer">
Phase 6 Deep Validation · LOPO + Threshold + Single-Stock Case
&nbsp;·&nbsp; Generated {case_data.get('generated_at', 'n/a')[:10]}
&nbsp;·&nbsp; Source: <code>outputs/reports/*.json</code>
&nbsp;·&nbsp; 大數據與商業分析專案 (v4.0)
</div>
""", unsafe_allow_html=True)
