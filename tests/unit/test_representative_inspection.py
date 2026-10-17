from dataclasses import replace
from hashlib import sha256

import pytest

from psp_buddy.representative_inspection import (
    InspectionRegion,
    RepresentativeInspectionProfile,
    decode_representative_inspection,
)
from psp_buddy.unit_pool_inspection import CodeAnchor, InspectionSpan, UnitPoolInspectionProfile

BASE = 0x08810000


def sample(form=122):
    data = bytearray(0x9000)

    def put(offset, value, size=4):
        data[offset : offset + size] = value.to_bytes(size, "little", signed=value < 0)

    pool, owner, actors, code = 0x100, 0x300, 0x400, 0x800
    data[pool] = 2
    data[pool + 8] = 4
    put(pool + 20, 1)
    for off, val in ((8, BASE + 0x900), (12, BASE + actors), (16, 16), (20, 2)):
        put(owner + off, val)
    for i in range(2):
        for off, val in (
            (0, BASE + 0x880),
            (4, BASE + 0x1000 + i * 12),
            (8, BASE + 0x1100),
            (12, BASE + pool),
        ):
            put(actors + i * 16 + off, val)
        put(0x1000 + i * 12, BASE + 0x1200 + i * 4)
        put(0x1004 + i * 12, BASE + 0x1300 + i * 0x100)
        put(0x1200 + i * 4, 122 + i, 2)
        rec = 0x1310 + i * 0x100
        for off, val, size in (
            (0x18, 5000, 4),
            (0x1C, 4700, 4),
            (0x20, 200, 2),
            (0x22, 190, 2),
            (0xA, 1000 - i * 100, 2),
            (8, 115 + i * 10, 2),
            (6, 6 + i * 2, 2),
        ):
            put(rec + off, val, size)
    put(0x1100, BASE + 0x1500)
    put(0x1104, BASE + 0x1600)
    put(0x1500, 134, 2)
    put(0x1608 + 0x3C, 70, 2)
    data[code : code + 4] = b"code"
    # source: u(u(u(u(u(root)+4))+4))+4)
    for off, val in (
        (0x2000, 0x2100),
        (0x2104, 0x2200),
        (0x2200, 0x2300),
        (0x2304, 0x2400),
        (0x2400, 0x2500),
        (0x2504, 0x2600),
        (0x2010, 0x2700),
        (0x2020, 0x2800),
        (0x2804, 0x3000),
        (0x2030, 0x2900),
        (0x2904, 0x4000),
    ):
        put(off, BASE + val)
    selected = actors + (form - 122) * 16
    for lst, node in ((0x2600, 0x5000), (0x2704, 0x500C)):
        put(lst + 12, BASE + node)
        put(node, BASE + selected)
        put(node + 4, BASE + lst + 20)
    for i in range(154):
        put(0x6000 + i * 4, -1)
    for i in range(90):
        put(0x3000 + i * 8, -1)
        put(0x3004 + i * 8, -1)
    anchor = CodeAnchor(BASE + code, 4, sha256(b"code").hexdigest())
    structural = UnitPoolInspectionProfile(
        "g",
        "p",
        "e",
        "synthetic",
        BASE + pool,
        1,
        104,
        BASE + owner,
        BASE + 0x900,
        16,
        2,
        BASE + 0x880,
        ("evidence",),
        (anchor,),
    )
    profile = RepresentativeInspectionProfile(
        structural,
        BASE + 0x2000,
        BASE + 0x2010,
        BASE + 0x6000,
        BASE + 0x2020,
        BASE + 0x2030,
        (InspectionRegion(BASE + 0x5000, 2, 12),),
        InspectionRegion(BASE + 0x1000, 2, 12),
        InspectionRegion(BASE + 0x1100, 1, 8),
        (anchor,),
        ("recipe",),
    )
    return profile, (InspectionSpan(BASE, bytes(data)),)


