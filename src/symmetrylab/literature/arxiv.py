"""arXiv candidate search and resolution of the researcher's own papers.

Only titles, keywords and identifiers are sent to arXiv / Crossref. Requests are spaced
3 seconds apart, as the arXiv API terms ask.
"""
import hashlib
import json
import re
import time
from urllib.parse import urlencode, quote
import xml.etree.ElementTree as ET
from symmetrylab.tools.sources import fetch_bytes, ATOM, ARXIV_DOI

PHYSICS = ['cond-mat*', 'quant-ph', 'physics*', 'hep-th', 'math-ph']
ARXIV_ID = re.compile(r'(?:arxiv[:\s/]*|abs/|pdf/)?(\d{4}\.\d{4,5})(?:v\d+)?', re.I)


def parse_feed(body):
    if b'<!DOCTYPE' in body or b'<!ENTITY' in body:
        raise ValueError('Unexpected arXiv response')
    rows = []
    for entry in ET.fromstring(body.decode('utf-8')).findall(ATOM + 'entry'):
        ident = (entry.findtext(ATOM + 'id') or '').rsplit('/abs/', 1)[-1]
        base = re.sub(r'v\d+$', '', ident)
        if not re.fullmatch(r'\d{4}\.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7}', base):
            continue
        rows.append({'id': 'arXiv:' + base, 'url': 'https://arxiv.org/abs/' + base,
                     'title': ' '.join((entry.findtext(ATOM + 'title') or '').split()),
                     'abstract': ' '.join((entry.findtext(ATOM + 'summary') or '').split()),
                     'authors': [a.findtext(ATOM + 'name') for a in entry.findall(ATOM + 'author')][:10],
                     'published': (entry.findtext(ATOM + 'published') or '')[:10],
                     'categories': [c.get('term') for c in entry.findall(ATOM + 'category')][:6],
                     'source': 'arXiv'})
    return rows


def query_for(phrase, physics_only=True):
    words = re.findall(r'"[^"]{2,80}"|[A-Za-z0-9][A-Za-z0-9.+_\-]{1,40}', phrase)[:6]
    if not words:
        raise ValueError('empty search phrase')
    text = ' AND '.join('all:' + (w if w.startswith('"') else w) for w in words)
    if physics_only:
        text = '(' + ' OR '.join('cat:' + c for c in PHYSICS) + ') AND ' + text
    return text


class ArxivClient:
    def __init__(self, fetch=fetch_bytes, sleep=time.sleep, spacing=3.):
        self.fetch, self.sleep, self.spacing, self.last = fetch, sleep, spacing, None

    def get(self, params):
        if self.last is not None:
            self.sleep(self.spacing)
        self.last = True
        return parse_feed(self.fetch('https://export.arxiv.org/api/query?' + urlencode(params), 30, 'application/atom+xml'))

    def search(self, phrase, physics_only=True, limit=25):
        return self.get({'search_query': query_for(phrase, physics_only), 'max_results': limit, 'sortBy': 'relevance'})

    def by_ids(self, ids):
        return self.get({'id_list': ','.join(ids), 'max_results': len(ids)}) if ids else []


def jaccard(a, b):
    a, b = set(re.findall(r'[a-z0-9]{3,}', a.lower())), set(re.findall(r'[a-z0-9]{3,}', b.lower()))
    return len(a & b) / len(a | b) if a | b else 0.


def resolve(entries, client):
    """Each entry: arXiv ID/URL, DOI, a pasted abstract (>200 chars) or a title."""
    papers, problems, ids = [], [], []
    for raw in entries[:12]:
        text = raw.strip()
        if not text:
            continue
        doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', text, flags=re.I)
        arxiv = ARXIV_ID.search(text) if len(text) < 120 else None
        if ARXIV_DOI.fullmatch(doi):
            ids.append(ARXIV_DOI.fullmatch(doi).group(1))
        elif arxiv and not re.fullmatch(r'10\.\d{4,9}/\S+', doi):
            ids.append(arxiv.group(1))
        elif re.fullmatch(r'10\.\d{4,9}/[^\s?#]{1,200}', doi):
            try:
                row = json.loads(client.fetch('https://api.crossref.org/works/' + quote(doi, safe=''), 20))['message']
                papers.append({'id': 'doi:' + doi, 'url': 'https://doi.org/' + doi, 'title': ' '.join(row.get('title', [''])),
                               'abstract': re.sub(r'<[^>]+>', ' ', row.get('abstract', '')).strip(), 'source': 'Crossref',
                               'published': '-'.join(str(x) for x in (row.get('published', {}).get('date-parts') or [['']])[0])})
            except Exception:
                problems.append(f'DOI not found in Crossref: {doi}')
        elif len(text) > 200:
            papers.append({'id': 'text:' + hashlib.sha256(text.encode()).hexdigest()[:12], 'url': '', 'title': text[:90] + '…',
                           'abstract': text, 'source': 'pasted text'})
        else:
            try:
                rows = client.get({'search_query': 'ti:"' + text.replace('"', '') + '"', 'max_results': 3})
            except Exception:
                rows = []
            best = max(rows, key=lambda r: jaccard(r['title'], text), default=None)
            if best and jaccard(best['title'], text) >= .6:
                papers.append(dict(best, matched_from_title=True))
            else:
                problems.append(f'No confident arXiv match for title: {text[:80]}')
    if ids:
        try:
            found = client.by_ids(list(dict.fromkeys(ids)))
            papers += found
            missing = set(ids) - {p['id'].split(':', 1)[1] for p in found}
            problems += [f'arXiv ID not found: {x}' for x in sorted(missing)]
        except Exception:
            problems.append('arXiv unavailable while resolving IDs')
    unique = {p['id']: p for p in papers}
    return list(unique.values()), problems
