"""Evidence-bound pure offline reconstruction of representative actors."""

from dataclasses import asdict, dataclass
from hashlib import sha256

from .unit_pool_inspection import (
    CodeAnchor,
    InspectionSpan,
    UnitPoolInspectionProfile,
    _disjoint,
    _integer,
    _text,
    _window,
    decode_unit_pool_inspection,
)


@dataclass(frozen=True)
class InspectionRegion:
    address: int
    capacity: int
    stride: int

    def __post_init__(self) -> None:
        _integer(self.capacity, 1, 2048, "region capacity")
        _integer(self.stride, 1, 1048576, "region stride")
        _window(self.address, self.capacity * self.stride, True)


@dataclass(frozen=True)
class RepresentativeInspectionProfile:
    pool_profile: UnitPoolInspectionProfile
    source_root_global: int
    cache_owner_global: int
    blocked_mech_ids_address: int
    selector_owner_global: int
    pair_exclusion_owner_global: int
    node_regions: tuple[InspectionRegion, ...]
    mech_descriptors: InspectionRegion
    pilot_descriptors: InspectionRegion
    code_anchors: tuple[CodeAnchor, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.pool_profile) is not UnitPoolInspectionProfile:
            raise ValueError("Invalid pool profile")
        self.pool_profile.__post_init__()
        for address in (
            self.source_root_global,
            self.cache_owner_global,
            self.blocked_mech_ids_address,
            self.selector_owner_global,
            self.pair_exclusion_owner_global,
        ):
            _window(address, 4, True)
        if type(self.node_regions) is not tuple or not 1 <= len(self.node_regions) <= 2:
            raise ValueError("Invalid node regions")
        for region, stride in [(r, 12) for r in self.node_regions] + [
            (self.mech_descriptors, 12),
            (self.pilot_descriptors, 8),
        ]:
            if type(region) is not InspectionRegion:
                raise ValueError("Invalid region")
            region.__post_init__()
            if region.stride != stride:
                raise ValueError("Invalid region stride")
        if (
            any(r.capacity > 1664 for r in self.node_regions)
            or sum(r.capacity for r in self.node_regions) > 2688
        ):
            raise ValueError("Node capacity exceeds bound")
        if type(self.code_anchors) is not tuple or not 1 <= len(self.code_anchors) <= 32:
            raise ValueError("Invalid code anchors")
        for anchor in self.code_anchors:
            if type(anchor) is not CodeAnchor:
                raise ValueError("Invalid code anchor")
            anchor.__post_init__()
        if sum(a.size for a in self.code_anchors) > 16384:
            raise ValueError("Code anchor total exceeds 16 KiB")
        _disjoint([_window(a.address, a.size) for a in self.code_anchors])
        if type(self.evidence_ids) is not tuple or not 1 <= len(self.evidence_ids) <= 32:
            raise ValueError("Invalid evidence count")
        for evidence in self.evidence_ids:
            _text(evidence)
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate evidence")
        regions = (*self.node_regions, self.mech_descriptors, self.pilot_descriptors)
        p = self.pool_profile
        _disjoint(
            [_window(r.address, r.capacity * r.stride) for r in regions]
            + [
                _window(a.address, a.size)
                for a in dict.fromkeys(p.code_anchors + self.code_anchors)
            ]
            + [
                _window(p.pool_address, p.pool_capacity * 104),
                _window(p.actor_owner_address, 28),
                _window(self.blocked_mech_ids_address, 154 * 4),
            ]
        )


