# ruff: noqa: F811
import asyncio
import hashlib

import pytest
from test_act import SimGame
from test_capture import owned, picture  # noqa: F401

from psp_buddy.navigation_mailbox import OPERATIONS, NavigationRefused

BASE = 149_000_000
DECL = {'unit': 'any', 'actions': ['act']}


def shifted_sim(**flags):
    sim = SimGame(**flags)
    for unit in sim.units:
        unit['object'] += BASE
    return sim


class SimAdapter:
    def __init__(self, sim):
        self.sim = sim
        self.sent = []

    async def press(self, button, frames=2):
        self.sent.append(button)
        await self.sim.press(button, frames)
        return True


def make(owned, tmp_path, sim, declaration=DECL, **kw):
    from psp_buddy.info_navigation import InfoNavigation
    adapter = SimAdapter(sim)

    async def verify():
        return {}

    async def state(n):
        return await sim.state()

    async def weapons(n, obj):
        return await sim.read_weapons(obj)

    async def hit(n):
        return await sim.hit()

    async def cursor():
        return sim.cursor[0], sim.cursor[1]

    async def row():
        return await sim.menu_row()

    service = InfoNavigation(
        owned[0], adapter, (5, 5), tmp_path / 'evidence', verify, declaration=declaration,
        read_state=state, read_weapons=weapons, read_hit=hit, read_cursor=cursor,
        read_menu_row=row, map_size=(24, 34), poll_seconds=0, settle_seconds=0,
        act_time_scale=0, **kw)
    root = owned[0].memstick_root / 'PSP/SCREENSHOT'
    root.mkdir(exist_ok=True)
    counter = [0]

    def frame(context='map', **extra):
        counter[0] += 1
        path = root / f'a{counter[0]}.png'
        data = picture()
        path.write_bytes(data)
        return dict(screen_file=path.name, screen_sha256=hashlib.sha256(data).hexdigest(),
                    context=context, **extra)
    return service, adapter, frame


def request(**kw):
    base = {'unit_object': BASE + 1000}
    base.update(kw)
    return base


MOVE_ATTACK = dict(move_to=[5, 7], attack={'weapon': 'BeamRifle', 'target_object': BASE + 2000})


def test_act_is_a_known_mailbox_operation():
    assert 'act' in OPERATIONS


def test_act_runs_a_whole_instruction_and_a_second_unit(owned, tmp_path):
    sim = shifted_sim()
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        first = await service.execute('act', frame(sequence=1, commit=True,
                                                   **request(**MOVE_ATTACK)))
        assert first['ok'] is True and first['phase'] == 'done' and first['sequence'] == 1
        second = await service.execute('act', frame(sequence=2, **request(
            unit_object=BASE + 1001, move_to=[3, 2])))
        assert second['ok'] is True and second['phase'] == 'moved'
    asyncio.run(scenario())
    assert 'start' in adapter.sent and set(adapter.sent) <= act_buttons()


def act_buttons():
    return {'up', 'down', 'left', 'right', 'circle', 'cross', 'start'}


def test_two_phase_flow_needs_the_same_instruction_and_a_forecast_screen(owned, tmp_path):
    sim = shifted_sim()
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        shown = await service.execute('act', frame(sequence=1, **request(**MOVE_ATTACK)))
        assert shown['phase'] == 'forecast' and 'start' not in adapter.sent
        with pytest.raises(NavigationRefused):                 # a new run while a forecast is open
            await service.execute('act', frame(sequence=2, **request(**MOVE_ATTACK)))
        with pytest.raises(NavigationRefused):                 # fire with another instruction
            await service.execute('act', frame('attack_forecast', sequence=2, phase='fire',
                                               **request(move_to=[5, 7], attack={
                                                   'weapon': 'Vulcan',
                                                   'target_object': BASE + 2000})))
        with pytest.raises(NavigationRefused):                 # fire on the wrong screen context
            await service.execute('act', frame('map', sequence=2, phase='fire',
                                               **request(**MOVE_ATTACK)))
        done = await service.execute('act', frame('attack_forecast', sequence=2, phase='fire',
                                                  **request(**MOVE_ATTACK)))
        assert done['ok'] is True and done['phase'] == 'done'
        with pytest.raises(NavigationRefused):                 # nothing pending any more
            await service.execute('act', frame('attack_forecast', sequence=3, phase='fire',
                                               **request(**MOVE_ATTACK)))
    asyncio.run(scenario())
    assert adapter.sent.count('start') == 1


def test_act_needs_the_act_declaration_and_blocks_manual_battle_presses(owned, tmp_path):
    sim = shifted_sim()
    for declaration in (None, {'unit': 'Destiny', 'actions': ['move'],
                               'destination_tile': [5, 6]}):
        service, adapter, frame = make(owned, tmp_path / str(declaration), sim,
                                       declaration=declaration)
        with pytest.raises(NavigationRefused):
            asyncio.run(service.execute('act', frame(sequence=1, **request(move_to=[6, 5]))))
        assert adapter.sent == []
    service, adapter, frame = make(owned, tmp_path / 'act', sim)
    with pytest.raises(NavigationRefused):
        asyncio.run(service.execute('press', frame('unit_commands', sequence=1, button='circle',
                                                   duration=2, purpose='open_move',
                                                   highlighted_entry='Move')))
    assert adapter.sent == []


@pytest.mark.parametrize('extra', [
    dict(context='info'),
    dict(unit_object=5),
    dict(unit_object=True),
    dict(move_to=[1]),
    dict(move_to=[1, True]),
    dict(attack={'weapon': 'Vulcan'}),
    dict(attack={'weapon': 'Vulcan', 'target_object': 5}),
    dict(attack={'weapon': '', 'target_object': BASE + 2000}),
    dict(attack={'weapon': 'Vulcan', 'target_object': BASE + 2000, 'extra': 1}),
    dict(commit='yes'),
    dict(phase='other'),
    dict(button='circle'),
])
def test_act_refuses_malformed_requests_before_any_press(owned, tmp_path, extra):
    sim = shifted_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    arguments = frame(sequence=1, **request(move_to=[6, 5]))
    arguments.update(extra)
    with pytest.raises(NavigationRefused):
        asyncio.run(service.execute('act', arguments))
    assert adapter.sent == []


def test_act_screenshot_is_single_use_and_the_count_is_bounded(owned, tmp_path):
    sim = shifted_sim()
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        first = frame(sequence=1, **request(move_to=[6, 5]))
        await service.execute('act', first)
        again = dict(first, sequence=2)
        with pytest.raises(NavigationRefused):
            await service.execute('act', again)
        sim.screen = 'map'
        for n in range(2, 12):
            sim.units[0].update(counted_as_unmoved=True, moved=False, tile_x=5, tile_y=5)
            sim.cursor = [5, 5]
            try:
                await service.execute('act', frame(sequence=n, **request(move_to=[6, 5])))
            except NavigationRefused:
                break
        assert n <= 9                                    # at most 8 acts per trial
    asyncio.run(scenario())


def test_act_io_failure_is_reported_not_fatal(owned, tmp_path):
    sim = shifted_sim()
    service, adapter, frame = make(owned, tmp_path, sim)

    async def broken(n):
        raise NavigationRefused('battle state not readable now')
    service._read_state = broken

    async def scenario():
        result = await service.execute('act', frame(sequence=1, **request(move_to=[6, 5])))
        assert result['ok'] is False and result['reason'].startswith('io_error')
        sim.cursor = [5, 5]
        # the session is still usable for a plain memory read
        with pytest.raises(NavigationRefused):
            await service.execute('state', {'sequence': 2})
    asyncio.run(scenario())
