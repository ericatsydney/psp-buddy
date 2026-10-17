"""Pure bounded structural inspection of supplied memory spans."""

from dataclasses import dataclass
from hashlib import sha256
from string import hexdigits

RAM_START = 0x08800000
RAM_END = 0x0A000000
UNAVAILABLE = ('unit_id', 'hp', 'max_hp', 'en', 'max_en', 'sp', 'max_sp', 'x', 'y',
               'side', 'action_available', 'dimensions', 'phase', 'terrain', 'legal_actions')


def _integer(value: object, low: int, high: int, label: str) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'Invalid {label}')


def _text(value: object) -> None:
    if (not isinstance(value, str) or not value.strip() or len(value) > 256
            or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value)):
        raise ValueError('Invalid identity, label or evidence text')


def _window(address: int, size: int, aligned: bool = False) -> tuple[int, int]:
    _integer(size, 1, RAM_END - RAM_START, 'window size')
    _integer(address, RAM_START, RAM_END - size, 'RAM window')
    if aligned and address % 4:
        raise ValueError('Misaligned address')
    return address, address + size


def _disjoint(windows: list[tuple[int, int]]) -> None:
    ordered = sorted(windows)
    if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:], strict=False)):
        raise ValueError('Overlapping windows')


@dataclass(frozen=True)
class CodeAnchor:
    address: int
    size: int
    sha256: str

    def __post_init__(self) -> None:
        _integer(self.size, 1, 4096, 'anchor size')
        _window(self.address, self.size)
        if (not isinstance(self.sha256, str) or len(self.sha256) != 64
                or any(char not in hexdigits for char in self.sha256)):
            raise ValueError('Invalid SHA-256')
        object.__setattr__(self, 'sha256', self.sha256.lower())


@dataclass(frozen=True)
class InspectionSpan:
    address: int
    data: bytes

    def __post_init__(self) -> None:
        if type(self.data) is not bytes or not 1 <= len(self.data) <= 65536:
            raise ValueError('Span requires 1..65536 immutable bytes')
        _window(self.address, len(self.data))


@dataclass(frozen=True)
class UnitPoolInspectionProfile:
    game_id: str
    patch_id: str
    emulator_version: str
    map_label: str
    pool_address: int
    pool_capacity: int
    pool_stride: int
    actor_owner_address: int
    actor_node_array_address: int
    actor_stride: int
    actor_capacity: int
    actor_vtable: int
    evidence_ids: tuple[str, ...]
    code_anchors: tuple[CodeAnchor, ...]

    def __post_init__(self) -> None:
        for text in (self.game_id, self.patch_id, self.emulator_version, self.map_label):
            _text(text)
        _integer(self.pool_capacity, 1, 256, 'pool capacity')
        _integer(self.actor_capacity, 1, 1024, 'actor capacity')
        _integer(self.pool_stride, 104, 104, 'pool stride')
        _integer(self.actor_stride, 16, 16, 'actor stride')
        pool = _window(self.pool_address, self.pool_capacity * 104, True)
        owner = _window(self.actor_owner_address, 28, True)
        _window(self.actor_node_array_address, 4, True)
        _window(self.actor_vtable, 4, True)
        if type(self.evidence_ids) is not tuple or not 1 <= len(self.evidence_ids) <= 32:
            raise ValueError('Invalid evidence count')
        for reference in self.evidence_ids:
            _text(reference)
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError('Duplicate evidence')
        if type(self.code_anchors) is not tuple or not 1 <= len(self.code_anchors) <= 8:
            raise ValueError('Invalid code anchors')
        windows = [pool, owner]
        total = 0
        for anchor in self.code_anchors:
            if type(anchor) is not CodeAnchor:
                raise ValueError('Invalid code anchor')
            anchor.__post_init__()
            windows.append(_window(anchor.address, anchor.size))
            total += anchor.size
        if total > 16384:
            raise ValueError('Code anchor total exceeds 16 KiB')
        _disjoint(windows)


@dataclass(frozen=True)
class UnitPoolActorBinding:
    actor_address: int
    mech_descriptor_address: int
    pilot_descriptor_address: int

    def to_dict(self) -> dict[str, int]:
        return {'actor_address': self.actor_address,
                'mech_descriptor_address': self.mech_descriptor_address,
                'pilot_descriptor_address': self.pilot_descriptor_address}


@dataclass(frozen=True)
class UnitPoolSlot:
    slot_index: int
    object_address: int
    occupancy_references: int
    raw_state_word: int
    raw_pixel_pair: tuple[int, int]
    actor_bindings: tuple[UnitPoolActorBinding, ...]

    def to_dict(self) -> dict[str, object]:
        mechs = sorted({actor.mech_descriptor_address for actor in self.actor_bindings})
        pilots = sorted({actor.pilot_descriptor_address for actor in self.actor_bindings})
        return {'slot_index': self.slot_index, 'object_address': self.object_address,
                'occupancy_references': self.occupancy_references,
                'raw_state_word': self.raw_state_word, 'raw_pixel_pair': list(self.raw_pixel_pair),
                'actor_bindings': [actor.to_dict() for actor in self.actor_bindings],
                'ambiguities': {'mech_descriptor_addresses': mechs if len(mechs) > 1 else [],
                                'pilot_descriptor_addresses': pilots if len(pilots) > 1 else []}}


