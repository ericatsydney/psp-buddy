import json
from dataclasses import asdict

import pytest
from test_menu_membership_inspection import menu_sample

from psp_buddy.inspection_io import load_json_object
from psp_buddy.menu_membership_inspection_io import parse_menu_membership_inspection_profile


def descriptor():
    values = asdict(menu_sample()[0])
    values.update(kind="menu_membership_inspection", schema_version=1)
    positioned = values["positioned_profile"]
    positioned.update(kind="positioned_representative_inspection", schema_version=1)
    representative = positioned["representative_profile"]
    representative.update(kind="representative_inspection", schema_version=1)
    representative["pool_profile"].update(kind="unit_pool_inspection", schema_version=1)
    return json.loads(json.dumps(values))


def test_nested_exact_descriptor():
    assert parse_menu_membership_inspection_profile(descriptor()) == menu_sample()[0]


@pytest.mark.parametrize(
    "field",
    [
        "kind",
        "schema_version",
        "positioned_profile",
        "menu_mask_table_address",
        "expected_category_masks",
        "ally_category_index",
        "foe_category_index",
        "code_anchors",
        "evidence_ids",
    ],
)
def test_missing_fields(field):
    values = descriptor()
    del values[field]
    with pytest.raises(ValueError):
        parse_menu_membership_inspection_profile(values)


@pytest.mark.parametrize(
    "change",
    [
        dict(extra=1),
        dict(schema_version=True),
        dict(schema_version=2),
        dict(kind="representative_inspection"),
        dict(positioned_profile={}),
        dict(menu_mask_table_address=True),
        dict(menu_mask_table_address=0x08806A01),
        dict(expected_category_masks=[True, 2, 4, 8]),
        dict(expected_category_masks=[]),
        dict(ally_category_index=True),
        dict(foe_category_index=4),
        dict(foe_category_index=0),
        dict(code_anchors=[]),
        dict(evidence_ids=["a", "a"]),
        dict(evidence_ids=["bad\n"]),
    ],
)
def test_invalid_fields(change):
    with pytest.raises(ValueError):
        parse_menu_membership_inspection_profile({**descriptor(), **change})


@pytest.mark.parametrize(
    "text", ['{"kind":1,"kind":2}', '{"value":NaN}', '{"value":Infinity}', '{"value":1e999}']
)
def test_strict_json(tmp_path, text):
    path = tmp_path / "profile.json"
    path.write_text(text)
    with pytest.raises(ValueError):
        parse_menu_membership_inspection_profile(load_json_object(path))
