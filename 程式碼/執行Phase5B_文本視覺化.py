"""Phase 5B Stage 2.5 — 文本分析視覺化（補件用）
=================================================

針對 Phase 4 審查發現「文本圖表缺件」問題，批次輸出六張核心圖：

  1. text_wordcloud.png              — 500 個 selected keyword 詞雲
  2. text_top_keywords.png           — top 30 by chi2 / mi / lift (3 subplot)
  3. text_sentiment_distribution.png — sent_polarity 1d/5d/20d + pos/neg ratio
  4. text_platform_share.png         — 5 platform article share
  5. text_volume_over_time.png       — daily article count（2023-03 ~ 2025-03）
  6. text_coverage_heatmap.png       — top 20 stocks × month mention density

所有中文字型使用 Windows 內建 mingliu.ttc（細明體），避免 SimHei 警告。

執行方式：
    python 程式碼/執行Phase5B_文本視覺化.py
"""
from __future__ import annotations

import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from wordcloud import WordCloud

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ===== Font setup =====
FONT_PATH = "C:/Windows/Fonts/mingliu.ttc"
if not Path(FONT_PATH).exists():
    FONT_PATH = "C:/Windows/Fonts/simsun.ttc"

prop = fm.FontProperties(fname=FONT_PATH)
plt.rcParams["font.sans-serif"] = [prop.get_name()]
plt.rcParams["axes.unicode_minus"] = False


def safe_print(msg: str):
    print(msg, flush=True)


# ============================================================
# 1. Wordcloud
# ============================================================
def plot_wordcloud():
    safe_print("[1/6] Generating wordcloud ...")
    kw = pd.read_parquet(PROJECT_ROOT / "outputs" / "text_keywords.parquet")
    sel = kw[kw["selected"]].copy()

    # 以 rank_combined 越小權重越大（取倒數）
    sel["weight"] = 1.0 / sel["rank_combined"].clip(lower=1)
    freq = dict(zip(sel["term"].astype(str), sel["weight"]))

    wc = WordCloud(
        font_path=FONT_PATH,
        width=1600,
        height=900,
        background_color="white",
        max_words=500,
        colormap="viridis",
        prefer_horizontal=0.9,
        margin=3,
    ).generate_from_frequencies(freq)

    fig, ax = plt.subplots(figsize=(16, 9))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("文本關鍵字詞雲（500 個 selected keywords，由 Chi² + MI + Lift 三重篩選）",
                 fontproperties=prop, fontsize=18, pad=16)
    out = FIG_DIR / "text_wordcloud.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    safe_print(f"      -> {out.name}")


# ============================================================
# 2. Top 30 keywords bar chart (3 metrics)
# ============================================================
def plot_top_keywords():
    safe_print("[2/6] Generating top-30 keywords chart ...")
    kw = pd.read_parquet(PROJECT_ROOT / "outputs" / "text_keywords.parquet")
    sel = kw[kw["selected"]].copy()

    fig, axes = plt.subplots(1, 3, figsize=(20, 8))
    metrics = [("chi2", "Chi² 分數（標籤關聯）", "#1f77b4"),
               ("mi",   "Mutual Information",    "#ff7f0e"),
               ("lift", "Lift（正標籤相對發生率）", "#2ca02c")]

    for ax, (col, title, color) in zip(axes, metrics):
        top = sel.nlargest(30, col).sort_values(col)
        ax.barh(range(len(top)), top[col], color=color, alpha=0.85)
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels(top["term"].astype(str).tolist(), fontproperties=prop, fontsize=9)
        ax.set_xlabel(title, fontproperties=prop, fontsize=11)
        ax.set_title(f"Top 30 by {col.upper()}", fontproperties=prop, fontsize=13)
        ax.grid(axis="x", alpha=0.3)

    fig.suptitle("關鍵字三重篩選 — 各指標 Top 30",
                 fontproperties=prop, fontsize=16, y=1.02)
    fig.tight_layout()
    out = FIG_DIR / "text_top_keywords.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    safe_print(f"      -> {out.name}")


