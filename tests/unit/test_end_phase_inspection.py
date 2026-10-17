from dataclasses import FrozenInstanceError, replace
from hashlib import sha256

import pytest
from test_menu_membership_inspection import BASE, menu_sample

from psp_buddy.end_phase_inspection import (
    EndPhaseInspectionProfile,
    decode_end_phase_inspection,
)
from psp_buddy.unit_pool_inspection import CodeAnchor, InspectionSpan


def end_sample(counter=1, group=0):
    menu, spans = menu_sample(group)
    data = bytearray(spans[0].data)
    data[0x108] = (data[0x108] & 0xE7) | (counter << 3)
    data[0x6C00:0x6C04] = b"end!"
    profile = EndPhaseInspectionProfile(
        menu, (CodeAnchor(BASE + 0x6C00, 4, sha256(b"end!").hexdigest()),), ("count-proof",)
    )
    return profile, (InspectionSpan(BASE, bytes(data)),)


def run(profile=None, spans=None):
    original, captured = end_sample()
    return decode_end_phase_inspection(profile or original, spans or captured, "g", "p", "e")


@pytest.mark.parametrize("counter", [0, 1, 2, 3])
@pytest.mark.parametrize("group", [0, 3, 12])
def test_exact_counter_and_distinct_end_phase_scope(counter, group):
    result = run(*end_sample(counter, group)).to_dict()
    row = result["representatives"][0]
    assert row["counter_value"] == counter
    assert row["end_phase_count_scope"] is (group == 0)
    assert row["counted_as_unmoved"] is (group == 0 and counter > 0)
    assert result["end_phase_scope_count"] == int(group == 0)
    assert result["unmoved_unit_count"] == int(group == 0 and counter > 0)
    assert result["displayed_unmoved_unit_count"] == result["unmoved_unit_count"]
    assert result["ally_menu_count"] == int(group in (0, 3))
    assert "action_available" not in row and "can_move" not in row
    assert (row["hp"], row["tile_x"], row["tile_y"]) == (4700, 3, 4)
    assert result["inspection_kind"] == "end_phase_inspection"
    assert "legality" in result["counter_semantics_note"]
    assert result["live_authenticated"] is result["autonomous_available"] is False


@pytest.mark.parametrize(
    "enabled,matching,reject", [(0, True, False), (1, False, False), (1, True, True)]
)
def test_existing_relationship_filter_proves_resolver_fallback(enabled, matching, reject):
    profile, spans = end_sample()
    data = bytearray(spans[0].data)
    data[0x4008:0x400C] = (122 if matching else 999).to_bytes(4, "little", signed=True)
    data[0x400C:0x4010] = enabled.to_bytes(4, "little")
    data[0x4014:0x4018] = (134).to_bytes(4, "little", signed=True)
    if reject:
        with pytest.raises(ValueError, match="recipe/cache"):
            run(profile, (InspectionSpan(BASE, bytes(data)),))
    else:
        assert (
            run(profile, (InspectionSpan(BASE, bytes(data)),)).to_dict()["unmoved_unit_count"] == 1
        )


@pytest.mark.parametrize(
    "field,bad",
    [
        ("menu_membership_profile", None),
        ("code_anchors", []),
        ("code_anchors", ()),
        ("code_anchors", (None,)),
        ("evidence_ids", []),
        ("evidence_ids", ()),
        ("evidence_ids", ("x", "x")),
        ("evidence_ids", ("bad\n",)),
    ],
)
def test_direct_profile_validation(field, bad):
    with pytest.raises(ValueError):
        replace(end_sample()[0], **{field: bad})


