"""Delete old trial copies that nothing reads again (user, 7 Nov: drive C: was full).

Only two kinds of folder are ever deleted: archived runtimes next to the active runtime and the
writable `working` copy inside an old trial. Verified snapshots, manifests and every other backup
are never touched. Best effort: a folder that cannot be deleted is recorded and skipped.
"""

import os
import re
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path

KEEP = 5
RUNTIME_MARKER = ".psp-buddy-runtime"
TRIAL_ID = re.compile(r"\d{8}T\d{12}Z-[0-9a-f]{32}")


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


def _delete(paths: list[Path]) -> PruneResult:
    removed: list[Path] = []
    failed: list[tuple[Path, str]] = []
    for path in paths:
        try:
            shutil.rmtree(path)
        except OSError as exc:
            failed.append((path, f"{type(exc).__name__}: {exc}"))
        else:
            removed.append(path)
    return PruneResult(tuple(removed), tuple(failed))


def _same(a: Path, b: Path | None) -> bool:
    return b is not None and os.path.normcase(a.absolute()) == os.path.normcase(b.absolute())


def prune_runtime_archives(runtime_root: Path, *, keep: int = KEEP,
                           protect: Path | None = None) -> PruneResult:
    """Delete owned `<runtime>-archive-<hex>` folders beyond the newest `keep` (by marker mtime).
    `protect` counts toward `keep` and is never deleted."""
    parent = runtime_root.parent
    pattern = re.compile(re.escape(runtime_root.name) + r"-archive-[0-9a-f]{32}")
    if not parent.is_dir():
        return PruneResult()
    owned: list[tuple[int, Path]] = []
    for path in parent.iterdir():
        if not pattern.fullmatch(path.name) or not _plain_dir(path):
            continue
        marker = path / RUNTIME_MARKER
        try:
            if not marker.is_file() or marker.is_symlink():
                continue
            owned.append((marker.stat().st_mtime_ns, path))
        except OSError:
            continue
    owned.sort(reverse=True)
    return _delete([path for _, path in owned[keep:] if not _same(path, protect)])


def prune_working_copies(backup_root: Path, *, keep: int = KEEP,
                         protect: Path | None = None) -> PruneResult:
    """Delete the `working` folder of trials beyond the newest `keep` (trial ids sort by time)."""
    if not backup_root.is_dir():
        return PruneResult()
    trials = sorted((p for p in backup_root.iterdir()
                     if TRIAL_ID.fullmatch(p.name) and _plain_dir(p)),
                    key=lambda p: p.name, reverse=True)
    old = [t / "working" for t in trials[keep:] if not _same(t, protect)]
    return _delete([w for w in old if _plain_dir(w)])
