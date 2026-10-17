from dataclasses import replace
from hashlib import sha256

import pytest
from test_representative_inspection import BASE, sample

from psp_buddy.positioned_inspection import (
    GeometryProfile,
    PositionedInspectionProfile,
    decode_positioned_inspection,
)
from psp_buddy.unit_pool_inspection import CodeAnchor, InspectionSpan


def positioned_sample(form=122):
    profile, spans = sample(form)
    data = bytearray(spans[0].data)
    data[0x6800:0x6804] = b"\x08\x00\x07\x00"
    data[0x6900:0x6904] = b"tile"
    data[0x126:0x12A] = b"\x03\x00\x04\x00"
    geometry = GeometryProfile(
        BASE + 0x6800,
        BASE + 0x6802,
        (CodeAnchor(BASE + 0x6900, 4, sha256(b"tile").hexdigest()),),
        ("geometry-evidence",),
    )
    return PositionedInspectionProfile(profile, geometry), (InspectionSpan(BASE, bytes(data)),)


def run(profile=None, spans=None):
    original, captured = positioned_sample()
    return decode_positioned_inspection(profile or original, spans or captured, "g", "p", "e")


def test_tiles_dimensions_and_unavailable_fields():
    result = run().to_dict()
    assert result["representatives"][0]["tile_x"] == 3
    assert result["representatives"][0]["tile_y"] == 4
    assert result["dimensions"] == {"width": 8, "height": 7}
    assert result["inspection_kind"] == "positioned_representative_inspection"
    assert result["coordinate_system"] == "zero_based_tiles"
    assert not {"x", "y", "dimensions"} & set(result["unavailable_fields"])
    assert {"side", "mv", "name", "terrain", "legal_actions"} <= set(result["unavailable_fields"])


@pytest.mark.parametrize(
    ("offset", "value"),
    [
        (0x6800, 0),
        (0x6802, 0),
        (0x6800, 1025),
        (0x6802, 1025),
        (0x6800, 147),
        (0x126, 8),
        (0x128, 7),
        (0x126, 65535),
        (0x128, 65535),
    ],
)
def test_invalid_dimensions_and_coordinates(offset, value):
    profile, spans = positioned_sample()
    data = bytearray(spans[0].data)
    data[offset : offset + 2] = value.to_bytes(2, "little")
    with pytest.raises(ValueError):
        run(profile, (InspectionSpan(BASE, bytes(data)),))


def test_largest_legal_coordinates_and_1024_cells():
    profile, spans = positioned_sample()
    data = bytearray(spans[0].data)
    data[0x6800:0x6804] = b"\x20\x00\x20\x00"
    data[0x126:0x12A] = b"\x1f\x00\x1f\x00"
    result = run(profile, (InspectionSpan(BASE, bytes(data)),)).to_dict()
    assert result["representatives"][0]["tile_x"] == 31
    assert result["dimensions"] == {"width": 32, "height": 32}


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("width_address", True),
        ("height_address", BASE + 1),
        ("width_address", 0),
        ("height_address", BASE + 0x6800),
        ("code_anchors", ()),
        ("code_anchors", []),
        ("evidence_ids", ()),
        ("evidence_ids", ["x"]),
        ("evidence_ids", ("x", "x")),
        ("evidence_ids", ("bad\n",)),
    ],
)
def test_direct_geometry_profile_rejects(field, bad):
    profile, _ = positioned_sample()
    with pytest.raises(ValueError):
        replace(profile.geometry, **{field: bad})


def test_identity_geometry_fingerprint_and_capture_reject():
    profile, spans = positioned_sample()
    with pytest.raises(ValueError):
        decode_positioned_inspection(profile, spans, "other", "p", "e")
    data = bytearray(spans[0].data)
    data[0x6900] = 0
    with pytest.raises(ValueError, match="Code anchor"):
        run(profile, (InspectionSpan(BASE, bytes(data)),))
    with pytest.raises(ValueError, match="Missing contiguous geometry"):
        run(
            profile,
            (
                InspectionSpan(BASE, spans[0].data[:0x6800]),
                InspectionSpan(BASE + 0x6804, spans[0].data[0x6804:]),
            ),
        )


