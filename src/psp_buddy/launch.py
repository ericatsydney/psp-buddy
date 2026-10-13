"""Protected PPSSPP launch with isolated files and one-use connection provenance."""

import configparser
import json
import os
import re
import shutil
import subprocess
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

from .backup import BackupGate, Inventory, _safe_path, inventory, sha256, writable_trial_root
from .config import RunConfig, paths_overlap
from .models import BackupReceipt


class ConnectionNotReady(RuntimeError):
    """The owned process has not opened its debugger listener yet."""


class Process(Protocol):
    pid: int
    def poll(self) -> int | None: ...
    def terminate(self) -> None: ...
    def wait(self, timeout: float) -> int: ...


@dataclass(frozen=True)
class ProcessIdentity:
    executable: Path
    command_line: str
    created: str


class Inspector(Protocol):
    def process(self, pid: int) -> ProcessIdentity: ...
    def listeners(self, port: int) -> tuple[tuple[str, int], ...]: ...


class WindowsInspector:
    """Trusted Windows inventory; missing/ambiguous evidence fails closed."""

    def _query(self, script: str) -> object:
        if os.name != "nt":
            raise ValueError("Windows process inspection unavailable")
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                 "$ErrorActionPreference='Stop'; " + script],
                check=True, capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return json.loads(result.stdout)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            raise ValueError("process ownership inspection failed") from exc

    def process(self, pid: int) -> ProcessIdentity:
        row = self._query(
            f"Get-CimInstance Win32_Process -Filter 'ProcessId={pid}' | "
            "Select-Object ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Compress"
        )
        if not isinstance(row, dict) or not all(
            isinstance(row.get(key), str) and row[key]
            for key in ("ExecutablePath", "CommandLine", "CreationDate")
        ):
            raise ValueError("process identity unavailable")
        return ProcessIdentity(Path(row["ExecutablePath"]), row["CommandLine"],
                               row["CreationDate"])

    def listeners(self, port: int) -> tuple[tuple[str, int], ...]:
        rows = self._query(
            "ConvertTo-Json -Compress -InputObject @(Get-NetTCPConnection -State Listen | "
            f"Where-Object LocalPort -eq {port} | Select-Object LocalAddress,OwningProcess)"
        )
        if not isinstance(rows, list):
            raise ValueError("listener inventory unavailable")
        result = []
        for row in rows:
            if (not isinstance(row, dict) or not isinstance(row.get("LocalAddress"), str)
                    or type(row.get("OwningProcess")) is not int):
                raise ValueError("listener identity unavailable")
            result.append((row["LocalAddress"], row["OwningProcess"]))
        return tuple(result)


def _copy_tree(source: Path, destination: Path) -> Inventory:
    before = inventory(source)
    shutil.copytree(source, destination)
    if inventory(source) != before or inventory(destination) != before:
        raise ValueError("copy inventory or hash mismatch")
    return before


def _writable(root: Path) -> None:
    _safe_path(root)
    probe = root / (".write-probe-" + uuid.uuid4().hex)
    try:
        with probe.open("xb") as stream:
            stream.write(b"protected launch probe")
    except OSError as exc:
        raise ValueError("isolated directory is not writable") from exc
    finally:
        if probe.exists():
            probe.unlink()


@dataclass(frozen=True)
class PreparedLaunch:
    config: RunConfig
    receipt: BackupReceipt
    executable: Path
    memstick_root: Path
    arguments: tuple[str, ...]
    app_inventory: Inventory
    iso_digest: str
    system_root: Path
    system_inventory: Inventory
    mutable_sources: tuple[Path, ...] = ()
    preserved: tuple[tuple[Path, Inventory], ...] = ()


_SESSION_ISSUERS: dict[object, tuple[PreparedLaunch, Process, Inspector]] = {}


