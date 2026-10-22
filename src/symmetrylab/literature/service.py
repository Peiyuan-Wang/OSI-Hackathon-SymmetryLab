"""Paper survey: interest profile, arXiv retrieval, feedback ranking, drift and voice profile.

State lives in <root>/profile.json (no Git, no upload). Vectors are cached per encoder
version in <root>/vectors.json so switching encoders never mixes coordinate systems.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import threading
from symmetrylab.schemas import write_json
from . import profile as P
from .arxiv import ArxivClient, resolve
from .encoders import get_encoder, seed_text, PHYSBERT
from .style import build_style, terms

MAX_KEYWORDS, MAX_CANDIDATES, SHOWN = 12, 200, 30
EMPTY = {'keywords': [], 'papers': [], 'physics_only': True, 'candidates': {}, 'feedback': {},
         'style': None, 'style_enabled': False, 'last_search': None, 'problems': []}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def text_of(paper):
    return (paper['title'] + '. ' + paper.get('abstract', ''))[:2000]


class Literature:
    def __init__(self, root, client=None, encoder=None):
        self.root = Path(root)
        self.client = client or ArxivClient()
        self._encoder = encoder
        self.lock = threading.Lock()

    @property
    def encoder(self):
        if self._encoder is None:
            self._encoder = get_encoder()
        return self._encoder

    # ---------- persistence ----------
    def load(self):
        path = self.root / 'profile.json'
        if not path.exists():
            return json.loads(json.dumps(EMPTY))
        return {**json.loads(json.dumps(EMPTY)), **json.loads(path.read_text(encoding='utf-8'))}

    def save(self, data):
        self.root.mkdir(parents=True, exist_ok=True)
        write_json(self.root / 'profile.json', data)

    def vectors(self, texts):
        path = self.root / 'vectors.json'
        cache = json.loads(path.read_text()) if path.exists() else {}
        table = cache.setdefault(self.encoder.version, {})
        keys = [hashlib.sha256(t.encode()).hexdigest()[:24] for t in texts]
        missing = [(k, t) for k, t in zip(keys, texts) if k not in table]
        if missing:
            for (k, _), v in zip(missing, self.encoder.encode([t for _, t in missing])):
                table[k] = v
            cache = {self.encoder.version: table}  # drop vectors from other encoders
            self.root.mkdir(parents=True, exist_ok=True)
            write_json(path, cache)
        return [table[k] for k in keys]

    # ---------- model ----------
    def model(self, data):
        enc = self.encoder
        seeds = [{'id': 'k:' + k, 'label': k, 'kind': 'keyword', 'priority': 2., 'text': seed_text(k)} for k in data['keywords']]
        seeds += [{'id': 'p:' + p['id'], 'label': p['title'][:80], 'kind': 'own paper', 'priority': 3., 'text': text_of(p)} for p in data['papers']]
        if not seeds:
            return None
        cands = list(data['candidates'].values())
        vecs = self.vectors([s['text'] for s in seeds] + [text_of(c) for c in cands])
        seed_vec = {s['id']: v for s, v in zip(seeds, vecs)}
        cand_vec = {c['id']: v for c, v in zip(cands, vecs[len(seeds):])}
        slots = P.make_slots(seeds, seed_vec, enc.merge)
        feedback = [{'paper_id': pid, 'vector': cand_vec[pid], **row} for pid, row in data['feedback'].items() if pid in cand_vec]
        slots, unexplained = P.evolve(slots, feedback, enc.match)
        return slots, cands, cand_vec, feedback, unexplained

    def view(self, data):
        enc = self.encoder
        built = self.model(data)
        own_ids = {p['id'] for p in data['papers']}
        ranked, interests, drift = [], [], {'unexplained_share': 0., 'max_angle': 0., 'emerging': []}
        if built:
            slots, cands, cand_vec, feedback, unexplained = built
            for c in cands:
                if c['id'] in own_ids:
                    continue
                m = P.match_paper(slots, cand_vec[c['id']], enc)
                vote = data['feedback'].get(c['id'], {}).get('vote')
                score = max(0., min(100., m['score'] + {'up': 4, 'down': -4}.get(vote, 0)))
                ranked.append({**{k: c[k] for k in ('id', 'url', 'title', 'authors', 'published', 'categories', 'abstract') if k in c},
                               'score': round(score, 1), 'match': m, 'vote': vote})
            ranked.sort(key=lambda r: (-r['score'], r['id']))
            interests = [{'labels': s['labels'], 'kinds': s['kinds'], 'angle': s['angle'], 'observations': s['observations'],
                          'liked': s['positive_mass'], 'disliked': s['negative_mass']} for s in slots]
            ups = [f for f in feedback if f['vote'] == 'up']
            background = cands
            clusters = P.emerging(unexplained, enc.merge)
            drift = {'unexplained_share': round(len(unexplained) / len(ups), 2) if ups else 0.,
                     'max_angle': max((s['angle'] for s in slots), default=0.),
                     'emerging': [{'terms': terms([data['candidates'][r['paper_id']] for r in cl], [], background, 3) or
                                            [data['candidates'][cl[0]['paper_id']]['title'][:60]],
                                   'papers': [r['paper_id'] for r in cl]} for cl in clusters[:3]]}
        return {'keywords': data['keywords'], 'papers': [{k: p.get(k) for k in ('id', 'title', 'url', 'source', 'published')} for p in data['papers']],
                'physics_only': data['physics_only'], 'problems': data['problems'], 'last_search': data['last_search'],
                'encoder': {'kind': enc.kind, 'version': enc.version,
                            'about': PHYSBERT['about'] if enc.kind == 'physbert' else 'Built-in physics concept lexicon (offline fallback)'},
                'policy': P.POLICY, 'interests': interests, 'drift': drift,
                'ranked': ranked[:SHOWN], 'candidate_count': len(data['candidates']),
                'votes': {'up': sum(v['vote'] == 'up' for v in data['feedback'].values()),
                          'down': sum(v['vote'] == 'down' for v in data['feedback'].values())},
                'style': data['style'], 'style_enabled': data['style_enabled']}

    # ---------- actions ----------
    def state(self):
        with self.lock:
            return self.view(self.load())

    def set_profile(self, keywords, papers, physics_only=True):
        if not isinstance(keywords, list) or not isinstance(papers, list) or len(keywords) > 40 or len(papers) > 40:
            raise ValueError('keywords and papers must be short lists')
        keywords = list(dict.fromkeys(k.strip() for k in keywords if isinstance(k, str) and 1 < len(k.strip()) <= 120))[:MAX_KEYWORDS]
        entries = [p for p in papers if isinstance(p, str) and p.strip()]
        with self.lock:
            data = self.load()
            known = {e.strip() for e in data.get('paper_inputs', [])}
            resolved, problems = (resolve(entries, self.client) if {e.strip() for e in entries} != known
                                  else (data['papers'], data['problems']))
            data.update(keywords=keywords, papers=resolved, paper_inputs=entries, physics_only=bool(physics_only), problems=problems)
            self.save(data)
            return self.view(data)

    def queries(self, data):
        out = list(data['keywords'])
        own = [p for p in data['papers'] if p.get('abstract')]
        if own:
            for term in terms(own, [], list(data['candidates'].values()), 4):
                if term.lower() not in {q.lower() for q in out}:
                    out.append('"' + term + '"' if ' ' in term else term)
        return out[:6]

    def search(self):
        with self.lock:
            data = self.load()
            queries = self.queries(data)
            if not queries:
                raise ValueError('Add interest keywords or your own papers first')
            problems, found = [], 0
            own = {p['id'] for p in data['papers']}
            for q in queries:
                try:
                    for row in self.client.search(q, data['physics_only']):
                        if row['id'] not in own and row['id'] not in data['candidates']:
                            data['candidates'][row['id']] = dict(row, found_by=q, found_at=now())
                            found += 1
                except Exception:
                    problems.append(f'arXiv search failed for: {q}')
            # Keep voted papers; drop the oldest unvoted ones beyond the cap.
            if len(data['candidates']) > MAX_CANDIDATES:
                unvoted = sorted((c for c in data['candidates'].values() if c['id'] not in data['feedback']), key=lambda c: c['found_at'])
                for c in unvoted[:len(data['candidates']) - MAX_CANDIDATES]:
                    del data['candidates'][c['id']]
            data['last_search'] = {'at': now(), 'queries': queries, 'new': found, 'problems': problems}
            self.save(data)
            return self.view(data)

    def vote(self, paper_id, vote):
        if vote not in {'up', 'down', 'none'}:
            raise ValueError('vote must be up, down or none')
        with self.lock:
            data = self.load()
            if paper_id not in data['candidates']:
                raise ValueError('unknown paper')
            if vote == 'none':
                data['feedback'].pop(paper_id, None)
            else:
                data['feedback'][paper_id] = {'vote': vote, 'at': now()}
            self.save(data)
            return self.view(data)

    def adopt(self, term):
        if not isinstance(term, str) or not 1 < len(term.strip()) <= 120:
            raise ValueError('choose an emerging interest term')
        with self.lock:
            data = self.load()
            if term.strip() not in data['keywords']:
                data['keywords'] = (data['keywords'] + [term.strip()])[-MAX_KEYWORDS:]
            self.save(data)
            return self.view(data)

    def rebuild_style(self, enabled=True):
        with self.lock:
            data = self.load()
            liked = [data['candidates'][pid] for pid, v in data['feedback'].items() if v['vote'] == 'up' and pid in data['candidates']]
            view = self.view(data)
            drift = [' / '.join(e['terms']) for e in view['drift']['emerging']]
            data['style'] = build_style(data['papers'], liked, list(data['candidates'].values()), data['keywords'], drift)
            data['style_enabled'] = bool(enabled)
            self.save(data)
            return self.view(data)

    def set_style_enabled(self, enabled):
        with self.lock:
            data = self.load()
            if enabled and not data['style']:
                raise ValueError('Build the voice profile first')
            data['style_enabled'] = bool(enabled)
            self.save(data)
            return self.view(data)

    def active_style(self):
        """The prompt injected into model runs, or None."""
        data = self.load()
        return data['style'] if data['style_enabled'] and data['style'] else None

    def clear(self):
        with self.lock:
            if self.root.exists():
                shutil.rmtree(self.root)
            return self.view(self.load())
