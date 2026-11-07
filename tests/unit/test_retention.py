import os
import shutil
import uuid
from pathlib import Path

import pytest

from psp_buddy import retention

MARKER = "psp-buddy-runtime-v1\n"


def _archive(parent: Path, index: int, *, marker: bool = True) -> Path:
    path = parent / f"runtime-archive-{uuid.uuid4().hex}"
    (path / "app").mkdir(parents=True)
    (path / "app" / "big.bin").write_bytes(b"x" * 10)
    if marker:
        stamp = path / ".psp-buddy-runtime"
        stamp.write_text(MARKER)
        os.utime(stamp, ns=(index * 10**9, index * 10**9))
    return path


def _trial(root: Path, index: int) -> Path:
    path = root / f"2026110{index}T120000000000Z-{uuid.uuid4().hex}"
    for part in ("snapshot", "working"):
        (path / part).mkdir(parents=True)
        (path / part / "save.bin").write_bytes(b"s")
    (path / "manifest.json").write_text("{}")
    return path


def test_runtime_archives_keep_newest_and_protected(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    archives = [_archive(tmp_path, i) for i in range(1, 9)]
    result = retention.prune_runtime_archives(runtime, keep=5, protect=archives[0])
    left = {p for p in tmp_path.iterdir()}
    assert left == set(archives[3:]) | {archives[0]}
    assert set(result.removed) == set(archives[1:3])
    assert result.failed == ()


def test_runtime_archives_ignore_unowned(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    unmarked = _archive(tmp_path, 1, marker=False)
    other = tmp_path / f"other-archive-{uuid.uuid4().hex}"
    other.mkdir()
    short = tmp_path / "runtime-archive-abc"
    short.mkdir()
    loose = tmp_path / f"runtime-archive-{uuid.uuid4().hex}"
    loose.write_text("file")
    result = retention.prune_runtime_archives(runtime, keep=0)
    assert result.removed == ()
    assert all(p.exists() for p in (unmarked, other, short, loose))


def test_runtime_archive_link_skipped(tmp_path: Path) -> None:
    target = _archive(tmp_path / "elsewhere", 1)
    link = tmp_path / f"runtime-archive-{uuid.uuid4().hex}"
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks not permitted")
    result = retention.prune_runtime_archives(tmp_path / "runtime", keep=0)
    assert result.removed == ()
    assert (target / "app" / "big.bin").exists()


def test_working_copies_keep_newest_and_protected(tmp_path: Path) -> None:
    trials = [_trial(tmp_path, i) for i in range(1, 9)]
    (tmp_path / "portable-memstick-x" / "working").mkdir(parents=True)
    result = retention.prune_working_copies(tmp_path, keep=5, protect=trials[0])
    for trial in trials:
        assert (trial / "snapshot" / "save.bin").exists()
        assert (trial / "manifest.json").exists()
    kept = {t for t in trials if (t / "working").exists()}
    assert kept == set(trials[3:]) | {trials[0]}
    assert set(result.removed) == {t / "working" for t in trials[1:3]}
    assert (tmp_path / "portable-memstick-x" / "working").exists()


def test_working_copies_skip_trials_without_working(tmp_path: Path) -> None:
    trials = [_trial(tmp_path, i) for i in range(1, 8)]
    shutil.rmtree(trials[0] / "working")
    result = retention.prune_working_copies(tmp_path, keep=5)
    assert set(result.removed) == {trials[1] / "working"}


def test_error_recorded_and_rest_continue(tmp_path: Path,
                                          monkeypatch: pytest.MonkeyPatch) -> None:
    trials = [_trial(tmp_path, i) for i in range(1, 9)]
    real = shutil.rmtree

    def flaky(path: Path, *args: object, **kwargs: object) -> None:
        if Path(path) == trials[0] / "working":
            raise PermissionError("locked")
        real(path)

    monkeypatch.setattr(retention.shutil, "rmtree", flaky)
    result = retention.prune_working_copies(tmp_path, keep=5)
    assert [p for p, _ in result.failed] == [trials[0] / "working"]
    assert "locked" in result.failed[0][1]
    assert set(result.removed) == {t / "working" for t in trials[1:3]}


def test_missing_roots_are_harmless(tmp_path: Path) -> None:
    assert retention.prune_working_copies(tmp_path / "none", keep=5).removed == ()
    assert retention.prune_runtime_archives(tmp_path / "none" / "rt", keep=5).removed == ()
