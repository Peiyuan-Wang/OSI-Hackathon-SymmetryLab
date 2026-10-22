"""Bounded skill discovery and dispatch; catalog location is never model controlled."""
import os
from importlib.resources import files
from symmetrylab.database.ssg import SSGCatalog


class SkillRegistry:
    NAMES = {'list_skills', 'read_skill', 'call_skill'}

    def __init__(self, state, remaining=lambda: None):
        self.state = state
        self.remaining = remaining
        self.catalog = SSGCatalog(os.environ.get('SYMMETRYLAB_SSG_CATALOG'))

    def list_skills(self):
        return {'skills': [{'id': 'ssg-database', 'description': 'Search and retrieve SSG symmetry records for subsequent reasoning and calculations.',
                            'configured': self.catalog.path.is_file(), 'operations': ['metadata', 'search', 'get', 'momentum_orbit', 'verify_group']}]}

    def read_skill(self, skill):
        if skill != 'ssg-database':
            raise ValueError('Unknown skill')
        return {'id': skill, 'instructions': files('symmetrylab.skills').joinpath('ssg-database/SKILL.md').read_text(encoding='utf-8')}

    def call_skill(self, skill, operation, arguments):
        if skill != 'ssg-database':
            raise ValueError('Unknown skill')
        if operation in {'momentum_orbit', 'verify_group'}:
            from symmetrylab.verifier.ssg import calculate
            from symmetrylab.schemas import digest
            if not isinstance(arguments, dict):
                raise ValueError('Skill arguments must be an object')
            record_id = arguments.get('record_id')
            provenance = self.call_skill(skill, 'get', {'record_id': record_id})
            if provenance['status'] != 'ok':
                return provenance
            record = self.catalog.reciprocal(record_id)
            result = calculate(record, operation, arguments, self.remaining)
            entries = self.state.setdefault('skill_calculations', [])
            result = dict(result, calculation_id=f'SSG{len(entries)+1:03d}', record_id=record_id,
                          operation=operation, record_hash=digest(record), catalog=provenance['catalog'],
                          source_ids=provenance['source_ids'])
            entries.append(result)
            return result
        result = self.catalog.call(operation, arguments)
        if operation == 'get' and result['status'] == 'ok':
            from symmetrylab.schemas import digest
            key = digest({'catalog': result['catalog'], 'record': result['record']})
            sources = self.state.setdefault('sources', [])
            url = 'urn:symmetrylab:ssg:' + key
            existing = next((s for s in sources if s['url'] == url), None)
            if existing is None and len(sources) < 25:
                existing = {'source_id': f'S{len(sources)+1:03d}', 'record_id': result['record']['id'], 'url': url, 'kind': 'ssg_database',
                            'scope': 'Symmetry database entry; not a verified derived physical claim.',
                            'fields': {'title': result['record']['label'], 'catalog': result['catalog'], 'record': result['record']}}
                sources.append(existing)
            result = dict(result, source_ids=[existing['source_id']] if existing else [],
                          provenance_status='recorded' if existing else 'source_budget_exceeded')
        return result

    def call(self, name, arguments):
        if name not in self.NAMES or not isinstance(arguments, dict):
            raise ValueError('Unknown skill tool or invalid arguments')
        return getattr(self, name)(**arguments)
