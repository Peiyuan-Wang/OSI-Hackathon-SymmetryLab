"""Discovery contracts: retrieval, conditional calculations, proposals and taste provenance."""
from symmetrylab.verifier.orientation import orientation_scan, check_orientation, axis_constraints, check_axis
from symmetrylab.tools.sources import search_public, source_url
from symmetrylab.knowledge.mnpt import mnpt_packet
from symmetrylab.schemas import digest


def bounded_text(value, name, length=2000):
    if not isinstance(value,str) or not 1<=len(value.strip())<=length:
        raise ValueError(f'{name} must be a nonempty bounded string')
    return value.strip()


def strings(value,name):
    if not isinstance(value,list) or not 1<=len(value)<=12:
        raise ValueError(f'{name} requires 1–12 entries')
    return [bounded_text(x,name,800) for x in value]


class DiscoveryTools:
    NAMES={'search_sources','load_material_context','record_structure_assessment','calculate_orientation',
           'check_axis_symmetry','propose_direction','design_experiment','learn_taste'}

    def __init__(self, state, remaining):
        self.state, self.remaining = state, remaining

    def source_ids(self, ids):
        if not isinstance(ids,list) or len(ids)>12 or any(not isinstance(x,str) for x in ids):
            raise ValueError('source_ids must be a bounded list')
        available={s['source_id'] for s in self.state['sources']}
        if any(x not in available for x in ids):
            raise ValueError('Unknown source ID; retrieve it before citing it')
        return list(dict.fromkeys(ids))

    def add_sources(self, packet):
        added=[]
        for record in packet.get('records',[]):
            if len(self.state['sources'])>=25:
                break
            existing=next((x for x in self.state['sources'] if x['url']==record['url']),None)
            if existing:
                added.append(existing['source_id']); continue
            item=dict(record,source_id=f'S{len(self.state["sources"])+1:03d}',
                      retrieval={k:packet[k] for k in ('status','retrieved_at','reviewed_on','response_hash') if k in packet})
            self.state['sources'].append(item); added.append(item['source_id'])
        return added

    def search_sources(self, kind, query):
        if self.state['mode']=='demo':
            return {'status':'offline','message':'Offline demonstrations never perform network searches. Use live research for public metadata retrieval.'}
        if len(self.state['retrievals'])>=8:
            return {'status':'retrieval_budget_exceeded','message':'Eight public searches per run'}
        record={'kind':kind,'query':bounded_text(query,'query',300)}
        self.state['retrievals'].append(record)
        try:
            source_url(kind, query)
        except ValueError as exc:
            record.update(status='invalid_query', message=str(exc))
            return record
        try:
            packet=search_public(kind,query,timeout=self.remaining(),material=self.state['research_profile']['material'])
            self.remaining()
            ids=self.add_sources(packet)
            record.update({k:v for k,v in packet.items() if k!='records'})
            record['source_ids']=ids
        except (OSError,ValueError,RuntimeError):
            record.update(status='unavailable',message='Public source unavailable or bounded response rejected; no scientific inference follows.')
        return record

    def load_material_context(self):
        self.state["material_context_loaded"] = True
        material=self.state['research_profile']['material'].lower().replace(' ','').replace('₀','0')
        if material not in {'mnpt','l10mnpt','l10-mnpt','l1_0mnpt'}:
            return {'status':'no_curated_packet','message':'Search public structure and literature metadata for this material.'}
        packet=mnpt_packet(); ids=self.add_sources(packet)
        result={k:v for k,v in packet.items() if k!='records'}
        result['source_ids']=ids
        return result

    def record_structure_assessment(self, source_ids, phase, chemical_group, magnetic_order, conditions, unresolved):
        ids=self.source_ids(source_ids)
        if not ids:
            raise ValueError('A structure interpretation needs retrieved source references')
        entry={'source_ids':ids,'phase':bounded_text(phase,'phase'),
               'chemical_group':bounded_text(chemical_group,'chemical_group'),
               'magnetic_order':bounded_text(magnetic_order,'magnetic_order'),
               'conditions':strings(conditions,'conditions'),'unresolved':strings(unresolved,'unresolved'),
               'status':'source_linked_interpretation','sample_verified':False}
        self.state['structure_assessments'].append(entry)
        return entry

    def calculate_orientation(self, directions, probes, domains=None):
        result=orientation_scan(directions,probes,domains)
        entry=self.record_calculation(result,check_orientation(result))
        if result['identical_pairs'] or result['unknown_common_scale_pairs']:
            lesson={'kind':'orientation_identifiability','calculation_id':entry['calculation_id'],
                    'lesson':'Compare alternative axes, sign reversal and domain mixtures before claiming a unique orientation; check unknown intensity scales.',
                    'scope':'collinear_neutron_orientation_v1','verified':entry['certificate_verified']}
            self.state['lessons'].append(lesson)
        return entry

    def check_axis_symmetry(self, rotations, directions):
        result=axis_constraints(rotations,directions)
        return self.record_calculation(result,check_axis(result))

    def record_calculation(self,result,checked):
        entry={'calculation_id':f'V{len(self.state["calculations"])+1:03d}', 'result':result,
               'certificate_verified':bool(checked),'input_hash':digest(result['inputs']),
               'material_assignment':'unverified; conditional input model only'}
        self.state['calculations'].append(entry)
        return entry

    def calculation_ids(self,ids,allow_empty=False):
        if isinstance(ids,list) and not ids and allow_empty:
            return []
        if not isinstance(ids,list) or not 1<=len(ids)<=12:
            raise ValueError('Reference at least one calculation or gauge certificate')
        available={c['calculation_id'] for c in self.state['calculations'] if c['certificate_verified']}
        available.update(e['candidate_id'] for e in self.state['evidence'] if e['certificate_verified'])
        if any(not isinstance(x,str) or x not in available for x in ids):
            raise ValueError('Unknown or uncertified evidence ID')
        return ids

    def propose_direction(self,title,mechanism,minimal_model,falsifier,next_test,source_ids,calculation_ids,taste_alignment):
        entry={'direction_id':f'D{len(self.state["directions"])+1:03d}',
               'source_ids':self.source_ids(source_ids),'calculation_ids':self.calculation_ids(calculation_ids),
               'status':'unverified_research_proposal','novelty':'not_established',
               'expert_preference':'not_rated'}
        for key,value in locals().copy().items():
            if key in ('title','mechanism','minimal_model','falsifier','next_test','taste_alignment'):
                entry[key]=bounded_text(value,key)
        self.state['directions'].append(entry)
        return entry

    def design_experiment(self,hypothesis,method,source_ids,calculation_ids,steps,controls,predictions,falsifier,requirements):
        entry={'design_id':f'E{len(self.state["experiment_designs"])+1:03d}',
               'source_ids':self.source_ids(source_ids),'calculation_ids':self.calculation_ids(calculation_ids,allow_empty=True),
               'status':'conditional_design','physical_feasibility':'requires_sample_and_instrument_validation'}
        for name in ('hypothesis','method','falsifier'):
            entry[name]=bounded_text(locals()[name],name)
        for name in ('steps','controls','predictions','requirements'):
            entry[name]=strings(locals()[name],name)
        self.state['experiment_designs'].append(entry)
        return entry

    def learn_taste(self,preferences):
        if not isinstance(preferences,list) or not 1<=len(preferences)<=8:
            raise ValueError('Provide 1–8 evidence-linked preference hypotheses')
        profile=self.state['research_profile']; result=[]
        for row in preferences:
            if not isinstance(row,dict): raise ValueError('Invalid preference')
            origin=row.get('origin')
            if origin in {'papers','keywords','taste_notes'}:
                source=profile[origin]
            else:
                ids=self.source_ids([origin]); source=str(next(s['fields'] for s in self.state['sources'] if s['source_id']==ids[0]))
            excerpt=bounded_text(row.get('excerpt'),'excerpt',800)
            if excerpt not in source:
                raise ValueError('Preference excerpt must occur in the supplied text or retrieved metadata')
            result.append({'preference':bounded_text(row.get('preference'),'preference',800),
                           'origin':origin,'excerpt':excerpt,'status':'inferred_preference; researcher confirmation pending'})
        self.state['taste_profile']=result
        return {'status':'profile_proposed','preferences':result,'note':'Bibliographic history is evidence of past work, not proof of future preference.'}

    def call(self,name,arguments):
        if name not in self.NAMES or not isinstance(arguments,dict):
            raise ValueError('Unknown discovery tool or malformed arguments')
        self.remaining()
        return getattr(self,name)(**arguments)