@dataclass(frozen=True)
class RepresentativeRecord:
    slot_index: int
    object_address: int
    actor_address: int
    mech_descriptor_address: int
    pilot_descriptor_address: int
    mech_id: int
    pilot_id: int
    mech_record_address: int
    pilot_record_address: int
    hp: int
    max_hp: int
    en: int
    max_en: int
    sp: int
    defense: int
    mobility: int
    accuracy: int
    alias_count: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class RepresentativeInspectionReport:
    profile: RepresentativeInspectionProfile
    representatives: tuple[RepresentativeRecord, ...]
    source_count: int
    cache_count: int
    reconstructed_count: int
    spans: tuple[InspectionSpan, ...]

    def to_dict(self) -> dict[str, object]:
        p = self.profile.pool_profile
        return {
            "inspection_kind": "representative_inspection",
            "mode": "offline_read_only",
            "game_id": p.game_id,
            "patch_id": p.patch_id,
            "emulator_version": p.emulator_version,
            "map_label": p.map_label,
            "selection_status": "source_recipe_matches_cache",
            "roster_completeness": "candidate_slots_only",
            "provenance": "user_supplied_spans_and_profile",
            "live_authenticated": False,
            "autonomous_available": False,
            "autonomous_execution_enabled": False,
            "tactical_snapshot_available": False,
            "candidate_count": len(self.representatives),
            "slot_capacity": p.pool_capacity,
            "source_count": self.source_count,
            "cache_count": self.cache_count,
            "reconstructed_count": self.reconstructed_count,
            "evidence_ids": list(p.evidence_ids + self.profile.evidence_ids),
            "spans": [
                {"address": s.address, "size": len(s.data), "sha256": sha256(s.data).hexdigest()}
                for s in self.spans
            ],
            "representatives": [r.to_dict() for r in self.representatives],
            "unavailable_fields": {
                k: "not_corroborated_by_representative_inspector"
                for k in (
                    "name",
                    "mv",
                    "max_sp",
                    "x",
                    "y",
                    "dimensions",
                    "side",
                    "action_available",
                    "phase",
                    "legal_actions",
                    "terrain",
                )
            },
        }


class _Reader:
    def __init__(self, spans: tuple[InspectionSpan, ...], anchors: tuple[CodeAnchor, ...]):
        self.spans = spans
        self.anchors = anchors
        self.regions: list[tuple[int, int, str]] = []
        self.views: list[tuple[int, int]] = []

    def read(self, address: int, size: int) -> bytes:
        _, end = _window(address, size)
        for span in self.spans:
            if span.address <= address and end <= span.address + len(span.data):
                return span.data[address - span.address : end - span.address]
        raise ValueError("Missing contiguous captured window")

    def u(self, address: int) -> int:
        _window(address, 4, True)
        self.view(address, 4)
        return int.from_bytes(self.read(address, 4), "little")

    def view(self, address: int, size: int) -> None:
        start, end = _window(address, size, True)
        if any(start < a.address + a.size and a.address < end for a in self.anchors):
            raise ValueError("Mutable window overlaps code")
        if any(
            start < e and s < end and c in ("mech_header", "pilot_header", "metadata")
            for s, e, c in self.regions
        ):
            raise ValueError("Pointer/list view overlaps stat or metadata record")
        self.views.append((start, end))

    def region(self, address: int, size: int, category: str) -> None:
        start, end = _window(address, size, category != "metadata")
        if category == "metadata" and address % 2:
            raise ValueError("Misaligned metadata")
        if any(start < a.address + a.size and a.address < end for a in self.anchors):
            raise ValueError("Data overlaps code")
        for s, e, c in self.regions:
            if start < e and s < end and (start, end, category) != (s, e, c):
                raise ValueError("Conflicting semantic storage regions")
        if category in ("mech_header", "pilot_header", "metadata") and any(
            start < e and s < end for s, e in self.views
        ):
            raise ValueError("Stat/metadata overlaps pointer view")
        item = (start, end, category)
        if item not in self.regions:
            self.regions.append(item)


