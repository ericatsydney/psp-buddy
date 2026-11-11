import os
import shutil
import uuid
from pathlib import Path

import pytest

from psp_buddy import retention


def test_a_path_check_error_skips_that_folder_and_never_raises(tmp_path, monkeypatch):
    for day in range(10, 18):
        folder = tmp_path / f'portable-memstick-202611{day}T000000Z'
        folder.mkdir()
        (folder / 'manifest.json').write_text('[{"verified": true}]', encoding='utf-8')

    def broken(first, second):
        raise OSError('reparse point')

    monkeypatch.setattr(retention, 'paths_overlap', broken)
    assert retention.plan_backup_cycles(tmp_path, never=(tmp_path / 'runtime',)) == []

# Backup cycles (user, 10 Nov): the newest 5 complete backups of each of three kinds.

GOOD = '[{"dir": "SAVEDATA", "path": "a", "sha256": "0", "verified": true}]'
BOM = "﻿" + GOOD
EVIDENCE_TRIAL = "20261015T120025749948Z-0289b926396c4c3683c13be0b1f44c51"


def _snapshot(backups: Path, day: int, *, complete: bool = True) -> Path:
    path = backups / "verified-snapshots" / f"202611{day:02d}T120000000000Z-{uuid.uuid4().hex}"
    for part in ("snapshot", "working"):
        (path / part).mkdir(parents=True)
    if complete:
        (path / "manifest.json").write_text("{}")
    else:
        (path / "INCOMPLETE").write_text("x")
    return path


def _dated(backups: Path, name: str, manifest: str | None = BOM) -> Path:
    path = backups / name
    (path / "SAVEDATA").mkdir(parents=True)
    if manifest is not None:
        (path / "manifest.json").write_text(manifest, encoding="utf-8")
    return path


def _portable(backups: Path, day: int, manifest: str | None = BOM) -> Path:
    return _dated(backups, f"portable-memstick-202611{day:02d}T120000Z", manifest)


def _original(backups: Path, day: int, label: str = "s2", manifest: str | None = BOM) -> Path:
    return _dated(backups, f"{label}-original-202611{day:02d}T120000Z", manifest)


def test_cycles_keep_newest_five_of_each_kind(tmp_path: Path) -> None:
    snapshots = [_snapshot(tmp_path, d) for d in range(1, 8)]
    portable = [_portable(tmp_path, d) for d in range(1, 8)]
    original = [_original(tmp_path, d) for d in range(1, 8)]
    assert set(retention.plan_backup_cycles(tmp_path)) == set(
        snapshots[:2] + portable[:2] + original[:2])


def test_cycles_plan_deletes_nothing(tmp_path: Path) -> None:
    portable = [_portable(tmp_path, d) for d in range(1, 8)]
    retention.plan_backup_cycles(tmp_path)
    assert all(p.is_dir() for p in portable)


def test_cycles_kinds_are_counted_separately(tmp_path: Path) -> None:
    _original(tmp_path, 1)
    portable = [_portable(tmp_path, d) for d in range(2, 7)]
    assert retention.plan_backup_cycles(tmp_path) == []
    assert all(p.is_dir() for p in portable)


def test_cycles_incomplete_does_not_count_and_older_goes(tmp_path: Path) -> None:
    oldest = _snapshot(tmp_path, 1)
    old_broken = _snapshot(tmp_path, 2, complete=False)
    kept = [_snapshot(tmp_path, d) for d in range(3, 7)]
    fifth = _snapshot(tmp_path, 7)
    new_broken = _snapshot(tmp_path, 8, complete=False)
    assert set(retention.plan_backup_cycles(tmp_path)) == {oldest, old_broken}
    assert all(p.is_dir() for p in (*kept, fifth, new_broken))


@pytest.mark.parametrize("manifest", [
    None, "", "not json", "[]", "{}", "[1]",
    '[{"verified": true}, {"verified": false}]',
])
def test_cycles_bad_manifest_does_not_count(tmp_path: Path, manifest: str | None) -> None:
    good = [_portable(tmp_path, d) for d in range(1, 6)]
    _portable(tmp_path, 6, manifest)
    assert retention.plan_backup_cycles(tmp_path) == []
    assert all(p.is_dir() for p in good)


def test_cycles_manifest_without_bom_counts(tmp_path: Path) -> None:
    oldest = _portable(tmp_path, 1, GOOD)
    for day in range(2, 7):
        _portable(tmp_path, day, GOOD)
    assert retention.plan_backup_cycles(tmp_path) == [oldest]


def test_cycles_timestamp_order_across_labels_and_name_forms(tmp_path: Path) -> None:
    hexed = _dated(tmp_path, f"zzz-original-20261101T120000Z-{uuid.uuid4().hex}")
    for day, label in zip(range(2, 6), "abcd", strict=True):
        _original(tmp_path, day, label)
    newer_hex = _dated(tmp_path, f"a-original-20261106T120000Z-{uuid.uuid4().hex}")
    assert retention.plan_backup_cycles(tmp_path) == [hexed]
    assert newer_hex.is_dir()


