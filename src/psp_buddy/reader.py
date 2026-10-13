"""Decode bounded supplied bytes without emulator access or roster inference."""

from dataclasses import dataclass

from .profile import InspectionProfile, PilotInspectionProfile


@dataclass(frozen=True)
class PilotInspection:
    """Immutable bounded stats, without roster, deployed pilot ID or tactical state."""
    game_id: str
    patch_id: str
    emulator_version: str
    pilot_label: str
    record_window: str
    record_address: int
    values: tuple[tuple[str, int], ...]

    def get(self, name: str) -> int | None:
        return next((value for key, value in self.values if key == name), None)


def decode_pilot_inspection(
    profile: PilotInspectionProfile, data: bytes, game_id: str, patch_id: str,
    emulator_version: str,
) -> PilotInspection:
    if not isinstance(profile, PilotInspectionProfile):
        raise ValueError('Pilot inspection profile required')
    if (game_id, patch_id, emulator_version) != (
        profile.game_id, profile.patch_id, profile.emulator_version,
    ):
        raise ValueError('Pilot inspection identity mismatch')
    if not isinstance(data, bytes) or len(data) != profile.record_size:
        raise ValueError('Exact bounded immutable pilot record bytes required')
    values = tuple((field.name, int.from_bytes(
        data[field.offset:field.offset + field.width], 'little', signed=False,
    )) for field in profile.fields)
    stats = dict(values)
    if stats['level'] <= 0:
        raise ValueError('Invalid pilot level')
    if 'max_sp' in stats and stats['sp'] > stats['max_sp']:
        raise ValueError('Pilot SP exceeds maximum SP')
    return PilotInspection(profile.game_id, profile.patch_id, profile.emulator_version,
                           profile.pilot_label, profile.record_window,
                           profile.record_address, values)


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
