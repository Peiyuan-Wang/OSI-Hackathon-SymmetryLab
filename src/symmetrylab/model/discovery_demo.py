"""Scripted walkthroughs of the new contracts; never presented as autonomous ideation."""
import json
from symmetrylab.model.simulated import SimulatedPolicy

DIRECTIONS=[[0,0,1],[1,0,0],[0,1,0],[1,1,0],[1,-1,0],[0,0,-1]]


class DiscoveryDemo:
    def complete(self,messages,max_tokens):
        s=json.loads(messages[-1]['content']); p=s['research_profile']
        tool=SimulatedPolicy.tool
        if not s['plan']:
            steps=(['Identify phase and sample conditions','Build competing Neel-axis hypotheses','Check assumed domain symmetry','Find measurement degeneracies','Refine geometry and propose controls'] if p['track']=='experiment' else
                   ['Infer a provisional taste profile from supplied research context','Construct a minimal falsifiable problem','Compute exact counterexamples','Compare two follow-up directions and retain a next test'])
            a={'action':'plan','steps':steps,'reason':'Scripted walkthrough; live mode chooses actions from the actual research question.'}
        elif p['track']=='experiment':
            if not s['sources'] and not s.get('material_context_loaded'):
                a=tool('load_material_context')
            elif not s['sources']:
                a={'action':'finish','summary':'No curated material context is available for this offline example. Use live source retrieval.', 'limitations':['Offline walkthrough is tailored to L10 MnPt; the sample remains unresolved.']}
            elif not s['structure_assessments']:
                a=tool('record_structure_assessment',source_ids=[x['source_id'] for x in s['sources']],phase='L10 MnPt (requested phase)',chemical_group='Published chemical reference: P4/mmm (123)',magnetic_order='Antiferromagnetic context; sample Neel direction and MSG unresolved',conditions=[p['conditions'] or 'Sample form, temperature and strain unspecified'],unresolved=['Magnetic basis, propagation vector and sample-specific symmetry','Composition, order, domains and instrument feasibility'])
            elif not s['hypotheses']:
                a={'action':'hypothesis','statement':'Several nonparallel scattering geometries may distinguish c-axis and basal-plane Neel directors in L10 MnPt under a validated collinear magnetic structure model.', 'assumptions':['Nonzero magnetic structure factors and corrected relative intensities','Sample phase, magnetic basis, domain populations and instrument access must be established']}
            elif not s['calculations']:
                a=tool('check_axis_symmetry',rotations=[[[0,-1,0],[1,0,0],[0,0,1]]],directions=DIRECTIONS)
            elif len(s['calculations'])==1:
                a=tool('calculate_orientation',directions=DIRECTIONS,probes=[[0,0,1]])
            elif len(s['calculations'])==2:
                a=tool('calculate_orientation',directions=DIRECTIONS,probes=[[1,0,0],[0,1,0],[1,1,0],[0,0,1]],domains=[[0,'1/2','1/2',0,0,0]])
            elif not s['experiment_designs']:
                a=tool('design_experiment',hypothesis='Competing c-axis and in-plane directors can have distinguishable corrected magnetic intensities; n and -n remain degenerate.',method='Conditional magnetic neutron diffraction design',source_ids=[x['source_id'] for x in s['sources']],calculation_ids=['V001','V002','V003'],
                       steps=['Measure chemical order, composition, orientation and lattice parameters before selecting a magnetic model.',
                              'Determine candidate magnetic propagation vectors and site basis; calculate nonzero accessible magnetic reflections using the sample reciprocal basis.',
                              'Choose nonparallel Q directions and collect corrected relative magnetic intensities with background and nuclear-scattering separation.',
                              'Fit competing directors and domain populations with uncertainties; compare to a second orientation-sensitive probe if available.'],
                       controls=['Independent nuclear refinement and background measurements','Multiple reflections, sample rotation and detector normalization','Strain, temperature and stoichiometry record; distinguish structural domains from magnetic domains','Do not equate zero net magnetization with absence of antiferromagnetic order'],
                       predictions=['Exact factors for the abstract Cartesian geometries appear in V002 and V003; these are not assigned Miller reflections.',
                                    'A c-axis-only Q probe cannot distinguish basal-plane axes.',
                                    'Adding basal-plane and diagonal Q can separate listed axes and a listed domain mixture, while sign-reversed directors remain identical.'],
                       falsifier='Failure of all candidate director/domain models after structure-factor and geometry corrections rejects the assumed collinear model or candidate set.',
                       requirements=[p['instruments'] or 'Confirm neutron access and sufficient magnetic scattering volume; a thin film may be signal limited.',
                                     'Validated sample magnetic basis, propagation vector, reciprocal lattice, background, resolution and domain populations.',
                                     'If neutron diffraction is impractical, evaluate XMLD with structural-dichroism controls and a sample-specific spectral model; that calculation is not implemented.'])
            else:
                a={'action':'finish','summary':'A conditional L10 MnPt dossier compares candidate Neel directors, exposes geometry and sign ambiguities, and specifies a controlled diffraction design. The input sample has not been assigned a magnetic structure.', 'limitations':['Scripted walkthrough, not a live model result.','The C4 test is a hypothetical single-domain constraint; in-plane order can break parent C4.','No calibrated intensity, accessible hkl, XMLD spectrum, energy stability or experimental feasibility has been established.']}
        else:
            origin=next((k for k in ('taste_notes','papers','keywords') if p[k].strip()),None)
            if origin and not s['taste_profile']:
                excerpt=p[origin].strip()[:200]
                a=tool('learn_taste',preferences=[{'preference':'Use the explicitly supplied research context to choose mechanisms and minimal models; this walkthrough does not infer expertise from venue.', 'origin':origin,'excerpt':excerpt}])
            elif not s['candidates']:
                a=tool('register_candidate',label='Inversion with a half shift',dimension=2,group='C2',operations=[{'R':[[-1,0],[0,-1]],'s':1,'q':['1/2',0]}])
            elif not s['claim_checks']:
                a=tool('test_claim',predicate='nonzero_q_implies_nontrivial',candidate_ids=['C001'])
            elif len(s['directions'])<2:
                i=len(s['directions'])
                a=tool('propose_direction',title=['Minimal obstructions to a common gauge','Identifiability under symmetry-equivalent descriptions'][i],
                       mechanism=['A nonzero shift can be removable; nontriviality depends on a simultaneous obstruction.','Equivalent coordinate descriptions can produce the same invariant classification.'][i],
                       minimal_model='Validated C2 affine action on T^2; the inversion certificate is one computed instance.',
                       falsifier='Enumerate valid actions and seek a certificate-backed counterexample to each sharpened predicate.',
                       next_test=['Extend from one generator to a valid two-generator action and test joint solvability.','Compare two registered actions sharing the linear representation; inspect gauge-equivalence witnesses.'][i],
                       source_ids=[],calculation_ids=['C001'],taste_alignment='Provisional connection to supplied keywords/papers; expert relevance and novelty review still required.')
            else:
                a={'action':'finish','summary':'Two scripted follow-up directions are grounded in one verified toy counterexample. Their novelty and alignment with the researcher require review.', 'limitations':['Offline policy uses fixed example directions; live mode generates question-dependent proposals.','Paper-derived taste is provisional. No expert preference labels or learning gains have been measured.']}
        return {'content':json.dumps(a),'usage':{}}
