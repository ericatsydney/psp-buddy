import copy

import pytest
from test_menu_membership_inspection import menu_sample
from test_menu_membership_inspection_io import descriptor as menu_descriptor

from psp_buddy.end_phase_inspection_io import parse_end_phase_inspection_profile
from psp_buddy.unit_pool_inspection import CodeAnchor


def descriptor():
    return dict(
        kind="end_phase_inspection",
        schema_version=1,
        menu_membership_profile=menu_descriptor(),
        code_anchors=[dict(address=0x08807000, size=4, sha256="a" * 64)],
        evidence_ids=["end-phase-evidence"],
    )


def test_exact_nested_descriptor_and_immutable_input():
    from psp_buddy.end_phase_inspection import EndPhaseInspectionProfile

    values = descriptor()
    original = copy.deepcopy(values)
    result = parse_end_phase_inspection_profile(values)
    assert result == EndPhaseInspectionProfile(
        menu_sample()[0],
        (CodeAnchor(0x08807000, 4, "a" * 64),),
        ("end-phase-evidence",),
    )
    assert values == original


@pytest.mark.parametrize("field", list(descriptor()))
def test_missing_fields(field):
    values = descriptor()
    del values[field]
    with pytest.raises(ValueError):
        parse_end_phase_inspection_profile(values)


@pytest.mark.parametrize(
    "change",
    [
        dict(extra=1),
        dict(kind="menu_membership_inspection"),
        dict(schema_version=True),
        dict(schema_version=2),
        dict(menu_membership_profile={}),
        dict(code_anchors=[]),
        dict(code_anchors=[{}]),
        dict(code_anchors=[dict(address=True, size=4, sha256="a" * 64)]),
        dict(code_anchors=[dict(address=0x08807000, size=True, sha256="a" * 64)]),
        dict(code_anchors=[dict(address=0x08807000, size=4, sha256="invalid")]),
        dict(code_anchors=[dict(address=0x08807000, size=4, sha256="a" * 64, extra=1)]),
        dict(code_anchors=[dict(address=0x08807000, size=4, sha256="a" * 64)] * 17),
        dict(evidence_ids=[]),
        dict(evidence_ids=["duplicate", "duplicate"]),
        dict(evidence_ids=["bad\n"]),
        dict(evidence_ids=[""]),
        dict(evidence_ids=[True]),
        dict(evidence_ids=[str(i) for i in range(33)]),
    ],
)
def test_invalid_fields(change):
    with pytest.raises(ValueError):
        parse_end_phase_inspection_profile({**descriptor(), **change})


@pytest.mark.parametrize("values", [None, [], True, "profile"])
def test_requires_object(values):
    with pytest.raises(ValueError):
        parse_end_phase_inspection_profile(values)


@pytest.mark.parametrize(
    "text",
    ['{"kind":1,"kind":2}', '{"value":NaN}', '{"value":Infinity}', '{"value":1e999}'],
)
def test_strict_json_loader(tmp_path, text):
    from psp_buddy.inspection_io import load_json_object

    path = tmp_path / "profile.json"
    path.write_text(text)
    with pytest.raises(ValueError):
        parse_end_phase_inspection_profile(load_json_object(path))
