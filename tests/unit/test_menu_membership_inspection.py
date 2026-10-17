from dataclasses import replace
from hashlib import sha256

import pytest
from test_positioned_inspection import BASE, positioned_sample

from psp_buddy.menu_membership_inspection import (
    MenuMembershipInspectionProfile,
    decode_menu_membership_inspection,
)
from psp_buddy.unit_pool_inspection import CodeAnchor, InspectionSpan


def menu_sample(group=0, form=122):
    positioned, spans = positioned_sample(form)
    data = bytearray(spans[0].data)
    masks = (0x000F, 0xF000, 0x00F0, 0x0F00)
    data[0x6A00:0x6A10] = b"".join(mask.to_bytes(4, "little") for mask in masks)
    data[0x6B00:0x6B04] = b"menu"
    data[0x115] = group
    profile = MenuMembershipInspectionProfile(
        positioned,
        BASE + 0x6A00,
        masks,
        0,
        1,
        (CodeAnchor(BASE + 0x6B00, 4, sha256(b"menu").hexdigest()),),
        ("menu-evidence",),
    )
    return profile, (InspectionSpan(BASE, bytes(data)),)


def run(profile=None, spans=None):
    original, captured = menu_sample()
    return decode_menu_membership_inspection(profile or original, spans or captured, "g", "p", "e")


def test_membership_preserves_position_stats_unknown_side_and_false_flags():
    result = run().to_dict()
    row = result["representatives"][0]
    assert (row["menu_membership"], row["raw_menu_group_byte"], row["menu_category_index"]) == (
        "ally_menu",
        0,
        0,
    )
    assert (row["tile_x"], row["tile_y"], row["hp"], row["defense"]) == (3, 4, 4700, 1000)
    assert result["category_counts"] == [1, 0, 0, 0]
    assert result["ally_menu_count"] == 1
    assert result["foe_menu_count"] == result["outside_menu_count"] == 0
    assert result["label_source"] == "user_supplied_menu_label_mapping"
    assert "side" in result["unavailable_fields"]
    for flag in (
        "live_authenticated",
        "autonomous_available",
        "autonomous_execution_enabled",
        "tactical_snapshot_available",
    ):
        assert result[flag] is False


@pytest.mark.parametrize(
    "group,category,label",
    [
        (0, 0, "ally_menu"),
        (3, 0, "ally_menu"),
        (4, 2, "outside_ally_foe_menus"),
        (8, 3, "outside_ally_foe_menus"),
        (12, 1, "foe_menu"),
        (15, 1, "foe_menu"),
    ],
)
def test_category_labels_and_partition(group, category, label):
    result = run(*menu_sample(group)).to_dict()
    assert result["representatives"][0]["menu_category_index"] == category
    assert result["representatives"][0]["menu_membership"] == label
    assert (
        sum(result["category_counts"])
        == (result["ally_menu_count"] + result["foe_menu_count"] + result["outside_menu_count"])
        == 1
    )


@pytest.mark.parametrize("group", [16, 31, 32, 255])
def test_unsupported_raw_group_rejects_whole_report(group):
    with pytest.raises(ValueError, match="Unsupported raw"):
        run(*menu_sample(group))


@pytest.mark.parametrize(
    "field,bad",
    [
        ("positioned_profile", None),
        ("menu_mask_table_address", True),
        ("menu_mask_table_address", BASE + 1),
        ("menu_mask_table_address", 0x0A000000),
        ("expected_category_masks", [15, 61440, 240, 3840]),
        ("expected_category_masks", (0, 61440, 240, 3840)),
        ("expected_category_masks", (15, 61440, 240)),
        ("expected_category_masks", (True, 61440, 240, 3840)),
        ("expected_category_masks", (15, 61440, 240, 0x10000)),
        ("expected_category_masks", (15, 61440, 240, 240)),
        ("expected_category_masks", (15, 61440, 240, 256)),
        ("ally_category_index", True),
        ("ally_category_index", -1),
        ("foe_category_index", 4),
        ("foe_category_index", 0),
        ("code_anchors", []),
        ("code_anchors", ()),
        ("code_anchors", (None,)),
        ("evidence_ids", []),
        ("evidence_ids", ()),
        ("evidence_ids", ("x", "x")),
        ("evidence_ids", ("bad\n",)),
    ],
)
def test_direct_profile_strictness(field, bad):
    with pytest.raises(ValueError):
        replace(menu_sample()[0], **{field: bad})


