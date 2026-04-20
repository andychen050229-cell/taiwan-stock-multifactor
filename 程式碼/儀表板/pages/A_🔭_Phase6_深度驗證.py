"""Phase 6 — 深度驗證儀表板

展示三項 Phase 6 補件分析：
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

inject_custom_css()

# ---- Top-bar (sticky breadcrumb + model chips + clock) ----
render_topbar(
    crumb_left="股票預測系統",
    crumb_current="Phase 6 深度驗證",
    chips=[("LOPO ablation", "pri"), ("threshold sweep", "vio"), ("2454 deep-case", "ok")],
    show_clock=True,
)

# ============================================================================
# Hero
# ============================================================================
st.markdown("""
<div class="gl-hero">
    <span class="gl-hero-eyebrow">PHASE 6 · DEEP VALIDATION</span>
    <div class="gl-hero-title">深度驗證:LOPO · 閾值 · 個股</div>
    <div class="gl-hero-subtitle">
        三項補件分析回答三個核心問題 ─<br>
        <strong>「哪些特徵真的有用?」</strong>(LOPO)、
        <strong>「該多嚴格地出手?」</strong>(Threshold Sweep)、
        <strong>「訊號能落地到個股嗎?」</strong>(2454 聯發科個案)。<br>
        所有分析皆基於 <span class="gl-mono">xgboost_D20</span> OOF 預測(404k 筆 OOS 樣本)。
    </div>
    <div style="margin-top:18px;">
        <span class="gl-live">live · phase 6 validated</span>
        <span class="gl-chip primary" style="margin-left:8px;">xgboost_D20</span>
        <span class="gl-chip violet" style="margin-left:4px;">oos n=404,724</span>
        <span class="gl-chip ok" style="margin-left:4px;">9 pillars · 91 features</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# 白話導讀 — 用吃早餐的比喻說明三個分析(非技術使用者友善)
# ============================================================================
st.markdown("""
<div style="
    background: linear-gradient(135deg, #f0fdfa 0%, #ecfeff 50%, #f0f9ff 100%);
    border: 1px solid rgba(6,182,212,0.18);
    border-left: 4px solid #06b6d4;
    border-radius: 14px;
    padding: 22px 26px;
    margin: 18px 0 8px 0;
    box-shadow: 0 2px 8px rgba(6,182,212,0.06);
">
    <div style="
        display: inline-block;
        background: #06b6d4;
        color: #ffffff;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        padding: 3px 10px;
        border-radius: 4px;
        margin-bottom: 12px;
    ">白話導讀 · PLAIN-LANGUAGE GUIDE</div>
    <div style="font-size: 1.05rem; font-weight: 700; color: #0f172a; margin-bottom: 10px;">
        這一頁在做什麼?一句話:
        <span style="color: #0891b2;">檢驗模型是不是真的懂股票,還是只是運氣好。</span>
    </div>
    <div style="font-size: 0.95rem; color: #334155; line-height: 1.85;">
        想像一個廚師宣稱自己做的菜很好吃,<br>
        我們要做三件事來驗證他:
    </div>
</div>
""", unsafe_allow_html=True)

# 三個白話比喻卡片
col_g1, col_g2, col_g3 = st.columns(3, gap="medium")

