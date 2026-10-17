import json
from copy import deepcopy
from dataclasses import asdict

import pytest
from test_positioned_inspection import positioned_sample

from psp_buddy.inspection_io import load_json_object
from psp_buddy.positioned_inspection_io import parse_positioned_inspection_profile


def descriptor():
    profile, _ = positioned_sample()
    values = asdict(profile)
    values.update(kind="positioned_representative_inspection", schema_version=1)
    nested = values["representative_profile"]
    nested.update(kind="representative_inspection", schema_version=1)
    nested["pool_profile"].update(kind="unit_pool_inspection", schema_version=1)
    return json.loads(json.dumps(values))


def test_complete_nested_profile():
    result = parse_positioned_inspection_profile(descriptor())
    assert result == positioned_sample()[0]


@pytest.mark.parametrize("field", ["kind", "schema_version", "representative_profile", "geometry"])
def test_missing_top_fields(field):
    values = descriptor()
    del values[field]
    with pytest.raises(ValueError):
        parse_positioned_inspection_profile(values)


@pytest.mark.parametrize(
    "change",
    [
        {"extra": 1},
        {"schema_version": True},
        {"schema_version": 2},
        {"kind": "representative_inspection"},
        {"geometry": None},
        {"representative_profile": {}},
    ],
)
def test_strict_top_fields(change):
    with pytest.raises(ValueError):
        parse_positioned_inspection_profile({**descriptor(), **change})


@pytest.mark.parametrize(
    "field", ["width_address", "height_address", "code_anchors", "evidence_ids"]
)
def test_missing_geometry_fields(field):
    values = descriptor()
    del values["geometry"][field]
    with pytest.raises(ValueError):
        parse_positioned_inspection_profile(values)


@pytest.mark.parametrize("bad", [True, False, -1, 0, 1.0, float("nan"), float("inf"), 0x0A000000])
def test_invalid_json_address(bad):
    values = descriptor()
    values["geometry"]["width_address"] = bad
    with pytest.raises(ValueError):
        parse_positioned_inspection_profile(values)


@pytest.mark.parametrize(
    "change",
    [
        {"extra": 0},
        {"code_anchors": []},
        {"evidence_ids": []},
        {"evidence_ids": ["x", "x"]},
        {"evidence_ids": ["x\n"]},
        {"code_anchors": [{"address": 0x08800000, "size": 4, "sha256": "bad"}]},
    ],
)
def test_strict_geometry_fields(change):
    values = deepcopy(descriptor())
    values["geometry"].update(change)
    with pytest.raises(ValueError):
        parse_positioned_inspection_profile(values)


def test_loader_rejects_duplicate_and_nonfinite_json(tmp_path):
    path = tmp_path / "profile.json"
    for text in ('{"kind":1,"kind":2}', '{"value":NaN}'):
        path.write_text(text)
        with pytest.raises(ValueError):
            parse_positioned_inspection_profile(load_json_object(path))


def test_parser_rejects_wrong_kind():
    with pytest.raises(ValueError):
        parse_positioned_inspection_profile({"kind": "wrong"})
