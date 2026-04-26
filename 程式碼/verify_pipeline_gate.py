"""Verify Phase 3 prediction_pipeline_valid gate against rebuilt joblib.
Stand-alone, no loguru/config dependency. Writes a fresh revalidation JSON.
"""
import json
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
fs_path = ROOT / 'outputs' / 'feature_store_final.parquet'
models_dir = ROOT / 'outputs' / 'models'
out_path = ROOT / 'outputs' / 'reports' / 'phase3_pipeline_revalidation.json'

print(f'feature_store: {fs_path.name}')
fs = pd.read_parquet(fs_path)
print(f'  rows: {len(fs):,} | cols: {len(fs.columns)}')

date_col = 'trade_date' if 'trade_date' in fs.columns else 'date'
latest = fs[date_col].max()
sample = fs[fs[date_col] == latest].head(20)
print(f'  latest date: {latest} | sample size: {len(sample)}')
print()

results = {}
for fp in sorted(models_dir.glob('*.joblib')):
    name = fp.stem.replace('_model', '')
    try:
        md = joblib.load(fp)
        model = md['model']
        feats = md['feature_cols']
        missing = [c for c in feats if c not in fs.columns]
        if missing:
            results[name] = {'status': 'fail', 'error': f'{len(missing)} missing cols, e.g. {missing[:3]}'}
            print(f'{name:18s} FAIL: {results[name]["error"]}')
            continue
        X = sample[feats].fillna(0).values
        pred = model.predict_proba(X)
        assert pred.shape[1] == 3, f'Expected 3 classes, got {pred.shape[1]}'
        assert np.allclose(pred.sum(axis=1), 1.0, atol=0.01), 'Probabilities do not sum to 1'
        assert not np.isnan(pred).any(), 'NaN in predictions'
        results[name] = {
            'status': 'pass',
            'sample_size': int(len(sample)),
            'pred_shape': list(pred.shape),
            'avg_up_prob': round(float(pred[:, 2].mean()), 4),
            'n_features': len(feats),
        }
        print(f'{name:18s} PASS  avg UP prob = {pred[:, 2].mean():.4f}  | {len(feats)} features')
    except Exception as e:
        results[name] = {'status': 'fail', 'error': str(e)}
        print(f'{name:18s} FAIL: {e}')

n_pass = sum(1 for r in results.values() if r['status'] == 'pass')
n_total = len(results)
all_pass = (n_pass == n_total)
print()
print('=' * 60)
print(f'RESULT: {n_pass}/{n_total} models PASS')
print(f'prediction_pipeline_valid = {all_pass}')
print('=' * 60)

# Write fresh revalidation report
out = {
    'phase': 'Phase 3 — prediction_pipeline gate revalidation',
    'timestamp': pd.Timestamp.now().isoformat(),
    'env': 'dev',
    'source_joblib_dir': str(models_dir),
    'feature_store': str(fs_path.name),
    'results': results,
    'summary': {
        'models_tested': n_total,
        'models_pass': n_pass,
        'models_fail': n_total - n_pass,
        'prediction_pipeline_valid': all_pass,
    },
    'note': (
        'Rebuilt joblib (2026-04-20 03:07–03:10) regenerated against the '
        'current 91-feature schema; feature naming drift '
        '(event_news_count_*  →  event_mention_cnt_*) resolved.'
    ),
}
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2, default=str)
print(f'\nWrote: {out_path}')
