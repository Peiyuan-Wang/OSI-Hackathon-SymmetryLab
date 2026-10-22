"""Read-only access to the original SSG Reciprocal Offline schema 3 catalog."""
import json
import sqlite3
import zlib
import sys
from pathlib import Path
from contextlib import closing


CATALOG_NAME = 'SSGReciprocalOffline-0.1.5.sqlite'
CATALOG_SHA256 = '72a371fe1d1e607c40a237d4788cfd2b5af11c06a953cafa32633c07eb25bf92'


def catalog_candidates():
    """Bundled copy first (desktop app), then a source checkout."""
    out = []
    if getattr(sys, 'frozen', False):
        exe = Path(sys.executable).resolve()
        out += [Path(getattr(sys, '_MEIPASS', exe.parent)) / 'data' / 'ssg' / CATALOG_NAME,
                exe.parent.parent / 'Resources' / 'data' / 'ssg' / CATALOG_NAME,   # macOS .app/Contents/Resources
                exe.parent / '_internal' / 'data' / 'ssg' / CATALOG_NAME]
    out.append(Path(__file__).resolve().parents[3] / 'data' / 'ssg' / CATALOG_NAME)
    return out


def default_catalog():
    candidates = catalog_candidates()
    return next((p for p in candidates if p.is_file()), candidates[0])


DEFAULT_CATALOG = default_catalog()
CONVENTION = ('k -> Rtilde k + kappa in the reciprocal basis dual to ZL0; '
              'antiunitary sign is already in Rtilde. Never multiply it a second time.')


def unpack(blob):
    decoder = zlib.decompressobj()
    raw = decoder.decompress(blob, 4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024 or not decoder.eof:
        raise ValueError('Compressed record exceeds limit or is incomplete')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Invalid record')
    return value


class SSGCatalog:
    def __init__(self, path=None):
        self.path = Path(path).expanduser().resolve() if path else DEFAULT_CATALOG

    def connect(self):
        conn = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        conn.execute('PRAGMA trusted_schema=OFF')
        return conn

    def call(self, operation, arguments):
        contracts = {'metadata': set(), 'search': {'query', 'offset', 'limit', 'parent_space_group', 'magnetic_order', 'bns_number', 'nonsymmorphic'},
                     'get': {'record_id', 'section', 'offset', 'limit'}}
        if operation not in contracts or not isinstance(arguments, dict) or set(arguments) - contracts[operation]:
            raise ValueError('Unsupported SSG operation or arguments')
        offset, limit = arguments.get('offset', 0), arguments.get('limit', 10)
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError('offset >=0 and limit 1..20 required')
        query = arguments.get('query', '')
        if not isinstance(query, str) or len(query) > 300:
            raise ValueError('query must contain at most 300 characters')
        if operation == 'get' and (not isinstance(arguments.get('record_id'), str) or not 1 <= len(arguments['record_id']) <= 100):
            raise ValueError('record_id is required')
        if not self.path.is_file():
            return {'status': 'unconfigured', 'message': 'Install the SSG SQLite catalog or set SYMMETRYLAB_SSG_CATALOG.'}
        try:
            with closing(self.connect()) as conn:
                meta = dict(conn.execute('select key,value from metadata'))
                if meta.get('schema_version') != '3':
                    raise ValueError('Unsupported SSG schema')
                result = {'status': 'ok', 'catalog': meta, 'conventions': CONVENTION,
                          'evidence_type': 'stored database data; not a newly verified physical conclusion'}
                if operation == 'metadata':
                    return dict(result, actual_record_count=conn.execute('select count(*) from ssg_records').fetchone()[0],
                                coverage='Stored representatives and parameter choices, not every continuous specialization.')
                if operation == 'get':
                    row = conn.execute('select * from ssg_records where label=?', (arguments['record_id'],)).fetchone()
                    if row is None:
                        return dict(result, status='not_found')
                    reciprocal = unpack(row['reciprocal_record_zlib'])
                    section = arguments.get('section', 'summary')
                    sections = {'summary', 'reciprocal', 'o3', 'magnetic_group', 'family_group', 'generators', 'elements'}
                    if section not in sections:
                        raise ValueError('Unknown SSG section')
                    if section == 'summary':
                        payload = {k: row[k] for k in row.keys() if not k.endswith('_zlib')}
                        payload.update({k: reciprocal.get(k) for k in ('ZL0', 'ZL0Convention', 'SourceConvention', 'OriginTest', 'RepresentationLabels', 'RepresentationComponentParameters', 'RepresentationParameterRegime')})
                    elif section == 'reciprocal':
                        payload = reciprocal
                    elif section == 'o3':
                        payload = unpack(row['o3_record_zlib'])
                    elif section in {'generators', 'elements'}:
                        key = 'ReciprocalGenerators' if section == 'generators' else 'GradedReciprocalGroupElements'
                        items = reciprocal.get(key, [])
                        payload = {'items': items[offset:offset+limit], 'total': len(items),
                                   'next_offset': offset+limit if offset+limit < len(items) else None}
                    else:
                        table, key = ('magnetic_space_group_classes', 'magnetic_class_key') if section == 'magnetic_group' else ('ordinary_space_group_classes', 'ordinary_class_key')
                        record = conn.execute(f'select record_zlib from {table} where class_key=?', (row[key],)).fetchone()
                        payload = unpack(record[0]) if record else None
                    if len(json.dumps(payload)) > 80000:
                        return dict(result, status='response_too_large', message='Use summary, generators or elements with pagination; the stored record is not truncated.')
                    return dict(result, record={'id': row['label'], 'label': row['label'], 'section': section, 'data': payload})
                clauses, params = [], []
                if query:
                    clauses.append('(instr(lower(label),lower(?))>0 or instr(lower(coalesce(magnetic_order,\'\')),lower(?))>0 or bns_number=?)')
                    params += [query, query, query]
                for key in ('parent_space_group', 'magnetic_order', 'bns_number', 'nonsymmorphic'):
                    if key not in arguments:
                        continue
                    value = arguments[key]
                    if key == 'parent_space_group' and (type(value) is not int or not 1 <= value <= 230):
                        raise ValueError('parent_space_group must be 1..230')
                    if key == 'nonsymmorphic' and type(value) is not bool:
                        raise ValueError('nonsymmorphic must be boolean')
                    if key in {'magnetic_order', 'bns_number'} and (not isinstance(value, str) or not 1 <= len(value) <= 100):
                        raise ValueError(f'{key} must be a string')
                    clauses.append(key+'=?'); params.append(value)
                where = ' where '+' and '.join(clauses) if clauses else ''
                total = conn.execute('select count(*) from ssg_records'+where, params).fetchone()[0]
                rows = conn.execute('select label,parent_space_group,magnetic_order,bns_number,nonsymmorphic,status from ssg_records'+where+' order by label limit ? offset ?', [*params, limit, offset])
                return dict(result, total=total, records=[dict(r) for r in rows], next_offset=offset+limit if offset+limit < total else None)
        except (sqlite3.Error, zlib.error, json.JSONDecodeError):
            return {'status': 'unavailable', 'message': 'The SSG catalog could not be read; no scientific inference follows.'}

    def reciprocal(self, record_id):
        """Internal full record for bounded computations, never a model-selected file path."""
        if not isinstance(record_id, str) or not 1 <= len(record_id) <= 100:
            raise ValueError('Invalid record ID')
        with closing(self.connect()) as conn:
            row = conn.execute('select reciprocal_record_zlib from ssg_records where label=?', (record_id,)).fetchone()
            if row is None:
                raise ValueError('SSG record not found')
            return unpack(row[0])
