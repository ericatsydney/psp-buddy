"""Pure offline End Phase UI counters; no legal-action or live capabilities."""

from dataclasses import dataclass, replace
from typing import cast

from .menu_membership_inspection import (
    MenuMembershipInspectionProfile,
    MenuMembershipInspectionReport,
    decode_menu_membership_inspection,
)
from .unit_pool_inspection import CodeAnchor, InspectionSpan, _text


@dataclass(frozen=True)
class EndPhaseInspectionProfile:
    menu_membership_profile: MenuMembershipInspectionProfile
    code_anchors: tuple[CodeAnchor, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.menu_membership_profile) is not MenuMembershipInspectionProfile:
            raise ValueError("Invalid menu membership profile")
        self.menu_membership_profile.__post_init__()
        if type(self.code_anchors) is not tuple or not 1 <= len(self.code_anchors) <= 16:
            raise ValueError("Invalid End Phase anchors")
        for anchor in self.code_anchors:
            if type(anchor) is not CodeAnchor:
                raise ValueError("Invalid End Phase anchor")
            anchor.__post_init__()
        if type(self.evidence_ids) is not tuple or not 1 <= len(self.evidence_ids) <= 32:
            raise ValueError("Invalid End Phase evidence")
        for evidence in self.evidence_ids:
            _text(evidence)
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate End Phase evidence")
        self.combined_profile()

    def combined_profile(self) -> MenuMembershipInspectionProfile:
        """Preserve layer limits while validating all inherited/additional anchors together."""
        menu = self.menu_membership_profile
        positioned = menu.positioned_profile
        representative = positioned.representative_profile
        anchors = tuple(dict.fromkeys(representative.code_anchors + self.code_anchors))
        combined = replace(
            menu,
            positioned_profile=replace(
                positioned,
                representative_profile=replace(representative, code_anchors=anchors),
            ),
        )
        fully_combined = combined.combined_profile().combined_profile()
        all_anchors = tuple(
            dict.fromkeys(fully_combined.pool_profile.code_anchors + fully_combined.code_anchors)
        )
        if len(all_anchors) > 32:
            raise ValueError("Combined code anchors exceed 32 entries")
        if sum(anchor.size for anchor in all_anchors) > 16384:
            raise ValueError("Combined code anchor total exceeds 16 KiB")
        return combined


@dataclass(frozen=True)
class EndPhaseInspectionReport:
    base_report: MenuMembershipInspectionReport
    profile: EndPhaseInspectionProfile
    counters: tuple[int, ...]

    def to_dict(self) -> dict[str, object]:
        result = self.base_report.to_dict()
        rows = cast(list[dict[str, object]], result["representatives"])
        scoped = [raw == 0 for raw, _, _ in self.base_report.memberships]
        counted = [
            scope and counter > 0 for scope, counter in zip(scoped, self.counters, strict=True)
        ]
        result["representatives"] = [
            dict(row, counter_value=counter, end_phase_count_scope=scope, counted_as_unmoved=count)
            for row, counter, scope, count in zip(rows, self.counters, scoped, counted, strict=True)
        ]
        total = sum(counted)
        result.update(
            inspection_kind="end_phase_inspection",
            end_phase_scope_count=sum(scoped),
            unmoved_unit_count=total,
            displayed_unmoved_unit_count=total % 100,
            counter_semantics_note=(
                "Positive two-bit counters in End Phase mask1 scope contribute one actor to "
                "the UnmovedUnits UI count; Move/Attack legality and causal action consumption "
                "remain unverified."
            ),
        )
        evidence = cast(list[str], result["evidence_ids"])
        result["evidence_ids"] = list(dict.fromkeys((*evidence, *self.profile.evidence_ids)))
        return result


def decode_end_phase_inspection(
    profile: EndPhaseInspectionProfile,
    spans: tuple[InspectionSpan, ...],
    game_id: str,
    patch_id: str,
    emulator_version: str,
) -> EndPhaseInspectionReport:
    """Require validated fallback objects before applying the fixed two-bit UI recipe.

    The representative decoder removes every enabled matching relationship pair before
    requiring exact source/cache agreement. Consequently every accepted cache actor has
    no enabled matching pair, proving the resolver fallback without parsing tables twice.
    """
    if type(profile) is not EndPhaseInspectionProfile:
        raise ValueError("Invalid End Phase profile")
    profile.__post_init__()
    base = decode_menu_membership_inspection(
        profile.combined_profile(), spans, game_id, patch_id, emulator_version
    )
    counters = []
    for row in base.base_report.base_report.representatives:
        address = row.object_address + 8
        for span in spans:
            if span.address <= address < span.address + len(span.data):
                counters.append((span.data[address - span.address] >> 3) & 3)
                break
        else:
            raise ValueError("Missing End Phase counter window")
    return EndPhaseInspectionReport(base, profile, tuple(counters))
