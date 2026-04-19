"""
Phase 5B Stage 2.5 — 特徵 IC 驗證 (Checkpoint 2)
==================================================

目的：在把文本/情緒/主題特徵送進模型前，先驗證每個特徵的預測力。
     這是「特徵有沒有用」的 go/no-go 守門員，避免浪費 Stage 3 建模時間。

流程：
  1. 合併三份檔：
        outputs/feature_store.parquet          ← 7 支柱 + labels
        outputs/feature_store_with_sent.parquet ← sent_ 已 merge（或獨立 sent_*.parquet）
        outputs/text_features.parquet          ← txt_keyword_* / txt_volume_*
  2. 對所有特徵逐一算 Rank IC（Spearman）對 fwd_ret_1 / fwd_ret_5 / fwd_ret_20
  3. 以 rank_ic_by_date 取逐日 IC → IC Mean / IC Std / IR = Mean/Std / IC Hit Rate
  4. 設定 3 段通過標準：
        STRONG  : |IC_mean|>=0.015 AND |IR|>=0.15 AND hit_rate>=0.55
        WEAK    : |IC_mean|>=0.005 AND |IR|>=0.05
        REJECT  : 其他
  5. 輸出：
        outputs/reports/feature_ic_report_{run_id}.csv
        outputs/reports/feature_ic_summary_{run_id}.json
     並在 stdout 印出每個 pillar 的通過率 + strong 特徵 top 10

執行：
    python 程式碼/執行Phase5B_IC驗證.py [--horizons 1,5,20]

輸出後請檢查：
  - sent_/txt_/event_/topic_ pillar 內有 STRONG 特徵嗎？若全部 REJECT → 文本 pillar 失敗
  - 與舊 pillar（trend_/fund_/val_/risk_/chip_/ind_）的 IC 量級比較，文本應在可比量級
"""
from __future__ import annotations

import sys
import io
import json
import argparse
import time
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "程式碼"))


# ============================================================
# IC 計算
# ============================================================

def _pillar_of(col: str) -> str:
    for prefix in ("trend_", "fund_", "val_", "event_", "risk_", "chip_",
                   "ind_", "sent_", "txt_", "topic_", "mg_"):
        if col.startswith(prefix):
            return prefix.rstrip("_")
    return "other"


def _summarize_ic(ic_series: pd.Series, feat: str, ret_col: str, n_obs: int) -> dict:
    """把一支 daily_ic 序列轉成 row dict。"""
    if len(ic_series) == 0:
        return dict(
            feat=feat, ret=ret_col,
            n_days=0, n_obs=int(n_obs),
            ic_mean=np.nan, ic_std=np.nan, ir=np.nan, hit_rate=np.nan,
            ic_p5=np.nan, ic_p95=np.nan,
        )
    m = ic_series.mean()
    s = ic_series.std()
    ir = m / s if s > 0 else np.nan
    hit = float((np.sign(ic_series) == np.sign(m)).mean())
    return dict(
        feat=feat, ret=ret_col,
        n_days=int(len(ic_series)), n_obs=int(n_obs),
        ic_mean=float(m), ic_std=float(s), ir=float(ir),
        hit_rate=float(hit),
        ic_p5=float(ic_series.quantile(0.05)),
        ic_p95=float(ic_series.quantile(0.95)),
    )


