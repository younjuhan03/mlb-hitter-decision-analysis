"""Verify the archived snapshot without dependencies, network access, or writes."""
from pathlib import Path
import csv
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]

def rows(relative):
    with (ROOT / relative).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))

def main():
    lock = json.loads((ROOT / 'reports/2027_evaluation_lock.json').read_text(encoding='utf-8'))
    for relative, expected in lock['sha256'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
    sources = 0
    for metadata in (ROOT / 'data/raw').glob('*.meta.json'):
        record = json.loads(metadata.read_text(encoding='utf-8'))
        stem = metadata.name.removesuffix('.meta.json')
        files = [p for p in metadata.parent.glob(stem + '.*') if p != metadata]
        assert len(files) == 1, stem
        assert hashlib.sha256(files[0].read_bytes()).hexdigest() == record['sha256'], stem
        sources += 1
    assert sources == 41, sources
    frozen = rows('reports/2027_frozen_evaluation.csv')
    assert len(frozen) == len({r['player_id'] for r in frozen}) == 298
    assert all(r['evaluation_status'] == 'pending' and not r['actual_woba_2027'] for r in frozen)
    historical = [r for r in rows('reports/historical_predictions.csv') if r['target_available'] == 'True']
    for metric in rows('reports/model_metrics.csv'):
        scope = metric['scope']
        if scope in ('development', 'final_2026'):
            selected = [r for r in historical if r['evaluation_scope'] == scope]
        elif scope == 'without_2022':
            selected = [r for r in historical if r['evaluation_scope'] == 'development' and float(r['target_season']) != 2022]
        else:
            selected = [r for r in historical if float(r['target_season']) == float(scope)]
        assert len(selected) == int(metric['n']), (scope, len(selected))
        col = 'p_' + metric['model']
        errors = [float(r['target_woba']) - float(r[col]) for r in selected]
        rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
        mae = sum(abs(e) for e in errors) / len(errors)
        assert math.isclose(rmse, float(metric['rmse']), abs_tol=1e-12), (scope, col, 'rmse')
        assert math.isclose(mae, float(metric['mae']), abs_tol=1e-12), (scope, col, 'mae')
    policies = {(r['policy'], r['method']): r for r in rows('reports/scouting_policy_summary.csv')}
    for policy, method, slots, successes in [('original_13', 'signal_then_M1', 53, 7), ('original_13', 'M1_only', 53, 13), ('revised_hidden_5', 'signal_then_M1', 22, 2), ('revised_hidden_5', 'M1_only', 22, 7)]:
        record = policies[policy, method]
        assert int(record['total_slots']) == slots and float(record['growth_successes']) == successes
    print('PASS: 4 frozen hashes; 41 cached sources; 298 pending forecasts; forecast metrics; policy counts.')

if __name__ == '__main__':
    main()
