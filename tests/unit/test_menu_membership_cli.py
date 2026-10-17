import json
from dataclasses import asdict
from pathlib import Path

from test_menu_membership_inspection import menu_sample

from psp_buddy.cli import main


def files(tmp_path, config_values, group=0):
    profile, spans = menu_sample(group=group)
    d = asdict(profile)
    d.update(kind="menu_membership_inspection", schema_version=1)
    positioned = d["positioned_profile"]
    positioned.update(kind="positioned_representative_inspection", schema_version=1)
    rep = positioned["representative_profile"]
    rep.update(kind="representative_inspection", schema_version=1)
    rep["pool_profile"].update(kind="unit_pool_inspection", schema_version=1)
    for key in ("game_id", "patch_id", "emulator_version"):
        rep["pool_profile"][key] = config_values[key]
    Path(config_values["profile_path"]).write_text(json.dumps(d))
    config = tmp_path / "config.json"
    config.write_text(json.dumps(config_values))
    entries = []
    for i, s in enumerate(spans):
        name = f"{i}.bin"
        (tmp_path / name).write_bytes(s.data)
        entries.append(dict(address=s.address, path=name))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(dict(kind="representative_spans", schema_version=1, spans=entries))
    )
    return config, manifest


def test_menu_cli_real_offline_success(tmp_path, config_values, capsys):
    cfg, manifest = files(tmp_path, config_values)
    assert main(["inspect-map", "--config", str(cfg), "--records", str(manifest)]) == 0
    r = json.loads(capsys.readouterr().out)
    assert r["category_counts"] == [1, 0, 0, 0]
    row = r["representatives"][0]
    assert (row["menu_membership"], row["tile_x"], row["tile_y"], row["hp"]) == (
        "ally_menu",
        3,
        4,
        4700,
    )
    assert "side" in r["unavailable_fields"]
    assert all(
        r[k] is False
        for k in (
            "live_authenticated",
            "autonomous_available",
            "autonomous_execution_enabled",
            "tactical_snapshot_available",
        )
    )


def test_menu_cli_identity_before_binary_loading(tmp_path, config_values, capsys):
    cfg, manifest = files(tmp_path, config_values)
    p = Path(config_values["profile_path"])
    d = json.loads(p.read_text())
    d["positioned_profile"]["representative_profile"]["pool_profile"]["game_id"] = "other"
    p.write_text(json.dumps(d))
    manifest.unlink()
    assert main(["inspect-map", "--config", str(cfg), "--records", str(manifest)]) == 2
    assert "identity" in json.loads(capsys.readouterr().err)["error"]


def test_menu_cli_outside_is_not_neutral(tmp_path, config_values, capsys):
    cfg, manifest = files(tmp_path, config_values, group=4)
    assert main(["inspect-map", "--config", str(cfg), "--records", str(manifest)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["outside_menu_count"] == 1
    assert report["representatives"][0]["menu_membership"] == "outside_ally_foe_menus"
    assert "side" in report["unavailable_fields"]


def test_menu_cli_unsupported_group_stops_without_transport(
    tmp_path, config_values, capsys, monkeypatch
):
    import socket

    cfg, manifest = files(tmp_path, config_values, group=32)

    def forbidden(*args, **kwargs):
        raise AssertionError("live transport forbidden")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    assert main(["inspect-map", "--config", str(cfg), "--records", str(manifest)]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert json.loads(output.err)["autonomous_execution_enabled"] is False


def test_menu_profile_hardlink_rejected(tmp_path, config_values, capsys):
    import os

    cfg, manifest = files(tmp_path, config_values)
    os.link(config_values["profile_path"], tmp_path / "profile-link.json")
    assert main(["inspect-map", "--config", str(cfg), "--records", str(manifest)]) == 2
    assert "hard link" in json.loads(capsys.readouterr().err)["error"]


def test_menu_cli_imports_no_live_controllers_and_writes_no_files(tmp_path, config_values):
    import subprocess
    import sys

    cfg, manifest = files(tmp_path, config_values)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    code = """import sys
from psp_buddy.cli import main
assert main(['inspect-map','--config',sys.argv[1],'--records',sys.argv[2]]) == 0
assert not any('psp_buddy.'+n in sys.modules for n in
('launch','trial','debugger','checkpoint','executor','supervisor'))
"""
    r = subprocess.run(
        [sys.executable, "-c", code, str(cfg), str(manifest)], capture_output=True, text=True
    )
    assert r.returncode == 0, r.stderr
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
