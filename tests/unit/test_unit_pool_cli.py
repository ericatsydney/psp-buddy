import hashlib
import json
import struct
from pathlib import Path

from psp_buddy.cli import main


def fixture_files(tmp_path, config_values):
    descriptor = dict(kind='unit_pool_inspection', schema_version=1,
        game_id=config_values['game_id'], patch_id=config_values['patch_id'],
        emulator_version=config_values['emulator_version'], map_label='synthetic',
        pool_address=0x08801000, pool_capacity=1, pool_stride=104,
        actor_owner_address=0x08802000, actor_node_array_address=0x08805000,
        actor_stride=16, actor_capacity=1, actor_vtable=0x08806000,
        evidence_ids=['synthetic'], code_anchors=[dict(address=0x08804000, size=4,
            sha256=hashlib.sha256(b'code').hexdigest())])
    profile = Path(config_values['profile_path'])
    profile.write_text(json.dumps(descriptor))
    config = tmp_path / 'config.json'
    config.write_text(json.dumps(config_values))
    pool = bytearray(104)
    pool[0] = 1
    struct.pack_into('<III', pool, 20, 0x401, 48, 80)
    owner = bytearray(28)
    struct.pack_into('<IIII', owner, 8, 0x08805000, 0x08803000, 16, 1)
    data = [(0x08801000, pool), (0x08802000, owner),
        (0x08803000, struct.pack('<IIII', 0x08806000, 0x08807000, 0x08808000, 0x08801000)),
        (0x08804000, b'code')]
    entries = []
    for i, (address, content) in enumerate(data):
        name = f'{i}.bin'
        (tmp_path / name).write_bytes(content)
        entries.append(dict(address=address, path=name))
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps(dict(kind='inspection_spans', schema_version=1, spans=entries)))
    return config, profile, manifest


def test_unit_pool_cli_real_synthetic_success(tmp_path, config_values, capsys):
    config, _, manifest = fixture_files(tmp_path, config_values)
    assert main(['inspect-map', '--config', str(config), '--records', str(manifest)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['candidate_count'] == 1
    assert report['provenance'] == 'user_supplied_spans_and_profile'
    assert report['slots'][0]['raw_state_word'] == 0x401
    assert report['autonomous_execution_enabled'] is False
    assert report['live_authenticated'] is False


def test_identity_mismatch_before_manifest_read(tmp_path, config_values, capsys, monkeypatch):
    config, profile, manifest = fixture_files(tmp_path, config_values)
    values = json.loads(profile.read_text())
    values['game_id'] = 'other'
    profile.write_text(json.dumps(values))
    def poisoned(*args):
        raise AssertionError('binary IO forbidden for mismatched identity')
    monkeypatch.setattr('psp_buddy.cli.load_inspection_spans', poisoned)
    assert main(['inspect-map', '--config', str(config), '--records', str(manifest)]) == 2
    assert 'identity' in json.loads(capsys.readouterr().err)['error']


def test_missing_span_has_no_live_fallback(tmp_path, config_values, capsys, monkeypatch):
    import socket
    config, _, manifest = fixture_files(tmp_path, config_values)
    (tmp_path / '0.bin').unlink()
    def poisoned(*args, **kwargs):
        raise AssertionError('live transport forbidden')
    monkeypatch.setattr(socket, 'create_connection', poisoned)
    assert main(['inspect-map', '--config', str(config), '--records', str(manifest)]) == 2
    assert 'error' in json.loads(capsys.readouterr().err)


def test_wrong_code_bytes_reject_entire_cli_report(tmp_path, config_values, capsys):
    config, _, manifest = fixture_files(tmp_path, config_values)
    (tmp_path / '3.bin').write_bytes(b'fake')
    assert main(['inspect-map', '--config', str(config), '--records', str(manifest)]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert 'error' in json.loads(output.err)


def test_pool_command_imports_no_live_modules_and_writes_no_files(tmp_path, config_values):
    import subprocess
    import sys
    config, _, manifest = fixture_files(tmp_path, config_values)
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
