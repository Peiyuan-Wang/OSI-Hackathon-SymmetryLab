"""Evidence-first dossier rendering with explicit calculation and proposal boundaries.

Every audience receives the same key findings, derived mechanically from checked
records. Audiences differ in how much method, notation and raw input they see.
"""
import json
from symmetrylab.verifier.orientation import check_orientation, check_axis
from symmetrylab.verifier.certificate import verify_certificate

ROTATIONS = {
    'C4z': [[0, -1, 0], [1, 0, 0], [0, 0, 1]], 'C4z^-1': [[0, 1, 0], [-1, 0, 0], [0, 0, 1]],
    'C2z': [[-1, 0, 0], [0, -1, 0], [0, 0, 1]], 'C2x': [[1, 0, 0], [0, -1, 0], [0, 0, -1]],
    'C2y': [[-1, 0, 0], [0, 1, 0], [0, 0, -1]],
}
AXIS_NAMES = {'[0, 0, 1]': '[001] (c axis)', '[0, 0, -1]': '[00-1] (c axis, reversed)', '[1, 0, 0]': '[100]',
              '[0, 1, 0]': '[010]', '[1, 1, 0]': '[110]', '[1, -1, 0]': '[1-10]'}
GLOSSARY = [
    ('Néel vector n', 'the direction along which the alternating magnetic moments of an antiferromagnet point.'),
    ('Scattering vector Q', 'the direction probed by a diffraction measurement. Neutrons only see the part of a moment perpendicular to Q.'),
    ('Orientation factor P(n,Q)', 'how strongly a moment along n contributes for probe Q (0 = invisible, 1 = maximal).'),
    ('Gauge (origin) change θ', 'shifting the momentum origin. A shift q is "trivial" if one common θ removes it for every symmetry operation.'),
    ('Certificate', 'an exact fractional witness that an independent checker re-verifies; it is not model text.'),
]


def axis(direction):
    return AXIS_NAMES.get(str(direction), str(direction))


def rotation_name(rotations):
    names = [next((k for k, v in ROTATIONS.items() if v == r), 'custom rotation') for r in rotations]
    return ' + '.join(names)


def classes(result):
    """Group candidates that give exactly identical responses."""
    parent = {x: x for x in result['labels']}
    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x
    for a, b in result['identical_pairs']:
        parent[find(a)] = find(b)
    groups = {}
    for label in result['labels']:
        groups.setdefault(find(label), []).append(label)
    return list(groups.values())


def candidate_name(result, label):
    if label.startswith('n'):
        return axis(result['inputs']['directions'][int(label[1:]) - 1])
    return 'domain mixture ' + label[len('domain_mix'):]


def calc_checked(c):
    r = c['result']
    return (check_orientation if r['kernel'] == 'collinear_neutron_orientation_v1' else check_axis)(r)


def calc_finding(c):
    r = c['result']
    if r['kernel'] == 'single_domain_director_v1':
        ok = [axis(x['direction']) for x in r['outcomes'] if x['compatible']]
        total = len(r['outcomes'])
        allowed = 'all listed axes' if len(ok) == total else ', '.join(ok) or 'none of the listed axes'
        return f"{c['calculation_id']}: assuming domain symmetry {rotation_name(r['inputs']['rotations'])}, allowed directions are {allowed} ({len(ok)}/{total})."
    groups = classes(r)
    tied = [g for g in groups if len(g) > 1]
    n_probes = len(r['inputs']['probes'])
    probe_text = f"{n_probes} probe{'s' if n_probes > 1 else ''}"
    if not tied:
        return f"{c['calculation_id']}: with {probe_text}, all {len(r['labels'])} candidates give distinct responses."
    tied_text = '; '.join(' = '.join(candidate_name(r, x) for x in g) for g in tied)
    return f"{c['calculation_id']}: with {probe_text}, {len(r['labels'])} candidates collapse to {len(groups)} distinguishable responses. Still tied: {tied_text}."


def gauge_rows(state):
    cases = {c['case_id']: c for c in state['candidates']}
    rows = []
    for cid, case in cases.items():
        entry = next((e for e in reversed(state['evidence']) if e['candidate_id'] == cid and not e.get('target_id')), None)
        if not entry:
            continue
        checked = entry['certificate_verified'] and verify_certificate(case, entry['result'])
        rows.append((case, entry['result'], checked))
    return rows


