import json
import subprocess
import sys
from pathlib import Path

import pytest

from psp_buddy.cli import main


def files(tmp_path, config_values):
    descriptor = dict(kind='stat_inspection', schema_version=1, game_id='ULJS00460',
        patch_id='english-v0.8', emulator_version='1.20.4', unit_label='synthetic',
        record_address=0x08800000, record_size=4, fields=[
            dict(name='hp', offset=0, width=2, evidence_ids=['synthetic-hp']),
            dict(name='max_hp', offset=2, width=2, evidence_ids=['synthetic-max-hp'])])
    profile = Path(config_values['profile_path'])
    profile.write_text(json.dumps(descriptor))
    config = tmp_path / 'config.json'
    config.write_text(json.dumps(config_values))
    record = tmp_path / 'record.bin'
    record.write_bytes(bytes([50, 0, 100, 0]))
    return config, profile, record


def test_validate_reports_unmet_gates(tmp_path, config_values, capsys):
    config, _, _ = files(tmp_path, config_values)
    assert main(['validate', '--config', str(config)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['autonomous_execution_enabled'] is False
    assert report['profile']['kind'] == 'stat_inspection'
    assert report['profile']['live_authenticated'] is False
    assert all(gate['passed'] is False for gate in report['live_gates'])
    assert report['policy']['max_retries'] == 3


def test_inspect_supplied_bytes_reports_stats_and_provenance(tmp_path, config_values, capsys):
    config, _, record = files(tmp_path, config_values)
    assert main(['inspect', '--config', str(config), '--record', str(record)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['values'] == {'hp': 50, 'max_hp': 100}
    assert report['provenance'] == 'user_supplied_record_and_profile'
    assert report['live_authenticated'] is False
    assert report['tactical_snapshot_available'] is False


def test_inspect_without_record_has_no_live_fallback(tmp_path, config_values, capsys):
    config, _, _ = files(tmp_path, config_values)
    assert main(['inspect', '--config', str(config)]) == 2
    assert 'record' in json.loads(capsys.readouterr().err)['error']


@pytest.mark.parametrize('extra', [[], ['--dry-run']])
def test_run_is_refused_including_dry_run(tmp_path, config_values, capsys, extra):
    config, _, _ = files(tmp_path, config_values)
    assert main(['run', '--config', str(config), *extra]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report['reason'] == 'live_integration_gates_unmet'
    assert report['autonomous_execution_enabled'] is False


@pytest.mark.parametrize('change', [dict(slot=True), dict(max_retries=4), dict(unknown=1),
    dict(debugger_endpoint='ws://example.com:8080')])
def test_bad_configuration_fails(tmp_path, config_values, capsys, change):
    config, _, _ = files(tmp_path, {**config_values, **change})
    assert main(['validate', '--config', str(config)]) == 2
    assert 'error' in json.loads(capsys.readouterr().err)


def test_bad_policy_is_not_ignored(tmp_path, config_values, capsys):
    config, _, _ = files(tmp_path, config_values)
    instructions = tmp_path / 'instructions.txt'
    instructions.write_text('attack anything anywhere')
    assert main(['validate', '--config', str(config),
                 '--instructions-file', str(instructions)]) == 2
    assert 'unsupported' in json.loads(capsys.readouterr().err)['error']


def test_config_retry_ceiling_limits_default_policy(tmp_path, config_values, capsys):
    config, _, _ = files(tmp_path, {**config_values, 'max_retries': 1})
    assert main(['validate', '--config', str(config)]) == 0
    assert json.loads(capsys.readouterr().out)['policy']['max_retries'] == 1


def test_explicit_policy_cannot_exceed_config_ceiling(tmp_path, config_values, capsys):
    config, _, _ = files(tmp_path, {**config_values, 'max_retries': 1})
    instructions = tmp_path / 'instructions.txt'
    instructions.write_text('retry at most 2 times')
    assert main(['validate', '--config', str(config),
                 '--instructions-file', str(instructions)]) == 2


@pytest.mark.parametrize('kind', ['identity', 'tactical', 'short', 'long', 'bad_hp'])
def test_invalid_profile_or_record_fails(tmp_path, config_values, capsys, kind):
    config, profile, record = files(tmp_path, config_values)
    if kind in ('identity', 'tactical'):
        descriptor = json.loads(profile.read_text())
        descriptor['game_id' if kind == 'identity' else 'kind'] = 'other'
        profile.write_text(json.dumps(descriptor))
    else:
        record.write_bytes({'short': b'1', 'long': b'12345', 'bad_hp': b'\xff\x00\x01\x00'}[kind])
    assert main(['inspect', '--config', str(config), '--record', str(record)]) == 2
    assert 'error' in json.loads(capsys.readouterr().err)


def test_commands_import_no_live_modules_and_write_no_files(tmp_path, config_values):
    config, _, record = files(tmp_path, config_values)
    code = """import sys
from psp_buddy.cli import main
for argv in (["validate", "--config", sys.argv[1]],
             ["inspect", "--config", sys.argv[1], "--record", sys.argv[2]],
             ["run", "--config", sys.argv[1], "--dry-run"]):
    main(argv)
assert not any('psp_buddy.' + name in sys.modules for name in
               ('launch', 'trial', 'debugger', 'checkpoint', 'executor', 'supervisor'))
"""
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = subprocess.run([sys.executable, '-c', code, str(config), str(record)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    after = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert before == after


def test_help_lists_offline_commands(capsys):
    with pytest.raises(SystemExit) as stopped:
        main(['--help'])
    assert stopped.value.code == 0
    assert 'validate' in capsys.readouterr().out


@pytest.mark.parametrize('content', [b' ' * (1024 * 1024 + 1),
    ('{"nested":' + '[' * 2000 + '0' + ']' * 2000 + '}').encode()],
    ids=['oversized', 'deeply_nested'])
def test_bounded_or_deep_config_errors_are_json_without_traceback(
    tmp_path, config_values, capsys, content,
):
    config, _, _ = files(tmp_path, config_values)
    config.write_bytes(content)
    assert main(['validate', '--config', str(config)]) == 2
    result = capsys.readouterr()
    assert result.out == ''
    assert json.loads(result.err)['autonomous_execution_enabled'] is False
    assert 'Traceback' not in result.err


def test_oversized_instructions_fail_before_policy_parsing(tmp_path, config_values, capsys):
    config, _, _ = files(tmp_path, config_values)
    instructions = tmp_path / 'instructions.txt'
    instructions.write_bytes(b' ' * (65536 + 1))
    assert main(['validate', '--config', str(config),
                 '--instructions-file', str(instructions)]) == 2
    report = json.loads(capsys.readouterr().err)
    assert 'bounds' in report['error']
    assert report['autonomous_execution_enabled'] is False
