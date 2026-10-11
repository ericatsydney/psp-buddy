"""Wire transport tests use synthetic sockets, never a running emulator."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from websockets.exceptions import ConnectionClosedError


class Socket:
    def __init__(self, response="{}", error=None):
        self.response = response
        self.error = error
        self.sent = []
        self.closed = False

    async def send(self, message):
        if self.error:
            raise self.error
        self.sent.append(message)

    async def recv(self):
        if self.error:
            raise self.error
        return self.response

    async def close(self):
        self.closed = True


def test_transport_preserves_text_and_closes_owned_socket():
    from psp_buddy.debugger import WebSocketTransport

    async def scenario():
        socket = Socket('{"event":"cpu.status"}')
        transport = WebSocketTransport(socket)
        await transport.send('{"event":"version"}')
        assert socket.sent == ['{"event":"version"}']
        assert await transport.recv() == '{"event":"cpu.status"}'
        await transport.close()
        assert socket.closed
    asyncio.run(scenario())


@pytest.mark.parametrize("operation", ["send", "recv"])
def test_websocket_close_is_normalized_for_adapter_cleanup(operation):
    from psp_buddy.debugger import WebSocketTransport

    async def scenario():
        transport = WebSocketTransport(Socket(error=ConnectionClosedError(None, None)))
        with pytest.raises(ConnectionError, match="debugger"):
            if operation == "send":
                await transport.send("{}")
            else:
                await transport.recv()
    asyncio.run(scenario())


def test_binary_wire_reply_is_rejected():
    from psp_buddy.debugger import WebSocketTransport

    async def scenario():
        with pytest.raises(ValueError, match="text"):
            await WebSocketTransport(Socket(b"binary")).recv()
    asyncio.run(scenario())


class Session:
    def __init__(self):
        self.config = SimpleNamespace(timeout_seconds=1, emulator_version="1.20.4",
                                      game_id="ULJS00460")
        self.game_version = "1.01"
        self.claimed = False
        self.bound_checks = 0

    def claim_connection(self):
        if self.claimed:
            raise ValueError("consumed session")
        self.claimed = True
        return "ws://127.0.0.1:27312/debugger"

    def assert_bound(self):
        self.bound_checks += 1


class IdentitySocket(Socket):
    subprotocol = "debugger.ppsspp.org"
    remote_address = ("127.0.0.1", 27312)

    def __init__(self, *, game_id="ULJS00460", version="v1.20.4", game_version="1.01"):
        super().__init__()
        self.game_id = game_id
        self.version = version
        self.game_version = game_version
        self.responses = asyncio.Queue()

    async def send(self, message):
        self.sent.append(message)
        request = json.loads(message)
        response = {"event": request["event"], "ticket": request["ticket"]}
        if request["event"] == "version":
            response.update(name="PPSSPP", version=self.version)
        elif request["event"] == "game.status":
            response["game"] = {"id": self.game_id, "version": self.game_version}
        elif request["event"] == "cpu.status":
            response.update(paused=False, stepping=False)
        await self.responses.put(json.dumps(response))

    async def recv(self):
        return await self.responses.get()


def test_live_factory_claims_bound_session_and_verifies_identity_before_inputs(monkeypatch):
    from psp_buddy import debugger

    async def scenario():
        session = Session()
        socket = IdentitySocket()
        connection_parameters = {}

        async def open_socket(endpoint, **kwargs):
            assert session.claimed
            connection_parameters.update(endpoint=endpoint, **kwargs)
            return socket

        monkeypatch.setattr(debugger, "_launch_session_type", lambda: Session, raising=False)
        monkeypatch.setattr(debugger, "_open_websocket", open_socket, raising=False)
        adapter = await debugger.DebuggerAdapter.connect_live(session)
        assert connection_parameters["proxy"] is None
        assert connection_parameters["subprotocols"] == ["debugger.ppsspp.org"]
        assert session.bound_checks >= 1
        assert [json.loads(x)["event"] for x in socket.sent] == ["version", "game.status"]
        await adapter.close()
        assert socket.closed
    asyncio.run(scenario())


@pytest.mark.parametrize("wrong", [{"game_id": "OTHER"}, {"version": "v1.9.3"},
                                  {"game_version": "2.00"}])
def test_wrong_runtime_identity_closes_transport_before_battle_inputs(monkeypatch, wrong):
    from psp_buddy import debugger

    async def scenario():
        socket = IdentitySocket(**wrong)

        async def open_socket(endpoint, **kwargs):
            return socket

        monkeypatch.setattr(debugger, "_launch_session_type", lambda: Session, raising=False)
        monkeypatch.setattr(debugger, "_open_websocket", open_socket, raising=False)
        with pytest.raises(ValueError, match="identity"):
            await debugger.DebuggerAdapter.connect_live(Session())
        assert socket.closed
        assert not any(json.loads(x)["event"].startswith("input.") for x in socket.sent)
    asyncio.run(scenario())


def test_wrong_protocol_closes_without_identity_or_input_requests(monkeypatch):
    from psp_buddy import debugger

    async def scenario():
        socket = IdentitySocket()
        socket.subprotocol = None

        async def open_socket(endpoint, **kwargs):
            return socket

        monkeypatch.setattr(debugger, "_launch_session_type", lambda: Session)
        monkeypatch.setattr(debugger, "_open_websocket", open_socket)
        with pytest.raises(ValueError, match="protocol identity"):
            await debugger.DebuggerAdapter.connect_live(Session())
        assert socket.closed
        assert socket.sent == []
    asyncio.run(scenario())


def test_consumed_session_never_opens_another_socket(monkeypatch):
    from psp_buddy import debugger

    async def scenario():
        session = Session()
        session.claim_connection()
        attempted = []

        async def open_socket(endpoint, **kwargs):
            attempted.append(endpoint)
            return IdentitySocket()

        monkeypatch.setattr(debugger, "_launch_session_type", lambda: Session)
        monkeypatch.setattr(debugger, "_open_websocket", open_socket)
        with pytest.raises(ValueError, match="consumed"):
            await debugger.DebuggerAdapter.connect_live(session)
        assert attempted == []
    asyncio.run(scenario())


def test_game_loading_is_polled_without_inputs(monkeypatch):
    from psp_buddy import debugger

    class LoadingSocket(IdentitySocket):
        def __init__(self):
            super().__init__()
            self.pending = True

        async def send(self, message):
            request = json.loads(message)
            if request["event"] == "game.status" and self.pending:
                self.pending = False
                self.sent.append(message)
                await self.responses.put(json.dumps({**request, "game": None}))
            else:
                await super().send(message)

    async def scenario():
        socket = LoadingSocket()

        async def open_socket(endpoint, **kwargs):
            return socket

        monkeypatch.setattr(debugger, "_launch_session_type", lambda: Session)
        monkeypatch.setattr(debugger, "_open_websocket", open_socket)
        adapter = await debugger.DebuggerAdapter.connect_live(Session())
        assert [json.loads(x)["event"] for x in socket.sent] == [
            "version", "game.status", "game.status"]
        await adapter.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("event", ["gpu.buffer.screenshot", "gpu.buffer.renderColor"])
def test_capture_requests_allow_only_png_uri(event):
    from psp_buddy import debugger

    debugger._validate(event, {"type": "uri"})
    with pytest.raises(ValueError, match="allowlisted"):
        debugger._validate(event, {"type": "uri", "stackWidth": 0xFFFFFFFF})


def install_fake_connection(monkeypatch, session, socket):
    from psp_buddy import debugger

    async def open_socket(endpoint, **kwargs):
        return socket

    monkeypatch.setattr(debugger, "_launch_session_type", lambda: type(session))
    monkeypatch.setattr(debugger, "_open_websocket", open_socket)


def test_revoked_binding_blocks_press_but_permits_release(monkeypatch):
    from psp_buddy import debugger

    class RevocableSession(Session):
        revoked = False

        def assert_bound(self):
            if self.revoked:
                raise RuntimeError("binding revoked")
            super().assert_bound()

    async def scenario():
        session, socket = RevocableSession(), IdentitySocket()
        install_fake_connection(monkeypatch, session, socket)
        adapter = await debugger.DebuggerAdapter.connect_live(session)
        session.revoked = True
        with pytest.raises(RuntimeError, match="binding revoked"):
            await adapter.press("cross")
        events = [json.loads(message)["event"] for message in socket.sent]
        assert "input.buttons.press" not in events
        assert events[-1] == "input.buttons.send"
        await adapter.close()

    asyncio.run(scenario())


def test_connect_preserves_identity_failure_when_close_fails(monkeypatch):
    from psp_buddy import debugger

    class BadCloseSocket(IdentitySocket):
        async def close(self):
            raise OSError("cleanup failed")

    async def scenario():
        session, socket = Session(), BadCloseSocket(game_id="OTHER")
        install_fake_connection(monkeypatch, session, socket)
        with pytest.raises(ValueError, match="game identity") as caught:
            await debugger.DebuggerAdapter.connect_live(session)
        assert any("cleanup failed" in note for note in caught.value.__notes__)

    asyncio.run(scenario())


@pytest.mark.parametrize("cancel", [False, True])
def test_pending_game_deadline_or_cancellation_closes_socket(monkeypatch, cancel):
    from psp_buddy import debugger

    class PendingSocket(IdentitySocket):
        async def send(self, message):
            request = json.loads(message)
            if request["event"] == "game.status":
                self.sent.append(message)
                await self.responses.put(json.dumps({**request, "game": None}))
            else:
                await super().send(message)

    async def scenario():
        session, socket = Session(), PendingSocket()
        session.config.timeout_seconds = 0.15
        install_fake_connection(monkeypatch, session, socket)
        task = asyncio.create_task(debugger.DebuggerAdapter.connect_live(session))
        if cancel:
            async with asyncio.timeout(1):
                while not any(json.loads(x)["event"] == "game.status" for x in socket.sent):
                    await asyncio.sleep(0.001)
            task.cancel()
        with pytest.raises(asyncio.CancelledError if cancel else TimeoutError):
            await task
        assert socket.closed
        assert not any(json.loads(x)["event"].startswith("input.") for x in socket.sent)

    asyncio.run(scenario())


def test_connection_not_ready_is_retried_before_claim(monkeypatch):
    from psp_buddy import debugger
    from psp_buddy.launch import ConnectionNotReady

    class StartingSession(Session):
        attempts = 0

        def claim_connection(self):
            self.attempts += 1
            if self.attempts == 1:
                raise ConnectionNotReady("starting")
            return super().claim_connection()

    async def scenario():
        session, socket = StartingSession(), IdentitySocket()
        install_fake_connection(monkeypatch, session, socket)
        adapter = await debugger.DebuggerAdapter.connect_live(session)
        assert session.attempts == 2
        assert session.claimed
        await adapter.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("control", ["cpu.stepping", "cpu.resume"])
def test_revoked_binding_blocks_execution_control(monkeypatch, control):
    from psp_buddy import debugger

    class RevocableSession(Session):
        revoked = False

        def assert_bound(self):
            if self.revoked:
                raise RuntimeError("binding revoked")
            super().assert_bound()

    async def scenario():
        session, socket = RevocableSession(), IdentitySocket()
        install_fake_connection(monkeypatch, session, socket)
        adapter = await debugger.DebuggerAdapter.connect_live(session)
        session.revoked = True
        with pytest.raises(RuntimeError, match="binding revoked"):
            await adapter._exchange(control, {})
        assert control not in [json.loads(message)["event"] for message in socket.sent]
        assert adapter.uncertain
        assert adapter.pause_status is None
        await adapter.request("input.buttons.send", {"buttons": {"cross": False}})
        assert json.loads(socket.sent[-1])["event"] == "input.buttons.send"
        await adapter.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("peer", [None, ("192.0.2.1", 27312), ("invalid", 27312)])
def test_unknown_or_nonlocal_peer_closes_without_requests(monkeypatch, peer):
    from psp_buddy import debugger

    async def scenario():
        session, socket = Session(), IdentitySocket()
        socket.remote_address = peer
        install_fake_connection(monkeypatch, session, socket)
        with pytest.raises(ValueError, match="loopback peer"):
            await debugger.DebuggerAdapter.connect_live(session)
        assert socket.closed
        assert socket.sent == []

    asyncio.run(scenario())
