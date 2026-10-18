# ruff: noqa: E501
import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest

from psp_buddy.navigation_mailbox import NavigationMailbox


def test_dispatch_and_terminal_failure(tmp_path: Path) -> None:
    async def run() -> None:
        calls = []
        async def handler(operation: str, arguments: dict[str, object]) -> dict[str, object]:
            calls.append((operation, arguments))
            if operation == "verify":
                raise RuntimeError("private C:/secret/path")
            return {"sequence": 1}
        box = NavigationMailbox(handler, "trial-1", tmp_path / "box")
        assert not await box.serve_once()
        for operation in ["press", "verify", "press"]:
            identity = uuid4().hex
            (box.root / "nav-request.json").write_text(json.dumps({"trial_id": "trial-1", "request_id": identity, "operation": operation, "arguments": {}}))
            assert await box.serve_once()
            result = json.loads((box.root / f"nav-response-{identity}.json").read_text())
            assert "private" not in json.dumps(result)
        assert [item[0] for item in calls] == ["press", "verify"]
        assert box.disabled
    asyncio.run(run())


def test_replay_and_wrong_trial(tmp_path: Path) -> None:
    async def run() -> None:
        calls = []
        async def handler(operation: str, arguments: dict[str, object]) -> dict[str, object]:
            calls.append(operation)
            return {}
        box = NavigationMailbox(handler, "trial-1", tmp_path / "box")
        identity = uuid4().hex
        data = {"trial_id": "wrong", "request_id": identity, "operation": "press", "arguments": {}}
        path = box.root / "nav-request.json"
        path.write_text(json.dumps(data))
        await box.serve_once()
        assert not calls
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="replay"):
            await box.serve_once()
    asyncio.run(run())


def test_refusal_is_reported_without_disabling(tmp_path: Path) -> None:
    from psp_buddy.navigation_mailbox import NavigationRefused

    async def run() -> None:
        async def handler(operation: str, arguments: dict[str, object]) -> dict[str, object]:
            if arguments.get("bad"):
                raise NavigationRefused("screenshot already used")
            return {"ok": True}
        box = NavigationMailbox(handler, "trial-1", tmp_path / "box")
        results = []
        for arguments in ({"bad": True}, {}):
            identity = uuid4().hex
            (box.root / "nav-request.json").write_text(json.dumps({"trial_id": "trial-1", "request_id": identity, "operation": "press", "arguments": arguments}))
            assert await box.serve_once()
            results.append(json.loads((box.root / f"nav-response-{identity}.json").read_text()))
        assert "screenshot already used" in results[0]["error"]
        assert results[1]["result"] == {"ok": True}
        assert not box.disabled
    asyncio.run(run())