with col_g1:
    st.markdown("""
    <div style="
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-top: 3px solid #2563eb;
        border-radius: 12px;
        padding: 20px;
        height: 100%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    ">
        <div style="
            display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
        ">
            <span style="font-size: 1.5rem;">🔬</span>
            <span style="
                font-size: 0.7rem; font-weight: 700; color: #2563eb;
                letter-spacing: 0.08em; text-transform: uppercase;
            ">§1 LOPO · 把食材一個一個拔掉</span>
        </div>
        <div style="font-size: 1.0rem; font-weight: 700; color: #0f172a; margin-bottom: 8px;">
            哪個食材最不可或缺?
        </div>
        <div style="font-size: 0.88rem; color: #475569; line-height: 1.7;">
            就像大廚的招牌菜,<br>
            我們把番茄、洋蔥、蒜頭 <strong>一個一個拿掉</strong>,<br>
            看少了哪一樣最難吃。<br><br>
            我們總共試 <strong>9 次</strong>,<br>
            每次拔掉一個面向的所有資料<br>
            (技術面、基本面、風險面......),<br>
            少了它,模型的準確度掉多少?<br>
            <strong style="color: #2563eb;">掉越多 → 這面向越重要。</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_g2:
    st.markdown("""
    <div style="
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-top: 3px solid #7c3aed;
        border-radius: 12px;
        padding: 20px;
        height: 100%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    ">
        <div style="
            display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
        ">
            <span style="font-size: 1.5rem;">🎯</span>
            <span style="
                font-size: 0.7rem; font-weight: 700; color: #7c3aed;
                letter-spacing: 0.08em; text-transform: uppercase;
            ">§2 閾值敏感度 · 要多有把握才出手</span>
        </div>
        <div style="font-size: 1.0rem; font-weight: 700; color: #0f172a; margin-bottom: 8px;">
            模型說「會漲」時,我該多信任?
        </div>
        <div style="font-size: 0.88rem; color: #475569; line-height: 1.7;">
            就像紅綠燈的紅有深淺,<br>
            機率 60% 跟 90% 意義不同。<br><br>
            把門檻從 30% 拉到 50%,<br>
            看 <strong>出手次數</strong> 跟 <strong>命中率</strong><br>
            怎麼跟著變化。<br><br>
            門檻高 → 出手少但命中高(保守),<br>
            門檻低 → 出手多但命中低(積極)。<br>
            <strong style="color: #7c3aed;">找出「兼顧次數與準度」的甜蜜點。</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_g3:
    st.markdown("""
    <div style="
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-top: 3px solid #10b981;
        border-radius: 12px;
        padding: 20px;
        height: 100%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    ">
        <div style="
            display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
        ">
            <span style="font-size: 1.5rem;">📈</span>
            <span style="
                font-size: 0.7rem; font-weight: 700; color: #10b981;
                letter-spacing: 0.08em; text-transform: uppercase;
            ">§3 2454 聯發科 · 真的拿去買會賺嗎</span>
        </div>
        <div style="font-size: 1.0rem; font-weight: 700; color: #0f172a; margin-bottom: 8px;">
            紙上 OK,實戰呢?
        </div>
        <div style="font-size: 0.88rem; color: #475569; line-height: 1.7;">
            挑一檔大家熟悉的股票 ─<br>
            <strong>2454 聯發科</strong>,<br>
            用過去一年真實盤面驗證。<br><br>
            當模型說「會漲」,我們買進,<br>
            看實際 <strong>漲了幾次 / 錯了幾次</strong>。<br><br>
            模型該在行情來時提高機率,<br>
            在盤整震盪時閉嘴不亂喊。<br>
            <strong style="color: #10b981;">會講話、會閉嘴,才是真本事。</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div style="
    background: #fefce8;
    border: 1px solid rgba(234,179,8,0.25);
    border-radius: 10px;
    padding: 14px 18px;
    margin: 14px 0 18px 0;
    font-size: 0.88rem;
    color: #713f12;
">
    <strong>💡 小提醒</strong>:下方三個分頁(🔬/🎯/📈)對應上面三個白話問題,
    每個分頁都附「方法論」說明與圖表,<br>
    不理解技術細節也能從 <strong>「關鍵洞察」區塊</strong> 看到重點結論。
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
    st.error(
        f"找不到以下 Phase 6 報告：`{', '.join(missing)}`\n\n"
        "請先執行：\n"
        "```bash\n"
        "python 程式碼/執行Phase6_LOPO驗證.py\n"
        "python 程式碼/執行Phase6_閾值敏感度與個股.py\n"
        "```"
    )
    st.stop()

# ============================================================================
# Tab layout
# ============================================================================
tab1, tab2, tab3 = st.tabs([
    "🔬 §1. LOPO 支柱貢獻",
    "🎯 §2. 閾值敏感度",
    "📈 §3. 2454 個股深度案例",
])

# ============================================================================
# §1. LOPO
# ============================================================================
with tab1:
    baseline = lopo_data["baseline"]
    ranking = lopo_data["ranking_by_delta_auc"]
    pillar_counts = lopo_data["pillar_counts"]

    st.markdown("### 方法論")
    st.markdown("""
    <div class="gl-box-info">
    <strong>Leave-One-Pillar-Out (LOPO)</strong> 是量化每個特徵支柱對最終模型**邊際貢獻**的標準做法：
    依次把 9 個支柱的所有特徵「移除」重訓，用 <span class="gl-mono">ΔAUC = baseline − LOPO</span>
    來衡量該支柱的真實價值。<strong>ΔAUC 越大 → 該支柱越不可或缺</strong>。
    </div>
    """, unsafe_allow_html=True)

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
        with st.expander("📸 靜態 PNG（論文/報告用）", expanded=False):
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
    fig.add_hline(y=0, line_dash="dash", line_color="#94a3b8", line_width=1)
    fig.update_layout(
        title="LOPO ΔAUC — 「拿掉該支柱後 AUC 下降多少」",
        yaxis_title="ΔAUC (basis points, bps)",
        xaxis_title="特徵支柱（依 ΔAUC 降序）",
        height=460,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", color="#0f172a"),
        showlegend=False,
    )
    fig.update_yaxes(gridcolor="#e2e8f0", zerolinecolor="#cbd5e1")
    st.plotly_chart(fig, use_container_width=True)

    # Key insight
    top = ranking[0]
    second = ranking[1]
    st.markdown(f"""
    <div class="success-box">
    <strong>📌 關鍵洞察</strong>：<strong>{top['zh']}</strong> 是最不可或缺的支柱
    （ΔAUC = <span class="gl-mono">+{top['delta_auc']*10000:.1f} bps</span>，
    ΔAUC_up = <span class="gl-mono">+{top['delta_auc_up']*10000:.1f} bps</span>），
    其次是 <strong>{second['zh']}</strong>（<span class="gl-mono">+{second['delta_auc']*10000:.1f} bps</span>）。
    風險支柱僅 <span class="gl-mono">{top['n_feats']}</span> 個特徵卻貢獻最大 ΔAUC_up，
    證明 <strong>downside 保護的邊際價值遠高於單純追求 upside</strong>。
    </div>
    """, unsafe_allow_html=True)

    # Detailed table
    st.markdown("### 完整結果表")

    # 欄位說明 — 每一欄代表什麼（白話版）
    st.markdown("""
    <div style="
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
        font-size: 0.86rem;
        color: #334155;
        line-height: 1.75;
    ">
        <div style="font-weight: 700; color: #0f172a; margin-bottom: 6px;">
            📘 欄位說明 — 每一欄代表什麼?
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 6px 20px;">
            <div><strong style="color: #2563eb;">支柱代碼</strong>:技術代稱(trend/risk/fund...)</div>
            <div><strong style="color: #2563eb;">中文名稱</strong>:白話說明(技術面/風險面/基本面...)</div>
            <div><strong style="color: #7c3aed;">特徵數</strong>:這個面向用了幾個資料欄位</div>
            <div><strong style="color: #10b981;">ΔAUC (bps)</strong>:拿掉這面向後,模型整體準度掉多少(越大越不可少)</div>
            <div><strong style="color: #f59e0b;">ΔAUC_up (bps)</strong>:對「會漲」這件事的判斷力掉多少</div>
            <div><strong style="color: #ef4444;">ΔIC_up</strong>:預測機率與實際表現的相關性變化</div>
        </div>
        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #cbd5e1; font-size: 0.82rem; color: #64748b;">
            <strong>bps</strong> = basis point(基點),1 bps = 0.01% 準確度。
            <strong>AUC</strong> 是分類準確度的指標,越靠近 1 越準。
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
        .gl-table {{ width:100%; border-collapse: collapse; font-family: var(--gl-font-sans); }}
        .gl-table th {{
            background: #f1f5f9; color: #0f172a; font-weight:600;
            padding:10px 12px; text-align:left; border-bottom:2px solid #cbd5e1;
            font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.04em;
        }}
        .gl-table td {{
            padding:10px 12px; border-bottom:1px solid #e2e8f0;
            font-family: var(--gl-font-mono); font-size: 0.86rem;
        }}
        .gl-table tbody tr:hover {{ background: #f8fafc; }}
</style>
        {html_table}
        """, unsafe_allow_html=True
    )

    # Pillar feature-count breakdown
    with st.expander("📊 各支柱特徵數分布", expanded=False):
        df_counts = pd.DataFrame([
            {"pillar": p, "n_features": n} for p, n in pillar_counts.items()
        ]).sort_values("n_features", ascending=False)
        fig2 = px.bar(
            df_counts, x="pillar", y="n_features",
            title="9 支柱特徵數（生產版 91 個）",
            color="n_features", color_continuous_scale="Blues",
        )
        fig2.update_layout(
            height=340,
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            showlegend=False, coloraxis_showscale=False,
        )
        fig2.update_yaxes(gridcolor="#e2e8f0")
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
    <strong>閾值敏感度掃描</strong>回答「我該多嚴格地相信模型訊號？」：
    讓預測機率閾值 <span class="gl-mono">t ∈ [0.30, 0.50]</span> 逐步調整，觀察
    <strong>出手率 (call rate)</strong>、<strong>命中率 (hit rate)</strong>、
    <strong>邊際優勢 (edge = hit rate − base rate)</strong> 的 trade-off。
    樣本 <span class="gl-mono">n = {oos_n:,}</span>，基準上漲率 <span class="gl-mono">{base_rate:.2%}</span>。
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

    st.markdown("### 閾值掃描曲線")

    png = fig_dir / "threshold_sweep_xgb_D20.png"
    if png.exists():
        with st.expander("📸 靜態 PNG（論文/報告用）", expanded=False):
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
        line=dict(color="#f59e0b", width=3, dash="dot"),
        marker=dict(size=8, color="#f59e0b"),
        yaxis="y2",
        hovertemplate="t=%{x:.2f}<br>Call %{y:.2f}%<extra></extra>",
    ))
    fig.add_hline(y=base_rate * 100, line_dash="dash", line_color="#94a3b8",
                  annotation_text=f"Base rate {base_rate:.1%}",
                  annotation_position="top left")
    fig.update_layout(
        title="閾值 vs 命中率 / 出手率（藍=hit、橙=call）",
        xaxis=dict(title="Probability Threshold t"),
        yaxis=dict(title="Hit Rate (%)", tickfont=dict(color="#2563eb"),
                   gridcolor="#e2e8f0"),
        yaxis2=dict(title="Call Rate (%)", overlaying="y", side="right",
                    tickfont=dict(color="#f59e0b")),
        height=460,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", color="#0f172a"),
        legend=dict(x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.9)", bordercolor="#e2e8f0"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Edge curve
    st.markdown("### Edge (命中率 − 基準率) 曲線")
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
    fig_edge.add_hline(y=0, line_dash="dash", line_color="#94a3b8")
    fig_edge.update_layout(
        title="Edge = P(label=up | prob>=t) − base_up_rate",
        xaxis_title="Probability Threshold t",
        yaxis_title="Edge (percentage points, pp)",
        height=360,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", color="#0f172a"),
    )
    fig_edge.update_yaxes(gridcolor="#e2e8f0")
    st.plotly_chart(fig_edge, use_container_width=True)

    st.markdown(f"""
    <div class="success-box">
    <strong>📌 關鍵洞察</strong>：Edge 幾乎**單調遞增**至 <span class="gl-mono">t=0.50</span>
    達到 <strong>+{sweep['edge'].max()*100:.2f}pp</strong>（命中率 {sweep.loc[sweep['edge'].idxmax(), 'hit_rate']:.1%} vs 基準 {base_rate:.1%}），
    但出手率降至 <span class="gl-mono">{sweep.loc[sweep['edge'].idxmax(), 'call_rate']:.2%}</span>（極端稀少）。
    <strong>實務建議使用 t=0.40</strong>（保守型）：edge +3.14pp，call 8.83%，兼顧統計顯著性與交易頻率。
    </div>
    """, unsafe_allow_html=True)

    # Top-K Precision
    st.markdown("### Top-K Precision（最強訊號命中率）")
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
    fig_topk.add_hline(y=base_rate * 100, line_dash="dash", line_color="#94a3b8",
                       annotation_text=f"Base {base_rate:.1%}")
    fig_topk.update_layout(
        title="精度曲線：模型最強訊號的命中率",
        yaxis_title="Hit Rate (%)",
        height=380,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", color="#0f172a"),
    )
    fig_topk.update_yaxes(gridcolor="#e2e8f0")
    st.plotly_chart(fig_topk, use_container_width=True)

    best = topk.iloc[0]
    st.markdown(f"""
    <div class="gl-box-info">
    <strong>📌 最強訊號 Top 0.1%</strong>（n={int(best['n_picks'])} 筆最有把握的預測）
    命中率 <strong>{best['hit_rate']:.2%}</strong>，相對基準 <strong>+{best['edge']*100:.2f}pp edge</strong>。
    精度曲線隨 Top-K 擴大而單調下降，證明模型**機率校準合理、排序可信**。
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

    st.markdown("### 月度命中 vs 出手走勢")

    png = fig_dir / "single_stock_2454_mediatek.png"
    if png.exists():
        with st.expander("📸 靜態 PNG（論文/報告用）", expanded=False):
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
                colorscale=[[0, "#f43f5e"], [0.5, "#f59e0b"], [1, "#10b981"]],
                showscale=False,
            ),
            yaxis="y2",
            opacity=0.72,
            hovertemplate="%{x}<br>hit %{y:.1f}%<br>calls %{customdata}<extra></extra>",
            customdata=called["n_calls"],
        ))
    fig_m.update_layout(
        title="2454 聯發科 — 月度平均上漲機率 vs 實際命中率",
        xaxis=dict(title="Month"),
        yaxis=dict(title="Avg Up Prob (%)", tickfont=dict(color="#2563eb"), gridcolor="#e2e8f0"),
        yaxis2=dict(title="Hit Rate When Called (%)", overlaying="y", side="right",
                    tickfont=dict(color="#10b981"), range=[0, 100]),
        height=460,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", color="#0f172a"),
        legend=dict(x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.9)", bordercolor="#e2e8f0"),
    )
    st.plotly_chart(fig_m, use_container_width=True)

    st.markdown("""
    <div class="success-box">
    <strong>📌 關鍵洞察</strong>：模型在 <strong>2024-10 ~ 2025-01</strong> 這段 AI 族群行情期間
    **明顯提升平均機率**（突破 t=0.35 門檻），並累積大部分出手；2025-01 命中率達
    <span class="gl-mono">81.8%</span>（11 次出手對中 9 次）。
    2024-06 ~ 2024-09 期間模型正確判斷**風險較高不出手**。
    顯示模型具備「有訊號時才喊、沒把握時閉嘴」的理想行為。
    </div>
    """, unsafe_allow_html=True)

    # Monthly table
    st.markdown("### 月度明細表")

    st.markdown("""
    <div style="
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
        font-size: 0.86rem;
        color: #334155;
        line-height: 1.75;
    ">
        <div style="font-weight: 700; color: #0f172a; margin-bottom: 6px;">
            📘 欄位說明 — 每一欄怎麼看?
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 6px 20px;">
            <div><strong style="color: #2563eb;">月份</strong>:OOS 期間的月份(YYYY-MM)</div>
            <div><strong style="color: #2563eb;">交易日</strong>:該月 2454 有多少個交易日</div>
            <div><strong style="color: #10b981;">實際上漲天數</strong>:真實結果,該月漲了幾天</div>
            <div><strong style="color: #7c3aed;">出手次數</strong>:模型認為會漲(機率≥門檻)的天數</div>
            <div><strong style="color: #10b981;">命中次數</strong>:出手後實際真的漲了幾次</div>
            <div><strong style="color: #f59e0b;">平均上漲機率</strong>:該月模型平均預測有多看好</div>
            <div><strong style="color: #f59e0b;">當月上漲率</strong>:實際上漲天數 / 總交易日</div>
            <div><strong style="color: #ef4444;">出手率</strong>:模型出手次數 / 總交易日</div>
            <div><strong style="color: #10b981;">出手命中率</strong>:命中次數 / 出手次數(越高越準)</div>
        </div>
        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #cbd5e1; font-size: 0.82rem; color: #64748b;">
            <strong>怎麼讀?</strong>重點看「平均上漲機率」是否有在行情來前上升,
            以及「出手命中率」是否 > 當月上漲率(代表選時能力)。
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

    # Top-10 probability days
    st.markdown("### Top-10 機率最高交易日（模型最看好）")
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
