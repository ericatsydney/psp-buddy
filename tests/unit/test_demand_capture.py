import asyncio
import base64
import json

import pytest
from test_capture import owned as owned
from test_capture import picture
from test_debugger import FakeTransport

from psp_buddy.debugger import DebuggerAdapter


class RenderTransport(FakeTransport):
    def __init__(self, data=None, *, stepping=False, paused=False, fail_resume=False):
        super().__init__(stepping=stepping, paused=paused)
        self.data = picture() if data is None else data
        self.fail_resume = fail_resume

    async def send(self, message):
        request = json.loads(message)
        if request['event'] == 'gpu.buffer.renderColor':
            self.sent.append(request)
            await self.messages.put({
                **request, 'width': 16, 'height': 12,
                'uri': 'data:image/png;base64,' + base64.b64encode(self.data).decode(),
            })
        elif request['event'] == 'cpu.resume' and self.fail_resume:
            raise ConnectionError('resume failed')
        else:
            await super().send(message)


def service(owned, transport=None):
    from psp_buddy.demand_capture import DemandCapture

    session = owned[0]
    transport = transport or RenderTransport()
    adapter = DebuggerAdapter(transport, timeout_seconds=.1)
    adapter._assert_bound = session.assert_bound
    return DemandCapture(session, adapter), adapter, transport


def test_capture_is_demanded_and_identical_screens_are_fresh_acquisitions(owned):
    async def scenario():
        capture, adapter, transport = service(owned)
        assert transport.sent == []
        first = await capture.capture('new command menu')
        second = await capture.capture('verify ambiguous same screen')
        assert first['sequence'] == 1 and second['sequence'] == 2
        assert first['sha256'] == second['sha256']
        assert first['path'] != second['path']
        assert first['trial_id'] == owned[0].receipt.trial_id
        assert first['pause_before'] == [False, False]
        assert first['pause_after'] is False
        assert adapter.pause_status is False
        assert not transport.stepping
        assert len([x for x in transport.sent if x['event'].startswith('gpu.')]) == 2
        from pathlib import Path
        assert Path(first['path']).read_bytes() == picture()
        metadata = json.loads(Path(first['metadata_path']).read_text())
        assert metadata == first
    asyncio.run(scenario())


@pytest.mark.parametrize('bad', [b'raw pixels', picture(blank=True), picture(fmt='JPEG')])
def test_bad_images_disable_capture_and_never_publish_success(owned, bad):
    async def scenario():
        capture, _, transport = service(owned, RenderTransport(bad))
        with pytest.raises(ValueError):
            await capture.capture('new screen')
        sent = len(transport.sent)
        with pytest.raises(RuntimeError, match='disabled'):
            await capture.capture('retry prohibited')
        assert len(transport.sent) == sent
        assert not list(capture.root.glob('*.json'))
    asyncio.run(scenario())


def test_restoration_failure_never_returns_a_capture(owned):
    async def scenario():
        capture, adapter, _ = service(owned, RenderTransport(fail_resume=True))
        with pytest.raises(ConnectionError, match='resume'):
            await capture.capture('new forecast')
        assert adapter.uncertain
        assert not list(capture.root.glob('*.json'))
    asyncio.run(scenario())


def test_prior_pause_is_preserved(owned):
    async def scenario():
        capture, _, transport = service(owned, RenderTransport(stepping=True))
        result = await capture.capture('ambiguous menu')
        assert result['pause_before'] == [True, False]
        assert result['pause_after'] is True
        assert not any(x['event'] == 'cpu.resume' for x in transport.sent)
    asyncio.run(scenario())


@pytest.mark.parametrize('reason', ['', ' ', 'x' * 513, None])
def test_missing_visual_need_is_rejected_before_io(owned, reason):
    async def scenario():
        capture, _, transport = service(owned)
        with pytest.raises(ValueError, match='reason'):
            await capture.capture(reason)
        assert transport.sent == []
    asyncio.run(scenario())


def test_unbound_adapter_is_rejected(owned):
    from psp_buddy.demand_capture import DemandCapture

    with pytest.raises(ValueError, match='bound'):
        DemandCapture(owned[0], DebuggerAdapter(RenderTransport()))