def test_cycles_ignore_every_other_name(tmp_path: Path) -> None:
    names = ("20261010-130740", "20261104-061103-before-copy-state4", "portable-ppsspp-v1.20.4",
             "act2-original-config-20261018T073635Z-b4f8ecd5a4ba49a59396daf9fb74c571",
             "portable-memstick-x", "x-original-tomorrow")
    others = [_dated(tmp_path, name) for name in names]
    loose = tmp_path / "verified-snapshots" / "not-a-trial"
    loose.mkdir(parents=True)
    assert retention.plan_backup_cycles(tmp_path, keep=0) == []
    assert all(p.is_dir() for p in (*others, loose))


def test_cycles_keep_zero_selects_all_of_a_kind(tmp_path: Path) -> None:
    portable = [_portable(tmp_path, d) for d in range(1, 3)]
    assert set(retention.plan_backup_cycles(tmp_path, keep=0)) == set(portable)


def test_cycles_protect_and_never_are_not_selected(tmp_path: Path) -> None:
    snapshots = [_snapshot(tmp_path, d) for d in range(1, 8)]
    portable = [_portable(tmp_path, d) for d in range(1, 8)]
    selected = retention.plan_backup_cycles(tmp_path, protect=snapshots[0],
                                            never=(portable[1] / "SAVEDATA",))
    assert set(selected) == {snapshots[1], portable[0]}


def test_cycles_links_are_skipped(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / "manifest.json").write_text(BOM, encoding="utf-8")
    link = tmp_path / "portable-memstick-20261101T120000Z"
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks not permitted")
    assert retention.plan_backup_cycles(tmp_path, keep=0) == []


def test_cycles_missing_folder_is_harmless(tmp_path: Path) -> None:
    assert retention.plan_backup_cycles(tmp_path / "none") == []


def test_prune_cycles_deletes_the_selection(tmp_path: Path) -> None:
    snapshots = [_snapshot(tmp_path, d) for d in range(1, 8)]
    portable = [_portable(tmp_path, d) for d in range(1, 8)]
    other = _dated(tmp_path, "20261010-130740")
    result = retention.prune_backup_cycles(tmp_path)
    assert set(result.removed) == set(snapshots[:2] + portable[:2])
    assert result.failed == ()
    assert not any(p.exists() for p in snapshots[:2] + portable[:2])
    assert all((p / "working").is_dir() for p in snapshots[2:])
    assert all(p.is_dir() for p in (*portable[2:], other))


def test_prune_cycles_keeps_user_evidence_of_test_trials(tmp_path: Path) -> None:
    trial = tmp_path / "verified-snapshots" / EVIDENCE_TRIAL
    (trial / "snapshot").mkdir(parents=True)
    (trial / "user-evidence").mkdir()
    (trial / "user-evidence" / "dump-08800000.bin").write_bytes(b"ram")
    (trial / "manifest.json").write_text("{}")
    plain = _snapshot(tmp_path, 1)
    (plain / "user-evidence").mkdir()
    result = retention.prune_backup_cycles(tmp_path, keep=0)
    assert set(result.removed) == {trial, plain}
    assert [p.name for p in trial.iterdir()] == ["user-evidence"]
    assert (trial / "user-evidence" / "dump-08800000.bin").read_bytes() == b"ram"
    assert not plain.exists()
    # Already reduced to its evidence: nothing more to do on later launches.
    assert retention.plan_backup_cycles(tmp_path, keep=0) == []


def test_prune_cycles_error_recorded_and_rest_continue(tmp_path: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    portable = [_portable(tmp_path, d) for d in range(1, 4)]
    real = shutil.rmtree

    def flaky(path: Path, *args: object, **kwargs: object) -> None:
        if Path(path) == portable[0]:
            raise PermissionError("locked")
        real(path)

    monkeypatch.setattr(retention.shutil, "rmtree", flaky)
    result = retention.prune_backup_cycles(tmp_path, keep=0)
    assert [p for p, _ in result.failed] == [portable[0]]
    assert "locked" in result.failed[0][1]
    assert set(result.removed) == set(portable[1:])


def test_prune_cycles_evidence_trial_error_is_recorded(tmp_path: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    trial = tmp_path / "verified-snapshots" / EVIDENCE_TRIAL
    (trial / "snapshot").mkdir(parents=True)
    (trial / "user-evidence").mkdir()

    def locked(path: Path, *args: object, **kwargs: object) -> None:
        raise PermissionError("locked")

    monkeypatch.setattr(retention.shutil, "rmtree", locked)
    result = retention.prune_backup_cycles(tmp_path, keep=0)
    assert result.removed == ()
    assert [p for p, _ in result.failed] == [trial / "snapshot"]