def test_selected_form_resources_and_no_capability():
    profile, spans = sample()
    report = decode_representative_inspection(profile, spans, "g", "p", "e").to_dict()
    row = report["representatives"][0]
    assert (row["mech_id"], row["pilot_id"], row["hp"], row["defense"]) == (122, 134, 4700, 1000)
    assert row["alias_count"] == 2
    assert report["autonomous_available"] is False


def changed(address, value, size=4, form=122):
    profile, spans = sample(form)
    data = bytearray(spans[0].data)
    offset = address - BASE
    data[offset : offset + size] = value.to_bytes(size, "little", signed=value < 0)
    return profile, (InspectionSpan(BASE, bytes(data)),)


def run(profile=None, spans=None):
    original, captured = sample()
    return decode_representative_inspection(profile or original, spans or captured, "g", "p", "e")


@pytest.mark.parametrize(
    ("address", "value", "size"),
    [
        (BASE + 0x5004, BASE + 0x5000, 4),  # cycle
        (BASE + 0x260C, BASE + 0x5001, 4),  # off-stride node
        (BASE + 0x5000, BASE + 0x401, 4),  # unknown actor
        (BASE + 0x500C, BASE + 0x410, 4),  # stale cache
        (BASE + 0x40C, BASE + 0x101, 4),  # invalid object
        (BASE + 0x404, 0, 4),
        (BASE + 0x404, BASE + 0x1004, 4),
        (BASE + 0x1000, 0, 4),
        (BASE + 0x1004, 0, 4),
        (BASE + 0x1200, 2048, 2),
        (BASE + 0x1200, -1, 2),
        (BASE + 0x6000, 2, 4),  # unsorted
        (BASE + 0x3000, 122, 4),  # second phase duplicate once matching pilot below
        (BASE + 0x3000, 2048, 4),
        (BASE + 0x1310 + 0x18, 0, 4),
        (BASE + 0x1310 + 0x1C, 5001, 4),
        (BASE + 0x1310 + 0x22, 201, 2),
        (BASE + 0x1004, BASE + 0x1301, 4),
        (BASE + 0x1004, BASE + 0x5000, 4),
    ],
)
def test_bad_observation_rejects(address, value, size):
    if address == BASE + 0x3000 and value == 122:
        profile, spans = changed(address, value, size)
        data = bytearray(spans[0].data)
        data[0x3004:0x3008] = (134).to_bytes(4, "little")
        spans = (InspectionSpan(BASE, bytes(data)),)

    else:
        profile, spans = changed(address, value, size)
    with pytest.raises(ValueError):
        run(profile, spans)


def test_round_trip_changes_form_record_and_restores_every_field():
    reports = [run(*sample(form)).to_dict() for form in (122, 123, 122)]
    assert reports[0] == reports[2]
    first, second = [r["representatives"][0] for r in reports[:2]]
    assert first["object_address"] == second["object_address"]
    assert first["pilot_id"] == second["pilot_id"] == 134
    assert [first["mech_id"], second["mech_id"]] == [122, 123]
    assert [first["mobility"], second["mobility"]] == [115, 125]
    assert first["actor_address"] != second["actor_address"]
    assert first["mech_record_address"] != second["mech_record_address"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_root_global", True),
        ("cache_owner_global", 0),
        ("selector_owner_global", BASE + 1),
        ("node_regions", ()),
        ("node_regions", []),
        ("evidence_ids", ()),
        ("evidence_ids", ("same", "same")),
        ("evidence_ids", ["a"]),
        ("code_anchors", ()),
        ("code_anchors", []),
        ("mech_descriptors", InspectionRegion(BASE + 0x1000, 2, 8)),
        ("pilot_descriptors", InspectionRegion(BASE + 0x1100, 1, 12)),
        ("node_regions", (InspectionRegion(BASE + 0x5000, 1665, 12),)),
    ],
)
def test_invalid_direct_profile_rejects(field, value):
    profile, _ = sample()
    with pytest.raises(ValueError):
        replace(profile, **{field: value})


def test_absent_selector_and_unused_partially_populated_pair_are_ignored():
    profile, spans = changed(BASE + 0x3004, 134)
    assert run(profile, spans).reconstructed_count == 1
    profile, spans = changed(BASE + 0x3000, 133)
    assert run(profile, spans).reconstructed_count == 1