def test_replaced_receipt_is_rejected(owned):
    from dataclasses import replace

    owned[0].receipt = replace(owned[0].receipt, trial_id='not-the-launch-receipt')
    with pytest.raises(ValueError, match='receipt'):
        service(owned)


def test_concurrent_demands_are_serialized(owned):
    async def scenario():
        capture, _, _ = service(owned)
        results = await asyncio.gather(capture.capture('menu'), capture.capture('forecast'))
        assert [r['sequence'] for r in results] == [1, 2]
    asyncio.run(scenario())


def test_identity_change_prevents_gpu_request(owned):
    async def scenario():
        capture, _, transport = service(owned)
        from psp_buddy.launch import ProcessIdentity
        old = owned[1].identity
        owned[1].identity = ProcessIdentity(old.executable, old.command_line, 'changed')
        with pytest.raises(ValueError, match='identity'):
            await capture.capture('menu')
        assert transport.sent == []
    asyncio.run(scenario())


def test_waiting_for_another_capture_has_a_deadline(owned):
    async def scenario():
        capture, _, transport = service(owned)
        await capture._lock.acquire()
        task = asyncio.create_task(capture.capture('menu', timeout_seconds=.01))
        try:
            completed, _ = await asyncio.wait({task}, timeout=.07)
            assert task in completed, 'capture deadline must include waiting for controller'
            with pytest.raises(TimeoutError):
                await task
        finally:
            capture._lock.release()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        assert transport.sent == []
    asyncio.run(scenario())


@pytest.mark.parametrize('mutation', ['raw', 'base64', 'oversize', 'width', 'bool', 'huge'])
def test_protocol_image_bounds(mutation):
    from psp_buddy.demand_capture import MAX_PNG_BYTES, PNG_PREFIX, decode_render_png

    response = {'uri': PNG_PREFIX + base64.b64encode(picture()).decode(),
                'width': 16, 'height': 12}
    if mutation == 'raw':
        response = {'base64': 'AAAA', 'width': 16, 'height': 12}
    elif mutation == 'base64':
        response['uri'] = PNG_PREFIX + '!!!!'
    elif mutation == 'oversize':
        response['uri'] = PNG_PREFIX + 'A' * (4 * ((MAX_PNG_BYTES + 2) // 3) + 1)
    elif mutation == 'width':
        response['width'] = 17
    elif mutation == 'bool':
        response['width'] = True
    else:
        data = picture(size=(4097, 2))
        response = {'uri': PNG_PREFIX + base64.b64encode(data).decode(),
                    'width': 4097, 'height': 2}
    with pytest.raises(ValueError):
        decode_render_png(response)


def test_node_bridge_and_python_controller_round_trip(owned):
    import shutil
    import subprocess
    import time

    from psp_buddy.capture_mailbox import CaptureMailbox

    node = shutil.which('node')
    if node is None:
        pytest.skip('Node is optional for the local MCP bridge')

    async def scenario():
        capture, _, transport = service(owned)
        mailbox = CaptureMailbox(capture, owned[0].receipt.trial_id, capture.root / 'mailbox')
        source = (
            "import {createCaptureClient} from './tools/ppsspp_capture_mcp.mjs';"
            "const c=await createCaptureClient(process.argv[1],process.argv[2]);"
            "const r=await c.capture(' synthetic cross-language menu ');"
            "console.log(r.content[0].text);"
        )
        process = subprocess.Popen(
            [node, '--input-type=module', '-e', source, str(mailbox.root), mailbox.trial_id],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        deadline = time.monotonic() + 20
        try:
            while process.poll() is None and time.monotonic() < deadline:
                await mailbox.serve_once()
                await asyncio.sleep(.01)
            assert process.poll() is not None, 'synthetic MCP client did not complete'
            stdout, stderr = process.communicate(timeout=2)
            assert process.returncode == 0, stderr
            result = json.loads(stdout)
            assert result['trial_id'] == mailbox.trial_id
            assert result['reason'] == ' synthetic cross-language menu '
            assert result['sequence'] == 1
            assert len([x for x in transport.sent if x['event'].startswith('gpu.')]) == 1
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    asyncio.run(scenario())
