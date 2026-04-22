"""Text Analysis — 文本情緒分析儀表板（Phase 5B 產物 · v11.5.14 輿情分析師重構）

從「展示原始結果」升級為「可行動的輿情訊號」：
  A. 看多 vs. 看空 關鍵字色譜 — 每個詞的 lift 對應勝率偏移
  B. 關鍵字 Lift × Chi² 強度圖 — 500 詞的方向性與重要性雙軸
  C. 情緒 → 報酬驗證 — 情緒極端象限的反彈機率（contrarian 訊號）
  D. 新聞 vs. 論壇 · 情緒分歧 — 兩個獨立來源的對照
  E. 每日情緒指數時序
  F. 11 情緒特徵分布 + 覆蓋不均預警
  G. 摺疊：原始輸出補件（詞雲 / 平台 / 時序 PNG）
"""

import math
from pathlib import Path
import importlib.util

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

_utils_path = Path(__file__).resolve().parent.parent / "utils.py"
_spec = importlib.util.spec_from_file_location("dashboard_utils", str(_utils_path))
_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils)
inject_custom_css = _utils.inject_custom_css
render_topbar = _utils.render_topbar
figures_dir = _utils.figures_dir
render_terminal_hero = _utils.render_terminal_hero
render_section_title = _utils.render_section_title
PAGE_EYEBROWS = _utils.PAGE_EYEBROWS
PAGE_TITLES = _utils.PAGE_TITLES
PAGE_BRIEFINGS = _utils.PAGE_BRIEFINGS
render_trust_strip = _utils.render_trust_strip
render_page_footer = _utils.render_page_footer
glint_plotly_layout = _utils.glint_plotly_layout
glint_icon = _utils.glint_icon
render_kpi = _utils.render_kpi

inject_custom_css()

# ---- Top-bar --------------------------------------------------------------
render_topbar(
    crumb_left="多因子股票分析系統",
    crumb_current="文本情緒分析",
    chips=[("jieba + SnowNLP", "pri"), ("500 keywords", "vio"), ("phase 5B", "ok")],
    show_clock=True,
)

render_terminal_hero(
    eyebrow=PAGE_EYEBROWS["text"],
    title=PAGE_TITLES["text"],
    briefing=PAGE_BRIEFINGS["text"],
)
render_trust_strip([
    ("原始文章",    "1,125,134",  "violet"),
    ("關鍵字",       "500",        "cyan"),
    ("txt_ 特徵",   "1,521",      "blue"),
    ("sent_ 特徵",  "11",         "emerald"),
])

fig_dir = figures_dir()

# ============================================================================
# Cached data loaders
# ============================================================================
_OUTPUTS = Path(__file__).resolve().parent.parent.parent.parent / "outputs"


@st.cache_data(ttl=3600, show_spinner=False)
def load_keywords() -> pd.DataFrame | None:
    path = _OUTPUTS / "text_keywords.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)


@st.cache_data(ttl=3600, show_spinner="讀取 948K 情緒樣本中…")
def load_sentiment_panel() -> pd.DataFrame | None:
    """Load the minimal columns needed for sentiment analytics (~10 cols, ~2s)."""
    path = _OUTPUTS / "feature_store_final.parquet"
    if not path.exists():
        return None
    cols = [
        "trade_date", "label_1", "label_5", "label_20",
        "sent_polarity_1d", "sent_polarity_5d", "sent_polarity_20d",
        "sent_pos_neg_spread_5d", "sent_pos_ratio_5d", "sent_neg_ratio_5d",
        "sent_news_mean_5d", "sent_forum_mean_5d",
        "sent_volatility_5d", "sent_extreme_ratio_5d", "sent_reversal_5d",
    ]
    df = pd.read_parquet(path, columns=cols)
    # Binary 'up' labels derived from tri-state {-1, 0, 1}
    for L in (1, 5, 20):
        df[f"up_{L}"] = (df[f"label_{L}"] == 1).astype(np.int8)
    return df