def compute_ic_matrix(
    df: pd.DataFrame,
    feature_cols: list,
    return_col: str,
    date_col: str = "trade_date",
    min_per_day: int = 30,
) -> dict:
    """
    一次對多個 feature 計算日 IC（Rank IC = Pearson on daily ranks）。

    純 numpy bincount 向量化（no Python/groupby per-feature loop）：
      1. 過濾 return 非 NaN 且日樣本數 >= min_per_day 的 row
      2. groupby(date).rank() 一次算完所有 feature + return 的日內 rank
      3. 用 np.unique 產生 group inverse index `inv`
      4. 對每個 feature 用 np.bincount 一次性算 per-day sum / mean / 相關係數
         - 所有運算都是 O(N) numpy 向量化，無 Python-per-date loop

    回傳 {feature_col: row_dict}
    """
    # 只保留必要欄，避免 DataFrame 太大
    keep_cols = [date_col, return_col] + feature_cols
    sub = df[keep_cols]
    # return 非 NaN
    sub = sub[sub[return_col].notna()]
    if len(sub) == 0:
        return {f: _summarize_ic(pd.Series(dtype=float), f, return_col, 0)
                for f in feature_cols}

    # 過濾日樣本數太少的日子
    day_sizes = sub.groupby(date_col)[return_col].size()
    valid_days = day_sizes[day_sizes >= min_per_day].index
    sub = sub[sub[date_col].isin(valid_days)]
    if len(sub) == 0:
        return {f: _summarize_ic(pd.Series(dtype=float), f, return_col, 0)
                for f in feature_cols}

    # 一次算 rank — 日內排名
    rank_cols = [return_col] + feature_cols
    ranks_df = sub.groupby(date_col, sort=False)[rank_cols].rank(method="average")

    # 產生 group inverse index（用 pandas.factorize 比 np.unique 快）
    date_vals = sub[date_col].values
    inv, uniq_dates = pd.factorize(date_vals, sort=False)
    n_groups = len(uniq_dates)

    # 預先算 return rank 的 per-day mean 與 centered
    r = ranks_df[return_col].values.astype(np.float64)
    # 所有 return rank 都有值（因為我們 dropna return 了）
    r_count = np.bincount(inv, minlength=n_groups)
    r_sum = np.bincount(inv, weights=r, minlength=n_groups)
    r_mean_group = r_sum / np.maximum(r_count, 1)
    r_mean = r_mean_group[inv]
    r_c = r - r_mean  # per-day centered return rank
    # 每日 r_c^2 sum（feature NaN 時會減去那些 row，所以另外算）
    # 這裡先不算 denom_r_sq_all，每個 feature 根據自己 valid mask 個別算

    results = {}
    for feat in feature_cols:
        f = ranks_df[feat].values.astype(np.float64)
        valid = ~np.isnan(f)
        n_obs = int(valid.sum())
        if n_obs < min_per_day * 3:
            results[feat] = _summarize_ic(pd.Series(dtype=float), feat, return_col, n_obs)
            continue

        # per-day count + sum (只算 valid rows)
        f_valid = np.where(valid, f, 0.0)
        w_valid = valid.astype(np.float64)
        count_g = np.bincount(inv, weights=w_valid, minlength=n_groups)
        f_sum_g = np.bincount(inv, weights=f_valid, minlength=n_groups)
        with np.errstate(divide="ignore", invalid="ignore"):
            f_mean_g = f_sum_g / np.maximum(count_g, 1)
        f_mean = f_mean_g[inv]
        # 只在 valid rows 上 centered，其餘填 0 避免汙染 sum
        f_c = np.where(valid, f - f_mean, 0.0)

        # 對 r 同樣只用 valid rows 的 r_mean（重新算）— 避免 feature NaN 處進來污染
        r_sum_v = np.bincount(inv, weights=r * w_valid, minlength=n_groups)
        with np.errstate(divide="ignore", invalid="ignore"):
            r_mean_v_g = r_sum_v / np.maximum(count_g, 1)
        r_mean_v = r_mean_v_g[inv]
        r_c_v = np.where(valid, r - r_mean_v, 0.0)

        numer = np.bincount(inv, weights=f_c * r_c_v, minlength=n_groups)
        denom_f_sq = np.bincount(inv, weights=f_c * f_c, minlength=n_groups)
        denom_r_sq = np.bincount(inv, weights=r_c_v * r_c_v, minlength=n_groups)

        with np.errstate(divide="ignore", invalid="ignore"):
            daily_ic = numer / np.sqrt(denom_f_sq * denom_r_sq)

        # 過濾掉日樣本數不足或 denom 為 0 的日子
        good = (count_g >= min_per_day) & np.isfinite(daily_ic)
        daily_ic_clean = daily_ic[good]

        ic_series = pd.Series(daily_ic_clean)
        results[feat] = _summarize_ic(ic_series, feat, return_col, n_obs)
    return results


def compute_feature_ic(
    df: pd.DataFrame,
    feature_col: str,
    return_col: str,
    date_col: str = "trade_date",
    min_per_day: int = 30,
) -> dict:
    """保留原單支介面（向後相容）。內部用 compute_ic_matrix。"""
    res = compute_ic_matrix(df, [feature_col], return_col, date_col, min_per_day)
    return res[feature_col]


