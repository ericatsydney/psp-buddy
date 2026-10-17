import json
from dataclasses import asdict
from pathlib import Path

from test_positioned_inspection import positioned_sample

from psp_buddy.cli import main


def files(tmp_path, config_values):
    p, spans = positioned_sample()
    d = asdict(p)
    d.update(kind="positioned_representative_inspection", schema_version=1)
    base = d["representative_profile"]
    base.update(kind="representative_inspection", schema_version=1)
    base["pool_profile"].update(kind="unit_pool_inspection", schema_version=1)
    for key in ("game_id", "patch_id", "emulator_version"):
        base["pool_profile"][key] = config_values[key]
    Path(config_values["profile_path"]).write_text(json.dumps(d))
    config = tmp_path / "config.json"
    config.write_text(json.dumps(config_values))
    entries = []
    for i, span in enumerate(spans):
        name = f"{i}.bin"
        (tmp_path / name).write_bytes(span.data)
        entries.append(dict(address=span.address, path=name))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(dict(kind="representative_spans", schema_version=1, spans=entries))
    )
    return config, manifest


def test_positioned_cli_success(tmp_path, config_values, capsys):
    config, manifest = files(tmp_path, config_values)
    assert main(["inspect-map", "--config", str(config), "--records", str(manifest)]) == 0
    r = json.loads(capsys.readouterr().out)
    assert r["dimensions"] == {"width": 8, "height": 7}
    assert (r["representatives"][0]["tile_x"], r["representatives"][0]["tile_y"]) == (3, 4)
    assert not r["autonomous_available"] and not r["live_authenticated"]
    assert "x" not in r["unavailable_fields"]


def test_positioned_identity_before_binary_io(tmp_path, config_values, capsys):
    config, manifest = files(tmp_path, config_values)
    p = Path(config_values["profile_path"])
    d = json.loads(p.read_text())
    d["representative_profile"]["pool_profile"]["game_id"] = "other"
    p.write_text(json.dumps(d))
    manifest.unlink()
    assert main(["inspect-map", "--config", str(config), "--records", str(manifest)]) == 2
    assert "identity" in json.loads(capsys.readouterr().err)["error"]


def test_positioned_rejects_hardlinked_profile(tmp_path, config_values, capsys):
    import os

    config, manifest = files(tmp_path, config_values)
    os.link(config_values["profile_path"], tmp_path / "link.json")
    assert main(["inspect-map", "--config", str(config), "--records", str(manifest)]) == 2
    assert "hard link" in json.loads(capsys.readouterr().err)["error"]


def test_positioned_cli_no_live_modules_or_file_writes(tmp_path, config_values):
    import subprocess
    import sys

    config, manifest = files(tmp_path, config_values)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    code = """import sys
from psp_buddy.cli import main
assert main(['inspect-map','--config',sys.argv[1],'--records',sys.argv[2]]) == 0
assert not any('psp_buddy.'+n in sys.modules for n in
('launch','debugger','checkpoint','executor','supervisor'))
"""
    r = subprocess.run(
        [sys.executable, "-c", code, str(config), str(manifest)], capture_output=True, text=True
    )
    assert r.returncode == 0, r.stderr
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_positioned_invalid_evidence_has_no_fallback(tmp_path, config_values, capsys, monkeypatch):
    import socket

    config, manifest = files(tmp_path, config_values)
    (tmp_path / "0.bin").unlink()

    def forbidden(*args, **kwargs):
        raise AssertionError("live transport forbidden")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    assert main(["inspect-map", "--config", str(config), "--records", str(manifest)]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert json.loads(output.err)["autonomous_execution_enabled"] is False
