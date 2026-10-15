import json

import pytest

from psp_buddy.map_inspection_io import load_map_records, parse_map_inspection_profile


def descriptor():
    return dict(kind='map_inspection', schema_version=1, game_id='game', patch_id='patch',
                emulator_version='version', map_label='synthetic', dimensions=None, records=[
                    dict(label='one', address=0x08800000, size=4, fields=[
                        dict(name='hp', offset=0, width=2, evidence_ids=['hp'], meanings=[]),
                        dict(name='max_hp', offset=2, width=2,
                             evidence_ids=['max-hp'], meanings=[])])])


def test_valid_descriptor_is_immutable():
    profile = parse_map_inspection_profile(descriptor())
    assert profile.records[0].fields[0].evidence_ids == ('hp',)
    assert profile.dimensions is None


@pytest.mark.parametrize('change', [dict(kind='tactical'), dict(schema_version=True),
    dict(schema_version=2), dict(game_id=1), dict(dimensions=[True, 2]),
    dict(dimensions=[1]), dict(records=[]), dict(records={}), dict(extra=1)])
def test_bad_top_level_rejected(change):
    with pytest.raises(ValueError):
        parse_map_inspection_profile({**descriptor(), **change})


@pytest.mark.parametrize('change', [dict(label=True), dict(address=True), dict(size='4'),
    dict(fields={}), dict(extra=1)])
def test_bad_record_rejected(change):
    values = descriptor()
    values['records'][0].update(change)
    with pytest.raises(ValueError):
        parse_map_inspection_profile(values)


@pytest.mark.parametrize('change', [dict(offset=True), dict(width='2'), dict(name='phase'),
    dict(evidence_ids='hp'), dict(evidence_ids=[1]), dict(meanings={}),
    dict(meanings=[[1]]), dict(meanings=[[True, 'ally']]), dict(extra=1)])
def test_bad_field_rejected(change):
    values = descriptor()
    values['records'][0]['fields'][0].update(change)
    with pytest.raises(ValueError):
        parse_map_inspection_profile(values)


def test_missing_nested_keys_and_duplicates_rejected():
    values = descriptor()
    del values['records'][0]['fields'][0]['meanings']
    with pytest.raises(ValueError):
        parse_map_inspection_profile(values)
    values = descriptor()
    values['records'].append(values['records'][0])
    with pytest.raises(ValueError):
        parse_map_inspection_profile(values)


def test_explicit_enum_and_dimensions():
    values = descriptor()
    values['dimensions'] = [10, 20]
    values['records'][0]['fields'] = [dict(name='side', offset=0, width=1,
        evidence_ids=['side'], meanings=[[3, 'ally'], [4, 'enemy']])]
    profile = parse_map_inspection_profile(values)
    assert profile.dimensions == (10, 20)
    assert profile.records[0].fields[0].meanings == ((3, 'ally'), (4, 'enemy'))


def manifest(tmp_path, records=None, **change):
    path = tmp_path / 'records.json'
    path.write_text(json.dumps(dict(kind='map_records', schema_version=1,
        records=[dict(label='one', path='record.bin')] if records is None else records, **change)))
    return path


def test_records_resolve_relative_to_manifest_and_exact_bytes(tmp_path, monkeypatch):
    (tmp_path / 'record.bin').write_bytes(b'abcd')
    path = manifest(tmp_path)
    monkeypatch.chdir(tmp_path.parent)
    assert load_map_records(path, parse_map_inspection_profile(descriptor())) == (b'abcd',)


@pytest.mark.parametrize('records', [[], {}, [dict(label='wrong', path='record.bin')],
    [dict(label='one', path='record.bin'), dict(label='one', path='record.bin')],
    [dict(label='one', path=True)], [dict(label='one', path='record.bin', extra=1)]])
def test_bad_manifest_records_rejected(tmp_path, records):
    (tmp_path / 'record.bin').write_bytes(b'abcd')
    with pytest.raises(ValueError):
        load_map_records(manifest(tmp_path, records), parse_map_inspection_profile(descriptor()))


@pytest.mark.parametrize('data', [b'abc', b'abcde'])
def test_short_or_oversized_record_rejected(tmp_path, data):
    (tmp_path / 'record.bin').write_bytes(data)
    with pytest.raises(ValueError):
        load_map_records(manifest(tmp_path), parse_map_inspection_profile(descriptor()))


def test_manifest_order_is_exact_and_absolute_paths_supported(tmp_path):
    values = descriptor()
    values['records'].append(dict(label='two', address=0x08800010, size=4, fields=[]))
    profile = parse_map_inspection_profile(values)
    first, second = tmp_path / 'record.bin', tmp_path / 'second.bin'
    first.write_bytes(b'abcd')
    second.write_bytes(b'efgh')
    entries = [dict(label='one', path=str(first)), dict(label='two', path=str(second))]
    assert load_map_records(manifest(tmp_path, entries), profile) == (b'abcd', b'efgh')
    with pytest.raises(ValueError, match='order'):
        load_map_records(manifest(tmp_path, entries[::-1]), profile)


@pytest.mark.parametrize('text', ['{"kind":"map_records","kind":"map_records"}',
    '{"kind":"map_records","schema_version":NaN,"records":[]}',
    '{"kind":"map_records","schema_version":1e999,"records":[]}',
    '{"kind":"map_records","schema_version":true,"records":[]}',
    '{"kind":"wrong","schema_version":1,"records":[]}',
    '{"kind":"map_records","schema_version":1,"records":[],"extra":1}'])
def test_strict_json_manifest(tmp_path, text):
    path = tmp_path / 'records.json'
    path.write_text(text)
    with pytest.raises(ValueError):
        load_map_records(path, parse_map_inspection_profile(descriptor()))
