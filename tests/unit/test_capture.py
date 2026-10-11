import asyncio
import hashlib
import io
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from psp_buddy.backup import BackupGate
from psp_buddy.config import RunConfig
from psp_buddy.launch import Launcher, ProcessIdentity


class Closed:
    def assert_non_writing(self, config):
        pass


class Process:
    pid = 1234
    stopped = False

    def poll(self):
        return 0 if self.stopped else None

    def terminate(self):
        self.stopped = True

    def wait(self, timeout):
        return 0


class Inspector:
    identity = ProcessIdentity(Path('unused'), '', 'created')

    def process(self, pid):
        return self.identity

    def listeners(self, port):
        return ()


@pytest.fixture
def owned(config_values, tmp_path):
    config = RunConfig.from_dict(config_values)
    config.emulator_path.write_bytes(b'synthetic exe')
    config.iso_path.write_bytes(b'synthetic ISO')
    assets = tmp_path / 'assets'
    assets.mkdir()
    (assets / 'font.bin').write_bytes(b'synthetic font')
    (config.portable_states / 'ULJS00460_1.01_1.ppst').write_bytes(b'synthetic state')
    system = tmp_path / 'SYSTEM'
    system.mkdir()
    (system / 'ppsspp.ini').write_text('[General]\n')
    (system / 'controls.ini').write_text('[ControlMapping]\n')
    inspector, process = Inspector(), Process()

    def factory(args, **kwargs):
        inspector.identity = ProcessIdentity(
            Path(args[0]), subprocess.list2cmdline(args), 'created')
        return process

    launcher = Launcher(gate=BackupGate(guard=Closed()), process_factory=factory,
                        inspector=inspector)
    prepared = launcher.prepare(config, state_filename='ULJS00460_1.01_1.ppst', system_root=system)
    session = launcher.start(prepared)
    return session, inspector


def picture(size=(16, 12), blank=False, fmt='PNG'):
    image = Image.new('RGB', size, 'black')
    if not blank:
        image.putpixel((1, 1), (255, 100, 20))
    stream = io.BytesIO()
    image.save(stream, format=fmt)
    return stream.getvalue()


def collector(owned):
    from psp_buddy.capture import ScreenshotCapture
    session, _ = owned
    return ScreenshotCapture(session, (16, 12))


async def write(owned, data, name='ULJS00460_00000.png'):
    directory = owned[0].memstick_root / 'PSP/SCREENSHOT'
    directory.mkdir(exist_ok=True)
    (directory / name).write_bytes(data)


def test_complete_distinct_identical_frames(owned):
    async def scenario():
        capture = collector(owned)
        data = picture(fmt='JPEG')
        first = await capture.capture(lambda: write(owned, data, 'ULJS00460_00000.jpg'),
                                      timeout_seconds=1)
        second = await capture.capture(lambda: write(owned, data, 'ULJS00460_00001.jpg'),
                                       timeout_seconds=1)
        assert first.encoded_bytes == second.encoded_bytes == data
        assert first.sha256 == hashlib.sha256(data).hexdigest()
        assert (first.sequence, second.sequence) == (1, 2)
        assert first.size == (16, 12)
        assert first.game_id == 'ULJS00460'
        assert first.trial_id == owned[0].receipt.trial_id
    asyncio.run(scenario())


def test_no_new_file_times_out_and_poisoned(owned):
    async def scenario():
        await write(owned, picture())
        capture = collector(owned)

        async def noop():
            pass
        with pytest.raises(TimeoutError):
            await capture.capture(noop, timeout_seconds=.06)
        with pytest.raises(ValueError, match='uncertain'):
            await capture.capture(lambda: write(owned, picture(), 'ULJS00460_00001.png'),
                                  timeout_seconds=1)
    asyncio.run(scenario())


