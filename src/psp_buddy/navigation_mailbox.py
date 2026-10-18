"""Single-controller, bounded local capture mailbox. No emulator connection."""

import asyncio
import json
import os
import re
import stat
from collections.abc import Awaitable, Callable
from pathlib import Path
from uuid import uuid4

NavigationHandler = Callable[[str, dict[str, object]], Awaitable[dict[str, object]]]


class NavigationRefused(ValueError):
    """A request refused before any input was sent; the session stays usable."""


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _safe_directory(path: Path) -> None:
    for component in (path, *path.parents):
        info = component.lstat()
        if not stat.S_ISDIR(info.st_mode) or component.is_symlink() or (
            getattr(info, "st_file_attributes", 0) & 0x400
        ):
            raise ValueError("mailbox directory must not contain links/reparse points")


class NavigationMailbox:
    """Create a fresh mailbox, then let the protected controller call serve_once."""

    def __init__(self, handler: NavigationHandler, trial_id: str, root: Path) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", trial_id):
            raise ValueError("invalid trial ID")
        root = root.absolute()
        _safe_directory(root.parent)
        root.mkdir(exist_ok=False)
        self.root = root
        self.trial_id = trial_id
        self._handler = handler
        self._lock = asyncio.Lock()
        self._seen: set[str] = set()
        self._disabled = False

    @property
    def disabled(self) -> bool:
        return self._disabled

    async def serve_once(self) -> bool:
        async with self._lock:
            _safe_directory(self.root)
            path = self.root / "nav-request.json"
            try:
                info = path.lstat()
            except FileNotFoundError:
                return False
            # The bridge publishes with link-then-unlink for atomic no-clobber.
            # Do not consume the brief two-link publication window.
            if stat.S_ISREG(info.st_mode) and info.st_nlink == 2:
                for pending in self.root.glob(".request-*.tmp"):
                    try:
                        candidate = pending.lstat()
                    except FileNotFoundError:
                        # Producer may finish publication after directory enumeration.
                        continue
                    if (candidate.st_dev, candidate.st_ino) == (info.st_dev, info.st_ino):
                        return False
                # Producer may also finish before enumeration. Revalidate the
                # request instead of treating the old two-link stat as current.
                current = path.lstat()
                if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                    raise ValueError("mailbox request changed during publication")
                info = current
            if (
                not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_nlink != 1
                or getattr(info, "st_file_attributes", 0) & 0x400 or info.st_size > 16384
            ):
                raise ValueError("unsafe or oversized mailbox request")
            with path.open("rb") as stream:
                opened = os.fstat(stream.fileno())
                if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                    raise ValueError("mailbox request changed")
                raw = stream.read(16385)
            try:
                data: object = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
            except (UnicodeError, ValueError) as exc:
                raise ValueError("invalid mailbox JSON") from exc
            if len(raw) > 16384 or not isinstance(data, dict):
                raise ValueError("invalid mailbox request")
            identity = data.get("request_id")
            if not isinstance(identity, str) or not re.fullmatch(r"[0-9a-f]{32}", identity):
                raise ValueError("invalid request ID")
            response = self.root / f"nav-response-{identity}.json"
            if identity in self._seen or response.exists() or response.is_symlink():
                raise ValueError("replay/out-of-order request")
            if len(self._seen) >= 256:
                raise ValueError("mailbox history exhausted; start a fresh protected session")
            self._seen.add(identity)
            payload: dict[str, object] = {"trial_id": self.trial_id, "request_id": identity}
            operation = data.get("operation")
            arguments = data.get("arguments")
            if set(data) != {"trial_id", "request_id", "operation", "arguments"} or (
                data.get("trial_id") != self.trial_id
                or operation not in ("press", "verify", "observe", "dump")
                or not isinstance(arguments, dict)
            ):
                self._disabled = True
                payload["error"] = "invalid navigation request schema or trial"
            elif self._disabled:
                payload["error"] = "navigation mailbox disabled after failure"
            else:
                try:
                    # The handler includes its own whole-investigation lock acquisition.
                    async with asyncio.timeout(10 if operation == "press" else 60):
                        payload["result"] = await self._handler(str(operation), arguments)
                except NavigationRefused as exc:
                    payload["error"] = f"refused: {str(exc)[:200]}"
                except Exception:
                    self._disabled = True
                    payload["error"] = "protected navigation failed; further requests disabled"
            encoded = json.dumps(payload, allow_nan=False).encode("utf-8")
            if len(encoded) > 16384:
                self._disabled = True
                raise ValueError("navigation response exceeds metadata limit")
            temporary = self.root / f".response-{uuid4().hex}.tmp"
            try:
                with temporary.open("xb") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
                if os.name == "nt":
                    # Windows rename is atomic and refuses an existing destination.
                    os.rename(temporary, response)
                else:
                    os.link(temporary, response)
            finally:
                temporary.unlink(missing_ok=True)
            current = path.lstat()
            if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                self._disabled = True
                raise ValueError("mailbox request replaced while processing")
            path.unlink()
            return True
