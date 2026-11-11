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


def test_plan_act_accepts_boss_names_and_keeps_foe_names_for_the_trial(owned, tmp_path):
    sim = plan_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    answer = asyncio.run(service.execute('plan_act', frame(
        sequence=1, policy='target non-bosses before bosses', boss_names=['Mercurius'],
        **request())))
    assert answer['ok'] is True
    assert set(service._mech_names) == {u['object'] for u in sim.units
                                        if u['raw_menu_group_byte'] == 12}


def test_plan_act_accepts_a_policy_text_up_to_800_characters(owned, tmp_path):
    # m16-j (3 Nov): the runner's policy grew to 402 characters and the 400 limit refused it.
    sim = plan_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    text = ('cheap weapons below 20%; ' * 32)[:800]
    answer = asyncio.run(service.execute('plan_act', frame(sequence=1, policy=text, **request())))
    assert answer['ok'] is True
    with pytest.raises(NavigationRefused):
        asyncio.run(service.execute('plan_act', frame(sequence=2, policy=text + ';',
                                                      **request())))


def test_plan_act_leaves_a_protected_unit_alone(owned, tmp_path):
    sim = plan_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    answer = asyncio.run(service.execute('plan_act', frame(
        sequence=1, policy='', protected=[BASE + 1000], **request())))
    assert answer['phase'] == 'handover' and answer['reason'] == 'protected'
    assert adapter.sent == []


@pytest.mark.parametrize('extra', [{'policy': 'win the battle'}, {'policy': 5}, {'bosses': [1]},
                                   {'protected': [1]}, {'protected': 'x'},
                                   {'protected': [BASE] * 27},
                                   {'unit_object': 5}, {'move_to': [1, 2]},
                                   {'boss_names': 'Mercurius'}, {'boss_names': ['']},
                                   {'boss_names': ['x' * 33]}, {'boss_names': ['a'] * 9}])
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


def test_plan_act_logs_rejected_ranges_in_the_evidence_folder(owned, tmp_path, monkeypatch):
    from psp_buddy import plan_act
    seen = {}

    async def fake(*_args, **kwargs):
        seen.update(kwargs)
        return {'ok': False, 'phase': 'handover', 'reason': 'no_target', 'moved': False}

    monkeypatch.setattr(plan_act, 'plan_and_act', fake)
    service, _adapter, frame = make(owned, tmp_path, plan_sim())

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        await service.execute('plan_act', frame(sequence=2, policy='', **request()))
    asyncio.run(scenario())
    assert seen['range_log'] == tmp_path / 'evidence' / 'rejected-ranges.jsonl'


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


# ---- M13: clear the non-boss foes, then hand over -------------------------------------------

def named_sim(names):
    """plan_sim whose weapon reads carry foe mech names; counts the reads."""
    sim = plan_sim()
    real, reads = sim.read_weapons, []

    async def read_weapons(obj):
        reads.append(obj)
        answer = await real(obj)
        return {**answer, 'mech_name': names.get(obj, 'Taurus')}
    sim.read_weapons = read_weapons
    return sim, reads


def drop(sim, obj):
    sim.units = [u for u in sim.units if u['object'] != obj]


INPUTS = ('press', 'goto', 'act', 'plan_act', 'probe_move', 'end_turn', 'enemy_phase')


def test_turn_next_reports_the_clear_status_and_reads_each_foe_name_once(owned, tmp_path):
    sim, reads = named_sim({BASE + 2000: 'Mercurius'})
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        first = await service.execute('turn_next', {'sequence': 1})
        assert first['clear'] == {'nonboss_left': [BASE + 2001], 'bosses': [BASE + 2000],
                                  'turn': 7}
        assert first['handover'] is None and first['unit_object'] == BASE + 1000
        assert sorted(reads) == [BASE + 2000, BASE + 2001]
        second = await service.execute('turn_next', {'sequence': 2})
        assert second['clear']['nonboss_left'] == [BASE + 2001]
        assert len(reads) == 2                               # names are cached
    asyncio.run(scenario())
    assert adapter.sent == []


def test_only_bosses_left_hands_over_cleared_and_locks_every_input(owned, tmp_path):
    import json
    sim, _ = named_sim({BASE + 2000: 'Mercurius'})
    service, adapter, frame = make(owned, tmp_path, sim)
    handover = tmp_path / 'evidence' / 'handover.json'

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        drop(sim, BASE + 2001)                               # the last non-boss is destroyed
        answer = await service.execute('turn_next', {'sequence': 2})
        assert answer['handover'] == {'reason': 'cleared'}
        assert answer['unit_object'] is None and answer['done'] is False
        data = json.loads(handover.read_text(encoding='utf-8'))
        assert data['reason'] == 'cleared' and data['nonboss_destroyed'] == [BASE + 2001]
        assert data['bosses'][0]['name'] == 'Mercurius' and data['lost'] == []
        for operation in INPUTS:
            with pytest.raises(NavigationRefused, match='handed over'):
                await service.execute(operation, frame(sequence=3, policy='', **request()))
        assert (await service.execute('state', {'sequence': 3}))['sequence'] == 3
        again = await service.execute('turn_next', {'sequence': 4})
        assert again['handover'] == {'reason': 'cleared'} and again['unit_object'] is None
    asyncio.run(scenario())
    assert adapter.sent == []


