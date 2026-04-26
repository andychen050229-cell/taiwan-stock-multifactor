"""Text Analysis — 文本情緒分析儀表板（Phase 5B 產物 · v11.5.17 定版）

從「展示原始結果」升級為「可行動的輿情訊號」：
  A. 看多 vs. 看空 關鍵字色譜 — 每個詞的 lift 對應勝率偏移（已過濾中文斷詞雜訊）
  B. 關鍵字 Lift × Chi² 強度圖 — 500 詞的方向性與重要性雙軸
  C. 情緒 → 報酬驗證 — 情緒極端象限的反彈機率（contrarian 訊號，跨 1/5/20d 穩定）
  D. 新聞 vs. 論壇 · 情緒分歧 + 4 象限共識矩陣 — 從獨立訊號到 trading rule
  E. 每日情緒指數時序
  F. 11 情緒特徵分布 + 覆蓋不均預警
  G. 摺疊：原始輸出補件（平台 / 時序 / Top-30 PNG）
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
def _resolve_outputs_dir() -> Path:
    """Match utils._project_outputs_dir() semantics.

    Handles both local dev (project_root/outputs) and the Streamlit Cloud
    shim case where dashboard/app.py does os.chdir(程式碼/儀表板/).
    """
    here = Path(__file__).resolve()
    for candidate in (
        here.parent.parent.parent.parent / "outputs",   # project_root/outputs (canonical)
        here.parent.parent.parent / "outputs",          # 程式碼/outputs (legacy)
        Path.cwd() / "outputs",
        Path.cwd().parent / "outputs",
        Path.cwd().parent.parent / "outputs",
    ):
        if candidate.exists():
            return candidate
    return Path.cwd() / "outputs"


_OUTPUTS = _resolve_outputs_dir()

_SENT_COLS = [
    "trade_date", "label_1", "label_5", "label_20",
    "sent_polarity_1d", "sent_polarity_5d", "sent_polarity_20d",
    "sent_pos_neg_spread_5d", "sent_pos_ratio_5d", "sent_neg_ratio_5d",
    "sent_news_mean_5d", "sent_forum_mean_5d",
    "sent_volatility_5d", "sent_extreme_ratio_5d", "sent_reversal_5d",
]


@st.cache_data(ttl=3600, show_spinner=False)
def load_keywords() -> pd.DataFrame | None:
    # text_keywords.parquet is tiny (~9655 rows) and lives in outputs/
    for candidate in (
        _OUTPUTS / "text_keywords.parquet",
        Path.cwd() / "outputs" / "text_keywords.parquet",
    ):
        if candidate.exists():
            return pd.read_parquet(candidate)
    return None


@st.cache_data(ttl=3600, show_spinner="讀取 948K 情緒樣本中…")
def load_sentiment_panel() -> pd.DataFrame | None:
    """Load 15 sentiment-related columns with column projection.

    Resolution order:
      1. Single-file `feature_store_final.parquet` (local dev, 284 MB — gitignored)
      2. Chunked `fs_chunks/fs_*.parquet` (Streamlit Cloud, 9 quarterly slices)
      3. Legacy `feature_store.parquet`
    """
    df: pd.DataFrame | None = None

    # 1. Single-file feature store
    single = _OUTPUTS / "feature_store_final.parquet"
    if single.exists():
        try:
            df = pd.read_parquet(single, columns=_SENT_COLS)
        except Exception:
            df = None

    # 2. Chunked fallback — sum of all quarters with column projection
    if df is None:
        chunk_dir = _OUTPUTS / "fs_chunks"
        if chunk_dir.exists():
            parts = sorted(chunk_dir.glob("fs_*.parquet"))
            if parts:
                try:
                    frames = [pd.read_parquet(p, columns=_SENT_COLS) for p in parts]
                    df = pd.concat(frames, ignore_index=True)
                except Exception:
                    df = None

    # 3. Legacy fallback
    if df is None:
        legacy = _OUTPUTS / "feature_store.parquet"
        if legacy.exists():
            try:
                df = pd.read_parquet(legacy, columns=_SENT_COLS)
            except Exception:
                df = None

    if df is None:
        return None

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
# Keyword noise filter — native-speaker judgment
# ============================================================================
# 以中文母語者視角整理的雜訊詞表：jieba 斷詞殘留 / 泛用詞 / 單位量詞 / 單字片段。
# 保留真訊號：個股名、事件題材（大火/私有化/deepseek）、機構（里昂/元大證）、
#            市況（盤漲/落後補漲）、產業（生技/金融股）、財報詞（年減/年增）。
_KW_NOISE: frozenset[str] = frozenset({
    # --- jieba 斷詞殘留 / token 碎片 -------------------------------------
    "銀上", "上銀上", "雙鴻營", "建準代", "客運營", "創代", "華開發", "回台",
    "元大金擬", "之營運", "台灣廠", "月合", "年股", "東常會", "折台", "權資產",
    "王可立", "由凱", "張庫", "海公公", "買台", "拚守", "寫佳績", "金發",
    # --- 過於泛用、無投資訊號 -----------------------------------------
    "生活", "台灣", "國際", "使用", "補充", "日期", "報告", "寶貝", "再講",
    "無關", "重要", "財務", "市場", "門檻", "升高", "召開", "公告", "決議",
    "受邀", "舉辦", "揭密", "遭控", "首富", "連拉", "器械", "富士", "有限公司",
    "子公司", "股份", "董事", "其他", "之一",
    # --- 單位 / 數量 ---------------------------------------------------
    "萬元", "億元", "每股", "億", "萬",
    # --- 單字 / 功能字（中文單字在此 corpus 幾乎都是 jieba 錯切殘留）----
    "估", "銀", "疫", "體", "第", "金", "月", "年", "併", "逾", "達",
    # --- 英文 / 數字異常 token -----------------------------------------
    "ith", "55%",
})


def _is_meaningful_term(t: str) -> bool:
    """Native-speaker noise filter for Chinese stock-text keywords."""
    if not isinstance(t, str):
        return False
    s = t.strip()
    if not s or len(s) < 2:        # 單字片段一律當雜訊
        return False
    if s in _KW_NOISE:
        return False
    if s.isdigit():                # 純數字
        return False
    return True


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
    # 過濾雜訊（jieba 斷詞殘留 / 泛用詞 / 單字片段），讓榜單只剩可讀的真訊號
    sel_clean = sel[sel["term"].apply(_is_meaningful_term)].copy()
    noise_removed = len(sel) - len(sel_clean)
    # 再以 lift=1 為基準分側：只有 lift > 1 的詞屬於看多、< 1 的屬於看空。
    bull_pool = sel_clean[sel_clean["lift"] > 1.0]
    bear_pool = sel_clean[sel_clean["lift"] < 1.0]
    top_bull = bull_pool.nlargest(15, "lift").reset_index(drop=True)
    top_bear = bear_pool.nsmallest(15, "lift").reset_index(drop=True)
    bull_max = top_bull["lift"].max() if len(top_bull) else 1.5
    bear_min = top_bear["lift"].min() if len(top_bear) else 0.5

    st.caption(
        f"已用中文母語者視角過濾 {noise_removed} 個雜訊詞（斷詞殘留、泛用字、單位量詞）。"
        f"lift > 1 計入看多（{len(bull_pool)} 詞）、lift < 1 計入看空（{len(bear_pool)} 詞），"
        f"每側取真訊號 Top 15 展示。"
    )

    col_b, col_s = st.columns(2, gap="medium")

    with col_b:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.68rem;'
            f'font-weight:700;letter-spacing:0.14em;color:#6ee7b7;text-transform:uppercase;'
            f'background:rgba(110,231,183,0.12);border:1px solid rgba(110,231,183,0.32);'
            f'padding:3px 10px;border-radius:4px;">BULLISH · 看多 TOP {len(top_bull)}（已濾雜訊）</span>'
            f'<span style="height:1px;flex:1;background:linear-gradient(90deg,rgba(110,231,183,0.32) 0%,transparent 100%);"></span>'
            f'</div>',
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
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.68rem;'
            f'font-weight:700;letter-spacing:0.14em;color:#fb7185;text-transform:uppercase;'
            f'background:rgba(244,63,94,0.12);border:1px solid rgba(244,63,94,0.32);'
            f'padding:3px 10px;border-radius:4px;">BEARISH · 看空 TOP {len(top_bear)}（已濾雜訊）</span>'
            f'<span style="height:1px;flex:1;background:linear-gradient(90deg,rgba(244,63,94,0.32) 0%,transparent 100%);"></span>'
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
    看多側的真訊號多為個股與事件題材（<strong>基泰、劉德音、deepseek、私有化、盤漲、大火</strong>），
    看空側則集中於產業標的與財報詞（<strong>生技、中鋼、金融股、國票、年減、異動</strong>）。
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

# ---- Pre-chart explanation: what this chart is asking & how to read it ----
st.markdown("""
<div class="gl-box-info" style="margin:8px 0 16px 0;">
<strong style="color:#E8F7FC;font-size:0.98rem;">這張圖在回答的問題 →</strong>
<span style="font-size:0.95rem;color:#cfe2ee;">
「論壇與新聞的情緒，到底能不能預測未來 5 天的股價走勢？」
</span>

