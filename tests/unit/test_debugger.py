import asyncio
import base64
import json

import pytest


class FakeTransport:
    def __init__(self, *, stepping=False, paused=False):
        self.stepping = stepping
        self.paused = paused
        self.buttons_down = set()
        self.sent = []
        self.messages = asyncio.Queue()
        self.silent = set()
        self.error = set()
        self.disconnected = False
        self.memory = b"abcd"

    async def send(self, message):
        data = json.loads(message)
        self.sent.append(data)
        event = data["event"]
        if event == "input.buttons.press":
            self.buttons_down.add(data["button"])
        if event == "input.buttons.send":
            self.buttons_down.difference_update(data["buttons"])
        if event in self.silent:
            return
        if event in self.error:
            await self.messages.put({"event": "error", "ticket": data["ticket"],
                                     "message": "denied"})
            return
        if event == "cpu.stepping":
            self.stepping = True
            await self.messages.put({"event": event})
            return
        if event == "cpu.resume":
            self.stepping = False
            await self.messages.put({"event": event})
            return
        response = {"event": event, "ticket": data["ticket"]}
        if event == "cpu.status":
            response.update(stepping=self.stepping, paused=self.paused)
        if event == "memory.read":
            response["base64"] = base64.b64encode(self.memory).decode()
        if event == "input.buttons.press":
            self.buttons_down.discard(data["button"])
        await self.messages.put(response)

    async def recv(self):
        if self.disconnected:
            raise ConnectionError("lost transport")
        return json.dumps(await self.messages.get())

    async def close(self):
        self.disconnected = True


def test_live_connection_is_disabled_before_any_io():
    from psp_buddy.debugger import DebuggerAdapter

    with pytest.raises(RuntimeError, match="trusted launch"):
        asyncio.run(DebuggerAdapter.connect_live("ws://127.0.0.1:27312/debugger"))


def test_ticket_correlation_ignores_unrelated_and_wrong_event():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        await transport.messages.put({"event": "cpu.status", "ticket": "other",
                                      "paused": True, "stepping": True})
        await transport.messages.put({"event": "unrelated", "ticket": "1"})
        adapter = DebuggerAdapter(transport)
        status = await adapter.status()
        assert status == (False, False)
        assert len(adapter.events) == 2
    asyncio.run(scenario())


@pytest.mark.parametrize("event,params", [
    ("memory.write", {"address": 0x08800000, "base64": "AA=="}),
    ("cpu.setReg", {"name": "pc", "value": 0}),
    ("cpu.evaluate", {"expression": "1"}),
    ("cpu.status", {"unexpected": True}),
    ("input.buttons.send", {"buttons": {"right": True}}),
    ("input.buttons.press", {"button": "home", "duration": 1}),
    ("input.buttons.press", {"button": "right", "duration": 0}),
    ("input.buttons.press", {"button": "right", "duration": True}),
    ("input.buttons.press", {"button": "right", "duration": 121}),
    ("input.buttons.press", {"button": "right", "duration": 31}),
    ("memory.read", {"address": 0x08800000, "size": 4, "replacements": False}),
    ("memory.read", {"address": -1, "size": 4}),
    ("memory.read", {"address": 0xFFFFFFFF, "size": 4}),
    ("memory.read", {"address": 0x08800000, "size": 65537}),
])
def test_unsafe_commands_or_parameters_never_transmitted(event, params):
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        adapter = DebuggerAdapter(transport)
        with pytest.raises(ValueError):
            await adapter.request(event, params)
        assert transport.sent == []
    asyncio.run(scenario())


def test_read_requires_exact_base64_length_and_keeps_replacements():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        adapter = DebuggerAdapter(transport)
        assert await adapter.read_memory(0x08800000, 4) == b"abcd"
        assert transport.sent[-1]["replacements"] is True
        with pytest.raises(ValueError, match="length"):
            await adapter.read_memory(0x08800000, 3)
    asyncio.run(scenario())