def test_an_ally_loss_hands_over_before_the_next_unit(owned, tmp_path):
    import json
    sim, _ = named_sim({})
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        drop(sim, BASE + 1001)                               # e.g. destroyed by a counter
        answer = await service.execute('turn_next', {'sequence': 2})
        assert answer['handover'] == {'reason': 'ally_lost'} and answer['unit_object'] is None
        data = json.loads((tmp_path / 'evidence' / 'handover.json').read_text(encoding='utf-8'))
        assert data['lost'] == [BASE + 1001]
    asyncio.run(scenario())


def test_a_stopped_turn_hands_over_with_its_reason(owned, tmp_path):
    service, adapter, frame = make(owned, tmp_path, plan_sim_with(start_ignored=True))

    async def scenario():
        failed = await service.execute('plan_act', frame(sequence=1, policy='', **request()))
        assert failed['phase'] == 'failed'
        nxt = await service.execute('turn_next', {'sequence': 2})
        assert nxt['handover'] == {'reason': f"stopped:{nxt['stopped']}"}
        with pytest.raises(NavigationRefused, match='handed over'):
            await service.execute('plan_act', frame(sequence=3, policy='', **request()))
    asyncio.run(scenario())


def test_an_unwritable_handover_report_is_reported_and_the_lock_holds(owned, tmp_path,
                                                                       monkeypatch):
    from pathlib import Path
    sim, _ = named_sim({BASE + 2000: 'Mercurius'})
    service, adapter, frame = make(owned, tmp_path, sim)
    real = Path.write_text

    def locked(self, *args, **kwargs):
        if self.name == 'handover.json':
            raise PermissionError('locked')
        return real(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'write_text', locked)

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        drop(sim, BASE + 2001)
        answer = await service.execute('turn_next', {'sequence': 2})
        assert answer['handover'] == {'reason': 'cleared'} and 'locked' in answer['report_error']
        with pytest.raises(NavigationRefused, match='handed over'):
            await service.execute('plan_act', frame(sequence=3, policy='', **request()))
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
        with pytest.raises(NavigationRefused):        # M13: turn 8 is a new player turn
            await service.execute('enemy_phase', {'sequence': sequence})
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


async def end_the_turn(service, frame, sequence):
    """turn_next (done) -> End Turn open/confirm -> enemy_phase until not continue."""
    assert (await service.execute('turn_next', {'sequence': sequence}))['done'] is True
    await service.execute('end_turn', frame(sequence=sequence + 1, phase='open'))
    await service.execute('end_turn', frame('system_menu', sequence=sequence + 2,
                                            phase='confirm', highlighted_entry='EndTurn'))
    sequence, step = sequence + 3, {'phase': 'continue'}
    while step['phase'] == 'continue':
        step = await service.execute('enemy_phase', {'sequence': sequence})
        sequence += 1
    return step, sequence


def test_a_finished_enemy_phase_starts_a_new_player_turn(owned, tmp_path):
    from psp_buddy import info_navigation
    sim = phase_sim(screens=2)
    service, adapter, frame = make(owned, tmp_path, sim)
    evidence = tmp_path / 'evidence'

    async def scenario():
        step, seq = await end_the_turn(service, frame, 1)
        assert step['phase'] == 'done' and step['turn'] == [7, 8]
        assert (evidence / 'turn-report-7.json').is_file()
        assert (evidence / 'enemy-phase-report-7.json').is_file()
        sim.player_turn = 8                              # the allies are reset and stay so
        nxt = await service.execute('turn_next', {'sequence': seq})
        assert nxt['unit_object'] in (BASE + 1, BASE + 2) and nxt['remaining'] == 2
        assert nxt['done'] is False and nxt['handover'] is None
        assert nxt['clear']['turn'] == 8
        with pytest.raises(NavigationRefused, match='turn done'):    # a fresh turn, not "started"
            await service.execute('end_turn', frame(sequence=seq + 1, phase='open'))
        guarded = await service.execute('plan_act', frame(sequence=seq + 1, policy='',
                                                          protected=[BASE + 1],
                                                          **request(unit_object=BASE + 1)))
        assert guarded['phase'] == 'handover' and guarded['reason'] == 'protected'
        for u in sim.units:                              # every ally has acted in turn 8
            u['counted_as_unmoved'] = False
        sim.screens = 2
        step, seq = await end_the_turn(service, frame, seq + 2)
        assert step['phase'] == 'done' and step['turn'] == [8, 9]
        assert (evidence / 'turn-report-8.json').is_file()
    asyncio.run(scenario())
    assert info_navigation.MAX_PLAYER_TURNS == 6


