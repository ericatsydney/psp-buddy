from dataclasses import FrozenInstanceError, replace

import pytest

from psp_buddy.profile import FieldBinding, PilotInspectionProfile
from psp_buddy.reader import decode_pilot_inspection


def profile():
    return PilotInspectionProfile('synthetic-game', 'synthetic-patch', 'synthetic-emulator',
        'synthetic-pilot', 'synthetic bounded window', 0x08800000, 8,
        (FieldBinding('sp', 0, 2, ('synthetic-sp',)),
         FieldBinding('level', 4, 1, ('synthetic-level',))))


def test_decode_minimal_pilot_record():
    result = decode_pilot_inspection(profile(), bytes([17, 0, 0, 0, 23, 0, 0, 0]),
        'synthetic-game', 'synthetic-patch', 'synthetic-emulator')
    assert result.get('sp') == 17
    assert result.get('level') == 23
    assert result.get('max_sp') is None
    assert result.get('will') is None

@pytest.mark.parametrize('changes', [dict(game_id=''), dict(patch_id=' '),
    dict(emulator_version=1), dict(pilot_label=''), dict(record_window=''),
    dict(record_window='x' * 4097), dict(record_address=True), dict(record_address=0),
    dict(record_address=0x0A000000), dict(record_size=True), dict(record_size=0),
    dict(record_size=65537), dict(fields=[]), dict(fields=()),
    dict(fields=(FieldBinding('sp', 0, 2, ('synthetic',)),)),
    dict(fields=(FieldBinding('level', 0, 1, ('synthetic',)),)),
    dict(fields=(FieldBinding('hp', 0, 2, ('synthetic',)),
                 FieldBinding('sp', 2, 2, ('synthetic',)),
                 FieldBinding('level', 4, 1, ('synthetic',)))),
    dict(fields=(FieldBinding('sp', 0, 2, ('synthetic',)),
                 FieldBinding('level', 1, 1, ('synthetic',)))),
    dict(fields=(FieldBinding('sp', 0, 2, ('synthetic',)),
                 FieldBinding('sp', 2, 2, ('synthetic',)),
                 FieldBinding('level', 4, 1, ('synthetic',)))),
    dict(fields=(FieldBinding('sp', 0, 2, ('synthetic',)),
                 FieldBinding('level', 8, 1, ('synthetic',)))),
    dict(fields=(object(),)),
])
def test_pilot_profile_rejects_invalid_identity_and_layout(changes):
    with pytest.raises(ValueError):
        replace(profile(), **changes)


@pytest.mark.parametrize('identity', [('wrong', 'synthetic-patch', 'synthetic-emulator'),
    ('synthetic-game', 'wrong', 'synthetic-emulator'),
    ('synthetic-game', 'synthetic-patch', 'wrong')])
def test_wrong_decode_identity_is_rejected(identity):
    with pytest.raises(ValueError, match='identity'):
        decode_pilot_inspection(profile(), b'\x01\x00\x00\x00\x01\x00\x00\x00', *identity)


@pytest.mark.parametrize('data', [b'1234567', b'123456789', bytearray(8), '12345678'])
def test_decoder_requires_exact_bounded_immutable_bytes(data):
    with pytest.raises(ValueError, match='record'):
        decode_pilot_inspection(profile(), data,
            'synthetic-game', 'synthetic-patch', 'synthetic-emulator')


def test_decoded_level_must_be_positive():
    with pytest.raises(ValueError, match='level'):
        decode_pilot_inspection(profile(), b'\x01\x00\x00\x00\x00\x00\x00\x00',
            'synthetic-game', 'synthetic-patch', 'synthetic-emulator')


def test_optional_max_sp_bounds_current_sp():
    complete = replace(profile(), fields=profile().fields + (
        FieldBinding('max_sp', 2, 2, ('synthetic-max',)),
        FieldBinding('will', 5, 1, ('synthetic-will',))))
    data = bytes([17, 0, 41, 0, 23, 112, 0, 0])
    result = decode_pilot_inspection(complete, data,
        'synthetic-game', 'synthetic-patch', 'synthetic-emulator')
    assert result.get('max_sp') == 41
    assert result.get('will') == 112
    with pytest.raises(ValueError, match='SP'):
        decode_pilot_inspection(complete, bytes([42, 0, 41, 0, 23, 112, 0, 0]),
            'synthetic-game', 'synthetic-patch', 'synthetic-emulator')


def test_zero_sp_is_known_zero_and_not_absent():
    result = decode_pilot_inspection(profile(), b'\x00\x00\x00\x00\x01\x00\x00\x00',
        'synthetic-game', 'synthetic-patch', 'synthetic-emulator')
    assert result.get('sp') == 0
    assert result.get('max_sp') is None
    assert result.get('hp') is None


def test_pilot_profiles_and_inspections_are_frozen_and_distinct():
    selected = profile()
    with pytest.raises(FrozenInstanceError):
        selected.pilot_label = 'changed'
    result = decode_pilot_inspection(selected, b'\x01\x00\x00\x00\x01\x00\x00\x00',
        'synthetic-game', 'synthetic-patch', 'synthetic-emulator')
    with pytest.raises(FrozenInstanceError):
        result.pilot_label = 'changed'
    assert result.record_window == 'synthetic bounded window'
    assert not hasattr(result, 'pilot_id')
    assert not hasattr(result, 'units')
    assert not hasattr(result, 'legal_actions')


@pytest.mark.parametrize('evidence', [(), [], ('',), (True,)])
def test_pilot_bindings_require_immutable_nonempty_evidence(evidence):
    with pytest.raises(ValueError):
        FieldBinding('sp', 0, 2, evidence)
