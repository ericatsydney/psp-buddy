from dataclasses import replace
from hashlib import sha256

import pytest

from psp_buddy.unit_pool_inspection import (
    CodeAnchor,
    InspectionSpan,
    UnitPoolInspectionProfile,
    decode_unit_pool_inspection,
)

P = 0x08801000
OWNER = 0x08802000
A = 0x08803000
C = 0x08804000
V = 0x08805000


def fixture():
    pool = bytearray(104 * 3)
    pool[104] = 2
    put(pool, 104 + 20, 0x401)
    put(pool, 104 + 24, 112)
    put(pool, 104 + 28, 176)
    put(pool, 20, 1)  # Empty-but-active must not become a candidate.
    pool[208] = 1  # Occupied-but-inactive must not become a candidate.
    owner = bytearray(28)
    for offset, value in ((8, 0x08806000), (12, A), (16, 16), (20, 4)):
        put(owner, offset, value)
    actors = bytearray(64)
    for row, mech, pilot in ((0, 0x08807000, 0x08808000),
                             (2, 0x08807004, 0x08808004)):
        for offset, value in ((0, V), (4, mech), (8, pilot), (12, P + 104)):
            put(actors, row * 16 + offset, value)
    # Excluded slot permits null descriptors.
    put(actors, 16, V)
    put(actors, 28, P + 208)
    profile = UnitPoolInspectionProfile(
        'g', 'p', 'e', 'synthetic', P, 3, 104, OWNER, 0x08806000, 16, 4, V,
        ('synthetic-evidence',), (CodeAnchor(C, 4, sha256(b'code').hexdigest()),),
    )
    return profile, (InspectionSpan(P, bytes(pool)), InspectionSpan(OWNER, bytes(owner)),
                     InspectionSpan(A, bytes(actors)), InspectionSpan(C, b'code'))


def put(data, offset, value):
    data[offset:offset + 4] = value.to_bytes(4, 'little')


def decode(profile=None, spans=None):
    original, samples = fixture()
    return decode_unit_pool_inspection(profile or original, spans or samples, 'g', 'p', 'e')


def changed_span(index, offset, value):
    profile, spans = fixture()
    data = bytearray(spans[index].data)
    put(data, offset, value)
    replacement = (InspectionSpan(spans[index].address, bytes(data)),)
    return profile, spans[:index] + replacement + spans[index+1:]


def test_candidate_aliases_exclusions_and_precise_report():
    report = decode().to_dict()
    assert set(report) == {'inspection_kind', 'mode', 'game_id', 'patch_id',
        'emulator_version', 'map_label', 'provenance', 'roster_completeness',
        'live_authenticated', 'autonomous_available', 'autonomous_execution_enabled',
        'tactical_snapshot_available', 'candidate_count', 'slot_capacity', 'exclusions',
        'slots', 'unavailable_fields'}
    assert report['candidate_count'] == 1
    assert report['exclusions'] == {'empty_slots': 1, 'inactive_slots': 1,
                                    'empty_slots_with_active_bit': 1}
    slot = report['slots'][0]
    assert set(slot) == {'slot_index', 'object_address', 'occupancy_references',
                         'raw_state_word', 'raw_pixel_pair', 'actor_bindings', 'ambiguities'}
    assert set(slot['actor_bindings'][0]) == {
        'actor_address', 'mech_descriptor_address', 'pilot_descriptor_address'}
    assert set(report['unavailable_fields']) == {
        'unit_id', 'hp', 'max_hp', 'en', 'max_en', 'sp', 'max_sp', 'x', 'y', 'side',
        'action_available', 'dimensions', 'phase', 'terrain', 'legal_actions'}
    assert slot['slot_index'] == 1
    assert slot['raw_state_word'] == 0x401
    assert slot['raw_pixel_pair'] == [112, 176]
    assert [a['actor_address'] for a in slot['actor_bindings']] == [A, A + 32]
    assert slot['ambiguities'] == {'mech_descriptor_addresses': [0x08807000, 0x08807004],
                                   'pilot_descriptor_addresses': [0x08808000, 0x08808004]}
    assert report['roster_completeness'] == 'candidate_slots_only'
    for key in ('live_authenticated', 'autonomous_available',
                'autonomous_execution_enabled', 'tactical_snapshot_available'):
        assert report[key] is False
    assert set(report['unavailable_fields'].values()) == {'not_decoded_by_structural_inspector'}


