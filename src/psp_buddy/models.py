"""Immutable shared contracts; None means unknown, never an inferred zero."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .config import RunConfig


class Affiliation(Enum):
    ALLY = "ally"
    ENEMY = "enemy"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class Phase(Enum):
    PLAYER = "player"
    ENEMY = "enemy"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


class Screen(Enum):
    MAP = "map"
    MENU = "menu"
    REACTION = "reaction"
    DIALOGUE = "dialogue"
    CHOICE = "choice"
    MAP_CLEAR = "map_clear"
    UNKNOWN = "unknown"


class ActionKind(Enum):
    MOVE = "move"
    ATTACK = "attack"
    REPAIR = "repair"
    TRUST = "trust"
    WAIT = "wait"
    END_TURN = "end_turn"
    DEFEND = "defend"
    EVADE = "evade"
    COUNTER = "counter"
    SKIP_DIALOGUE = "skip_dialogue"
    HANDOVER = "handover"


class ValidationStatus(Enum):
    UNAVAILABLE = "unavailable"
    PARTIAL = "partial"
    VALIDATED = "validated"


Position = tuple[int, int]


@dataclass(frozen=True)
class Prediction:
    attacker_id: str
    target_id: str
    weapon_id: str | None = None
    damage: int | None = None
    hit_rate: int | None = None
    validated: bool = False


@dataclass(frozen=True)
class Weapon:
    id: str
    power: int | None = None
    en_cost: int | None = None
    ammo_cost: int | None = None
    ammo: int | None = None
    min_range: int | None = None
    max_range: int | None = None
    post_move: bool | None = None
    map_attack: bool | None = None
    risks_allies: bool | None = None
    legal_target_ids: tuple[str, ...] | None = None
    predictions: tuple[Prediction, ...] = ()


@dataclass(frozen=True)
class Unit:
    id: str
    type_id: str
    affiliation: Affiliation
    position: Position | None = None
    hp: int | None = None
    max_hp: int | None = None
    en: int | None = None
    max_en: int | None = None
    pilot_id: str | None = None
    level: int | None = None
    defense: int | None = None
    sp: int | None = None
    action_available: bool | None = None
    defeated: bool | None = None
    scripted_departure: bool | None = None
    repair_capable: bool | None = None
    trust_capable: bool | None = None
    trust_sp_cost: int | None = None
    legal_repair_targets: tuple[str, ...] | None = None
    legal_trust_targets: tuple[str, ...] | None = None
    legal_moves: tuple[Position, ...] | None = None
    # Validated enemy attack reach for this turn, including permitted movement.
    attack_positions: tuple[Position, ...] | None = None
    weapons: tuple[Weapon, ...] | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.type_id:
            raise ValueError("unit identity required")
        if self.hp is not None and (type(self.hp) is not int or self.hp < 0):
            raise ValueError("invalid HP")
        if self.max_hp is not None:
            if type(self.max_hp) is not int or self.max_hp <= 0:
                raise ValueError("invalid maximum HP")
            if self.hp is not None and self.hp > self.max_hp:
                raise ValueError("HP exceeds maximum HP")


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    snapshot_sequence: int
    actor_id: str | None = None
    target_id: str | None = None
    weapon_id: str | None = None
    destination: Position | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if type(self.snapshot_sequence) is not int or self.snapshot_sequence < 0:
            raise ValueError("invalid action snapshot sequence")


@dataclass(frozen=True)
class Snapshot:
    sequence: int
    map_id: str | None = None
    game_id: str | None = None
    patch_id: str | None = None
    capture_id: str | None = None
    profile_id: str | None = None
    validation: ValidationStatus = ValidationStatus.UNAVAILABLE
    turn: int | None = None
    phase: Phase = Phase.UNKNOWN
    screen: Screen = Screen.UNKNOWN
    cursor: Position | None = None
    units: tuple[Unit, ...] | None = None
    legal_actions: tuple[Action, ...] | None = None
    predictions: tuple[Prediction, ...] = ()
    confirmed_defeated_ids: tuple[str, ...] = ()
    scripted_departure_ids: tuple[str, ...] = ()
    map_complete: bool | None = None
    paused: bool | None = None
    # Evidence-bound identity of recognized decision-free dialogue content/position.
    # A fresh capture alone cannot prove that skipping advanced the dialogue.
    dialogue_id: str | None = None

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("invalid snapshot sequence")
        if self.dialogue_id is not None and (
            not isinstance(self.dialogue_id, str) or not self.dialogue_id.strip()
        ):
            raise ValueError("invalid dialogue identity")
        if self.legal_actions is not None and any(
            action.snapshot_sequence != self.sequence for action in self.legal_actions
        ):
            raise ValueError("stale legal action evidence")
        if self.validation is ValidationStatus.VALIDATED and not all(
            (self.map_id, self.game_id, self.patch_id, self.capture_id, self.profile_id)
        ):
            raise ValueError("validated snapshot requires complete identity")


@dataclass(frozen=True)
class Policy:
    heal_below_percent: int = 70
    evade_below_percent: int = 50
    defend_above_hit_percent: int = 80
    cheap_weapon_below_percent: int = 20
    strongest_boss_above_percent: int = 90
    common_type_min_count: int = 4
    max_retries: int = 3
    stop_on_map_clear: bool = True

    def __post_init__(self) -> None:
        if type(self.max_retries) is not int or not 0 <= self.max_retries <= 3:
            raise ValueError("max_retries must be from 0 to 3")


@dataclass(frozen=True)
class GameProfile:
    id: str
    game_id: str
    patch_id: str
    emulator_version: str
    validated_fields: tuple[str, ...] = ()
    supported_map_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class BackupFile:
    source: Path
    copied: Path
    sha256: str
    size: int


@dataclass(frozen=True)
class BackupReceipt:
    trial_id: str
    snapshot_root: Path
    manifest_path: Path
    source_roots: tuple[Path, ...]
    files: tuple[BackupFile, ...]
    created_at: str


@dataclass(frozen=True)
class CheckpointReceipt:
    slot: int
    game_id: str
    map_id: str
    snapshot_sequence: int
    checkpoint_id: str
    state_path: Path
    sha256: str
    verified: bool = False


@dataclass(frozen=True)
class Handover:
    reason: str
    checkpoint: CheckpointReceipt | None = None
    retry_count: int = 0
    affected_unit_ids: tuple[str, ...] = ()
    history: tuple[Action, ...] = ()
    paused: bool | None = None


class BackupService(Protocol):
    def prepare_trial(self, config: "RunConfig") -> BackupReceipt: ...


class Observer(Protocol):
    async def observe(self) -> Snapshot: ...


class PolicyParser(Protocol):
    def parse_policy(self, text: str) -> Policy: ...


class Planner(Protocol):
    def choose_action(self, snapshot: Snapshot, policy: Policy) -> Action: ...


class Executor(Protocol):
    async def execute(self, action: Action, before: Snapshot) -> Snapshot: ...


class CheckpointService(Protocol):
    async def save_checkpoint(self, snapshot: Snapshot) -> CheckpointReceipt: ...
    async def load_checkpoint(self, receipt: CheckpointReceipt) -> Snapshot: ...


class ReactionPlanner(Protocol):
    def choose_reaction(
        self, snapshot: Snapshot, policy: Policy, attempt: int, history: Sequence[Action]
    ) -> Action: ...