def test_geometry_code_cannot_overlap_base_mutable_regions():
    profile, spans = positioned_sample()
    for address in (BASE + 0x100, BASE + 0x1318, BASE + 0x1630):
        offset = address - BASE
        anchor = CodeAnchor(address, 4, sha256(spans[0].data[offset : offset + 4]).hexdigest())
        geometry = replace(profile.geometry, code_anchors=(anchor,))
        with pytest.raises(ValueError):
            run(replace(profile, geometry=geometry), spans)


def test_shared_anchor_and_form_tile_stability_preserve_caller_profile():
    profile, spans = positioned_sample()
    shared = profile.representative_profile.code_anchors[0]
    profile = replace(
        profile,
        geometry=replace(profile.geometry, code_anchors=profile.geometry.code_anchors + (shared,)),
    )
    original = profile.representative_profile
    result = run(profile, spans).to_dict()
    other = run(*positioned_sample(123)).to_dict()
    assert original is profile.representative_profile
    assert len(original.code_anchors) == 1
    assert result["representatives"][0]["tile_x"] == other["representatives"][0]["tile_x"] == 3
    assert result["representatives"][0]["mech_id"] != other["representatives"][0]["mech_id"]
    for flag in (
        "live_authenticated",
        "autonomous_available",
        "autonomous_execution_enabled",
        "tactical_snapshot_available",
    ):
        assert result[flag] is False
    assert len(result["evidence_ids"]) == len(set(result["evidence_ids"]))


def test_empty_roster_still_requires_dimensions():
    profile, spans = positioned_sample()
    data = bytearray(spans[0].data)
    data[0x100] = data[0x108] = 0
    data[0x260C:0x2610] = (BASE + 0x2614).to_bytes(4, "little")
    data[0x2710:0x2714] = (BASE + 0x2718).to_bytes(4, "little")
    assert run(profile, (InspectionSpan(BASE, bytes(data)),)).to_dict()["representatives"] == []
    data[0x6800:0x6802] = b"\x00\x00"
    with pytest.raises(ValueError, match="dimensions"):
        run(profile, (InspectionSpan(BASE, bytes(data)),))


def test_many_representatives_join_exact_objects_and_preserve_order():
    profile, spans = positioned_sample()
    data = bytearray(spans[0].data)
    base = profile.representative_profile
    from psp_buddy.representative_inspection import InspectionRegion

    base = replace(
        base,
        pool_profile=replace(base.pool_profile, pool_capacity=2),
        node_regions=(InspectionRegion(BASE + 0x5000, 4, 12),),
    )
    profile = replace(profile, representative_profile=base)
    data[0x100] = data[0x168] = 1
    data[0x170] = 4
    data[0x18E:0x192] = b"\x07\x00\x06\x00"
    for off, val in (
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
        data[off : off + 4] = val.to_bytes(4, "little")
    result = run(profile, (InspectionSpan(BASE, bytes(data)),)).to_dict()
    assert [(r["slot_index"], r["tile_x"], r["tile_y"]) for r in result["representatives"]] == [
        (0, 3, 4),
        (1, 7, 6),
    ]


def test_geometry_recipe_union_enforces_anchor_count_and_budget():
    profile, _ = positioned_sample()
    base = profile.representative_profile
    digest = sha256(b"x").hexdigest()
    anchors = tuple(CodeAnchor(BASE + 0x10000 + i * 8, 1, digest) for i in range(32))
    base = replace(base, code_anchors=anchors)
    with pytest.raises(ValueError, match="anchors"):
        replace(profile, representative_profile=base)
    anchors = tuple(CodeAnchor(BASE + 0x10000 + i * 4096, 4096, digest) for i in range(4))
    base = replace(profile.representative_profile, code_anchors=anchors)
    with pytest.raises(ValueError, match="total"):
        replace(profile, representative_profile=base)


def test_geometry_rejects_partially_overlapping_fingerprints():
    profile, _ = positioned_sample()
    anchor = profile.representative_profile.code_anchors[0]
    geometry = replace(
        profile.geometry, code_anchors=(CodeAnchor(anchor.address + 1, 4, anchor.sha256),)
    )
    with pytest.raises(ValueError, match="Overlapping"):
        replace(profile, geometry=geometry)
