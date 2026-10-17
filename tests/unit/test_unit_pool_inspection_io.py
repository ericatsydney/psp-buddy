import hashlib
import json

import pytest

from psp_buddy.unit_pool_inspection_io import (
    load_inspection_spans,
    parse_unit_pool_inspection_profile,
)


def descriptor():
    return dict(kind='unit_pool_inspection', schema_version=1, game_id='g', patch_id='p',
        emulator_version='e', map_label='synthetic', pool_address=0x08801000,
        pool_capacity=1, pool_stride=104, actor_owner_address=0x08802000,
        actor_node_array_address=0x08805000, actor_stride=16, actor_capacity=1,
        actor_vtable=0x08806000, evidence_ids=['synthetic'], code_anchors=[dict(
            address=0x08804000, size=4, sha256=hashlib.sha256(b'code').hexdigest())])


def test_parse_exact_descriptor():
    profile = parse_unit_pool_inspection_profile(descriptor())
    assert profile.pool_capacity == 1
    assert profile.code_anchors[0].sha256 == hashlib.sha256(b'code').hexdigest()


@pytest.mark.parametrize('change', [dict(extra=1), dict(schema_version=True),
    dict(pool_address=True), dict(evidence_ids=[]), dict(evidence_ids=['x', 'x']),
    dict(game_id='a\n'), dict(code_anchors=[]), dict(pool_stride=100)])
def test_reject_bad_descriptor(change):
    with pytest.raises(ValueError):
        parse_unit_pool_inspection_profile({**descriptor(), **change})


def test_relative_manifest_paths(tmp_path):
    (tmp_path / 'data.bin').write_bytes(b'abcd')
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(dict(kind='inspection_spans', schema_version=1,
        spans=[dict(address=0x08801000, path='data.bin')])))
    spans = load_inspection_spans(path)
    assert spans[0].address == 0x08801000
    assert spans[0].data == b'abcd'


@pytest.mark.parametrize('entry', [dict(address=True, path='x'),
    dict(address=0x08800000, path=''), dict(address=0x08800000, path='a\x00b'),
    dict(address=0x08800000, path='x', extra=1)])
def test_reject_bad_manifest_entries_before_read(tmp_path, entry):
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(dict(kind='inspection_spans', schema_version=1, spans=[entry])))
    with pytest.raises(ValueError):
        load_inspection_spans(path)

@pytest.mark.parametrize('mutation', ['missing', 'anchor_extra', 'digest', 'control', 'long',
    'evidence_many', 'anchor_many', 'float', 'kind'])
def test_more_strict_profile_rejections(mutation):
    values = descriptor()
    if mutation == 'missing':
        del values['pool_stride']
    elif mutation == 'anchor_extra':
        values['code_anchors'][0]['extra'] = 1
    elif mutation == 'digest':
        values['code_anchors'][0]['sha256'] = 'z' * 64
    elif mutation == 'control':
        values['map_label'] = 'bad\x00label'
    elif mutation == 'long':
        values['game_id'] = 'x' * 257
    elif mutation == 'evidence_many':
        values['evidence_ids'] = [str(i) for i in range(33)]
    elif mutation == 'anchor_many':
        values['code_anchors'] *= 9
    elif mutation == 'float':
        values['pool_capacity'] = 1.0
    else:
        values['kind'] = 'map_inspection'
    with pytest.raises(ValueError):
        parse_unit_pool_inspection_profile(values)


@pytest.mark.parametrize('kind', ['map_records', 'wrong'])
def test_wrong_manifest_kind(tmp_path, kind):
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(dict(kind=kind, schema_version=1, spans=[])))
    with pytest.raises(ValueError):
        load_inspection_spans(path)


@pytest.mark.parametrize('content', ['{"kind":"inspection_spans","kind":"x"}',
    '{"kind":NaN}', '{"kind":Infinity}', '{"kind":1e999}'])
def test_invalid_json_manifest(tmp_path, content):
    path = tmp_path / 'manifest.json'
    path.write_text(content)
    with pytest.raises(ValueError):
        load_inspection_spans(path)


@pytest.mark.parametrize('case', ['large', 'empty', 'missing', 'directory', 'overlap',
    'too_many', 'total', 'schema', 'unknown', 'bool', 'out_of_ram'])
def test_manifest_file_bounds_and_schema(tmp_path, case):
    data = tmp_path / 'data.bin'
    data.write_bytes(b'abcd')
    entries = [dict(address=0x08801000, path='data.bin')]
    manifest = dict(kind='inspection_spans', schema_version=1, spans=entries)
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
        entries.append(dict(address=0x08801002, path='data.bin'))
    elif case == 'too_many':
        manifest['spans'] = entries * 33
    elif case == 'total':
        data.write_bytes(b'x' * 65536)
        manifest['spans'] = [dict(address=0x08800000 + i * 65536, path='data.bin')
                             for i in range(17)]
    elif case == 'schema':
        manifest['schema_version'] = 2
    elif case == 'unknown':
        manifest['extra'] = 1
    elif case == 'bool':
        manifest['schema_version'] = True
    else:
        entries[0]['address'] = 0x087FFFFF
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(manifest))
    with pytest.raises((ValueError, OSError)):
        load_inspection_spans(path)


def test_span_changed_before_read_is_rejected(tmp_path, monkeypatch):
    (tmp_path / 'data.bin').write_bytes(b'abcd')
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(dict(kind='inspection_spans', schema_version=1,
        spans=[dict(address=0x08801000, path='data.bin')])))
    monkeypatch.setattr('psp_buddy.unit_pool_inspection_io.read_bounded',
                        lambda *args: b'a')
    with pytest.raises(ValueError, match='changed size'):
        load_inspection_spans(path)


def test_spans_manifest_rejected_by_named_record_loader(tmp_path):
    from psp_buddy.map_inspection_io import load_map_records
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(dict(kind='inspection_spans', schema_version=1, spans=[])))
    with pytest.raises(ValueError):
        load_map_records(path, None)


def test_uppercase_digest_is_normalized():
    values = descriptor()
    values['code_anchors'][0]['sha256'] = values['code_anchors'][0]['sha256'].upper()
    profile = parse_unit_pool_inspection_profile(values)
    assert profile.code_anchors[0].sha256 == hashlib.sha256(b'code').hexdigest()


def test_aggregate_bound_rejected_before_binary_reads(tmp_path, monkeypatch):
    (tmp_path / 'data.bin').write_bytes(b'x' * 65536)
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(dict(kind='inspection_spans', schema_version=1,
        spans=[dict(address=0x08800000 + i * 65536, path='data.bin') for i in range(17)])))
    def poisoned(*args):
        raise AssertionError('aggregate bound must be checked before binary reads')
    monkeypatch.setattr('psp_buddy.unit_pool_inspection_io.read_bounded', poisoned)
    with pytest.raises(ValueError, match='sizes exceed'):
        load_inspection_spans(path)
