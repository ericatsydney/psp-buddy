import json
from dataclasses import asdict
from pathlib import Path

from test_representative_inspection import sample

from psp_buddy.cli import main


def files(tmp_path, config_values):
    profile, spans = sample()
    descriptor = asdict(profile)
    descriptor.update(kind='representative_inspection', schema_version=1)
    descriptor['pool_profile'].update(kind='unit_pool_inspection', schema_version=1)
    for key in ('game_id', 'patch_id', 'emulator_version'):
        descriptor['pool_profile'][key] = config_values[key]
    Path(config_values['profile_path']).write_text(json.dumps(descriptor))
    config = tmp_path / 'config.json'
    config.write_text(json.dumps(config_values))
    entries = []
    for i, span in enumerate(spans):
        name = f'span-{i}.bin'
        (tmp_path / name).write_bytes(span.data)
        entries.append(dict(address=span.address, path=name))
    manifest = tmp_path / 'representatives.json'
    manifest.write_text(json.dumps(dict(kind='representative_spans', schema_version=1,
                                       spans=entries)))
    return config, manifest


def test_representative_cli_real_offline_success(tmp_path, config_values, capsys, monkeypatch):
    import socket

    config, manifest = files(tmp_path, config_values)
    def forbidden(*args, **kwargs):
        raise AssertionError('live transport forbidden')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    assert main(['inspect-map', '--config', str(config), '--records', str(manifest)]) == 0
    report = json.loads(capsys.readouterr().out)
    row = report['representatives'][0]
    assert (row['mech_id'], row['pilot_id'], row['defense']) == (122, 134, 1000)
    assert report['live_authenticated'] is False
    assert report['autonomous_available'] is False
    assert report['tactical_snapshot_available'] is False


def test_representative_cli_identity_before_span_reads(tmp_path, config_values, capsys):
    config, manifest = files(tmp_path, config_values)
    path = Path(config_values['profile_path'])
    d = json.loads(path.read_text())
    d['pool_profile']['game_id'] = 'wrong'
    path.write_text(json.dumps(d))
    manifest.unlink()
    assert main(['inspect-map', '--config', str(config), '--records', str(manifest)]) == 2
    assert 'identity' in json.loads(capsys.readouterr().err)['error']


def test_representative_profile_rejects_hardlink(tmp_path, config_values, capsys):
    import os

    config, manifest = files(tmp_path, config_values)
    os.link(config_values['profile_path'], tmp_path / 'linked-profile.json')
    assert main(['inspect-map', '--config', str(config), '--records', str(manifest)]) == 2
    assert 'hard link' in json.loads(capsys.readouterr().err)['error']


def test_representative_missing_spans_returns_error_without_live(tmp_path, config_values,
                                                              capsys, monkeypatch):
    import socket

    config, manifest = files(tmp_path, config_values)
    (tmp_path / 'span-0.bin').unlink()
    def forbidden(*args, **kwargs):
        raise AssertionError('live transport forbidden')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    assert main(['inspect-map', '--config', str(config), '--records', str(manifest)]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert json.loads(output.err)['autonomous_execution_enabled'] is False


def test_representative_command_imports_no_live_modules_and_writes_no_files(tmp_path,
                                                                         config_values):
    import subprocess
    import sys

    config, manifest = files(tmp_path, config_values)
    code = '''import sys
from psp_buddy.cli import main
assert main(['inspect-map', '--config', sys.argv[1], '--records', sys.argv[2]]) == 0
assert not any('psp_buddy.' + name in sys.modules for name in
    ('launch', 'trial', 'debugger', 'checkpoint', 'executor', 'supervisor'))
'''
    before = {path: path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    result = subprocess.run([sys.executable, '-c', code, str(config), str(manifest)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert before == {path: path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
