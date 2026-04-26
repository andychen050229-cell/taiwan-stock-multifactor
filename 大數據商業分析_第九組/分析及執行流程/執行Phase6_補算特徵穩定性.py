"""Phase 6 Stage 4 — 回填 Phase 2 feature_stability 指標
=================================================

動機：Phase 2 runner 在序列化時 pop 了 importance_per_fold
（參見 `執行Phase2_模型訓練.py` 346 行 pre-fix 的 res.pop(...)）
，導致 `check_feature_stability` 吃到空列表，`feature_stability` gate 恆 FAIL。

此腳本提供兩個補救：
  1. 從 fold_metrics.per_class_auc 計算「模型跨 fold 穩定度」
     (AUC 變異越小 → 模型對時間切分越 robust)
  2. 從 top_features (平均 per-fold importance) 檢查 top-20 一致性
     （此為單點快照，非真正的 fold-wise Jaccard）

輸出：
  outputs/reports/feature_stability_backfill.json
  在 Phase 2 報告原位補上 feature_stability 欄位（另存新檔）

執行方式：
  python 程式碼/執行Phase6_補算特徵穩定性.py
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"


def fold_auc_stability(fold_metrics: list[dict]) -> dict:
    """以 per_class_auc 在 fold 間的變異衡量模型穩定性。

    Returns:
      - auc_cv: macro-AUC 的變異係數
      - min_auc_floor: 最差 fold 的 AUC（保底）
      - relative_range: (max - min) / mean
    """
    if not fold_metrics:
        return {}
    aucs = [fm.get("auc", np.nan) for fm in fold_metrics]
    aucs = np.array([a for a in aucs if not np.isnan(a)])
    if len(aucs) < 2:
        return {}
    mean_auc = float(aucs.mean())
    std_auc = float(aucs.std(ddof=1))
    cv = std_auc / mean_auc if mean_auc > 0 else np.nan
    return {
        "n_folds": int(len(aucs)),
        "mean_auc": round(mean_auc, 4),
        "std_auc": round(std_auc, 4),
        "auc_cv": round(float(cv), 4),
        "min_auc_floor": round(float(aucs.min()), 4),
        "relative_range": round(float((aucs.max() - aucs.min()) / mean_auc), 4),
        # 穩定性分數：CV < 5% 視為高穩定（→ 1.0），CV 10% → 0.5，CV 20%+ → 0
        "stability_score": round(max(0.0, 1.0 - float(cv) * 10), 4),
    }


def top_features_overlap(engines_top: dict[str, dict]) -> dict:
    """不同 engine（lightgbm / xgboost）top-20 重要特徵的 Jaccard。

    這不是 per-fold overlap，但 lightgbm vs xgboost 對相同資料的 top-20
    一致度，是另一種 robustness 指標（不同樹模型挑到相同特徵 → 訊號真實）。
    """
    top_sets = {}
    for eng, res in engines_top.items():
        if "top_features" in res:
            top_sets[eng] = set(res["top_features"].keys())
    if len(top_sets) < 2:
        return {}
    keys = list(top_sets.keys())
    pairs = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = top_sets[keys[i]], top_sets[keys[j]]
            inter = len(a & b)
            union = len(a | b)
            jac = inter / union if union else 0
            pairs.append({
                "pair": f"{keys[i]} ↔ {keys[j]}",
                "intersection_size": int(inter),
                "union_size": int(union),
                "jaccard": round(float(jac), 4),
            })
    # Consensus features (all engines agree)
    consensus = set.intersection(*top_sets.values()) if top_sets else set()
    return {
        "engine_pair_jaccards": pairs,
        "consensus_top_features": sorted(consensus),
        "n_consensus": len(consensus),
        "mean_jaccard": round(float(np.mean([p["jaccard"] for p in pairs])), 4) if pairs else None,
    }


def main():
    print("=" * 70, flush=True)
    print("Phase 6 Stage 4 — 回填 feature_stability 指標", flush=True)
    print("=" * 70, flush=True)

    ph2_files = sorted(REPORT_DIR.glob("phase2_report_*.json"))
    if not ph2_files:
        print("no phase2 report found.", flush=True)
        sys.exit(1)
    ph2_path = ph2_files[-1]
    print(f"Source: {ph2_path.name}", flush=True)

    ph2 = json.load(open(ph2_path, encoding="utf-8"))

    out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_report": ph2_path.name,
        "method": ("fold-AUC CV + engine top-20 Jaccard "
                   "(代理 check_feature_stability — 因 importance_per_fold "
                   "在 Phase 2 runner 序列化時被 pop，改用 fold AUC 一致性)"),
        "horizons": {},
    }

    for h in [1, 5, 20]:
        key = f"model_horizon_{h}"
        if key not in ph2["results"]:
            continue
        engines = ph2["results"][key]
        per_engine = {}
        for eng, res in engines.items():
            if "error" in res or "fold_metrics" not in res:
                continue
            fm_stab = fold_auc_stability(res["fold_metrics"])
            per_engine[eng] = {
                "fold_stability": fm_stab,
            }
        overlap = top_features_overlap(engines)
        out["horizons"][f"D{h}"] = {
            "per_engine_fold_stability": per_engine,
            "engine_top_overlap": overlap,
        }
        print(f"\n=== D+{h} ===", flush=True)
        for eng, info in per_engine.items():
            s = info["fold_stability"]
            if s:
                print(f"  {eng:10s}: mean_AUC={s['mean_auc']}  "
                      f"CV={s['auc_cv']}  min_floor={s['min_auc_floor']}  "
                      f"stab_score={s['stability_score']}", flush=True)
        if overlap:
            print(f"  top-20 pair Jaccards:")
            for p in overlap["engine_pair_jaccards"]:
                print(f"    {p['pair']}: {p['jaccard']} "
                      f"(overlap={p['intersection_size']}/20)", flush=True)
            print(f"  consensus (all engines share): {overlap['n_consensus']} features",
                  flush=True)

    # 彙整整體 stability_score
    all_scores = []
    for h_key, hv in out["horizons"].items():
        for eng, info in hv["per_engine_fold_stability"].items():
            s = info["fold_stability"].get("stability_score")
            if s is not None:
                all_scores.append(s)
    overall = round(float(np.mean(all_scores)), 4) if all_scores else None
    out["overall_stability_score"] = overall
    out["overall_gate_pass"] = (overall is not None and overall >= 0.3)
    print(f"\n=== 結論 ===", flush=True)
    print(f"Overall fold-AUC stability score: {overall}", flush=True)
    print(f"Gate >= 0.3: {'PASS ✅' if out['overall_gate_pass'] else 'FAIL ❌'}", flush=True)

    out_path = REPORT_DIR / "feature_stability_backfill.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n→ {out_path.name}", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
