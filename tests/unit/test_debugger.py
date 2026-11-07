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


def gap_adapter(transport):
    """Adapter on a fake clock: sleeps advance the clock and are recorded."""
    from psp_buddy.debugger import DebuggerAdapter

    adapter = DebuggerAdapter(transport)
    adapter.now, adapter.slept = 100.0, []
    adapter._clock = lambda: adapter.now

    async def sleep(seconds):
        adapter.slept.append(round(seconds, 3))
        adapter.now += seconds
    adapter._gap_sleep = sleep
    return adapter


def test_a_pause_right_after_a_press_waits_for_the_press_gap():
    # fr-s33b (1 Nov): with fast reads a pause came milliseconds after a press, and the
    # debugger then stopped answering for 60 s.
    async def scenario():
        transport = FakeTransport()
        adapter = gap_adapter(transport)
        await adapter.press("down", 2)
        adapter.now += 0.05
        async with adapter.observation_pause():
            pass
        assert adapter.slept == [0.15]
    asyncio.run(scenario())


def test_a_pause_right_after_a_resume_waits_for_the_resume_gap():
    async def scenario():
        adapter = gap_adapter(FakeTransport())
        async with adapter.observation_pause():
            pass
        async with adapter.observation_pause():
            pass
        assert adapter.slept == [0.1]
    asyncio.run(scenario())


def test_a_pause_long_after_the_last_input_does_not_wait():
    async def scenario():
        adapter = gap_adapter(FakeTransport())
        await adapter.press("down", 2)
        adapter.now += 5
        async with adapter.observation_pause():
            pass
        assert adapter.slept == []
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


# 7 Nov (debugger-freeze spec, Part 1): one trace record per debugger request.
def traced_adapter(transport, **options):
    from psp_buddy.debugger import DebuggerAdapter

    adapter = DebuggerAdapter(transport, **options)
    adapter.records = []
    adapter.trace = adapter.records.append
    return adapter


def test_each_request_is_traced_with_event_ticket_seconds_and_ok():
    async def scenario():
        adapter = traced_adapter(FakeTransport())
        await adapter.read_memory(0x08800000, 4)
        [record] = adapter.records
        assert record["event"] == "memory.read" and record["outcome"] == "ok"
        assert record["ticket"] == "1" and record["seconds"] >= 0
        assert isinstance(record["sent_ns"], int)
    asyncio.run(scenario())


def test_a_silent_request_is_traced_as_timeout_and_still_raises():
    async def scenario():
        transport = FakeTransport()
        transport.silent.add("memory.read")
        adapter = traced_adapter(transport, timeout_seconds=0.05)
        with pytest.raises(TimeoutError):
            await adapter.read_memory(0x08800000, 4)
        assert [r["outcome"] for r in adapter.records] == ["timeout"]
    asyncio.run(scenario())


def test_an_error_reply_is_traced_with_its_type():
    async def scenario():
        transport = FakeTransport()
        transport.error.add("memory.read")
        adapter = traced_adapter(transport)
        with pytest.raises(RuntimeError):
            await adapter.read_memory(0x08800000, 4)
        assert adapter.records[0]["outcome"] == "error: RuntimeError"
    asyncio.run(scenario())


def test_pause_and_status_polls_are_traced():
    async def scenario():
        adapter = traced_adapter(FakeTransport())
        async with adapter.observation_pause():
            pass
        events = [r["event"] for r in adapter.records]
        assert "cpu.stepping" in events and "cpu.resume" in events
        assert events.count("cpu.status") >= 2
    asyncio.run(scenario())


def test_a_failing_trace_never_changes_the_request():
    async def scenario():
        from psp_buddy.debugger import DebuggerAdapter

        adapter = DebuggerAdapter(FakeTransport())

        def broken(record):
            raise OSError("disk full")
        adapter.trace = broken
        assert await adapter.read_memory(0x08800000, 4) == b"abcd"
        assert adapter.trace_errors == 1
    asyncio.run(scenario())


# 7 Nov (fallback fix): after a read/status timeout, recover() checks the link with cpu.status.
def frozen_read_adapter(transport):
    from psp_buddy.debugger import DebuggerAdapter

    adapter = DebuggerAdapter(transport, timeout_seconds=0.05)
    adapter.RECOVER_SECONDS = 0.05

    async def freeze():
        transport.silent.add("memory.read")
        with pytest.raises(TimeoutError):
            async with adapter.observation_pause():
                await adapter.read_memory(0x08800000, 4)
        transport.silent.discard("memory.read")
    return adapter, freeze


def test_recover_after_a_read_timeout_clears_uncertain_and_resumes_the_cpu():
    async def scenario():
        transport = FakeTransport()
        adapter, freeze = frozen_read_adapter(transport)
        await freeze()
        assert adapter.uncertain and transport.stepping      # our pause was left in place
        assert await adapter.recover() is True
        assert not adapter.uncertain and not transport.stepping
        assert await adapter.read_memory(0x08800000, 4) == b"abcd"
    asyncio.run(scenario())


def test_recover_fails_when_the_status_check_stays_silent():
    async def scenario():
        transport = FakeTransport()
        adapter, freeze = frozen_read_adapter(transport)
        await freeze()
        transport.silent.add("cpu.status")
        assert await adapter.recover() is False
        assert adapter.uncertain
    asyncio.run(scenario())


def test_recover_never_clears_an_uncertain_press():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        transport.silent.add("input.buttons.press")
        adapter = DebuggerAdapter(transport, timeout_seconds=0.05)
        adapter.RECOVER_SECONDS = 0.05
        with pytest.raises(TimeoutError):
            await adapter.press("down", 2)
        assert await adapter.recover() is False
        assert adapter.uncertain
        assert not any(x["event"] == "cpu.status" for x in transport.sent)
    asyncio.run(scenario())


def test_recover_leaves_a_user_pause_alone():
    async def scenario():
        transport = FakeTransport()
        adapter, freeze = frozen_read_adapter(transport)
        await freeze()
        transport.paused = True
        assert await adapter.recover() is True
        assert not any(x["event"] == "cpu.resume" for x in transport.sent)
    asyncio.run(scenario())


def test_recover_on_a_healthy_adapter_is_a_no_op():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        assert await DebuggerAdapter(transport).recover() is True
        assert transport.sent == []
    asyncio.run(scenario())


def test_a_pause_that_never_takes_effect_is_recoverable():
    from psp_buddy.debugger import DebuggerAdapter

    async def scenario():
        transport = FakeTransport()
        transport.silent.add("cpu.stepping")       # the CPU never reports stepping
        adapter = DebuggerAdapter(transport, timeout_seconds=0.05)
        adapter.RECOVER_SECONDS = 0.05
        with pytest.raises(TimeoutError):
            async with adapter.observation_pause():
                pass
        assert adapter.uncertain
        assert await adapter.recover() is True and not adapter.uncertain
    asyncio.run(scenario())


def test_recover_bounds_the_resume_by_recover_seconds_not_the_adapter_timeout():
    import time

    async def scenario():
        transport = FakeTransport()
        adapter, freeze = frozen_read_adapter(transport)
        await freeze()
        adapter.timeout_seconds = 5           # live: 60 s from config.json
        transport.silent.add("cpu.resume")    # the CPU never resumes
        started = time.monotonic()
        assert await adapter.recover() is False
        assert time.monotonic() - started < 1
    asyncio.run(scenario())