class LaunchSession:
    def __init__(self, prepared: PreparedLaunch, process: Process, inspector: Inspector,
                 *, _issuer: object | None = None) -> None:
        issued = _SESSION_ISSUERS.pop(_issuer, None)
        if issued is None or any(a is not b for a, b in zip(
                issued, (prepared, process, inspector), strict=True)):
            raise ValueError("launch session requires its launcher issuer")
        self._prepared = prepared
        self._process = process
        self._inspector = inspector
        self._claimed = False
        self._closed = False
        self.config = prepared.config
        self.receipt = prepared.receipt
        self.executable = prepared.executable
        self.memstick_root = prepared.memstick_root
        self.endpoint = self.config.debugger_endpoint
        self.pid = process.pid
        self.game_version = Path(prepared.arguments[3].split("=", 1)[1]).stem.split("_")[1]
        self._identity = inspector.process(self.pid)
        self.assert_bound()

    def assert_bound(self) -> None:
        if self._closed or self._process.poll() is not None:
            raise ValueError("owned emulator process is not running")
        identity = self._inspector.process(self.pid)
        expected_line = subprocess.list2cmdline(list(self._prepared.arguments))
        if (identity != self._identity or identity.executable.resolve() != self.executable.resolve()
                or identity.command_line != expected_line):
            raise ValueError("launched process identity or command line mismatch")
        _safe_path(self.memstick_root)
        if (self.executable.parent / "installed.txt").exists():
            raise ValueError("memory stick override appeared")

    def claim_connection(self) -> str:
        if self._claimed:
            raise ValueError("launch connection already claimed")
        self.assert_bound()
        port = urlsplit(self.endpoint).port
        assert port is not None
        listeners = self._inspector.listeners(port)
        if not listeners:
            raise ConnectionNotReady("owned debugger listener not ready")
        # v1.20.4 Common/Net/HTTPServer.cpp Listen binds INADDR_ANY/in6addr_any.
        # Our client endpoint and connected peer must still be loopback.
        if any(pid != self.pid or address not in ("127.0.0.1", "::1", "0.0.0.0", "::")
               for address, pid in listeners):
            raise ValueError("foreign or unsupported debugger listener")
        self._claimed = True
        return self.endpoint

    def verify_sources(self) -> None:
        for index, root in enumerate(self.receipt.source_roots):
            snapshot = self.receipt.snapshot_root / f"{index}-{root.name}"
            if root in self._prepared.mutable_sources:
                continue
            if inventory(root) != inventory(snapshot):
                raise ValueError("original save source hash changed")
        if (self._prepared.system_root not in self._prepared.mutable_sources
                and inventory(self._prepared.system_root) != self._prepared.system_inventory):
            raise ValueError("original configuration changed")
        for root, entries in self._prepared.preserved:
            if inventory(root) != entries:
                raise ValueError("preserved snapshot or archive changed")

    def close(self) -> None:
        if self._closed:
            return
        if self._process.poll() is None:
            self.assert_bound()
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired as exc:
                raise ValueError("owned emulator did not stop within deadline") from exc
        self._closed = True