def classify_ic(row: pd.Series) -> str:
    """3 段通過標準"""
    if pd.isna(row["ic_mean"]):
        return "INVALID"
    ic = abs(row["ic_mean"])
    ir = abs(row["ir"]) if not pd.isna(row["ir"]) else 0.0
    hit = row["hit_rate"] if not pd.isna(row["hit_rate"]) else 0.0
    if ic >= 0.015 and ir >= 0.15 and hit >= 0.55:
        return "STRONG"
    if ic >= 0.005 and ir >= 0.05:
        return "WEAK"
    return "REJECT"


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Phase 5B Stage 2.5 — Feature IC validation")
    parser.add_argument("--feature-store", default="outputs/feature_store_with_sent.parquet",
                        help="已 merge sent_ 的 feature store")
    parser.add_argument("--text-features", default="outputs/text_features.parquet",
                        help="Stage 2.2 txt_ 輸出")
    parser.add_argument("--horizons", default="1,5,20",
                        help="要評估的 forward return horizons (逗號分隔)")
    parser.add_argument("--min-per-day", type=int, default=30,
                        help="每日最少樣本數（低於則跳過該日）")
    parser.add_argument("--output-dir", default="outputs/reports",
                        help="報告輸出目錄")
    parser.add_argument("--include-pillars", default=None,
                        help="只評估指定 pillar，逗號分隔（例：sent,txt_volume,event）。"
                             "預設評估所有 pillar（txt_keyword 量大所以預設跳過）")
    parser.add_argument("--skip-txt-keyword", action="store_true", default=True,
                        help="跳過 txt_keyword_* 個別關鍵字（1500 個，IC 驗證過慢；預設 True）")
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = PROJECT_ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    log_path = PROJECT_ROOT / "logs" / f"phase5b_s25_ic_{run_id}.log"
    logger.remove()
    logger.add(sys.stdout, format="{time:HH:mm:ss} | {level:<7} | {message}", level="INFO")
    logger.add(str(log_path), level="DEBUG", encoding="utf-8")

    logger.info("=" * 70)
    logger.info("Phase 5B Stage 2.5 — Feature IC Validation (Checkpoint 2)")
    logger.info(f"Run ID: {run_id}")
    logger.info("=" * 70)

    horizons = [int(h) for h in args.horizons.split(",")]
    t0 = time.time()

    # ─── 1. 載入 feature_store + text_features + merge ───
    fs_path = PROJECT_ROOT / args.feature_store
    if not fs_path.exists():
        # 退回到沒 sent_ 的版本
        fs_path = PROJECT_ROOT / "outputs" / "feature_store.parquet"
        logger.warning(f"sent feature store 不存在，退回 {fs_path}")

    logger.info(f"\n[1/4] Loading {fs_path.name} ...")
    df = pd.read_parquet(fs_path)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["company_id"] = df["company_id"].astype(str)
    logger.info(f"  base: {df.shape}")

    # 若 feature_store 已含 txt_ 欄（例如 feature_store_final.parquet），略過再 merge
    existing_txt = [c for c in df.columns if c.startswith("txt_")]
    if existing_txt:
        logger.info(f"\n  feature_store already has {len(existing_txt)} txt_ cols; "
                    f"skip redundant text_features merge.")
    else:
        txt_path = PROJECT_ROOT / args.text_features
        if txt_path.exists():
            logger.info(f"\n  Loading {txt_path.name} ...")
            txt_df = pd.read_parquet(txt_path)
            txt_df["trade_date"] = pd.to_datetime(txt_df["trade_date"])
            txt_df["company_id"] = txt_df["company_id"].astype(str)
            txt_cols = [c for c in txt_df.columns if c.startswith("txt_")]
            logger.info(f"  txt_ cols: {len(txt_cols)}")
            # 只 merge txt_ 欄，避免把其他重複欄位帶進來
            df = df.merge(
                txt_df[["company_id", "trade_date"] + txt_cols],
                on=["company_id", "trade_date"], how="left",
            )
            for c in txt_cols:
                df[c] = df[c].fillna(0.0)
            logger.info(f"  merged: {df.shape}")
        else:
            logger.warning(f"  text_features 不存在：{txt_path}，略過 txt_ 評估")

    # ─── 2. 找 forward return 欄 ───
    ret_cols = {h: f"fwd_ret_{h}" for h in horizons if f"fwd_ret_{h}" in df.columns}
    if not ret_cols:
        logger.error(f"找不到 fwd_ret_* 欄：{df.columns.tolist()[:30]}")
        sys.exit(1)
    logger.info(f"\n[2/4] Return cols: {list(ret_cols.values())}")

    # ─── 3. 找所有特徵欄 ───
    excluded = {"company_id", "trade_date", "date"}
    non_feat_prefix = ("fwd_ret_", "label_")
    feature_cols = [
        c for c in df.columns
        if c not in excluded
        and not c.startswith(non_feat_prefix)
        and pd.api.types.is_numeric_dtype(df[c])
    ]
    logger.info(f"  Feature cols (raw): {len(feature_cols)}")

    # 過濾：跳過 txt_keyword_*（太多 1500 個，IC 驗證成本高）
    if args.skip_txt_keyword:
        before = len(feature_cols)
        feature_cols = [c for c in feature_cols if not c.startswith("txt_keyword_")]
        logger.info(f"  skip txt_keyword_: {before} → {len(feature_cols)}")

    if args.include_pillars:
        wanted = [p.strip() for p in args.include_pillars.split(",")]
        feature_cols = [c for c in feature_cols if any(c.startswith(p + "_") or c.startswith(p) for p in wanted)]
        logger.info(f"  include-pillars={wanted}: {len(feature_cols)}")

    # 依 pillar 分組統計
    by_pillar = {}
    for c in feature_cols:
        by_pillar.setdefault(_pillar_of(c), []).append(c)
    for p, cols in sorted(by_pillar.items()):
        logger.info(f"    {p}: {len(cols)}")

    # ─── 4. 每個 horizon 用一次 vectorized 算完所有特徵 IC ───
    logger.info(f"\n[3/4] Computing IC for {len(feature_cols)} features × {len(ret_cols)} horizons (vectorized) ...")
    rows = []
    for h, rcol in ret_cols.items():
        t_h = time.time()
        logger.info(f"    h={h} ({rcol}) ...")
        ic_dict = compute_ic_matrix(
            df=df,
            feature_cols=feature_cols,
            return_col=rcol,
            min_per_day=args.min_per_day,
        )
        for feat in feature_cols:
            rows.append(ic_dict[feat])
        logger.info(f"    h={h} done in {time.time()-t_h:.0f}s")

    ic_df = pd.DataFrame(rows)
    ic_df["pillar"] = ic_df["feat"].apply(_pillar_of)
    ic_df["verdict"] = ic_df.apply(classify_ic, axis=1)

    # ─── 5. 輸出報告 ───
    logger.info(f"\n[4/4] Writing reports ...")
    csv_out = out_dir / f"feature_ic_report_{run_id}.csv"
    ic_df.sort_values(["pillar", "ret", "ic_mean"], ascending=[True, True, False]).to_csv(
        csv_out, index=False, encoding="utf-8-sig"
    )
    logger.info(f"  CSV: {csv_out}")

    # Summary
    summary = {"run_id": run_id, "horizons": horizons, "by_pillar": {}, "by_verdict": {}}
    logger.info("\n" + "=" * 70)
    logger.info("Summary by pillar × horizon (verdict counts)")
    logger.info("=" * 70)
    for pillar, sub in ic_df.groupby("pillar"):
        logger.info(f"\n[{pillar}] n_feats={sub['feat'].nunique()}")
        summary["by_pillar"][pillar] = {}
        for h in horizons:
            rcol = ret_cols.get(h)
            if not rcol:
                continue
            sub_h = sub[sub["ret"] == rcol]
            counts = sub_h["verdict"].value_counts().to_dict()
            strong = counts.get("STRONG", 0)
            weak = counts.get("WEAK", 0)
            rej = counts.get("REJECT", 0)
            top_ic = sub_h.nlargest(3, "ic_mean")[["feat", "ic_mean", "ir", "hit_rate"]]
            logger.info(
                f"  h={h:<3} STRONG={strong:<3} WEAK={weak:<3} REJECT={rej:<3}  "
                f"| ic_mean max={sub_h['ic_mean'].max():+.4f} "
                f"min={sub_h['ic_mean'].min():+.4f}"
            )
            if strong > 0:
                for _, r in top_ic.iterrows():
                    logger.info(
                        f"         ★ {r['feat']:<35} ic={r['ic_mean']:+.4f} "
                        f"ir={r['ir']:+.3f} hit={r['hit_rate']:.2f}"
                    )
            summary["by_pillar"][pillar][f"h{h}"] = {
                "strong": strong, "weak": weak, "reject": rej,
                "ic_mean_max": float(sub_h["ic_mean"].max()) if len(sub_h) else None,
                "ic_mean_min": float(sub_h["ic_mean"].min()) if len(sub_h) else None,
            }

    for v, n in ic_df["verdict"].value_counts().items():
        summary["by_verdict"][v] = int(n)

    summary_path = out_dir / f"feature_ic_summary_{run_id}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.info(f"\n  JSON: {summary_path}")

    elapsed = time.time() - t0
    logger.info("=" * 70)
    logger.info(f"✅ Stage 2.5 完成 — {elapsed/60:.1f} 分鐘")
    logger.info(f"   STRONG:  {ic_df[ic_df['verdict']=='STRONG'].shape[0]}")
    logger.info(f"   WEAK:    {ic_df[ic_df['verdict']=='WEAK'].shape[0]}")
    logger.info(f"   REJECT:  {ic_df[ic_df['verdict']=='REJECT'].shape[0]}")
    logger.info(f"   INVALID: {ic_df[ic_df['verdict']=='INVALID'].shape[0]}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
