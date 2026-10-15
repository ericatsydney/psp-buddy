"""Offline named-record inspection; supplied evidence never authenticates deployment."""

from dataclasses import dataclass

FIELD_NAMES = (
    "unit_id", "hp", "max_hp", "en", "max_en", "sp", "max_sp", "x", "y",
    "side", "action_available",
)


def _integer(value: object, minimum: int, maximum: int, label: str) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"Invalid {label}")


def _text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError(f"Invalid {label}")


@dataclass(frozen=True)
class MapField:
    name: str
    offset: int
    width: int
    evidence_ids: tuple[str, ...]
    meanings: tuple[tuple[int, str], ...] = ()

    def __post_init__(self) -> None:
        if self.name not in FIELD_NAMES:
            raise ValueError("Unsupported inspection field")
        _integer(self.offset, 0, 65535, "field offset")
        if type(self.width) is not int or self.width not in (1, 2, 4):
            raise ValueError("Invalid field width")
        if type(self.evidence_ids) is not tuple or not 1 <= len(self.evidence_ids) <= 32:
            raise ValueError("Evidence references must be a bounded nonempty tuple")
        for reference in self.evidence_ids:
            _text(reference, "evidence reference")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate evidence reference")
        if type(self.meanings) is not tuple or len(self.meanings) > 256:
            raise ValueError("Invalid meanings")
        allowed = {"side": ("ally", "enemy", "neutral"),
                   "action_available": ("available", "spent")}.get(self.name)
        if allowed is None:
            if self.meanings:
                raise ValueError("Meanings only supported for enum fields")
            return
        if not self.meanings:
            raise ValueError("Enum requires explicit meanings")
        raw_values: set[int] = set()
        labels: set[str] = set()
        for pair in self.meanings:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError("Invalid enum pair")
            raw, meaning = pair
            _integer(raw, 0, 2 ** (8 * self.width) - 1, "enum raw value")
            if meaning not in allowed or raw in raw_values or meaning in labels:
                raise ValueError("Invalid or duplicate enum meaning")
            raw_values.add(raw)
            labels.add(meaning)


@dataclass(frozen=True)
class MapRecordProfile:
    label: str
    address: int
    size: int
    fields: tuple[MapField, ...]

    def __post_init__(self) -> None:
        _text(self.label, "record label")
        _integer(self.size, 1, 65536, "record size")
        _integer(self.address, 0x08800000, 0x0A000000 - self.size, "record address")
        if type(self.fields) is not tuple or len(self.fields) > len(FIELD_NAMES):
            raise ValueError("Invalid fields")
        names: set[str] = set()
        windows: list[tuple[int, int]] = []
        for field in self.fields:
            if not isinstance(field, MapField):
                raise ValueError("Invalid field")
            start, end = field.offset, field.offset + field.width
            if (field.name in names or end > self.size
                    or any(start < old_end and old_start < end
                           for old_start, old_end in windows)):
                raise ValueError("Duplicate, overlapping or out-of-bounds field")
            names.add(field.name)
            windows.append((start, end))


@dataclass(frozen=True)
class MapInspectionProfile:
    game_id: str
    patch_id: str
    emulator_version: str
    map_label: str
    dimensions: tuple[int, int] | None
    records: tuple[MapRecordProfile, ...]

    def __post_init__(self) -> None:
        for value in (self.game_id, self.patch_id, self.emulator_version, self.map_label):
            _text(value, "profile identity/label")
        if self.dimensions is not None:
            if type(self.dimensions) is not tuple or len(self.dimensions) != 2:
                raise ValueError("Invalid dimensions")
            for dimension in self.dimensions:
                _integer(dimension, 1, 1024, "map dimension")
        if type(self.records) is not tuple or not 1 <= len(self.records) <= 256:
            raise ValueError("Invalid record count")
        labels: set[str] = set()
        windows: list[tuple[int, int]] = []
        total = 0
        for record in self.records:
            if not isinstance(record, MapRecordProfile):
                raise ValueError("Invalid record profile")
            start, end = record.address, record.address + record.size
            if (record.label in labels
                    or any(start < old_end and old_start < end
                           for old_start, old_end in windows)):
                raise ValueError("Duplicate labels or overlapping records")
            labels.add(record.label)
            windows.append((start, end))
            total += record.size
            names = {field.name for field in record.fields}
            if ("x" in names or "y" in names) and (
                    not {"x", "y"} <= names or self.dimensions is None):
                raise ValueError("Coordinates require paired fields and map dimensions")
        if total > 1024 * 1024:
            raise ValueError("Total inspection memory exceeds 1 MiB")


