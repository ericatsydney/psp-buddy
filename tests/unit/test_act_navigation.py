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
        for n in range(2, 60):
            sim.units[0].update(counted_as_unmoved=True, moved=False, tile_x=5, tile_y=5)
            sim.cursor = [5, 5]
            try:
                await service.execute('act', frame(sequence=n, **request(move_to=[6, 5])))
            except NavigationRefused:
                break
        assert 9 < n <= 41                               # at most 40 acts per trial
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


def test_attack_may_carry_a_weapon_slot_and_it_must_be_an_integer(owned, tmp_path):
    sim = shifted_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    with_slot = dict(move_to=[5, 7], attack={'weapon': 'BeamRifle', 'slot': 3,
                                              'target_object': BASE + 2000})

    async def scenario():
        for bad in ('3', True, -1, 21):
            broken = dict(with_slot, attack=dict(with_slot['attack'], slot=bad))
            with pytest.raises(NavigationRefused):
                await service.execute('act', frame(sequence=1, **request(**broken)))
        shown = await service.execute('act', frame(sequence=1, **request(**with_slot)))
        assert shown['ok'] is True and shown['phase'] == 'forecast'
    asyncio.run(scenario())


def test_a_missing_screenshot_folder_after_an_act_does_not_disable_the_helper(owned, tmp_path):
    import shutil
    sim = shifted_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    shots = owned[0].memstick_root / 'PSP/SCREENSHOT'
    request_ = frame(sequence=1, **request(unit_object=BASE + 1001, move_to=[3, 2]))
    shutil.rmtree(shots)

    async def scenario():
        # the frame itself must exist for the request check, so recreate it, then drop the folder
        # while the macro runs
        shots.mkdir()
        (shots / request_['screen_file']).write_bytes(picture())
        real = adapter.press

        async def press(button, frames=2):
            if shots.exists():
                shutil.rmtree(shots)
            return await real(button, frames)
        adapter.press = press
        result = await service.execute('act', request_)
        assert result['ok'] is True
        assert not service._failed
    asyncio.run(scenario())


def test_plan_act_is_a_known_mailbox_operation():
    assert 'plan_act' in OPERATIONS


def plan_sim():
    return plan_sim_with()


def plan_sim_with(**flags):
    sim = shifted_sim(**flags)
    for unit in sim.units:
        unit['max_hp'] = unit['hp']
    for weapon, power in zip(sim.weapons, (1000, 2000, 3000), strict=True):
        weapon['power'] = power
    return sim


def test_plan_act_chooses_gates_fires_and_logs(owned, tmp_path):
    sim = plan_sim()
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        answer = await service.execute('plan_act', frame(
            sequence=1, policy='cheap weapons below 20%', **request()))
        assert answer['ok'] is True and answer['phase'] == 'fired'
        assert answer['plan']['act']['attack']['weapon'] == 'Grenade'
        with pytest.raises(NavigationRefused):                 # same screenshot cannot be reused
            await service.execute('plan_act', {**frame(sequence=2, policy='', **request()),
                                               'screen_file': 'a1.png'})
    asyncio.run(scenario())
    assert adapter.sent.count('start') == 1
    assert (tmp_path / 'evidence' / 'damage-log.jsonl').read_text(encoding='utf-8').count('\n') == 1


@pytest.mark.parametrize('extra', [{'policy': 'win the battle'}, {'policy': 5}, {'bosses': [1]},
                                   {'unit_object': 5}, {'move_to': [1, 2]}])
def test_plan_act_refuses_bad_requests_before_any_press(owned, tmp_path, extra):
    sim = plan_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    body = {'policy': '', **request(), **extra}

    async def scenario():
        with pytest.raises(NavigationRefused):
            await service.execute('plan_act', frame(sequence=1, **body))
    asyncio.run(scenario())
    assert adapter.sent == []


def test_plan_act_needs_the_act_declaration(owned, tmp_path):
    service, adapter, frame = make(owned, tmp_path, plan_sim(), declaration=None)

    async def scenario():
        with pytest.raises(NavigationRefused):
            await service.execute('plan_act', frame(sequence=1, policy='', **request()))
    asyncio.run(scenario())
    assert adapter.sent == []


def test_plan_act_min_hit_is_validated_and_applied(owned, tmp_path):
    sim = plan_sim()
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        for bad in (0, 101, '5'):
            with pytest.raises(NavigationRefused):
                await service.execute('plan_act', frame(sequence=1, policy='', min_hit=bad,
                                                        **request()))
        answer = await service.execute('plan_act', frame(sequence=1, policy='', min_hit=90,
                                                         **request()))
        assert answer['phase'] == 'declined' and answer['reason'] == 'hit_too_low'
    asyncio.run(scenario())
    assert 'start' not in adapter.sent