def test_the_per_turn_budgets_start_again_but_taps_and_dumps_do_not(owned, tmp_path):
    from psp_buddy import info_navigation
    sim = phase_sim(screens=2)
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        service._acts = info_navigation.MAX_ACTS          # turn 7 used every act
        service._taps, service._dumps = 3, 2
        with pytest.raises(NavigationRefused):
            await service.execute('plan_act', frame(sequence=2, policy='', protected=[BASE + 1],
                                                    **request(unit_object=BASE + 1)))
        step, seq = await end_the_turn(service, frame, 2)
        assert step['phase'] == 'done'
        sim.player_turn = 8
        await service.execute('turn_next', {'sequence': seq})
        guarded = await service.execute('plan_act', frame(sequence=seq + 1, policy='',
                                                          protected=[BASE + 1],
                                                          **request(unit_object=BASE + 1)))
        assert guarded['reason'] == 'protected'
        assert (service._taps, service._dumps) == (3, 2)
    asyncio.run(scenario())


def test_the_player_turn_limit_hands_over(owned, tmp_path, monkeypatch):
    from psp_buddy import info_navigation
    monkeypatch.setattr(info_navigation, 'MAX_PLAYER_TURNS', 1)
    sim = phase_sim(screens=2)
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        step, seq = await end_the_turn(service, frame, 1)
        assert step['phase'] == 'done'
        sim.player_turn = 8
        nxt = await service.execute('turn_next', {'sequence': seq})
        assert nxt['handover'] == {'reason': 'player_turn_limit'} and nxt['unit_object'] is None
        with pytest.raises(NavigationRefused, match='handed over'):
            await service.execute('plan_act', frame(sequence=seq + 1, policy='',
                                                    **request(unit_object=BASE + 1)))
    asyncio.run(scenario())


def test_a_stopped_enemy_phase_hands_over_with_its_reason(owned, tmp_path):
    import json
    sim = phase_sim(screens=3, destroy_ally=True)
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        step, seq = await end_the_turn(service, frame, 1)
        assert step['phase'] == 'stopped' and step['reason'] == 'ally_destroyed'
        nxt = await service.execute('turn_next', {'sequence': seq})
        assert nxt['handover'] == {'reason': 'ally_destroyed'}
        data = json.loads((tmp_path / 'evidence' / 'handover.json').read_text(encoding='utf-8'))
        assert data['reason'] == 'ally_destroyed' and data['screen_state'] == 'after_stop'
        assert data['lost'] == [BASE + 2]
        sent = len(adapter.sent)
        with pytest.raises(NavigationRefused, match='handed over'):
            await service.execute('enemy_phase', {'sequence': seq + 1})
        assert len(adapter.sent) == sent
    asyncio.run(scenario())


def test_an_unreadable_state_hands_over_instead_of_playing_on(owned, tmp_path):
    sim, _ = named_sim({})
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        sim.units[-1]['en'] = None                       # lost_allies cannot read this state
        answer = await service.execute('turn_next', {'sequence': 2})
        assert answer['handover'] == {'reason': 'state_unreadable'}
        assert answer['unit_object'] is None
        with pytest.raises(NavigationRefused, match='handed over'):
            await service.execute('plan_act', frame(sequence=3, policy='', **request()))
    asyncio.run(scenario())


def test_the_player_turn_limit_locks_input_before_any_turn_next(owned, tmp_path, monkeypatch):
    import json

    from psp_buddy import info_navigation
    monkeypatch.setattr(info_navigation, 'MAX_PLAYER_TURNS', 1)
    sim = phase_sim(screens=2)
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        step, seq = await end_the_turn(service, frame, 1)
        sim.player_turn = 8
        with pytest.raises(NavigationRefused, match='handed over'):
            await service.execute('plan_act', frame(sequence=seq, policy='', protected=[BASE + 1],
                                                    **request(unit_object=BASE + 1)))
        await service.execute('turn_next', {'sequence': seq})
    asyncio.run(scenario())
    data = json.loads((tmp_path / 'evidence' / 'handover.json').read_text(encoding='utf-8'))
    assert data['reason'] == 'player_turn_limit'
    assert data['turn_reports'] == ['turn-report-7.json']
    assert data['enemy_phase_reports'] == ['enemy-phase-report-7.json']


def test_an_accepted_loss_does_not_leave_a_stale_enemy_phase_stop(owned, tmp_path):
    sim = phase_sim(screens=3, destroy_ally=True)
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        step, seq = await end_the_turn(service, frame, 1)
        assert step['phase'] == 'stopped' and step['reason'] == 'ally_destroyed'
        while step['phase'] != 'done':
            step = await service.execute('enemy_phase', {'sequence': seq, 'accept_losses': True})
            seq += 1
        sim.player_turn = 8
        nxt = await service.execute('turn_next', {'sequence': seq})
        assert nxt['handover'] == {'reason': 'ally_lost'}     # the clear rule, not the old stop
    asyncio.run(scenario())


