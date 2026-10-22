"""Scripted walkthroughs of the new contracts; never presented as autonomous ideation.

Each step carries its own reason so the activity stream explains what is being tested.
Recalled, independently rechecked lessons change the script: a refuted claim is not
re-proposed and a known degenerate measurement is not repeated.
"""
import json

DIRECTIONS = [[0, 0, 1], [1, 0, 0], [0, 1, 0], [1, 1, 0], [1, -1, 0], [0, 0, -1]]
C4Z = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
C2Z = [[-1, 0, 0], [0, -1, 0], [0, 0, 1]]
INVERSION_HALF = [{'R': [[-1, 0], [0, -1]], 's': 1, 'q': ['1/2', 0]}]
TRANSLATION_HALF = [{'R': [[1, 0], [0, 1]], 's': 1, 'q': ['1/2', 0]}]
REFUTED = 'nonzero_q_implies_nontrivial'


def tool(name, reason, **arguments):
    return {'action': 'tool', 'name': name, 'arguments': arguments, 'reason': reason}


def recalled(state, kind):
    lessons = state.get('recalled_lessons') or []
    if kind == 'gauge':
        return next((x for x in lessons if x.get('predicate') == REFUTED), None)
    return next((x for x in lessons if x.get('scope') == 'collinear_neutron_orientation_v1'
                 and len(x.get('inputs', {}).get('probes', [])) == 1), None)


