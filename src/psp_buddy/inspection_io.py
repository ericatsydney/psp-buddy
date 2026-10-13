"""Strict bounded local input; supplied evidence never grants live capability."""

import json
import math
import os
import stat
from pathlib import Path
from typing import cast

from .profile import FieldBinding, InspectionProfile

MAX_JSON_BYTES = 1024 * 1024
MAX_INSTRUCTIONS_BYTES = 65536


def read_bounded(path: Path, limit: int) -> bytes:
    if path.is_symlink():
        raise ValueError('input must be a regular file')
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        raise ValueError('input file exceeds bounds or is not regular')
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    current = path.stat()
    def signature(info: os.stat_result) -> tuple[int, int, int, int]:
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns
    if (len(data) > limit or not signature(before) == signature(opened)
            == signature(after) == signature(current)):
        raise ValueError('input exceeds bounds or changed while reading')
    return data


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise ValueError('JSON object required')
    return cast(dict[str, object], value)


def _keys(values: dict[str, object], expected: set[str]) -> None:
    if set(values) - expected:
        raise ValueError('unknown descriptor fields')
    if expected - set(values):
        raise ValueError('missing descriptor fields')


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise ValueError('bounded nonempty text required')
    return value


def _integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError('integer required')
    return value


def load_json_object(path: Path) -> dict[str, object]:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def invalid_constant(value: str) -> object:
        raise ValueError('nonfinite JSON number forbidden')
    def finite_float(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('nonfinite JSON number forbidden')
        return number
    try:
        value = json.loads(read_bounded(path, MAX_JSON_BYTES).decode('utf-8'),
                           object_pairs_hook=pairs, parse_constant=invalid_constant,
                           parse_float=finite_float)
    except (RecursionError, UnicodeError) as exc:
        raise ValueError('invalid JSON encoding or nesting') from exc
    return _object(value)


def parse_inspection_profile(values: object) -> InspectionProfile:
    values = _object(values)
    _keys(values, {'kind', 'schema_version', 'game_id', 'patch_id', 'emulator_version',
                   'unit_label', 'record_address', 'record_size', 'fields'})
    if values['kind'] != 'stat_inspection' or _integer(values['schema_version']) != 1:
        raise ValueError('unsupported profile kind or schema version')
    fields = values['fields']
    if not isinstance(fields, list) or not 1 <= len(fields) <= 11:
        raise ValueError('bounded field list required')
    bindings = []
    for field in fields:
        field = _object(field)
        _keys(field, {'name', 'offset', 'width', 'evidence_ids'})
        evidence = field['evidence_ids']
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 64:
            raise ValueError('bounded evidence reference list required')
        bindings.append(FieldBinding(_text(field['name']), _integer(field['offset']),
                                     _integer(field['width']), tuple(_text(e) for e in evidence)))
    return InspectionProfile(_text(values['game_id']), _text(values['patch_id']),
                             _text(values['emulator_version']), _text(values['unit_label']),
                             _integer(values['record_address']), _integer(values['record_size']),
                             tuple(bindings))


def load_record(path: Path, profile: InspectionProfile) -> bytes:
    data = read_bounded(path, profile.record_size)
    if len(data) != profile.record_size:
        raise ValueError('record must contain exactly record_size bytes')
    return data