def test_turn_next_hands_over_at_the_turn_budget_after_five_turns(owned, tmp_path):
    sim = phase_sim(screens=2)
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        seq = 1
        for turn in range(7, 12):                        # turns 7..11 are played
            step, seq = await end_the_turn(service, frame, seq)
            assert step['phase'] == 'done' and step['turn'] == [turn, turn + 1]
            sim.player_turn = turn + 1
            for u in sim.units:
                u['counted_as_unmoved'] = False
            sim.screens = 2
        nxt = await service.execute('turn_next', {'sequence': seq})
        assert nxt['handover'] == {'reason': 'turn_budget'} and nxt['clear']['turn'] == 12
    asyncio.run(scenario())


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


def test_no_other_input_is_accepted_once_end_turn_has_started(owned, tmp_path):
    # Spec: after End Turn only Circle (end_turn confirm, enemy_phase) may reach the game.
    sim = phase_sim(screens=3)
    service, adapter, frame = make(owned, tmp_path, sim)

    async def refused(sequence):
        sent = len(adapter.sent)
        for operation, body in (
                ('plan_act', frame(sequence=sequence, policy='', **request())),
                ('act', frame(sequence=sequence, **request(**MOVE_ATTACK))),
                ('goto', frame(sequence=sequence, target=[1, 1]))):
            with pytest.raises(NavigationRefused):
                await service.execute(operation, body)
        assert len(adapter.sent) == sent

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        await service.execute('end_turn', frame(sequence=2, phase='open'))
        await refused(3)
        await service.execute('end_turn', frame('system_menu', sequence=3, phase='confirm',
                                                highlighted_entry='EndTurn'))
        await refused(4)
    asyncio.run(scenario())


def test_the_system_menu_can_still_be_backed_out_of_before_confirm(owned, tmp_path):
    # Review 25 Oct: a wrong highlight on the MENU_SHOT must be escapable with Cross.
    sim = phase_sim(screens=3)
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        await service.execute('end_turn', frame(sequence=2, phase='open'))
        sent = len(adapter.sent)
        await service.execute('press', frame('system_menu', sequence=3, button='cross',
                                             duration=2, purpose='cancel'))
        assert len(adapter.sent) > sent
        with pytest.raises(NavigationRefused):     # the menu is closed: no confirm now
            await service.execute('end_turn', frame('system_menu', sequence=4, phase='confirm',
                                                    highlighted_entry='EndTurn'))
    asyncio.run(scenario())


def test_the_enemy_phase_is_not_cut_short_by_the_player_turn_press_budget(owned, tmp_path):
    from psp_buddy import info_navigation
    sim = phase_sim(screens=3)
    service, adapter, frame = make(owned, tmp_path, sim)

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        await service.execute('end_turn', frame(sequence=2, phase='open'))
        await service.execute('end_turn', frame('system_menu', sequence=3, phase='confirm',
                                                highlighted_entry='EndTurn'))
        service._act_presses = info_navigation.MAX_ACT_PRESSES     # the turn used it all
        done = await service.execute('enemy_phase', {'sequence': 4})
        assert done['phase'] == 'done' and done['turn'] == [7, 8]
    asyncio.run(scenario())


def spirit_sim():
    from test_spirit_cast import Spirited
    sim = Spirited()
    for unit in sim.units:
        unit['object'] += BASE
    return sim


def test_plan_act_casts_sense_through_the_spirit_readers_and_reports_it(owned, tmp_path):
    import json
    sim = spirit_sim()

    async def spirits(n, obj):
        return await sim.spirits(obj)

    async def cursor_bytes():
        return await sim.spirit_cursor_bytes()

    async def command_menu():
        return await sim.command_menu()

    service, adapter, frame = make(owned, tmp_path, sim, read_spirits=spirits,
                                   read_spirit_cursor_bytes=cursor_bytes,
                                   read_command_menu=command_menu)
    answer = asyncio.run(service.execute('plan_act', frame(
        sequence=1, policy='use sense then focus before attacking', **request())))
    assert answer['ok'] is True and answer['spirit']['status'] == 'cast'
    assert answer['spirit']['spirit'] == 'Sense' and sim.sp == 35
    assert adapter.sent[:5] == ['circle', 'down', 'down', 'circle', 'down']
    report = json.loads((tmp_path / 'evidence' / 'turn-report.json').read_text(encoding='utf-8'))
    assert report['entries'][0]['spirit']['sp'] == [55, 35]


def test_plan_act_without_spirit_readers_skips_the_spirit_and_attacks(owned, tmp_path):
    sim = spirit_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    answer = asyncio.run(service.execute('plan_act', frame(
        sequence=1, policy='use sense then focus before attacking', **request())))
    assert answer['spirit']['status'] == 'skipped'
    assert answer['spirit']['reason'].startswith('spirits_unreadable')
    assert answer['ok'] is True and sim.sp == 55


