import subprocess
from pathlib import Path

import pytest

from psp_buddy.backup import BackupGate
from psp_buddy.config import RunConfig
from psp_buddy.launch import ConnectionNotReady, Launcher, ProcessIdentity


class Closed:
    def assert_non_writing(self, config: RunConfig) -> None:
        pass


def test_prepare_rejects_state_traversal(config_values: dict[str, object], tmp_path: Path) -> None:
    launcher = Launcher(gate=BackupGate(guard=Closed()))
    with pytest.raises(ValueError, match="state filename"):
        launcher.prepare(RunConfig.from_dict(config_values), state_filename="../bad.ppst",
                         system_root=tmp_path)




class FakeProcess:
    pid = 1234
    stopped = False

    def poll(self) -> int | None:
        return 0 if self.stopped else None

    def terminate(self) -> None:
        self.stopped = True

    def wait(self, timeout: float) -> int:
        return 0


class FakeInspector:
    identity = ProcessIdentity(Path('unused'), '', 'created')
    ports: tuple[tuple[str, int], ...] = ()

    def process(self, pid: int) -> ProcessIdentity:
        return self.identity

    def listeners(self, port: int) -> tuple[tuple[str, int], ...]:
        return self.ports


@pytest.fixture
def prepared_env(config_values: dict[str, object], tmp_path: Path):
    config = RunConfig.from_dict(config_values)
    config.emulator_path.write_bytes(b'synthetic exe')
    config.iso_path.write_bytes(b'synthetic ISO')
    assets = config.emulator_path.parent / 'assets'
    assets.mkdir()
    (assets / 'font.bin').write_bytes(b'synthetic font')
    (config.portable_states / 'ULJS00460_1.01_1.ppst').write_bytes(b'synthetic state')
    system = tmp_path / 'SYSTEM'
    system.mkdir()
    (system / 'ppsspp.ini').write_text('[General]\n[Graphics]\nGraphicsBackend=3\n')
    (system / 'controls.ini').write_text('[ControlMapping]\n')
    (system / 'ULJS00460_ppsspp.ini').write_text('pergame settings')
    inspector = FakeInspector()
    process = FakeProcess()

    def factory(args, **kwargs):
        inspector.identity = ProcessIdentity(
            Path(args[0]), subprocess.list2cmdline(args), 'created')
        return process

    launcher = Launcher(gate=BackupGate(guard=Closed()), process_factory=factory,
                        inspector=inspector)
    return launcher, config, system, inspector, process


def test_isolated_configuration_and_one_use_claim(prepared_env):
    launcher, config, system, inspector, process = prepared_env
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=system)
    assert (prepared.receipt.snapshot_root / 'SYSTEM' / 'ULJS00460_ppsspp.ini').is_file()
    isolated_system = prepared.memstick_root / 'PSP' / 'SYSTEM'
    assert not (isolated_system / 'ULJS00460_ppsspp.ini').exists()
    assert 'GraphicsBackend = 3' in (isolated_system / 'ppsspp.ini').read_text()
    session = launcher.start(prepared)
    assert session.game_version == '1.01'
    with pytest.raises(ConnectionNotReady):
        session.claim_connection()
    inspector.ports = (('127.0.0.1', process.pid),)
    assert session.claim_connection() == config.debugger_endpoint
    with pytest.raises(ValueError, match='already claimed'):
        session.claim_connection()
    session.close()
    session.verify_sources()
    assert process.stopped
    with pytest.raises(ValueError, match='consumed'):
        launcher.start(prepared)


def test_selected_d3d11_backend_changes_only_verified_trial_configuration(prepared_env):
    launcher, config, system, inspector, process = prepared_env
    source = (system / 'ppsspp.ini').read_bytes()
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=system, graphics_backend=2)
    assert (system / 'ppsspp.ini').read_bytes() == source
    assert (prepared.receipt.snapshot_root / 'SYSTEM' / 'ppsspp.ini').read_bytes() == source
    assert 'GraphicsBackend = 2' in (prepared.memstick_root / 'PSP' / 'SYSTEM' /
                                   'ppsspp.ini').read_text()
    session = launcher.start(prepared)
    session.close()
    session.verify_sources()


