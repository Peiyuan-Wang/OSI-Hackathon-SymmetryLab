"""Frozen seed correctness suite. This does not score scientific taste or novelty."""
import argparse
import json
from pathlib import Path
from symmetrylab.verifier.orientation import orientation_scan, check_orientation, axis_constraints, check_axis


def evaluate_discovery(suite, output):
    cases=json.loads(Path(suite).read_text())['cases']
    rows=[]
    for case in cases:
        kernel=case['kernel']
        if kernel not in {'orientation','axis'}:raise ValueError('Unknown benchmark kernel')
        try:
            result=(orientation_scan if kernel=='orientation' else axis_constraints)(**case['inputs'])
            certified=(check_orientation if kernel=='orientation' else check_axis)(result)
            actual={key:result[key] for key in case['expected']}
            correct=certified and actual==case['expected']
        except ValueError:
            certified=False;actual={'error':'invalid_input'};correct=case['expected']==actual
        rows.append({'id':case['id'],'family':case['family'],'correct':correct,'certificate_verified':certified,'actual':actual})
    metrics={'suite':'discovery-seed-v1','split':'public_seed_only','total':len(rows),
             'correct':sum(x['correct'] for x in rows),'model_calls':0,
             'taste_evaluated':False,'improvement_evaluated':False,
             'scope':'Deterministic conditional-kernel correctness; no discovery, expert-taste or live-agent score.'}
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('Use a new output directory')
    output.mkdir(parents=True,exist_ok=True)
    (output/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    (output/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
    return metrics


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',default='benchmarks/discovery/seed.json')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=evaluate_discovery(args.suite,args.output)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['correct']==result['total'] else 1)
