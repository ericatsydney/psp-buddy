"""Delete old backup cycles (user, 7 and 10 Nov: drive C: was full).

After each launch the newest 5 complete backups are kept of each of three kinds: verified snapshots,
portable-memstick backups and `<label>-original-` backups. Only those three folder name shapes are
ever deleted, and never anything under the active runtime; runtime archives are not touched at all.
Best effort: a folder that cannot be deleted is recorded and skipped.
"""

import json
import os
import re
import shutil
import stat
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from .config import paths_overlap

KEEP = 5
TRIAL_ID = re.compile(r"(\d{8}T\d{12}Z)-[0-9a-f]{32}")
PORTABLE_BACKUP = re.compile(r"portable-memstick-(\d{8}T\d{6}Z)")
ORIGINAL_BACKUP = re.compile(r".+-original-(\d{8}T\d{6}Z)(?:-[0-9a-f]{32})?")
# Two local test_collector.py files read these RAM dumps (user, 10 Nov: keep what a test needs).
EVIDENCE_FOLDER = "user-evidence"
EVIDENCE_TEST_TRIALS = frozenset({
    "20261015T120025749948Z-0289b926396c4c3683c13be0b1f44c51",
    "20261015T065827988941Z-c31825d738e445cc9db4e7fa0ceb0173",
})


@dataclass(frozen=True)
class PruneResult:
    removed: tuple[Path, ...] = ()
    failed: tuple[tuple[Path, str], ...] = ()


def _plain_dir(path: Path) -> bool:
    """A real directory: not a symlink, junction or other reparse point."""
    try:
        info = os.lstat(path)
    except OSError:
        return False
    if not stat.S_ISDIR(info.st_mode):
        return False
    return not getattr(info, "st_file_attributes", 0) & getattr(
        stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _same(a: Path, b: Path | None) -> bool:
    return b is not None and os.path.normcase(a.absolute()) == os.path.normcase(b.absolute())


def _snapshot_complete(path: Path) -> bool:
    return (path / "manifest.json").is_file() and not (path / "INCOMPLETE").exists()


def _dated_complete(path: Path) -> bool:
    """A non-empty manifest list with no failed entry. The PowerShell backups write a BOM."""
    try:
        entries = json.loads((path / "manifest.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    return (isinstance(entries, list) and bool(entries)
            and all(isinstance(e, dict) and e.get("verified") is not False for e in entries))


def _children(parent: Path) -> list[Path]:
    try:
        return list(parent.iterdir())
    except OSError:     # missing or unreadable: nothing to prune, and pruning must never raise
        return []


def _older_than_kept(paths: list[Path], pattern: re.Pattern[str],
                     complete: Callable[[Path], bool], keep: int) -> list[Path]:
    """Folders of one kind older than its `keep`-th complete backup, by the name's timestamp."""
    dated = []
    for path in paths:
        match = pattern.fullmatch(path.name)
        if match and _plain_dir(path):
            dated.append((match.group(1), path.name, path))
    dated.sort(reverse=True)
    kept = 0
    older: list[Path] = []
    for _, _, path in dated:
        if kept >= keep:
            older.append(path)
        elif complete(path):
            kept += 1
    return older


def _touches(path: Path, forbidden: tuple[Path, ...]) -> bool:
    """Overlaps a forbidden root; a path that cannot be checked counts as overlapping."""
    try:
        return any(paths_overlap(path, root) for root in forbidden)
    except OSError:
        return True


def _has_more_than_evidence(path: Path) -> bool:
    return any(child.name != EVIDENCE_FOLDER for child in _children(path))


def plan_backup_cycles(backups_dir: Path, *, keep: int = KEEP, protect: Path | None = None,
                       never: Iterable[Path] = ()) -> list[Path]:
    """The backups `prune_backup_cycles` would delete; reads only."""
    top = _children(backups_dir)
    older = (_older_than_kept(_children(backups_dir / "verified-snapshots"), TRIAL_ID,
                              _snapshot_complete, keep)
             + _older_than_kept(top, PORTABLE_BACKUP, _dated_complete, keep)
             + _older_than_kept(top, ORIGINAL_BACKUP, _dated_complete, keep))
    forbidden = tuple(never)
    return [path for path in older
            if not _same(path, protect) and not _touches(path, forbidden)
            and (path.name not in EVIDENCE_TEST_TRIALS or _has_more_than_evidence(path))]


def _delete_all(path: Path) -> list[tuple[Path, str]]:
    """Remove a backup folder, or for a test-evidence trial everything but its evidence."""
    if path.name not in EVIDENCE_TEST_TRIALS:
        targets = [path]
    else:
        targets = [c for c in _children(path) if c.name != EVIDENCE_FOLDER]
    failed: list[tuple[Path, str]] = []
    for target in targets:
        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        except OSError as exc:
            failed.append((target, f"{type(exc).__name__}: {exc}"))
    return failed


def prune_backup_cycles(backups_dir: Path, *, keep: int = KEEP, protect: Path | None = None,
                        never: Iterable[Path] = ()) -> PruneResult:
    """Delete what `plan_backup_cycles` selects; an error is recorded and the rest continue."""
    removed: list[Path] = []
    failed: list[tuple[Path, str]] = []
    for path in plan_backup_cycles(backups_dir, keep=keep, protect=protect, never=never):
        errors = _delete_all(path)
        failed.extend(errors)
        if not errors:
            removed.append(path)
    return PruneResult(tuple(removed), tuple(failed))