@pytest.mark.parametrize('backend', [True, 1, 3, -1])
def test_unvalidated_backend_selection_is_rejected(prepared_env, backend):
    launcher, config, system, inspector, process = prepared_env
    with pytest.raises(ValueError, match='graphics backend'):
        launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                         system_root=system, graphics_backend=backend)
    assert not config.backup_root.exists()


def test_hash_drift_prevents_launch(prepared_env):
    launcher, config, system, inspector, process = prepared_env
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=system)
    prepared.executable.write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash changed'):
        launcher.start(prepared)
    assert not process.stopped


def test_foreign_listener_and_pid_reuse_fail_closed(prepared_env):
    launcher, config, system, inspector, process = prepared_env
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=system)
    session = launcher.start(prepared)
    inspector.ports = (('127.0.0.1', 999),)
    with pytest.raises(ValueError, match='foreign'):
        session.claim_connection()
    identity = inspector.identity
    inspector.identity = ProcessIdentity(identity.executable, identity.command_line, 'reused')
    with pytest.raises(ValueError, match='identity'):
        session.close()
    assert not process.stopped


def test_bad_state_slot_and_override_denied(prepared_env):
    launcher, config, system, inspector, process = prepared_env
    with pytest.raises(ValueError, match='state filename'):
        launcher.prepare(config, state_filename='ULJS00460_1.01_0.ppst', system_root=system)
    (system / 'ppsspp.ini').write_text('[General]\nMemStickDirectory=C:/foreign\n')
    with pytest.raises(ValueError, match='override'):
        launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst', system_root=system)


def test_missing_assets_fail_closed(prepared_env):
    launcher, config, system, inspector, process = prepared_env
    (config.emulator_path.parent / 'assets' / 'font.bin').unlink()
    with pytest.raises(ValueError, match='assets'):
        launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst', system_root=system)



def test_current_directory_rewritten_only_in_isolated_copy(prepared_env):
    launcher, config, system, inspector, process = prepared_env
    original = '[General]\nCurrentDirectory=C:/normal/browser\n'
    (system / 'ppsspp.ini').write_text(original)
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=system)
    assert (system / 'ppsspp.ini').read_text() == original
    assert (prepared.receipt.snapshot_root / 'SYSTEM' / 'ppsspp.ini').read_text() == original
    isolated = prepared.memstick_root / 'PSP' / 'SYSTEM' / 'ppsspp.ini'
    assert f'CurrentDirectory = {prepared.memstick_root}' in isolated.read_text()


def test_direct_session_construction_is_denied(prepared_env):
    from psp_buddy.launch import LaunchSession
    launcher, config, system, inspector, process = prepared_env
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=system)
    inspector.identity = ProcessIdentity(prepared.executable,
                                        subprocess.list2cmdline(prepared.arguments), 'created')
    with pytest.raises(ValueError, match='issuer'):
        LaunchSession(prepared, process, inspector)


def test_failed_initial_identity_stops_only_owned_handle(prepared_env):
    launcher, config, system, inspector, process = prepared_env
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=system)

    def unavailable(pid):
        raise ValueError('identity unavailable')

    inspector.process = unavailable
    with pytest.raises(ValueError, match='identity unavailable'):
        launcher.start(prepared)
    assert process.stopped


@pytest.mark.parametrize('endpoint', [
    'wss://localhost:8080/debugger', 'ws://localhost:8080/other',
    'ws://localhost:8080/debugger?x=y', 'ws://localhost:0/debugger',
])
def test_unsupported_endpoint_denied_before_preparation(prepared_env, endpoint):
    from dataclasses import replace
    launcher, config, system, inspector, process = prepared_env
    config = replace(config, debugger_endpoint=endpoint)
    with pytest.raises(ValueError, match='endpoint'):
        launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst', system_root=system)
    assert not config.backup_root.exists()


