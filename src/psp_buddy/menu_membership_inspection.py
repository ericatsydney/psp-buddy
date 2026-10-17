"""Pure evidence-bound menu membership, independently of tactical allegiance."""

from dataclasses import dataclass, replace
from hashlib import sha256
from typing import cast

from .positioned_inspection import (
    PositionedInspectionProfile,
    PositionedInspectionReport,
    decode_positioned_inspection,
)
from .unit_pool_inspection import CodeAnchor, InspectionSpan, _integer, _text, _window


@dataclass(frozen=True)
class MenuMembershipInspectionProfile:
    positioned_profile: PositionedInspectionProfile
    menu_mask_table_address: int
    expected_category_masks: tuple[int, ...]
    ally_category_index: int
    foe_category_index: int
    code_anchors: tuple[CodeAnchor, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.positioned_profile) is not PositionedInspectionProfile:
            raise ValueError("Invalid positioned profile")
        self.positioned_profile.__post_init__()
        _window(self.menu_mask_table_address, 16, True)
        masks = self.expected_category_masks
        if type(masks) is not tuple or len(masks) != 4:
            raise ValueError("Exactly four immutable masks required")
        covered = 0
        for mask in masks:
            _integer(mask, 1, 65535, "category mask")
            if covered & mask:
                raise ValueError("Overlapping category masks")
            covered |= mask
        if covered != 65535:
            raise ValueError("Category masks must cover all supported groups")
        for index in (self.ally_category_index, self.foe_category_index):
            _integer(index, 0, 3, "category index")
        if self.ally_category_index == self.foe_category_index:
            raise ValueError("Menu label indices must differ")
        if type(self.code_anchors) is not tuple or not 1 <= len(self.code_anchors) <= 16:
            raise ValueError("Invalid menu anchors")
        for anchor in self.code_anchors:
            if type(anchor) is not CodeAnchor:
                raise ValueError("Invalid menu anchor")
            anchor.__post_init__()
        if sum(anchor.size for anchor in self.code_anchors) > 16384:
            raise ValueError("Menu anchor total exceeds 16 KiB")
        if type(self.evidence_ids) is not tuple or not 1 <= len(self.evidence_ids) <= 32:
            raise ValueError("Invalid menu evidence")
        for evidence in self.evidence_ids:
            _text(evidence)
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate menu evidence")
        self.combined_profile()

    def combined_profile(self) -> PositionedInspectionProfile:
        table = b"".join(mask.to_bytes(4, "little") for mask in self.expected_category_masks)
        fingerprint = CodeAnchor(self.menu_mask_table_address, 16, sha256(table).hexdigest())
        original = self.positioned_profile
        anchors = tuple(
            dict.fromkeys(
                original.representative_profile.code_anchors + self.code_anchors + (fingerprint,)
            )
        )
        return replace(
            original,
            representative_profile=replace(original.representative_profile, code_anchors=anchors),
        )


@dataclass(frozen=True)
class MenuMembershipInspectionReport:
    base_report: PositionedInspectionReport
    profile: MenuMembershipInspectionProfile
    memberships: tuple[tuple[int, int, str], ...]

    def to_dict(self) -> dict[str, object]:
        result = self.base_report.to_dict()
        rows = cast(list[dict[str, object]], result["representatives"])
        result["representatives"] = [
            dict(row, raw_menu_group_byte=raw, menu_category_index=category, menu_membership=label)
            for row, (raw, category, label) in zip(rows, self.memberships, strict=True)
        ]
        counts = [sum(category == i for _, category, _ in self.memberships) for i in range(4)]
        ally, foe = self.profile.ally_category_index, self.profile.foe_category_index
        result.update(
            inspection_kind="menu_membership_inspection",
            category_counts=counts,
            ally_menu_count=counts[ally],
            foe_menu_count=counts[foe],
            outside_menu_count=sum(counts) - counts[ally] - counts[foe],
            category_masks=list(self.profile.expected_category_masks),
            label_source="user_supplied_menu_label_mapping",
            menu_membership_note="Menu membership is not tactical allegiance.",
        )
        evidence = cast(list[str], result["evidence_ids"])
        result["evidence_ids"] = list(dict.fromkeys((*evidence, *self.profile.evidence_ids)))
        return result


def decode_menu_membership_inspection(
    profile: MenuMembershipInspectionProfile,
    spans: tuple[InspectionSpan, ...],
    game_id: str,
    patch_id: str,
    emulator_version: str,
) -> MenuMembershipInspectionReport:
    """Join direct supported group bytes to explicit evidence-bound menu labels."""
    if type(profile) is not MenuMembershipInspectionProfile:
        raise ValueError("Invalid menu membership profile")
    profile.__post_init__()
    base = decode_positioned_inspection(
        profile.combined_profile(), spans, game_id, patch_id, emulator_version
    )

    def read(address: int, size: int) -> bytes:
        _window(address, size)
        for span in spans:
            if span.address <= address and address + size <= span.address + len(span.data):
                offset = address - span.address
                return span.data[offset : offset + size]
        raise ValueError("Missing contiguous menu window")

    table = read(profile.menu_mask_table_address, 16)
    captured = tuple(int.from_bytes(table[i : i + 4], "little") for i in range(0, 16, 4))
    if captured != profile.expected_category_masks:
        raise ValueError("Menu mask table mismatch")
    memberships = []
    for row in base.base_report.representatives:
        raw = read(row.object_address + 0x15, 1)[0]
        if raw > 15:
            raise ValueError("Unsupported raw menu group byte")
        categories = [i for i, mask in enumerate(captured) if mask & (1 << raw)]
        if len(categories) != 1:
            raise ValueError("Ambiguous menu category")
        category = categories[0]
        label = (
            "ally_menu"
            if category == profile.ally_category_index
            else "foe_menu"
            if category == profile.foe_category_index
            else "outside_ally_foe_menus"
        )
        memberships.append((raw, category, label))
    return MenuMembershipInspectionReport(base, profile, tuple(memberships))
