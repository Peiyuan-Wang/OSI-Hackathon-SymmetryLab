import json
from datetime import datetime, timedelta, timezone
import pytest
from symmetrylab.literature import profile as P
from symmetrylab.literature.arxiv import parse_feed, query_for, resolve
from symmetrylab.literature.encoders import LexiconEncoder, seed_text
from symmetrylab.literature.service import Literature
from symmetrylab.literature.style import build_style

PAPERS = {
    'arXiv:2510.04184': ('Longitudinal transport spin polarization of spin degenerate antiferromagnets',
                         'We show, using magnetic point group symmetry, that most PT-symmetric antiferromagnets can generate longitudinal spin currents due to spin-orbit coupling (SOC). Using density-functional theory we calculate the longitudinal spin conductivity of L10-MnPt and Mn2Au.'),
    'arXiv:0001.00001': ('Spin space groups and nonrelativistic spin splitting',
                         'We classify spin space groups and show how nonrelativistic spin splitting arises in collinear antiferromagnets. The symmetry analysis predicts altermagnetic band structures.'),
    'arXiv:0001.00002': ('Altermagnetic d-wave spin splitting in RuO2',
                         'Altermagnets exhibit momentum-dependent spin splitting without net magnetization. We compute the anomalous Hall conductivity of the altermagnet RuO2 from first principles.'),
    'arXiv:0001.00003': ('Giant tunneling magnetoresistance in antiferromagnetic tunnel junctions',
                         'We predict giant tunneling magnetoresistance in all-antiferromagnetic tunnel junctions based on noncollinear Mn3Sn, enabled by momentum-dependent spin polarization.'),
    'arXiv:0001.00004': ('Dark matter halo profiles in cosmological simulations',
                         'Dark matter halos in cosmological simulations show a universal density profile across galaxy masses.'),
    'arXiv:0001.00006': ('Superconducting qubits in circuit QED',
                         'Superconducting qubits coupled to microwave resonators enable circuit quantum electrodynamics with long coherence.'),
}


def row(i):
    title, abstract = PAPERS[i]
    return {'id': i, 'url': 'https://arxiv.org/abs/' + i[6:], 'title': title, 'abstract': abstract,
            'authors': ['A. Author'], 'published': '2025-10-05', 'categories': ['cond-mat.mtrl-sci'], 'source': 'arXiv'}


class FakeArxiv:
    def __init__(self):
        self.queries = []
    def search(self, q, physics_only=True, limit=25):
        self.queries.append((q, physics_only))
        return [row(i) for i in PAPERS if i != 'arXiv:2510.04184']
    def by_ids(self, ids):
        return [row('arXiv:' + i) for i in ids if 'arXiv:' + i in PAPERS]
    def get(self, params):
        return [row('arXiv:2510.04184')] if 'Longitudinal' in params.get('search_query', '') else []
    def fetch(self, *a):
        raise OSError('offline')


def survey(tmp_path):
    lit = Literature(tmp_path / 'lit', client=FakeArxiv(), encoder=LexiconEncoder())
    lit.set_profile(['spin-space groups', 'altermagnetism'], ['https://arxiv.org/abs/2510.04184v1'])
    return lit, lit.search()


