"""Text Analysis — 文本分析儀表板（Phase 5B 產物）

展示：
  A. 詞雲（500 selected keywords）
  B. Top 30 關鍵字（Chi² / MI / Lift 三指標）
  C. 情緒特徵分布（sent_* 9 個核心欄位）
  D. 五平台文章比例（Dcard / Mobile01 / PTT / Yahoo 新聞 / Yahoo 股市）
  E. 文本量時序（2023-03 ~ 2025-03）
  F. Top 20 個股 × 月份 mention 覆蓋熱圖
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
figures_dir = _utils.figures_dir
render_terminal_hero = _utils.render_terminal_hero
render_section_title = _utils.render_section_title
PAGE_EYEBROWS = _utils.PAGE_EYEBROWS
PAGE_TITLES = _utils.PAGE_TITLES
PAGE_BRIEFINGS = _utils.PAGE_BRIEFINGS
render_trust_strip = _utils.render_trust_strip
render_page_footer = _utils.render_page_footer

inject_custom_css()

# ---- Top-bar (sticky breadcrumb + model chips + clock) ----
render_topbar(
    crumb_left="多因子股票分析系統",
    crumb_current="文本情緒分析",
    chips=[("jieba + SnowNLP", "pri"), ("500 keywords", "vio"), ("phase 5B", "ok")],
    show_clock=True,
)

# v11.3 § Page-9 rescue — dark terminal hero + trust strip (parity with other pages)
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

# ===== Overview KPIs =====
st.markdown("### 文本特徵概覽")
col1, col2, col3, col4 = st.columns(4)
col1.metric("原始文章數", "1,125,134", "PTT / Dcard / Mobile01 / Yahoo")
col2.metric("Selected 關鍵字", "500", "from 9,655 候選")
col3.metric("txt_ 特徵", "1,521", "500 kw × 3 window + 21 volume")
col4.metric("sent_ 特徵", "11", "polarity / ratio / spread / vol / reversal")

st.divider()

# ===== A. Wordcloud =====
render_section_title("A. 關鍵字詞雲", "Wordcloud · Top 500 keywords")
st.caption("500 個 selected keywords，字體大小依 Chi²+MI+Lift 三重排序的 rank_combined 倒數加權")
png = fig_dir / "text_wordcloud.png"
if png.exists():
    st.image(str(png), use_container_width=True)
    st.markdown("""
    <div class="insight-box">
    <strong>觀察</strong>：頭部詞以<strong>半導體與電子龍頭個股名稱</strong>為主（台積電、聯發科、鴻海、群聯、大立光等），
    反映 2023-2025 的主導題材。個股名稱主導是意料中事，因為 stock_text 原始資料以<strong>點名式新聞/論壇</strong>為主；
    事件詞「大火 / 私有化 / deepseek / future」等呈現可辨識的時事脈絡。
    </div>
    """, unsafe_allow_html=True)
else:
    st.warning(f"圖檔不存在：{png}，請先執行 `python 程式碼/執行Phase5B_文本視覺化.py`")

# ===== B. Top 30 keywords (3 metrics) =====
render_section_title("B. Top 30 關鍵字", "Chi² / MI / Lift · 三指標對照")
st.caption("Chi² 捕捉與標籤的相關性 ｜ Mutual Information 捕捉非線性依賴 ｜ Lift 捕捉正標籤相對發生率")
png = fig_dir / "text_top_keywords.png"
if png.exists():
    st.image(str(png), use_container_width=True)

kw_path = Path(__file__).resolve().parent.parent.parent.parent / "outputs" / "text_keywords.parquet"
if kw_path.exists():
    kw = pd.read_parquet(kw_path)
    sel = kw[kw["selected"]].copy()
    top30 = sel.nsmallest(30, "rank_combined")[["term", "chi2", "mi", "lift", "rank_combined"]]
    top30["chi2"] = top30["chi2"].round(2)
    top30["mi"] = top30["mi"].round(6)
    top30["lift"] = top30["lift"].round(3)
    top30["rank_combined"] = top30["rank_combined"].round(2)
    with st.expander("📋 Top 30 by combined rank — 詳細數值", expanded=False):
        st.dataframe(top30, use_container_width=True, hide_index=True)

    # ---- Design-ported interactive heat cloud (size ∝ Chi², color ∝ lift) ----
    st.markdown("### 🔥 關鍵字熱度雲 — Interactive Heat Cloud")
    st.caption("字體大小 ∝ Chi² 指標；顏色越暖代表 Lift 越高（對正報酬樣本的相對發生率越強）")

    # Normalize sizes (0.85rem–2.2rem) and pick tint by lift quantile
    max_chi2 = max(top30["chi2"].max(), 1.0)
    min_chi2 = max(top30["chi2"].min(), 0.01)
    lift_q66 = top30["lift"].quantile(0.66)
    lift_q33 = top30["lift"].quantile(0.33)
    spans = []
    for _, r in top30.iterrows():
        # Size 0.85rem – 2.2rem scaled logarithmically against chi2
        import math
        t = (math.log(r["chi2"] + 1) - math.log(min_chi2 + 1)) / (math.log(max_chi2 + 1) - math.log(min_chi2 + 1) + 1e-9)
        size = 0.85 + t * 1.35
        # Color by lift (rose for low, amber for mid, emerald for high)
        if r["lift"] >= lift_q66:
            color = "var(--gl-emerald)"
            bg = "rgba(16,185,129,0.08)"
        elif r["lift"] >= lift_q33:
            color = "var(--gl-amber)"
            bg = "rgba(245,158,11,0.08)"
        else:
            color = "var(--gl-rose)"
            bg = "rgba(244,63,94,0.07)"
        spans.append(
            f'<span style="display:inline-block;padding:4px 12px;margin:4px;'
            f'background:{bg};border-radius:999px;'
            f'font-size:{size:.2f}rem;font-weight:{600 + int(t*2)*100};'
            f'color:{color};line-height:1.2;" '
            f'title="Chi² {r["chi2"]:.2f} · Lift {r["lift"]:.3f}">{r["term"]}</span>'
        )
    st.markdown(
        '<div class="gl-panel" style="padding:18px 22px;display:flex;flex-wrap:wrap;'
        'align-items:center;justify-content:center;min-height:180px;">'
        + "".join(spans) + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="display:flex;gap:14px;font-size:0.82rem;color:var(--gl-text-3);margin-top:8px;">'
        '<span><span class="gl-dot" style="background:var(--gl-emerald);display:inline-block;'
        'width:8px;height:8px;border-radius:50%;margin-right:6px;"></span>Lift ≥ Q66（高正面性）</span>'
        '<span><span class="gl-dot" style="background:var(--gl-amber);display:inline-block;'
        'width:8px;height:8px;border-radius:50%;margin-right:6px;"></span>Q33 ≤ Lift &lt; Q66（中性）</span>'
        '<span><span class="gl-dot" style="background:var(--gl-rose);display:inline-block;'
        'width:8px;height:8px;border-radius:50%;margin-right:6px;"></span>Lift &lt; Q33（低正面性）</span>'
        '</div>',
        unsafe_allow_html=True,
    )

# ===== C. Sentiment distribution =====
render_section_title("C. 情緒特徵分布", "Sentiment Features · 9 core")
st.caption("SnowNLP 極性（-1 ~ +1）+ 辭典輔助 ｜ 5d/20d rolling 窗 ｜ 區分新聞與論壇來源")
png = fig_dir / "text_sentiment_distribution.png"
if png.exists():
    st.image(str(png), use_container_width=True)
    st.markdown("""
    <div class="insight-box">
    <strong>觀察</strong>：1. <code>sent_polarity</code> 整體偏負（mean ≈ -0.04），
    反映論壇發文「抱怨/質疑」語氣佔優。2. <code>sent_pos_neg_spread_5d</code> 平均 -0.26，
    負面比例普遍高於正面，符合財經論壇的情緒偏誤。
    3. <code>sent_news_mean_5d</code>（新聞）與 <code>sent_forum_mean_5d</code>（論壇）
    分布明顯不同：新聞更負（-0.14 vs -0.01），反映媒體選題偏向風險事件。
    </div>
    """, unsafe_allow_html=True)

# ===== D. Platform share =====
render_section_title("D. 資料來源平台", "Platform Share · PTT / Dcard / Mobile01 / Yahoo")
st.caption("五個來源：Dcard / Mobile01 / PTT / Yahoo 新聞 / Yahoo 股市")
png = fig_dir / "text_platform_share.png"
if png.exists():
    st.image(str(png), use_container_width=True)

# ===== E. Volume over time =====
render_section_title("E. 文本量時序", "Volume Over Time · 2023-03 ~ 2025-03")
st.caption("每日文章量（article × stock mention）+ 7 日滑動平均")
png = fig_dir / "text_volume_over_time.png"
if png.exists():
    st.image(str(png), use_container_width=True)
    st.markdown("""
    <div class="insight-box">
    <strong>觀察</strong>：文本量在 2024 下半起明顯<strong>放大約 2 倍</strong>，
    與台股成交量、關注度上升同步。2025 年初因 DeepSeek 題材與 AI 供應鏈重新洗牌，
    文本量又有一波尖峰。<strong>Phase 2 訓練視窗剛好涵蓋此結構轉變</strong>，
    模型學到的文本訊號較能對應現行市場語境。
    </div>
    """, unsafe_allow_html=True)

# ===== F. Coverage heatmap =====
render_section_title("F. Top 20 個股 × 月份", "Coverage Heatmap")
st.caption("縱軸為被提及最頻繁的前 20 檔，橫軸為月份，顏色深淺代表月度提及次數")
png = fig_dir / "text_coverage_heatmap.png"
if png.exists():
    st.image(str(png), use_container_width=True)
    st.markdown("""
    <div class="warning-box">
    ⚠️ <strong>覆蓋不均</strong>：Top 5 提及量已佔整體的相當比例（台積電/聯發科/鴻海等），
    中小型股文本覆蓋稀疏。這解釋了為何 <strong>txt_ 支柱在 Phase 3 的平均貢獻僅 ~6%</strong>——
    樹模型在無文本的列無法 split，實際上對大型股的邊際效用較高。
    Phase 5B LOPO 驗證（txt_/sent_ 支柱移除前後 AUC/IC 對照）已列為後續工作。
    </div>
    """, unsafe_allow_html=True)

# ===== Footer =====
st.divider()
st.markdown("""
<div class="page-footer">
Phase 5B Text & Sentiment Analysis · jieba + SnowNLP · 1.12M articles → 500 kw × 3 window + 11 sent features · 2026-04-20
</div>
""", unsafe_allow_html=True)