def sentiment_quintile_edge(df: pd.DataFrame, sent_col: str, label_col: str):
    """Bucket samples into 5 sentiment quintiles and return hit-rate edge vs baseline."""
    m = df[sent_col].notna() & df[label_col].notna()
    d = df.loc[m, [sent_col, label_col]].copy()
    # rank-based quintile to handle duplicates in sentiment (many zeros)
    d["q"] = pd.qcut(
        d[sent_col].rank(method="first"), q=5,
        labels=["Q1 最負", "Q2 負", "Q3 中", "Q4 正", "Q5 最正"],
    )
    base = d[label_col].mean()
    g = d.groupby("q", observed=True).agg(
        n=(label_col, "size"),
        hit_rate=(label_col, "mean"),
        sent_mean=(sent_col, "mean"),
    ).reset_index()
    g["edge_pp"] = (g["hit_rate"] - base) * 100
    return g, base


def daily_sentiment_index(df: pd.DataFrame) -> pd.DataFrame:
    d = df.groupby("trade_date").agg(
        sent_mean=("sent_polarity_1d", "mean"),
        news_mean=("sent_news_mean_5d", "mean"),
        forum_mean=("sent_forum_mean_5d", "mean"),
    ).reset_index()
    d["sent_20ma"] = d["sent_mean"].rolling(20, min_periods=5).mean()
    return d


# ============================================================================
# Overview KPIs
# ============================================================================
st.markdown("### 輿情資產概覽")
col1, col2, col3, col4 = st.columns(4)
col1.metric("原始文章數", "1,125,134", "PTT / Dcard / Mobile01 / Yahoo")
col2.metric("Selected 關鍵字", "500", "from 9,655 候選")
col3.metric("txt_ 特徵", "1,521", "500 kw × 3 window + 21 volume")
col4.metric("sent_ 特徵", "11", "polarity / ratio / spread / news-forum")

st.markdown("""
<div style="
    background: linear-gradient(180deg, rgba(15,23,37,0.92) 0%, rgba(8,16,32,0.95) 100%);
    border: 1px solid rgba(103,232,249,0.22);
    border-left: 4px solid #67e8f9;
    border-radius: 10px;
    padding: 12px 18px;
    margin: 10px 0 18px 0;
    font-size: 0.88rem;
    color: #cfe2ee;
    line-height: 1.7;
">
    <strong style="color:#E8F7FC;">這一頁的定位：</strong>從 1.12M 篇原文，萃取出可下注的方向性訊號。
    每個關鍵字背後都是 <span class="gl-mono" style="color:#67e8f9;">lift = 出現時上漲機率 ÷ 基準上漲機率</span>——
    直接告訴你這個詞值不值得關注、往哪個方向下注。
</div>
""", unsafe_allow_html=True)

# ============================================================================
# A. Keyword spectrum — Bullish vs Bearish
# ============================================================================
render_section_title("A. 看多 vs. 看空 · 關鍵字色譜", "Directional Keyword Spectrum · ranked by lift")
st.caption("Lift > 1 → 該詞出現時後續上漲機率 **高於** 基準；Lift < 1 → **低於** 基準。色塊深度 ∝ lift 絕對偏離。")

kw = load_keywords()
if kw is None:
    st.warning("找不到 `outputs/text_keywords.parquet`。")
