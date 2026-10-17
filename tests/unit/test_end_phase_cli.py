import json
from pathlib import Path

from test_menu_membership_cli import files as menu_files

from psp_buddy.cli import main


def files(tmp_path, config_values, group=0):
    cfg, manifest = menu_files(tmp_path, config_values, group)
    path = Path(config_values["profile_path"])
    menu = json.loads(path.read_text())
    path.write_text(json.dumps(dict(kind="end_phase_inspection", schema_version=1,
        menu_membership_profile=menu, code_anchors=menu["code_anchors"],
        evidence_ids=["end-phase-evidence"])))
    return cfg, manifest


def test_end_phase_cli_success(tmp_path, config_values, capsys):
    cfg, manifest = files(tmp_path, config_values)
    assert main(["inspect-map", "--config", str(cfg), "--records", str(manifest)]) == 0
    r = json.loads(capsys.readouterr().out)
    assert r["inspection_kind"] == "end_phase_inspection"
    assert r["end_phase_scope_count"] == 1
    assert r["unmoved_unit_count"] == r["displayed_unmoved_unit_count"] == 0
    row = r["representatives"][0]
    assert (row["hp"], row["tile_x"], row["counter_value"]) == (4700, 3, 0)
    assert row["end_phase_count_scope"] is True
    assert row["counted_as_unmoved"] is False
    assert all(r[k] is False for k in ("live_authenticated", "autonomous_available",
        "autonomous_execution_enabled", "tactical_snapshot_available"))


def test_identity_checked_before_records(tmp_path, config_values, capsys):
    cfg, manifest = files(tmp_path, config_values)
    path = Path(config_values["profile_path"])
    d = json.loads(path.read_text())
    d["menu_membership_profile"]["positioned_profile"]["representative_profile"][
        "pool_profile"]["game_id"] = "other"
    path.write_text(json.dumps(d))
    manifest.unlink()
    assert main(["inspect-map", "--config", str(cfg), "--records", str(manifest)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "identity" in json.loads(captured.err)["error"]


def test_end_phase_scope_differs_from_ally_menu(tmp_path, config_values, capsys):
    cfg, manifest = files(tmp_path, config_values, 3)
    assert main(["inspect-map", "--config", str(cfg), "--records", str(manifest)]) == 0
    r = json.loads(capsys.readouterr().out)
    assert r["ally_menu_count"] == 1
    assert r["end_phase_scope_count"] == 0


def test_invalid_group_no_partial_report(tmp_path, config_values, capsys):
    cfg, manifest = files(tmp_path, config_values, 32)
    assert main(["inspect-map", "--config", str(cfg), "--records", str(manifest)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Unsupported raw" in json.loads(captured.err)["error"]
