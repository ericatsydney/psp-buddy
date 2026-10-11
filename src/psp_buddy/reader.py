"""Decode bounded supplied bytes without emulator access or roster inference."""

from dataclasses import dataclass

from .profile import InspectionProfile


@dataclass(frozen=True)
class StatInspection:
    """Inspection only: no phase, affiliation, position, activity or legal actions."""

    game_id: str
    patch_id: str
    emulator_version: str
    unit_label: str
    record_address: int
    values: tuple[tuple[str, int], ...]

    def get(self, name: str) -> int | None:
        return next((value for key, value in self.values if key == name), None)


def decode_inspection(
    profile: InspectionProfile, data: bytes, game_id: str, patch_id: str,
    emulator_version: str,
) -> StatInspection:
    if (game_id, patch_id, emulator_version) != (
        profile.game_id, profile.patch_id, profile.emulator_version,
    ):
        raise ValueError("Inspection identity mismatch")
    if not isinstance(data, bytes) or len(data) < profile.record_size:
        raise ValueError("Incomplete record bytes")
    values = tuple((field.name, int.from_bytes(
        data[field.offset:field.offset + field.width], "little", signed=False,
    )) for field in profile.fields)
    stats = dict(values)
    if stats["max_hp"] <= 0 or stats["hp"] > stats["max_hp"]:
        raise ValueError("Invalid current or maximum HP")
    for current, maximum in (("en", "max_en"), ("sp", "max_sp")):
        if current in stats and maximum in stats and stats[current] > stats[maximum]:
            raise ValueError(f"{current.upper()} exceeds maximum")
    return StatInspection(profile.game_id, profile.patch_id, profile.emulator_version,
                          profile.unit_label, profile.record_address, values)