class Launcher:
    def __init__(self, *, gate: BackupGate | None = None,
                 process_factory: Callable[..., Process] = subprocess.Popen,
                 inspector: Inspector | None = None) -> None:
        self.gate = gate if gate is not None else BackupGate()
        self.process_factory = process_factory
        self.inspector = inspector if inspector is not None else WindowsInspector()
        self._issued: dict[int, PreparedLaunch] = {}

    def prepare(self, config: RunConfig, *, state_filename: str,
                system_root: Path, graphics_backend: int | None = None,
                runtime_root: Path | None = None) -> PreparedLaunch:
        system_root = system_root.absolute()
        archive: Path | None = None
        prior_entries: Inventory = ()
        mutable: tuple[Path, ...] = ()
        if runtime_root is not None:
            runtime_root = runtime_root.absolute()
            _safe_path(runtime_root)
            workspace = Path.cwd().resolve()
            if (runtime_root.resolve() == workspace
                    or workspace not in runtime_root.resolve().parents):
                raise ValueError("runtime must be inside workspace")
            for root in (config.original_savedata, config.original_states, config.backup_root,
                         config.emulator_path, config.emulator_path.parent / "assets",
                         *config.emulator_path.parent.glob("*.dll"),
                         config.iso_path, config.profile_path):
                if paths_overlap(runtime_root, root):
                    raise ValueError("runtime overlaps protected source")
            app_root = runtime_root / "app"
            psp_root = app_root / "memstick" / "PSP"
            if runtime_root.exists():
                marker = runtime_root / ".psp-buddy-runtime"
                if (not marker.is_file() or marker.read_text() != "psp-buddy-runtime-v1\n"
                        or {p.name for p in runtime_root.iterdir()} != {"app", marker.name}):
                    raise ValueError("existing directory is not an owned runtime")
                prior_entries = inventory(runtime_root)
                allowed = {config.emulator_path.name, "assets", "memstick"}
                if any(p.name not in allowed and p.suffix.lower() != ".dll"
                       for p in app_root.iterdir()):
                    raise ValueError("unknown owned runtime application files")
                for parent, names in (
                        (app_root / "memstick", {"PSP"}),
                        (psp_root, {"SAVEDATA", "PPSSPP_STATE", "SYSTEM", "SCREENSHOT",
                                    "Cheats", "GAME", "PLUGINS", "TEXTURES"})):
                    if any(p.name not in names or not p.is_dir() for p in parent.iterdir()):
                        raise ValueError("unknown owned runtime memory stick files")
                expected = (psp_root / "SAVEDATA", psp_root / "PPSSPP_STATE",
                            psp_root / "SYSTEM")
                actual = (config.portable_savedata, config.portable_states, system_root)
                if any(a.resolve() != b.resolve() for a, b in zip(actual, expected, strict=True)):
                    raise ValueError("sources must identify active runtime memory stick")
                for root in expected:
                    inventory(root)
                mutable = tuple(root.absolute() for root in actual)
            else:
                for root in (*config.save_roots, system_root):
                    if paths_overlap(runtime_root, root):
                        raise ValueError("runtime overlaps seed source")
        endpoint = urlsplit(config.debugger_endpoint)
        if (endpoint.scheme != "ws" or endpoint.hostname not in ("localhost", "127.0.0.1", "::1")
                or endpoint.path != "/debugger" or endpoint.query or not endpoint.port):
            raise ValueError("unsupported debugger endpoint")
        if graphics_backend is not None and (
                type(graphics_backend) is not int or graphics_backend not in (0, 2)):
            raise ValueError("unsupported graphics backend")
        pattern = re.escape(config.game_id) + r"_\d+\.\d+_" + str(config.slot - 1) + r"\.ppst"
        if not re.fullmatch(pattern, state_filename):
            raise ValueError("state filename must match game, version and selected slot")
        if config.emulator_version != "1.20.4":
            raise ValueError("unsupported emulator version")
        for path in (config.emulator_path, config.iso_path):
            _safe_path(path)
            if not path.is_file() or path.stat().st_nlink != 1:
                raise ValueError("missing or unsafe launch file")
        if paths_overlap(system_root, config.backup_root):
            raise ValueError("configuration snapshot overlaps source")
        self.gate._guard(config)
        receipt = self.gate.prepare_trial(config)
        trial = receipt.snapshot_root.parent
        system_entries = _copy_tree(system_root, receipt.snapshot_root / "SYSTEM")
        self.gate._guard(config)
        if runtime_root is not None:
            if runtime_root.exists():
                if inventory(runtime_root) != prior_entries:
                    raise ValueError("active runtime changed during backup")
                archive = runtime_root.with_name(runtime_root.name + "-archive-" + uuid.uuid4().hex)
                _safe_path(archive)
                runtime_root.rename(archive)
                if inventory(archive) != prior_entries:
                    raise ValueError("runtime archive inventory changed")
            runtime_root.mkdir(parents=True, exist_ok=False)
            (runtime_root / ".psp-buddy-runtime").write_text("psp-buddy-runtime-v1\n")
        app = (runtime_root if runtime_root is not None else writable_trial_root(receipt)) / "app"
        app.mkdir()
        exe = app / config.emulator_path.name
        shutil.copy2(config.emulator_path, exe)
        if sha256(exe) != sha256(config.emulator_path):
            raise ValueError("executable copy hash mismatch")
        asset_entries = _copy_tree(config.emulator_path.parent / "assets", app / "assets")
        if not any(kind == "file" for _, kind, _, _ in asset_entries):
            raise ValueError("missing application assets")
        # DLLs alongside the configured executable belong to the application bundle.
        for dll in config.emulator_path.parent.glob("*.dll"):
            _safe_path(dll)
            if dll.stat().st_nlink != 1:
                raise ValueError("unsafe bundle hard link")
            shutil.copy2(dll, app / dll.name)
            if sha256(dll) != sha256(app / dll.name):
                raise ValueError("bundle hash mismatch")
        memstick = app / "memstick"
        psp = memstick / "PSP"
        psp.mkdir(parents=True)
        for index, name in ((2, "SAVEDATA"), (3, "PPSSPP_STATE")):
            source = receipt.snapshot_root / f"{index}-{config.save_roots[index].name}"
            _copy_tree(source, psp / name)
        system = psp / "SYSTEM"
        system.mkdir()
        for name in ("ppsspp.ini", "controls.ini"):
            source = receipt.snapshot_root / "SYSTEM" / name
            if not source.is_file():
                raise ValueError("missing required configuration")
            shutil.copy2(source, system / name)
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str  # type: ignore[method-assign,assignment]
        parser.read(system / "ppsspp.ini", encoding="utf-8-sig")
        for section in parser.sections():
            for key, value in parser.items(section):
                if key.casefold() in ("memstickdirectory", "flash0directory",
                                      "internaldatadirectory") and value.strip():
                    raise ValueError("configuration path override rejected")
        for section, settings in {
            "General": {"RemoteDebuggerOnStartup": "True", "RemoteDebuggerLocal": "True",
                        "RemoteISOPort": str(urlsplit(config.debugger_endpoint).port),
                        "CurrentDirectory": str(memstick),
                        "StateSlot": str(config.slot - 1), "EnableCheats": "False",
                        "EnablePlugins": "False", "LoadPlugins": "False",
                        "CheckForNewVersion": "False", "RemoteShareOnStartup": "False"},
            "Graphics": {"FullScreen": "False"},
        }.items():
            if not parser.has_section(section):
                parser.add_section(section)
            for key, value in settings.items():
                parser.set(section, key, value)
        if graphics_backend is not None:
            parser.set("Graphics", "GraphicsBackend", str(graphics_backend))
        with (system / "ppsspp.ini").open("w", encoding="utf-8") as stream:
            parser.write(stream)
        state = psp / "PPSSPP_STATE" / state_filename
        if not state.is_file() or not state.stat().st_size:
            raise ValueError("selected state is missing or empty")
        for root in (app, memstick, psp, system, psp / "SAVEDATA", psp / "PPSSPP_STATE"):
            _writable(root)
        args = (str(exe), f"--config={system / 'ppsspp.ini'}",
                f"--controlconfig={system / 'controls.ini'}", f"--state={state}",
                "--windowed", f"--log={writable_trial_root(receipt) / 'ppsspp.log'}",
                str(config.iso_path))
        (trial / "configuration-manifest.json").write_text(
            json.dumps({"source": str(system_root), "inventory": system_entries}, indent=2),
            encoding="utf-8",
        )
        prepared = PreparedLaunch(config, receipt, exe, memstick, args, inventory(app),
                                  sha256(config.iso_path), system_root, system_entries, mutable,
                                  ((receipt.snapshot_root, inventory(receipt.snapshot_root)),)
                                  + (() if archive is None else ((archive, prior_entries),)))
        self._issued[id(prepared)] = prepared
        return prepared

    def start(self, prepared: PreparedLaunch) -> LaunchSession:
        if self._issued.pop(id(prepared), None) is not prepared:
            raise ValueError("unknown or consumed prepared launch")
        if (inventory(prepared.executable.parent) != prepared.app_inventory
                or sha256(prepared.config.iso_path) != prepared.iso_digest
                or inventory(prepared.receipt.snapshot_root / "SYSTEM") != prepared.system_inventory
                or (prepared.system_root not in prepared.mutable_sources
                    and inventory(prepared.system_root) != prepared.system_inventory)):
            raise ValueError("prepared files or configuration hash changed")
        for root, entries in prepared.preserved:
            if inventory(root) != entries:
                raise ValueError("preserved snapshot or archive changed")
        port = urlsplit(prepared.config.debugger_endpoint).port
        assert port is not None
        if self.inspector.listeners(port):
            raise ValueError("existing debugger listener blocks launch")
        self.gate.validate_receipt(prepared.config, prepared.receipt)
        process = self.process_factory(list(prepared.arguments), cwd=prepared.executable.parent)
        issuer = object()
        _SESSION_ISSUERS[issuer] = (prepared, process, self.inspector)
        try:
            return LaunchSession(prepared, process, self.inspector, _issuer=issuer)
        except Exception:
            _SESSION_ISSUERS.pop(issuer, None)
            # The Popen handle belongs to this start call, even when inspection fails.
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            raise







