"""Read-only, deterministic integration check of an installed SSG catalog."""
import argparse
from contextlib import closing
import json
from pathlib import Path
from time import monotonic
from symmetrylab.database.ssg import SSGCatalog, DEFAULT_CATALOG
from symmetrylab.verifier.ssg import calculate

parser=argparse.ArgumentParser()
parser.add_argument('--catalog',default=str(DEFAULT_CATALOG))
parser.add_argument('--output',required=True)
args=parser.parse_args()
catalog=SSGCatalog(args.catalog)
metadata=catalog.call('metadata',{})
with closing(catalog.connect()) as conn:
    integrity=conn.execute('PRAGMA quick_check').fetchone()[0]
    labels=[conn.execute('select label from ssg_records where parent_space_group=? order by label limit 1',(n,)).fetchone()[0] for n in range(1,231,10)]
labels=list(dict.fromkeys(labels+['N143.10.1','N10.14.12','P143.5.1']))
results=[]
for label in labels:
    deadline=monotonic()+10
    def remaining():
        if monotonic()>deadline: raise TimeoutError('Per-record verification deadline exceeded')
    record=catalog.reciprocal(label)
    try:
        check=calculate(record,'verify_group',{'record_id':label},remaining)
        orbit=calculate(record,'momentum_orbit',{'record_id':label,'k':['1/3','1/5','1/7']},remaining)
        results.append({'record_id':label,'verification':check,'orbit_size':orbit['orbit_size']})
    except (ValueError,TimeoutError) as exc:
        results.append({'record_id':label,'error':str(exc)})
report={'metadata':metadata,'sqlite_quick_check':integrity,'cases':results,
        'passed':sum(r.get('verification',{}).get('status')=='verified' for r in results),
        'note':'Deterministic sampled integration checks, not an exhaustive re-verification of the scientific catalog.'}
output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(report,indent=2))
print(json.dumps({'integrity':integrity,'sample_count':len(results),'passed':report['passed'],'output':str(output)}))
assert integrity=='ok' and report['passed']==len(results)