def test_fingerprints_identity_missing_and_null_reject_atomically():
    profile, spans = end_sample()
    with pytest.raises(ValueError):
        decode_end_phase_inspection(profile, spans, "wrong", "p", "e")
    for offset in (0x6C00, 0x40C):
        data = bytearray(spans[0].data)
        data[offset : offset + 4] = bytes(4)
        with pytest.raises(ValueError):
            run(profile, (InspectionSpan(BASE, bytes(data)),))
    with pytest.raises(ValueError):
        run(
            profile,
            (
                InspectionSpan(BASE, spans[0].data[:0x108]),
                InspectionSpan(BASE + 0x109, spans[0].data[0x109:]),
            ),
        )


def test_frozen_profile_and_no_mutation_or_runtime_side_effects(monkeypatch):
    import builtins

    profile, spans = end_sample()
    original = profile.menu_membership_profile
    with pytest.raises(FrozenInstanceError):
        profile.evidence_ids = ("different",)

    def poison(*args, **kwargs):
        raise AssertionError("decoder must not open files")

    monkeypatch.setattr(builtins, "open", poison)
    report = run(profile, spans)
    result = report.to_dict()
    result["representatives"][0]["counter_value"] = 999
    assert report.to_dict()["representatives"][0]["counter_value"] == 1
    assert profile.menu_membership_profile is original
    assert len(original.code_anchors) == 1
    assert "count-proof" in report.to_dict()["evidence_ids"]


def test_empty_map_preserves_zero_counts_after_all_gates():
    profile, spans = end_sample()
    data = bytearray(spans[0].data)
    data[0x100] = data[0x108] = 0
    data[0x260C:0x2610] = (BASE + 0x2614).to_bytes(4, "little")
    data[0x2710:0x2714] = (BASE + 0x2718).to_bytes(4, "little")
    result = run(profile, (InspectionSpan(BASE, bytes(data)),)).to_dict()
    assert result["representatives"] == []
    assert result["end_phase_scope_count"] == result["unmoved_unit_count"] == 0
    assert result["displayed_unmoved_unit_count"] == 0
    data[0x6C00] ^= 1
    with pytest.raises(ValueError):
        run(profile, (InspectionSpan(BASE, bytes(data)),))


