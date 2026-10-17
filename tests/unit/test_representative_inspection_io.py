import hashlib
import json
import os

import pytest
from test_unit_pool_inspection_io import descriptor as pool_descriptor

from psp_buddy.representative_inspection_io import (
    load_representative_spans,
    parse_representative_inspection_profile,
)


def descriptor():
    return dict(kind='representative_inspection', schema_version=1,
        pool_profile=pool_descriptor(), source_root_global=0x08807000,
        cache_owner_global=0x08807004, blocked_mech_ids_address=0x08808000,
        selector_owner_global=0x08807008, pair_exclusion_owner_global=0x0880700c,
        node_regions=[dict(address=0x08809000, capacity=10, stride=12)],
        mech_descriptors=dict(address=0x08810000, capacity=10, stride=12),
        pilot_descriptors=dict(address=0x08811000, capacity=10, stride=8),
        code_anchors=[dict(address=0x08812000, size=4,
                           sha256=hashlib.sha256(b'test').hexdigest())],
        evidence_ids=['synthetic'])


def manifest(tmp_path, entries, kind='representative_spans'):
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(dict(kind=kind, schema_version=1, spans=entries)))
    return path


def test_profile_exact_nested_contract():
    profile = parse_representative_inspection_profile(descriptor())
    assert profile.pool_profile.pool_stride == 104
    assert profile.source_root_global == 0x08807000


@pytest.mark.parametrize('field', ['source_root_global', 'cache_owner_global',
    'blocked_mech_ids_address', 'selector_owner_global', 'pair_exclusion_owner_global'])
@pytest.mark.parametrize('bad', [True, -1, 0x100000000, 0x08807001, 1.0])
def test_invalid_addresses(field, bad):
    with pytest.raises(ValueError):
        parse_representative_inspection_profile({**descriptor(), field: bad})


@pytest.mark.parametrize('change', [dict(extra=1), dict(schema_version=True),
    dict(kind='unit_pool_inspection'), dict(node_regions=[]), dict(code_anchors=[]),
    dict(evidence_ids=['x', 'x'])])
def test_strict_profile(change):
    with pytest.raises(ValueError):
        parse_representative_inspection_profile({**descriptor(), **change})


def test_manifest_relative_and_128_entries(tmp_path):
    (tmp_path / 'data.bin').write_bytes(b'abcd')
    entries = [dict(address=0x08800000 + i * 4, path='data.bin') for i in range(128)]
    result = load_representative_spans(manifest(tmp_path, entries))
    assert len(result) == 128
    assert result[-1].data == b'abcd'


@pytest.mark.parametrize('case', ['large', 'empty', 'missing', 'directory', 'overlap',
    'count', 'total', 'address', 'hardlink'])
def test_file_rejections(tmp_path, case):
    data = tmp_path / 'data.bin'
    data.write_bytes(b'abcd')
    entries = [dict(address=0x08801000, path='data.bin')]
    if case == 'large':
        data.write_bytes(b'x' * 65537)
    elif case == 'empty':
        data.write_bytes(b'')
    elif case == 'missing':
        data.unlink()
    elif case == 'directory':
        data.unlink()
        data.mkdir()
    elif case == 'overlap':
        entries *= 2
    elif case == 'count':
        entries *= 129
    elif case == 'total':
        data.write_bytes(b'x' * 65536)
        entries = [dict(address=0x08800000 + i * 65536, path='data.bin') for i in range(17)]
    elif case == 'address':
        entries[0]['address'] = True
    else:
        os.link(data, tmp_path / 'alias.bin')
    with pytest.raises((ValueError, OSError)):
        load_representative_spans(manifest(tmp_path, entries))


@pytest.mark.parametrize('content', ['{"kind":"x","kind":"y"}', '{"kind":NaN}',
    '{"kind":Infinity}', '{"kind":1e999}'])
def test_invalid_json(tmp_path, content):
    path = tmp_path / 'manifest.json'
    path.write_text(content)
    with pytest.raises(ValueError):
        load_representative_spans(path)


def test_aggregate_checked_before_reads(tmp_path, monkeypatch):
    (tmp_path / 'data.bin').write_bytes(b'x' * 65536)
    path = manifest(tmp_path, [dict(address=0x08800000 + i * 65536, path='data.bin')
                               for i in range(17)])
    def poisoned(*args):
        raise AssertionError('must reject before binary reads')
    monkeypatch.setattr('psp_buddy.representative_inspection_io.read_bounded', poisoned)
    with pytest.raises(ValueError, match='sizes exceed'):
        load_representative_spans(path)