def decode_representative_inspection(
    profile: RepresentativeInspectionProfile,
    spans: tuple[InspectionSpan, ...],
    game_id: str,
    patch_id: str,
    emulator_version: str,
) -> RepresentativeInspectionReport:
    """Reject incomplete or inconsistent evidence; never guess a selected alias."""
    if type(profile) is not RepresentativeInspectionProfile:
        raise ValueError("Invalid profile")
    profile.__post_init__()
    p = profile.pool_profile
    for identity in (game_id, patch_id, emulator_version):
        _text(identity)
    if (game_id, patch_id, emulator_version) != (p.game_id, p.patch_id, p.emulator_version):
        raise ValueError("Inspection identity mismatch")
    if type(spans) is not tuple or not 1 <= len(spans) <= 128:
        raise ValueError("Invalid span count or mutable collection")
    for span in spans:
        if type(span) is not InspectionSpan:
            raise ValueError("Invalid span")
        span.__post_init__()
    if sum(len(s.data) for s in spans) > 1048576:
        raise ValueError("Span total exceeds 1 MiB")
    _disjoint([_window(s.address, len(s.data)) for s in spans])
    anchors = tuple(dict.fromkeys(p.code_anchors + profile.code_anchors))
    _disjoint([_window(a.address, a.size) for a in anchors])
    reader = _Reader(spans, anchors)
    for anchor in anchors:
        if sha256(reader.read(anchor.address, anchor.size)).hexdigest() != anchor.sha256:
            raise ValueError("Code anchor mismatch")
    actor_base = reader.u(p.actor_owner_address + 12)
    windows = [
        (p.pool_address, p.pool_capacity * 104),
        (p.actor_owner_address, 28),
        (actor_base, p.actor_capacity * 16),
    ] + [(a.address, a.size) for a in p.code_anchors]
    subset: list[InspectionSpan] = []
    for start, size in windows:
        reader.read(start, size)
        span = next(
            s for s in spans if s.address <= start and start + size <= s.address + len(s.data)
        )
        if span not in subset:
            subset.append(span)
    structural = decode_unit_pool_inspection(p, tuple(subset), game_id, patch_id, emulator_version)
    for start, size, category in (
        [
            (p.pool_address, p.pool_capacity * 104, "pool"),
            (p.actor_owner_address, 28, "owner"),
            (actor_base, p.actor_capacity * 16, "catalogue"),
            (profile.blocked_mech_ids_address, 154 * 4, "blocked"),
        ]
        + [(r.address, r.capacity * r.stride, "nodes") for r in profile.node_regions]
        + [
            (
                profile.mech_descriptors.address,
                profile.mech_descriptors.capacity * 12,
                "mech_descriptors",
            ),
            (
                profile.pilot_descriptors.address,
                profile.pilot_descriptors.capacity * 8,
                "pilot_descriptors",
            ),
        ]
    ):
        reader.region(start, size, category)
    catalogue = {
        a
        for a in range(actor_base, actor_base + p.actor_capacity * 16, 16)
        if reader.u(a) == p.actor_vtable
    }

    def walk(lst: int) -> list[int]:
        reader.view(lst, 36)
        reader.read(lst, 36)
        node = reader.u(lst + 12)
        seen: set[int] = set()
        actors: list[int] = []
        while node != lst + 20:
            if (
                node in seen
                or len(seen) >= min(1664, sum(r.capacity for r in profile.node_regions))
                or not any(
                    r.address <= node < r.address + r.capacity * 12 and (node - r.address) % 12 == 0
                    for r in profile.node_regions
                )
            ):
                raise ValueError("Invalid/cyclic list node")
            reader.view(node, 12)
            reader.read(node, 12)
            seen.add(node)
            actor = reader.u(node)
            if actor not in catalogue or actor in actors:
                raise ValueError("Invalid/duplicate catalogue actor")
            actors.append(actor)
            node = reader.u(node + 4)
        return actors

    s = reader.u(profile.source_root_global)
    a = reader.u(reader.u(s + 4))
    b = reader.u(reader.u(a + 4))
    source = walk(reader.u(b + 4))
    cache = walk(reader.u(profile.cache_owner_global) + 4)
    aliases = {
        binding.actor_address for slot in structural.slots for binding in slot.actor_bindings
    }
    descriptors: dict[int, tuple[int, int, int, int, int, int]] = {}

    def descriptor(address: int, region: InspectionRegion, kind: str) -> tuple[int, int]:
        if not address:
            return -1, 0
        if not (
            region.address <= address < region.address + region.capacity * region.stride
            and (address - region.address) % region.stride == 0
        ):
            raise ValueError("Invalid descriptor stride/range")
        reader.read(address, region.stride)
        metadata, header = reader.u(address), reader.u(address + 4)
        reader.region(metadata, 2, "metadata")
        identifier = int.from_bytes(reader.read(metadata, 2), "little", signed=True)
        if not -1 <= identifier <= 2047:
            raise ValueError("Invalid descriptor ID")
        size, offset = (96, 16) if kind == "mech" else (88, 8)
        # Complete capture coverage includes unused tail bytes in packed allocations.
        # Only the interpreted record footprint owns semantic storage.
        footprint = 0x24 if kind == "mech" else 0x3E
        reader.region(header + offset, footprint, kind + "_header")
        reader.read(header, size)
        return identifier, header + offset

    for actor in sorted(set(source) | set(cache) | aliases):
        md, pd = reader.u(actor + 4), reader.u(actor + 8)
        mech, mrec = descriptor(md, profile.mech_descriptors, "mech")
        pilot, prec = descriptor(pd, profile.pilot_descriptors, "pilot")
        if actor in aliases and (mech < 0 or pilot < 0):
            raise ValueError("Candidate missing descriptor/ID")
        descriptors[actor] = (md, pd, mech, pilot, mrec, prec)
    blocked_data = reader.read(profile.blocked_mech_ids_address, 154 * 4)
    blocked = [
        int.from_bytes(blocked_data[i : i + 4], "little", signed=True) for i in range(0, 616, 4)
    ]
    if blocked != sorted(blocked):
        raise ValueError("Unsorted blocked IDs")

    def object_ok(actor: int) -> bool:
        obj = reader.u(actor + 12)
        if not obj:
            return False
        if (
            not p.pool_address <= obj < p.pool_address + p.pool_capacity * 104
            or (obj - p.pool_address) % 104
        ):
            raise ValueError("Actor object is not a pool slot")
        return bool(reader.read(obj + 8, 1)[0] & 4)

    reconstructed = [
        actor
        for actor in source
        if object_ok(actor) and descriptors[actor][2] != -1 and descriptors[actor][2] not in blocked
    ]
    selector = reader.u(reader.u(profile.selector_owner_global) + 4)
    reader.region(selector, 90 * 8, "selector")
    pairs = reader.read(selector, 90 * 8)

    def identifier(value: int) -> int:
        if not -1 <= value <= 2047:
            raise ValueError("Invalid recipe ID")
        return value

    for i in range(90):
        mech = identifier(int.from_bytes(pairs[i * 8 : i * 8 + 4], "little", signed=True))
        pilot = identifier(int.from_bytes(pairs[i * 8 + 4 : i * 8 + 8], "little", signed=True))
        if mech == -1:
            continue
        matches = [actor for actor in source if descriptors[actor][2:4] == (mech, pilot)]
        if len(matches) > 1:
            raise ValueError("Ambiguous selector pair")
        if matches and object_ok(matches[0]):
            reconstructed.append(matches[0])
    exclusion = reader.u(reader.u(profile.pair_exclusion_owner_global) + 4)
    reader.region(exclusion, 4 + 127 * 20, "exclusion")
    data = reader.read(exclusion, 4 + 127 * 20)
    excluded: set[tuple[int, int]] = set()
    for i in range(127):
        start = 4 + i * 20
        mech = int.from_bytes(data[start + 4 : start + 8], "little", signed=True)
        pilot = int.from_bytes(data[start + 16 : start + 20], "little", signed=True)
        if int.from_bytes(data[start + 8 : start + 12], "little"):
            excluded.add((mech, pilot))
    reconstructed = [actor for actor in reconstructed if descriptors[actor][2:4] not in excluded]
    if len(set(reconstructed)) != len(reconstructed):
        raise ValueError("Duplicate reconstructed actor")
    if set(reconstructed) != set(cache):
        raise ValueError("Source recipe/cache disagreement")
    selected: dict[int, int] = {}
    for actor in reconstructed:
        obj = reader.u(actor + 12)
        if obj in selected:
            raise ValueError("Multiple representatives for object")
        selected[obj] = actor
    if set(selected) != {slot.object_address for slot in structural.slots}:
        raise ValueError("Candidate object coverage disagreement")
    rows: list[RepresentativeRecord] = []
    for slot in structural.slots:
        actor = selected[slot.object_address]
        md, pd, mech, pilot, mrec, prec = descriptors[actor]
        mdata, pdata = reader.read(mrec, 80), reader.read(prec, 80)

        def value(offset: int, size: int = 2, record: bytes = mdata) -> int:
            return int.from_bytes(record[offset : offset + size], "little")

        maximum, hp, maxen, en = value(0x18, 4), value(0x1C, 4), value(0x20), value(0x22)
        if not maximum or hp > maximum or en > maxen:
            raise ValueError("Inconsistent representative resources")
        rows.append(
            RepresentativeRecord(
                slot.slot_index,
                slot.object_address,
                actor,
                md,
                pd,
                mech,
                pilot,
                mrec,
                prec,
                hp,
                maximum,
                en,
                maxen,
                int.from_bytes(pdata[0x3C:0x3E], "little"),
                value(0xA),
                value(8),
                value(6),
                len(slot.actor_bindings),
            )
        )
    return RepresentativeInspectionReport(
        profile,
        tuple(rows),
        len(source),
        len(cache),
        len(reconstructed),
        tuple(sorted(spans, key=lambda s: s.address)),
    )