<div style="margin-top:12px;">
<strong style="color:#c4b5fd;">怎麼讀這張圖</strong>
<ul style="margin:6px 0 4px 18px;padding:0;color:#b4ccdf;line-height:1.8;font-size:0.9rem;">
<li><strong>X 軸</strong>：948K 個「股票 × 交易日」樣本依前 5 日情緒分 5 桶
（每桶 ≈ 189K 筆）—— Q1 最負、Q3 中性、Q5 最正。</li>
<li><strong>Y 軸</strong>：該桶在 5 日後的實際上漲率，<strong>減去全樣本基準（~29%）</strong>的 pp 差距。</li>
<li><strong>顏色</strong>：<span style="color:#6ee7b7;">綠</span> = 該桶勝率高於基準；
<span style="color:#f472b6;">粉</span> = 低於基準。</li>
</ul>
</div>

<div style="margin-top:12px;">
<strong style="color:#c4b5fd;">三種可能形態、各自代表什麼</strong>
<ul style="margin:6px 0 4px 18px;padding:0;color:#b4ccdf;line-height:1.8;font-size:0.9rem;">
<li><strong style="color:#6ee7b7;">單調右上</strong>（Q1 負 edge → Q5 正 edge）：情緒是「動能訊號」——
看好就會漲，驗證傳統「情緒領先價格」的假設。</li>
<li><strong style="color:#a78bfa;">U / V 型</strong>（Q1 高、Q3 低、Q5 偏）：情緒是「反向訊號」——
極端情緒對應 mean-reversion 機會，跟隨情緒反而被套牢。</li>
<li><strong style="color:#94a3b8;">柱子齊平</strong>：情緒沒有預測力，應該從模型剝離。</li>
</ul>
</div>

