"""Strict bounded offline map descriptors and supplied record manifests."""

from pathlib import Path

from .inspection_io import _integer, _keys, _object, _text, load_json_object, read_bounded
from .map_inspection import MapField, MapInspectionProfile, MapRecordProfile


def _list(value: object, limit: int) -> list[object]:
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError('bounded JSON list required')
    return value


def parse_map_inspection_profile(values: object) -> MapInspectionProfile:
    """Parse exact versioned keys; core dataclasses validate layout invariants."""
    values = _object(values)
    _keys(values, {'kind', 'schema_version', 'game_id', 'patch_id', 'emulator_version',
                   'map_label', 'dimensions', 'records'})
    if values['kind'] != 'map_inspection' or _integer(values['schema_version']) != 1:
        raise ValueError('unsupported map profile kind or schema version')
    dimensions = None
    if values['dimensions'] is not None:
        dimensions_list = _list(values['dimensions'], 2)
        if len(dimensions_list) != 2:
            raise ValueError('dimensions require width and height')
        dimensions = (_integer(dimensions_list[0]), _integer(dimensions_list[1]))
    records = []
    for record_value in _list(values['records'], 256):
        record = _object(record_value)
        _keys(record, {'label', 'address', 'size', 'fields'})
        fields = []
        for field_value in _list(record['fields'], 11):
            field = _object(field_value)
            _keys(field, {'name', 'offset', 'width', 'evidence_ids', 'meanings'})
            meanings = []
            for pair_value in _list(field['meanings'], 256):
                pair = _list(pair_value, 2)
                if len(pair) != 2:
                    raise ValueError('meaning requires raw value and label')
                meanings.append((_integer(pair[0]), _text(pair[1])))
            fields.append(MapField(_text(field['name']), _integer(field['offset']),
                _integer(field['width']),
                tuple(_text(item) for item in _list(field['evidence_ids'], 32)),
                tuple(meanings)))
        records.append(MapRecordProfile(_text(record['label']), _integer(record['address']),
                                        _integer(record['size']), tuple(fields)))
    return MapInspectionProfile(_text(values['game_id']), _text(values['patch_id']),
                                _text(values['emulator_version']), _text(values['map_label']),
                                dimensions, tuple(records))


def load_map_records(path: Path, profile: MapInspectionProfile) -> tuple[bytes, ...]:
    """Read exact-sized local records in profile order, never from a live source."""
    manifest = load_json_object(path)
    _keys(manifest, {'kind', 'schema_version', 'records'})
    if manifest['kind'] != 'map_records' or _integer(manifest['schema_version']) != 1:
        raise ValueError('unsupported records manifest kind or schema version')
    records = _list(manifest['records'], 256)
    if len(records) != len(profile.records):
        raise ValueError('manifest record count must match profile')
    paths = []
    for record_value, descriptor in zip(records, profile.records, strict=True):
        record = _object(record_value)
        _keys(record, {'label', 'path'})
        if _text(record['label']) != descriptor.label:
            raise ValueError('manifest labels must match profile order')
        record_path = Path(_text(record['path']))
        if not record_path.is_absolute():
            record_path = path.absolute().parent / record_path
        paths.append(record_path)
    samples = []
    for record_path, descriptor in zip(paths, profile.records, strict=True):
        data = read_bounded(record_path, descriptor.size)
        if len(data) != descriptor.size:
            raise ValueError('record must contain exactly profile size bytes')
        samples.append(data)
    return tuple(samples)
