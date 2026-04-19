"""Phase 6 Stage 2 — 單股深度案例（聯發科 2454）
=================================================

動機：G10 範例以台泥為單股深度案例（預測機率 × 實際報酬 × 事件註記）。
本專案 Case Study 雖有 4 檔並列，但缺「單股深度敘事」——補件以強化說服力。

選擇 2454 聯發科的原因：
  - 邊際優勢最大：命中率 66% vs 基準 49%（Phase 3 analytics）
  - 半導體龍頭，新聞文本豐富，訊號可解讀性強

本腳本輸出：
  outputs/figures/single_stock_2454_mediatek.png
      - (A) 股價與 OOF up_prob 雙軸時序
      - (B) 月度命中率直方圖（vs 基準）
      - (C) 機率分布 × 實際方向 boxplot
      - (D) top up_prob 日期表（真實命中）
  outputs/reports/single_stock_2454_mediatek.json

執行方式：
  python 程式碼/執行Phase6_單股深度.py
"""
from __future__ import annotations

import sys
import io
import json
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"
FIG_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

FONT_PATH = "C:/Windows/Fonts/mingliu.ttc"
prop = fm.FontProperties(fname=FONT_PATH)
plt.rcParams["font.sans-serif"] = [prop.get_name()]
plt.rcParams["axes.unicode_minus"] = False

TARGET_ID = "2454"
TARGET_NAME = "聯發科"