def key_findings(state):
    out = []
    if state.get('recalled_lessons'):
        out.append(f"Memory: {len(state['recalled_lessons'])} independently rechecked lesson(s) from earlier runs were loaded and changed this run's plan (see Activity).")
    for c in state['calculations']:
        if c['certificate_verified']:
            out.append(calc_finding(c))
    axis_calcs = [c for c in state['calculations'] if c['result']['kernel'] == 'single_domain_director_v1' and c['certificate_verified']]
    if len(axis_calcs) >= 2:
        counts = {sum(x['compatible'] for x in c['result']['outcomes']) for c in axis_calcs}
        if len(counts) > 1:
            out.append('Consequence: the allowed axes depend on the assumed domain symmetry, so symmetry alone does not decide the axis — it must be measured.')
    for case, result, checked in gauge_rows(state):
        theta = f" (θ = {', '.join(result['theta'])})" if result.get('theta') else ''
        label = {'gauge_trivial': 'removable by one origin change', 'gauge_nontrivial': 'a genuine obstruction'}.get(result['status'], result['status'])
        out.append(f"{case['case_id']} {case['label']}: the shift is {label}{theta}; certificate {'verified' if checked else 'NOT verified'}.")
    for claim in state['claim_checks']:
        if claim['counterexamples']:
            out.append(f"Refuted claim: \"{claim['statement']}\" — counterexample {', '.join(claim['counterexamples'])}.")
    return out


def open_questions(state):
    p = state['research_profile']
    out = []
    if p['track'] == 'experiment':
        out += ['Sample magnetic structure, propagation vector and domain populations are not established.',
                'No calibrated intensity, accessible hkl, XMLD spectrum, energy stability or experimental feasibility has been established.']
    else:
        out += ['Two finite examples do not classify all actions or establish a physical realization.',
                'Novelty and relevance of the proposed directions need expert review.']
    for c in state['calculations']:
        if c['result']['kernel'] == 'collinear_neutron_orientation_v1' and any(
                set(g) >= {'n1', 'n6'} for g in classes(c['result'])) and len(c['result']['inputs']['probes']) > 1:
            out.append('n and −n stay indistinguishable for unpolarized neutrons; polarized or another probe is required to fix the sign.')
            break
    return out


def calc_section(c, audience):
    r = c['result']
    checked = calc_checked(c)
    lines = [f"### {c['calculation_id']} — {'Allowed axes' if r['kernel'] == 'single_domain_director_v1' else 'Neutron orientation factors'}", '',
             f"Independent check: {'passed' if checked else 'FAILED'}. Material assignment: unverified.", '', calc_finding(c), '']
    if r['kernel'] == 'single_domain_director_v1':
        lines += ['| Direction | Allowed? |', '|---|---|'] + [f"| {axis(x['direction'])} | {'yes' if x['compatible'] else 'no'} |" for x in r['outcomes']]
    else:
        probes = r['inputs']['probes']
        lines += [f"`{r['formula']}`" if audience == 'researcher' else 'Values: 0 = invisible to this probe, 1 = maximal.', '',
                  '| Candidate | ' + ' | '.join('Q=' + axis(q).split(' ')[0] for q in probes) + ' |', '|---|' + '---|' * len(probes)]
        lines += ['| ' + candidate_name(r, label) + ' | ' + ' | '.join(row) + ' |' for label, row in zip(r['labels'], r['factors'])]
    lines.append('')
    if audience == 'researcher':
        lines += ['Inputs: `' + json.dumps(r['inputs'], separators=(',', ':')) + '`', '']
        lines += ['- ' + x for x in r.get('assumptions', []) + r['limitations']]
        lines.append('')
    return lines


