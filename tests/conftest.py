from pathlib import Path

import pytest


@pytest.fixture
def config_values(tmp_path: Path) -> dict[str, object]:
    roots = {}
    for name in (
        "original_savedata", "original_states", "portable_savedata", "portable_states"
    ):
        root = tmp_path / name
        root.mkdir()
        roots[name] = str(root)
    return {
        **roots,
        "backup_root": str(tmp_path / "backups"),
        "debugger_endpoint": "ws://127.0.0.1:8080/debugger",
        "slot": 2,
        "max_retries": 3,
        "emulator_path": str(tmp_path / "PPSSPPWindows64.exe"),
        "iso_path": str(tmp_path / "game.iso"),
        "profile_path": str(tmp_path / "profile.json"),
        "game_id": "ULJS00460",
        "patch_id": "english-v0.8",
        "emulator_version": "1.20.4",
    }
