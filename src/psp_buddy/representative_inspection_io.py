"""Strict local descriptors and bounded files for representative inspection."""

import stat
from pathlib import Path

from .inspection_io import _integer, _keys, _object, _text, load_json_object, read_bounded
from .representative_inspection import InspectionRegion, RepresentativeInspectionProfile
from .unit_pool_inspection import CodeAnchor, InspectionSpan
from .unit_pool_inspection_io import _list, parse_unit_pool_inspection_profile


def _region(value: object) -> InspectionRegion:
    values = _object(value)
    _keys(values, {'address', 'capacity', 'stride'})
    return InspectionRegion(*(_integer(values[key]) for key in ('address', 'capacity', 'stride')))


def parse_representative_inspection_profile(values: object) -> RepresentativeInspectionProfile:
    """Parse the exact version-one recipe; the immutable profile checks invariants."""
    values = _object(values)
    addresses = ('source_root_global', 'cache_owner_global', 'blocked_mech_ids_address',
                 'selector_owner_global', 'pair_exclusion_owner_global')
    _keys(values, {'kind', 'schema_version', 'pool_profile', 'node_regions',
                   'mech_descriptors', 'pilot_descriptors', 'code_anchors', 'evidence_ids',
                   *addresses})
    if values['kind'] != 'representative_inspection' or _integer(values['schema_version']) != 1:
        raise ValueError('unsupported representative profile kind or schema version')
    anchors = []
    for item in _list(values['code_anchors'], 1, 32):
        anchor = _object(item)
        _keys(anchor, {'address', 'size', 'sha256'})
        anchors.append(CodeAnchor(_integer(anchor['address']), _integer(anchor['size']),
                                  _text(anchor['sha256'])))
    return RepresentativeInspectionProfile(
        pool_profile=parse_unit_pool_inspection_profile(values['pool_profile']),
        source_root_global=_integer(values['source_root_global']),
        cache_owner_global=_integer(values['cache_owner_global']),
        blocked_mech_ids_address=_integer(values['blocked_mech_ids_address']),
        selector_owner_global=_integer(values['selector_owner_global']),
        pair_exclusion_owner_global=_integer(values['pair_exclusion_owner_global']),
        node_regions=tuple(_region(item) for item in _list(values['node_regions'], 1, 2)),
        mech_descriptors=_region(values['mech_descriptors']),
        pilot_descriptors=_region(values['pilot_descriptors']),
        code_anchors=tuple(anchors),
        evidence_ids=tuple(_text(item) for item in _list(values['evidence_ids'], 1, 32)))


def load_representative_spans(path: Path) -> tuple[InspectionSpan, ...]:
    """Load 1..128 immutable regular files, checking aggregate bounds before reads."""
    if path.stat().st_nlink != 1:
        raise ValueError('manifest must not have hard links')
    manifest = load_json_object(path)
    if path.stat().st_nlink != 1:
        raise ValueError('manifest gained a hard link while reading')
    _keys(manifest, {'kind', 'schema_version', 'spans'})
    if manifest['kind'] != 'representative_spans' or _integer(manifest['schema_version']) != 1:
        raise ValueError('unsupported representative spans kind or schema version')
    paths = []
    for item in _list(manifest['spans'], 1, 128):
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
    sizes = []
    for _, source in paths:
        info = source.stat()
        if source.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('input must be a regular file without links')
        sizes.append(info.st_size)
    if any(not 1 <= size <= 65536 for size in sizes) or sum(sizes) > 1048576:
        raise ValueError('representative span file sizes exceed bounds')
    # Validate address windows and overlaps before retaining any binary input.
    ordered = sorted(zip(paths, sizes, strict=True), key=lambda item: item[0][0])
    for (address, _), size in ordered:
        if not 0x08800000 <= address < address + size <= 0x0A000000:
            raise ValueError('inspection span is outside PSP user RAM')
    if any(left[0][0] + left[1] > right[0][0]
           for left, right in zip(ordered, ordered[1:], strict=False)):
        raise ValueError('inspection spans overlap')
    spans = []
    for (address, source), size in zip(paths, sizes, strict=True):
        data = read_bounded(source, size)
        if len(data) != size:
            raise ValueError('inspection span changed size before reading')
        if source.stat().st_nlink != 1:
            raise ValueError('input gained a hard link while reading')
        spans.append(InspectionSpan(address, data))
    return tuple(spans)