@pytest.mark.parametrize('mode', ['overwrite', 'multiple', 'blank', 'size', 'format', 'hardlink'])
def test_rejects_unsafe_or_invalid_output(owned, mode):
    async def scenario():
        capture = collector(owned)
        if mode == 'overwrite':
            await write(owned, picture())

        async def trigger():
            data = picture(blank=mode == 'blank', size=(8, 8) if mode == 'size' else (16, 12),
                           fmt='GIF' if mode == 'format' else 'PNG')
            if mode == 'overwrite':
                data += b'changed'
            await write(owned, data)
            if mode == 'multiple':
                await write(owned, data, 'ULJS00460_00001.png')
            if mode == 'hardlink':
                directory = owned[0].memstick_root / 'PSP/SCREENSHOT'
                (directory / 'other').hardlink_to(directory / 'ULJS00460_00000.png')
        with pytest.raises(ValueError):
            await capture.capture(trigger, timeout_seconds=2)
    asyncio.run(scenario())


def test_partial_output_waits(owned):
    async def scenario():
        capture = collector(owned)
        data = picture()

        async def trigger():
            await write(owned, data[:25])

        async def finish():
            await asyncio.sleep(.06)
            await write(owned, data)
        task = asyncio.create_task(finish())
        frame = await capture.capture(trigger, timeout_seconds=1)
        await task
        assert frame.encoded_bytes == data
    asyncio.run(scenario())


@pytest.mark.parametrize('mode', ['failure', 'timeout', 'cancel', 'identity'])
def test_uncertain_trigger_and_binding_poison(owned, mode):
    async def scenario():
        capture = collector(owned)

        async def trigger():
            if mode == 'failure':
                raise RuntimeError('trigger failed')
            if mode == 'cancel':
                raise asyncio.CancelledError
            if mode == 'timeout':
                await asyncio.sleep(1)
            if mode == 'identity':
                old = owned[1].identity
                owned[1].identity = ProcessIdentity(old.executable, old.command_line, 'reused')
                await write(owned, picture())
        error = {'failure': RuntimeError, 'cancel': asyncio.CancelledError,
                 'timeout': TimeoutError, 'identity': ValueError}[mode]
        with pytest.raises(error):
            await capture.capture(trigger, timeout_seconds=.06)
        with pytest.raises(ValueError, match='uncertain'):
            await capture.capture(trigger, timeout_seconds=1)
    asyncio.run(scenario())


def test_impostor_session_rejected():
    from psp_buddy.capture import ScreenshotCapture
    with pytest.raises(ValueError, match='LaunchSession'):
        ScreenshotCapture(object(), (16, 12))


def test_unstable_new_file_read_waits(owned, monkeypatch):
    async def scenario():
        capture = collector(owned)
        original = capture._read
        unstable = True

        def read(path):
            nonlocal unstable
            if unstable:
                unstable = False
                return None
            return original(path)
        monkeypatch.setattr(capture, '_read', read)
        frame = await capture.capture(lambda: write(owned, picture()), timeout_seconds=1)
        assert frame.sequence == 1
    asyncio.run(scenario())


def test_concurrent_requests_serialize_before_trigger(owned):
    async def scenario():
        capture = collector(owned)
        calls = []

        async def trigger(number):
            calls.append(number)
            await asyncio.sleep(.03)
            await write(owned, picture(), f'ULJS00460_{number:05}.png')
        frames = await asyncio.gather(
            capture.capture(lambda: trigger(0), timeout_seconds=1),
            capture.capture(lambda: trigger(1), timeout_seconds=1))
        assert calls == [0, 1]
        assert [frame.sequence for frame in frames] == [1, 2]
    asyncio.run(scenario())


def test_expired_baseline_never_triggers_and_poisoned(owned, monkeypatch):
    import time

    async def scenario():
        capture = collector(owned)
        original = capture._inventory
        called = False

        def slow_inventory(**kwargs):
            time.sleep(.03)
            return original(**kwargs)

        async def trigger():
            nonlocal called
            called = True

        monkeypatch.setattr(capture, '_inventory', slow_inventory)
        with pytest.raises(TimeoutError):
            await capture.capture(trigger, timeout_seconds=.01)
        assert not called
        with pytest.raises(ValueError, match='uncertain'):
            await capture.capture(trigger, timeout_seconds=1)
    asyncio.run(scenario())
