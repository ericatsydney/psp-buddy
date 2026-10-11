from dataclasses import FrozenInstanceError, replace

import pytest

from psp_buddy.profile import FieldBinding, InspectionProfile
from psp_buddy.reader import decode_inspection


def profile() -> InspectionProfile:
    return InspectionProfile("game", "patch", "version", "unit", 0x08800000, 32, (
        FieldBinding("hp", 0, 4, ("screen",)),
        FieldBinding("max_hp", 4, 4, ("screen",)),
        FieldBinding("en", 8, 2, ("screen",)),
        FieldBinding("max_en", 10, 2, ("screen",)),
    ))


def decode(p: InspectionProfile, data: bytes):  # type: ignore[no-untyped-def]
    return decode_inspection(p, data, "game", "patch", "version")


def record(hp: int = 5000, maximum: int = 5000, en: int = 121, max_en: int = 210) -> bytes:
    return (hp.to_bytes(4, "little") + maximum.to_bytes(4, "little")
            + en.to_bytes(2, "little") + max_en.to_bytes(2, "little") + bytes(20))


def test_inspection_decodes_without_inventing_optional_stats() -> None:
    result = decode(profile(), record())
    assert result.values == (("hp", 5000), ("max_hp", 5000), ("en", 121), ("max_en", 210))
    assert result.get("sp") is None
    assert result.unit_label == "unit"
    with pytest.raises(FrozenInstanceError):
        result.unit_label = "other"


@pytest.mark.parametrize("name,offset,width,evidence", [
    ("hp", -1, 2, ("e",)), ("hp", True, 2, ("e",)),
    ("hp", 0, True, ("e",)), ("hp", 0, 3, ("e",)),
    ("position", 0, 2, ("e",)), ("hp", 0, 2, ()), ("hp", 0, 2, ("",)),
])
def test_bad_binding(name: str, offset: int, width: int, evidence: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        FieldBinding(name, offset, width, evidence)


@pytest.mark.parametrize("changes", [
    {"record_address": 0x087FFFFF}, {"record_address": True},
    {"record_address": 0x09FFFFFF}, {"record_size": -1},
    {"record_size": True}, {"record_size": 65537}, {"unit_label": ""},
    {"fields": (FieldBinding("hp", 0, 4, ("e",)),)},
    {"fields": (FieldBinding("hp", 0, 4, ("e",)),
                FieldBinding("max_hp", 2, 4, ("e",)))},
    {"fields": (FieldBinding("hp", 0, 4, ("e",)),
                FieldBinding("max_hp", 4, 4, ("e",)),
                FieldBinding("hp", 8, 4, ("e",)))},
    {"record_size": 8},
])
def test_bad_profile(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        replace(profile(), **changes)


@pytest.mark.parametrize("data", [record(5001), record(maximum=0), record(en=211), bytes(31)])
def test_bad_record(data: bytes) -> None:
    with pytest.raises(ValueError):
        decode(profile(), data)


@pytest.mark.parametrize("identity", [("wrong", "patch", "version"),
                                     ("game", "wrong", "version"),
                                     ("game", "patch", "wrong")])
def test_identity_mismatch(identity: tuple[str, str, str]) -> None:
    with pytest.raises(ValueError):
        decode_inspection(profile(), record(), *identity)


def test_supported_optional_stats_and_unsigned_values() -> None:
    names = ("defense", "mobility", "accuracy", "sp", "max_sp", "level", "will")
    fields = profile().fields[:2] + tuple(
        FieldBinding(name, 8 + index, 1, ("e",)) for index, name in enumerate(names)
    )
    p = replace(profile(), fields=fields)
    result = decode(p, record()[:8] + bytes([255] * 7) + bytes(17))
    assert result.get("defense") == 255
    assert result.get("will") == 255
    with pytest.raises(ValueError):
        decode(p, record()[:8] + bytes([255, 255, 255, 2, 1, 255, 255]) + bytes(17))


def test_ram_end_boundary_and_maximum_unsigned_hp() -> None:
    p = replace(profile(), record_address=0x0A000000 - 32)
    assert decode(p, record(0xFFFFFFFF, 0xFFFFFFFF)).get("hp") == 0xFFFFFFFF