def test_exact_table_u32_and_code_fingerprints():
    profile, spans = menu_sample()
    for offset in (0x6A00, 0x6A02, 0x6B00):
        data = bytearray(spans[0].data)
        data[offset] ^= 1
        with pytest.raises(ValueError, match="Code anchor"):
            run(profile, (InspectionSpan(BASE, bytes(data)),))
    with pytest.raises(ValueError):
        decode_menu_membership_inspection(profile, spans, "wrong", "p", "e")
    with pytest.raises(ValueError):
        run(
            profile,
            (
                InspectionSpan(BASE, spans[0].data[:0x6A00]),
                InspectionSpan(BASE + 0x6A10, spans[0].data[0x6A10:]),
            ),
        )


@pytest.mark.parametrize("offset", [0x100, 0x1318, 0x1630, 0x6800])
def test_readonly_table_cannot_overlap_mutable_regions(offset):
    original, spans = menu_sample()
    with pytest.raises(ValueError):
        run(replace(original, menu_mask_table_address=BASE + offset), spans)


def test_shared_fingerprints_and_caller_profiles_remain_unchanged():
    profile, spans = menu_sample()
    original = profile.positioned_profile
    shared = original.representative_profile.code_anchors[0]
    profile = replace(profile, code_anchors=profile.code_anchors + (shared, shared))
    result = run(profile, spans).to_dict()
    assert profile.positioned_profile is original
    assert len(original.representative_profile.code_anchors) == 1
    assert len(original.geometry.code_anchors) == 1
    assert result["representatives"][0]["hp"] == 4700
    assert result["category_masks"] == [15, 61440, 240, 3840]
    assert len(result["evidence_ids"]) == len(set(result["evidence_ids"]))


def test_anchor_partial_overlap_and_combined_budgets():
    profile, _ = menu_sample()
    existing = profile.positioned_profile.representative_profile.code_anchors[0]
    with pytest.raises(ValueError, match="Overlapping"):
        replace(profile, code_anchors=(CodeAnchor(existing.address + 1, 4, existing.sha256),))
    anchors = tuple(
        CodeAnchor(BASE + 0x10000 + i * 8, 1, sha256(b"x").hexdigest()) for i in range(31)
    )
    positioned = profile.positioned_profile
    representative = replace(positioned.representative_profile, code_anchors=anchors)
    positioned = replace(positioned, representative_profile=representative)
    with pytest.raises(ValueError, match="anchors"):
        replace(profile, positioned_profile=positioned)
    anchors = tuple(
        CodeAnchor(BASE + 0x10000 + i * 4096, 4096, sha256(b"x").hexdigest()) for i in range(4)
    )
    with pytest.raises(ValueError, match="total"):
        replace(profile, code_anchors=anchors)


def test_relabeling_is_explicit_and_other_categories_are_not_neutral():
    profile, spans = menu_sample(group=4)
    profile = replace(profile, ally_category_index=2, foe_category_index=3)
    result = run(profile, spans).to_dict()
    assert result["representatives"][0]["menu_membership"] == "ally_menu"
    profile = replace(profile, expected_category_masks=(240, 3840, 15, 61440))
    data = bytearray(spans[0].data)
    data[0x6A00:0x6A10] = b"".join(m.to_bytes(4, "little") for m in profile.expected_category_masks)
    result = run(profile, (InspectionSpan(BASE, bytes(data)),)).to_dict()
    assert result["representatives"][0]["menu_membership"] == "outside_ally_foe_menus"
    assert "side" in result["unavailable_fields"]