def test_changed_size_rejected(tmp_path, monkeypatch):
    (tmp_path / 'data.bin').write_bytes(b'abcd')
    path = manifest(tmp_path, [dict(address=0x08801000, path='data.bin')])
    monkeypatch.setattr('psp_buddy.representative_inspection_io.read_bounded', lambda *a: b'a')
    with pytest.raises(ValueError, match='changed size'):
        load_representative_spans(path)


def test_old_new_manifests_remain_separate(tmp_path):
    from psp_buddy.unit_pool_inspection_io import load_inspection_spans
    (tmp_path / 'data.bin').write_bytes(b'abcd')
    entries = [dict(address=0x08800000 + i * 4, path='data.bin') for i in range(33)]
    with pytest.raises(ValueError):
        load_inspection_spans(manifest(tmp_path, entries))
    with pytest.raises(ValueError):
        load_inspection_spans(manifest(tmp_path, entries, 'inspection_spans'))
    with pytest.raises(ValueError):
        load_representative_spans(manifest(tmp_path, entries, 'inspection_spans'))

@pytest.mark.parametrize('field', ['node_regions', 'mech_descriptors', 'pilot_descriptors'])
@pytest.mark.parametrize('part,bad', [('address', True), ('address', -1),
    ('address', 0x100000000), ('address', 0x08809001), ('capacity', True),
    ('capacity', -1), ('capacity', 2049), ('stride', True), ('stride', -1),
    ('stride', 0x100000000), ('stride', 3)])
def test_invalid_regions(field, part, bad):
    values = descriptor()
    region = values[field][0] if field == 'node_regions' else values[field]
    region[part] = bad
    with pytest.raises(ValueError):
        parse_representative_inspection_profile(values)


@pytest.mark.parametrize('case', ['missing', 'nested_extra', 'anchor_extra', 'bad_digest',
    'region_extra', 'region_missing', 'evidence_empty', 'anchor_many', 'pool_extra'])
def test_nested_strictness(case):
    values = descriptor()
    if case == 'missing':
        del values['source_root_global']
    elif case == 'nested_extra':
        values['pool_profile']['extra'] = 1
    elif case == 'anchor_extra':
        values['code_anchors'][0]['extra'] = 1
    elif case == 'bad_digest':
        values['code_anchors'][0]['sha256'] = 'z' * 64
    elif case == 'region_extra':
        values['node_regions'][0]['extra'] = 1
    elif case == 'region_missing':
        del values['node_regions'][0]['stride']
    elif case == 'evidence_empty':
        values['evidence_ids'] = []
    elif case == 'anchor_many':
        values['code_anchors'] *= 33
    else:
        values['pool_profile']['pool_address'] = True
    with pytest.raises(ValueError):
        parse_representative_inspection_profile(values)


def test_symlink_rejected(tmp_path):
    data = tmp_path / 'data.bin'
    data.write_bytes(b'abcd')
    link = tmp_path / 'link.bin'
    try:
        link.symlink_to(data)
    except OSError:
        pytest.skip('symlink creation unavailable')
    with pytest.raises(ValueError):
        load_representative_spans(manifest(tmp_path, [dict(address=0x08801000, path='link.bin')]))


@pytest.mark.parametrize('change', [dict(schema_version=True), dict(schema_version=2),
    dict(extra=1), dict(spans=[]), dict(spans=[dict(address=1, path='x', extra=1)]),
    dict(spans=[dict(address=0x08800000, path='')]),
    dict(spans=[dict(address=0x08800000, path='x\x00y')])])
def test_manifest_schema(tmp_path, change):
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(dict(kind='representative_spans', schema_version=1,
                                    spans=[]) | change))
    with pytest.raises(ValueError):
        load_representative_spans(path)


def test_hardlinked_manifest_rejected(tmp_path):
    (tmp_path / 'data.bin').write_bytes(b'abcd')
    path = manifest(tmp_path, [dict(address=0x08801000, path='data.bin')])
    os.link(path, tmp_path / 'manifest-alias.json')
    with pytest.raises(ValueError):
        load_representative_spans(path)

