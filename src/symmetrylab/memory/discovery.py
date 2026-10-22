"""Read-only cross-run strategy recall, regenerated from checked calculations."""
import json
from time import monotonic
from pathlib import Path
from symmetrylab.verifier.orientation import check_orientation
from symmetrylab.verifier.certificate import verify_certificate
from symmetrylab.verifier.counterexample import is_counterexample, PREDICATES


def recall_lessons(root, track, mode, limit=4):
    lessons=[]
    deadline=monotonic()+3
    paths=sorted(Path(root).glob('*/result.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:100]
    for path in paths:
        if monotonic()>deadline: break
        if path.is_symlink() or path.parent.is_symlink() or path.stat().st_size>2_000_000:
            continue
        try:
            state=json.loads(path.read_text())
            if state.get('research_profile',{}).get('track')!=track or state.get('mode')!=mode:
                continue
            cases = {c["case_id"]: c for c in state.get("candidates", [])}
            for claim in state.get("claim_checks", []):
                predicate = claim.get("predicate")
                if predicate not in PREDICATES:
                    continue
                for cid in claim.get("counterexamples", [])[:4]:
                    case = cases.get(cid)
                    evidence = next((e for e in state.get("evidence", []) if e.get("candidate_id") == cid and not e.get("target_id")), None)
                    if not case or not evidence or not verify_certificate(case, evidence["result"]):
                        continue
                    if not is_counterexample(predicate, case, evidence["result"], 1):
                        continue
                    lessons.append({"source_run":path.parent.name, "scope":"public_torus_affine_v1",
                                    "predicate":predicate, "counterexample":case,
                                    "strategy":"Validate relations, then solve for one common gauge. Test the stored counterexample before proposing this predicate again.",
                                    "status":"rechecked_conditional_counterexample"})
                    if len(lessons) >= limit:
                        return lessons
            for calculation in state.get('calculations',[]):
                result=calculation['result']
                if result.get('kernel')!='collinear_neutron_orientation_v1' or not check_orientation(result):
                    continue
                if not result['identical_pairs'] and not result['unknown_common_scale_pairs']:
                    continue
                lessons.append({'source_run':path.parent.name,'source_calculation':calculation['calculation_id'],
                                'scope':result['kernel'], 'strategy':'Test sign, alternative-axis and domain-mixture ambiguity before adding measurements. Compare proportional response vectors when the common intensity scale is unknown.',
                                'counterexamples':result['identical_pairs'],'inputs':result['inputs'],
                                'status':'rechecked_conditional_counterexample'})
                if len(lessons)>=limit: return lessons
        except (OSError,ValueError,KeyError,TypeError):
            continue
    return lessons


def recall_preferences(root, profile, limit=4):
    """Human feedback only, scoped to the exact supplied paper text and research track."""
    output=[]
    for path in sorted(Path(root).glob('*/preference_feedback.jsonl'),key=lambda p:p.stat().st_mtime,reverse=True)[:100]:
        if path.is_symlink() or path.parent.is_symlink() or path.stat().st_size>100000: continue
        try:
            result_path=path.parent/'result.json'
            if result_path.is_symlink() or result_path.stat().st_size>2_000_000: continue
            state=json.loads(result_path.read_text())
            previous=state.get('research_profile',{})
            if previous.get('track')!=profile['track'] or previous.get('papers','')!=profile['papers']:
                continue
            if not profile['papers'] and previous.get('keywords','') != profile.get('keywords',''):
                continue
            for line in reversed(path.read_text().splitlines()):
                item=json.loads(line)
                if item.get('origin')!='researcher_feedback': continue
                output.append(dict(item,source_run=path.parent.name))
                if len(output)>=limit: return output
        except (OSError,ValueError,KeyError,TypeError): continue
    return output
