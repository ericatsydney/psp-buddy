"""Bounded read-only collection of owned PPSSPP screenshot output."""

import asyncio
import hashlib
import io
import math
import os
import re
import stat
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .backup import _safe_path
from .launch import LaunchSession

MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_DIRECTORY_FILES = 4096
POLL_SECONDS = .025


@dataclass(frozen=True)
class CapturedFrame:
    encoded_bytes: bytes
    sha256: str
    sequence: int
    size: tuple[int, int]
    game_id: str
    trial_id: str
    path: Path


class ScreenshotCapture:
    """One collector per launch; uncertain completion permanently disables reuse."""

    def __init__(self, session: LaunchSession, expected_size: tuple[int, int]) -> None:
        if type(session) is not LaunchSession:
            raise ValueError("capture requires an issuer-created LaunchSession")
        session.assert_bound()
        if (len(expected_size) != 2 or any(type(n) is not int or n <= 0 for n in expected_size)
                or expected_size[0] * expected_size[1] > 16_777_216):
            raise ValueError("invalid expected screenshot size")
        self._session = session
        self._root = session.memstick_root / 'PSP' / 'SCREENSHOT'
        self._size = expected_size
        self._pattern = re.compile(re.escape(session.config.game_id) + r'_\d+\.(?:jpg|png)', re.I)
        self._sequence = 0
        self._uncertain = False
        self._lock = asyncio.Lock()

    def _inventory(self, *, allow_unstable: bool = False
                   ) -> dict[str, tuple[int, int, int, int, str]]:
        _safe_path(self._root)
        if not self._root.exists():
            return {}
        if not self._root.is_dir():
            raise ValueError('screenshot directory is not a directory')
        result: dict[str, tuple[int, int, int, int, str]] = {}
        for path in self._root.iterdir():
            if len(result) >= MAX_DIRECTORY_FILES:
                raise ValueError('screenshot inventory exceeds limit')
            _safe_path(path)
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError('unsafe screenshot file or hardlink')
            data = self._read(path)
            if data is None and not allow_unstable:
                raise ValueError('screenshot inventory changed while reading')
            result[path.name] = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
                                 hashlib.sha256(data).hexdigest() if data is not None else '')
        return result

    def _read(self, path: Path) -> bytes | None:
        _safe_path(path)
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError('unsafe screenshot file or hardlink')
        if before.st_size > MAX_IMAGE_BYTES:
            raise ValueError('screenshot exceeds byte limit')
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise ValueError('screenshot file identity changed')
            data = stream.read(MAX_IMAGE_BYTES + 1)
            after = os.fstat(stream.fileno())
        _safe_path(path)
        current = path.lstat()
        if (current.st_nlink != 1 or not stat.S_ISREG(current.st_mode)
                or len(data) > MAX_IMAGE_BYTES):
            raise ValueError('unsafe screenshot file or byte limit')
        def signature(s: os.stat_result) -> tuple[int, int, int, int]:
            return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
        if not signature(before) == signature(opened) == signature(after) == signature(current):
            return None
        return data

    def _decode(self, data: bytes) -> bool:
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ('JPEG', 'PNG'):
                    raise ValueError('unsupported screenshot format')
                if image.size != self._size:
                    raise ValueError('wrong screenshot dimensions')
                image.load()
                extrema = [band.getextrema() for band in image.convert('RGB').split()]
                if all(isinstance(pair, tuple) and pair[0] == pair[1] for pair in extrema):
                    raise ValueError('blank screenshot')
                return True
        except (UnidentifiedImageError, OSError):
            return False  # A partial encoder write may become complete within this request.

    async def capture(self, trigger: Callable[[], Awaitable[None]], *,
                      timeout_seconds: float) -> CapturedFrame:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError('capture timeout must be finite and positive')
        async with self._lock:
            if self._uncertain:
                raise ValueError('capture completion uncertain; create a fresh launch collector')
            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout_seconds

            def check_deadline() -> None:
                # Synchronous Windows inspection/read calls cannot yield to asyncio's timer.
                if loop.time() >= deadline:
                    raise TimeoutError('screenshot deadline expired')

            try:
                async with asyncio.timeout_at(deadline):
                    self._session.assert_bound()
                    check_deadline()
                    baseline = self._inventory()
                    check_deadline()
                    self._session.assert_bound()
                    check_deadline()
                    await trigger()
                    check_deadline()
                    previous: tuple[str, bytes] | None = None
                    while True:
                        self._session.assert_bound()
                        check_deadline()
                        current = self._inventory(allow_unstable=True)
                        check_deadline()
                        if any(current.get(name) != value for name, value in baseline.items()):
                            raise ValueError('baseline screenshot overwritten or removed')
                        names = [name for name in current if name not in baseline]
                        if len(names) > 1:
                            raise ValueError('ambiguous new screenshot output')
                        if names:
                            name = names[0]
                            if not self._pattern.fullmatch(name):
                                raise ValueError('screenshot filename does not match game identity')
                            path = self._root / name
                            data = self._read(path)
                            if data is not None and previous == (name, data) and self._decode(data):
                                self._session.assert_bound()
                                if self._inventory() != current:
                                    raise ValueError('screenshot output changed before acceptance')
                                check_deadline()
                                self._sequence += 1
                                return CapturedFrame(data, hashlib.sha256(data).hexdigest(),
                                                     self._sequence, self._size,
                                                     self._session.config.game_id,
                                                     self._session.receipt.trial_id, path)
                            previous = (name, data) if data is not None else None
                        await asyncio.sleep(POLL_SECONDS)
            except BaseException:
                self._uncertain = True
                raise
