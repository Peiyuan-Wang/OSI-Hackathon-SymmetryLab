"""Evidence-first dossier rendering with explicit calculation and proposal boundaries."""
import json
from symmetrylab.verifier.orientation import check_orientation, check_axis


def render_discovery(state,audience):
    p=state['research_profile']
    lines=['# SymmetryLab — '+('Experimental research' if p['track']=='experiment' else 'Theory exploration'),'',
           f"Run: {state['run_id']} | Policy: {state['mode']} | Workflow: {state['status']}",'',
           'A completed workflow is a conditional research dossier. It does not certify a sample assignment, experimental feasibility, or a new discovery.','',
           '## Research brief','',state['goal'],'',f"Material: {p['material'] or 'Open theoretical exploration'}",'',
           f"Conditions: {p['conditions'] or 'Not supplied'}",f"Instruments: {p['instruments'] or 'Not supplied'}",'',
           '## Reading guide','']
    guides={'researcher':'Inspect source scope, coordinate conventions, assumptions and independent certificate checks before interpreting any proposed mechanism.',
            'student':'The calculation tests a stated model. A source may support a possible structure without proving that your sample has that structure. Compare alternative explanations before choosing a measurement.',
            'general':'The report separates what was calculated from what still needs to be measured. Several magnetic arrangements can produce the same signal.'}
    lines += [guides[audience],'']
    if state['mode']=='demo':
        lines += ['**Scripted offline walkthrough. No live model or network search was used in this run.**','']
    lines += ['## Source ledger','']
    for s in state['sources']:
        title=s['fields'].get('title',s['record_id'])
        if isinstance(title,list):title='; '.join(title)
        lines += [f"- {s['source_id']}: {title} — {s['url']}", f"  Scope: {s['scope']}. Retrieval: {s['retrieval']['status']}."]
    if not state['sources']: lines+=['No sources retrieved; novelty and material structure remain unresolved.']
    for r in state['retrievals']:
        lines += [f"- Search `{r['kind']}` / {r['query']}: {r.get('status','pending')}"]
    lines += ['','## Structure interpretation — sample assignment unverified','']
    for a in state['structure_assessments']:
        lines += [a['phase'],a['chemical_group'],a['magnetic_order'],f"References: {', '.join(a['source_ids'])}",'']
        lines += ['- Condition: '+x for x in a['conditions']]
        lines += ['- Missing: '+x for x in a['unresolved']]
    lines += ['','## Hypotheses — unverified proposals','']
    for h in state['hypotheses']:
        lines += [f"### {h['id']}",'',h['statement'],''] + ['- Assumption: '+a for a in h['assumptions']]
    lines += ['','## Conditional exact calculations','']
    for c in state['calculations']:
        r=c['result']; checker=check_orientation if r['kernel']=='collinear_neutron_orientation_v1' else check_axis
        checked=checker(r)
        lines += [f"### {c['calculation_id']} — {r['kernel']}",'',f"Independent check: {'passed' if checked else 'FAILED'}. Material assignment: unverified.",'']
        if 'factors' in r:
            lines += [r['formula'],'','| Candidate | '+' | '.join('Q'+str(i+1) for i in range(len(r['inputs']['probes'])))+' |',
                      '|---|'+'---|'*len(r['inputs']['probes'])]
            lines += ['| '+label+' | '+' | '.join(row)+' |' for label,row in zip(r['labels'],r['factors'])]
            lines += ['',f"Exactly identical pairs: {r['identical_pairs']}",f"Indistinguishable with unknown common scale: {r['unknown_common_scale_pairs']}",'']
        else:
            lines += [r['scope'],'']+[f"- {x['direction']}: {'compatible' if x['compatible'] else 'incompatible'} with the assumed domain operations." for x in r['outcomes']]
        lines += ['','Inputs:','```json',json.dumps(r['inputs'],indent=2),'```','']
        lines += ['- '+x for x in r.get('assumptions',[])+r['limitations']]
    if state['evidence']:
        from symmetrylab.communication.workbench import render_agent_report
        legacy=dict(state,research_profile={'track':'legacy'})
        # Include the existing independently rechecked gauge evidence in a separate section.
        lines += ['','## Exact toy-model evidence','',render_agent_report(legacy,audience)]
    lines += ['','## Research taste — provisional, evidence-linked','']
    for pref in state['taste_profile']:
        lines += [f"- {pref['preference']}",f"  Origin: {pref['origin']}; excerpt: {pref['excerpt']}; {pref['status']}."]
    if not state['taste_profile']: lines+=['No paper-derived preference profile was produced. Supply your selected papers and interests.']
    lines += ['','## Proposed directions — expert review pending','']
    for d in state['directions']:
        lines += [f"### {d['direction_id']}: {d['title']}",'']
        lines += [f"- {k.replace('_',' ').capitalize()}: {d[k]}" for k in ('mechanism','minimal_model','falsifier','next_test','taste_alignment','novelty','expert_preference')]
        lines += [f"- Conditional evidence references: {', '.join(d['calculation_ids'])}",
                  f"- Source references: {', '.join(d['source_ids']) or 'None; literature review pending'}",'']
    lines += ['','## Experimental designs — conditional proposals','']
    for d in state['experiment_designs']:
        lines += [f"### {d['design_id']}: {d['method']}",'',d['hypothesis'],f"Evidence: {', '.join(d['calculation_ids'])}",
                  f"Sources: {', '.join(d['source_ids']) or 'None; literature review pending'}",'']
        for name in ('steps','controls','predictions','requirements'):
            lines += [f"**{name.capitalize()}**",'']+['- '+x for x in d[name]]+['']
        lines += ['Falsifier: '+d['falsifier'],'']
    lines += ['## Reused strategies','',json.dumps(state['recalled_lessons'],indent=2), '',
              '## Model synthesis — unverified','',state.get('summary') or 'Not yet produced','',
              '## Limitations','']+['- '+x for x in state['limitations']]
    lines += ['','## Run metrics','',json.dumps(state['metrics'],indent=2),'',f"Evidence hash: {state.get('evidence_hash','pending')}"]
    return '\n'.join(lines)
