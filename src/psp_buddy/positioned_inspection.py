"""Pure positioned wrapper around evidence-bound representative inspection."""

from dataclasses import dataclass, replace

from .representative_inspection import (
    RepresentativeInspectionProfile,
    RepresentativeInspectionReport,
    decode_representative_inspection,
)
from .unit_pool_inspection import CodeAnchor, InspectionSpan, _disjoint, _text, _window


@dataclass(frozen=True)
class GeometryProfile:
    width_address: int
    height_address: int
    code_anchors: tuple[CodeAnchor, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        windows = []
        for address in (self.width_address, self.height_address):
            _window(address, 2)
            if address % 2:
                raise ValueError("Misaligned dimension address")
            windows.append(_window(address, 2))
        if type(self.code_anchors) is not tuple or not 1 <= len(self.code_anchors) <= 16:
            raise ValueError("Invalid geometry anchors")
        for anchor in self.code_anchors:
            if type(anchor) is not CodeAnchor:
                raise ValueError("Invalid geometry anchor")
            anchor.__post_init__()
            windows.append(_window(anchor.address, anchor.size))
        if sum(a.size for a in self.code_anchors) > 16384:
            raise ValueError("Geometry anchor total exceeds 16 KiB")
        _disjoint(windows)
        if type(self.evidence_ids) is not tuple or not 1 <= len(self.evidence_ids) <= 32:
            raise ValueError("Invalid geometry evidence")
        for reference in self.evidence_ids:
            _text(reference)
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate geometry evidence")


@dataclass(frozen=True)
class PositionedInspectionProfile:
    representative_profile: RepresentativeInspectionProfile
    geometry: GeometryProfile

    def __post_init__(self) -> None:
        if type(self.representative_profile) is not RepresentativeInspectionProfile:
            raise ValueError("Invalid representative profile")
        if type(self.geometry) is not GeometryProfile:
            raise ValueError("Invalid geometry profile")
        self.representative_profile.__post_init__()
        self.geometry.__post_init__()
        # Reuse all layout/code overlap checks; retain the caller's immutable profile.
        self.combined_profile()

    def combined_profile(self) -> RepresentativeInspectionProfile:
        anchors = tuple(
            dict.fromkeys(self.representative_profile.code_anchors + self.geometry.code_anchors)
        )
        nested = replace(self.representative_profile, code_anchors=anchors)
        all_anchors = tuple(dict.fromkeys(nested.pool_profile.code_anchors + anchors))
        _disjoint([_window(a.address, a.size) for a in all_anchors])
        for address in (self.geometry.width_address, self.geometry.height_address):
            if any(address < a.address + a.size and a.address < address + 2 for a in all_anchors):
                raise ValueError("Dimensions overlap code anchor")
        return nested


@dataclass(frozen=True)
class PositionedInspectionReport:
    base_report: RepresentativeInspectionReport
    geometry: GeometryProfile
    dimensions: tuple[int, int]
    positions: tuple[tuple[int, int, int], ...]

    def to_dict(self) -> dict[str, object]:
        result = self.base_report.to_dict()
        position = {address: (x, y) for address, x, y in self.positions}
        result["inspection_kind"] = "positioned_representative_inspection"
        result["coordinate_system"] = "zero_based_tiles"
        result["dimensions"] = dict(zip(("width", "height"), self.dimensions, strict=True))
        result["representatives"] = [
            dict(
                row.to_dict(),
                tile_x=position[row.object_address][0],
                tile_y=position[row.object_address][1],
            )
            for row in self.base_report.representatives
        ]
        result["evidence_ids"] = list(
            dict.fromkeys(
                self.base_report.profile.pool_profile.evidence_ids
                + self.base_report.profile.evidence_ids
                + self.geometry.evidence_ids
            )
        )
        unavailable = result["unavailable_fields"]
        assert isinstance(unavailable, dict)
        result["unavailable_fields"] = {
            k: v for k, v in unavailable.items() if k not in ("x", "y", "dimensions")
        }
        return result


def decode_positioned_inspection(
    profile: PositionedInspectionProfile,
    spans: tuple[InspectionSpan, ...],
    game_id: str,
    patch_id: str,
    emulator_version: str,
) -> PositionedInspectionReport:
    """Join corroborated direct tiles without promoting tactical capabilities."""
    if type(profile) is not PositionedInspectionProfile:
        raise ValueError("Invalid positioned profile")
    profile.__post_init__()
    base = decode_representative_inspection(
        profile.combined_profile(), spans, game_id, patch_id, emulator_version
    )

    def half(address: int) -> int:
        _window(address, 2)
        for span in spans:
            if span.address <= address and address + 2 <= span.address + len(span.data):
                offset = address - span.address
                return int.from_bytes(span.data[offset : offset + 2], "little")
        raise ValueError("Missing contiguous geometry window")

    width, height = half(profile.geometry.width_address), half(profile.geometry.height_address)
    if not 1 <= width <= 1024 or not 1 <= height <= 1024 or width * height > 1024:
        raise ValueError("Invalid captured map dimensions")
    positions = []
    for row in base.representatives:
        x, y = half(row.object_address + 0x26), half(row.object_address + 0x28)
        if x >= width or y >= height:
            raise ValueError("Representative tile outside map dimensions")
        positions.append((row.object_address, x, y))
    return PositionedInspectionReport(base, profile.geometry, (width, height), tuple(positions))