@pytest.mark.parametrize("count", [100, 101])
def test_validated_large_map_counts_actors_not_counter_sum_and_displays_modulo(count):
    from psp_buddy.representative_inspection import InspectionRegion

    profile, spans = end_sample()
    data = bytearray(spans[0].data) + bytearray(0x10000)
    menu = profile.menu_membership_profile
    positioned = menu.positioned_profile
    representative = positioned.representative_profile
    pool, actors, nodes = 0x14000, 0x12000, 0x10000
    structural = replace(
        representative.pool_profile,
        pool_address=BASE + pool,
        pool_capacity=count,
        actor_capacity=count,
    )
    representative = replace(
        representative,
        pool_profile=structural,
        node_regions=(InspectionRegion(BASE + nodes, count * 2, 12),),
    )
    profile = replace(
        profile,
        menu_membership_profile=replace(
            menu, positioned_profile=replace(positioned, representative_profile=representative)
        ),
    )

    def put(offset, value, size=4):
        data[offset : offset + size] = value.to_bytes(size, "little")

    put(0x30C, BASE + actors)
    put(0x314, count)
    put(0x6800, 8, 2)
    put(0x6802, 13, 2)
    for index in range(count):
        obj = pool + index * 104
        data[obj] = 1
        data[obj + 8] = 4 | (2 << 3)
        put(obj + 20, 1)
        put(obj + 0x26, index % 8, 2)
        put(obj + 0x28, index // 8, 2)
        for offset, value in (
            (0, structural.actor_vtable),
            (4, BASE + 0x1000),
            (8, BASE + 0x1100),
            (12, BASE + obj),
        ):
            put(actors + index * 16 + offset, value)
        for which, lst in ((0, 0x2600), (1, 0x2704)):
            node = nodes + (which * count + index) * 12
            put(node, BASE + actors + index * 16)
            put(node + 4, BASE + (node + 12 if index + 1 < count else lst + 20))
    put(0x260C, BASE + nodes)
    put(0x2710, BASE + nodes + count * 12)
    captures = (
        InspectionSpan(BASE, bytes(data[:65536])),
        InspectionSpan(BASE + 65536, bytes(data[65536:])),
    )
    result = run(profile, captures).to_dict()
    assert result["end_phase_scope_count"] == result["unmoved_unit_count"] == count
    assert result["displayed_unmoved_unit_count"] == count % 100
    assert all(row["counter_value"] == 2 for row in result["representatives"])


def test_partial_overlap_and_additional_layer_anchor_cap():
    profile, _ = end_sample()
    inherited = (
        profile.menu_membership_profile.positioned_profile.representative_profile.code_anchors[0]
    )
    with pytest.raises(ValueError, match="Overlapping"):
        replace(profile, code_anchors=(CodeAnchor(inherited.address + 1, 4, inherited.sha256),))
    anchors = tuple(
        CodeAnchor(BASE + 0x30000 + i * 8, 1, sha256(b"x").hexdigest()) for i in range(17)
    )
    with pytest.raises(ValueError, match="anchors"):
        replace(profile, code_anchors=anchors)


def test_combined_32_anchor_budget_and_immutable_nested_composition():
    profile, _ = end_sample()
    menu = profile.menu_membership_profile
    positioned = menu.positioned_profile
    base = positioned.representative_profile
    extra = tuple(
        CodeAnchor(BASE + 0x20000 + i * 8, 1, sha256(b"x").hexdigest()) for i in range(26)
    )
    base = replace(base, code_anchors=base.code_anchors + extra)
    menu = replace(menu, positioned_profile=replace(positioned, representative_profile=base))
    added = tuple(CodeAnchor(BASE + 0x30000 + i * 8, 1, sha256(b"x").hexdigest()) for i in range(3))
    valid = replace(profile, menu_membership_profile=menu, code_anchors=added[:2])
    combined = valid.combined_profile().combined_profile().combined_profile()
    assert len(combined.code_anchors) == 32
    assert valid.menu_membership_profile is menu and len(base.code_anchors) == 27
    with pytest.raises(ValueError, match="anchors"):
        replace(valid, code_anchors=added)


def test_combined_16k_byte_budget_boundary():
    profile, _ = end_sample()
    menu = profile.menu_membership_profile
    positioned = menu.positioned_profile
    base = positioned.representative_profile
    extra = tuple(
        CodeAnchor(BASE + 0x60000 + i * 4096, 4096, sha256(b"x").hexdigest()) for i in range(3)
    )
    base = replace(base, code_anchors=base.code_anchors + extra)
    menu = replace(menu, positioned_profile=replace(positioned, representative_profile=base))
    valid = replace(
        profile,
        menu_membership_profile=menu,
        code_anchors=(CodeAnchor(BASE + 0x70000, 4068, sha256(b"x").hexdigest()),),
    )
    assert (
        sum(
            a.size
            for a in valid.combined_profile().combined_profile().combined_profile().code_anchors
        )
        == 16384
    )
    with pytest.raises(ValueError, match="total"):
        replace(valid, code_anchors=(CodeAnchor(BASE + 0x70000, 4069, sha256(b"x").hexdigest()),))


def test_pool_fingerprints_are_included_in_global_16k_budget():
    profile, _ = end_sample()
    menu = profile.menu_membership_profile
    positioned = menu.positioned_profile
    representative = positioned.representative_profile
    pool_anchors = tuple(
        CodeAnchor(BASE + 0x80000 + i * 4096, 4096, sha256(b"x").hexdigest()) for i in range(4)
    )
    representative = replace(
        representative, pool_profile=replace(representative.pool_profile, code_anchors=pool_anchors)
    )
    menu = replace(
        menu, positioned_profile=replace(positioned, representative_profile=representative)
    )
    with pytest.raises(ValueError, match="total"):
        replace(profile, menu_membership_profile=menu)