def render_discovery(state, audience):
    p = state['research_profile']
    experiment = p['track'] == 'experiment'
    full, student = audience == 'researcher', audience == 'student'
    lines = ['# SymmetryLab — ' + ('Experimental research' if experiment else 'Theory exploration'), '',
             f"Run `{state['run_id'][:12]}` · {'offline demonstration' if state['mode'] == 'demo' else 'live model'} · {state['status'].replace('_', ' ')}", '']
    if state['mode'] == 'demo':
        lines += ['> **Scripted offline walkthrough.** No live model or network search was used in this run; the calculations are real.', '']
    lines += ['## Key findings', '']
    findings = key_findings(state)
    lines += ['- ' + x for x in findings] if findings else ['- No independently checked result was produced in this run.']
    if state.get('summary'):
        lines += ['', '**Synthesis (unverified model text):** ' + state['summary']]
    lines += ['', '## Still open', ''] + ['- ' + x for x in open_questions(state)] + ['']
    if audience == 'general':
        lines += ['## What this means', '',
                  ('The tool compared possible magnetic orientations using exact arithmetic and found which measurements could tell them apart. '
                   'It does not tell you what your sample actually does — that still requires the experiment described below.') if experiment else
                  ('The tool tested a mathematical claim on small, exactly solvable examples and found where it fails. '
                   'These are toy models: they sharpen the question but are not a physical discovery.'), '']
    if student:
        lines += ['## Concepts used', ''] + [f"- **{k}:** {v}" for k, v in GLOSSARY if experiment or 'Gauge' in k or 'Certificate' in k] + ['']
    lines += ['## Research brief', '', state['goal'], '']
    if experiment:
        lines += [f"Material: {p['material'] or 'not supplied'} · Conditions: {p['conditions'] or 'not supplied'} · Instruments: {p['instruments'] or 'not supplied'}", '']
    if state['sources'] or state['retrievals']:
        lines += ['## Sources', '']
        for s in state['sources']:
            title = s['fields'].get('title', s['record_id'])
            if isinstance(title, list):
                title = '; '.join(title)
            lines.append(f"- {s['source_id']}: [{title}]({s['url']})" + (f" — {s['scope']}" if full else ''))
        lines += [f"- Search `{r['kind']}` / {r['query']}: {r.get('status', 'pending')}" for r in state['retrievals'] if full or r.get('status') != 'retrieved']
        lines.append('')
    if state['structure_assessments'] and audience != 'general':
        lines += ['## Structure interpretation — sample assignment unverified', '']
        for a in state['structure_assessments']:
            lines += [f"{a['phase']}; {a['chemical_group']}; {a['magnetic_order']}.", '']
            lines += ['- Missing: ' + x for x in a['unresolved']] + ['']
    if state['hypotheses'] and audience != 'general':
        lines += ['## Hypotheses — unverified proposals', '']
        for h in state['hypotheses']:
            lines.append(f"- **{h['id']}:** {h['statement']}" + (' Assumptions: ' + '; '.join(h['assumptions']) + '.' if full else ''))
        lines.append('')
    rows = gauge_rows(state)
    if state['calculations'] or rows:
        lines += ['## Conditional exact calculations', '']
        if audience == 'general':
            lines += ['The individual results are listed under Key findings; the Researcher view shows full tables and inputs.', '']
        else:
            for c in state['calculations']:
                lines += calc_section(c, audience)
        if rows:
            lines += ['| Candidate | Action | Result | Certificate |', '|---|---|---|---|']
            for case, result, checked in rows:
                op = case['operations'][0]
                action = f"R={op['R']}, q={op['q']}" if audience != 'general' else case['label']
                lines.append(f"| {case['case_id']} {case['label']} | `{action}` | {result['status'].replace('_', ' ')} | {'verified' if checked else 'not verified'} |")
            lines.append('')
            if full:
                lines += ['Criterion: `(R_g − s_g I) θ ≡ q_g (mod Z^d)` for every generator; exact certificates are in the evidence JSON.', '']
    if state['taste_profile'] and audience != 'general':
        lines += ['## Research taste — provisional', '']
        lines += [f"- {x['preference']} (from {x['origin']}: \"{x['excerpt'][:120]}\")" for x in state['taste_profile']] + ['']
    if state['directions']:
        lines += ['## Proposed directions — expert review pending', '']
        for d in state['directions']:
            lines += [f"### {d['direction_id']}: {d['title']}", '', d['mechanism'], '', f"- Next test: {d['next_test']}"]
            if audience != 'general':
                lines += [f"- Falsifier: {d['falsifier']}", f"- Evidence: {', '.join(d['calculation_ids'])} · novelty {d['novelty'].replace('_', ' ')}"]
            lines.append('')
    for d in state['experiment_designs']:
        lines += ['## Proposed experiment — conditional', '', f"### {d['design_id']}: {d['method']}", '', d['hypothesis'], '',
                  '**Predictions**', ''] + ['- ' + x for x in d['predictions']] + ['']
        if audience != 'general':
            lines += ['**Steps**', ''] + [f"{i+1}. {x}" for i, x in enumerate(d['steps'])] + ['']
        if full:
            lines += ['**Controls**', ''] + ['- ' + x for x in d['controls']] + ['', '**Requirements**', ''] + ['- ' + x for x in d['requirements']] + ['']
        lines += ['Falsifier: ' + d['falsifier'], '', f"Evidence: {', '.join(d['calculation_ids'])}", '']
    if state.get('recalled_lessons'):
        lines += ['## Lessons reused from earlier runs', '']
        for x in state['recalled_lessons']:
            lines.append(f"- From run `{x['source_run'][:12]}`: {x['strategy']}")
        lines.append('')
    extra = [x for x in state['limitations'] if x not in open_questions(state)]
    if extra:
        lines += ['## Limitations', ''] + ['- ' + x for x in extra] + ['']
    m = state['metrics']
    lines += ['---', '', f"Model calls {m['model_calls']} · policy steps {m['policy_turns']} · tool calls {m['tool_calls']} · {m['elapsed_seconds']} s · reported tokens {m['reported_tokens']}", '',
              f"Evidence hash: `{state.get('evidence_hash', 'pending')}`"]
    return '\n'.join(lines)