@pytest.mark.parametrize(('field', 'bad'), [
    ('pool_stride', 103), ('pool_capacity', True), ('pool_capacity', 0),
    ('pool_capacity', 257), ('actor_capacity', 1025), ('actor_capacity', 0),
    ('actor_stride', 32), ('pool_address', P + 1), ('actor_owner_address', 0x0A000000),
    ('actor_node_array_address', 0), ('actor_vtable', V + 1),
    ('evidence_ids', ()), ('evidence_ids', ('x', 'x')), ('evidence_ids', ['x']),
    ('game_id', 'x\n'), ('map_label', ' '), ('patch_id', 'x' * 257),
    ('code_anchors', ()), ('code_anchors', []),
])
def test_profile_rejects_invalid_direct_values(field, bad):
    profile, _ = fixture()
    with pytest.raises(ValueError):
        decode(replace(profile, **{field: bad}))


@pytest.mark.parametrize(('index', 'offset', 'value'), [
    (1, 8, 0x08806004), (1, 16, 32), (1, 20, 3), (1, 12, A + 1),
    (1, 12, 0x09FFFFF0), (1, 12, P), (0, 104, 3),
    (2, 12, P + 1), (2, 12, P + 312), (2, 4, 0), (2, 8, 0x08808001),
])
def test_inconsistent_observation_fails(index, offset, value):
    profile, spans = changed_span(index, offset, value)
    with pytest.raises(ValueError):
        decode(profile, spans)


def test_identity_and_code_mismatch_fail():
    profile, spans = fixture()
    with pytest.raises(ValueError):
        decode_unit_pool_inspection(profile, spans, 'wrong', 'p', 'e')
    with pytest.raises(ValueError):
        decode(profile, spans[:-1] + (InspectionSpan(C, b'nope'),))


def test_missing_overlap_cross_gap_and_mutable_spans_fail():
    profile, spans = fixture()
    bad_samples = [spans[:-1], spans + (spans[0],), list(spans), (),
                   spans[:1] + (InspectionSpan(OWNER, spans[1].data[:14]),
                                InspectionSpan(OWNER+14, spans[1].data[14:])) + spans[2:]]
    for bad in bad_samples:
        with pytest.raises(ValueError):
            decode_unit_pool_inspection(profile, bad, 'g', 'p', 'e')
    with pytest.raises(ValueError):
        InspectionSpan(P, bytearray(b'x'))


@pytest.mark.parametrize(('address', 'size', 'digest'), [
    (C, 0, '0'*64), (C, 4097, '0'*64), (0, 4, '0'*64),
    (C, 4, 'z'*64), (C, 4, 'a'*63), (C, True, 'a'*64),
])
def test_bad_anchors_fail(address, size, digest):
    with pytest.raises(ValueError):
        CodeAnchor(address, size, digest)


def test_empty_candidate_pool_and_repeated_aliases():
    profile, spans = fixture()
    pool = bytearray(spans[0].data)
    pool[104] = 0
    empty = decode(profile, (InspectionSpan(P, bytes(pool)),) + spans[1:]).to_dict()
    assert empty['slots'] == []
    assert empty['candidate_count'] == 0
    profile, repeated = changed_span(2, 36, 0x08807000)
    _, repeated2 = changed_span(2, 40, 0x08808000)
    data = bytearray(repeated[2].data)
    data[40:44] = repeated2[2].data[40:44]
    result = decode(profile, repeated[:2] + (InspectionSpan(A, bytes(data)),) + repeated[3:])
    assert len(result.to_dict()['slots'][0]['actor_bindings']) == 2
    assert result.to_dict()['slots'][0]['ambiguities'] == {
        'mech_descriptor_addresses': [], 'pilot_descriptor_addresses': []}

@pytest.mark.parametrize(('address', 'data'), [
    (P, b''), (P, b'x' * 65537), (P, bytearray(b'x')), (True, b'x'),
    (0x087FFFFF, b'x'), (0x09FFFFFF, b'xx'),
], ids=['empty', 'oversized', 'mutable', 'bool-address', 'below-ram', 'overflow'])
def test_span_type_size_and_ram_limits(address, data):
    with pytest.raises(ValueError):
        InspectionSpan(address, data)