def test_no_implicit_spanning_across_adjacent_capture_windows():
    profile, spans = sample()
    data = spans[0].data
    with pytest.raises(ValueError):
        run(
            profile,
            (InspectionSpan(BASE, data[:0x13A]), InspectionSpan(BASE + 0x13A, data[0x13A:])),
        )


def test_more_than_32_spans_accepted_without_weakening_structural_limit():
    profile, spans = sample()
    extra = tuple(InspectionSpan(BASE + 0x10000 + i * 4, b"x") for i in range(40))
    assert run(profile, spans + extra).reconstructed_count == 1
    with pytest.raises(ValueError):
        run(profile, spans + extra * 4)


def test_identity_anchor_and_mutable_collection_reject():
    profile, spans = sample()
    with pytest.raises(ValueError):
        decode_representative_inspection(profile, spans, "wrong", "p", "e")
    profile, spans = changed(BASE + 0x800, 0)
    with pytest.raises(ValueError):
        run(profile, spans)
    with pytest.raises(ValueError):
        run(sample()[0], list(sample()[1]))


def test_output_provenance_and_unavailable_contract():
    profile, spans = sample()
    result = run(profile, spans).to_dict()
    assert result["spans"] == [
        {"address": BASE, "size": 0x9000, "sha256": sha256(spans[0].data).hexdigest()}
    ]
    for flag in (
        "live_authenticated",
        "autonomous_available",
        "autonomous_execution_enabled",
        "tactical_snapshot_available",
    ):
        assert result[flag] is False
    assert {"name", "mv", "max_sp", "x", "y", "side", "legal_actions"} <= set(
        result["unavailable_fields"]
    )


def test_enabled_exclusion_removes_phase_duplicates_before_duplicate_rejection():
    profile, spans = sample()
    data = bytearray(spans[0].data)
    data[0x100] = 0  # empty candidate pool; source-only rows are allowed
    data[0x3000:0x3008] = (122).to_bytes(4, "little") + (134).to_bytes(4, "little")
    for offset, value in ((0x4008, 122), (0x400C, 1), (0x4014, 134), (0x2710, BASE + 0x2704 + 20)):
        data[offset : offset + 4] = value.to_bytes(4, "little")
    result = run(profile, (InspectionSpan(BASE, bytes(data)),)).to_dict()
    assert result["representatives"] == []
    assert result["source_count"] == 1
    assert result["cache_count"] == result["reconstructed_count"] == 0


def test_two_phase_selector_can_supply_blocked_actor():
    profile, spans = sample()
    data = bytearray(spans[0].data)
    for i in range(154):
        data[0x6000 + i * 4 : 0x6004 + i * 4] = (122).to_bytes(4, "little")
    data[0x3000:0x3008] = (122).to_bytes(4, "little") + (134).to_bytes(4, "little")
    assert run(profile, (InspectionSpan(BASE, bytes(data)),)).reconstructed_count == 1


def test_ambiguous_source_pair_rejects_even_when_cache_plausible():
    profile, spans = sample()
    data = bytearray(spans[0].data)
    data[0x1204:0x1206] = (122).to_bytes(2, "little")
    # Two distinct source actor nodes; separate third cache node.
    profile = replace(profile, node_regions=(InspectionRegion(BASE + 0x5000, 3, 12),))
    for offset, value in (
        (0x5004, BASE + 0x500C),
        (0x500C, BASE + 0x410),
        (0x5010, BASE + 0x2614),
        (0x2710, BASE + 0x5018),
        (0x5018, BASE + 0x400),
        (0x501C, BASE + 0x2718),
        (0x3000, 122),
        (0x3004, 134),
    ):
        data[offset : offset + 4] = value.to_bytes(4, "little")
    with pytest.raises(ValueError, match="Ambiguous selector"):
        run(profile, (InspectionSpan(BASE, bytes(data)),))


def test_profile_rejects_declared_mutable_region_overlapping_anchor():
    profile, _ = sample()
    with pytest.raises(ValueError):
        replace(profile, code_anchors=(CodeAnchor(BASE + 0x1000, 4, sha256(b"xxxx").hexdigest()),))


