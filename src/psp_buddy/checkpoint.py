"""Offline single-slot contracts. A live backend remains an unpassed integration gate.

The backend must prove emulator completion and decode the complete state format;
request acknowledgements and file modification times are insufficient evidence.
"""

import asyncio
import hashlib
import math
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .backup import _safe_path
from .models import (
    ActionKind,
    Affiliation,
    CheckpointReceipt,
    Phase,
    Screen,
    Snapshot,
    ValidationStatus,
)

MAX_STATE_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True)
class CheckpointCompletion:
    request_id: str
    operation: str
    slot: int
    game_id: str
    map_id: str
    success: bool
    checkpoint_id: str
    state_path: Path


@dataclass(frozen=True)
class StateArtifact:
    slot: int
    game_id: str
    map_id: str
    checkpoint_id: str
    size: int
    sha256: str
    complete_format: bool
    state_fingerprint: str | None = None


class CheckpointBackend(Protocol):
    """Trusted adapter contract; inspection must decode actual state metadata."""

    async def request_save(self, slot: int) -> str: ...
    async def request_load(self, slot: int) -> str: ...
    async def wait_complete(self, request_id: str) -> CheckpointCompletion: ...
    async def inspect_state(self, path: Path) -> StateArtifact: ...
    async def observe(self) -> Snapshot: ...


def _state(snapshot: Snapshot) -> tuple[object, ...]:
    return (snapshot.map_id, snapshot.game_id, snapshot.patch_id, snapshot.profile_id,
            snapshot.turn, snapshot.phase, snapshot.screen, snapshot.cursor, snapshot.units,
            snapshot.confirmed_defeated_ids, snapshot.scripted_departure_ids,
            snapshot.map_complete, snapshot.dialogue_id)


def checkpoint_state_fingerprint(snapshot: Snapshot) -> str:
    """In-process v1 contract: decoder must reconstruct the same tactical fields.

    This is not a PPSSPP header field or durable cross-version format.
    """
    return hashlib.sha256(repr(_state(snapshot)).encode('utf-8')).hexdigest()