@pytest.mark.parametrize("stepping,paused", [(True, False), (False, True), (True, True)])
def test_observation_preserves_preexisting_user_pause(stepping, paused):
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport(stepping=stepping, paused=paused)
        adapter = DebuggerAdapter(transport)
        async with adapter.observation_pause():
            pass
        assert (transport.stepping, transport.paused) == (stepping, paused)
        assert not any(x["event"] == "cpu.resume" for x in transport.sent)
    asyncio.run(scenario())


def test_observation_exception_resumes_running_game():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        adapter = DebuggerAdapter(transport)
        with pytest.raises(RuntimeError, match="decode failed"):
            async with adapter.observation_pause():
                assert transport.stepping
                raise RuntimeError("decode failed")
        assert not transport.stepping
        assert not transport.buttons_down
    asyncio.run(scenario())


def test_press_timeout_releases_button_and_stops_later_actions():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        transport.silent.add("input.buttons.press")
        adapter = DebuggerAdapter(transport, timeout_seconds=0.02)
        with pytest.raises(TimeoutError):
            await adapter.press("right", 1)
        assert transport.buttons_down == set()
        with pytest.raises(RuntimeError, match="uncertain"):
            await adapter.press("left", 1)
        assert not any(x.get("button") == "left" for x in transport.sent)
    asyncio.run(scenario())


def test_cancellation_releases_injected_button():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        transport.silent.add("input.buttons.press")
        adapter = DebuggerAdapter(transport)
        task = asyncio.create_task(adapter.press("right", 1))
        while not transport.buttons_down:
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not transport.buttons_down
    asyncio.run(scenario())


def test_server_error_is_correlated_and_disconnect_marks_pause_unknown():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        adapter = DebuggerAdapter(transport)
        transport.error.add("cpu.status")
        with pytest.raises(RuntimeError, match="denied"):
            await adapter.status()
        transport.error.clear()
        transport.disconnected = True
        with pytest.raises(ConnectionError):
            await adapter.status()
        assert adapter.pause_status is None
        assert adapter.uncertain
    asyncio.run(scenario())


def test_user_ui_pause_during_observation_is_not_resumed():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        adapter = DebuggerAdapter(transport)
        async with adapter.observation_pause():
            transport.paused = True
        assert transport.paused
        assert not any(x["event"] == "cpu.resume" for x in transport.sent)
    asyncio.run(scenario())


def test_unconfirmed_pause_reports_unknown_and_blocks_actions():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        transport.silent.add("cpu.stepping")
        adapter = DebuggerAdapter(transport, timeout_seconds=0.02)
        with pytest.raises(TimeoutError):
            async with adapter.observation_pause():
                pytest.fail("unconfirmed pause yielded observation")
        assert adapter.uncertain
        assert adapter.pause_status is None
    asyncio.run(scenario())


def test_asynchronous_control_error_is_not_ignored():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        transport.error.add("cpu.stepping")
        adapter = DebuggerAdapter(transport, timeout_seconds=0.02)
        with pytest.raises(RuntimeError, match="denied"):
            async with adapter.observation_pause():
                pytest.fail("failed pause yielded observation")
        assert adapter.uncertain
    asyncio.run(scenario())


def test_malformed_base64_is_rejected():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        await transport.messages.put({"event": "memory.read", "ticket": "1", "base64": "!"})
        adapter = DebuggerAdapter(transport)
        with pytest.raises(ValueError, match="base64"):
            await adapter.read_memory(0x08800000, 4)
    asyncio.run(scenario())


@pytest.mark.parametrize("event", ["version", "game.status"])
def test_readonly_identity_commands_are_allowed_without_parameters(event):
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        response = await DebuggerAdapter(transport).request(event, {})
        assert response["event"] == event
    asyncio.run(scenario())


def test_queued_press_never_sends_after_read_timeout():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        transport.silent.add("memory.read")
        adapter = DebuggerAdapter(transport, timeout_seconds=0.02)
        read = asyncio.create_task(adapter.read_memory(0x08800000, 4))
        while not transport.sent:
            await asyncio.sleep(0)
        press = asyncio.create_task(adapter.press("right", 1))
        results = await asyncio.gather(read, press, return_exceptions=True)
        assert isinstance(results[0], TimeoutError)
        assert isinstance(results[1], RuntimeError)
        assert not any(x["event"] == "input.buttons.press" for x in transport.sent)
    asyncio.run(scenario())