def test_a_bonus_action_permits_only_result_and_cancel_presses_until_the_next_plan(owned,
                                                                                   tmp_path):
    from test_act import ContinueAttack
    sim = ContinueAttack()
    for unit in sim.units:
        unit['object'] += BASE
        unit['max_hp'] = unit['hp']
    for weapon, power in zip(sim.weapons, (1000, 2000, 3000), strict=True):
        weapon['power'] = power
    service, adapter, frame = make(owned, tmp_path, sim)

    def press(sequence, context, purpose, button):
        return service.execute('press', frame(context, sequence=sequence, button=button,
                                              duration=2, purpose=purpose))

    async def scenario():
        with pytest.raises(NavigationRefused):                  # no bonus yet
            await press(1, 'result', 'dismiss_result', 'circle')
        answer = await service.execute('plan_act', frame(sequence=1, policy='', **request()))
        assert answer['ok'] and answer['outcome']['bonus_action'] is True
        sent = len(adapter.sent)
        await press(2, 'result', 'dismiss_result', 'circle')    # user, 24 Oct: look first
        await press(3, 'weapon_list', 'cancel', 'cross')
        assert adapter.sent[sent:] == ['circle', 'cross']
        with pytest.raises(NavigationRefused):                  # still no other battle press
            await press(4, 'unit_commands', 'open_move', 'circle')
    asyncio.run(scenario())


def test_a_pending_dialogue_makes_the_next_plan_act_settle_it_first(owned, tmp_path,
                                                                   monkeypatch):
    from psp_buddy import plan_act
    seen = []
    answers = [{'ok': True, 'phase': 'fired', 'outcome': {'dialogue_pending': True}},
               {'ok': True, 'phase': 'fired', 'outcome': {},
                'dialogue_settled': {'settled': True, 'presses': 3}},
               {'ok': True, 'phase': 'fired', 'outcome': {}}]

    async def fake(io, policy, unit_object, **kw):
        seen.append(kw['settle_first'])
        return answers[len(seen) - 1]

    monkeypatch.setattr(plan_act, 'plan_and_act', fake)
    service, adapter, frame = make(owned, tmp_path, plan_sim())

    async def scenario():
        for n in (1, 2, 3):
            await service.execute('plan_act', frame(sequence=n, policy='', **request()))
    asyncio.run(scenario())
    assert seen == [False, True, False]


def test_end_turn_open_settles_a_pending_dialogue_first(owned, tmp_path, monkeypatch):
    # Review (24 Oct): the turn's last unit can leave a story dialogue pending.
    from psp_buddy import act as act_macro
    from psp_buddy import end_turn
    calls = []

    async def settle(io, **kw):
        calls.append('settle')
        return {'settled': False, 'presses': 40}

    async def open_menu(io, state):
        calls.append('open')
        return {'ok': True, 'phase': 'menu_open'}

    monkeypatch.setattr(act_macro, 'settle_dialogue', settle)
    monkeypatch.setattr(end_turn, 'open_menu', open_menu)
    service, adapter, frame = make(owned, tmp_path, plan_sim())
    service._turn_done, service._dialogue_pending = True, True
    answer = asyncio.run(service.execute('end_turn', frame(sequence=1, phase='open')))
    assert answer['ok'] is False and answer['reason'] == 'dialogue_not_finished'
    assert calls == ['settle']


# ---- Stage 33: a state saved mid-move (start-of-run back-out) ------------------------------

def close_menu(frame, sequence):
    return frame('unit_commands', sequence=sequence, purpose='close_command_menu', button='cross',
                 duration=2)


def test_the_command_menu_may_be_closed_before_the_first_action(owned, tmp_path):
    service, adapter, frame = make(owned, tmp_path, plan_sim())

    async def scenario():
        await service.execute('press', frame('move_range', sequence=1, purpose='cancel',
                                              button='cross', duration=2))
        await service.execute('press', close_menu(frame, 2))
    asyncio.run(scenario())
    assert adapter.sent == ['cross', 'cross']


def test_closing_the_command_menu_is_refused_once_the_trial_has_played(owned, tmp_path):
    service, adapter, frame = make(owned, tmp_path, plan_sim())

    async def scenario():
        fired = await service.execute('plan_act', frame(sequence=1, policy='', **request()))
        assert fired['phase'] == 'fired'
        sent = len(adapter.sent)
        with pytest.raises(NavigationRefused, match='first action'):
            await service.execute('press', close_menu(frame, 2))
        assert len(adapter.sent) == sent
    asyncio.run(scenario())


def test_close_command_menu_is_cross_on_the_command_menu_only(owned, tmp_path):
    service, adapter, frame = make(owned, tmp_path, plan_sim())

    async def scenario():
        for bad in (dict(button='circle'), dict(context='map'), dict(context='result')):
            args = {**close_menu(frame, 1), **bad}
            with pytest.raises(NavigationRefused):
                await service.execute('press', args)
    asyncio.run(scenario())
    assert adapter.sent == []


# ---- M15: the per-turn cursor budget hands over on the map ------------------------------------

