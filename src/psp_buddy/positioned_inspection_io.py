"""Strict nested JSON descriptor for offline positioned inspection."""

from .inspection_io import _integer, _keys, _object, _text
from .positioned_inspection import GeometryProfile, PositionedInspectionProfile
from .representative_inspection_io import parse_representative_inspection_profile
from .unit_pool_inspection import CodeAnchor
from .unit_pool_inspection_io import _list


def parse_positioned_inspection_profile(values: object) -> PositionedInspectionProfile:
    """Accept exactly the version-one positioned descriptor."""
    values = _object(values)
    _keys(values, {"kind", "schema_version", "representative_profile", "geometry"})
    if (
        values["kind"] != "positioned_representative_inspection"
        or _integer(values["schema_version"]) != 1
    ):
        raise ValueError("Unsupported positioned profile kind or schema version")
    geometry = _object(values["geometry"])
    _keys(geometry, {"width_address", "height_address", "code_anchors", "evidence_ids"})
    anchors = []
    for item in _list(geometry["code_anchors"], 1, 16):
        anchor = _object(item)
        _keys(anchor, {"address", "size", "sha256"})
        anchors.append(
            CodeAnchor(
                _integer(anchor["address"]), _integer(anchor["size"]), _text(anchor["sha256"])
            )
        )
    return PositionedInspectionProfile(
        parse_representative_inspection_profile(values["representative_profile"]),
        GeometryProfile(
            _integer(geometry["width_address"]),
            _integer(geometry["height_address"]),
            tuple(anchors),
            tuple(_text(value) for value in _list(geometry["evidence_ids"], 1, 32)),
        ),
    )
