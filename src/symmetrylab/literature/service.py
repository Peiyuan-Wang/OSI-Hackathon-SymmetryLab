"""Paper survey: interest profile, arXiv retrieval, feedback ranking, drift and voice profile.

State lives in <root>/profile.json (no Git, no upload). Vectors are cached per encoder
version in <root>/vectors.json so switching encoders never mixes coordinate systems.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import threading
from symmetrylab.schemas import write_json
from . import profile as P
from .arxiv import ArxivClient, resolve
from .bond import BondClient, BondError, identities
from .encoders import get_encoder, seed_text, PHYSBERT
from .style import build_style, terms
from .personalization import preferences, writing_preferences, paper_facets, context, style_fingerprint, task_examples
from .ranking import lexical_scores

MAX_KEYWORDS, MAX_CANDIDATES, SHOWN = 12, 200, 30
EMPTY = {'keywords': [], 'papers': [], 'physics_only': True, 'candidates': {}, 'feedback': {},
         'style': None, 'style_enabled': False, 'last_search': None, 'problems': [],
         'preferences': {}, 'writing': {}, 'style_feedback': {}, 'search_round': 0,
         'search_sources': ['arxiv']}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def text_of(paper):
    return (paper['title'] + '. ' + paper.get('abstract', ''))[:2000]


class Literature:
    def __init__(self, root, client=None, encoder=None, bond_factory=BondClient):
        self.root = Path(root)
        self.client = client or ArxivClient()
        self._encoder = encoder
        self.lock = threading.Lock()
        self.bond_factory = bond_factory
        self._bond_token = ''
        self._bond_test = 'Not tested'

    def bond_token(self):
        return self._bond_token or os.environ.get('SYMMETRYLAB_BOND_TOKEN', '')

    def bond_state(self):
        return {'configured': bool(self.bond_token()), 'test': self._bond_test,
                'token_source': 'session' if self._bond_token else ('environment' if self.bond_token() else 'none')}

    def configure_sources(self, sources, token='', forget_token=False):
        if not isinstance(sources, list) or not sources or any(s not in ('arxiv', 'bond') for s in sources):
            raise ValueError('Select arXiv, Bond, or both.')
        if not isinstance(token, str) or len(token) > 8192 or any(c.isspace() for c in token):
            raise ValueError('Bond token must be one line without spaces.')
        with self.lock:
            if token or forget_token:
                self._bond_token = '' if forget_token else token
                self._bond_test = 'Not tested'
            data = self.load()
            data['search_sources'] = [s for s in ('arxiv', 'bond') if s in sources]
            self.save(data)

    def test_bond(self):
        with self.lock:
            try:
                self.bond_factory(self.bond_token()).test()
            except BondError as exc:
                self._bond_test = str(exc)
                raise
            self._bond_test = 'Authenticated list_sources call succeeded'

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
        prefs = preferences(data.get('preferences', {}))
        seeds += [{'id': 'intent:' + k, 'label': prefs[k], 'kind': 'current intent', 'priority': 4., 'text': prefs[k]}
                  for k in ('problem', 'methods', 'current_goal') if prefs[k]]
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
            prefs = preferences(data.get('preferences', {}))
            query = ' '.join(data['keywords'] + [prefs[k] for k in ('problem', 'methods', 'current_goal')]
                             + [p['title'] for p in data['papers']])
            lexical = lexical_scores(query, cands)
            maximum = max(lexical.values(), default=0) or 1.
            for c in cands:
                if c['id'] in own_ids:
                    continue
                m = P.match_paper(slots, cand_vec[c['id']], enc)
                vote = data['feedback'].get(c['id'], {}).get('vote')
                # Transparent baseline weights, not learned or calibrated probabilities.
                lexical_score = 100 * lexical[c['id']] / maximum
                score = max(0., min(100., .85 * m['score'] + .15 * lexical_score + {'up': 4, 'down': -4}.get(vote, 0)))
                ranked.append({**{k: c[k] for k in ('id', 'url', 'title', 'authors', 'published', 'categories', 'abstract', 'source', 'retrieved_via', 'doi') if k in c},
                               'score': round(score, 1), 'match': m, 'vote': vote,
                               'ranking_components': {'semantic': m['score'], 'lexical': round(lexical_score, 1), 'policy': '85% anchored similarity + 15% normalized BM25 + explicit vote'},
                               'style_selected': bool(data.get('style_feedback', {}).get(c['id']))})
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
        stale = bool(data['style']) and data['style'].get('corpus_hash') != style_fingerprint(data)
        return {'keywords': data['keywords'], 'papers': [{k: p.get(k) for k in ('id', 'title', 'url', 'source', 'published')} for p in data['papers']],
                'preferences': preferences(data.get('preferences', {})), 'writing': writing_preferences(data.get('writing', {})),
                'facets': paper_facets(data['papers']), 'style_stale': stale,
                'physics_only': data['physics_only'], 'problems': data['problems'], 'last_search': data['last_search'],
                'search_sources': data['search_sources'], 'bond': self.bond_state(),
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

    def set_profile(self, keywords, papers, physics_only=True, research_preferences=None):
        if not isinstance(keywords, list) or not isinstance(papers, list) or len(keywords) > 40 or len(papers) > 40:
            raise ValueError('keywords and papers must be short lists')
        keywords = list(dict.fromkeys(k.strip() for k in keywords if isinstance(k, str) and 1 < len(k.strip()) <= 120))[:MAX_KEYWORDS]
        entries = [p for p in papers if isinstance(p, str) and p.strip()]
        with self.lock:
            data = self.load()
            if research_preferences is not None:
                data['preferences'] = preferences(research_preferences)
            known = {e.strip() for e in data.get('paper_inputs', [])}
            resolved, problems = (resolve(entries, self.client) if {e.strip() for e in entries} != known
                                  else (data['papers'], data['problems']))
            data.update(keywords=keywords, papers=resolved, paper_inputs=entries, physics_only=bool(physics_only), problems=problems)
            self.save(data)
            return self.view(data)

    def queries(self, data):
        keywords = list(data['keywords'])
        if keywords:
            offset = (data.get('search_round', 0) * 2) % len(keywords)
            keywords = keywords[offset:] + keywords[:offset]
        own = [p for p in data['papers'] if p.get('abstract')]
        liked = [data['candidates'][pid] for pid, row in data.get('feedback', {}).items()
                 if row['vote'] == 'up' and pid in data['candidates']]
        phrase = lambda t: '"' + t + '"' if ' ' in t else t
        own_terms = [phrase(t) for t in terms(own, [], list(data['candidates'].values()), 4)] if own else []
        feedback_terms = [phrase(t) for t in terms(liked, [], list(data['candidates'].values()), 2)] if liked else []
        prefs = preferences(data.get('preferences', {}))
        intent = [phrase(t) for t in terms([{'title': ' '.join(prefs[k] for k in ('problem', 'methods', 'current_goal')), 'abstract': ''}], [], [], 2)] if any(prefs[k] for k in ('problem', 'methods', 'current_goal')) else []
        # Reserve representation for each source before filling spare query slots.
        queues = [keywords[:2], own_terms[:1], intent[:1], feedback_terms[:1], keywords[2:], own_terms[1:], intent[1:]]
        out, seen = [], set()
        for queue in queues:
            for query in queue:
                if query.lower() not in seen:
                    out.append(query); seen.add(query.lower())
                if len(out) == 6:
                    return out
        return out

    def search(self):
        with self.lock:
            data = self.load()
            queries = self.queries(data)
            if not queries:
                raise ValueError('Add interest keywords or your own papers first')
            problems, found = [], 0
            own = set().union(*(identities(p) for p in data['papers']))
            known = {key: pid for pid, paper in data['candidates'].items() for key in identities(paper)}
            clients = [('arxiv', self.client)] if 'arxiv' in data['search_sources'] else []
            if 'bond' in data['search_sources']:
                try:
                    clients.append(('bond', self.bond_factory(self.bond_token())))
                except BondError as exc:
                    problems.append(str(exc))
            counts = {source: 0 for source in data['search_sources']}
            for source, client in clients:
                for q in queries:
                    try:
                        rows = client.search(q, data['physics_only'])
                        counts[source] += len(rows)
                        for row in rows:
                            keys = identities(row)
                            if keys & own:
                                continue
                            existing = next((known[k] for k in sorted(keys) if k in known), None)
                            if existing:
                                paper = data['candidates'][existing]
                                via = paper.get('retrieved_via', ['arxiv'] if paper.get('source') == 'arXiv' else [])
                                paper['retrieved_via'] = sorted(set(via + [source]))
                                if row.get('doi') and not paper.get('doi'):
                                    paper['doi'] = row['doi']
                            else:
                                existing = row['id']
                                data['candidates'][existing] = dict(row, retrieved_via=[source], found_by=q, found_at=now())
                                found += 1
                            known.update({key: existing for key in keys})
                    except Exception as exc:
                        # Only our bounded diagnostics can reach the UI; never raw remote errors.
                        message = str(exc) if isinstance(exc, BondError) else f'{source} search failed for: {q}'
                        problems.append(message)
                        if source == 'bond':
                            break  # Do not multiply failed authentication or quota calls.
            # Keep voted papers; drop the oldest unvoted ones beyond the cap.
            if len(data['candidates']) > MAX_CANDIDATES:
                unvoted = sorted((c for c in data['candidates'].values() if c['id'] not in data['feedback'] and not data.get('style_feedback', {}).get(c['id'])), key=lambda c: c['found_at'])
                for c in unvoted[:len(data['candidates']) - MAX_CANDIDATES]:
                    del data['candidates'][c['id']]
            data['last_search'] = {'at': now(), 'queries': queries, 'new': found, 'problems': problems,
                                   'sources': data['search_sources'], 'returned_per_source': counts}
            data['search_round'] = data.get('search_round', 0) + 1
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
            liked = [data['candidates'][pid] for pid, selected in data.get('style_feedback', {}).items() if selected and pid in data['candidates']]
            writing = writing_preferences(data.get('writing', {}))
            samples = [{'id': 'approved-sample:' + P.identity(s), 'title': '', 'abstract': s['text']} for s in writing['samples']]
            # A stable background prevents unrelated new search results changing the voice.
            data['style'] = build_style(data['papers'] + samples, liked, [], data['keywords'], [], writing=writing)
            data['style']['corpus_hash'] = style_fingerprint(data)
            data['style_enabled'] = bool(enabled)
            self.save(data)
            return self.view(data)

    def set_style_enabled(self, enabled):
        with self.lock:
            data = self.load()
            if enabled and (not data['style'] or data['style'].get('corpus_hash') != style_fingerprint(data)):
                raise ValueError('Build a current voice profile first')
            data['style_enabled'] = bool(enabled)
            self.save(data)
            return self.view(data)

    def active_style(self, goal=''):
        """The prompt injected into model runs, or None."""
        data = self.load()
        if not data['style_enabled'] or not data['style']:
            return None
        if data['style'].get('corpus_hash') != style_fingerprint(data):
            raise ValueError('Voice profile is out of date. Rebuild it on Paper survey before use.')
        result = dict(data['style'])
        result['task_examples'] = task_examples(data, goal)
        result['writing'] = {k: v for k, v in writing_preferences(data.get('writing', {})).items() if k != 'samples'}
        return result

    def planning_context(self, goal=''):
        with self.lock:
            return context(self.load(), goal)

    def style_vote(self, paper_id, selected):
        if type(selected) is not bool:
            raise ValueError('Style selection must be true or false')
        with self.lock:
            data = self.load()
            if paper_id not in data['candidates']:
                raise ValueError('Unknown writing example')
            if selected:
                data['style_feedback'][paper_id] = True
            else:
                data['style_feedback'].pop(paper_id, None)
            self.save(data)
            return self.view(data)

    def set_writing(self, value):
        validated = writing_preferences(value)
        with self.lock:
            data = self.load(); data['writing'] = validated
            self.save(data)
            return self.view(data)

    def clear(self):
        with self.lock:
            self._bond_token = ''
            self._bond_test = 'Not tested'
            if self.root.exists():
                shutil.rmtree(self.root)
            return self.view(self.load())
