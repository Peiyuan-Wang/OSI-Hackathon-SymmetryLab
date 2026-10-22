"""Anchored multi-interest profile with attention routing and reversible feedback.

Ported from Newspaper's semantic_profile.py (anchored-multi-interest-v1):
- Seeds (keywords, the researcher's own papers) are merged by complete linkage into slots.
- Q = slot anchor, K = V = paper vector. attention = softmax(cos(anchor, x) / T) assigns
  each feedback item to slots; likes/dislikes then move the slot vector Rocchio-style:
  p = unit(a + 0.75 P - 0.35 N), clamped to a 25-degree cone around the anchor.
- Rebuilt from the current feedback log every time, so undo/replace is exact.
Added here: interest-drift detection. Likes that no anchor explains (low attention
support) are clustered into "emerging interests" instead of being forced into a slot.
No encoder or Wq/Wk/Wv is trained.
"""
from datetime import datetime, timezone
import hashlib
import json
import math

POLICY = 'symmetrylab-anchored-multi-interest-v1 (from newspaper anchored-multi-interest-v1)'
ATTENTION_TEMPERATURE = .12
NEIGHBOURHOOD = .12
PRIOR = 3.
MAX_ANGLE = 25.
HALF_LIFE_DAYS = 90.


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def unit(vector):
    length = math.sqrt(sum(v * v for v in vector))
    if not math.isfinite(length) or length < 1e-9:
        raise ValueError('zero or invalid vector')
    return [v / length for v in vector]


def dot(a, b):
    if len(a) != len(b):
        raise ValueError('vectors from different encoders are not comparable')
    return max(-1., min(1., sum(x * y for x, y in zip(a, b))))


def mean(vectors, weights=None):
    weights = weights or [1.] * len(vectors)
    return unit([sum(w * v[i] for v, w in zip(vectors, weights)) for i in range(len(vectors[0]))])


def make_slots(seeds, vectors, merge):
    """seeds: [{id, label, kind, priority}]. Complete linkage avoids chaining distant topics."""
    clusters = [[s] for s in seeds]
    while True:
        best = None
        for i, a in enumerate(clusters):
            for j in range(i + 1, len(clusters)):
                similarity = min(dot(vectors[x['id']], vectors[y['id']]) for x in a for y in clusters[j])
                if similarity >= merge and (best is None or similarity > best[0]):
                    best = similarity, i, j
        if best is None:
            break
        clusters[best[1]] += clusters.pop(best[2])
    slots = []
    for members in clusters:
        anchor = mean([vectors[s['id']] for s in members], [s['priority'] for s in members])
        slots.append({'id': identity(sorted(s['id'] for s in members)), 'labels': [s['label'] for s in members],
                      'kinds': sorted({s['kind'] for s in members}), 'anchor': anchor, 'vector': list(anchor),
                      'positive_mass': 0., 'negative_mass': 0., 'observations': 0, 'angle': 0., 'affinity_bias': 0.})
    return slots


def route(slots, vector, match):
    """Attention over slots whose anchor is close enough; [] means no anchor explains the item."""
    scored = [(s, dot(s['anchor'], vector)) for s in slots]
    scored = [(s, c) for s, c in scored if c >= match]
    if not scored:
        return []
    top = max(c for _, c in scored)
    scored = [(s, c) for s, c in scored if c >= top - NEIGHBOURHOOD]
    weights = [math.exp((c - top) / ATTENTION_TEMPERATURE) for _, c in scored]
    total = sum(weights)
    return [(s, w / total, c) for (s, c), w in zip(scored, weights)]


def constrain(anchor, proposal):
    cosine = dot(anchor, proposal)
    limit = math.radians(MAX_ANGLE)
    if cosine >= math.cos(limit):
        return proposal
    tangent = [p - cosine * a for p, a in zip(proposal, anchor)]
    if sum(v * v for v in tangent) < 1e-12:
        return list(anchor)
    tangent = unit(tangent)
    return unit([math.cos(limit) * a + math.sin(limit) * t for a, t in zip(anchor, tangent)])


def age_weight(at, now):
    when = datetime.fromisoformat(at)
    if when.tzinfo is None:
        raise ValueError('feedback timestamps need a timezone')
    return 2 ** (-max(0., (now - when).total_seconds() / 86400) / HALF_LIFE_DAYS)


def evolve(slots, feedback, match, now=None):
    """feedback: [{vector, vote: up|down, at}]. Returns (slots, unexplained likes)."""
    now = now or datetime.now(timezone.utc)
    totals = {s['id']: {'positive': [0.] * len(s['anchor']), 'negative': [0.] * len(s['anchor']),
                        'positive_mass': 0., 'negative_mass': 0., 'observations': 0} for s in slots}
    unexplained = []
    for row in feedback:
        weight = age_weight(row['at'], now)
        routing = route(slots, row['vector'], match)
        if not routing:
            if row['vote'] == 'up':
                unexplained.append(row)
            continue
        sign = 'negative' if row['vote'] == 'down' else 'positive'
        for slot, attention, _ in routing:
            acc = totals[slot['id']]
            w = weight * attention
            acc[sign] = [a + w * x for a, x in zip(acc[sign], row['vector'])]
            acc[sign + '_mass'] += w
            acc['observations'] += 1
    result = []
    for slot in slots:
        acc = totals[slot['id']]
        pos = [v / (PRIOR + acc['positive_mass']) for v in acc['positive']]
        neg = [v / (PRIOR + acc['negative_mass']) for v in acc['negative']]
        proposal = unit([a + .75 * p - .35 * n for a, p, n in zip(slot['anchor'], pos, neg)]) if acc['observations'] else list(slot['anchor'])
        vector = constrain(slot['anchor'], proposal)
        result.append({**slot, 'vector': vector, 'positive_mass': round(acc['positive_mass'], 4),
                       'negative_mass': round(acc['negative_mass'], 4), 'observations': acc['observations'],
                       'affinity_bias': .08 * acc['positive_mass'] / (PRIOR + acc['positive_mass'])
                                        - .15 * acc['negative_mass'] / (PRIOR + acc['negative_mass']),
                       'angle': round(math.degrees(math.acos(dot(slot['anchor'], vector))), 2)})
    return result, unexplained


def emerging(unexplained, merge):
    """Cluster likes outside every anchor; each cluster is a candidate new interest."""
    clusters = []
    for row in unexplained:
        for cluster in clusters:
            if min(dot(row['vector'], other['vector']) for other in cluster) >= merge * .8:
                cluster.append(row)
                break
        else:
            clusters.append([row])
    return sorted(clusters, key=len, reverse=True)


def match_paper(slots, vector, encoder):
    routing = route(slots, vector, encoder.match)
    if not routing:
        best = max(slots, key=lambda s: dot(s['vector'], vector)) if slots else None
        cosine = dot(best['vector'], vector) if best else 0.
        return {'slot_id': None, 'labels': best['labels'] if best else [], 'cosine': round(cosine, 4),
                'score': round(max(0, min(100, (cosine - encoder.floor) / encoder.span * 100)) * .5, 1), 'attention': 0.}
    best, attention, _ = max(routing, key=lambda r: dot(r[0]['vector'], vector) + r[0]['affinity_bias'])
    cosine = dot(best['vector'], vector)
    effective = max(-1., min(1., cosine + best['affinity_bias']))
    return {'slot_id': best['id'], 'labels': best['labels'], 'cosine': round(cosine, 4),
            'anchor_cosine': round(dot(best['anchor'], vector), 4), 'attention': round(attention, 3),
            'score': round(max(0, min(100, (effective - encoder.floor) / encoder.span * 100)), 1)}