class VerifiedCheckpointService:
    """One selected slot, issuer-owned receipts, and fail-closed completion.

    On uncertainty retain the prior receipt for handover, disable all operations,
    and require a new protected session. This cannot guarantee that a failing live
    adapter preserved the file; supported undo and immutable backups remain gates.
    """

    def __init__(self, slot: int, game_id: str, map_id: str, backend: CheckpointBackend,
                 *, state_root: Path, timeout_seconds: float = 5) -> None:
        if type(slot) is not int or not 1 <= slot <= 5 or not game_id or not map_id:
            raise ValueError('invalid selected slot or identity')
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError('invalid checkpoint timeout')
        _safe_path(state_root)
        if not state_root.is_dir():
            raise ValueError('protected checkpoint state root must exist')
        self._root = state_root.resolve()
        self._slot, self._game, self._map = slot, game_id, map_id
        self._backend, self._timeout = backend, timeout_seconds
        self._receipt: CheckpointReceipt | None = None
        self._saved: Snapshot | None = None
        self._last: Snapshot | None = None
        self._uncertain = False
        self._lock = asyncio.Lock()

    @property
    def receipt(self) -> CheckpointReceipt | None:
        return self._receipt

    @property
    def current_snapshot(self) -> Snapshot | None:
        return self._last

    def _safe_snapshot(self, snapshot: Snapshot, *, completed: bool = True) -> None:
        if (snapshot.validation is not ValidationStatus.VALIDATED
                or (snapshot.game_id, snapshot.map_id) != (self._game, self._map)
                or snapshot.phase is not Phase.PLAYER or snapshot.screen is not Screen.MAP
                or snapshot.map_complete is not False or snapshot.turn is None
                or snapshot.units is None or not snapshot.units
                or snapshot.legal_actions is None or snapshot.confirmed_defeated_ids
                or (completed and any(a.kind is not ActionKind.END_TURN
                                      for a in snapshot.legal_actions))):
            raise ValueError('checkpoint requires resolved validated player map')
        allies = [u for u in snapshot.units if u.affiliation is Affiliation.ALLY]
        active = [u for u in allies if u.scripted_departure is not True]
        if (not active or any(u.affiliation is Affiliation.UNKNOWN for u in snapshot.units)
                or any(u.defeated is not False for u in allies)
                or any(u.hp is None or u.hp <= 0
                       or u.max_hp is None or u.max_hp <= 0
                       or type(u.action_available) is not bool
                       or (completed and u.action_available is not False) for u in active)):
            raise ValueError('allied safety or completed actions unresolved')

    def _fresh(self, observed: Snapshot, previous: Snapshot) -> None:
        self._safe_snapshot(observed, completed=False)
        if (observed.sequence <= previous.sequence or observed.capture_id == previous.capture_id
                or _state(observed) != _state(previous)):
            raise ValueError('checkpoint observation is stale or state mismatched')

    def can_end_turn(self, snapshot: Snapshot, receipt: CheckpointReceipt | None) -> bool:
        if (self._uncertain or receipt is None or receipt is not self._receipt
                or not receipt.verified):
            return False
        try:
            self._safe_snapshot(snapshot)
        except ValueError:
            return False
        return (self._last is not None and snapshot == self._last
                and self._saved is not None and _state(snapshot) == _state(self._saved))

    def _read(self, path: Path) -> bytes:
        _safe_path(self._root)
        _safe_path(path)
        if not path.resolve().is_relative_to(self._root):
            raise ValueError('checkpoint artifact outside protected state root')
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not 0 < before.st_size <= MAX_STATE_BYTES):
            raise ValueError('invalid checkpoint artifact')
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            data = stream.read(MAX_STATE_BYTES + 1)
            after = os.fstat(stream.fileno())
        _safe_path(self._root)
        _safe_path(path)
        if not path.resolve().is_relative_to(self._root):
            raise ValueError('checkpoint artifact outside protected state root')
        current = path.lstat()
        def signature(info: os.stat_result) -> tuple[int, int, int, int, int]:
            return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink
        if (len(data) > MAX_STATE_BYTES or not signature(before) == signature(opened)
                == signature(after) == signature(current)):
            raise ValueError('checkpoint artifact changed while reading')
        return data

    async def _artifact(self, completion: CheckpointCompletion, expected: Snapshot) -> str:
        data = self._read(completion.state_path)
        metadata = await self._backend.inspect_state(completion.state_path)
        digest = hashlib.sha256(data).hexdigest()
        if (metadata.complete_format is not True or metadata.size != len(data)
                or metadata.state_fingerprint != checkpoint_state_fingerprint(expected)
                or metadata.sha256 != digest or not completion.checkpoint_id
                or (metadata.slot, metadata.game_id, metadata.map_id, metadata.checkpoint_id)
                != (self._slot, self._game, self._map, completion.checkpoint_id)
                or self._read(completion.state_path) != data):
            raise ValueError('checkpoint artifact verification failed')
        return digest

    async def _complete(self, request: str, operation: str) -> CheckpointCompletion:
        if not request:
            raise ValueError('missing checkpoint request identity')
        completion = await self._backend.wait_complete(request)
        if (completion.success is not True or completion.request_id != request
                or completion.operation != operation
                or (completion.slot, completion.game_id, completion.map_id)
                != (self._slot, self._game, self._map)):
            raise ValueError('checkpoint completion failed or identity mismatched')
        return completion

    @staticmethod
    def _check_deadline(deadline: float) -> None:
        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError('checkpoint deadline expired')

    async def verify_initial_checkpoint(self, snapshot: Snapshot,
                                        state_path: Path) -> CheckpointReceipt:
        """Adopt a user-selected artifact without issuing any save/load command."""
        async with self._lock:
            if self._uncertain or self._receipt is not None:
                raise ValueError('initial checkpoint requires a fresh protected session')
            self._safe_snapshot(snapshot, completed=False)
            try:
                deadline = asyncio.get_running_loop().time() + self._timeout
                async with asyncio.timeout_at(deadline):
                    self._read(state_path)
                    self._check_deadline(deadline)
                    metadata = await self._backend.inspect_state(state_path)
                    self._check_deadline(deadline)
                    completion = CheckpointCompletion('', 'initial', self._slot, self._game,
                        self._map, True, metadata.checkpoint_id, state_path)
                    digest = await self._artifact(completion, snapshot)
                    self._check_deadline(deadline)
                    observed = await self._backend.observe()
                    self._check_deadline(deadline)
                    self._fresh(observed, snapshot)
                    receipt = CheckpointReceipt(self._slot, self._game, self._map,
                        snapshot.sequence, completion.checkpoint_id, state_path, digest, True)
                self._receipt, self._saved, self._last = receipt, snapshot, observed
                return receipt
            except BaseException:
                self._uncertain = True
                raise
    async def save_checkpoint(self, snapshot: Snapshot) -> CheckpointReceipt:
        async with self._lock:
            if self._uncertain:
                raise ValueError('checkpoint completion uncertain; new protected session required')
            self._safe_snapshot(snapshot)
            if self._last is not None and snapshot.sequence < self._last.sequence:
                raise ValueError('stale checkpoint input')
            try:
                deadline = asyncio.get_running_loop().time() + self._timeout
                async with asyncio.timeout_at(deadline):
                    request = await self._backend.request_save(self._slot)
                    completion = await self._complete(request, 'save')
                    self._check_deadline(deadline)
                    digest = await self._artifact(completion, snapshot)
                    self._check_deadline(deadline)
                    observed = await self._backend.observe()
                    self._check_deadline(deadline)
                    self._fresh(observed, snapshot)
                    self._safe_snapshot(observed)
                    receipt = CheckpointReceipt(self._slot, self._game, self._map,
                        snapshot.sequence, completion.checkpoint_id, completion.state_path,
                        digest, True)
                self._receipt, self._saved, self._last = receipt, snapshot, observed
                return receipt
            except BaseException:
                self._uncertain = True
                raise

    async def load_checkpoint(self, receipt: CheckpointReceipt) -> Snapshot:
        async with self._lock:
            if (self._uncertain or receipt is not self._receipt or not receipt.verified
                    or self._saved is None or self._last is None):
                raise ValueError('load requires current issuer-verified receipt')
            try:
                deadline = asyncio.get_running_loop().time() + self._timeout
                async with asyncio.timeout_at(deadline):
                    baseline = CheckpointCompletion('', 'load', receipt.slot, receipt.game_id,
                        receipt.map_id, True, receipt.checkpoint_id, receipt.state_path)
                    if await self._artifact(baseline, self._saved) != receipt.sha256:
                        raise ValueError('checkpoint artifact no longer matches receipt')
                    self._check_deadline(deadline)
                    request = await self._backend.request_load(self._slot)
                    completion = await self._complete(request, 'load')
                    self._check_deadline(deadline)
                    if (completion.checkpoint_id != receipt.checkpoint_id
                            or completion.state_path != receipt.state_path
                            or await self._artifact(completion, self._saved) != receipt.sha256):
                        raise ValueError('restored artifact mismatched')
                    observed = await self._backend.observe()
                    self._check_deadline(deadline)
                    self._fresh(observed, self._last)
                    if _state(observed) != _state(self._saved):
                        raise ValueError('restored battle state mismatched')
                self._last = observed
                return observed
            except BaseException:
                self._uncertain = True
                raise