def test_feed_parsing_and_physics_query():
    feed = b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2510.04184v1</id>
    <title>Longitudinal  transport</title><summary>Abstract text.</summary><published>2025-10-05T00:00:00Z</published>
    <author><name>Meng Zhu</name></author><category term="cond-mat.mtrl-sci"/></entry></feed>'''
    r = parse_feed(feed)[0]
    assert r['id'] == 'arXiv:2510.04184' and r['title'] == 'Longitudinal transport' and r['categories'] == ['cond-mat.mtrl-sci']
    with pytest.raises(ValueError):
        parse_feed(b'<!DOCTYPE x [<!ENTITY a "b">]><feed/>')
    q = query_for('"spin polarization" MnPt')
    assert q.startswith('(cat:cond-mat* OR') and 'all:"spin polarization" AND all:MnPt' in q
    assert not query_for('MnPt', physics_only=False).startswith('(')


def test_resolve_ids_titles_and_failures():
    papers, problems = resolve(['2510.04184', 'Longitudinal transport spin polarization of spin degenerate antiferromagnets',
                                'An unrelated title that does not exist', '10.1103/PhysRevB.1'], FakeArxiv())
    assert [p['id'] for p in papers] == ['arXiv:2510.04184']
    assert any('No confident' in x for x in problems) and any('DOI not found' in x for x in problems)


def test_ranking_prefers_own_field_and_excludes_own_paper(tmp_path):
    lit, v = survey(tmp_path)
    ids = [r['id'] for r in v['ranked']]
    assert 'arXiv:2510.04184' not in ids
    assert ids.index('arXiv:0001.00001') < ids.index('arXiv:0001.00004')
    assert ids[-1] in {'arXiv:0001.00004', 'arXiv:0001.00006'}
    assert v['ranked'][0]['match']['slot_id'] and v['ranked'][0]['match']['attention'] > 0
    assert lit.client.queries and all(physics for _, physics in lit.client.queries)
    assert v['last_search']['queries'][:2] == ['spin-space groups', 'altermagnetism']


def test_votes_move_anchors_flag_drift_and_undo_exactly(tmp_path):
    lit, before = survey(tmp_path)
    lit.vote('arXiv:0001.00003', 'up')
    v = lit.vote('arXiv:0001.00006', 'up')            # qubits: no anchor explains it
    assert v['drift']['unexplained_share'] == .5 and v['drift']['emerging'][0]['papers'] == ['arXiv:0001.00006']
    assert 0 < v['drift']['max_angle'] <= P.MAX_ANGLE
    liked = next(r for r in v['ranked'] if r['id'] == 'arXiv:0001.00003')
    assert liked['score'] > next(r for r in before['ranked'] if r['id'] == 'arXiv:0001.00003')['score']
    lit.vote('arXiv:0001.00003', 'none'); v = lit.vote('arXiv:0001.00006', 'none')
    assert [r['score'] for r in v['ranked']] == [r['score'] for r in before['ranked']]
    assert v['drift']['max_angle'] == 0
    v = lit.adopt('superconducting qubits')
    assert 'superconducting qubits' in v['keywords']


def test_cone_limit_and_half_life():
    a = P.unit([1., 0.]); far = P.unit([0., 1.])
    assert abs(P.dot(P.constrain(a, far), a) - __import__('math').cos(__import__('math').radians(25))) < 1e-9
    now = datetime.now(timezone.utc)
    assert abs(P.age_weight((now - timedelta(days=90)).isoformat(), now) - .5) < 1e-6
    with pytest.raises(ValueError):
        P.age_weight('2025-01-01T00:00:00', now)


def test_voice_profile_is_traceable_and_bounded(tmp_path):
    lit, _ = survey(tmp_path)
    lit.vote('arXiv:0001.00003', 'up')
    v = lit.rebuild_style()
    s = v['style']
    assert s['sources'] == {'own': ['arXiv:2510.04184'], 'liked': ['arXiv:0001.00003']}
    assert 'never overrides tool rules' in s['prompt'] and 'SOC = spin-orbit coupling' in s['prompt']
    assert 'longitudinal spin conductivity' in s['prompt'].lower() and '[arXiv:2510.04184]' in s['prompt']
    assert len(s['prompt']) <= 3500 and v['style_enabled']
    assert lit.active_style()['hash'] == s['hash']
    lit.set_style_enabled(False); assert lit.active_style() is None
    with pytest.raises(ValueError):
        build_style([], [], [], [], [])
    lit.clear(); assert not (tmp_path / 'lit').exists() and lit.state()['candidate_count'] == 0


def test_vectors_are_cached_per_encoder(tmp_path):
    lit, _ = survey(tmp_path)
    cache = json.loads((tmp_path / 'lit' / 'vectors.json').read_text())
    assert list(cache) == [LexiconEncoder.version]
    assert seed_text('altermagnetism') == 'We study altermagnetism.'


def test_physbert_separates_physics_subfields():
    pytest.importorskip('sentence_transformers')
    from symmetrylab.literature.encoders import PhysBERTEncoder
    try:
        enc = PhysBERTEncoder()
    except Exception:
        pytest.skip('PhysBERT not prepared locally')
    a, b, c = enc.encode([PAPERS['arXiv:0001.00001'][1], PAPERS['arXiv:0001.00002'][1], PAPERS['arXiv:0001.00004'][1]])
    assert P.dot(a, b) > enc.match > P.dot(a, c)
