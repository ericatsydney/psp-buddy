"""Explicitly opted-in, freshly protected identity and pause checks; no battle inputs."""

import asyncio
import json
import os
from pathlib import Path

import pytest

from psp_buddy.config import RunConfig
from psp_buddy.debugger import DebuggerAdapter
from psp_buddy.launch import Launcher

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("PSP_BUDDY_LIVE") != "1", reason="live opt-in required"),
]


def test_runtime_identity_and_pause_cleanup():
    config_path = os.environ.get("PSP_BUDDY_CONFIG")
    state_filename = os.environ.get("PSP_BUDDY_STATE")
    if not config_path or not state_filename:
        pytest.fail("explicit PSP_BUDDY_CONFIG and PSP_BUDDY_STATE are required")
    config = RunConfig.from_dict(json.loads(Path(config_path).read_text(encoding="utf-8")))
    launcher = Launcher()
    prepared = launcher.prepare(
        config, state_filename=state_filename,
        system_root=config.portable_savedata.parent / "SYSTEM",
    )
    session = launcher.start(prepared)

    async def exercise():
        adapter = await DebuggerAdapter.connect_live(session)
        try:
            before = await adapter.status()
            async with adapter.observation_pause():
                stepping, paused = await adapter.status()
                assert stepping or paused
            after = await adapter.status()
            assert after == before
            assert not adapter.uncertain
            evidence = session.receipt.snapshot_root.parent / "evidence"
            evidence.mkdir()
            (evidence / "debugger-status.json").write_text(
                json.dumps({"before": before, "after": after}), encoding="utf-8",
            )
        finally:
            await adapter.close()

    try:
        asyncio.run(exercise())
    finally:
        try:
            session.close()
        finally:
            session.verify_sources()
