"""Bounded public metadata retrieval. Never fetch model-supplied URLs or execute text."""
from datetime import datetime, timezone
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlencode, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


ARXIV_DOI = re.compile(r'10\.48550/arxiv\.(\d{4}\.\d{4,5})(v\d+)?', re.I)
ATOM = '{http://www.w3.org/2005/Atom}'


def fetch_bytes(url, timeout=10, accept='application/json'):
    req = Request(url, headers={'User-Agent':'SymmetryLab/0.3 (public scientific metadata)', 'Accept':accept})
    with build_opener(NoRedirect).open(req, timeout=max(.1,min(20,timeout))) as response:
        body = response.read(2_000_001)
    if len(body)>2_000_000:
        raise ValueError('Source response exceeded the bounded size; narrow the search')
    return body


def fetch_json(url, timeout=10):
    body = fetch_bytes(url, timeout)
    if url.startswith('https://export.arxiv.org/'):
        if b'<!DOCTYPE' in body or b'<!ENTITY' in body:
            raise ValueError('Unexpected arXiv response')
        return {'atom': body.decode('utf-8')}
    return json.loads(body)


def arxiv_query(text):
    """Free text -> AND of all: terms; quoted phrases are kept together."""
    terms = re.findall(r'"([^"]{1,80})"|([A-Za-z0-9][A-Za-z0-9.+_-]{1,40})', text)
    words = [a or b for a, b in terms][:6]
    if not words:
        raise ValueError('arXiv search needs at least one word, e.g. MnPt "spin polarization"')
    return ' AND '.join('all:' + (f'"{w}"' if ' ' in w else w) for w in words)


def parse_arxiv(atom):
    rows = []
    for entry in ET.fromstring(atom).findall(ATOM + 'entry')[:8]:
        ident = (entry.findtext(ATOM + 'id') or '').rsplit('/abs/', 1)[-1]
        base = re.sub(r'v\d+$', '', ident)
        if not re.fullmatch(r'\d{4}\.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7}', base):
            continue
        rows.append({'provider':'arXiv','record_id':'arXiv:' + base,'url':'https://arxiv.org/abs/' + base,
                     'fields':{'title':' '.join((entry.findtext(ATOM + 'title') or '').split()),
                               'author':[a.findtext(ATOM + 'name') for a in entry.findall(ATOM + 'author')][:12],
                               'published':(entry.findtext(ATOM + 'published') or '')[:10],
                               'abstract':' '.join((entry.findtext(ATOM + 'summary') or '').split()),
                               'type':'preprint','doi':'10.48550/arXiv.' + base},
                     'scope':'arXiv preprint metadata and abstract only; not peer reviewed unless stated; full text not retrieved'})
    return rows


def hill_formula(value):
    compact = value.replace(' ', '')
    parts = re.findall(r'([A-Z][a-z]?)(\d*)', compact)
    if not parts or ''.join(a+b for a,b in parts) != compact:
        raise ValueError('Use a simple elemental formula such as MnPt, or choose text search')
    elements = set('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og'.split())
    if any(atom not in elements or (count and not 1 <= int(count) <= 9999) for atom,count in parts):
        raise ValueError('Use valid element symbols and positive bounded counts')
    counts = {}
    for atom, count in parts:
        counts[atom] = counts.get(atom,0)+int(count or 1)
    order = sorted(counts, key=lambda x:(0 if x=='C' else 1 if x=='H' else 2,x)) if 'C' in counts else sorted(counts)
    return ' '.join(x+(str(counts[x]) if counts[x]!=1 else '') for x in order)