def test_turn_next_hands_over_cursor_budget_when_reaching_the_unit_would_not_fit(owned, tmp_path):
    import json

    from psp_buddy import info_navigation, press_budget
    sim, _ = named_sim({})
    service, adapter, frame = make(owned, tmp_path, sim)
    unit = next(u for u in sim.units if u['object'] == BASE + 1000)
    cost = press_budget.reach_unit(tuple(sim.cursor), (unit['tile_x'], unit['tile_y']))
    service._goto_presses = info_navigation.MAX_GOTO_PRESSES - cost + 1

    async def scenario():
        answer = await service.execute('turn_next', {'sequence': 1})
        assert answer['handover'] == {'reason': 'cursor_budget'}
        assert answer['unit_object'] is None and answer['done'] is False
        data = json.loads((tmp_path / 'evidence' / 'handover.json').read_text(encoding='utf-8'))
        assert data['reason'] == 'cursor_budget' and data['screen_state'] == 'map'
        assert any(a['unmoved'] for a in data['allies'])
    asyncio.run(scenario())
    assert adapter.sent == []


def test_turn_next_plays_on_when_reaching_the_unit_fits_exactly(owned, tmp_path):
    from psp_buddy import info_navigation, press_budget
    sim, _ = named_sim({})
    service, adapter, frame = make(owned, tmp_path, sim)
    unit = next(u for u in sim.units if u['object'] == BASE + 1000)
    cost = press_budget.reach_unit(tuple(sim.cursor), (unit['tile_x'], unit['tile_y']))
    service._goto_presses = info_navigation.MAX_GOTO_PRESSES - cost

    answer = asyncio.run(service.execute('turn_next', {'sequence': 1}))
    assert answer['handover'] is None and answer['unit_object'] == BASE + 1000


def test_the_cursor_budget_refusal_names_the_turn():
    import inspect

    from psp_buddy import info_navigation
    source = inspect.getsource(info_navigation.InfoNavigation._goto)
    assert 'for this turn' in source and 'for this trial' not in source


def _cost_of_planned_act(sim, unit_object):
    from psp_buddy import press_budget
    unit = next(u for u in sim.units if u['object'] == unit_object)
    foe = min((u for u in sim.units if u['raw_menu_group_byte'] == 12),
              key=lambda u: abs(u['tile_x'] - unit['tile_x']) + abs(u['tile_y'] - unit['tile_y']))
    return press_budget.act_cost((unit['tile_x'], unit['tile_y']), destination=None,
                                 target=(foe['tile_x'], foe['tile_y']))


def test_plan_act_hands_over_cursor_budget_before_a_walk_it_cannot_finish(owned, tmp_path):
    from psp_buddy import info_navigation
    sim = plan_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    service._goto_presses = info_navigation.MAX_GOTO_PRESSES - 1

    async def scenario():
        answer = await service.execute('plan_act', frame(sequence=1, policy='', **request()))
        assert answer['phase'] == 'handover' and answer['reason'] == 'cursor_budget'
        assert answer['moved'] is False
        nxt = await service.execute('turn_next', {'sequence': 2})
        assert nxt['handover'] == {'reason': 'cursor_budget'} and nxt['unit_object'] is None
    asyncio.run(scenario())
    assert adapter.sent == []


def test_plan_act_fires_when_the_planned_walks_fit(owned, tmp_path):
    from psp_buddy import info_navigation
    sim = plan_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    service._goto_presses = (info_navigation.MAX_GOTO_PRESSES
                             - _cost_of_planned_act(sim, BASE + 1000) - 20)
    answer = asyncio.run(service.execute('plan_act', frame(sequence=1, policy='', **request())))
    assert answer['phase'] == 'fired'


def test_enemy_reaction_recon_presses_directions_only_at_a_stopped_window(owned, tmp_path):
    # M16 recon (user, 3 Nov: evade above 30% hit): find the defender options on the forecast.
    from test_end_turn import WindowSim
    sim = WindowSim(screens=3)
    for u in sim.units:
        u['object'] += BASE
        u['counted_as_unmoved'] = False
    service, adapter, frame = make(owned, tmp_path, sim)

    def reaction(sequence, button='right'):
        return service.execute('press', frame('enemy_forecast', sequence=sequence, button=button,
                                              duration=2, purpose='reaction_move'))

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        await service.execute('end_turn', frame(sequence=2, phase='open'))
        await service.execute('end_turn', frame('system_menu', sequence=3, phase='confirm',
                                                highlighted_entry='EndTurn'))
        with pytest.raises(NavigationRefused):        # not stopped at a window yet
            await reaction(4)
        stop = await service.execute('enemy_phase', {'sequence': 4, 'stop_at_window': True})
        assert stop['phase'] == 'window'
        await reaction(5)
        await reaction(6, 'down')
        with pytest.raises(NavigationRefused):        # Circle stays with enemy_phase
            await reaction(7, 'circle')
        step = await service.execute('enemy_phase', {'sequence': 7})
        assert step['phase'] in ('continue', 'done')
        with pytest.raises(NavigationRefused):        # the window has moved on
            await reaction(8)
    asyncio.run(scenario())
    assert sim.log.count('right') == 1 and sim.log.count('down') == 1


