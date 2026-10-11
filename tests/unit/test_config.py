import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("slot", [0, 6, True, 2.5])
def test_invalid_slot(config_values: dict[str, object], slot: object) -> None:
    from psp_buddy.config import RunConfig

    with pytest.raises(ValueError, match="slot"):
        RunConfig.from_dict({**config_values, "slot": slot})


@pytest.mark.parametrize("retries", [-1, 4, True, 1.5])
def test_retry_budget_cannot_exceed_user_limit(
    config_values: dict[str, object], retries: object
) -> None:
    from psp_buddy.config import RunConfig

    with pytest.raises(ValueError, match="retries"):
        RunConfig.from_dict({**config_values, "max_retries": retries})


@pytest.mark.parametrize("endpoint", [
    "ws://example.com:8080/debugger", "http://127.0.0.1:8080", "ws://0.0.0.0:8080",
    "ws://user:secret@localhost:8080", "ws://localhost:99999",
])
def test_endpoint_must_be_local_websocket(
    config_values: dict[str, object], endpoint: str
) -> None:
    from psp_buddy.config import RunConfig

    with pytest.raises(ValueError, match="endpoint"):
        RunConfig.from_dict({**config_values, "debugger_endpoint": endpoint})


def test_missing_save_root(config_values: dict[str, object], tmp_path: Path) -> None:
    from psp_buddy.config import RunConfig

    with pytest.raises(ValueError, match="save root"):
        RunConfig.from_dict({**config_values, "original_savedata": str(tmp_path / "missing")})


@pytest.mark.parametrize("relation", ["equal", "inside", "outside"])
def test_overlapping_backup_root(config_values: dict[str, object], relation: str) -> None:
    from psp_buddy.config import RunConfig

    source = Path(str(config_values["original_savedata"]))
    backup = {"equal": source, "inside": source / "backup", "outside": source.parent}[relation]
    with pytest.raises(ValueError, match="overlap"):
        RunConfig.from_dict({**config_values, "backup_root": str(backup)})


def test_valid_config_preserves_explicit_limits(config_values: dict[str, object]) -> None:
    from psp_buddy.config import RunConfig

    config = RunConfig.from_dict({**config_values, "max_retries": 0})
    assert config.slot == 2
    assert config.max_retries == 0
    assert config.original_savedata.is_dir()


def test_unknown_keys_rejected(config_values: dict[str, object]) -> None:
    from psp_buddy.config import RunConfig

    with pytest.raises(ValueError, match="unknown"):
        RunConfig.from_dict({**config_values, "max_retry": 99})


def test_game_image_path_is_required(config_values: dict[str, object]) -> None:
    from psp_buddy.config import RunConfig

    without_image = {key: value for key, value in config_values.items() if key != "iso_path"}
    with pytest.raises(ValueError, match="iso_path"):
        RunConfig.from_dict(without_image)


@pytest.mark.parametrize("nested", [False, True])
def test_save_source_roots_cannot_overlap(
    config_values: dict[str, object], nested: bool
) -> None:
    from psp_buddy.config import RunConfig

    root = Path(str(config_values["original_savedata"]))
    portable = root / "nested" if nested else root
    portable.mkdir(exist_ok=True)
    with pytest.raises(ValueError, match="overlap"):
        RunConfig.from_dict({**config_values, "portable_savedata": str(portable)})


def test_ipv6_loopback_endpoint_is_accepted(config_values: dict[str, object]) -> None:
    from psp_buddy.config import RunConfig

    endpoint = "ws://[::1]:8080/debugger"
    config = RunConfig.from_dict({**config_values, "debugger_endpoint": endpoint})
    assert config.debugger_endpoint == endpoint


def test_cli_lists_commands_and_refuses_live_use() -> None:
    help_result = subprocess.run(
        [sys.executable, "-m", "psp_buddy", "--help"], capture_output=True, text=True
    )
    assert help_result.returncode == 0
    assert all(command in help_result.stdout for command in ("inspect", "validate", "run"))
    run_result = subprocess.run(
        [sys.executable, "-m", "psp_buddy", "run"], capture_output=True, text=True
    )
    assert run_result.returncode != 0
    assert "disabled" in run_result.stderr
