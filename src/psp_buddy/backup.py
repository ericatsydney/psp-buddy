"""Fail-closed, fresh save snapshots. No emulator launch or debugger operations.

The runner never modifies snapshots after verification; writable trial files live
separately. Snapshots remain owner-writable and are reverified before launch, rather
than changing host ACLs or treating them as an OS-enforced immutable store.
"""

import hashlib
import json
import math
import os
import shutil
import stat
import subprocess
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from .config import RunConfig, paths_overlap
from .models import BackupFile, BackupReceipt


class NonWritingGuard(Protocol):
    """Trusted integration dependency: raise unless non-writing is established.

    Implementations for a running emulator must validate an explicit non-writing
    mechanism throughout the operation. A stable timestamp or boolean is insufficient.
    """

    def assert_non_writing(self, config: RunConfig) -> object: ...


class ClosedProcessGuard:
    """Conservatively deny any PPSSPP process, including renamed configured binaries."""

    def assert_non_writing(self, config: RunConfig) -> None:
        if os.name != "nt":
            raise ValueError("reliable emulator process check unavailable")
        script = (
            "$ErrorActionPreference='Stop'; "
            "@(Get-CimInstance Win32_Process | Select-Object Name,ExecutablePath) "
            "| ConvertTo-Json -Compress"
        )
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                check=True, capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            rows = json.loads(result.stdout)
            if not isinstance(rows, list) or not rows:
                raise ValueError("invalid process inventory")
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("Name"), str):
                    raise ValueError("invalid process inventory")
                name = row["Name"].casefold()
                path = row.get("ExecutablePath")
                if ("ppsspp" in name or name == config.emulator_path.name.casefold()
                        or isinstance(path, str)
                        and Path(path).resolve() == config.emulator_path.resolve()):
                    raise ValueError("emulator must be closed before backup")
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            raise ValueError("emulator non-writing status unavailable") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_path(path: Path) -> None:
    for entry in (path, *path.parents):
        if not entry.exists() and not entry.is_symlink():
            continue
        info = entry.lstat()
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError(f"unsafe link or reparse point: {entry}")


# Relative path, entry kind, size and digest include empty directories.
Inventory = tuple[tuple[str, str, int, str], ...]


