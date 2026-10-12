"""Conservative evidence-bound screen landmarks; never tactical observations."""

import hashlib
import io
import math
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from .capture import CapturedFrame
from .models import Screen

Box = tuple[int, int, int, int]


@dataclass(frozen=True)
class ScreenSignature:
    label: str
    screen: Screen
    game_id: str
    size: tuple[int, int]
    landmarks: tuple[tuple[Box, bytes], ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (not isinstance(self.label, str) or not self.label.strip()
                or not isinstance(self.game_id, str) or not self.game_id.strip()
                or not isinstance(self.screen, Screen) or self.screen is Screen.UNKNOWN
                or not isinstance(self.size, tuple) or len(self.size) != 2
                or any(type(n) is not int or n <= 0 for n in self.size)
                or self.size[0] * self.size[1] > 16_777_216
                or not isinstance(self.evidence_ids, tuple) or not self.evidence_ids
                or any(not isinstance(e, str) or not e.strip() for e in self.evidence_ids)
                or not isinstance(self.landmarks, tuple) or not 2 <= len(self.landmarks) <= 16):
            raise ValueError("invalid signature identity, evidence or landmarks")
        seen: list[Box] = []
        for box, pixels in self.landmarks:
            if (not isinstance(box, tuple) or len(box) != 4
                    or any(type(n) is not int for n in box)
                    or not 0 <= box[0] < box[2] <= self.size[0]
                    or not 0 <= box[1] < box[3] <= self.size[1]
                    or not isinstance(pixels, bytes)
                    or len(pixels) != (box[2] - box[0]) * (box[3] - box[1]) * 3):
                raise ValueError("invalid landmark bytes or dimensions")
            if any(max(prior[0], box[0]) < min(prior[2], box[2])
                   and max(prior[1], box[1]) < min(prior[3], box[3]) for prior in seen):
                raise ValueError("overlapping landmarks")
            if all(len(set(pixels[channel::3])) == 1 for channel in range(3)):
                raise ValueError("uniform landmark cannot discriminate screens")
            seen.append(box)


@dataclass(frozen=True)
class RecognizedScreen:
    screen: Screen
    label: str | None
    sequence: int
    frame_sha256: str
    evidence_ids: tuple[str, ...]


def _image(frame: CapturedFrame) -> Image.Image:
    if (type(frame.sequence) is not int or frame.sequence <= 0
            or any(not isinstance(value, str) or not value.strip()
                   for value in (frame.game_id, frame.trial_id))
            or not isinstance(frame.encoded_bytes, bytes)
            or len(frame.encoded_bytes) > 32 * 1024 * 1024
            or hashlib.sha256(frame.encoded_bytes).hexdigest() != frame.sha256):
        raise ValueError("invalid frame identity, digest or sequence")
    if (len(frame.size) != 2 or any(type(n) is not int or n <= 0 for n in frame.size)
            or frame.size[0] * frame.size[1] > 16_777_216):
        raise ValueError("invalid frame dimensions")
    try:
        with Image.open(io.BytesIO(frame.encoded_bytes)) as image:
            if image.size != frame.size or image.format not in ("PNG", "JPEG"):
                raise ValueError("frame dimensions or format mismatch")
            image.load()
            return image.convert("RGB")
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError("invalid frame image") from exc


def signature_from_frame(frame: CapturedFrame, label: str, screen: Screen,
                         boxes: tuple[Box, ...], evidence_ids: tuple[str, ...]
                         ) -> ScreenSignature:
    if (not isinstance(label, str) or not label.strip() or screen is Screen.UNKNOWN
            or not isinstance(screen, Screen) or not isinstance(evidence_ids, tuple)
            or not evidence_ids or any(not isinstance(e, str) or not e.strip()
                                       for e in evidence_ids)
            or not isinstance(boxes, tuple) or not 2 <= len(boxes) <= 16):
        raise ValueError("reviewed label, screen, evidence and multiple landmarks required")
    image = _image(frame)
    landmarks: list[tuple[Box, bytes]] = []
    for box in boxes:
        if (not isinstance(box, tuple) or len(box) != 4
                or any(type(n) is not int for n in box)
                or not 0 <= box[0] < box[2] <= frame.size[0]
                or not 0 <= box[1] < box[3] <= frame.size[1]):
            raise ValueError("landmark outside frame bounds")
        for prior, _ in landmarks:
            if (max(prior[0], box[0]) < min(prior[2], box[2])
                    and max(prior[1], box[1]) < min(prior[3], box[3])):
                raise ValueError("overlapping landmarks")
        crop = image.crop(box)
        if all(band.getextrema()[0] == band.getextrema()[1] for band in crop.split()):
            raise ValueError("uniform landmark cannot discriminate screens")
        landmarks.append((box, crop.tobytes()))
    return ScreenSignature(label, screen, frame.game_id, frame.size,
                           tuple(landmarks), evidence_ids)


class ScreenRecognizer:
    def __init__(self, game_id: str, trial_id: str, size: tuple[int, int],
                 signatures: tuple[ScreenSignature, ...], *, max_mean_error: float = 2) -> None:
        if (any(not isinstance(value, str) or not value.strip() for value in (game_id, trial_id))
                or not isinstance(signatures, tuple)
                or not 1 <= len(signatures) <= 64 or not math.isfinite(max_mean_error)
                or not 0 <= max_mean_error <= 4):
            raise ValueError("invalid recognizer identity, signatures or tolerance")
        for signature in signatures:
            if not isinstance(signature, ScreenSignature):
                raise ValueError("screen signature required")
            if signature.game_id != game_id or signature.size != size:
                raise ValueError("signature identity or dimensions mismatch")
        self._game_id, self._trial_id, self._size = game_id, trial_id, size
        self._signatures = signatures
        self._tolerance = max_mean_error
        self._sequence = 0

    def recognize(self, frame: CapturedFrame) -> RecognizedScreen:
        if (frame.game_id != self._game_id or frame.trial_id != self._trial_id
                or frame.size != self._size):
            raise ValueError("frame identity or dimensions mismatch")
        image = _image(frame)
        if frame.sequence <= self._sequence:
            raise ValueError("stale frame sequence")
        self._sequence = frame.sequence
        matches = []
        for signature in self._signatures:
            if all(sum(abs(a - b) for a, b in zip(image.crop(box).tobytes(), pixels,
                                                strict=True)) / len(pixels) <= self._tolerance
                   for box, pixels in signature.landmarks):
                matches.append(signature)
        if len(matches) != 1:
            return RecognizedScreen(Screen.UNKNOWN, None, frame.sequence, frame.sha256, ())
        match = matches[0]
        return RecognizedScreen(match.screen, match.label, frame.sequence, frame.sha256,
                                match.evidence_ids)