def test_turn_next_is_a_known_mailbox_operation_and_budgets_fit_a_turn():
    from psp_buddy import info_navigation
    assert 'turn_next' in OPERATIONS
    assert info_navigation.MAX_ACTS == 40 and info_navigation.MAX_ACT_PRESSES == 1000


def test_a_simulated_turn_runs_to_done_and_writes_the_report(owned, tmp_path):
    import json
    sim = plan_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    report = tmp_path / 'evidence' / 'turn-report.json'

    async def scenario():
        first = await service.execute('turn_next', {'sequence': 1})
        assert first['unit_object'] == BASE + 1000 and first['remaining'] == 2
        assert first['done'] is False and first['stopped'] is None
        fired = await service.execute('plan_act', frame(sequence=2, policy='', **request()))
        assert fired['phase'] == 'fired'
        assert json.loads(report.read_text(encoding='utf-8'))['fired'] == 1
        second = await service.execute('turn_next', {'sequence': 3})
        assert second['unit_object'] == BASE + 1001 and second['remaining'] == 1
        skipped = await service.execute('plan_act', frame(sequence=4, policy='', **request(
            unit_object=BASE + 1001)))
        assert skipped['phase'] == 'handover' and skipped['reason'] == 'no_target'
        last = await service.execute('turn_next', {'sequence': 5})
        assert last['done'] is True and last['unit_object'] is None
        assert last['skipped'] == {str(BASE + 1001): 'no_target'}
    asyncio.run(scenario())
    data = json.loads(report.read_text(encoding='utf-8'))
    assert data['fired'] == 1 and data['done'] is True and data['stopped'] is None
    assert data['skipped'] == {str(BASE + 1001): 'no_target'} and len(data['entries']) == 2
    assert adapter.sent.count('start') == 1


def test_a_failed_plan_act_stops_the_turn(owned, tmp_path):
    service, adapter, frame = make(owned, tmp_path, plan_sim_with(start_ignored=True))

    async def scenario():
        failed = await service.execute('plan_act', frame(sequence=1, policy='', **request()))
        assert failed['phase'] == 'failed'
        nxt = await service.execute('turn_next', {'sequence': 2})
        assert nxt['unit_object'] is None and nxt['done'] is False and nxt['stopped']
    asyncio.run(scenario())


def test_turn_next_takes_only_a_sequence_and_needs_no_screenshot(owned, tmp_path):
    service, adapter, frame = make(owned, tmp_path, plan_sim())

    async def scenario():
        with pytest.raises(NavigationRefused):
            await service.execute('turn_next', {'sequence': 1, 'object': 5})
        with pytest.raises(NavigationRefused):
            await service.execute('turn_next', {'sequence': 7})            # out of order
        answer = await service.execute('turn_next', {'sequence': 1})
        assert answer['sequence'] == 1
    asyncio.run(scenario())
    assert adapter.sent == []


def test_an_unwritable_turn_report_does_not_lose_the_plan_act_result(owned, tmp_path, monkeypatch):
    # The attack already happened: a report write error is reported, never raised.
    from pathlib import Path
    sim = plan_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    real = Path.write_text

    def locked(self, *args, **kwargs):
        if self.name == 'turn-report.json':
            raise PermissionError('locked')
        return real(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'write_text', locked)

    async def scenario():
        fired = await service.execute('plan_act', frame(sequence=1, policy='', **request()))
        assert fired['phase'] == 'fired' and 'locked' in fired['report_error']
        nxt = await service.execute('turn_next', {'sequence': 2})
        assert 'locked' in nxt['report_error']
    asyncio.run(scenario())


# ---- M10: End Turn and the enemy phase ------------------------------------------------------

def phase_sim(**flags):
    from test_end_turn import EnemyPhaseSim
    sim = EnemyPhaseSim(**flags)
    for u in sim.units:
        u['object'] += BASE
        u['counted_as_unmoved'] = False              # every ally has acted: turn_next is done
    return sim


def test_end_turn_operations_are_known_mailbox_operations():
    assert {'end_turn', 'enemy_phase'} <= set(OPERATIONS)