def inventory(root: Path, hash_file: Callable[[Path], str] = sha256) -> Inventory:
    _safe_path(root)
    if not root.is_dir():
        raise ValueError(f"missing save root: {root}")
    entries: list[tuple[str, str, int, str]] = []
    for path in sorted(root.rglob("*")):
        _safe_path(path)
        info = path.lstat()
        relative = path.relative_to(root).as_posix()
        if stat.S_ISDIR(info.st_mode):
            entries.append((relative, "directory", 0, ""))
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            before = (info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            digest = hash_file(path)
            after_info = path.stat()
            after = (after_info.st_size, after_info.st_mtime_ns, after_info.st_ctime_ns)
            if before != after:
                raise ValueError("source changed during hashing")
            entries.append((relative, "file", info.st_size, digest))
        else:
            raise ValueError(f"unsafe special file or hard link: {path}")
    return tuple(entries)


def writable_trial_root(receipt: BackupReceipt) -> Path:
    return receipt.snapshot_root.parent / "working"


class BackupGate:
    def __init__(
        self, *, guard: NonWritingGuard | None = None,
        copy_file: Callable[[Path, Path], object] = shutil.copy2,
        hash_file: Callable[[Path], str] = sha256,
        freshness_seconds: float = 60,
    ) -> None:
        if (isinstance(freshness_seconds, bool) or not math.isfinite(freshness_seconds)
                or freshness_seconds <= 0):
            raise ValueError("receipt freshness must be positive and finite")
        self.freshness_seconds = freshness_seconds
        self.guard = guard if guard is not None else ClosedProcessGuard()
        self.copy_file = copy_file
        self.hash_file = hash_file
        self._issued: dict[str, BackupReceipt] = {}
        self._consumed: set[str] = set()
        self._inventories: dict[str, tuple[Inventory, ...]] = {}

    def _guard(self, config: RunConfig) -> None:
        if self.guard.assert_non_writing(config) is not None:
            raise ValueError("non-writing guard must validate, not return a boolean")

    def _validate_roots(self, config: RunConfig) -> None:
        roots = config.save_roots
        _safe_path(config.backup_root)
        for index, root in enumerate(roots):
            _safe_path(root)
            if not root.is_dir():
                raise ValueError(f"missing save root: {root}")
            if paths_overlap(root, config.backup_root) or any(
                paths_overlap(root, other) for other in roots[index + 1:]
            ):
                raise ValueError("backup/source roots overlap")

    def prepare_trial(self, config: RunConfig) -> BackupReceipt:
        self._validate_roots(config)
        self._guard(config)
        trial_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex
        trial = config.backup_root / trial_id
        trial.mkdir(parents=True, exist_ok=False)
        incomplete = trial / "INCOMPLETE"
        incomplete.write_text("Backup verification incomplete; never authorize a trial.\n")
        snapshot = trial / "snapshot"
        working = trial / "working"
        snapshot.mkdir()
        working.mkdir()
        roots = tuple(root.absolute() for root in config.save_roots)
        before = tuple(inventory(root, self.hash_file) for root in roots)
        files: list[BackupFile] = []
        for index, (source, entries) in enumerate(zip(roots, before, strict=True)):
            label = f"{index}-{source.name}"
            for destination in (snapshot / label, working / label):
                destination.mkdir()
                for relative, kind, size, digest in entries:
                    self._guard(config)
                    source_path = source / relative
                    _safe_path(source_path)
                    target = destination / relative
                    if kind == "directory":
                        target.mkdir()
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            self.copy_file(source_path, target)
                        except OSError as exc:
                            raise ValueError("backup copy failed") from exc
                        if self.hash_file(target) != digest:
                            raise ValueError("backup hash mismatch")
                        if destination.parent == snapshot:
                            files.append(BackupFile(source_path, target, digest, size))
                if inventory(destination, self.hash_file) != entries:
                    raise ValueError("backup inventory or hash mismatch")
        self._guard(config)
        after = tuple(inventory(root, self.hash_file) for root in roots)
        self._guard(config)
        if before != after:
            raise ValueError("source inventory or hash changed during backup")
        created = datetime.now(UTC).isoformat()
        manifest_path = trial / "manifest.json"
        manifest = {
            "trial_id": trial_id, "created_at": created,
            "source_roots": [str(root) for root in roots],
            "snapshot_root": str(snapshot), "working_root": str(working),
            "inventories": before,
            "files": [{"source": str(f.source), "copied": str(f.copied),
                       "sha256": f.sha256, "size": f.size} for f in files],
        }
        with manifest_path.open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, indent=2)
        receipt = BackupReceipt(trial_id, snapshot, manifest_path, roots, tuple(files), created)
        self._issued[trial_id] = receipt
        self._inventories[trial_id] = before
        incomplete.unlink()
        return receipt

    def validate_receipt(self, config: RunConfig, receipt: BackupReceipt) -> None:
        """Revalidate current provenance immediately BEFORE emulator launch.

        Only this gate's freshly issued receipts are accepted. Successful validation
        consumes the receipt; subsequent trials require a new complete snapshot.
        This does not authorize arbitrary running-emulator connections: a launch
        adapter must bind the actual process and effective memory stick to /working.
        """
        if (self._issued.get(receipt.trial_id) is not receipt
                or receipt.trial_id in self._consumed):
            raise ValueError("unknown or consumed backup receipt")
        age = (datetime.now(UTC) - datetime.fromisoformat(receipt.created_at)).total_seconds()
        if not 0 <= age <= self.freshness_seconds:
            raise ValueError("stale backup receipt; prepare a fresh trial")
        self._validate_roots(config)
        self._guard(config)
        if tuple(root.absolute() for root in config.save_roots) != receipt.source_roots:
            raise ValueError("receipt source roots mismatch")
        if receipt.snapshot_root.parent != config.backup_root / receipt.trial_id:
            raise ValueError("receipt backup root mismatch")
        _safe_path(receipt.manifest_path)
        manifest = json.loads(receipt.manifest_path.read_text(encoding="utf-8"))
        expected = {
            "trial_id": receipt.trial_id, "created_at": receipt.created_at,
            "source_roots": [str(root) for root in receipt.source_roots],
            "snapshot_root": str(receipt.snapshot_root),
            "working_root": str(writable_trial_root(receipt)),
            "files": [{"source": str(f.source), "copied": str(f.copied),
                       "sha256": f.sha256, "size": f.size} for f in receipt.files],
        }
        if any(manifest.get(key) != value for key, value in expected.items()):
            raise ValueError("receipt manifest provenance mismatch")
        inventories = manifest.get("inventories")
        if inventories != json.loads(json.dumps(self._inventories[receipt.trial_id])):
            raise ValueError("receipt manifest inventory provenance mismatch")
        for base in (None, receipt.snapshot_root, writable_trial_root(receipt)):
            current = [inventory(root if base is None else base / f"{index}-{root.name}",
                                 self.hash_file)
                       for index, root in enumerate(receipt.source_roots)]
            if json.loads(json.dumps(current)) != inventories:
                raise ValueError("receipt inventory or hash changed")
        self._guard(config)
        age = (datetime.now(UTC) - datetime.fromisoformat(receipt.created_at)).total_seconds()
        if not 0 <= age <= self.freshness_seconds:
            raise ValueError("stale backup receipt; prepare a fresh trial")
        self._consumed.add(receipt.trial_id)


def prepare_trial(config: RunConfig) -> BackupReceipt:
    """Default production entry point; reliable closed-process checks are mandatory."""
    return BackupGate().prepare_trial(config)

