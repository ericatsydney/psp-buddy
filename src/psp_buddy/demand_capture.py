"""On-demand PNG capture by the existing launch-bound observation controller."""

import asyncio
import base64
import binascii
import hashlib
import io
import json
import math
from datetime import UTC, datetime
from typing import Any

from PIL import Image, UnidentifiedImageError

from .backup import _safe_path
from .debugger import DebuggerAdapter
from .launch import LaunchSession

MAX_PNG_BYTES = 4 * 1024 * 1024
MAX_PIXELS = 8_388_608
PNG_PREFIX = 'data:image/png;base64,'


def decode_render_png(response: dict[str, object]) -> tuple[bytes, tuple[int, int]]:
    """Reject raw buffers and malformed images before storing any accepted evidence."""
    uri = response.get('uri')
    if (not isinstance(uri, str) or not uri.startswith(PNG_PREFIX)
            or len(uri) > len(PNG_PREFIX) + 4 * ((MAX_PNG_BYTES + 2) // 3)):
        raise ValueError('bounded PNG URI required')
    try:
        data = base64.b64decode(uri[len(PNG_PREFIX):], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError('invalid PNG base64') from exc
    if len(data) > MAX_PNG_BYTES or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('invalid PNG payload')
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            if (image.format != 'PNG' or getattr(image, 'n_frames', 1) != 1
                    or not 1 <= width <= 4096 or not 1 <= height <= 4096
                    or width * height > MAX_PIXELS):
                raise ValueError('unsupported PNG dimensions or format')
            if (type(response.get('width')) is not int or type(response.get('height')) is not int
                    or response['width'] != width or response['height'] != height):
                raise ValueError('PNG dimensions disagree with protocol')
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            extrema = [band.getextrema() for band in image.convert('RGB').split()]
            if all(isinstance(pair, tuple) and pair[0] == pair[1] for pair in extrema):
                raise ValueError('blank PNG capture')
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValueError('invalid PNG image') from exc
    return data, (width, height)


class DemandCapture:
    """No autonomous polling; each explicit demand acquires one new render image.

    PNG URI fixes encoding only. Backend download failures disable this service;
    no output framebuffer fallback, reconnect, game input or emulator closure.
    """

    def __init__(self, session: LaunchSession, adapter: DebuggerAdapter) -> None:
        if type(session) is not LaunchSession or type(adapter) is not DebuggerAdapter:
            raise ValueError('capture requires a launch-bound session and adapter')
        if adapter._assert_bound != session.assert_bound:
            raise ValueError('adapter is not bound to this launch session')
        if session.receipt is not session._prepared.receipt:
            raise ValueError('capture requires the original launch receipt')
        session.assert_bound()
        self._session = session
        self._adapter = adapter
        self._lock = asyncio.Lock()
        self._sequence = 0
        self._disabled = False
        self.root = session.receipt.snapshot_root.parent / 'capture-evidence'
        _safe_path(self.root)
        self.root.mkdir(exist_ok=False)

    async def capture(self, reason: str, *, timeout_seconds: float = 10) -> dict[str, Any]:
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 512:
            raise ValueError('bounded nonempty visual reason required')
        if (isinstance(timeout_seconds, bool) or not math.isfinite(timeout_seconds)
                or not 0 < timeout_seconds <= 30):
            raise ValueError('capture timeout must be finite, positive and at most30seconds')
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        async with asyncio.timeout_at(deadline):
            return await self._capture(reason, deadline)

    async def _capture(self, reason: str, deadline: float) -> dict[str, Any]:
        async with self._lock:
            if self._disabled:
                raise RuntimeError('capture disabled; use a fresh protected session')
            loop = asyncio.get_running_loop()

            def check_deadline() -> None:
                if loop.time() >= deadline:
                    raise TimeoutError('capture deadline expired')

            try:
                async with asyncio.timeout_at(deadline):
                    self._session.assert_bound()
                    check_deadline()
                    if (self._adapter._assert_bound != self._session.assert_bound
                            or self._adapter.uncertain):
                        raise ValueError('capture adapter binding or state changed')
                    if self._session.receipt is not self._session._prepared.receipt:
                        raise ValueError('capture launch receipt changed')
                    requested_at = datetime.now(UTC).isoformat()
                    async with self._adapter.observation_pause() as prior_status:
                        response = await self._adapter.read_render_png()
                        captured_at = datetime.now(UTC).isoformat()
                        data, size = decode_render_png(response)
                        check_deadline()
                    # observation_pause has completed its restoration before evidence publication.
                    pause_after = self._adapter.pause_status
                    if pause_after is None or self._adapter.uncertain:
                        raise RuntimeError('capture restoration outcome unknown')
                    self._session.assert_bound()
                    check_deadline()
                    _safe_path(self.root)
                    sequence = self._sequence + 1
                    image_path = self.root / f'capture-{sequence:04d}.png'
                    metadata_path = self.root / f'capture-{sequence:04d}.json'
                    result: dict[str, Any] = {
                        'trial_id': self._session.receipt.trial_id,
                        'game_id': self._session.config.game_id,
                        'sequence': sequence, 'reason': reason,
                        'requested_at': requested_at, 'captured_at': captured_at,
                        'completed_at': datetime.now(UTC).isoformat(),
                        'source': 'gpu.buffer.renderColor', 'encoding': 'PNG URI',
                        'path': str(image_path), 'metadata_path': str(metadata_path),
                        'sha256': hashlib.sha256(data).hexdigest(), 'size': list(size),
                        'pause_before': list(prior_status), 'pause_after': pause_after,
                        'timing': 'render acquisition; no atomic RAM snapshot claimed',
                    }
                    with image_path.open('xb') as image_file:
                        image_file.write(data)
                    check_deadline()
                    with metadata_path.open('x', encoding='utf-8') as metadata_file:
                        json.dump(result, metadata_file, indent=2)
                    check_deadline()
                    self._sequence = sequence
                    return result
            except BaseException:
                self._disabled = True
                raise
