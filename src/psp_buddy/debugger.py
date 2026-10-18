"""Allowlisted debugger primitives and a protected, identity-checked connection.

Schemas: PPSSPP v1.20.4 Core/Debugger/WebSocket/{CPUCore,Input,Memory}Subscriber.cpp.
Transport injection is a trusted integration seam, not live-trial authorization.
"""

import asyncio
import base64
import binascii
import ipaddress
import json
import math
from collections import deque
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Protocol

from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException
from websockets.typing import Subprotocol

if TYPE_CHECKING:
    from .launch import LaunchSession


def _launch_session_type() -> type["LaunchSession"]:
    from .launch import LaunchSession

    return LaunchSession


async def _open_websocket(
    endpoint: str, *, subprotocols: list[str], proxy: None, compression: None,
    open_timeout: float, close_timeout: float, max_size: int,
) -> "Socket":
    return await connect(
        endpoint, subprotocols=[Subprotocol(value) for value in subprotocols], proxy=proxy,
        compression=compression, open_timeout=open_timeout, close_timeout=close_timeout,
        max_size=max_size,
    )


class Transport(Protocol):
    async def send(self, message: str) -> None: ...
    async def recv(self) -> str: ...
    async def close(self) -> None: ...


class Socket(Protocol):
    async def send(self, message: str) -> None: ...
    async def recv(self) -> str | bytes: ...
    async def close(self) -> None: ...


class WebSocketTransport:
    def __init__(self, socket: Socket) -> None:
        self.socket = socket

    async def send(self, message: str) -> None:
        try:
            await self.socket.send(message)
        except (WebSocketException, OSError) as exc:
            raise ConnectionError("debugger connection lost while sending") from exc

    async def recv(self) -> str:
        try:
            message = await self.socket.recv()
        except (WebSocketException, OSError) as exc:
            raise ConnectionError("debugger connection lost while receiving") from exc
        if not isinstance(message, str):
            raise ValueError("debugger reply must be text")
        return message

    async def close(self) -> None:
        await self.socket.close()


BUTTONS = frozenset({"cross", "circle", "triangle", "square", "up", "down", "left",
                     "right", "start", "select", "ltrigger", "rtrigger"})


def _bounded_integer(value: object, lower: int, upper: int) -> bool:
    return type(value) is int and lower <= value <= upper


def _validate(event: str, params: Mapping[str, object]) -> None:
    valid = False
    if event in {"version", "game.status", "cpu.status", "cpu.stepping", "cpu.resume"}:
        valid = not params
    elif event in {"gpu.buffer.screenshot", "gpu.buffer.renderColor"}:
        valid = dict(params) == {"type": "uri"}
    elif event == "input.buttons.press":
        valid = (set(params) == {"button", "duration"}
                 and isinstance(params["button"], str) and params["button"] in BUTTONS
                 and _bounded_integer(params["duration"], 1, 30))
    elif event == "input.buttons.send":
        buttons = params.get("buttons")
        valid = (set(params) == {"buttons"} and isinstance(buttons, dict) and bool(buttons)
                 and all(key in BUTTONS and value is False for key, value in buttons.items()))
    elif event == "memory.read":
        address, size = params.get("address"), params.get("size")
        valid = (set(params) <= {"address", "size", "replacements"}
                 and _bounded_integer(address, 0, 0xFFFFFFFF)
                 and _bounded_integer(size, 1, 65536)
                 and params.get("replacements", True) is True)
        if valid:
            assert isinstance(address, int) and isinstance(size, int)
            valid = address + size <= 0x100000000
    if not valid:
        raise ValueError(f"command or parameters not allowlisted: {event}")


