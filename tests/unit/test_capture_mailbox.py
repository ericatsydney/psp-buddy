import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

from psp_buddy.capture_mailbox import CaptureMailbox


class Capture:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[str] = []
        self.fail = fail

    async def capture(self, reason: str, *, timeout_seconds: float = 10) -> dict[str, object]:
        self.calls.append(reason)
        if self.fail:
            raise RuntimeError("capture failed")
        await asyncio.sleep(0)
        return {"path": "image.png", "sha256": "a" * 64, "trial_id": "trial-1"}


def request(root: Path, **overrides: object) -> str:
    data = {"trial_id": "trial-1", "request_id": uuid4().hex, "reason": "new menu"}
    data.update(overrides)
    (root / "capture-request.json").write_text(json.dumps(data), encoding="utf-8")
    return str(data["request_id"])


def response(root: Path, identity: str) -> dict[str, object]:
    return json.loads((root / f"capture-response-{identity}.json").read_text())  # type: ignore[no-any-return]


def test_demand_only_and_response(tmp_path: Path) -> None:
    async def run() -> None:
        capture = Capture()
        root = tmp_path / "mailbox"
        mailbox = CaptureMailbox(capture, "trial-1", root)
        assert not await mailbox.serve_once()
        assert capture.calls == []
        identity = request(root)
        assert await mailbox.serve_once()
        assert capture.calls == ["new menu"]
        assert response(root, identity)["result"] == {
            "path": "image.png", "sha256": "a" * 64, "trial_id": "trial-1"
        }
        assert not (root / "capture-request.json").exists()
    asyncio.run(run())


@pytest.mark.parametrize("overrides", [
    {"trial_id": "wrong"}, {"reason": ""}, {"reason": "a" * 513}, {"extra": 1},
])
def test_rejects_invalid_request_without_capture(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    async def run() -> None:
        capture = Capture()
        root = tmp_path / "mailbox"
        mailbox = CaptureMailbox(capture, "trial-1", root)
        identity = request(root, **overrides)
        assert await mailbox.serve_once()
        assert "error" in response(root, identity)
        assert capture.calls == []
        assert mailbox.disabled
    asyncio.run(run())


@pytest.mark.parametrize("raw", [
    b"x" * 4097, b"\xff", b'{"request_id":"a","request_id":"b"}', b"[]"
])
def test_malformed_requests_raise(tmp_path: Path, raw: bytes) -> None:
    async def run() -> None:
        capture = Capture()
        root = tmp_path / "mailbox"
        mailbox = CaptureMailbox(capture, "trial-1", root)
        (root / "capture-request.json").write_bytes(raw)
        with pytest.raises(ValueError):
            await mailbox.serve_once()
        assert capture.calls == []
    asyncio.run(run())


def test_replay_is_rejected_without_overwriting_result(tmp_path: Path) -> None:
    async def run() -> None:
        capture = Capture()
        root = tmp_path / "mailbox"
        mailbox = CaptureMailbox(capture, "trial-1", root)
        identity = request(root)
        await mailbox.serve_once()
        previous = response(root, identity)
        request(root, request_id=identity)
        with pytest.raises(ValueError, match="replay"):
            await mailbox.serve_once()
        assert len(capture.calls) == 1
        assert response(root, identity) == previous
    asyncio.run(run())


def test_capture_failure_disables_future_calls(tmp_path: Path) -> None:
    async def run() -> None:
        capture = Capture(fail=True)
        root = tmp_path / "mailbox"
        mailbox = CaptureMailbox(capture, "trial-1", root)
        first = request(root)
        await mailbox.serve_once()
        assert "error" in response(root, first)
        second = request(root)
        await mailbox.serve_once()
        assert "disabled" in str(response(root, second)["error"])
        assert len(capture.calls) == 1
    asyncio.run(run())


def test_refuses_existing_directory(tmp_path: Path) -> None:
    with pytest.raises((ValueError, FileExistsError)):
        CaptureMailbox(Capture(), "trial-1", tmp_path)


def test_concurrent_serves_capture_once(tmp_path: Path) -> None:
    async def run() -> None:
        capture = Capture()
        root = tmp_path / "mailbox"
        mailbox = CaptureMailbox(capture, "trial-1", root)
        request(root)
        served = await asyncio.gather(mailbox.serve_once(), mailbox.serve_once())
        assert sorted(served) == [False, True]
        assert len(capture.calls) == 1
    asyncio.run(run())


def test_hardlinked_request_is_never_captured(tmp_path: Path) -> None:
    async def hostile() -> None:
        capture = Capture()
        root = tmp_path / "hostile"
        mailbox = CaptureMailbox(capture, "trial-1", root)
        request(root)
        (tmp_path / "external").hardlink_to(root / "capture-request.json")
        with pytest.raises(ValueError, match="unsafe"):
            await mailbox.serve_once()
        assert capture.calls == []
    asyncio.run(hostile())


def test_producer_finishing_publication_after_stat_is_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        capture = Capture()
        root = tmp_path / "mailbox"
        mailbox = CaptureMailbox(capture, "trial-1", root)
        identity = request(root)
        temporary = root / f".request-{identity}.tmp"
        temporary.hardlink_to(root / "capture-request.json")
        original = Path.glob

        def producer_finishes(path: Path, pattern: str) -> Iterator[Path]:
            if path == root:
                temporary.unlink(missing_ok=True)
            return original(path, pattern)

        monkeypatch.setattr(Path, "glob", producer_finishes)
        assert await mailbox.serve_once()
        assert capture.calls == ["new menu"]
        assert not mailbox.disabled
    asyncio.run(run())


def test_producer_unlinking_during_temporary_stat_is_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        capture = Capture()
        root = tmp_path / "mailbox"
        mailbox = CaptureMailbox(capture, "trial-1", root)
        identity = request(root)
        temporary = root / f".request-{identity}.tmp"
        temporary.hardlink_to(root / "capture-request.json")
        original = Path.glob

        def producer_finishes(path: Path, pattern: str) -> Iterator[Path]:
            candidates = list(original(path, pattern))
            if path == root:
                temporary.unlink(missing_ok=True)
            return iter(candidates)

        monkeypatch.setattr(Path, "glob", producer_finishes)
        assert await mailbox.serve_once()
        assert capture.calls == ["new menu"]
        assert not mailbox.disabled
    asyncio.run(run())
