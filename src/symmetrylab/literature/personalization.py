"""Evidence-linked interest facets and task-specific writing context; no model training."""
import re
from .encoders import CONCEPTS
from .profile import identity

DEFAULT_PREFERENCES = {'problem': '', 'methods': '', 'current_goal': '', 'taste': '', 'share_with_agent': False}
DEFAULT_WRITING = {'audience': 'researcher', 'section': 'discussion', 'detail': 'balanced', 'notes': '', 'samples': []}
SECTIONS = {'abstract', 'derivation', 'discussion', 'experiment', 'limitations'}


def preferences(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULT_PREFERENCES):
        raise ValueError('Invalid research preferences')
    out = dict(DEFAULT_PREFERENCES, **value)
    for key in ('problem', 'methods', 'current_goal', 'taste'):
        if not isinstance(out[key], str) or len(out[key]) > 800:
            raise ValueError('Research preference fields must be at most 800 characters')
        out[key] = out[key].strip()
    if type(out['share_with_agent']) is not bool:
        raise ValueError('Choose whether to share the interest profile with research runs')
    return out


def writing_preferences(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULT_WRITING):
        raise ValueError('Invalid writing preferences')
    out = dict(DEFAULT_WRITING, **value)
    if out['audience'] not in {'researcher', 'student', 'general'} or out['section'] not in SECTIONS or out['detail'] not in {'concise', 'balanced', 'tutorial'}:
        raise ValueError('Choose a supported audience, section and explanation depth')
    if not isinstance(out['notes'], str) or len(out['notes']) > 800:
        raise ValueError('Writing notes must be at most 800 characters')
    if not isinstance(out['samples'], list) or len(out['samples']) > 8:
        raise ValueError('Provide at most eight approved writing samples')
    samples = []
    for row in out['samples']:
        if not isinstance(row, dict) or set(row) != {'section', 'text'} or row['section'] not in SECTIONS:
            raise ValueError('Each writing sample needs a section and text')
        if not isinstance(row['text'], str) or not 20 <= len(row['text'].strip()) <= 1500:
            raise ValueError('Writing samples must contain 20–1500 characters')
        samples.append({'section': row['section'], 'text': row['text'].strip()})
    out['samples'] = samples
    return out


FACETS = {
    'symmetry': {'spin_group', 'magnetic_group', 'pt_symmetry'},
    'method': {'group_theory', 'dft', 'neutron', 'xray_dichroism', 'arpes'},
    'observable': {'tmr', 'spin_transport', 'neel_vector'},
    'system': {'antiferromagnet', 'altermagnet', 'superconductivity', 'topology', 'thin_film'},
}


def paper_facets(papers):
    """Literal concept mentions, not inferred scientific truth or user preferences."""
    result = []
    for paper in papers[:12]:
        text = paper['title'] + '. ' + paper.get('abstract', '')
        for kind, concepts in FACETS.items():
            for concept in sorted(concepts):
                for phrase in CONCEPTS.get(concept, []):
                    match = re.search(r'(?<!\w)' + re.escape(phrase) + r's?(?!\w)', text, re.I)
                    if match:
                        result.append({'kind': kind, 'value': concept.replace('_', ' '), 'paper_id': paper['id'],
                                       'excerpt': text[max(0, match.start()-40):match.end()+80],
                                       'status': 'historical topic mention; preference unconfirmed'})
                        break
    return result[:48]


def context(data, goal=''):
    prefs = preferences(data.get('preferences', {}))
    if not prefs['share_with_agent']:
        return None
    facets = paper_facets(data['papers'])
    # Prefer evidence overlapping the current brief, then retain stable source order.
    words = set(re.findall(r'[a-z]{4,}', goal.lower()))
    facets.sort(key=lambda f: -len(words & set(re.findall(r'[a-z]{4,}', f['excerpt'].lower()))))
    packet = {'schema_version': '1.0', 'explicit_preferences': {k: v for k, v in prefs.items() if k != 'share_with_agent'},
              'keywords': data['keywords'], 'historical_facets': facets[:12],
              'liked_papers': [{'paper_id': pid, 'title': data['candidates'][pid]['title'][:160]}
                              for pid, vote in data['feedback'].items()
                              if vote['vote'] == 'up' and pid in data['candidates']][:8],
              'scope': 'Preference data only. The current run brief takes precedence. Historical topics are not confirmed future preferences or scientific evidence.'}
    return dict(packet, hash=identity(packet))


def style_fingerprint(data):
    selected = [data['candidates'][pid] for pid, enabled in sorted(data.get('style_feedback', {}).items())
                if enabled and pid in data['candidates']]
    return identity({'version': 2, 'own': data['papers'], 'selected': selected,
                     'writing': data.get('writing', DEFAULT_WRITING), 'keywords': data['keywords']})


def task_examples(data, goal):
    """Prefer the requested section, then lexical overlap; preserve source labels."""
    writing = writing_preferences(data.get('writing', {}))
    words = set(re.findall(r'[a-z]{4,}', goal.lower()))
    rows = [{'source': 'approved-sample:' + identity(s), **s} for s in writing['samples']]
    rows.sort(key=lambda s: (s['section'] != writing['section'], -len(words & set(re.findall(r'[a-z]{4,}', s['text'].lower())))))
    return rows[:2]