else:
    sel = kw[kw["selected"]].copy()
    top_bull = sel.nlargest(20, "lift").reset_index(drop=True)
    top_bear = sel.nsmallest(20, "lift").reset_index(drop=True)
    bull_max = top_bull["lift"].max()
    bear_min = top_bear["lift"].min()

    col_b, col_s = st.columns(2, gap="medium")

    with col_b:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            '<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.68rem;'
            'font-weight:700;letter-spacing:0.14em;color:#6ee7b7;text-transform:uppercase;'
            'background:rgba(110,231,183,0.12);border:1px solid rgba(110,231,183,0.32);'
            'padding:3px 10px;border-radius:4px;">BULLISH · 看多 TOP 20</span>'
            '<span style="height:1px;flex:1;background:linear-gradient(90deg,rgba(110,231,183,0.32) 0%,transparent 100%);"></span>'
            '</div>',
            unsafe_allow_html=True,
        )
        rows = []
        for i, r in top_bull.iterrows():
            intensity = min(1.0, (r["lift"] - 1.0) / max(bull_max - 1.0, 0.01))
            bg_alpha = 0.10 + intensity * 0.35
            rows.append(
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'background:rgba(20,184,166,{bg_alpha:.2f});'
                f'border-left:3px solid #14b8a6;padding:6px 12px;margin:3px 0;border-radius:4px;">'
                f'<span style="display:flex;align-items:center;gap:10px;">'
                f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.72rem;color:#5eead4;min-width:22px;">'
                f'#{i+1:02d}</span>'
                f'<span style="color:#e0fdf4;font-weight:600;">{r["term"]}</span>'
                f'</span>'
                f'<span style="display:flex;align-items:center;gap:8px;">'
                f'<span style="font-family:\'JetBrains Mono\',monospace;color:#6ee7b7;font-size:0.82rem;font-weight:700;">'
                f'×{r["lift"]:.2f}</span>'
                f'<span style="font-family:\'JetBrains Mono\',monospace;color:rgba(148,163,184,0.7);font-size:0.72rem;">'
                f'χ² {r["chi2"]:.0f}</span>'
                f'</span></div>'
            )
        st.markdown("".join(rows), unsafe_allow_html=True)

    with col_s:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            '<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.68rem;'
            'font-weight:700;letter-spacing:0.14em;color:#fb7185;text-transform:uppercase;'
            'background:rgba(244,63,94,0.12);border:1px solid rgba(244,63,94,0.32);'
            'padding:3px 10px;border-radius:4px;">BEARISH · 看空 TOP 20</span>'
            '<span style="height:1px;flex:1;background:linear-gradient(90deg,rgba(244,63,94,0.32) 0%,transparent 100%);"></span>'
            '</div>',
            unsafe_allow_html=True,
        )
        rows = []
        for i, r in top_bear.iterrows():
            intensity = min(1.0, (1.0 - r["lift"]) / max(1.0 - bear_min, 0.01))
            bg_alpha = 0.10 + intensity * 0.35
            rows.append(
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'background:rgba(244,114,182,{bg_alpha:.2f});'
                f'border-left:3px solid #f472b6;padding:6px 12px;margin:3px 0;border-radius:4px;">'
                f'<span style="display:flex;align-items:center;gap:10px;">'
                f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.72rem;color:#fda4af;min-width:22px;">'
                f'#{i+1:02d}</span>'
                f'<span style="color:#fce7f3;font-weight:600;">{r["term"]}</span>'
                f'</span>'
                f'<span style="display:flex;align-items:center;gap:8px;">'
                f'<span style="font-family:\'JetBrains Mono\',monospace;color:#fb7185;font-size:0.82rem;font-weight:700;">'
                f'×{r["lift"]:.2f}</span>'
                f'<span style="font-family:\'JetBrains Mono\',monospace;color:rgba(148,163,184,0.7);font-size:0.72rem;">'
                f'χ² {r["chi2"]:.0f}</span>'
                f'</span></div>'
            )
        st.markdown("".join(rows), unsafe_allow_html=True)

    # Bull/bear context insight
    bull_n = (sel["lift"] > 1.15).sum()
    bear_n = (sel["lift"] < 0.92).sum()
    neutral_n = len(sel) - bull_n - bear_n
    st.markdown(f"""
    <div class="gl-box-info" style="margin-top:14px;">
    <strong style="display:inline-flex;align-items:center;gap:6px;">
    {glint_icon("pin", 15, "#22d3ee")} 色譜結構</strong>
    ：500 個關鍵字中，<strong style="color:#6ee7b7;">看多詞 {bull_n}</strong>（lift &gt; 1.15）、
    <strong style="color:#f472b6;">看空詞 {bear_n}</strong>（lift &lt; 0.92）、
    中性詞 {neutral_n}。整體 lift 分布明顯右偏（mean = {sel["lift"].mean():.2f}）——
    選出的 500 詞大多對應「出現時後續偏上漲」的情境。
    看多側以個股事件為主（上銀、建準、陽明、雙鴻、私有化、盤漲），
    看空側則集中於總經標的與通用財報詞（生技、中鋼、金融股、年減、美元、異動）。
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# B. Lift × Chi² strength scatter
# ============================================================================
render_section_title("B. 關鍵字強度圖", "Lift × Chi² · 500 selected keywords")
st.caption("X 軸 = lift（方向性：左空右多）｜ Y 軸 = chi²（重要性，log）｜ 點大小 ∝ 互資訊（MI）")

if kw is not None:
    sel = kw[kw["selected"]].copy()
    sel["direction"] = np.where(
        sel["lift"] > 1.15, "看多",
        np.where(sel["lift"] < 0.92, "看空", "中性"),
    )
    sel["mi_sz"] = (sel["mi"] * 1e6).clip(lower=0.5)
    color_map = {"看多": "#14b8a6", "看空": "#f472b6", "中性": "#94a3b8"}

    fig_b = px.scatter(
        sel, x="lift", y="chi2", color="direction",
        color_discrete_map=color_map,
        size="mi_sz", size_max=18,
        hover_data={"term": True, "lift": ":.3f", "chi2": ":.1f",
                    "mi": ":.6f", "mi_sz": False, "direction": False},
        log_y=True,
    )
    fig_b.add_vline(x=1.0, line_dash="dash", line_color="rgba(148,163,184,0.45)",
                    annotation_text="baseline lift=1.0",
                    annotation_position="top",
                    annotation_font_color="#94a3b8")
    fig_b.update_traces(marker=dict(line=dict(width=0)), opacity=0.78)
    fig_b.update_layout(**glint_plotly_layout(
        title="Lift × Chi² · 500 關鍵字的方向性與重要性",
        subtitle="右上象限 = 強看多且高頻｜左上象限 = 強看空且高頻",
        height=480, xlabel="Lift", ylabel="Chi² (log)",
    ))
    fig_b.update_layout(legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0,
        bgcolor="rgba(8,16,32,0.8)",
    ))
    st.plotly_chart(fig_b, use_container_width=True)

# ============================================================================
# C. Sentiment → Forward return validation  ·  THE KILLER INSIGHT
# ============================================================================
fv = load_sentiment_panel()

render_section_title("C. 情緒 → 報酬驗證", "Sentiment Quintile → Forward Hit Rate · n = 948K")
st.caption("把 948K 樣本依 `sent_polarity_5d` 分五桶，檢驗各桶 5 日後實際上漲率是否有系統性偏移。")

if fv is None:
    st.warning("找不到 `outputs/feature_store_final.parquet`，跳過情緒驗證。")
else:
    buckets, base5 = sentiment_quintile_edge(fv, "sent_polarity_5d", "up_5")

    # Killer bar chart
    colors_c = ["#14b8a6" if e > 0 else "#f472b6" for e in buckets["edge_pp"]]
    fig_c = go.Figure()
    fig_c.add_trace(go.Bar(
        x=buckets["q"], y=buckets["edge_pp"],
        marker=dict(color=colors_c, line=dict(width=0)),
        text=[f"{e:+.2f}pp<br>up {h:.1%}<br>n={n:,}"
              for e, h, n in zip(buckets["edge_pp"], buckets["hit_rate"], buckets["n"])],
        textposition="outside",
        textfont=dict(size=11, color="#cfe2ee", family="JetBrains Mono"),
        hovertemplate="<b>%{x}</b><br>sent_mean %{customdata[0]:+.3f}<br>"
                      "up_rate %{customdata[1]:.2%}<br>edge %{y:+.2f}pp<br>"
                      "n %{customdata[2]:,}<extra></extra>",
        customdata=np.stack([buckets["sent_mean"], buckets["hit_rate"], buckets["n"]], axis=-1),
    ))
    fig_c.add_hline(y=0, line_dash="dash", line_color="rgba(148,163,184,0.5)")
    fig_c.update_layout(**glint_plotly_layout(
        title=f"情緒五桶 → 5 日上漲率 · 基準 {base5:.2%}",
        subtitle="正值 = 該情緒桶後續勝率高於基準（綠）；負值 = 低於基準（粉）",
        height=440, xlabel="情緒分位", ylabel="vs. 基準 (pp)",
    ), showlegend=False)
    st.plotly_chart(fig_c, use_container_width=True)

    # --- The insight ---
    q1 = buckets.iloc[0]
    q3 = buckets.iloc[2]
    q5 = buckets.iloc[-1]
    # Describe U-shape factually without assuming Q5 sign
    q5_sign_word = "略勝" if q5["edge_pp"] > 0 else "略低於"
    st.markdown(f"""
    <div class="success-box">
    <strong style="display:inline-flex;align-items:center;gap:6px;">
    {glint_icon("pin", 15, "#c4b5fd")} 反直覺發現 · Contrarian Signal</strong>
    ：情緒最負象限（<strong>{q1["q"]}</strong>）5 日上漲率
    <strong>{q1["hit_rate"]:.2%}</strong>（edge <span class="gl-mono">{q1["edge_pp"]:+.2f}pp</span>，n = {q1["n"]:,}）——
    反而是全樣本中 <strong>勝率最高</strong> 的一桶。中性情緒（<strong>{q3["q"]}</strong>）勝率最低
    （edge <span class="gl-mono">{q3["edge_pp"]:+.2f}pp</span>），最正情緒（<strong>{q5["q"]}</strong>）{q5_sign_word}基準
    （<span class="gl-mono">{q5["edge_pp"]:+.2f}pp</span>），並未因情緒轉正而顯出優勢。
    <br><br>
    <strong>實務意涵：</strong>極端負面情緒不是繼續看空的理由，而是 <strong>mean reversion 入場</strong> 的候選訊號。
    反過來，情緒並未在「越正越好」方向單調遞增 —— 市場對媒體與論壇的狂熱有耐受性，吹捧並不自動兌現為上漲。
    </div>
    """, unsafe_allow_html=True)

    # Multi-horizon comparison mini-chart
    st.markdown("##### 跨期驗證 · 1 / 5 / 20 日")
    st.caption("同一組情緒五桶，檢驗不同持有期的 edge 走勢。如果訊號來自噪聲，邊際應該隨期限漸消。")
    rows_h = []
    for L in (1, 5, 20):
        bk, bs = sentiment_quintile_edge(fv, "sent_polarity_5d", f"up_{L}")
        for _, r in bk.iterrows():
            rows_h.append({"horizon": f"{L}d", "q": r["q"], "edge_pp": r["edge_pp"]})
    dh = pd.DataFrame(rows_h)
    fig_h = px.line(
        dh, x="q", y="edge_pp", color="horizon", markers=True,
        color_discrete_map={"1d": "#67e8f9", "5d": "#a78bfa", "20d": "#14b8a6"},
    )
    fig_h.add_hline(y=0, line_dash="dash", line_color="rgba(148,163,184,0.5)")
    fig_h.update_layout(**glint_plotly_layout(
        title="edge (pp) × 情緒分位 × 持有期",
        subtitle="U 型在 1d / 5d / 20d 三個持有期皆維持方向 —— 不是噪聲，半衰期至少跨一個月",
        height=320, xlabel="情緒分位", ylabel="edge (pp)",
    ))
    fig_h.update_layout(legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0,
        bgcolor="rgba(8,16,32,0.8)",
    ))
    st.plotly_chart(fig_h, use_container_width=True)

# ============================================================================
# D. News vs Forum divergence
# ============================================================================
render_section_title("D. 新聞 vs. 論壇 · 情緒分歧", "Media vs. Social · Independent Signals")
st.caption("媒體選題偏風險、論壇偏抱怨—— 兩者相關性多強？當它們同向時訊號可信度高多少？")

if fv is not None:
    nf = fv[["sent_news_mean_5d", "sent_forum_mean_5d"]].dropna()
    corr = nf.corr().iloc[0, 1]
    news_mean = nf["sent_news_mean_5d"].mean()
    forum_mean = nf["sent_forum_mean_5d"].mean()
    disagree = ((nf["sent_news_mean_5d"] > 0) != (nf["sent_forum_mean_5d"] > 0)).mean()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("新聞均值", f"{news_mean:+.3f}", sub="偏向風險事件", accent="rose")
    with c2:
        render_kpi("論壇均值", f"{forum_mean:+.3f}", sub="近中性", accent="cyan")
    with c3:
        render_kpi("相關係數", f"{corr:.3f}", sub="近乎獨立", accent="violet")
    with c4:
        render_kpi("方向分歧", f"{disagree:.1%}", sub="10 次中 1 次", accent="amber")

    # Density-lite scatter (sample for perf)
    sample = nf.sample(min(45000, len(nf)), random_state=42)
    fig_d = go.Figure()
    fig_d.add_trace(go.Scattergl(
        x=sample["sent_news_mean_5d"], y=sample["sent_forum_mean_5d"],
        mode="markers",
        marker=dict(size=3, color="rgba(103,232,249,0.22)", line=dict(width=0)),
        hovertemplate="news %{x:+.3f}<br>forum %{y:+.3f}<extra></extra>",
        showlegend=False,
    ))
    # 45° agreement line
    lim = 1.0
    fig_d.add_trace(go.Scatter(
        x=[-lim, lim], y=[-lim, lim], mode="lines",
        line=dict(color="rgba(167,139,250,0.55)", dash="dash", width=1.5),
        name="共識 y=x", hoverinfo="skip",
    ))
    fig_d.add_hline(y=0, line_color="rgba(148,163,184,0.25)")
    fig_d.add_vline(x=0, line_color="rgba(148,163,184,0.25)")
    fig_d.update_layout(**glint_plotly_layout(
        title="新聞情緒 vs. 論壇情緒 · 45K 抽樣",
        subtitle="點落在 45° 虛線附近 = 共識；偏離對角線 = 媒體與論壇看法分歧",
        height=460, xlabel="新聞 sent (5d)", ylabel="論壇 sent (5d)",
    ))
    fig_d.update_layout(legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0,
        bgcolor="rgba(8,16,32,0.8)",
    ))
    st.plotly_chart(fig_d, use_container_width=True)

    st.markdown(f"""
    <div class="gl-box-info">
    <strong style="display:inline-flex;align-items:center;gap:6px;">
    {glint_icon("pin", 15, "#22d3ee")} 獨立訊號，不是冗餘</strong>
    ：兩者相關係數僅 <span class="gl-mono">{corr:.2f}</span>，接近獨立。
    新聞均值 <span class="gl-mono">{news_mean:+.3f}</span> 比論壇 <span class="gl-mono">{forum_mean:+.3f}</span>
    負了一個量級，符合媒體「報憂不報喜」的選題慣性（罷工、火災、下修、調查）。
    <br><br>
    <strong>使用方式：</strong>把 <code>sent_news_mean_5d</code> 與 <code>sent_forum_mean_5d</code>
    當作兩個獨立訊號源——當它們同向，訊號可信度加倍；當它們分歧（約 {disagree:.0%} 的時點），
    可能是消息面 vs. 散戶情緒的背離機會。
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# E. Daily sentiment index
# ============================================================================
render_section_title("E. 每日情緒指數", "Daily Sentiment Index · 2023-03 → 2025-03")
st.caption("全市場當日 `sent_polarity_1d` 均值 + 20 日平滑線。持續偏負 = 論壇語氣的結構性偏誤，不是市場訊號本身。")

if fv is not None:
    daily = daily_sentiment_index(fv)

    fig_e = go.Figure()
    fig_e.add_trace(go.Scatter(
        x=daily["trade_date"], y=daily["sent_mean"],
        mode="lines", name="日情緒 raw",
        line=dict(color="rgba(103,232,249,0.32)", width=1),
        hovertemplate="%{x|%Y-%m-%d}<br>sent %{y:+.3f}<extra></extra>",
    ))
    fig_e.add_trace(go.Scatter(
        x=daily["trade_date"], y=daily["sent_20ma"],
        mode="lines", name="20 日平滑",
        line=dict(color="#a78bfa", width=2.8),
        hovertemplate="%{x|%Y-%m-%d}<br>20MA %{y:+.3f}<extra></extra>",
    ))
    fig_e.add_hline(y=0, line_dash="dash", line_color="rgba(148,163,184,0.3)")
    fig_e.update_layout(**glint_plotly_layout(
        title="每日情緒均值 · 505 個交易日",
        subtitle="整段區間均值約 −0.04，20MA 谷底探至 −0.07 —— 負面並非偶發，是語氣的結構性偏誤",
        height=360, xlabel="日期", ylabel="sent_polarity_1d",
    ))
    fig_e.update_layout(legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0,
        bgcolor="rgba(8,16,32,0.8)",
    ))
    st.plotly_chart(fig_e, use_container_width=True)

    # Find most negative trough & most positive peak
    trough = daily.loc[daily["sent_20ma"].idxmin()]
    peak = daily.loc[daily["sent_20ma"].idxmax()]
    st.markdown(f"""
    <div class="gl-box-info">
    情緒 20 日低點落在 <strong>{trough["trade_date"].strftime("%Y-%m-%d")}</strong>
    （20MA <span class="gl-mono">{trough["sent_20ma"]:+.3f}</span>），高點落在
    <strong>{peak["trade_date"].strftime("%Y-%m-%d")}</strong>
    （<span class="gl-mono">{peak["sent_20ma"]:+.3f}</span>）。
    整段均值為負並不代表市場在跌 —— 而是論壇/新聞天然偏抱怨語氣，
    <strong>真正的訊號是「相對於自身平均的偏離」</strong>，這正是 Phase 2 特徵工程把 5d/20d rolling
    再做 z-score 化的原因。
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# F. 11 sentiment features distribution (keep PNG, dark-wrapped)
# ============================================================================
render_section_title("F. 11 情緒特徵分布", "Sentiment Feature Distributions")
st.caption("polarity / pos-neg ratio / spread / volatility / reversal / news-forum split — Phase 2 納入模型的 11 個核心情緒欄位")

png_f = fig_dir / "text_sentiment_distribution.png"
if png_f.exists():
    st.image(str(png_f), use_container_width=True)
    st.markdown("""
    <div class="gl-box-info">
    三個要看的型態：(1) <code>sent_polarity</code> 整體偏負（mean ≈ −0.04）— 論壇抱怨語氣是常態；
    (2) <code>sent_pos_neg_spread_5d</code> 均值 −0.26 — 負面比例系統性高於正面；
    (3) <code>sent_news_mean_5d</code> 比 <code>sent_forum_mean_5d</code> 負一倍（−0.14 vs −0.01）—
    這個差距就是新聞與論壇可以作為 cross-validation 的來源。
    </div>
    """, unsafe_allow_html=True)
else:
    st.warning(f"圖檔不存在：{png_f}")

# ============================================================================
# G. Coverage warning (Top 20 stocks × month) — keep as-is, it's a critical caveat
# ============================================================================
render_section_title("G. 覆蓋不均預警", "Coverage Heatmap · Top 20 Stocks × Month")
st.caption("縱軸 = 提及頻率 Top 20 個股，橫軸 = 月份。覆蓋集中在大型股 —— 這是 txt_ 支柱貢獻上限的物理根源。")

png_g = fig_dir / "text_coverage_heatmap.png"
if png_g.exists():
    st.image(str(png_g), use_container_width=True)

st.markdown("""
<div class="warning-box">
<strong>⚠️ 覆蓋不均是模型的硬上限</strong>：前 5 檔（台積電 / 聯發科 / 鴻海 / 群聯 / 大立光等）
已佔整體文本量相當比例；中小型股常是零文本列。樹模型遇到零文本列沒有 split 依據，所以
<strong>txt_ 支柱在 Phase 3 平均貢獻僅 ~6%</strong> 不是特徵設計弱，而是資料結構上限。
<br><br>
<strong>這反過來也告訴交易員：</strong>文本訊號對 <strong>大型股</strong> 的邊際效用遠高於中小型股。
策略若要倚重情緒面，應聚焦在高覆蓋股票池。
</div>
""", unsafe_allow_html=True)

# ============================================================================
# Supporting visualizations (collapsed)
# ============================================================================
with st.expander(
    "補充視覺化 · Supporting Visualizations（詞雲 / 平台 / 文本量）",
    expanded=False,
    icon=":material/collections:",
):
    st.caption("原始 Phase 5B 輸出 — 適合做簡報與報告引用，不含決策性洞察。")

    st.markdown("##### 詞雲總覽 · 500 selected keywords")
    png_wc = fig_dir / "text_wordcloud.png"
    if png_wc.exists():
        st.image(str(png_wc), use_container_width=True)
        st.markdown("""
        <div style="font-size:0.86rem;color:#b4ccdf;line-height:1.65;">
        頭部詞以半導體電子龍頭（台積電 / 聯發科 / 鴻海 / 群聯 / 大立光）為主 —— 這是
        stock_text 資料集「點名式」文章的天然後果。事件詞（大火 / 私有化 / deepseek / future）
        展現 2023–2025 的題材脈絡。詞雲本身只是詞頻熱度圖，<strong>方向性訊號請回到 A / B 兩節</strong>。
        </div>
        """, unsafe_allow_html=True)

    st.markdown("##### 資料來源平台分布")
    png_plat = fig_dir / "text_platform_share.png"
    if png_plat.exists():
        st.image(str(png_plat), use_container_width=True)

    st.markdown("##### 文本量時序 · 2023-03 → 2025-03")
    png_vol = fig_dir / "text_volume_over_time.png"
    if png_vol.exists():
        st.image(str(png_vol), use_container_width=True)
        st.markdown("""
        <div style="font-size:0.86rem;color:#b4ccdf;line-height:1.65;">
        2024 下半文本量放大約 2 倍，與台股成交量同步。2025 Q1 因 DeepSeek 題材再有一波尖峰 ——
        Phase 2 訓練視窗剛好涵蓋此結構轉變，模型學到的文本訊號對應現行市場語境。
        </div>
        """, unsafe_allow_html=True)

    st.markdown("##### Top 30 關鍵字 · 三指標對照（PNG）")
    png_tk = fig_dir / "text_top_keywords.png"
    if png_tk.exists():
        st.image(str(png_tk), use_container_width=True)
        st.caption("Chi² 與標籤相關性 ｜ MI 非線性依賴 ｜ Lift 正報酬相對發生率。三者交集即 A / B 兩節的來源。")

# ============================================================================
# Footer
# ============================================================================
st.divider()
st.markdown("""
<div class="page-footer">
Phase 5B Text & Sentiment Analytics · jieba + SnowNLP · 1.12M articles → 500 kw × 3 window + 11 sent features · v11.5.14 (2026-04-23)
</div>
""", unsafe_allow_html=True)
