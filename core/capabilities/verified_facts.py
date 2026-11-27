"""Shared business-fact input contract. Approval is human, not proof of truth.

Only approved demo facts may flow into deterministic consumers. Unknown or
conflicting fields remain unavailable. Never infer approval from an AI output.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlsplit

MAX_BYTES = 32000
STATUSES = {'approved_for_demo', 'source_verified_for_demo', 'unverified', 'conflicting'}
KINDS = {'owner', 'official_site', 'directory', 'user', 'synthetic'}
REQUIRED = ('name', 'category', 'city')
OPTIONAL = ('address', 'phone', 'tagline', 'whatsapp')


def strict_json(raw: str):
    if len(raw.encode('utf-8')) > MAX_BYTES:
        raise ValueError('JSON input exceeds bound')
    def pairs(items):
        result = {}
        for key, val in items:
            if key in result:
                raise ValueError(f'Duplicate key: {key}')
            result[key] = val
        return result
    def constant(value):
        raise ValueError(f'Invalid JSON constant: {value}')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def exact_keys(obj, required, optional=()):
    if not isinstance(obj, dict) or not set(required) <= obj.keys() or obj.keys() - set(required) - set(optional):
        raise ValueError('Unexpected or missing object fields')


def clean_text(value, limit=180):
    if (not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > limit
            or any(unicodedata.category(c) in {'Cc', 'Cf', 'Cs'} for c in value)):
        raise ValueError('Invalid or oversized text field')
    return value


@dataclass(frozen=True)
class Fact:
    value: str
    status: str
    source_kind: str
    source_reference: str

    @classmethod
    def parse(cls, raw, *, phone=False):
        exact_keys(raw, ('value', 'status', 'source'))
        exact_keys(raw['source'], ('kind', 'reference'))
        value = clean_text(raw['value'])
        status = raw['status']
        kind = raw['source']['kind']
        reference = clean_text(raw['source']['reference'], 500)
        if status not in STATUSES or kind not in KINDS:
            raise ValueError('Unknown status or source kind')
        if status == 'source_verified_for_demo' and kind != 'official_site':
            raise ValueError('Source-verified demo facts need a reviewed first-party source')
        if kind in {'official_site', 'directory'}:
            u = urlsplit(reference)
            if u.scheme not in {'http', 'https'} or not u.hostname or u.username or u.password:
                raise ValueError('Web evidence needs a public-source URL (not fetched here)')
        if phone and not re.fullmatch(r'\+[1-9][0-9]{7,14}', value):
            raise ValueError('Phone must use E.164 format')
        return cls(value, status, kind, reference)

    @property
    def usable(self):
        return self.status in {'approved_for_demo', 'source_verified_for_demo'}


@dataclass(frozen=True)
class BusinessFacts:
    language: str
    fields: tuple[tuple[str, Fact], ...]
    services: tuple[Fact, ...]

    @classmethod
    def parse(cls, raw):
        exact_keys(raw, ('version', 'language', 'facts'), ('services',))
        if type(raw['version']) is not int or raw['version'] != 1 or raw['language'] not in ('he', 'en'):
            raise ValueError('Unsupported facts version or language')
        exact_keys(raw['facts'], REQUIRED, OPTIONAL)
        fields = tuple((k, Fact.parse(v, phone=k in {'phone', 'whatsapp'})) for k, v in sorted(raw['facts'].items()))
        for k, fact in fields:
            if k in REQUIRED and not fact.usable:
                raise ValueError(f'Required business fact not approved: {k}')
        services = raw.get('services', [])
        if not isinstance(services, list) or len(services) > 12:
            raise ValueError('Services must be a bounded list')
        service_facts = tuple(Fact.parse(item) for item in services)
        if len({x.value.casefold() for x in service_facts}) != len(service_facts):
            raise ValueError('Duplicate service facts')
        return cls(raw['language'], fields, service_facts)

    def render_data(self):
        """The only business content allowed in the verified-layout renderer."""
        return {'language': self.language, **{k: f.value for k, f in self.fields if f.usable},
                'services': [f.value for f in self.services if f.usable]}

    def report(self):
        sourced = [k for k, f in self.fields if f.status == 'source_verified_for_demo']
        report = {'approved_demo_fields': [k for k, f in self.fields if f.status == 'approved_for_demo'],
                'withheld_fields': [k for k in OPTIONAL if (k != 'whatsapp' or k in dict(self.fields))
                                    and not any(n == k and f.usable for n, f in self.fields)],
                'approved_services': sum(f.status == 'approved_for_demo' for f in self.services),
                'withheld_services': sum(not f.usable for f in self.services),
                'publication_approved': False,
                'verification_scope': 'Human-supplied approvals for private demo, not independent verification'}
        if sourced or any(f.status == 'source_verified_for_demo' for f in self.services):
            report.update(source_verified_fields=sourced,
                          source_verified_services=sum(f.status == 'source_verified_for_demo' for f in self.services),
                          verification_scope='Private demo using attributed source review and any separate human approvals.')
        return report