def test_dead_process_and_config_drift_are_denied(prepared_env):
    launcher, config, system, inspector, process = prepared_env
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=system)
    session = launcher.start(prepared)
    process.stopped = True
    with pytest.raises(ValueError, match='not running'):
        session.claim_connection()
    (system / 'controls.ini').write_text('changed')
    with pytest.raises(ValueError, match='configuration changed'):
        session.verify_sources()


def test_inherited_plugins_disabled_only_in_copy(prepared_env):
    launcher, config, system, inspector, process = prepared_env
    original = '[General]\nEnablePlugins=True\nLoadPlugins=True\n'
    (system / 'ppsspp.ini').write_text(original)
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=system)
    isolated = prepared.memstick_root / 'PSP' / 'SYSTEM' / 'ppsspp.ini'
    assert 'EnablePlugins = False' in isolated.read_text()
    assert 'LoadPlugins = False' in isolated.read_text()
    assert (system / 'ppsspp.ini').read_text() == original


@pytest.mark.parametrize('address', ['0.0.0.0', '::'])
def test_owned_documented_wildcard_listener_accepted(prepared_env, address):
    launcher, config, system, inspector, process = prepared_env
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=system)
    session = launcher.start(prepared)
    inspector.ports = ((address, process.pid),)
    assert session.claim_connection() == config.debugger_endpoint


def test_owned_other_network_address_rejected(prepared_env):
    launcher, config, system, inspector, process = prepared_env
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=system)
    session = launcher.start(prepared)
    inspector.ports = (('192.168.1.2', process.pid),)
    with pytest.raises(ValueError, match='listener'):
        session.claim_connection()

def test_static_runtime_reuses_paths_and_preserves_previous_trial(prepared_env, tmp_path):
    from dataclasses import replace

    from psp_buddy.backup import inventory
    launcher, config, system, inspector, process = prepared_env
    runtime = tmp_path / 'runtime'
    first = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                             system_root=system, runtime_root=runtime)
    active = first.memstick_root / 'PSP'
    (active / 'SAVEDATA' / 'trial.bin').write_bytes(b'previous trial')
    config = replace(config, portable_savedata=active / 'SAVEDATA',
                     portable_states=active / 'PPSSPP_STATE')
    second = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                              system_root=active / 'SYSTEM', runtime_root=runtime)
    assert first.executable == second.executable
    assert first.arguments[3] == second.arguments[3]
    archives = list(tmp_path.glob('runtime-archive-*'))
    assert len(archives) == 1
    assert (archives[0] / 'app/memstick/PSP/SAVEDATA/trial.bin').read_bytes() == b'previous trial'
    assert (second.receipt.snapshot_root / '2-SAVEDATA/trial.bin').read_bytes() == b'previous trial'
    original = inventory(config.original_savedata)
    session = launcher.start(second)
    (active / 'SAVEDATA' / 'trial.bin').write_bytes(b'new trial')
    (active / 'SYSTEM' / 'ppsspp.ini').write_text('new settings')
    session.close()
    session.verify_sources()
    assert inventory(config.original_savedata) == original


def test_static_runtime_rejects_mismatched_active_sources(prepared_env, tmp_path):
    launcher, config, system, inspector, process = prepared_env
    runtime = tmp_path / 'runtime'
    launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                     system_root=system, runtime_root=runtime)
    with pytest.raises(ValueError, match='active runtime'):
        launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                         system_root=system, runtime_root=runtime)


def test_static_runtime_rejects_unowned_directory(prepared_env, tmp_path):
    launcher, config, system, inspector, process = prepared_env
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    (runtime / 'user-file').write_text('preserve')
    with pytest.raises(ValueError, match='owned runtime'):
        launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                         system_root=system, runtime_root=runtime)
    assert (runtime / 'user-file').read_text() == 'preserve'

