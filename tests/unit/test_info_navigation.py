# ruff: noqa: F811
import asyncio
import hashlib

import pytest
from test_capture import owned, picture  # noqa: F401
from test_debugger import FakeTransport

from psp_buddy.debugger import DebuggerAdapter


def setup(owned, tmp_path):
    from psp_buddy.info_navigation import InfoNavigation
    session, _ = owned
    transport = FakeTransport()
    adapter = DebuggerAdapter(transport)
    adapter._assert_bound = session.assert_bound
    async def observe():
        return {'unit': 'Destiny', 'hp': 5200}
    service = InfoNavigation(session, adapter, (3, 4), tmp_path / 'evidence', observe)
    root = session.memstick_root / 'PSP/SCREENSHOT'
    root.mkdir(exist_ok=True)
    def frame(sequence=1, context='map', **extra):
        path = root / f'frame{sequence}.png'
        data = picture()
        path.write_bytes(data)
        return dict(sequence=sequence, screen_file=path.name,
                    screen_sha256=hashlib.sha256(data).hexdigest(), context=context, **extra)
    return service, transport, frame


def test_reject_unsafe_confirm_before_io(owned, tmp_path):
    service, transport, frame = setup(owned, tmp_path)
    with pytest.raises(ValueError):
        asyncio.run(service.execute('press', frame(button='circle', duration=2, purpose='attack')))
    assert not transport.sent


def test_valid_navigation_and_terminal(owned, tmp_path):
    service, transport, frame = setup(owned, tmp_path)
    async def scenario():
        await service.execute('press', frame(button='circle', duration=2,
                              purpose='open_unit_menu', cursor_tile=[3, 4]))
        await service.execute('press', frame(2, 'unit_commands', button='circle', duration=2,
                              purpose='open_info', highlighted_entry='Info'))
        result = await service.execute('verify', frame(3, 'info'))
        assert result['hp'] == 5200
        with pytest.raises(ValueError):
            await service.execute('press', frame(4, button='right', duration=2, purpose='cursor'))
    asyncio.run(scenario())


@pytest.mark.parametrize('patch', [dict(screen_sha256='0'*64), dict(sequence=2),
                                  dict(unexpected=True), dict(duration=True),
                                  dict(button='start'), dict(cursor_tile=[9, 9])])
def test_invalid_requests(owned, tmp_path, patch):
    service, transport, frame = setup(owned, tmp_path)
    args = frame(button='circle', duration=2, purpose='open_unit_menu', cursor_tile=[3, 4])
    args.update(patch)
    with pytest.raises(ValueError):
        asyncio.run(service.execute('press', args))
    assert not transport.sent


def test_old_frame_cannot_confirm_after_press(owned, tmp_path):
    service, _, frame = setup(owned, tmp_path)
    args = frame(2, 'unit_commands', button='circle', duration=2,
                 purpose='open_info', highlighted_entry='Info')
    async def scenario():
        await service.execute('press', frame(button='right', duration=2, purpose='cursor'))
        with pytest.raises(ValueError, match='fresh'):
            await service.execute('press', args)
    asyncio.run(scenario())