def source_url(kind, query):
    """Validate a structured search before any network request."""
    if not isinstance(query,str) or not 1<=len(query.strip())<=300:
        raise ValueError('Query must contain 1–300 characters')
    if kind == 'structure_formula':
        url = 'https://www.crystallography.net/cod/result?'+urlencode({'formula':hill_formula(query),'format':'json'})
    elif kind == 'structure_text':
        url = 'https://www.crystallography.net/cod/result?'+urlencode({'text':query,'format':'json'})
    elif kind == 'literature':
        url = 'https://api.crossref.org/works?'+urlencode({'query.bibliographic':query,'rows':8,
                                                         'filter':'type:journal-article,type:posted-content,type:proceedings-article'})
    elif kind == 'arxiv':
        url = 'https://export.arxiv.org/api/query?'+urlencode({'search_query':arxiv_query(query),'max_results':8,'sortBy':'relevance'})
    elif kind == 'doi':
        query = re.sub(r'^https?://(dx\.)?doi\.org/', '', query.strip(), flags=re.I)
        if not re.fullmatch(r'10\.\d{4,9}/[^\s?#]{1,200}',query):
            raise ValueError('Supply a DOI such as 10.1103/PhysRevB.104.144403')
        arxiv = ARXIV_DOI.fullmatch(query)
        # arXiv DOIs are registered with DataCite, not Crossref; resolve them through arXiv.
        url = ('https://export.arxiv.org/api/query?'+urlencode({'id_list':arxiv.group(1)}) if arxiv
               else 'https://api.crossref.org/works/'+quote(query,safe=''))
    else:
        raise ValueError('Source kind must be structure_formula, structure_text, literature, arxiv or doi')
    return url


def search_public(kind, query, timeout=10, fetch=fetch_json, material=''):
    url = source_url(kind, query)
    raw = fetch(url, timeout)
    records = []
    if isinstance(raw, dict) and 'atom' in raw:
        records = parse_arxiv(raw['atom'])
    elif kind.startswith('structure'):
        if not isinstance(raw,list):
            raise ValueError('Unexpected COD response')
        for row in raw[:5]:
            if not isinstance(row,dict): continue
            cid = str(row.get('file',''))
            fields = {k: row[k] for k in ('formula','sg','sgHall','a','b','c','alpha','beta','gamma','title','year','doi','temperature') if k in row}
            records.append({'provider':'COD','record_id':cid,'url':f'https://www.crystallography.net/cod/{cid}.html' if re.fullmatch(r'\d{7}',cid) else url,
                            'fields':fields,'scope':'Chemical structure metadata; phase match and magnetic structure unresolved'})
    else:
        if not isinstance(raw,dict) or not isinstance(raw.get('message'),dict):
            raise ValueError('Unexpected bibliographic response')
        rows = [raw.get('message',{})] if kind=='doi' else raw.get('message',{}).get('items',[])
        if not isinstance(rows,list):
            raise ValueError('Unexpected bibliographic result list')
        for row in rows[:8]:
            if not isinstance(row,dict):
                raise ValueError('Unexpected bibliographic record')
            doi = row.get('DOI','')
            if not isinstance(doi,str):
                raise ValueError('Invalid DOI metadata')
            # Supporting-information files (type "component", DOI suffix .s001) are not papers.
            if row.get('type') == 'component' or re.search(r'\.s\d{3}$', doi):
                continue
            records.append({'provider':'Crossref','record_id':doi,'url':'https://doi.org/'+quote(doi,safe='/'),
                            'fields':{k:row[k] for k in ('title','author','published','abstract','container-title','type') if k in row},
                            'scope':'Bibliographic metadata and supplied abstract only; full text not retrieved'})
    # Bound metadata passed to the policy without claiming full-text coverage.
    for record in records:
        record['mentions_material'] = mentions(material, record['fields'])
        for key,value in list(record['fields'].items()):
            if len(json.dumps(value))>6000:
                record['fields'][key]=str(value)[:6000]+' [truncated]'
    relevant = sum(r['mentions_material'] is not False for r in records)
    return {'status':'retrieved' if records else 'no_results','query':query,'kind':kind,'request_url':url,
            'relevant_records':relevant,
            'retrieved_at':datetime.now(timezone.utc).isoformat(),'response_hash':hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest(),
            'records':records, 'limit':5, 'untrusted_source_text':True}


def mentions(material, fields):
    """True/False when the title or abstract names the material; None when no material was given."""
    core = re.sub(r'(?i)^l1[_]?0[- ]?|[^A-Za-z0-9]', '', material or '')
    if not core:
        return None
    text = json.dumps([fields.get('title', ''), fields.get('abstract', '')], ensure_ascii=False)
    return bool(re.search(r'(?<![A-Za-z])' + re.escape(core) + r'(?![a-z])', text, re.I))