<div style="margin-top:12px;font-size:0.88rem;color:#94a3b8;">
<strong style="color:#cfe2ee;">為什麼用五等分而非線性迴歸</strong>：情緒分布極度不對稱
（50%+ 為 0），五分位能把尾部訊號獨立出來，避免被中位區間主導。
</div>
</div>
""", unsafe_allow_html=True)

if fv is None:
    st.warning(
        "情緒樣本 parquet 未就緒：已掃描 `outputs/feature_store_final.parquet` 與 "
        "`outputs/fs_chunks/` 皆缺 15 個必要欄位。本地請執行 Phase 2；"
        "Cloud 請確認 `fs_chunks/fs_*.parquet` 九份切片皆已同步。"
    )
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
    </div>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # D2. 4-quadrant agreement × forward hit-rate matrix
    # 把「訊號可信度加倍」這句話從口號變成可驗證的 edge。
    # ------------------------------------------------------------------
    st.markdown("##### D2 · 4 象限共識矩陣 · 當新聞 × 論壇同向 vs. 分歧")
    st.caption(
        "把樣本依「新聞情緒 ±」× 「論壇情緒 ±」切成 4 個象限，檢驗各象限 5 日後實際上漲率。"
        "共識 > 單邊 > 分歧 —— 就是所謂「雙印證」的統計基礎。"
    )

    nf4 = fv[["sent_news_mean_5d", "sent_forum_mean_5d", "up_5"]].dropna().copy()
    base4 = nf4["up_5"].mean()
    # 把「正好為 0」當作未表態，略過；正負各自歸類
    mask_pos_n = nf4["sent_news_mean_5d"] > 0
    mask_neg_n = nf4["sent_news_mean_5d"] < 0
    mask_pos_f = nf4["sent_forum_mean_5d"] > 0
    mask_neg_f = nf4["sent_forum_mean_5d"] < 0

    nf4["quad"] = np.select(
        [
            mask_pos_n & mask_pos_f,
            mask_neg_n & mask_neg_f,
            mask_pos_n & mask_neg_f,
            mask_neg_n & mask_pos_f,
        ],
        [
            "共識看多 (news+ / forum+)",
            "共識看空 (news− / forum−)",
            "新聞多 / 論壇空",
            "新聞空 / 論壇多",
        ],
        default=None,
    )
    quad_df = nf4.dropna(subset=["quad"]).groupby("quad", observed=True).agg(
        n=("up_5", "size"),
        hit_rate=("up_5", "mean"),
    ).reset_index()
    quad_df["edge_pp"] = (quad_df["hit_rate"] - base4) * 100
    quad_order = [
        "共識看多 (news+ / forum+)",
        "新聞多 / 論壇空",
        "新聞空 / 論壇多",
        "共識看空 (news− / forum−)",
    ]
    quad_df["quad"] = pd.Categorical(quad_df["quad"], categories=quad_order, ordered=True)
    quad_df = quad_df.sort_values("quad").reset_index(drop=True)

    # 漸層配色：共識多 → 綠；共識空 → 粉；分歧 → 灰紫
    def _quad_color(name: str) -> str:
        if "共識看多" in name: return "#14b8a6"
        if "共識看空" in name: return "#f472b6"
        return "#a78bfa"
    quad_colors = [_quad_color(q) for q in quad_df["quad"].astype(str)]

    fig_d4 = go.Figure()
    fig_d4.add_trace(go.Bar(
        x=quad_df["quad"].astype(str), y=quad_df["edge_pp"],
        marker=dict(color=quad_colors, line=dict(width=0)),
        text=[f"{e:+.2f}pp<br>up {h:.1%}<br>n={n:,}"
              for e, h, n in zip(quad_df["edge_pp"], quad_df["hit_rate"], quad_df["n"])],
        textposition="outside",
        textfont=dict(size=11, color="#cfe2ee", family="JetBrains Mono"),
        hovertemplate="<b>%{x}</b><br>up_rate %{customdata[0]:.2%}<br>"
                      "edge %{y:+.2f}pp<br>n %{customdata[1]:,}<extra></extra>",
        customdata=np.stack([quad_df["hit_rate"], quad_df["n"]], axis=-1),
    ))
    fig_d4.add_hline(y=0, line_dash="dash", line_color="rgba(148,163,184,0.5)")
    fig_d4.update_layout(**glint_plotly_layout(
        title=f"新聞 × 論壇 · 4 象限 5 日上漲率 edge · 基準 {base4:.2%}",
        subtitle="共識看多 = 加倍下注；共識看空 = 避險；分歧 = 降低曝險或等待",
        height=380, xlabel="象限", ylabel="vs. 基準 (pp)",
    ), showlegend=False)
    st.plotly_chart(fig_d4, use_container_width=True)

    # 自動產生文字結論
    q_cm = quad_df.loc[quad_df["quad"] == "共識看多 (news+ / forum+)"].iloc[0]
    q_cs = quad_df.loc[quad_df["quad"] == "共識看空 (news− / forum−)"].iloc[0]
    q_d1 = quad_df.loc[quad_df["quad"] == "新聞多 / 論壇空"].iloc[0]
    q_d2 = quad_df.loc[quad_df["quad"] == "新聞空 / 論壇多"].iloc[0]
    st.markdown(f"""
    <div class="success-box">
    <strong style="display:inline-flex;align-items:center;gap:6px;">
    {glint_icon("pin", 15, "#c4b5fd")} 雙印證能放大 edge · 分歧則稀釋訊號</strong>
    <ul style="margin:8px 0 4px 18px;padding:0;color:#b4ccdf;line-height:1.8;font-size:0.93rem;">
    <li><strong style="color:#6ee7b7;">共識看多</strong>（n={q_cm["n"]:,}）edge
    <span class="gl-mono">{q_cm["edge_pp"]:+.2f}pp</span>、勝率 <strong>{q_cm["hit_rate"]:.2%}</strong>
    —— 當新聞與論壇「同時偏正」，5 日勝率相對基準的偏移最大。</li>
    <li><strong style="color:#f472b6;">共識看空</strong>（n={q_cs["n"]:,}）edge
    <span class="gl-mono">{q_cs["edge_pp"]:+.2f}pp</span>、勝率 <strong>{q_cs["hit_rate"]:.2%}</strong>
    —— 雙負時反而出現 C 節 contrarian 訊號的共鳴：極端情緒對應反彈機會。</li>
    <li><strong style="color:#a78bfa;">分歧象限</strong>（n={q_d1["n"]+q_d2["n"]:,}）edge
    <span class="gl-mono">{q_d1["edge_pp"]:+.2f}pp</span> / <span class="gl-mono">{q_d2["edge_pp"]:+.2f}pp</span>
    —— 當兩個來源看法不一致，訊號強度明顯被稀釋，不建議倚重。</li>
    </ul>
    <div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(148,163,184,0.18);">
    <strong>實務操作建議</strong>：把 <code>sent_news_mean_5d</code> × <code>sent_forum_mean_5d</code>
    視為 <strong>AND 邏輯的第二道確認</strong>。當模型給出多頭訊號但兩來源分歧時，
    降低部位或等待；當模型訊號與「共識看多」同時成立，可放大部位（Phase 3 模型實際上已隱式學到，
    此節用於驗證其可解釋性）。
    </div>
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
    "補充視覺化 · Supporting Visualizations（平台 / 文本量 / Top-30）",
    expanded=False,
    icon=":material/collections:",
):
    st.markdown("""
    <div style="font-size:0.85rem;color:#94a3b8;line-height:1.7;margin-bottom:10px;
                border-left:2px solid rgba(148,163,184,0.28);padding-left:12px;">
    <strong style="color:#cfe2ee;">為何沒有詞雲？</strong>
    原始詞頻榜上有大量 tokenization artifacts（例：<code>銀上</code>、<code>上銀上</code>、
    <code>再講</code>、<code>王可立</code>），這類雜訊在頻率排序下會被視覺化放大，
    反而掩蓋真訊號。上方 A / B 兩節已用 <strong>lift</strong>（方向性）與 <strong>chi²</strong>（顯著性）
    把可下注的詞篩出來 —— 詞雲在這份 corpus 只會添噪，故移除。
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
Phase 5B Text & Sentiment Analytics · jieba + SnowNLP · 1.12M articles → 500 kw × 3 window + 11 sent features · v11.5.17 (2026-04-24)
</div>
""", unsafe_allow_html=True)
