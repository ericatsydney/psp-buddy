from dataclasses import FrozenInstanceError, replace

import pytest

from psp_buddy.map_inspection import (
    MapField,
    MapInspectionProfile,
    MapRecordProfile,
    decode_map_inspection,
)


def profile(fields=None, dimensions=None):
    fields = fields if fields is not None else (
        MapField("unit_id", 0, 1, ("visible-info",)),
        MapField("hp", 1, 2, ("visible-info",)),
        MapField("max_hp", 3, 2, ("visible-info",)),
    )
    return MapInspectionProfile("game", "patch", "emu", "map", dimensions,
                                (MapRecordProfile("named", 0x08800000, 12, fields),))


def decode(p, samples=(b"\x01\x05\x00\x0a\x00" + bytes(7),)):
    return decode_map_inspection(p, samples, "game", "patch", "emu")


def test_partial_named_record_preserves_unknowns_and_is_immutable():
    report = decode(profile())
    record = report.records[0]
    assert (record.unit_id, record.hp, record.max_hp) == (1, 5, 10)
    assert record.x is record.y is record.side is record.sp is record.action_available is None
    assert dict(record.missing_fields)["x"]
    assert report.roster_completeness == "named_records_only"
    assert report.live_authenticated is report.autonomous_available is False
    with pytest.raises(FrozenInstanceError):
        record.hp = 3


def test_explicit_coordinates_and_enums():
    fields = (
        MapField("x", 0, 1, ("reload",)), MapField("y", 1, 1, ("reload",)),
        MapField("side", 2, 1, ("reload",), ((7, "ally"),)),
        MapField("action_available", 3, 1, ("reload",), ((9, "spent"),)),
    )
    record = decode(profile(fields, (4, 5)), (bytes([3, 4, 7, 9]) + bytes(8),)).records[0]
    assert (record.x, record.y, record.side, record.action_available) == (3, 4, "ally", False)
    with pytest.raises(ValueError):
        decode(profile(fields, (4, 5)), (bytes([4, 4, 7, 9]) + bytes(8),))
    with pytest.raises(ValueError):
        decode(profile(fields, (4, 5)), (bytes([3, 4, 0, 9]) + bytes(8),))


def test_identity_and_immutable_exact_samples():
    p = profile()
    for samples in ((b"short",), (bytearray(12),), [], (), (bytes(12), bytes(12))):
        with pytest.raises(ValueError):
            decode(p, samples)
    with pytest.raises(ValueError):
        decode_map_inspection(p, (bytes(12),), "other", "patch", "emu")


def test_bad_layouts_evidence_and_enums():
    for kwargs in (
        {"name": "deployment"}, {"offset": True}, {"width": 3},
        {"evidence_ids": ()}, {"evidence_ids": ("same", "same")},
        {"meanings": ((0, "ally"),)},
    ):
        with pytest.raises(ValueError):
            MapField(**({"name": "hp", "offset": 0, "width": 2,
                         "evidence_ids": ("e",)} | kwargs))
    for meanings in ((), ((0, "bad"),), ((0, "ally"), (0, "enemy")),
                     ((0, "ally"), (1, "ally")), ((True, "ally"),)):
        with pytest.raises(ValueError):
            MapField("side", 0, 1, ("e",), meanings)
    for fields in (
        (MapField("hp", 11, 2, ("e",)),),
        (MapField("hp", 0, 2, ("e",)), MapField("max_hp", 1, 2, ("e",))),
        (MapField("hp", 0, 2, ("e",)), MapField("hp", 2, 2, ("e",))),
    ):
        with pytest.raises(ValueError):
            profile(fields)


def test_profile_limits_and_windows():
    for dimensions in ((True, 3), (0, 3), (3, 1025), [3, 3]):
        with pytest.raises(ValueError):
            profile(dimensions=dimensions)
    p = profile()
    for kwargs in ({"label": ""}, {"address": 0x087FFFFF}, {"size": 65537}):
        with pytest.raises(ValueError):
            replace(p.records[0], **kwargs)


def test_duplicate_ids_resources_and_pair_requirements():
    p = profile()
    second = replace(p.records[0], label="second", address=0x08800020)
    for records in ((p.records[0], p.records[0]),
                    (p.records[0], replace(second, address=0x08800001)),
                    tuple(replace(second, label=str(i), address=0x08800100 + i * 16)
                          for i in range(257))):
        with pytest.raises(ValueError):
            replace(p, records=records)
    with pytest.raises(ValueError):
        decode(replace(p, records=(p.records[0], second)),
               (b"\x01\x05\x00\x0a\x00" + bytes(7),) * 2)
    for hp, maximum in ((11, 10), (0, 0)):
        with pytest.raises(ValueError):
            decode(p, (bytes([1, hp, 0, maximum, 0]) + bytes(7),))
    with pytest.raises(ValueError):
        profile((MapField("x", 0, 1, ("e",)),), (3, 3))
    with pytest.raises(ValueError):
        profile((MapField("x", 0, 1, ("e",)), MapField("y", 1, 1, ("e",))))


def test_total_memory_limit_and_mutable_profile_inputs():
    p = profile()
    records = tuple(MapRecordProfile(str(i), 0x08800000 + i * 65536, 65536, ())
                    for i in range(16))
    assert len(replace(p, records=records).records) == 16
    with pytest.raises(ValueError):
        replace(p, records=records + (MapRecordProfile("extra", 0x08900000, 1, ()),))
    for changes in ({"records": list(p.records)}, {"game_id": " "},
                    {"map_label": "x" * 257}):
        with pytest.raises(ValueError):
            replace(p, **changes)
    for changes in ({"address": True}, {"size": False}, {"fields": []}):
        with pytest.raises(ValueError):
            replace(p.records[0], **changes)
    with pytest.raises(ValueError):
        MapField("hp", 0, 1, ["mutable"])
    with pytest.raises(ValueError):
        MapField("side", 0, 1, ("e",), ((256, "ally"),))


def test_zero_capacity_en_and_sp_are_valid_but_cannot_be_exceeded():
    fields = tuple(MapField(name, index, 1, ("e",))
                   for index, name in enumerate(("en", "max_en", "sp", "max_sp")))
    record = decode(profile(fields), (bytes(12),)).records[0]
    assert (record.en, record.max_en, record.sp, record.max_sp) == (0, 0, 0, 0)
    for sample in (bytes([1, 0, 0, 0]) + bytes(8), bytes([0, 0, 1, 0]) + bytes(8)):
        with pytest.raises(ValueError):
            decode(profile(fields), (sample,))


def test_empty_field_profile_reports_every_field_unknown():
    record = decode(profile(()), (bytes(12),)).records[0]
    assert record.hp is record.unit_id is record.x is record.action_available is None
    assert len(record.missing_fields) == 11