@pytest.mark.parametrize("count", [0, 1, 12, 26, 69])
def test_variable_candidate_counts_and_shared_pilot_records(count):
    profile, spans = sample()
    data = bytearray(spans[0].data) + bytearray(0x10000)

    def put(offset, value):
        data[offset : offset + 4] = value.to_bytes(4, "little")

    pool, actors, nodes = 0x14000, 0x12000, 0x10000
    capacity = max(count, 1)
    p = replace(
        profile.pool_profile,
        pool_address=BASE + pool,
        pool_capacity=capacity,
        actor_capacity=capacity,
    )
    profile = replace(
        profile, pool_profile=p, node_regions=(InspectionRegion(BASE + nodes, capacity * 2, 12),)
    )
    put(0x30C, BASE + actors)
    put(0x314, capacity)
    for index in range(count):
        obj = pool + index * 104
        data[obj] = 1
        data[obj + 8] = 4
        put(obj + 20, 1)
        for off, val in (
            (0, p.actor_vtable),
            (4, BASE + 0x1000),
            (8, BASE + 0x1100),
            (12, BASE + obj),
        ):
            put(actors + index * 16 + off, val)
        for which, lst in ((0, 0x2600), (1, 0x2704)):
            node = nodes + (which * capacity + index) * 12
            put(node, BASE + actors + index * 16)
            put(node + 4, BASE + (node + 12 if index + 1 < count else lst + 20))
    put(0x260C, BASE + (nodes if count else 0x2614))
    put(0x2710, BASE + (nodes + capacity * 12 if count else 0x2718))
    captures = (
        InspectionSpan(BASE, bytes(data[:65536])),
        InspectionSpan(BASE + 65536, bytes(data[65536:])),
    )
    result = run(profile, captures)
    assert len(result.representatives) == count
    assert [row.slot_index for row in result.representatives] == list(range(count))
    assert result.source_count == result.cache_count == result.reconstructed_count == count
    assert {row.sp for row in result.representatives} <= {70}


def test_two_node_allocations_may_total_2688_with_separate_traversal_bound():
    profile, _ = sample()
    expanded = replace(
        profile,
        node_regions=(
            InspectionRegion(BASE + 0x20000, 1024, 12),
            InspectionRegion(BASE + 0x30000, 1664, 12),
        ),
    )
    assert sum(region.capacity for region in expanded.node_regions) == 2688


@pytest.mark.parametrize("enabled", [0, 1])
def test_exclusion_table_signed_ids_are_not_selector_id_schema(enabled):
    profile, spans = sample()
    data = bytearray(spans[0].data)
    for off, val in ((0x4008, 9000), (0x400C, enabled), (0x4014, -50)):
        data[off : off + 4] = val.to_bytes(4, "little", signed=True)
    assert run(profile, (InspectionSpan(BASE, bytes(data)),)).reconstructed_count == 1


def test_adjacent_packed_mech_records_allow_unused_capture_tail_overlap():
    profile, spans = sample()
    data = bytearray(spans[0].data)
    data[0x1010:0x1014] = (BASE + 0x1350).to_bytes(4, "little")
    data[0x1360:0x13B0] = data[0x1410:0x1460]
    assert run(profile, (InspectionSpan(BASE, bytes(data)),)).reconstructed_count == 1


@pytest.mark.parametrize("header", [BASE + 0x1310, BASE + 0x1314])
def test_packed_records_still_reject_interpreted_field_collisions(header):
    profile, spans = changed(BASE + 0x1010, header)
    with pytest.raises(ValueError, match="Conflicting semantic"):
        run(profile, spans)


def test_complete_mech_capture_is_required_beyond_interpreted_fields():
    profile, spans = sample()
    data = spans[0].data
    captures = (InspectionSpan(BASE, data[:0x1340]), InspectionSpan(BASE + 0x1340, data[0x1340:]))
    with pytest.raises(ValueError, match="Missing contiguous"):
        run(profile, captures)