def test_enemy_phase_evades_above_the_given_hit_with_the_cursor_reader(owned, tmp_path):
    # M16 (user, 3 Nov): "in enemy phase, if the foe hit rate more than 30%, choose eva".
    import json

    from test_end_turn import ReactionSim
    sim = ReactionSim(hits=(35, 20, 100))
    for u in sim.units:
        u['object'] += BASE
        u['counted_as_unmoved'] = False
    service, adapter, frame = make(owned, tmp_path, sim, read_reaction_cursors=sim.reaction_cursors)

    async def scenario():
        await service.execute('turn_next', {'sequence': 1})
        await service.execute('end_turn', frame(sequence=2, phase='open'))
        await service.execute('end_turn', frame('system_menu', sequence=3, phase='confirm',
                                                highlighted_entry='EndTurn'))
        for bad in (-1, 101, '30', True):
            for key in ('evade_above', 'defend_at'):      # defend_at: M16, m16-i
                with pytest.raises(NavigationRefused):
                    await service.execute('enemy_phase', {'sequence': 4, key: bad})
        sequence, step = 4, {'phase': 'continue'}
        while step['phase'] == 'continue':
            step = await service.execute('enemy_phase', {'sequence': sequence, 'evade_above': 30,
                                                         'defend_at': 100})
            sequence += 1
        assert step['phase'] == 'done'
    asyncio.run(scenario())
    assert sim.chosen == [0] and sim.defended == [2]
    report = tmp_path / 'evidence' / 'enemy-phase-report.json'
    data = json.loads(report.read_text(encoding='utf-8'))
    assert [r['action'] for r in data['reactions']] == ['evade', 'default', 'defend']


def test_the_act_io_reads_the_menu_masks_through_the_helper_reader(owned, tmp_path):
    from psp_buddy import act as act_macro
    sim = phase_sim()

    async def masks():
        return 0x0880000C, 0x06000000

    service, adapter, frame = make(owned, tmp_path, sim, read_menu_masks=masks)
    assert asyncio.run(service._act_io().menu_masks()) == (0x0880000C, 0x06000000)
    bare, _, _ = make(owned, tmp_path / 'b', sim)
    with pytest.raises(act_macro.ActIOError):
        asyncio.run(bare._act_io().menu_masks())


def test_run_boss_names_replace_the_defaults_and_the_max_hp_rule(owned, tmp_path):
    # s4-c (4 Nov): a checkpoint names its stage's bosses; nothing else counts as one.
    sim = plan_sim()
    service, adapter, frame = make(owned, tmp_path, sim)
    service._boss_names = ('D-Beast Rook ADAMON P',)
    state = {'turn': {'turn': 1}, 'units': [
        {'object': 1, 'raw_menu_group_byte': 0, 'hp': 5000, 'max_hp': 5000},
        {'object': 2, 'raw_menu_group_byte': 12, 'hp': 18500, 'max_hp': 18500},
        {'object': 3, 'raw_menu_group_byte': 12, 'hp': 5000, 'max_hp': 5000},
        {'object': 4, 'raw_menu_group_byte': 12, 'hp': 5000, 'max_hp': 5000},
        {'object': 5, 'raw_menu_group_byte': 12, 'hp': 36000, 'max_hp': 36000}]}
    service._mech_names.update({2: 'Android DB ADAMON', 3: 'x', 4: 'y',
                                5: 'D-Beast Rook  Adamon P'})
    run = service._begin_clear(state)
    assert run.bosses == frozenset({5})


# 7 Nov (debugger-freeze spec): a hung read must not be logged as "ok" (s2d logged 60 s "ok").
# A reader timeout becomes DebuggerFrozen (no recover() on the fake adapter): 7 Nov fallback.
@pytest.mark.parametrize('error, outcome, raised', [
    (TimeoutError(), 'error: DebuggerFrozen', 'DebuggerFrozen'),
    (OSError('gone'), 'error: OSError', 'OSError')])
def test_a_failed_act_read_logs_its_outcome(owned, tmp_path, error, outcome, raised):
    import json
    sim = phase_sim()

    async def masks():
        raise error

    service, _, _ = make(owned, tmp_path, sim, read_menu_masks=masks)
    with pytest.raises(Exception) as caught:
        asyncio.run(service._act_io().menu_masks())
    assert type(caught.value).__name__ == raised
    lines = (tmp_path / 'evidence' / 'agent-navigation-inputs.jsonl').read_text().splitlines()
    act_reads = [json.loads(x) for x in lines if '"act_read"' in x]
    assert act_reads[-1]['outcome'] == outcome


# 7 Nov (debugger-freeze spec, Part 4): s4-d handed over `cursor_budget` with a story dialogue up.
@pytest.mark.parametrize('settled', [True, False])
def test_a_cursor_budget_handover_settles_a_pending_dialogue_first(owned, tmp_path, monkeypatch,
                                                                   settled):
    import json

    from psp_buddy import act as act_macro
    from psp_buddy import info_navigation
    calls = []

    async def settle(io, **kw):
        calls.append('settle')
        return {'settled': settled, 'presses': 3}

    monkeypatch.setattr(act_macro, 'settle_dialogue', settle)
    sim, _ = named_sim({})
    service, adapter, frame = make(owned, tmp_path, sim)
    service._goto_presses = info_navigation.MAX_GOTO_PRESSES
    service._dialogue_pending = True
    answer = asyncio.run(service.execute('turn_next', {'sequence': 1}))
    assert answer['handover'] == {'reason': 'cursor_budget'} and calls == ['settle']
    data = json.loads((tmp_path / 'evidence' / 'handover.json').read_text(encoding='utf-8'))
    assert data['reason'] == 'cursor_budget'
    assert data['screen_state'] == ('map' if settled else 'dialogue')
    assert data.get('dialogue_pending', False) is (not settled)
    assert service._dialogue_pending is (not settled)