def test_static_runtime_backup_failure_preserves_active_runtime(prepared_env, tmp_path):
    from dataclasses import replace

    from psp_buddy.backup import inventory
    launcher, config, system, inspector, process = prepared_env
    runtime = tmp_path / 'runtime'
    first = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                             system_root=system, runtime_root=runtime)
    active = first.memstick_root / 'PSP'
    config = replace(config, portable_savedata=active / 'SAVEDATA',
                     portable_states=active / 'PPSSPP_STATE')
    before = inventory(runtime)

    def fail_copy(source, target):
        raise OSError('copy failure')

    launcher.gate.copy_file = fail_copy
    with pytest.raises(ValueError, match='backup copy failed'):
        launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                         system_root=active / 'SYSTEM', runtime_root=runtime)
    assert inventory(runtime) == before
    assert not list(tmp_path.glob('runtime-archive-*'))


def test_static_runtime_snapshot_tampering_blocks_launch(prepared_env, tmp_path):
    launcher, config, system, inspector, process = prepared_env
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=system, runtime_root=tmp_path / 'runtime')
    (prepared.receipt.snapshot_root / 'SYSTEM/controls.ini').write_text('tampered')
    with pytest.raises(ValueError, match='hash changed'):
        launcher.start(prepared)


def test_static_runtime_unknown_memstick_files_preserved_and_denied(prepared_env, tmp_path):
    from dataclasses import replace
    launcher, config, system, inspector, process = prepared_env
    runtime = tmp_path / 'runtime'
    first = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                             system_root=system, runtime_root=runtime)
    active = first.memstick_root / 'PSP'
    unknown = first.memstick_root / 'user-file'
    unknown.write_text('preserve')
    config = replace(config, portable_savedata=active / 'SAVEDATA',
                     portable_states=active / 'PPSSPP_STATE')
    with pytest.raises(ValueError, match='unknown owned runtime'):
        launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                         system_root=active / 'SYSTEM', runtime_root=runtime)
    assert unknown.read_text() == 'preserve'

def test_static_runtime_accepts_emulator_created_directories(prepared_env, tmp_path):
    from dataclasses import replace
    launcher, config, system, inspector, process = prepared_env
    runtime = tmp_path / 'runtime'
    first = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                             system_root=system, runtime_root=runtime)
    active = first.memstick_root / 'PSP'
    for name in ('Cheats', 'GAME', 'PLUGINS', 'TEXTURES', 'SCREENSHOT'):
        (active / name).mkdir()
        (active / name / 'prior.bin').write_bytes(b'preserved content')
    config = replace(config, portable_savedata=active / 'SAVEDATA',
                     portable_states=active / 'PPSSPP_STATE')
    launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                     system_root=active / 'SYSTEM', runtime_root=runtime)
    archives = list(tmp_path.glob('runtime-archive-*'))
    assert len(archives) == 1
    for name in ('Cheats', 'GAME', 'PLUGINS', 'TEXTURES', 'SCREENSHOT'):
        assert (archives[0] / 'app/memstick/PSP' / name / 'prior.bin').read_bytes() == (
            b'preserved content')
        assert not (active / name).exists()
    settings = (active / 'SYSTEM/ppsspp.ini').read_text()
    assert 'EnableCheats = False' in settings
    assert 'EnablePlugins = False' in settings

def test_static_runtime_relative_active_paths_allow_trial_writes(prepared_env, tmp_path):
    from dataclasses import replace
    launcher, config, system, inspector, process = prepared_env
    runtime = tmp_path / 'runtime'
    first = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                             system_root=system, runtime_root=runtime)
    active = first.memstick_root / 'PSP'
    relative = active.relative_to(Path.cwd())
    config = replace(config, portable_savedata=relative / 'SAVEDATA',
                     portable_states=relative / 'PPSSPP_STATE')
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst',
                                system_root=relative / 'SYSTEM', runtime_root=runtime)
    session = launcher.start(prepared)
    (active / 'SAVEDATA' / 'trial.bin').write_bytes(b'new trial')
    (active / 'SYSTEM/ppsspp.ini').write_text('new settings')
    session.close()
    session.verify_sources()