# ============================================================
# 3. Sentiment distribution
# ============================================================
def plot_sentiment_distribution():
    safe_print("[3/6] Generating sentiment distribution ...")
    fs_path = PROJECT_ROOT / "outputs" / "feature_store_final.parquet"
    sent_cols = [
        "sent_polarity_1d", "sent_polarity_5d", "sent_polarity_20d",
        "sent_pos_ratio_5d", "sent_neg_ratio_5d", "sent_pos_neg_spread_5d",
        "sent_volatility_5d", "sent_news_mean_5d", "sent_forum_mean_5d",
    ]
    df = pd.read_parquet(fs_path, columns=sent_cols)

    fig, axes = plt.subplots(3, 3, figsize=(18, 12))
    axes = axes.ravel()
    for ax, col in zip(axes, sent_cols):
        v = df[col].dropna().sample(n=min(200_000, len(df)), random_state=42)
        ax.hist(v, bins=60, color="#636EFA", alpha=0.75, edgecolor="white")
        ax.axvline(v.mean(), color="red", linestyle="--", linewidth=1.2,
                   label=f"mean={v.mean():+.3f}")
        ax.set_title(col, fontsize=11)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)

    fig.suptitle("情緒特徵分布（11 個 sent_ 欄位取 9 個核心）",
                 fontproperties=prop, fontsize=16, y=1.01)
    fig.tight_layout()
    out = FIG_DIR / "text_sentiment_distribution.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    safe_print(f"      -> {out.name}")


# ============================================================
# 4. Platform share
# ============================================================
def plot_platform_share():
    safe_print("[4/6] Generating platform share ...")
    tokens_path = PROJECT_ROOT / "outputs" / "text_tokens_lite.parquet"
    # 若 text_tokens_lite 太大，改從 text_features 統計
    txt_path = PROJECT_ROOT / "outputs" / "text_features.parquet"
    vol_cols_1d = [
        "txt_volume_plat_Dcard_1d",
        "txt_volume_plat_Mobile01_1d",
        "txt_volume_plat_Ptt_1d",
        "txt_volume_plat_Yahoo新聞_1d",
        "txt_volume_plat_Yahoo股市_1d",
    ]
    df = pd.read_parquet(txt_path, columns=["company_id", "trade_date"] + vol_cols_1d)
    total = {c.replace("txt_volume_plat_", "").replace("_1d", ""): df[c].sum() for c in vol_cols_1d}
    total = {k: v for k, v in total.items() if v > 0}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    colors = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A"]

    # Pie
    labels = list(total.keys())
    values = list(total.values())
    ax1.pie(values, labels=labels, autopct="%1.1f%%", colors=colors,
            textprops={"fontproperties": prop, "fontsize": 11},
            wedgeprops={"edgecolor": "white", "linewidth": 2})
    ax1.set_title("五平台文章比例", fontproperties=prop, fontsize=14)

    # Bar absolute
    bars = ax2.bar(labels, values, color=colors, alpha=0.85)
    ax2.set_ylabel("提及次數（article × stock）", fontproperties=prop, fontsize=11)
    ax2.set_title("五平台絕對量", fontproperties=prop, fontsize=14)
    for bar, v in zip(bars, values):
        ax2.text(bar.get_x() + bar.get_width() / 2, v,
                 f"{int(v):,}", ha="center", va="bottom", fontsize=10)
    for lbl in ax2.get_xticklabels():
        lbl.set_fontproperties(prop)
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle("文本資料來源分布（Dcard / Mobile01 / PTT / Yahoo 新聞 / Yahoo 股市）",
                 fontproperties=prop, fontsize=15, y=1.02)
    fig.tight_layout()
    out = FIG_DIR / "text_platform_share.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    safe_print(f"      -> {out.name}")