def test_a_cursor_budget_handover_without_a_dialogue_does_not_settle(owned, tmp_path, monkeypatch):
    from psp_buddy import act as act_macro
    from psp_buddy import info_navigation

    async def settle(io, **kw):
        raise AssertionError('no dialogue is pending')

    monkeypatch.setattr(act_macro, 'settle_dialogue', settle)
    sim, _ = named_sim({})
    service, adapter, frame = make(owned, tmp_path, sim)
    service._goto_presses = info_navigation.MAX_GOTO_PRESSES
    answer = asyncio.run(service.execute('turn_next', {'sequence': 1}))
    assert answer['handover'] == {'reason': 'cursor_budget'}


# ---- 7 Nov: debugger-freeze fallback (wait-and-retry, then a clean handover) ----------------

def _hangs_once(result):
    calls = []

    async def reader(*a):
        calls.append(a)
        if len(calls) == 1:
            await asyncio.sleep(30)
        return result
    return reader, calls


def test_a_frozen_read_is_retried_once_after_the_adapter_recovers(owned, tmp_path, monkeypatch):
    from psp_buddy import info_navigation
    monkeypatch.setattr(info_navigation, 'READ_FREEZE_SECONDS', 0.05)
    masks, calls = _hangs_once((1, 2))
    service, adapter, _ = make(owned, tmp_path, phase_sim(), read_menu_masks=masks)
    recovered = []

    async def recover():
        recovered.append(True)
        return True
    adapter.recover = recover
    assert asyncio.run(service._act_io().menu_masks()) == (1, 2)
    assert len(calls) == 2 and recovered == [True]


def test_a_frozen_read_without_recovery_raises_debugger_frozen(owned, tmp_path, monkeypatch):
    from psp_buddy import info_navigation
    monkeypatch.setattr(info_navigation, 'READ_FREEZE_SECONDS', 0.05)
    masks, calls = _hangs_once((1, 2))
    service, adapter, _ = make(owned, tmp_path, phase_sim(), read_menu_masks=masks)

    async def recover():
        return False
    adapter.recover = recover
    with pytest.raises(info_navigation.DebuggerFrozen):
        asyncio.run(service._act_io().menu_masks())
    assert len(calls) == 1


def test_a_press_that_times_out_is_a_debugger_freeze_and_is_never_repeated(owned, tmp_path):
    from psp_buddy import info_navigation
    service, adapter, _ = make(owned, tmp_path, phase_sim())
    pressed = []

    async def press(button, frames=2):
        pressed.append(button)
        raise TimeoutError()
    adapter.press = press
    with pytest.raises(info_navigation.DebuggerFrozen):
        asyncio.run(service._act_io().press('down'))
    assert pressed == ['down']


def test_a_frozen_turn_next_hands_over_and_reads_nothing_after(owned, tmp_path, monkeypatch):
    import json

    from psp_buddy import info_navigation
    monkeypatch.setattr(info_navigation, 'READ_FREEZE_SECONDS', 0.05)
    sim, _ = named_sim({})
    service, adapter, frame = make(owned, tmp_path, sim)
    calls = []

    async def frozen(n):
        calls.append(n)
        await asyncio.sleep(30)
    service._read_state = service._guard_reader(frozen)

    async def scenario():
        first = await service.execute('turn_next', {'sequence': 1})
        assert first['handover'] == {'reason': 'debugger_frozen'}
        assert first['unit_object'] is None and first['done'] is False
        data = json.loads((tmp_path / 'evidence' / 'handover.json').read_text(encoding='utf-8'))
        assert data['reason'] == 'debugger_frozen' and data['screen_state'] == 'unknown'
        again = await service.execute('turn_next', {'sequence': 2})
        assert again['handover'] == {'reason': 'debugger_frozen'}
    asyncio.run(scenario())
    assert len(calls) == 1 and adapter.sent == []


@pytest.mark.parametrize('uncertain', [True, False])
def test_only_a_debugger_timeout_becomes_a_frozen_handover(owned, tmp_path, uncertain):
    # 7 Nov review: a TimeoutError from elsewhere must not be labelled debugger_frozen.
    sim, _ = named_sim({})
    service, adapter, frame = make(owned, tmp_path, sim)
    adapter.uncertain = uncertain

    async def times_out(n):
        raise TimeoutError()
    service._read_state = times_out           # unguarded on purpose
    if uncertain:
        answer = asyncio.run(service.execute('turn_next', {'sequence': 1}))
        assert answer['handover'] == {'reason': 'debugger_frozen'}
    else:
        with pytest.raises(TimeoutError):
            asyncio.run(service.execute('turn_next', {'sequence': 1}))
