"""Machine-local configuration. Validation grants no live-trial authorization."""

import ipaddress
from collections.abc import Mapping
from dataclasses import dataclass, fields
from pathlib import Path
from urllib.parse import urlsplit


def _integer(value: object, name: str, lower: int, upper: int) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"{name} must be an integer from {lower} to {upper}")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value


def paths_overlap(first: Path, second: Path) -> bool:
    """Check lexical and resolved ancestry with Windows case-insensitive semantics."""
    for a, b in ((first.absolute(), second.absolute()), (first.resolve(), second.resolve())):
        a_parts = tuple(part.casefold() for part in a.parts)
        b_parts = tuple(part.casefold() for part in b.parts)
        if a_parts == b_parts[:len(a_parts)] or b_parts == a_parts[:len(b_parts)]:
            return True
    return False


@dataclass(frozen=True)
class RunConfig:
    original_savedata: Path
    original_states: Path
    portable_savedata: Path
    portable_states: Path
    backup_root: Path
    debugger_endpoint: str
    emulator_path: Path
    iso_path: Path
    profile_path: Path
    game_id: str
    patch_id: str
    emulator_version: str
    slot: int = 2
    max_retries: int = 3
    timeout_seconds: int = 10
    max_actions: int = 1000
    max_transitions: int = 30

    def __post_init__(self) -> None:
        _integer(self.slot, "slot", 1, 5)
        _integer(self.max_retries, "max_retries", 0, 3)
        for name, upper in (("timeout_seconds", 300), ("max_actions", 100000),
                            ("max_transitions", 1000)):
            _integer(getattr(self, name), name, 1, upper)
        for name in ("game_id", "patch_id", "emulator_version"):
            _text(getattr(self, name), name)
        try:
            endpoint = urlsplit(self.debugger_endpoint)
            host = endpoint.hostname
            local = host == "localhost"
            if host and not local:
                local = ipaddress.ip_address(host).is_loopback
            if (endpoint.scheme not in ("ws", "wss") or not local or endpoint.username
                    or endpoint.password or endpoint.fragment or endpoint.port is None):
                raise ValueError("unsafe endpoint")
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("debugger endpoint must be a loopback WebSocket with a port") from exc
        roots = self.save_roots
        for root in roots:
            if not isinstance(root, Path) or not root.is_dir():
                raise ValueError(f"missing save root: {root}")
            if paths_overlap(root, self.backup_root):
                raise ValueError("backup/source roots overlap")
        for index, root in enumerate(roots):
            if any(paths_overlap(root, other) for other in roots[index + 1:]):
                raise ValueError("save roots overlap")

    @property
    def save_roots(self) -> tuple[Path, ...]:
        return (self.original_savedata, self.original_states,
                self.portable_savedata, self.portable_states)

    @classmethod
    def from_dict(cls, values: Mapping[str, object]) -> "RunConfig":
        allowed = {field.name for field in fields(cls)}
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"unknown configuration fields: {sorted(unknown)}")
        required = ("original_savedata", "original_states", "portable_savedata",
                    "portable_states", "backup_root", "debugger_endpoint", "emulator_path",
                    "iso_path", "profile_path", "game_id", "patch_id", "emulator_version")
        missing = set(required) - set(values)
        if missing:
            raise ValueError(f"missing configuration fields: {sorted(missing)}")
        return cls(
            original_savedata=Path(_text(values["original_savedata"], "original_savedata")),
            original_states=Path(_text(values["original_states"], "original_states")),
            portable_savedata=Path(_text(values["portable_savedata"], "portable_savedata")),
            portable_states=Path(_text(values["portable_states"], "portable_states")),
            backup_root=Path(_text(values["backup_root"], "backup_root")),
            debugger_endpoint=_text(values["debugger_endpoint"], "debugger_endpoint"),
            emulator_path=Path(_text(values["emulator_path"], "emulator_path")),
            iso_path=Path(_text(values["iso_path"], "iso_path")),
            profile_path=Path(_text(values["profile_path"], "profile_path")),
            game_id=_text(values["game_id"], "game_id"),
            patch_id=_text(values["patch_id"], "patch_id"),
            emulator_version=_text(values["emulator_version"], "emulator_version"),
            slot=_integer(values.get("slot", 2), "slot", 1, 5),
            max_retries=_integer(values.get("max_retries", 3), "max_retries", 0, 3),
            timeout_seconds=_integer(values.get("timeout_seconds", 10), "timeout_seconds", 1, 300),
            max_actions=_integer(values.get("max_actions", 1000), "max_actions", 1, 100000),
            max_transitions=_integer(values.get("max_transitions", 30), "max_transitions", 1, 1000),
        )