def test_empty_report_requires_valid_table_and_preserves_all_zero_counts():
    profile, spans = menu_sample()
    data = bytearray(spans[0].data)
    data[0x100] = data[0x108] = 0
    data[0x260C:0x2610] = (BASE + 0x2614).to_bytes(4, "little")
    data[0x2710:0x2714] = (BASE + 0x2718).to_bytes(4, "little")
    result = run(profile, (InspectionSpan(BASE, bytes(data)),)).to_dict()
    assert result["representatives"] == []
    assert result["category_counts"] == [0, 0, 0, 0]
    assert (
        result["ally_menu_count"] == result["foe_menu_count"] == result["outside_menu_count"] == 0
    )
    data[0x6A00] ^= 1
    with pytest.raises(ValueError):
        run(profile, (InspectionSpan(BASE, bytes(data)),))


def test_runtime_imports_and_file_writes_are_unavailable(monkeypatch):
    import builtins
    import sys

    profile, spans = menu_sample()
    imported = set(sys.modules)

    def poison(*args, **kwargs):
        raise AssertionError("pure decoder cannot write files")

    monkeypatch.setattr(builtins, "open", poison)
    assert run(profile, spans).to_dict()["ally_menu_count"] == 1
    assert not any(
        "controller" in name or "transport" in name for name in set(sys.modules) - imported
    )


def test_multiple_objects_join_by_address_with_different_menu_membership():
    from psp_buddy.representative_inspection import InspectionRegion

    profile, spans = menu_sample()
    data = bytearray(spans[0].data)
    positioned = profile.positioned_profile
    base = positioned.representative_profile
    base = replace(
        base,
        pool_profile=replace(base.pool_profile, pool_capacity=2),
        node_regions=(InspectionRegion(BASE + 0x5000, 4, 12),),
    )
    profile = replace(profile, positioned_profile=replace(positioned, representative_profile=base))
    data[0x100] = data[0x168] = 1
    data[0x170] = 4
    data[0x17D] = 15
    data[0x18E:0x192] = b"\x07\x00\x06\x00"
    for offset, value in (
        (0x17C, 1),
        (0x41C, BASE + 0x168),
        (0x5004, BASE + 0x500C),
        (0x500C, BASE + 0x410),
        (0x5010, BASE + 0x2614),
        (0x2710, BASE + 0x5018),
        (0x5018, BASE + 0x410),
        (0x501C, BASE + 0x5024),
        (0x5024, BASE + 0x400),
        (0x5028, BASE + 0x2718),
    ):
        data[offset : offset + 4] = value.to_bytes(4, "little")
    # The object byte is independent of the word at +0x14 used by structural occupancy.
    data[0x17D] = 15
    result = run(profile, (InspectionSpan(BASE, bytes(data)),)).to_dict()
    assert [
        (r["slot_index"], r["tile_x"], r["menu_membership"]) for r in result["representatives"]
    ] == [(0, 3, "ally_menu"), (1, 7, "foe_menu")]
    assert result["category_counts"] == [1, 1, 0, 0]


def test_base_output_is_unchanged_and_result_dictionaries_are_independent():
    from psp_buddy.positioned_inspection import decode_positioned_inspection

    profile, spans = menu_sample()
    original = decode_positioned_inspection(
        profile.positioned_profile, spans, "g", "p", "e"
    ).to_dict()
    report = run(profile, spans)
    result = report.to_dict()
    for old, new in zip(original["representatives"], result["representatives"], strict=True):
        assert all(new[key] == value for key, value in old.items())
    result["representatives"][0]["hp"] = 0
    result["category_counts"][0] = 999
    assert report.to_dict()["representatives"][0]["hp"] == 4700
    assert report.to_dict()["category_counts"] == [1, 0, 0, 0]
    assert (
        decode_positioned_inspection(profile.positioned_profile, spans, "g", "p", "e").to_dict()
        == original
    )