@dataclass(frozen=True)
class MapInspectionRecord:
    label: str
    unit_id: int | None
    hp: int | None
    max_hp: int | None
    en: int | None
    max_en: int | None
    sp: int | None
    max_sp: int | None
    x: int | None
    y: int | None
    side: str | None
    action_available: bool | None
    missing_fields: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class MapInspectionReport:
    game_id: str
    patch_id: str
    emulator_version: str
    map_label: str
    dimensions: tuple[int, int] | None
    records: tuple[MapInspectionRecord, ...]
    roster_completeness: str = "named_records_only"
    live_authenticated: bool = False
    autonomous_available: bool = False


def decode_map_inspection(
    profile: MapInspectionProfile,
    samples: tuple[bytes, ...],
    game_id: str,
    patch_id: str,
    emulator_version: str,
) -> MapInspectionReport:
    """Decode only explicit bindings from supplied bytes, with no live fallback."""
    if not isinstance(profile, MapInspectionProfile):
        raise ValueError("Invalid inspection profile")
    if (game_id, patch_id, emulator_version) != (
            profile.game_id, profile.patch_id, profile.emulator_version):
        raise ValueError("Inspection identity mismatch")
    if type(samples) is not tuple or len(samples) != len(profile.records):
        raise ValueError("Samples must be an immutable tuple matching records")
    records: list[MapInspectionRecord] = []
    unit_ids: set[int] = set()
    for descriptor, sample in zip(profile.records, samples, strict=True):
        if type(sample) is not bytes or len(sample) != descriptor.size:
            raise ValueError("Record requires immutable bytes of exact length")
        values: dict[str, int] = {}
        enum_values: dict[str, str] = {}
        for field in descriptor.fields:
            raw = int.from_bytes(sample[field.offset:field.offset + field.width], "little")
            if field.meanings:
                meanings = dict(field.meanings)
                if raw not in meanings:
                    raise ValueError(f"Unmapped {field.name} value")
                enum_values[field.name] = meanings[raw]
            else:
                values[field.name] = raw
        for resource in ("hp", "en", "sp"):
            current, maximum = values.get(resource), values.get(f"max_{resource}")
            if maximum is not None and ((resource == "hp" and maximum == 0) or (
                    current is not None and current > maximum)):
                raise ValueError(f"Invalid {resource} resource bounds")
        x, y = values.get("x"), values.get("y")
        if x is not None and y is not None:
            assert profile.dimensions is not None
            if x >= profile.dimensions[0] or y >= profile.dimensions[1]:
                raise ValueError("Coordinate outside supplied map dimensions")
        unit_id = values.get("unit_id")
        if unit_id is not None:
            if unit_id in unit_ids:
                raise ValueError("Duplicate decoded unit identity")
            unit_ids.add(unit_id)
        known = values.keys() | enum_values.keys()
        missing = tuple((name, "No supplied evidence-bound field layout")
                        for name in FIELD_NAMES if name not in known)
        action = enum_values.get("action_available")
        records.append(MapInspectionRecord(
            descriptor.label, unit_id, values.get("hp"), values.get("max_hp"),
            values.get("en"), values.get("max_en"), values.get("sp"), values.get("max_sp"),
            x, y, enum_values.get("side"), None if action is None else action == "available",
            missing,
        ))
    return MapInspectionReport(profile.game_id, profile.patch_id, profile.emulator_version,
                               profile.map_label, profile.dimensions, tuple(records))
