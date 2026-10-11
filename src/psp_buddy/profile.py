"""Evidence-bound stat layout for inspection only, never tactical observation."""

from dataclasses import dataclass

SUPPORTED_STATS = frozenset({
    "hp", "max_hp", "en", "max_en", "defense", "mobility", "accuracy",
    "sp", "max_sp", "level", "will",
})


def _integer(value: int, minimum: int, maximum: int, name: str) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"Invalid {name}")


@dataclass(frozen=True)
class FieldBinding:
    name: str
    offset: int
    width: int
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.name not in SUPPORTED_STATS:
            raise ValueError("Unsupported stat field")
        _integer(self.offset, 0, 65535, "field offset")
        _integer(self.width, 1, 4, "field width")
        if self.width not in (1, 2, 4):
            raise ValueError("Field width must be 1, 2 or 4")
        if (not isinstance(self.evidence_ids, tuple) or not self.evidence_ids
                or any(not isinstance(e, str) or not e.strip() for e in self.evidence_ids)):
            raise ValueError("Nonempty evidence references required")


@dataclass(frozen=True)
class InspectionProfile:
    game_id: str
    patch_id: str
    emulator_version: str
    unit_label: str
    record_address: int
    record_size: int
    fields: tuple[FieldBinding, ...]

    def __post_init__(self) -> None:
        for value in (self.game_id, self.patch_id, self.emulator_version, self.unit_label):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Nonempty identity and unit label required")
        _integer(self.record_size, 1, 65536, "record size")
        _integer(self.record_address, 0x08800000, 0x0A000000 - self.record_size,
                 "PSP user RAM record address")
        if not isinstance(self.fields, tuple):
            raise ValueError("Immutable field tuple required")
        names: set[str] = set()
        occupied: set[int] = set()
        for field in self.fields:
            if not isinstance(field, FieldBinding):
                raise ValueError("Field binding required")
            positions = set(range(field.offset, field.offset + field.width))
            if field.name in names or occupied & positions:
                raise ValueError("Duplicate or overlapping field binding")
            if field.offset + field.width > self.record_size:
                raise ValueError("Field exceeds record bounds")
            names.add(field.name)
            occupied.update(positions)
        if not {"hp", "max_hp"} <= names:
            raise ValueError("Corroborated current and maximum HP required")