class DebuggerAdapter:
    def __init__(self, transport: Transport, *, timeout_seconds: float = 10) -> None:
        if (isinstance(timeout_seconds, bool) or not math.isfinite(timeout_seconds)
                or timeout_seconds <= 0):
            raise ValueError("timeout must be finite and positive")
        self.transport = transport
        self.timeout_seconds = timeout_seconds
        self.events: deque[dict[str, object]] = deque(maxlen=100)
        self.uncertain = False
        self.pause_status: bool | None = None
        self._ticket = 0
        self._io_lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()
        self._held: set[str] = set()
        self._control_ticket: str | None = None
        self._pause_owner: asyncio.Task[object] | None = None
        self._assert_bound: Callable[[], None] | None = None

    @classmethod
    async def connect_live(cls, session: object) -> "DebuggerAdapter":
        """Accept only a launch-issued session, never an arbitrary endpoint or receipt."""
        from .launch import ConnectionNotReady

        if not isinstance(session, _launch_session_type()):
            raise RuntimeError("trusted launch session required before any debugger I/O")
        timeout = session.config.timeout_seconds
        async with asyncio.timeout(timeout):
            while True:
                try:
                    endpoint = await asyncio.to_thread(session.claim_connection)
                    break
                except ConnectionNotReady:
                    await asyncio.sleep(0.05)
            socket = await _open_websocket(
                endpoint, subprotocols=["debugger.ppsspp.org"], proxy=None, compression=None,
                open_timeout=timeout, close_timeout=timeout, max_size=8 * 1024 * 1024,
            )
            adapter = cls(WebSocketTransport(socket), timeout_seconds=timeout)
            adapter._assert_bound = session.assert_bound
            try:
                peer = getattr(socket, "remote_address", None)
                try:
                    local_peer = (isinstance(peer, tuple) and len(peer) >= 2
                                  and isinstance(peer[0], str)
                                  and ipaddress.ip_address(peer[0]).is_loopback)
                except ValueError:
                    local_peer = False
                if not local_peer:
                    raise ValueError("debugger connection requires a loopback peer")
                if getattr(socket, "subprotocol", None) != "debugger.ppsspp.org":
                    raise ValueError("debugger protocol identity mismatch")
                await asyncio.to_thread(session.assert_bound)
                version = await adapter.request("version", {})
                if (version.get("name") != "PPSSPP"
                        or version.get("version") != f"v{session.config.emulator_version}"):
                    raise ValueError("emulator identity mismatch")
                while True:
                    status = await adapter.request("game.status", {})
                    game = status.get("game")
                    if game is not None:
                        if (not isinstance(game, dict)
                                or game.get("id") != session.config.game_id
                                or game.get("version") != session.game_version):
                            raise ValueError("game identity mismatch")
                        break
                    await asyncio.sleep(0.05)
                await asyncio.to_thread(session.assert_bound)
                return adapter
            except BaseException as exc:
                try:
                    await adapter.close()
                except BaseException as cleanup_error:
                    exc.add_note(f"debugger cleanup failed: {cleanup_error}")
                raise

    def _original_code_scope(self) -> None:
        if (self._pause_owner is not asyncio.current_task()
                or not self._operation_lock.locked() or self.pause_status is not True
                or self._assert_bound is None):
            raise RuntimeError("original code requires an owned, bound observation pause")

    def _render_scope(self) -> None:
        if (self._pause_owner is not asyncio.current_task()
                or not self._operation_lock.locked() or self.pause_status is not True
                or self._assert_bound is None):
            raise RuntimeError("render capture requires an owned, bound observation pause")

    async def _exchange(self, event: str, params: Mapping[str, object], *,
                        original_code: bool = False,
                        render_capture: bool = False) -> dict[str, object]:
        if render_capture:
            self._render_scope()
            if event != "gpu.buffer.renderColor" or dict(params) != {"type": "uri"}:
                raise ValueError("invalid render capture command")
        if original_code:
            self._original_code_scope()
            address, size = params.get("address"), params.get("size")
            if (event != "memory.read" or set(params) != {"address", "size", "replacements"}
                    or params.get("replacements") is not False
                    or not _bounded_integer(address, 0x08800000, 0x09FFFFFC)
                    or not _bounded_integer(size, 4, 4096)):
                raise ValueError("invalid original code window")
            assert isinstance(address, int) and isinstance(size, int)
            if address % 4 or size % 4 or address + size > 0x0A000000:
                raise ValueError("invalid original code window")
        else:
            _validate(event, params)
        if self.uncertain and event not in {"input.buttons.send", "cpu.status", "cpu.resume"}:
            raise RuntimeError("transport outcome uncertain; further actions prohibited")
        async with self._io_lock:
            if original_code:
                self._original_code_scope()
            if render_capture:
                self._render_scope()
            # A preceding queued request may have failed while this caller waited.
            if self.uncertain and event not in {"input.buttons.send", "cpu.status", "cpu.resume"}:
                raise RuntimeError("transport outcome uncertain; further actions prohibited")
            self._ticket += 1
            ticket = str(self._ticket)
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    if ((original_code or render_capture or event in {
                            "input.buttons.press", "cpu.stepping", "cpu.resume"})
                            and self._assert_bound is not None):
                        try:
                            await asyncio.to_thread(self._assert_bound)
                        except BaseException:
                            self.uncertain = True
                            self.pause_status = None
                            raise
                    if original_code:
                        self._original_code_scope()
                    if render_capture:
                        self._render_scope()
                    await self.transport.send(json.dumps({**params, "event": event,
                                                          "ticket": ticket}))
                    if event in {"cpu.stepping", "cpu.resume"}:
                        self._control_ticket = ticket
                        return {}
                    while True:
                        message = json.loads(await self.transport.recv())
                        if not isinstance(message, dict):
                            raise ValueError("invalid debugger message")
                        if (message.get("ticket") == self._control_ticket
                                and message.get("event") == "error"):
                            raise RuntimeError(str(message.get("message", "control error")))
                        if message.get("ticket") != ticket:
                            self.events.append(message)
                            continue
                        if message.get("event") == "error":
                            raise RuntimeError(str(message.get("message", "debugger error")))
                        if message.get("event") == event:
                            return message
                        self.events.append(message)
            except (TimeoutError, ConnectionError, OSError, asyncio.CancelledError,
                    ValueError):
                self.uncertain = True
                self.pause_status = None
                raise

    async def request(self, event: str, params: Mapping[str, object]) -> dict[str, object]:
        """Validated public seam; state-changing controls use scoped methods only."""
        _validate(event, params)
        if event in {"cpu.stepping", "cpu.resume"}:
            raise ValueError("execution control requires observation_pause scope")
        if event == "input.buttons.press":
            button, duration = params["button"], params["duration"]
            assert isinstance(button, str) and isinstance(duration, int)
            return await self.press(button, duration)
        return await self._exchange(event, params)

    async def status(self) -> tuple[bool, bool]:
        response = await self._exchange("cpu.status", {})
        stepping, paused = response.get("stepping"), response.get("paused")
        if type(stepping) is not bool or type(paused) is not bool:
            self.uncertain = True
            self.pause_status = None
            raise ValueError("invalid CPU status")
        self.pause_status = stepping or paused
        return stepping, paused

    async def read_memory(self, address: int, size: int) -> bytes:
        response = await self._exchange(
            "memory.read", {"address": address, "size": size, "replacements": True}
        )
        encoded = response.get("base64")
        try:
            if not isinstance(encoded, str):
                raise ValueError("invalid memory base64")
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("invalid memory base64") from exc
        if len(data) != size:
            raise ValueError("memory response length mismatch")
        return data

    async def read_original_code(self, address: int, size: int) -> bytes:
        """Read a bounded original instruction view only within the caller's owned pause."""
        # Validate before any I/O; public request() never receives this private capability.
        if (not _bounded_integer(address, 0x08800000, 0x09FFFFFC)
                or not _bounded_integer(size, 4, 4096)
                or address % 4 or size % 4 or address + size > 0x0A000000):
            raise ValueError("invalid original code window")
        self._original_code_scope()
        try:
            response = await self._exchange(
                "memory.read", {"address": address, "size": size, "replacements": False},
                original_code=True,
            )
            encoded = response.get("base64")
            if not isinstance(encoded, str):
                raise ValueError("invalid memory base64")
            try:
                data = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise ValueError("invalid memory base64") from exc
            if len(data) != size:
                raise ValueError("memory response length mismatch")
            return data
        except (TimeoutError, ConnectionError, OSError, asyncio.CancelledError,
                ValueError, RuntimeError):
            self.uncertain = True
            self.pause_status = None
            raise

    async def read_render_png(self) -> dict[str, object]:
        """Acquire one render-color PNG URI within the caller's bound observation pause.

        The capture service validates the returned image before accepting it as evidence.
        Transport and protocol failures prohibit subsequent captures; never retry here.
        """
        self._render_scope()
        try:
            return await self._exchange(
                "gpu.buffer.renderColor", {"type": "uri"}, render_capture=True,
            )
        except (TimeoutError, ConnectionError, OSError, asyncio.CancelledError,
                ValueError, RuntimeError):
            self.uncertain = True
            self.pause_status = None
            raise

    async def _release(self) -> None:
        if self._held:
            await self._exchange(
                "input.buttons.send", {"buttons": dict.fromkeys(self._held, False)}
            )
            self._held.clear()

    async def press(self, button: str, duration: int = 1) -> dict[str, object]:
        params: dict[str, object] = {"button": button, "duration": duration}
        _validate("input.buttons.press", params)
        if self._pause_owner is asyncio.current_task():
            raise RuntimeError("cannot press buttons inside an observation scope")
        async with self._operation_lock:
            if self.uncertain:
                raise RuntimeError("transport outcome uncertain; further actions prohibited")
            self._held.add(button)
            try:
                return await self._exchange("input.buttons.press", params)
            finally:
                await self._release()

    async def _transition(self, event: str, expected_stepping: bool) -> None:
        try:
            await self._exchange(event, {})
            async with asyncio.timeout(self.timeout_seconds):
                while True:
                    stepping, paused = await self.status()
                    if stepping is expected_stepping:
                        if not expected_stepping and paused:
                            raise RuntimeError("user UI pause active during resume")
                        return
                    await asyncio.sleep(0.005)
        except BaseException:
            self.uncertain = True
            self.pause_status = None
            raise
        finally:
            self._control_ticket = None

    @asynccontextmanager
    async def observation_pause(self) -> AsyncIterator[tuple[bool, bool]]:
        if self._pause_owner is asyncio.current_task():
            raise RuntimeError("nested observation scope prohibited")
        async with self._operation_lock:
            stepping, paused = await self.status()
            owns_pause = not stepping and not paused
            try:
                if owns_pause:
                    await self._transition("cpu.stepping", True)
                self._pause_owner = asyncio.current_task()
                yield stepping, paused
            finally:
                self._pause_owner = None
                await self._release()
                if owns_pause and not self.uncertain:
                    _, user_paused = await self.status()
                    if not user_paused:
                        await self._transition("cpu.resume", False)

    async def close(self) -> None:
        try:
            await self._release()
        finally:
            await self.transport.close()
            self.pause_status = None
