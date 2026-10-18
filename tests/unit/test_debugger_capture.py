import asyncio
import json

import pytest
from test_debugger import FakeTransport

from psp_buddy.debugger import DebuggerAdapter


class CaptureTransport(FakeTransport):
    async def send(self, message):
        data = json.loads(message)
        if (data["event"] == "gpu.buffer.renderColor"
                and data["event"] not in self.error | self.silent):
            self.sent.append(data)
            await self.messages.put({"event": data["event"], "ticket": data["ticket"],
                                     "uri": "data:image/png;base64,example"})
        else:
            await super().send(message)


def test_capture_requires_bound_current_task_observation_without_io():
    async def scenario():
        transport = CaptureTransport()
        adapter = DebuggerAdapter(transport)
        with pytest.raises(RuntimeError, match="observation"):
            await adapter.read_render_png()
        assert not transport.sent
        async with adapter.observation_pause():
            before = len(transport.sent)
            with pytest.raises(RuntimeError, match="bound"):
                await adapter.read_render_png()
            adapter._assert_bound = lambda: None
            with pytest.raises(RuntimeError, match="observation"):
                await asyncio.create_task(adapter.read_render_png())
            assert len(transport.sent) == before
    asyncio.run(scenario())


@pytest.mark.parametrize("stepping,paused", [(False, False), (True, False), (False, True)])
def test_capture_sends_render_uri_once_and_preserves_initial_state(stepping, paused):
    async def scenario():
        transport = CaptureTransport(stepping=stepping, paused=paused)
        adapter = DebuggerAdapter(transport)
        adapter._assert_bound = lambda: None
        async with adapter.observation_pause() as prior:
            assert prior == (stepping, paused)
            response = await adapter.read_render_png()
            assert response["uri"] == "data:image/png;base64,example"
        captures = [m for m in transport.sent if m["event"].startswith("gpu.")]
        assert len(captures) == 1
        assert captures[0] == {"event": "gpu.buffer.renderColor", "type": "uri",
                               "ticket": captures[0]["ticket"]}
        assert (transport.stepping, transport.paused) == (stepping, paused)
    asyncio.run(scenario())


def test_capture_checks_binding_at_actual_send_and_latches_failure():
    async def scenario():
        transport = CaptureTransport()
        adapter = DebuggerAdapter(transport)
        valid = True

        def assert_bound():
            if not valid:
                raise RuntimeError("binding changed")

        adapter._assert_bound = assert_bound
        async with adapter.observation_pause():
            await adapter._io_lock.acquire()

            def invalidate():
                nonlocal valid
                valid = False
                adapter._io_lock.release()

            asyncio.get_running_loop().call_soon(invalidate)
            with pytest.raises(RuntimeError, match="binding changed"):
                await adapter.read_render_png()
            assert adapter.uncertain
            assert adapter.pause_status is None
        assert not any(m["event"].startswith("gpu.") for m in transport.sent)
    asyncio.run(scenario())


def test_capture_rechecks_owned_scope_after_waiting_for_io():
    async def scenario():
        transport = CaptureTransport()
        adapter = DebuggerAdapter(transport)
        adapter._assert_bound = lambda: None
        async with adapter.observation_pause():
            await adapter._io_lock.acquire()

            def lose_scope():
                adapter._pause_owner = None
                adapter._io_lock.release()

            asyncio.get_running_loop().call_soon(lose_scope)
            with pytest.raises(RuntimeError, match="observation"):
                await adapter.read_render_png()
        assert not any(m["event"].startswith("gpu.") for m in transport.sent)
    asyncio.run(scenario())


@pytest.mark.parametrize("fault", ["transport", "protocol", "malformed", "timeout"])
def test_capture_failure_latches_without_retry_or_resume(fault):
    async def scenario():
        transport = CaptureTransport()
        adapter = DebuggerAdapter(transport, timeout_seconds=0.02)
        adapter._assert_bound = lambda: None
        async with adapter.observation_pause():
            if fault == "transport":
                transport.disconnected = True
            elif fault == "protocol":
                transport.error.add("gpu.buffer.renderColor")
            elif fault == "timeout":
                transport.silent.add("gpu.buffer.renderColor")
            else:
                await transport.messages.put([])
            with pytest.raises((TimeoutError, ConnectionError, RuntimeError, ValueError)):
                await adapter.read_render_png()
            assert adapter.uncertain
            assert adapter.pause_status is None
            with pytest.raises(RuntimeError):
                await adapter.read_render_png()
        assert len([m for m in transport.sent if m["event"].startswith("gpu.")]) == 1
        assert not any(m["event"] == "cpu.resume" for m in transport.sent)
    asyncio.run(scenario())


def test_capture_cancellation_latches_and_does_not_resume():
    async def scenario():
        transport = CaptureTransport()
        adapter = DebuggerAdapter(transport)
        adapter._assert_bound = lambda: None

        async def capture():
            async with adapter.observation_pause():
                transport.silent.add("gpu.buffer.renderColor")
                await adapter.read_render_png()

        task = asyncio.create_task(capture())
        while not any(m["event"].startswith("gpu.") for m in transport.sent):
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert adapter.uncertain
        assert adapter.pause_status is None
        assert not any(m["event"] == "cpu.resume" for m in transport.sent)
    asyncio.run(scenario())


def test_observation_surfaces_restoration_failure_after_successful_capture():
    async def scenario():
        transport = CaptureTransport()
        adapter = DebuggerAdapter(transport)
        adapter._assert_bound = lambda: None
        with pytest.raises(RuntimeError, match="denied"):
            async with adapter.observation_pause():
                await adapter.read_render_png()
                transport.error.add("cpu.resume")
        assert adapter.uncertain
        assert adapter.pause_status is None
    asyncio.run(scenario())
