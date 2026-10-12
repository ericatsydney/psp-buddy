import hashlib
import io
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from psp_buddy.capture import CapturedFrame
from psp_buddy.models import Screen
from psp_buddy.recognition import ScreenRecognizer, ScreenSignature, signature_from_frame


def frame(color: str = "green", sequence: int = 1) -> CapturedFrame:
    image = Image.new("RGB", (20, 12), color)
    image.paste("white", (2, 2, 7, 5))
    image.paste("black", (12, 7, 18, 10))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    data = stream.getvalue()
    return CapturedFrame(data, hashlib.sha256(data).hexdigest(), sequence,
                         image.size, "test-game", "trial", Path("unused.png"))


def signature(source: CapturedFrame | None = None, label: str = "mech") -> ScreenSignature:
    return signature_from_frame(source or frame(), label, Screen.MENU,
                                ((0, 0, 9, 6), (10, 6, 20, 12)), ("visible-mech",))


def test_recognizes_multiple_landmarks_without_tactical_claim():
    result = ScreenRecognizer("test-game", "trial", (20, 12), (signature(),)).recognize(frame())
    assert result.screen is Screen.MENU
    assert result.label == "mech"
    assert result.evidence_ids == ("visible-mech",)
    assert result.sequence == 1
    assert result.frame_sha256 == frame().sha256


def test_unfamiliar_screen_is_unknown():
    result = ScreenRecognizer("test-game", "trial", (20, 12), (signature(),)).recognize(
        frame("red"))
    assert result.screen is Screen.UNKNOWN
    assert result.label is None


def test_ambiguous_match_is_unknown():
    recognizer = ScreenRecognizer("test-game", "trial", (20, 12),
                                  (signature(), signature(label="pilot")))
    assert recognizer.recognize(frame()).screen is Screen.UNKNOWN


def test_stale_sequence_is_rejected_even_after_unknown_screen():
    recognizer = ScreenRecognizer("test-game", "trial", (20, 12), (signature(),))
    recognizer.recognize(frame("red"))
    with pytest.raises(ValueError, match="sequence"):
        recognizer.recognize(frame())


@pytest.mark.parametrize("field,value", [
    ("game_id", "other"), ("trial_id", "other"), ("size", (30, 12)),
    ("sha256", "0" * 64), ("encoded_bytes", b"broken"), ("sequence", True),
])
def test_invalid_frame_rejected(field: str, value: object):
    bad = replace(frame(), **{field: value})
    recognizer = ScreenRecognizer("test-game", "trial", (20, 12), (signature(),))
    with pytest.raises(ValueError):
        recognizer.recognize(bad)


@pytest.mark.parametrize("boxes,evidence", [
    (((0, 0, 9, 6),), ("e",)),
    (((0, 0, 9, 6), (0, 0, 9, 6)), ("e",)),
    (((0, 0, 9, 6), (5, 5, 21, 12)), ("e",)),
    (((0, 0, 9, 6), (10, 6, 20, 12)), ()),
])
def test_invalid_signature_rejected(boxes, evidence):
    with pytest.raises(ValueError):
        signature_from_frame(frame(), "mech", Screen.MENU, boxes, evidence)


def test_uniform_landmarks_rejected():
    with pytest.raises(ValueError, match="uniform"):
        signature_from_frame(frame(), "mech", Screen.MENU,
                             ((0, 0, 2, 2), (8, 6, 10, 8)), ("e",))


def test_unreviewed_tolerance_rejected():
    with pytest.raises(ValueError):
        ScreenRecognizer("test-game", "trial", (20, 12), (signature(),), max_mean_error=255)


@pytest.mark.parametrize("field,value", [
    ("evidence_ids", ("",)), ("screen", "menu"), ("label", " "),
    ("landmarks", (((0, 0, 2, 2), b"\x00" * 12), ((8, 6, 10, 8), b"\x00" * 12))),
])
def test_direct_signature_cannot_bypass_validation(field: str, value: object):
    with pytest.raises(ValueError):
        forged = replace(signature(), **{field: value})
        ScreenRecognizer("test-game", "trial", (20, 12), (forged,))


def test_one_matching_landmark_is_insufficient():
    source = frame()
    image = Image.open(io.BytesIO(source.encoded_bytes)).convert("RGB")
    image.paste("blue", (10, 6, 20, 12))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    data = stream.getvalue()
    changed = replace(source, encoded_bytes=data, sha256=hashlib.sha256(data).hexdigest())
    result = ScreenRecognizer("test-game", "trial", (20, 12), (signature(),)).recognize(changed)
    assert result.screen is Screen.UNKNOWN


@pytest.mark.parametrize("bad", [" ", 1])
def test_invalid_trial_identity_rejected(bad):
    with pytest.raises(ValueError):
        ScreenRecognizer("test-game", bad, (20, 12), (signature(),))


@pytest.mark.parametrize("error,expected", [(2, Screen.MENU), (3, Screen.UNKNOWN)])
def test_landmark_error_boundary(error: int, expected: Screen):
    image = Image.new("RGB", (20, 12), (100, 100, 100))
    image.paste((120, 120, 120), (2, 2, 7, 5))
    image.paste((120, 120, 120), (12, 7, 18, 10))
    def encoded(image):
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        data = stream.getvalue()
        return replace(frame(), encoded_bytes=data, sha256=hashlib.sha256(data).hexdigest())
    reference = encoded(image)
    pixels = image.load()
    for y in range(6, 12):
        for x in range(10, 20):
            pixels[x, y] = tuple(channel + error for channel in pixels[x, y])
    recognizer = ScreenRecognizer("test-game", "trial", (20, 12), (signature(reference),))
    assert recognizer.recognize(encoded(image)).screen is expected