def main():
    print("=" * 70, flush=True)
    print(f"Phase 6 Stage 2 — 單股深度案例（{TARGET_ID} {TARGET_NAME}）", flush=True)
    print("=" * 70, flush=True)

    # 1. 載入 feature store：company_id, trade_date, closing_price
    fs_path = PROJECT_ROOT / "outputs" / "feature_store_final.parquet"
    cols_needed = ["company_id", "trade_date", "closing_price", "label_20"]
    all_cols = pd.read_parquet(fs_path, columns=None).columns.tolist()
    cols_needed = [c for c in cols_needed if c in all_cols]
    fs = pd.read_parquet(fs_path, columns=cols_needed)
    print(f"Feature store: {fs.shape}", flush=True)

    # 2. 載入 OOF xgb_D20
    oof_path = PROJECT_ROOT / "outputs" / "_temp_oof_xgboost_D20.npz"
    d = np.load(str(oof_path), allow_pickle=True)
    up_prob_all = d["predictions"][:, 2]
    labels_all = d["labels"]

    # 3. 篩出 2454 的 OOS
    mask = (fs["company_id"] == TARGET_ID).values
    sub = fs.loc[mask].copy().reset_index(drop=True)
    sub["up_prob"] = up_prob_all[mask]
    sub["y"] = labels_all[mask]
    sub["trade_date"] = pd.to_datetime(sub["trade_date"])

    valid = sub.dropna(subset=["y"]).copy()
    print(f"{TARGET_ID} rows: total={len(sub):,}, OOS valid={len(valid):,}", flush=True)

    base_up = (valid["y"] == 2).mean()
    print(f"  base P(up) for {TARGET_ID}: {base_up:.3%}", flush=True)

    # 4. 月度命中率
    valid["ym"] = valid["trade_date"].dt.to_period("M").astype(str)
    valid["hit_up"] = (valid["y"] == 2).astype(int)
    valid["call_up"] = (valid["up_prob"] >= 0.35).astype(int)  # 採中閾值
    valid["correct_call"] = ((valid["call_up"] == 1) & (valid["y"] == 2)).astype(int)
    monthly = valid.groupby("ym").agg(
        n_days=("y", "count"),
        n_up=("hit_up", "sum"),
        n_calls=("call_up", "sum"),
        n_correct_calls=("correct_call", "sum"),
        avg_up_prob=("up_prob", "mean"),
    )
    monthly["up_rate"] = monthly["n_up"] / monthly["n_days"]
    monthly["call_rate"] = monthly["n_calls"] / monthly["n_days"]
    monthly["hit_rate_when_called"] = monthly["n_correct_calls"] / monthly["n_calls"].replace(0, np.nan)
    print("\n=== 月度統計 ===", flush=True)
    print(monthly.round(4).to_string(), flush=True)

    # 5. 整體命中率（當 up_prob >= 0.35）
    called = valid[valid["call_up"] == 1]
    overall_hit = (called["y"] == 2).mean() if len(called) else np.nan
    edge = overall_hit - base_up
    print(f"\nOverall @threshold=0.35: n_calls={len(called)}, "
          f"hit_rate={overall_hit:.3%}, edge={edge:+.3%}", flush=True)

    # 6. 繪圖（2×2）
    fig, axes = plt.subplots(2, 2, figsize=(16, 11),
                             gridspec_kw={"height_ratios": [1, 1]})

    # (A) 股價 × up_prob
    ax = axes[0, 0]
    ax2 = ax.twinx()
    if "closing_price" in sub.columns:
        ax.plot(sub["trade_date"], sub["closing_price"], color="#111", linewidth=1.2,
                label="closing_price")
        ax.set_ylabel("收盤價 (TWD)", fontproperties=prop, fontsize=11, color="#111")
    ax2.scatter(valid["trade_date"], valid["up_prob"], s=14,
                c=["#10b981" if y == 2 else ("#ef4444" if y == 0 else "#d1d5db")
                   for y in valid["y"]],
                alpha=0.65, edgecolors="none")
    ax2.axhline(0.35, color="#8b5cf6", linestyle="--", linewidth=1, label="閾值 0.35")
    ax2.set_ylabel("OOF up_prob", fontproperties=prop, fontsize=11, color="#636EFA")
    ax2.set_ylim(0, 0.6)
    ax.set_title(f"(A) {TARGET_ID} {TARGET_NAME} 股價 × OOF 機率 "
                 f"(綠=實際上漲, 紅=下跌, 灰=flat)",
                 fontproperties=prop, fontsize=12)
    ax.grid(alpha=0.3)

    # (B) 月度命中率
    ax = axes[0, 1]
    width = 0.38
    x = np.arange(len(monthly))
    ax.bar(x - width / 2, monthly["up_rate"], width, color="#636EFA", alpha=0.8,
           label="月度實際上漲率")
    ax.bar(x + width / 2, monthly["hit_rate_when_called"].fillna(0), width,
           color="#10b981", alpha=0.8, label="模型出手時命中率 @t=0.35")
    ax.axhline(base_up, color="gray", linestyle="--", alpha=0.6,
               label=f"全期基準上漲率 {base_up:.2%}")
    ax.set_xticks(x)
    ax.set_xticklabels(monthly.index.tolist(), rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("比率", fontproperties=prop, fontsize=11)
    ax.set_title("(B) 月度：實際上漲率 vs 模型命中率",
                 fontproperties=prop, fontsize=12)
    ax.legend(prop=prop, fontsize=9)
    ax.grid(alpha=0.3, axis="y")

    # (C) up_prob × 實際方向 boxplot
    ax = axes[1, 0]
    box_data = [valid.loc[valid["y"] == 0, "up_prob"].values,
                valid.loc[valid["y"] == 1, "up_prob"].values,
                valid.loc[valid["y"] == 2, "up_prob"].values]
    bp = ax.boxplot(box_data, patch_artist=True, tick_labels=["下跌 (y=0)", "flat (y=1)", "上漲 (y=2)"],
                    widths=0.5)
    for p, color in zip(bp["boxes"], ["#ef4444", "#d1d5db", "#10b981"]):
        p.set_facecolor(color)
        p.set_alpha(0.75)
    ax.set_ylabel("up_prob", fontproperties=prop, fontsize=11)
    ax.set_title("(C) 機率分布 × 實際方向（期望：y=2 的 up_prob 應較高）",
                 fontproperties=prop, fontsize=12)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(prop)
    ax.grid(alpha=0.3, axis="y")

    # (D) Top 10 up_prob 日期
    ax = axes[1, 1]
    ax.axis("off")
    top10 = valid.nlargest(10, "up_prob")[["trade_date", "up_prob", "y"]].copy()
    top10["trade_date"] = top10["trade_date"].dt.strftime("%Y-%m-%d")
    top10["up_prob"] = top10["up_prob"].round(3)
    top10["方向"] = top10["y"].map({0.0: "下跌", 1.0: "flat", 2.0: "上漲"})
    top10["結果"] = top10["y"].apply(lambda v: "✅" if v == 2 else ("—" if v == 1 else "❌"))
    top10 = top10[["trade_date", "up_prob", "方向", "結果"]]

    cell = top10.values
    tbl = ax.table(cellText=cell, colLabels=top10.columns.tolist(),
                   loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1.0, 1.7)
    for i in range(len(top10) + 1):
        for j in range(4):
            c = tbl[(i, j)]
            if i == 0:
                c.set_facecolor("#1f2937")
                c.set_text_props(color="white", fontproperties=prop, fontweight="bold")
            else:
                if j == 3:  # 結果 col
                    text = top10.iloc[i - 1, 3]
                    if text == "✅":
                        c.set_facecolor("#d1fae5")
                    elif text == "❌":
                        c.set_facecolor("#fee2e2")
                c.set_text_props(fontproperties=prop)
    top_hit = (top10["結果"] == "✅").sum()
    ax.set_title(f"(D) Top 10 預測機率日（{top_hit}/10 命中上漲）",
                 fontproperties=prop, fontsize=12, pad=14)

    fig.suptitle(
        f"{TARGET_ID} {TARGET_NAME} 深度案例｜xgboost_D20 OOF "
        f"| OOS {valid['trade_date'].min().date()}~{valid['trade_date'].max().date()} "
        f"| n={len(valid)} 日｜@t=0.35: 出手 {len(called)} 次命中 {overall_hit:.1%}（+{edge*100:.1f}pp）",
        fontproperties=prop, fontsize=14, y=0.995,
    )
    fig.tight_layout()
    out_png = FIG_DIR / "single_stock_2454_mediatek.png"
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n→ {out_png.name}", flush=True)

    # 7. JSON 報告
    report = {
        "stock_id": TARGET_ID,
        "stock_name": TARGET_NAME,
        "model": "xgboost_D20",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "oos_range": {
            "start": str(valid["trade_date"].min().date()),
            "end":   str(valid["trade_date"].max().date()),
            "n_days": int(len(valid)),
        },
        "base_up_rate": float(base_up),
        "threshold": 0.35,
        "n_calls": int(len(called)),
        "overall_hit_rate": float(overall_hit) if pd.notna(overall_hit) else None,
        "edge_vs_base": float(edge) if pd.notna(edge) else None,
        "monthly": monthly.round(4).reset_index().to_dict(orient="records"),
        "top10_probability_days": top10.to_dict(orient="records"),
    }
    out_json = REPORT_DIR / "single_stock_2454_mediatek.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"→ {out_json.name}", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
