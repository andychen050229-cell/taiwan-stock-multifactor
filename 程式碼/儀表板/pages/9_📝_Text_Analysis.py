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
figures_dir = _utils.figures_dir

inject_custom_css()

# ===== Banner =====
st.markdown("""
<div style="background:#e0f2fe; border-left:4px solid #0284c7; border-radius:0 8px 8px 0; padding:12px 16px; font-size:0.85rem; color:#075985; margin-bottom:20px;">
📝 <strong>Phase 5B 文本分析儀表板</strong>：1,125,134 篇文章 → 500 selected keywords + 11 sentiment features → 1,532 txt_/sent_ 特徵入 feature_store
</div>
""", unsafe_allow_html=True)

st.title("📝 文本分析 — Text Analysis")
st.caption("Phase 5B Stage 2.1–2.4 + 2.5 視覺化｜jieba 斷詞 + Chi²/MI/Lift 關鍵字三重篩選 + SnowNLP 情緒打分")

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
st.header("A. 關鍵字詞雲 — Wordcloud")
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
st.header("B. Top 30 關鍵字 — 三指標對照")
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

# ===== C. Sentiment distribution =====
st.header("C. 情緒特徵分布 — Sentiment Features")
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
st.header("D. 資料來源平台 — Platform Share")
st.caption("五個來源：Dcard / Mobile01 / PTT / Yahoo 新聞 / Yahoo 股市")
png = fig_dir / "text_platform_share.png"
if png.exists():
    st.image(str(png), use_container_width=True)

# ===== E. Volume over time =====
st.header("E. 文本量時序 — Volume Over Time")
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
st.header("F. Top 20 個股 × 月份 — Coverage Heatmap")
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
