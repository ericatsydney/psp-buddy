"""All backup data is synthetic; no PPSSPP process or debugger is contacted."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from psp_buddy.backup import BackupGate, ClosedProcessGuard, writable_trial_root
from psp_buddy.config import RunConfig


class Closed:
    def assert_non_writing(self, config: RunConfig) -> None:
        pass


@pytest.fixture
def configured(config_values: dict[str, object]) -> RunConfig:
    config = RunConfig.from_dict(config_values)
    for root in config.save_roots:
        (root / "nested").mkdir()
        (root / "empty").mkdir()
        for name in ("STAGE.BIN", "SYSTEM.BIN", "metadata", "thumb.png", "slot.ppst", "undo"):
            (root / "nested" / name).write_bytes(b"synthetic-" + name.encode())
    return config


def test_complete_fresh_backups(configured: RunConfig) -> None:
    gate = BackupGate(guard=Closed())
    first = gate.prepare_trial(configured)
    second = gate.prepare_trial(configured)
    assert first.trial_id != second.trial_id
    assert len(first.files) == 24
    assert first.manifest_path.is_file()
    manifest = json.loads(first.manifest_path.read_text())
    assert len(manifest["inventories"]) == 4
    assert all(len(f.sha256) == 64 for f in first.files)
    assert all(f.copied.read_bytes() == f.source.read_bytes() for f in first.files)
    working = writable_trial_root(first)
    assert working != first.snapshot_root
    target = working / "0-original_savedata" / "nested" / "STAGE.BIN"
    target.write_bytes(b"trial change")
    assert first.files[0].copied.read_bytes() == first.files[0].source.read_bytes()
    assert (first.snapshot_root / "0-original_savedata" / "empty").is_dir()
    assert first.snapshot_root.is_dir()


@pytest.mark.parametrize("fault", ["copy", "corruption", "addition", "removal", "mutation"])
def test_failure_prevents_connection_and_manifest(configured: RunConfig, fault: str) -> None:
    calls = 0
    connection_attempts = 0

    def copy(source: Path, target: Path) -> object:
        nonlocal calls
        calls += 1
        if fault == "copy":
            raise OSError("injected disk error")
        result = shutil.copy2(source, target)
        if calls == 1:
            if fault == "corruption":
                target.write_bytes(b"corrupted")
            elif fault == "addition":
                (configured.original_savedata / "new.bin").write_bytes(b"added")
            elif fault == "removal":
                (configured.original_states / "nested" / "undo").unlink()
            elif fault == "mutation":
                source.write_bytes(b"changed")
        return result

    gate = BackupGate(guard=Closed(), copy_file=copy)
    with pytest.raises((ValueError, OSError)):
        gate.prepare_trial(configured)
        connection_attempts += 1
    assert connection_attempts == 0
    assert not list(configured.backup_root.rglob("manifest.json"))
    assert len(list(configured.backup_root.iterdir())) == 1  # failed evidence preserved


def test_missing_root_blocks_before_destination(configured: RunConfig) -> None:
    shutil.rmtree(configured.portable_states)
    with pytest.raises(ValueError, match="missing"):
        BackupGate(guard=Closed()).prepare_trial(configured)
    assert not configured.backup_root.exists()


def test_hash_exception_blocks(configured: RunConfig) -> None:
    def fail_hash(path: Path) -> str:
        raise OSError("hash read failure")

    with pytest.raises(OSError, match="hash read"):
        BackupGate(guard=Closed(), hash_file=fail_hash).prepare_trial(configured)
    assert not list(configured.backup_root.rglob("manifest.json"))


def test_boolean_is_not_nonwriting_proof(configured: RunConfig) -> None:
    class BooleanGuard:
        def assert_non_writing(self, config: RunConfig) -> bool:
            return True

    with pytest.raises(ValueError, match="boolean"):
        BackupGate(guard=BooleanGuard()).prepare_trial(configured)


def test_guard_rechecked_during_copy(configured: RunConfig) -> None:
    class StartsWriting:
        calls = 0

        def assert_non_writing(self, config: RunConfig) -> None:
            self.calls += 1
            if self.calls > 2:
                raise ValueError("emulator writing")

    with pytest.raises(ValueError, match="writing"):
        BackupGate(guard=StartsWriting()).prepare_trial(configured)
    assert not list(configured.backup_root.rglob("manifest.json"))


def test_receipt_current_single_use_provenance(configured: RunConfig) -> None:
    gate = BackupGate(guard=Closed())
    receipt = gate.prepare_trial(configured)
    with pytest.raises(ValueError, match="unknown"):
        BackupGate(guard=Closed()).validate_receipt(configured, receipt)
    gate.validate_receipt(configured, receipt)
    with pytest.raises(ValueError, match="consumed"):
        gate.validate_receipt(configured, receipt)


@pytest.mark.parametrize("area", ["source", "snapshot", "working", "manifest"])
def test_modified_provenance_blocks_connection(configured: RunConfig, area: str) -> None:
    gate = BackupGate(guard=Closed())
    receipt = gate.prepare_trial(configured)
    if area == "manifest":
        receipt.manifest_path.write_text('{}')
    else:
        target = (receipt.files[0].source if area == "source" else receipt.files[0].copied
                  if area == "snapshot" else writable_trial_root(receipt)
                  / "0-original_savedata" / "nested" / "STAGE.BIN")
        target.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="provenance|hash"):
        gate.validate_receipt(configured, receipt)


def test_reparse_ancestor_blocks(configured: RunConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    real_lstat = Path.lstat

    def fake_lstat(path: Path) -> Any:
        info = real_lstat(path)
        if path == configured.original_savedata:
            class Reparse:
                st_mode = info.st_mode
                st_file_attributes = 1024
            return Reparse()
        return info

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(ValueError, match="reparse"):
        BackupGate(guard=Closed()).prepare_trial(configured)


def test_process_enumeration_failure_denies(configured: RunConfig,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise OSError("unavailable")

    monkeypatch.setattr("psp_buddy.backup.subprocess.run", fail)
    with pytest.raises(ValueError, match="unavailable"):
        ClosedProcessGuard().assert_non_writing(configured)


def test_running_process_denies(configured: RunConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    class Result:
        stdout = '[{"Name":"PPSSPPWindows64.exe","ExecutablePath":null}]'

    def process(*args: object, **kwargs: object) -> Result:
        return Result()

    monkeypatch.setattr("psp_buddy.backup.subprocess.run", process)
    with pytest.raises(ValueError, match="closed"):
        ClosedProcessGuard().assert_non_writing(configured)


def test_stale_receipt_denies(configured: RunConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import UTC, datetime, timedelta

    from psp_buddy import backup

    gate = BackupGate(guard=Closed())
    receipt = gate.prepare_trial(configured)
    future = datetime.now(UTC) + timedelta(seconds=61)

    class Clock:
        @staticmethod
        def now(tz: object) -> datetime:
            return future

        fromisoformat = datetime.fromisoformat

    monkeypatch.setattr(backup, 'datetime', Clock)
    with pytest.raises(ValueError, match='stale'):
        gate.validate_receipt(configured, receipt)


@pytest.mark.parametrize('value', [0, -1, float('inf'), float('nan'), True])
def test_freshness_requires_positive_finite(value: float) -> None:
    with pytest.raises(ValueError, match='freshness'):
        BackupGate(guard=Closed(), freshness_seconds=value)


def test_forged_receipt_denies(configured: RunConfig) -> None:
    from dataclasses import replace
    gate = BackupGate(guard=Closed())
    receipt = gate.prepare_trial(configured)
    forged = replace(receipt, trial_id=receipt.trial_id + '-forged')
    with pytest.raises(ValueError, match='unknown'):
        gate.validate_receipt(configured, forged)


def test_manifest_inventory_cannot_reauthorize_changes(configured: RunConfig) -> None:
    from psp_buddy.backup import inventory
    gate = BackupGate(guard=Closed())
    receipt = gate.prepare_trial(configured)
    (configured.original_savedata / 'new').mkdir()
    manifest = json.loads(receipt.manifest_path.read_text())
    manifest['inventories'][0] = inventory(configured.original_savedata)
    receipt.manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='provenance'):
        gate.validate_receipt(configured, receipt)


def test_hardlink_denied(configured: RunConfig) -> None:
    import os
    source = configured.original_savedata / 'nested' / 'STAGE.BIN'
    os.link(source, configured.original_savedata / 'alias')
    with pytest.raises(ValueError, match='hard link'):
        BackupGate(guard=Closed()).prepare_trial(configured)


def test_overlap_rechecked(configured: RunConfig) -> None:
    object.__setattr__(configured, 'backup_root', configured.original_savedata / 'backup')
    with pytest.raises(ValueError, match='overlap'):
        BackupGate(guard=Closed()).prepare_trial(configured)


def test_freshness_starts_after_complete_verification(configured: RunConfig,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import UTC, datetime, timedelta

    from psp_buddy import backup

    current = datetime(2026, 10, 10, tzinfo=UTC)

    class Clock:
        @staticmethod
        def now(tz: object) -> datetime:
            return current

        fromisoformat = datetime.fromisoformat

    def slow_hash(path: Path) -> str:
        nonlocal current
        current += timedelta(seconds=1)
        return backup.sha256(path)

    monkeypatch.setattr(backup, 'datetime', Clock)
    gate = BackupGate(guard=Closed(), hash_file=slow_hash)
    receipt = gate.prepare_trial(configured)
    assert datetime.fromisoformat(receipt.created_at) == current


def test_receipt_expiring_during_validation_denies(configured: RunConfig,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import UTC, datetime, timedelta

    from psp_buddy import backup

    current = datetime(2026, 10, 10, tzinfo=UTC)
    validation = False

    class Clock:
        @staticmethod
        def now(tz: object) -> datetime:
            return current

        fromisoformat = datetime.fromisoformat

    def slow_hash(path: Path) -> str:
        nonlocal current
        if validation:
            current += timedelta(seconds=1)
        return backup.sha256(path)

    monkeypatch.setattr(backup, 'datetime', Clock)
    gate = BackupGate(guard=Closed(), hash_file=slow_hash, freshness_seconds=60)
    receipt = gate.prepare_trial(configured)
    validation = True
    with pytest.raises(ValueError, match='stale'):
        gate.validate_receipt(configured, receipt)