class DiscoveryDemo:
    def complete(self, messages, max_tokens):
        s = json.loads(messages[-1]['content'])
        a = self.experiment(s) if s['research_profile']['track'] == 'experiment' else self.theory(s)
        return {'content': json.dumps(a), 'usage': {}}

    def experiment(self, s):
        p = s['research_profile']
        skip_c_only = recalled(s, 'orientation') is not None
        n_calc = len(s['calculations'])
        if not s['plan']:
            steps = ['Load published context for the requested phase',
                     'Test which axes each assumed domain symmetry allows',
                     'Find probe geometries that cannot tell candidate axes apart',
                     'Choose probes that separate them and design controls']
            return {'action': 'plan', 'steps': steps,
                    'reason': 'Scripted walkthrough; live mode chooses actions from the actual research question.'}
        if not s['sources'] and not s.get('material_context_loaded'):
            return tool('load_material_context', 'Collect curated published context before choosing a magnetic model.')
        if not s['sources']:
            return {'action': 'finish', 'summary': 'No curated material context is available for this offline example. Use live source retrieval.',
                    'limitations': ['Offline walkthrough is tailored to L10 MnPt; the sample remains unresolved.']}
        if not s['structure_assessments']:
            return tool('record_structure_assessment', 'Record what the sources support and what remains unknown about the sample.',
                        source_ids=[x['source_id'] for x in s['sources']], phase='L10 MnPt (requested phase)',
                        chemical_group='Published chemical reference: P4/mmm (123)',
                        magnetic_order='Antiferromagnetic context; sample Neel direction and MSG unresolved',
                        conditions=[p['conditions'] or 'Sample form, temperature and strain unspecified'],
                        unresolved=['Magnetic basis, propagation vector and sample-specific symmetry',
                                    'Composition, order, domains and instrument feasibility'])
        if not s['hypotheses']:
            return {'action': 'hypothesis',
                    'statement': 'Symmetry alone does not fix the L10 MnPt Neel axis; nonparallel scattering geometries are needed to separate c-axis and basal-plane directors.',
                    'assumptions': ['Collinear magnetic order with nonzero magnetic structure factors',
                                    'Sample phase, magnetic basis, domain populations and instrument access must be established']}
        if n_calc == 0:
            return tool('check_axis_symmetry', 'If a single domain kept the parent fourfold axis C4z, which directors survive?',
                        rotations=[C4Z], directions=DIRECTIONS)
        if n_calc == 1:
            return tool('check_axis_symmetry', 'If in-plane order lowers the domain symmetry to C2z, which directors survive?',
                        rotations=[C2Z], directions=DIRECTIONS)
        if n_calc == 2 and not skip_c_only:
            return tool('calculate_orientation', 'Test the simplest measurement: a single scattering vector along c.',
                        directions=DIRECTIONS, probes=[[0, 0, 1]])
        multi_done = any(len(c['result']['inputs'].get('probes', [])) > 1 for c in s['calculations'])
        if not multi_done:
            reason = ('Recalled lesson: a c-only probe leaves basal-plane axes degenerate, so go directly to nonparallel probes.'
                      if skip_c_only else 'Add basal-plane and diagonal probes plus a domain mixture to break the degeneracy.')
            return tool('calculate_orientation', reason, directions=DIRECTIONS,
                        probes=[[1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 1]], domains=[[0, '1/2', '1/2', 0, 0, 0]])
        ids = [c['calculation_id'] for c in s['calculations']]
        if not s['experiment_designs']:
            return tool('design_experiment', 'Turn the separating probe set into a measurement protocol with controls and a falsifier.',
                        hypothesis='Competing c-axis and in-plane directors can have distinguishable corrected magnetic intensities; n and -n remain degenerate.',
                        method='Conditional magnetic neutron diffraction design', source_ids=[x['source_id'] for x in s['sources']], calculation_ids=ids,
                        steps=['Measure chemical order, composition, orientation and lattice parameters before selecting a magnetic model.',
                               'Determine candidate magnetic propagation vectors and site basis; calculate nonzero accessible magnetic reflections using the sample reciprocal basis.',
                               'Choose nonparallel Q directions and collect corrected relative magnetic intensities with background and nuclear-scattering separation.',
                               'Fit competing directors and domain populations with uncertainties; compare to a second orientation-sensitive probe if available.'],
                        controls=['Independent nuclear refinement and background measurements', 'Multiple reflections, sample rotation and detector normalization',
                                  'Strain, temperature and stoichiometry record; distinguish structural domains from magnetic domains',
                                  'Do not equate zero net magnetization with absence of antiferromagnetic order'],
                        predictions=['A c-axis-only probe cannot distinguish basal-plane axes.',
                                     'Adding basal-plane and diagonal probes separates the listed axes and the listed domain mixture; sign-reversed directors remain identical.',
                                     'The factors are for abstract Cartesian geometries, not assigned Miller reflections.'],
                        falsifier='Failure of all candidate director/domain models after structure-factor and geometry corrections rejects the assumed collinear model or candidate set.',
                        requirements=[p['instruments'] or 'Confirm neutron access and sufficient magnetic scattering volume; a thin film may be signal limited.',
                                      'Validated sample magnetic basis, propagation vector, reciprocal lattice, background, resolution and domain populations.',
                                      'If neutron diffraction is impractical, evaluate XMLD with structural-dichroism controls and a sample-specific spectral model; that calculation is not implemented.'])
        return {'action': 'finish',
                'summary': 'Symmetry assumptions alone do not decide the L10 MnPt Neel axis: C4z allows only the c axis, C2z allows every listed axis. A c-only probe cannot separate basal-plane axes; four nonparallel probes can, except for the n / -n sign. The diffraction design follows from that probe set.',
                'limitations': ['Scripted walkthrough, not a live model result.',
                                'No calibrated intensity, accessible hkl, XMLD spectrum, energy stability or experimental feasibility has been established.']}

    def theory(self, s):
        p = s['research_profile']
        lesson = recalled(s, 'gauge')
        cands, hyps = s['candidates'], s['hypotheses']
        if not s['plan']:
            steps = (['Recheck the recalled counterexample instead of re-proposing a refuted claim',
                      'Compare it with a shift that cannot be removed',
                      'Propose two follow-up directions'] if lesson else
                     ['State a falsifiable claim about momentum shifts',
                      'Search for an exact counterexample',
                      'Revise the claim and test a contrasting action',
                      'Propose two follow-up directions'])
            return {'action': 'plan', 'steps': steps,
                    'reason': 'Scripted walkthrough; live mode chooses actions from the actual research question.'}
        origin = next((k for k in ('taste_notes', 'papers', 'keywords') if p[k].strip()), None)
        if origin and not s['taste_profile']:
            return tool('learn_taste', 'Record the supplied interests as provisional, evidence-linked preferences.',
                        preferences=[{'preference': 'Use the explicitly supplied research context to choose mechanisms and minimal models; this walkthrough does not infer expertise from venue.',
                                      'origin': origin, 'excerpt': p[origin].strip()[:200]}])
        revised = {'action': 'hypothesis',
                   'statement': 'A nonzero shift is gauge-trivial exactly when one common origin change removes every generator shift; test the joint equations, not q itself.',
                   'assumptions': ['The registered action satisfies its group relations', 'The exact certificate is independently checked']}
        if not hyps:
            if lesson:
                return dict(revised, statement='Recalled lesson: "every nonzero shift is gauge-nontrivial" is already refuted. ' + revised['statement'])
            return {'action': 'hypothesis', 'statement': 'Every nonzero momentum shift in a valid C2 action is gauge-nontrivial.',
                    'assumptions': ['Valid C2 affine action on a two-dimensional torus']}
        if not cands:
            return tool('register_candidate', 'Build the smallest candidate that could break the claim: inversion with a half shift.',
                        label='Inversion with a half shift', dimension=2, group='C2', operations=INVERSION_HALF)
        if not s['claim_checks']:
            reason = ('Recheck the recalled counterexample with the current verifier before relying on it.' if lesson
                      else 'Solve the gauge equation exactly and test the claim against this candidate.')
            return tool('test_claim', reason, predicate=REFUTED, candidate_ids=['C001'])
        if len(hyps) == 1 and not lesson:
            return revised
        if len(cands) == 1:
            return tool('register_candidate', 'Contrast: a pure translation by half a period, where no origin change can help.',
                        label='Translation by half a period', dimension=2, group='C2', operations=TRANSLATION_HALF)
        if not any(e['candidate_id'] == 'C002' for e in s['evidence']):
            return tool('solve_gauge', 'Certify that the translation shift is a genuine obstruction.', candidate_id='C002')
        if len(s['directions']) < 2:
            i = len(s['directions'])
            return tool('propose_direction', ['Propose a follow-up that extends the obstruction to two generators.',
                                              'Propose a follow-up about when different descriptions are the same action.'][i],
                        title=['Minimal obstructions to a common gauge', 'Identifiability under symmetry-equivalent descriptions'][i],
                        mechanism=['A nonzero shift can be removable (C001) or obstructed (C002); nontriviality depends on a simultaneous obstruction.',
                                   'Equivalent coordinate descriptions can produce the same invariant classification.'][i],
                        minimal_model='Validated C2 affine actions on T^2; C001 and C002 are the computed instances.',
                        falsifier='Enumerate valid actions and seek a certificate-backed counterexample to each sharpened predicate.',
                        next_test=['Extend from one generator to a valid two-generator action and test joint solvability.',
                                   'Compare two registered actions sharing the linear representation; inspect gauge-equivalence witnesses.'][i],
                        source_ids=[], calculation_ids=['C001', 'C002'],
                        taste_alignment='Provisional connection to supplied keywords/papers; expert relevance and novelty review still required.')
        return {'action': 'finish',
                'summary': 'A nonzero shift does not imply gauge nontriviality: inversion with a half shift is removable (C001), while a half-period translation is a certified obstruction (C002). The test is the joint gauge equation. Two follow-up directions build on these two instances.',
                'limitations': ['Offline policy uses fixed example directions; live mode generates question-dependent proposals.',
                                'Paper-derived taste is provisional. No expert preference labels or learning gains have been measured.']}