def test_span_count_and_total_limits_are_enforced_before_reads():
    profile, _ = fixture()
    spans = tuple(InspectionSpan(0x08900000 + index * 65536, b'x' * 65536)
                  for index in range(17))
    for excessive in (spans, (InspectionSpan(P, b'x'),) * 33):
        with pytest.raises(ValueError):
            decode_unit_pool_inspection(profile, excessive, 'g', 'p', 'e')


def test_profile_anchor_overlap_count_total_and_data_overlap():
    profile, _ = fixture()
    anchor = profile.code_anchors[0]
    excessive_total = tuple(CodeAnchor(0x08900000 + i * 4096, 4096, '0' * 64)
                            for i in range(5))
    for anchors in ((anchor, anchor), (anchor,) * 9, excessive_total,
                    (CodeAnchor(P, 4, '0' * 64),),
                    (CodeAnchor(OWNER, 4, '0' * 64),)):
        with pytest.raises(ValueError):
            replace(profile, code_anchors=anchors)
    with pytest.raises(ValueError):
        replace(profile, actor_owner_address=P)
    with pytest.raises(ValueError):
        replace(profile, evidence_ids=tuple(str(i) for i in range(33)))


def test_dynamic_actor_window_cannot_overlap_anchor_or_owner():
    for base in (C, OWNER):
        profile, spans = changed_span(1, 12, base)
        with pytest.raises(ValueError):
            decode(profile, spans)


def test_alias_count_too_few_or_many_rejects_entire_result():
    for reference_count in (1, 3):
        profile, spans = fixture()
        data = bytearray(spans[0].data)
        data[104] = reference_count
        with pytest.raises(ValueError):
            decode(profile, (InspectionSpan(P, bytes(data)),) + spans[1:])


def test_wrong_vtable_and_null_object_are_ignored():
    profile, spans = fixture()
    actors = bytearray(spans[2].data)
    # An unrelated row may contain arbitrary pointers.
    for offset in (48, 52, 56, 60):
        put(actors, offset, 0xFFFFFFFF)
    assert decode(profile, spans[:2] + (InspectionSpan(A, bytes(actors)),) + spans[3:])
    put(actors, 48, V)
    put(actors, 60, 0)
    assert decode(profile, spans[:2] + (InspectionSpan(A, bytes(actors)),) + spans[3:])


def test_empty_inactive_and_candidate_accounting_all_raw_states():
    profile, spans = fixture()
    for empty_state in (0, 1):
        pool = bytearray(spans[0].data)
        put(pool, 20, empty_state)
        result = decode(profile, (InspectionSpan(P, bytes(pool)),) + spans[1:]).to_dict()
        assert result['candidate_count'] + result['exclusions']['empty_slots'] + (
            result['exclusions']['inactive_slots']) == result['slot_capacity']
        assert result['exclusions']['empty_slots_with_active_bit'] == empty_state
    for state in (1, 0x401, 0xC01, 0xFFFFFFFF):
        profile, updated = changed_span(0, 124, state)
        assert decode(profile, updated).to_dict()['slots'][0]['raw_state_word'] == state


def test_arbitrary_span_order_and_larger_covering_window_are_supported():
    profile, spans = fixture()
    assert decode(profile, tuple(reversed(spans))).to_dict() == decode().to_dict()
    covering = InspectionSpan(P - 4, b'head' + spans[0].data + b'tail')
    assert decode(profile, (covering,) + spans[1:]).to_dict() == decode().to_dict()


def test_report_returns_fresh_serialized_containers():
    report = decode()
    first = report.to_dict()
    first['slots'].clear()
    first['unavailable_fields']['side'] = 'ally'
    assert len(report.to_dict()['slots']) == 1
    assert report.to_dict()['unavailable_fields']['side'] == 'not_decoded_by_structural_inspector'


def test_anchor_digest_case_normalizes_and_objects_are_frozen():
    from dataclasses import FrozenInstanceError

    profile, spans = fixture()
    upper = replace(profile.code_anchors[0], sha256=profile.code_anchors[0].sha256.upper())
    assert upper.sha256 == profile.code_anchors[0].sha256
    assert decode(replace(profile, code_anchors=(upper,)), spans)
    for value, attribute in ((profile, 'pool_capacity'), (spans[0], 'address'),
                             (decode(), 'slot_capacity')):
        with pytest.raises(FrozenInstanceError):
            setattr(value, attribute, 999)
