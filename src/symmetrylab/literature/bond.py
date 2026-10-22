"""Bond paper metadata adapter. Retrieved text is data, never instructions."""
import hashlib
import re
from urllib.parse import urlsplit

from symmetrylab.mcp.bond import BondError, BondMCP, tool_data


def clean(value, limit=12000):
    return ' '.join(value.split())[:limit] if isinstance(value, str) else ''


def arxiv_id(value):
    value = re.sub(r'^(?:https?://arxiv.org/(?:abs|pdf)/|arxiv:|10\.48550/arxiv\.)', '', value, flags=re.I)
    value = re.sub(r'(?:v\d+)?(?:\.pdf)?$', '', value)
    return value if re.fullmatch(r'\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7}', value) else ''


def doi_id(value):
    value = re.sub(r'^(?:https?://(?:dx\.)?doi.org/|doi:)', '', clean(value), flags=re.I).lower()
    return value if re.fullmatch(r'10\.\d{4,9}/[^\s?#]+', value) else ''


def safe_url(value):
    try:
        parts = urlsplit(value)
        return value if parts.scheme in ('https', 'http') and parts.hostname and not parts.username else ''
    except ValueError:
        return ''


def strings(value):
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        value = [value] if isinstance(value, dict) else []
    return [text for item in value[:30] if (text := clean(item if isinstance(item, str) else item.get('name') if isinstance(item, dict) else ''))]


def normalize(row):
    if not isinstance(row, dict):
        return None
    title = clean(row.get('title') or row.get('name'), 1000)
    if not title:
        return None
    url = safe_url(clean(row.get('url') or row.get('@id'), 2000))
    identifiers = [clean(row.get(k)) for k in ('arxiv_id', 'doi', 'id', 'paper_id', 'identifier')]
    identifiers.append(url)
    aid = next((a for v in identifiers if (a := arxiv_id(v))), '')
    doi = next((d for v in identifiers if (d := doi_id(v))), '')
    if aid:
        ident, url = 'arXiv:' + aid, 'https://arxiv.org/abs/' + aid
    elif doi:
        ident, url = 'doi:' + doi, 'https://doi.org/' + doi
    else:
        ident = 'bond:' + hashlib.sha256((url or clean(row.get('id') or row.get('paper_id')) or title).encode()).hexdigest()[:24]
    categories = strings(row.get('categories') or row.get('category') or row.get('about'))
    return {'id': ident, 'url': url, 'title': title,
            'abstract': clean(row.get('abstract') or row.get('description')),
            'authors': strings(row.get('authors') or row.get('author'))[:10],
            'published': clean(row.get('published') or row.get('datePublished') or row.get('publication_date'), 10),
            'categories': categories, 'doi': doi, 'source': clean(row.get('source'), 100) or 'Bond',
            'retrieved_via': ['bond']}


def paper_rows(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ('papers', 'results', 'data', '@graph', 'items', 'result'):
            if isinstance(data.get(key), (dict, list)):
                return paper_rows(data[key])
    raise BondError('Bond search output is not a supported paper list; no papers were imported.')


def physics_paper(row):
    return any(re.match(r'^(cond-mat|quant-ph|physics|hep-th|math-ph)(?:[.\s:/-]|$)', c.lower())
               or c.lower() in {'condensed matter physics', 'quantum physics', 'mathematical physics'}
               for c in row['categories'])


def has_type(schema, kind):
    return isinstance(schema, dict) and (schema.get('type') == kind or
        any(has_type(option, kind) for option in schema.get('anyOf', []) + schema.get('oneOf', [])))


class BondClient:
    def __init__(self, token, mcp=None):
        self.mcp = mcp or BondMCP(token)

    def test(self):
        if 'list_sources' not in self.mcp.list_tools():
            raise BondError('Bond did not advertise list_sources.')
        tool_data(self.mcp.call('list_sources', {}))

    def search(self, phrase, physics_only=True, limit=25):
        tools = self.mcp.list_tools()
        tool = tools.get('semantic_search_papers')
        if not isinstance(tool, dict):
            raise BondError('Bond did not advertise semantic_search_papers.')
        schema = tool.get('inputSchema', {})
        props = schema.get('properties', {})
        query_key = next((k for k in ('query', 'search_query', 'query_text', 'text')
                          if has_type(props.get(k), 'string')), None)
        if not query_key:
            raise BondError('Bond search schema is not supported by this version of SymmetryLab.')
        args = {query_key: phrase}
        for key in ('limit', 'max_results', 'top_k'):
            prop = props.get(key, {})
            if has_type(prop, 'integer'):
                args[key] = min(limit, prop.get('maximum', limit))
                if args[key] < prop.get('minimum', 1):
                    raise BondError('Bond requires a result limit above this application’s bound.')
                break
        if set(schema.get('required', [])) - args.keys():
            raise BondError('Bond requires unsupported search parameters; update the integration.')
        raw = paper_rows(tool_data(self.mcp.call('semantic_search_papers', args)))
        rows = [p for row in raw[:200] if (p := normalize(row))]
        if raw and not rows:
            raise BondError('Bond paper fields are not recognized; no papers were imported.')
        return [p for p in rows if not physics_only or physics_paper(p)][:limit]


def identities(row):
    """Strong IDs only: title similarity must not collapse distinct publications."""
    keys = {row['id']}
    for value in (row.get('doi', ''), row.get('url', ''), row['id']):
        if aid := arxiv_id(value):
            keys.add('arXiv:' + aid)
        if doi := doi_id(value):
            keys.add('doi:' + doi)
    return keys