# ============================================================
# 5. Volume over time
# ============================================================
def plot_volume_over_time():
    safe_print("[5/6] Generating volume over time ...")
    txt_path = PROJECT_ROOT / "outputs" / "text_features.parquet"
    df = pd.read_parquet(txt_path, columns=["trade_date", "txt_volume_n_articles_1d"])
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    daily = df.groupby("trade_date")["txt_volume_n_articles_1d"].sum().reset_index()

    fig, ax = plt.subplots(figsize=(16, 6))
    ax.fill_between(daily["trade_date"], daily["txt_volume_n_articles_1d"],
                    alpha=0.4, color="#636EFA")
    ax.plot(daily["trade_date"], daily["txt_volume_n_articles_1d"],
            color="#4b50c4", linewidth=1.2)

    # 7 日 rolling mean
    daily["roll7"] = daily["txt_volume_n_articles_1d"].rolling(7, min_periods=1).mean()
    ax.plot(daily["trade_date"], daily["roll7"],
            color="#ef4444", linewidth=2, label="7 日均值")

    ax.set_xlabel("交易日", fontproperties=prop, fontsize=12)
    ax.set_ylabel("當日文章量（article × stock）", fontproperties=prop, fontsize=12)
    ax.set_title(f"文本量時序（{daily['trade_date'].min().date()} ~ {daily['trade_date'].max().date()}，"
                 f"合計 {int(daily['txt_volume_n_articles_1d'].sum()):,} 次提及）",
                 fontproperties=prop, fontsize=14, pad=10)
    ax.legend(prop=prop, fontsize=11)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = FIG_DIR / "text_volume_over_time.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    safe_print(f"      -> {out.name}")


# ============================================================
# 6. Coverage heatmap (top 20 stocks × month)
# ============================================================
def plot_coverage_heatmap():
    safe_print("[6/6] Generating coverage heatmap ...")
    txt_path = PROJECT_ROOT / "outputs" / "text_features.parquet"
    df = pd.read_parquet(txt_path, columns=["company_id", "trade_date", "txt_volume_n_articles_1d"])
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["ym"] = df["trade_date"].dt.to_period("M").astype(str)

    # Top 20 stocks by total volume
    top_stocks = (df.groupby("company_id")["txt_volume_n_articles_1d"].sum()
                  .nlargest(20).index.tolist())

    # Load company names — companies.parquet uses company_id / short_name
    comp_path = PROJECT_ROOT / "選用資料集" / "parquet" / "companies.parquet"
    name_map = {}
    if comp_path.exists():
        try:
            comp = pd.read_parquet(comp_path, columns=["company_id", "short_name"])
            comp["company_id"] = comp["company_id"].astype(str)
            name_map = dict(zip(comp["company_id"], comp["short_name"]))
        except Exception:
            pass

    sub = df[df["company_id"].astype(str).isin([str(s) for s in top_stocks])].copy()
    sub["company_id"] = sub["company_id"].astype(str)
    piv = sub.pivot_table(index="company_id", columns="ym",
                          values="txt_volume_n_articles_1d", aggfunc="sum").fillna(0)
    piv = piv.reindex([str(s) for s in top_stocks])
    piv.index = [f"{s} {name_map.get(s, '')}".strip() for s in piv.index]

    fig, ax = plt.subplots(figsize=(16, 9))
    im = ax.imshow(piv.values, aspect="auto", cmap="YlOrRd")

    ax.set_xticks(range(len(piv.columns)))
    ax.set_xticklabels(piv.columns, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels(piv.index, fontproperties=prop, fontsize=10)
    ax.set_title(f"Top 20 最常被提及個股 × 月份覆蓋熱圖（2023-03 ~ 2025-03）",
                 fontproperties=prop, fontsize=14, pad=12)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("月度提及次數", fontproperties=prop, fontsize=11)
    fig.tight_layout()
    out = FIG_DIR / "text_coverage_heatmap.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    safe_print(f"      -> {out.name}")


if __name__ == "__main__":
    safe_print("=" * 70)
    safe_print("Phase 5B Stage 2.5 — 文本分析視覺化")
    safe_print(f"Output dir: {FIG_DIR}")
    safe_print("=" * 70)

    plot_wordcloud()
    plot_top_keywords()
    plot_sentiment_distribution()
    plot_platform_share()
    plot_volume_over_time()
    plot_coverage_heatmap()

    safe_print("=" * 70)
    safe_print("All 6 figures generated.")
    safe_print("=" * 70)
