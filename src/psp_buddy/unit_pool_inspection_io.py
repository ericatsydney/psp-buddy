"""Strict bounded local descriptors and manifests for structural pool inspection."""

from pathlib import Path

from .inspection_io import _integer, _keys, _object, _text, load_json_object, read_bounded
from .unit_pool_inspection import CodeAnchor, InspectionSpan, UnitPoolInspectionProfile


def _list(value: object, minimum: int, maximum: int) -> list[object]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError('bounded JSON list required')
    return value


def parse_unit_pool_inspection_profile(values: object) -> UnitPoolInspectionProfile:
    """Parse exact version-one keys; immutable core validates binary invariants."""
    values = _object(values)
    integers = ('pool_address', 'pool_capacity', 'pool_stride', 'actor_owner_address',
                'actor_node_array_address', 'actor_stride', 'actor_capacity', 'actor_vtable')
    texts = ('game_id', 'patch_id', 'emulator_version', 'map_label')
    _keys(values, {'kind', 'schema_version', 'evidence_ids', 'code_anchors', *integers, *texts})
    if values['kind'] != 'unit_pool_inspection' or _integer(values['schema_version']) != 1:
        raise ValueError('unsupported unit pool profile kind or schema version')
    anchors = []
    for item in _list(values['code_anchors'], 1, 8):
        anchor = _object(item)
        _keys(anchor, {'address', 'size', 'sha256'})
        anchors.append(CodeAnchor(_integer(anchor['address']), _integer(anchor['size']),
                                  _text(anchor['sha256'])))
    return UnitPoolInspectionProfile(
        game_id=_text(values['game_id']), patch_id=_text(values['patch_id']),
        emulator_version=_text(values['emulator_version']), map_label=_text(values['map_label']),
        pool_address=_integer(values['pool_address']),
        pool_capacity=_integer(values['pool_capacity']),
        pool_stride=_integer(values['pool_stride']),
        actor_owner_address=_integer(values['actor_owner_address']),
        actor_node_array_address=_integer(values['actor_node_array_address']),
        actor_stride=_integer(values['actor_stride']),
        actor_capacity=_integer(values['actor_capacity']),
        actor_vtable=_integer(values['actor_vtable']),
        evidence_ids=tuple(_text(item) for item in _list(values['evidence_ids'], 1, 32)),
        code_anchors=tuple(anchors))


def load_inspection_spans(path: Path) -> tuple[InspectionSpan, ...]:
    """Load supplied regular local files with bounded per-file and aggregate sizes."""
    manifest = load_json_object(path)
    _keys(manifest, {'kind', 'schema_version', 'spans'})
    if manifest['kind'] != 'inspection_spans' or _integer(manifest['schema_version']) != 1:
        raise ValueError('unsupported spans manifest kind or schema version')
    paths = []
    for item in _list(manifest['spans'], 1, 32):
        entry = _object(item)
        _keys(entry, {'address', 'path'})
        address = _integer(entry['address'])
        name = entry['path']
        if not isinstance(name, str) or not name or '\x00' in name:
            raise ValueError('nonempty path without NUL required')
        source = Path(name)
        if not source.is_absolute():
            source = path.absolute().parent / source
        paths.append((address, source))
    sizes = [source.stat().st_size for _, source in paths]
    if any(not 1 <= size <= 65536 for size in sizes) or sum(sizes) > 1048576:
        raise ValueError('inspection span file sizes exceed bounds')
    spans = []
    total = 0
    for (address, source), size in zip(paths, sizes, strict=True):
        data = read_bounded(source, size)
        if len(data) != size:
            raise ValueError('inspection span changed size before reading')
        total += len(data)
        if total > 1048576:
            raise ValueError('inspection span aggregate exceeds bounds')
        spans.append(InspectionSpan(address, data))
    ordered = sorted(spans, key=lambda span: span.address)
    if any(left.address + len(left.data) > right.address
           for left, right in zip(ordered, ordered[1:], strict=False)):
        raise ValueError('inspection spans overlap')
    return tuple(spans)