def test_nested_press_fails_promptly_and_observation_resumes():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        adapter = DebuggerAdapter(transport)
        async with adapter.observation_pause():
            with pytest.raises(RuntimeError, match="observation"):
                async with asyncio.timeout(0.02):
                    await adapter.press("right", 1)
        assert not transport.stepping
        assert not any(x["event"] == "input.buttons.press" for x in transport.sent)
    asyncio.run(scenario())


def test_original_code_read_requires_owned_pause_and_preserves_public_false_rejection():
    from psp_buddy.debugger import DebuggerAdapter
    async def scenario():
        transport = FakeTransport()
        adapter = DebuggerAdapter(transport)
        adapter._assert_bound = lambda: None
        with pytest.raises(RuntimeError):
            await adapter.read_original_code(0x08800000, 4)
        assert transport.sent == []
        async with adapter.observation_pause():
            assert await adapter.read_original_code(0x08800000, 4) == b"abcd"
            reads = [m for m in transport.sent if m["event"] == "memory.read"]
            assert reads[-1]["replacements"] is False
            with pytest.raises(ValueError):
                await adapter.request("memory.read", {
                    "address": 0x08800000, "size": 4, "replacements": False})
            with pytest.raises(RuntimeError):
                await asyncio.create_task(adapter.read_original_code(0x08800000, 4))
            assert await adapter.read_memory(0x08800000, 4) == b"abcd"
            assert transport.sent[-1]["replacements"] is True
        assert not transport.stepping
    asyncio.run(scenario())


@pytest.mark.parametrize("address,size", [(True, 4), (0x08800001, 4), (0x08800000, True),
    (0x087FFFFC, 4), (0x09FFFFFC, 8), (0x08800000, 0), (0x08800000, 6), (0x08800000, 4100)])
def test_original_code_invalid_bounds_never_transmit(address, size):
    from psp_buddy.debugger import DebuggerAdapter
    async def scenario():
        transport = FakeTransport()
        adapter = DebuggerAdapter(transport)
        adapter._assert_bound = lambda: None
        async with adapter.observation_pause():
            before = len(transport.sent)
            with pytest.raises(ValueError):
                await adapter.read_original_code(address, size)
            assert len(transport.sent) == before
    asyncio.run(scenario())


def test_original_code_rechecks_scope_at_queued_dispatch():
    from psp_buddy.debugger import DebuggerAdapter
    async def scenario():
        transport = FakeTransport()
        adapter = DebuggerAdapter(transport)
        adapter._assert_bound = lambda: None
        async with adapter.observation_pause():
            await adapter._io_lock.acquire()
            def lose_scope():
                adapter._pause_owner = None
                adapter._io_lock.release()
            asyncio.get_running_loop().call_soon(lose_scope)
            with pytest.raises(RuntimeError):
                await adapter.read_original_code(0x08800000, 4)
            assert not any(m["event"] == "memory.read" for m in transport.sent)
    asyncio.run(scenario())


@pytest.mark.parametrize("fault", ["unbound", "unpaused", "short", "error"])
def test_original_code_identity_pause_and_response_fail_closed(fault):
    from psp_buddy.debugger import DebuggerAdapter
    async def scenario():
        transport = FakeTransport()
        adapter = DebuggerAdapter(transport)
        adapter._assert_bound = lambda: None
        async with adapter.observation_pause():
            if fault == "unbound":
                adapter._assert_bound = None
            if fault == "unpaused":
                adapter.pause_status = False
            if fault == "short":
                transport.memory = b"abc"
            if fault == "error":
                transport.error.add("memory.read")
            with pytest.raises((RuntimeError, ValueError)):
                await adapter.read_original_code(0x08800000, 4)
            if fault in ("unbound", "unpaused"):
                assert not any(m["event"] == "memory.read" for m in transport.sent)
            else:
                assert adapter.uncertain
    asyncio.run(scenario())