@dataclass(frozen=True)
class UnitPoolInspectionReport:
    game_id: str
    patch_id: str
    emulator_version: str
    map_label: str
    slot_capacity: int
    empty_slots: int
    inactive_slots: int
    empty_slots_with_active_bit: int
    slots: tuple[UnitPoolSlot, ...]

    def to_dict(self) -> dict[str, object]:
        return {'inspection_kind': 'unit_pool_inspection', 'mode': 'offline_read_only',
                'game_id': self.game_id, 'patch_id': self.patch_id,
                'emulator_version': self.emulator_version, 'map_label': self.map_label,
                'provenance': 'user_supplied_spans_and_profile',
                'roster_completeness': 'candidate_slots_only', 'live_authenticated': False,
                'autonomous_available': False, 'autonomous_execution_enabled': False,
                'tactical_snapshot_available': False, 'candidate_count': len(self.slots),
                'slot_capacity': self.slot_capacity,
                'exclusions': {'empty_slots': self.empty_slots,
                               'inactive_slots': self.inactive_slots,
                               'empty_slots_with_active_bit': self.empty_slots_with_active_bit},
                'slots': [slot.to_dict() for slot in self.slots],
                'unavailable_fields': {field: 'not_decoded_by_structural_inspector'
                                       for field in UNAVAILABLE}}


def decode_unit_pool_inspection(
    profile: UnitPoolInspectionProfile, spans: tuple[InspectionSpan, ...],
    game_id: str, patch_id: str, emulator_version: str,
) -> UnitPoolInspectionReport:
    """Validate supplied identity/layout and retain every structurally consistent alias."""
    if type(profile) is not UnitPoolInspectionProfile:
        raise ValueError('Invalid profile')
    profile.__post_init__()
    for value in (game_id, patch_id, emulator_version):
        _text(value)
    if (game_id, patch_id, emulator_version) != (
            profile.game_id, profile.patch_id, profile.emulator_version):
        raise ValueError('Inspection identity mismatch')
    if type(spans) is not tuple or not 1 <= len(spans) <= 32:
        raise ValueError('Invalid span count or mutable collection')
    for span in spans:
        if type(span) is not InspectionSpan:
            raise ValueError('Invalid span')
        span.__post_init__()
    if sum(len(span.data) for span in spans) > 1048576:
        raise ValueError('Span total exceeds 1 MiB')
    _disjoint([_window(span.address, len(span.data)) for span in spans])

    def read(address: int, size: int) -> bytes:
        _, end = _window(address, size)
        for span in spans:
            if span.address <= address and end <= span.address + len(span.data):
                return span.data[address - span.address:end - span.address]
        raise ValueError('Missing contiguous captured window')

    for anchor in profile.code_anchors:
        if sha256(read(anchor.address, anchor.size)).hexdigest() != anchor.sha256:
            raise ValueError('Code anchor mismatch')
    owner = read(profile.actor_owner_address, 28)
    if (_word(owner, 8), _word(owner, 16), _word(owner, 20)) != (
            profile.actor_node_array_address, profile.actor_stride, profile.actor_capacity):
        raise ValueError('Actor owner metadata mismatch')
    actor_base = _word(owner, 12)
    actor_window = _window(actor_base, profile.actor_capacity * 16, True)
    pool_window = _window(profile.pool_address, profile.pool_capacity * 104, True)
    _disjoint([pool_window, _window(profile.actor_owner_address, 28), actor_window]
              + [_window(anchor.address, anchor.size) for anchor in profile.code_anchors])
    pool = read(profile.pool_address, profile.pool_capacity * 104)
    actors = read(actor_base, profile.actor_capacity * 16)
    included: dict[int, tuple[int, int, tuple[int, int]]] = {}
    bindings: dict[int, list[UnitPoolActorBinding]] = {}
    empty = inactive = empty_active = 0
    for index in range(profile.pool_capacity):
        offset = index * 104
        refs, state = pool[offset], _word(pool, offset + 20)
        if not refs:
            empty += 1
            empty_active += bool(state & 1)
        elif not state & 1:
            inactive += 1
        else:
            included[index] = refs, state, (_word(pool, offset + 24), _word(pool, offset + 28))
            bindings[index] = []
    for index in range(profile.actor_capacity):
        offset = index * 16
        if _word(actors, offset) != profile.actor_vtable:
            continue
        object_address = _word(actors, offset + 12)
        if not object_address:
            continue
        if not (pool_window[0] <= object_address < pool_window[1]) or (
                object_address - profile.pool_address) % 104:
            raise ValueError('Actor object is not a declared pool slot')
        slot_index = (object_address - profile.pool_address) // 104
        if slot_index not in included:
            continue
        mech, pilot = _word(actors, offset + 4), _word(actors, offset + 8)
        _window(mech, 4, True)
        _window(pilot, 4, True)
        bindings[slot_index].append(UnitPoolActorBinding(actor_base + offset, mech, pilot))
    slots: list[UnitPoolSlot] = []
    for index, (refs, state, pixels) in included.items():
        if len(bindings[index]) != refs:
            raise ValueError('Actor alias count disagrees with occupancy references')
        slots.append(UnitPoolSlot(index, profile.pool_address + index * 104,
                                  refs, state, pixels, tuple(bindings[index])))
    return UnitPoolInspectionReport(profile.game_id, profile.patch_id, profile.emulator_version,
                                    profile.map_label, profile.pool_capacity, empty, inactive,
                                    empty_active, tuple(slots))


def _word(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 4], 'little')
