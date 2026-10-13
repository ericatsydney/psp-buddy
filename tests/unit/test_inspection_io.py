import pytest

from psp_buddy.inspection_io import parse_inspection_profile


def descriptor():
    return dict(kind='stat_inspection', schema_version=1, game_id='game', patch_id='patch',
                emulator_version='version', unit_label='synthetic', record_address=0x08800000,
                record_size=4, fields=[
                    dict(name='hp', offset=0, width=2, evidence_ids=['synthetic-hp']),
                    dict(name='max_hp', offset=2, width=2, evidence_ids=['synthetic-max-hp'])])


def test_parse_profile_rejects_tactical_claims():
    with pytest.raises(ValueError, match='unknown'):
        parse_inspection_profile({**descriptor(), 'legal_actions': []})


def test_parse_valid_profile_is_immutable():
    profile = parse_inspection_profile(descriptor())
    assert profile.record_size == 4
    assert isinstance(profile.fields, tuple)
    assert profile.fields[0].evidence_ids == ('synthetic-hp',)


@pytest.mark.parametrize('changes', [dict(kind='tactical'), dict(schema_version=True),
    dict(schema_version=2), dict(game_id=3), dict(record_address=True),
    dict(record_size=65537), dict(record_size=0), dict(fields={}),
    dict(fields=[]), dict(unit_label=''), dict(validated=True)])
def test_invalid_descriptors_fail_closed(changes):
    with pytest.raises(ValueError):
        parse_inspection_profile({**descriptor(), **changes})


@pytest.mark.parametrize('changes', [dict(offset=True), dict(width='2'),
    dict(name='phase'), dict(evidence_ids='text'), dict(evidence_ids=[]),
    dict(evidence_ids=[True]), dict(extra=1), dict(offset=3)])
def test_invalid_field_bindings_fail_closed(changes):
    values = descriptor()
    values['fields'][0].update(changes)
    with pytest.raises(ValueError):
        parse_inspection_profile(values)


def test_unknown_missing_and_nonobject_profiles_rejected():
    for values in (None, [], {'kind': 'stat_inspection'}, {**descriptor(), 'verified': True}):
        with pytest.raises(ValueError):
            parse_inspection_profile(values)


def test_json_duplicate_keys_and_nonfinite_values_rejected(tmp_path):
    from psp_buddy.inspection_io import load_json_object
    path = tmp_path / 'descriptor.json'
    for text in ('{"key":1,"key":2}', '{"x":{"key":1,"key":2}}', '{"x":NaN}', '[]'):
        path.write_text(text)
        with pytest.raises(ValueError):
            load_json_object(path)


def test_record_requires_exact_size(tmp_path):
    from psp_buddy.inspection_io import load_record
    path = tmp_path / 'record.bin'
    for data in (b'abc', b'abcde'):
        path.write_bytes(data)
        with pytest.raises(ValueError):
            load_record(path, parse_inspection_profile(descriptor()))
    path.write_bytes(b'abcd')
    assert load_record(path, parse_inspection_profile(descriptor())) == b'abcd'


def test_bounded_file_reads_reject_oversize(tmp_path):
    from psp_buddy.inspection_io import read_bounded
    path = tmp_path / 'large'
    path.write_bytes(b'12345')
    with pytest.raises(ValueError):
        read_bounded(path, 4)


def test_json_exponent_overflow_is_not_finite(tmp_path):
    from psp_buddy.inspection_io import load_json_object
    path = tmp_path / 'overflow.json'
    path.write_text('{"x":1e999}')
    with pytest.raises(ValueError):
        load_json_object(path)


def test_input_mutation_during_read_is_rejected(tmp_path, monkeypatch):
    from psp_buddy import inspection_io
    path = tmp_path / 'changing.bin'
    path.write_bytes(b'abcd')
    original = inspection_io.os.fstat
    calls = 0
    def mutate_after_read(descriptor):
        nonlocal calls
        calls += 1
        if calls == 2:
            path.write_bytes(b'changed')
        return original(descriptor)
    monkeypatch.setattr(inspection_io.os, 'fstat', mutate_after_read)
    with pytest.raises(ValueError, match='changed'):
        inspection_io.read_bounded(path, 16)
    assert calls == 2
