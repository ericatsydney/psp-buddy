# ruff: noqa: F811
import asyncio

import pytest
from test_action_navigation import press, setup
from test_capture import owned, picture  # noqa: F401

from psp_buddy.navigation_mailbox import OPERATIONS, NavigationRefused

DESTINY_OBJECT = 149303288


def service_with(owned, tmp_path, reader):
    from psp_buddy.info_navigation import InfoNavigation
    base, transport, frame, _ = setup(owned, tmp_path)
    service = InfoNavigation(owned[0], base._adapter, (19, 5), tmp_path / 'w', base._verify,
                             read_weapons=reader)
    return service, transport, frame


def test_weapons_operation_is_known_to_the_mailbox():
    assert 'weapons' in OPERATIONS


def test_weapon_read_takes_an_object_sends_no_input_and_shares_the_sequence(owned, tmp_path):
    calls = []

    async def reader(n, unit_object):
        calls.append((n, unit_object))
        return {'mech_name': 'Destiny Gundam', 'weapons': [{'name': '17.5mmCIWS'}]}

    service, transport, frame = service_with(owned, tmp_path, reader)

    async def scenario():
        result = await service.execute('weapons', {'sequence': 1, 'object': DESTINY_OBJECT})
        assert result['mech_name'] == 'Destiny Gundam'
        assert result['sequence'] == 1 and result['weapon_read'] == 1
        with pytest.raises(ValueError):                          # sequence already used
            await service.execute('weapons', {'sequence': 1, 'object': DESTINY_OBJECT})
        for bad in ({'sequence': 2}, {'sequence': 2, 'object': '1'},
                    {'sequence': 2, 'object': 5}, {'sequence': 2, 'object': True},
                    {'sequence': 2, 'object': DESTINY_OBJECT, 'screen_file': 'x.png'}):
            with pytest.raises(ValueError):
                await service.execute('weapons', bad)
        await press(service, frame, 2, 'map', 'cursor', button='right')
        await service.execute('weapons', {'sequence': 3, 'object': DESTINY_OBJECT})
    sent_before = len(transport.sent)
    asyncio.run(scenario())
    assert calls == [(1, DESTINY_OBJECT), (2, DESTINY_OBJECT)]
    assert len(transport.sent) > sent_before   # only the press sent anything


def test_weapon_reads_are_bounded_and_need_a_reader(owned, tmp_path):
    async def reader(n, unit_object):
        return {'weapons': []}

    service, _, _ = service_with(owned, tmp_path, reader)

    async def scenario():
        for n in range(1, 201):
            await service.execute('weapons', {'sequence': n, 'object': DESTINY_OBJECT})
        with pytest.raises(ValueError):
            await service.execute('weapons', {'sequence': 201, 'object': DESTINY_OBJECT})
    asyncio.run(scenario())
    bare, _, _, _ = setup(owned, tmp_path / 'bare')
    with pytest.raises(ValueError):
        asyncio.run(bare.execute('weapons', {'sequence': 1, 'object': DESTINY_OBJECT}))


def test_weapon_refusal_and_oversize_keep_the_session_usable(owned, tmp_path):
    modes = ['refused', 'bad-memory', 'huge', 'ok']

    async def reader(n, unit_object):
        mode = modes.pop(0)
        if mode == 'refused':
            raise NavigationRefused('unit not on the map')
        if mode == 'bad-memory':
            raise ValueError('invalid weapon record pointer')
        if mode == 'huge':
            return {'blob': 'x' * 20000}
        return {'weapons': []}

    service, _, _ = service_with(owned, tmp_path, reader)

    async def scenario():
        for _ in range(3):
            with pytest.raises(NavigationRefused):
                await service.execute('weapons', {'sequence': 1, 'object': DESTINY_OBJECT})
        result = await service.execute('weapons', {'sequence': 1, 'object': DESTINY_OBJECT})
        assert result['sequence'] == 1 and result['weapon_read'] == 1
    asyncio.run(scenario())