def test_a_whole_end_turn_reaches_the_next_player_phase_with_circle_only(owned, tmp_path):
    import json
    sim = phase_sim(screens=4, hit_ally=True)
    service, adapter, frame = make(owned, tmp_path, sim)
    evidence = tmp_path / 'evidence'

    async def scenario():
        assert (await service.execute('turn_next', {'sequence': 1}))['done'] is True
        opened = await service.execute('end_turn', frame(sequence=2, phase='open'))
        assert opened['ok'] is True and opened['phase'] == 'menu_open'
        assert sim.screen == 'system_menu'
        confirmed = await service.execute('end_turn', frame(
            'system_menu', sequence=3, phase='confirm', highlighted_entry='EndTurn'))
        assert confirmed['ok'] is True and confirmed['phase'] == 'ending'
        assert json.loads((evidence / 'turn-report.json').read_text(encoding='utf-8'))['ended']
        sequence, step = 4, {'phase': 'continue'}
        while step['phase'] == 'continue':
            step = await service.execute('enemy_phase', {'sequence': sequence})
            sequence += 1
        assert step['ok'] is True and step['phase'] == 'done' and step['turn'] == [7, 8]
        again = await service.execute('enemy_phase', {'sequence': sequence})
        assert again['phase'] == 'done'
    asyncio.run(scenario())
    walk = adapter.sent.index('circle')               # the cursor walk, then only Circle
    assert set(adapter.sent[:walk]) <= {'up', 'down', 'left', 'right'}
    assert set(adapter.sent[walk:]) == {'circle'}
    data = json.loads((evidence / 'enemy-phase-report.json').read_text(encoding='utf-8'))
    assert data['done'] is True and data['turn'] == [7, 8]
    assert data['damaged_allies'] == [BASE + 2]


def test_end_turn_is_refused_before_the_turn_is_done_and_out_of_order(owned, tmp_path):
    sim = phase_sim()
    sim.units[0]['counted_as_unmoved'] = True        # one ally still to play
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        with pytest.raises(NavigationRefused):        # turn_next never said done
            await service.execute('end_turn', frame(sequence=1, phase='open'))
        assert (await service.execute('turn_next', {'sequence': 1}))['done'] is False
        with pytest.raises(NavigationRefused):        # not done yet
            await service.execute('end_turn', frame(sequence=2, phase='open'))
        with pytest.raises(NavigationRefused):        # confirm without an open menu
            await service.execute('end_turn', frame('system_menu', sequence=2, phase='confirm',
                                                    highlighted_entry='EndTurn'))
        with pytest.raises(NavigationRefused):        # no enemy phase before confirm
            await service.execute('enemy_phase', {'sequence': 2})
    asyncio.run(scenario())
    assert adapter.sent == []


@pytest.mark.parametrize('bad', [
    {'context': 'map'}, {'highlighted_entry': 'Save'}, {'highlighted_entry': None},
    {'phase': 'other'}])
def test_confirm_needs_the_system_menu_with_end_turn_highlighted(owned, tmp_path, bad):
    sim = phase_sim()
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        await service.execute('end_turn', frame(sequence=2, phase='open'))
        body = {**frame('system_menu', sequence=3, phase='confirm',
                        highlighted_entry='EndTurn'), **bad}
        body = {k: v for k, v in body.items() if v is not None}
        with pytest.raises(NavigationRefused):
            await service.execute('end_turn', body)
        with pytest.raises(NavigationRefused):        # a second open is refused too
            await service.execute('end_turn', frame(sequence=3, phase='open'))
    asyncio.run(scenario())
    assert adapter.sent[-1] == 'circle' and adapter.sent.count('circle') == 1


def test_a_stopped_enemy_phase_reports_and_sends_nothing_more(owned, tmp_path):
    import json
    sim = phase_sim(screens=3, destroy_ally=True)
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        await service.execute('end_turn', frame(sequence=2, phase='open'))
        await service.execute('end_turn', frame('system_menu', sequence=3, phase='confirm',
                                                highlighted_entry='EndTurn'))
        stopped = await service.execute('enemy_phase', {'sequence': 4})
        assert stopped['ok'] is False and stopped['reason'] == 'ally_destroyed'
        sent = len(adapter.sent)
        again = await service.execute('enemy_phase', {'sequence': 5})
        assert again['reason'] == 'ally_destroyed' and len(adapter.sent) == sent
    asyncio.run(scenario())
    data = json.loads((tmp_path / 'evidence' / 'enemy-phase-report.json').read_text(
        encoding='utf-8'))
    assert data['stopped'] == 'ally_destroyed' and data['destroyed'] == [BASE + 2]


def test_enemy_phase_can_accept_a_loss_and_reach_the_next_turn(owned, tmp_path):
    import json
    sim = phase_sim(screens=3, destroy_ally=True)
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        await service.execute('end_turn', frame(sequence=2, phase='open'))
        await service.execute('end_turn', frame('system_menu', sequence=3, phase='confirm',
                                                highlighted_entry='EndTurn'))
        first = await service.execute('enemy_phase', {'sequence': 4})
        assert first['reason'] == 'ally_destroyed'
        for bad in ('yes', 1, None):
            with pytest.raises(NavigationRefused):
                await service.execute('enemy_phase', {'sequence': 5, 'accept_losses': bad})
        done = await service.execute('enemy_phase', {'sequence': 5, 'accept_losses': True})
        assert done['phase'] == 'done' and done['turn'] == [7, 8]
    asyncio.run(scenario())
    data = json.loads((tmp_path / 'evidence' / 'enemy-phase-report.json').read_text(
        encoding='utf-8'))
    assert data['done'] is True and data['losses'] == {str(BASE + 2): 'ally_destroyed'}
