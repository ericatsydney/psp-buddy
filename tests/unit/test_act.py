import asyncio
import copy

import pytest

from psp_buddy import act

ALLOWED = {'up', 'down', 'left', 'right', 'circle', 'cross', 'start'}


class SimGame:
    """A tiny model of the unit-command UI, exposing the memory reads `act` is allowed to use."""

    def __init__(self, *, moved_entries=('Attack', 'Standby'), **flags):
        self.units = [
            {'object': 1000, 'tile_x': 5, 'tile_y': 5, 'hp': 5000, 'en': 100,
             'raw_menu_group_byte': 0, 'counter_value': 1, 'counted_as_unmoved': True},
            {'object': 1001, 'tile_x': 2, 'tile_y': 2, 'hp': 3000, 'en': 50,
             'raw_menu_group_byte': 0, 'counter_value': 1, 'counted_as_unmoved': True},
            {'object': 2000, 'tile_x': 5, 'tile_y': 9, 'hp': 8000, 'en': 80,
             'raw_menu_group_byte': 12, 'counter_value': 1, 'counted_as_unmoved': True},
            {'object': 2001, 'tile_x': 12, 'tile_y': 12, 'hp': 8000, 'en': 80,
             'raw_menu_group_byte': 12, 'counter_value': 1, 'counted_as_unmoved': True},
        ]
        self.weapons = [
            {'slot': 0, 'name': 'Vulcan', 'min_range': 1, 'max_range': 2, 'max_ammo': 10,
             'ammo': 10, 'en_cost': 0, 'flags': {'p': True}},
            {'slot': 1, 'name': 'Grenade', 'min_range': 1, 'max_range': 5, 'max_ammo': 6,
             'ammo': 6, 'en_cost': 0, 'flags': {'p': False}},
            {'slot': 3, 'name': 'BeamRifle', 'min_range': 2, 'max_range': 4, 'max_ammo': 10,
             'ammo': 9, 'en_cost': 0, 'flags': {'p': True}},
        ]
        self.screen = 'map'
        self.cursor = [5, 5]
        self.entry = 0
        self.entries: list[str] = []
        self.moved_entries = list(moved_entries)
        self.row = 0
        self.acting: dict | None = None
        self.weapon: dict | None = None
        self.log: list[str] = []
        self.combat_reads = 0
        self.flags = flags

    def unit_at(self, x, y):
        return next((u for u in self.units if (u['tile_x'], u['tile_y']) == (x, y)), None)

    async def press(self, button, frames=2):
        self.log.append(button)
        assert button in ALLOWED
        s = self.screen
        step = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}.get(button)
        if s in ('map', 'move_range', 'target_select') and step:
            self.cursor = [self.cursor[0] + step[0], self.cursor[1] + step[1]]
        elif s == 'unit_menu' and step:
            self.entry = max(0, min(len(self.entries) - 1, self.entry + step[1]))
        elif s == 'weapon_list' and step and not self.flags.get('row_stuck'):
            self.row = max(0, min(len(self.weapons) - 1, self.row + step[1]))
        elif s == 'map' and button == 'circle':
            u = self.unit_at(*self.cursor)
            if u and u['raw_menu_group_byte'] == 0 and u['counted_as_unmoved']:
                self.acting = u
                moved = u.get('moved')
                self.entries = list(self.moved_entries) if moved else ['Move', 'Attack', 'Info']
                self.entry, self.screen = 0, 'unit_menu'
        elif s == 'unit_menu' and button == 'circle':
            choice = self.entries[self.entry]
            if choice == 'Move':
                self.screen = 'move_range'
            elif choice == 'Attack':
                self.screen, self.row = 'weapon_list', 0
        elif s == 'unit_menu' and button == 'cross':
            self.screen = 'map'
        elif s == 'move_range' and button == 'circle':
            assert self.acting is not None
            dist = (abs(self.cursor[0] - self.acting['tile_x'])
                    + abs(self.cursor[1] - self.acting['tile_y']))
            if 0 < dist <= 3 and not self.unit_at(*self.cursor):
                self.acting.update(tile_x=self.cursor[0], tile_y=self.cursor[1], moved=True)
                self.acting['en'] -= dist
                self.entries, self.entry, self.screen = list(self.moved_entries), 0, 'unit_menu'
        elif s == 'move_range' and button == 'cross':
            self.screen = 'unit_menu'
        elif s == 'weapon_list' and button == 'circle':
            self.weapon = self.weapons[self.row]
            foe = next(u for u in self.units if u['raw_menu_group_byte'] == 12)
            self.cursor, self.screen = [foe['tile_x'], foe['tile_y']], 'target_select'
        elif s == 'weapon_list' and button == 'cross':
            self.screen = 'unit_menu'
        elif s == 'target_select' and button == 'circle':
            u = self.unit_at(*self.cursor)
            if u and u['raw_menu_group_byte'] == 12:
                self.screen = 'forecast'
        elif s in ('target_select', 'forecast') and button == 'cross':
            self.screen = 'weapon_list' if s == 'target_select' else 'target_select'
        elif s == 'forecast' and button == 'start' and not self.flags.get('start_ignored'):
            assert self.weapon is not None
            if self.weapon['ammo'] is not None:
                self.weapon['ammo'] -= 1
            self.acting['en'] -= self.weapon.get('en_cost', 0)
            self.screen, self.combat_reads = 'combat', 0
        elif s == 'result' and button == 'circle' and not self.flags.get('dismiss_never'):
            assert self.acting is not None
            self.acting.update(counter_value=0, counted_as_unmoved=False)
            self.screen = 'map'

    async def goto(self, tile):
        self.log.append(f'goto{tuple(tile)}')
        if self.flags.get('goto_fails'):
            return {'reached': False, 'cursor': {'x': self.cursor[0], 'y': self.cursor[1]}}
        self.cursor = list(tile)
        return {'reached': True, 'cursor': {'x': tile[0], 'y': tile[1]}}

    async def state(self):
        if self.screen == 'combat':
            self.combat_reads += 1
            if self.combat_reads >= 2:
                self.screen = 'result'
        reachable = []
        if self.screen == 'move_range' and self.acting and not self.flags.get('range_stale'):
            ax, ay = self.acting['tile_x'], self.acting['tile_y']
            reachable = [[ax + dx, ay + dy, abs(dx) + abs(dy)]
                         for dx in range(-3, 4) for dy in range(-3, 4)
                         if 0 < abs(dx) + abs(dy) <= 3]
        if self.screen == 'move_range' and self.flags.get('range_stale'):
            reachable = [[20, 20, 1], [21, 20, 2]]
        return {'turn': {'turn': 7}, 'cursor': {'x': self.cursor[0], 'y': self.cursor[1]},
                'units': copy.deepcopy(self.units), 'reachable': reachable}

    async def read_weapons(self, unit_object):
        return {'object': unit_object, 'weapons': copy.deepcopy(self.weapons)}

    async def hit(self):
        if self.screen in ('target_select', 'forecast'):
            u = self.unit_at(*self.cursor)
            if u and u['raw_menu_group_byte'] == 12:
                return {'state': 'hit', 'hit': 42}
            return {'state': 'no_target', 'hit': None}
        return {'state': 'unknown', 'hit': None}

    async def menu_row(self):
        if self.screen == 'weapon_list':
            return self.row, len(self.weapons)
        return 0, 0

    async def sleep(self, seconds):
        pass

    def time_left(self):
        left = self.flags.get('time_left', float('inf'))
        if left != float('inf'):
            self.flags['time_left'] = left - 1       # one second per press or read
        return left


def run(coro):
    return asyncio.run(coro)


def instruction(**kw):
    base = {'unit_object': 1000}
    base.update(kw)
    return base


MOVE_ATTACK = instruction(move_to=[5, 7], attack={'weapon': 'BeamRifle', 'target_object': 2000})


def test_move_and_attack_runs_every_stage_in_order():
    sim = SimGame()
    result = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert result['ok'] is True and result['phase'] == 'done'
    assert [s['stage'] for s in result['stages']] == [
        'plan', 'select', 'move', 'attack_menu', 'weapon', 'target', 'forecast', 'fire', 'result']
    assert sim.log == ['goto(5, 5)', 'circle', 'circle', 'goto(5, 7)', 'circle',
                       'circle', 'down', 'down', 'circle', 'goto(5, 9)', 'circle', 'start',
                       'circle']
    me = sim.units[0]
    assert (me['tile_x'], me['tile_y']) == (5, 7) and me['en'] == 98
    assert sim.weapons[2]['ammo'] == 8 and me['counted_as_unmoved'] is False
    assert result['deltas'][0]['object'] == 1000 and sim.screen == 'map'


def test_commit_false_stops_at_the_forecast_and_fire_finishes_it():
    sim = SimGame()
    first = run(act.run_act(MOVE_ATTACK, sim, commit=False))
    assert first['ok'] is True and first['phase'] == 'forecast'
    assert first['stages'][-1]['facts']['hit'] == 42
    assert 'start' not in sim.log and sim.screen == 'forecast'
    done = run(act.run_act(MOVE_ATTACK, sim, phase='fire'))
    assert done['ok'] is True and done['phase'] == 'done'
    assert sim.log.count('start') == 1 and sim.screen == 'map'


def test_attack_without_move_takes_the_second_menu_entry():
    sim = SimGame()
    request = instruction(attack={'weapon': 'Vulcan', 'target_object': 2000})
    # Vulcan 1~2: the foe is 4 tiles away, so use the unit next to it instead
    sim.units[2]['tile_y'] = 6
    result = run(act.run_act(request, sim, commit=True))
    assert result['ok'] is True
    assert sim.log[:4] == ['goto(5, 5)', 'circle', 'down', 'circle']
    assert 'goto(5, 6)' in sim.log


def test_move_only_leaves_the_post_move_menu_open():
    sim = SimGame()
    result = run(act.run_act(instruction(move_to=[6, 5]), sim, commit=True))
    assert result['ok'] is True and result['phase'] == 'moved'
    assert sim.screen == 'unit_menu' and 'start' not in sim.log
    assert (sim.units[0]['tile_x'], sim.units[0]['tile_y']) == (6, 5)


@pytest.mark.parametrize('request_, reason', [
    (instruction(unit_object=2000, move_to=[5, 8]), 'unit_not_ally'),
    (instruction(unit_object=77, move_to=[5, 8]), 'unit_not_found'),
    (instruction(), 'nothing_to_do'),
    (instruction(move_to=[5, 5]), 'move_to_current_tile'),
    (instruction(move_to=[2, 2]), 'move_tile_occupied'),
    (instruction(attack={'weapon': 'Laser', 'target_object': 2000}), 'unknown_weapon'),
    (instruction(attack={'weapon': 'Vulcan', 'target_object': 1001}), 'target_not_in_range'),
    (instruction(move_to=[6, 5], attack={'weapon': 'Grenade', 'target_object': 2000}),
     'weapon_unusable'),
    (instruction(move_to=[5, 6], attack={'weapon': 'Vulcan', 'target_object': 2001}),
     'target_not_in_range'),
])
def test_plan_refusals_press_nothing(request_, reason):
    sim = SimGame()
    sim.units[3]['tile_x'], sim.units[3]['tile_y'] = 12, 12
    result = run(act.run_act(request_, sim, commit=True))
    assert result['ok'] is False and result['stage'] == 'plan' and result['reason'] == reason
    assert sim.log == []


def test_a_unit_that_already_acted_is_refused():
    sim = SimGame()
    sim.units[0].update(counter_value=0, counted_as_unmoved=False)
    result = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert result['reason'] == 'unit_already_acted' and sim.log == []


def test_unreachable_destination_backs_out_of_move_range():
    sim = SimGame()
    result = run(act.run_act(instruction(move_to=[5, 12]), sim, commit=True))
    assert result['ok'] is False and result['stage'] == 'move'
    assert result['reason'] == 'destination_not_reachable'
    assert sim.log[-2:] == ['cross', 'cross'] and sim.screen == 'map'


def test_stale_range_not_centred_on_the_unit_backs_out():
    sim = SimGame(range_stale=True)
    result = run(act.run_act(instruction(move_to=[6, 5]), sim, commit=True))
    assert result['stage'] == 'move' and result['reason'] == 'range_not_centered_on_unit'
    assert sim.log[-2:] == ['cross', 'cross']


def test_cursor_walk_failure_backs_out_and_reports_the_stage():
    sim = SimGame(goto_fails=True)
    result = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert result['ok'] is False and result['stage'] == 'select'
    assert result['reason'] == 'cursor_did_not_reach_tile' and sim.log == ['goto(5, 5)']


def test_weapon_menu_row_mismatch_backs_out_before_choosing():
    sim = SimGame(row_stuck=True)
    result = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert result['stage'] == 'weapon' and result['reason'] == 'weapon_row_mismatch'
    assert sim.log[-1] == 'cross' and sim.screen == 'unit_menu'
    assert 'start' not in sim.log


def test_wrong_menu_count_means_the_weapon_list_is_not_open():
    sim = SimGame(moved_entries=('Standby', 'Attack'))      # Attack is not the default entry
    result = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert result['ok'] is False and result['stage'] == 'attack_menu'
    assert result['reason'] == 'weapon_list_not_open' and 'start' not in sim.log


def test_target_not_hittable_backs_out():
    sim = SimGame()
    sim.units[2]['tile_y'] = 9
    request = instruction(move_to=[5, 7], attack={'weapon': 'BeamRifle', 'target_object': 2000})

    async def scenario():
        real = sim.goto

        async def goto(tile):
            outcome = await real(tile)
            if tile == [5, 9]:
                sim.cursor = [6, 9]          # lands next to the foe: reads no_target
                outcome = {'reached': True, 'cursor': {'x': 6, 'y': 9}}
            return outcome
        sim.goto = goto
        return await act.run_act(request, sim, commit=True)
    result = run(scenario())
    assert result['stage'] == 'target' and result['reason'] == 'target_not_hittable'
    assert 'start' not in sim.log and sim.log[-2:] == ['cross', 'cross']


def test_start_that_changes_nothing_is_reported_without_more_input():
    sim = SimGame(start_ignored=True)
    result = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert result['ok'] is False and result['stage'] == 'fire'
    assert result['reason'] == 'start_not_confirmed' and sim.log.count('start') == 1
    assert sim.log[-1] == 'start'


def test_result_dialog_dismissal_is_bounded():
    sim = SimGame(dismiss_never=True)
    result = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert result['ok'] is False and result['stage'] == 'result'
    assert result['reason'] == 'result_not_dismissed'
    assert sim.log.count('circle') <= 6 + 6 and sim.log.count('start') == 1


def test_fire_phase_needs_a_forecast_screen():
    sim = SimGame()
    result = run(act.run_act(MOVE_ATTACK, sim, phase='fire'))
    assert result['ok'] is False and result['reason'] == 'not_at_forecast'
    assert 'start' not in sim.log


def test_only_known_buttons_and_start_only_after_forecast():
    sim = SimGame()
    run(act.run_act(MOVE_ATTACK, sim, commit=True))
    first_start = sim.log.index('start')
    assert sim.log[first_start - 1] == 'circle'
    assert set(sim.log) <= ALLOWED | {'goto(5, 5)', 'goto(5, 7)', 'goto(5, 9)'}


def test_menu_row_decoder_accepts_only_plausible_list_cursors():
    assert act.decode_menu_row(bytes([2, 0, 5])) == (2, 5)
    assert act.decode_menu_row(bytes([0, 0, 21])) == (0, 21)
    for bad in (bytes([5, 0, 5]), bytes([0, 0, 0]), bytes([0, 0, 22])):
        assert act.decode_menu_row(bad) is None
    with pytest.raises(ValueError):
        act.decode_menu_row(b'\x00\x00')


def test_unit_object_must_be_an_integer():
    with pytest.raises(ValueError):
        run(act.run_act({'unit_object': '1000', 'move_to': [6, 5]}, SimGame()))


def test_transient_read_failures_during_polls_are_retried():
    sim = SimGame()
    real = sim.state
    failures = [0]

    async def flaky():
        if sim.screen in ('combat', 'result') and failures[0] < 3:
            failures[0] += 1
            raise act.ActIOError('normal running status required')
        return await real()
    sim.state = flaky
    result = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert result['ok'] is True and failures[0] == 3


def test_persistent_read_failures_still_stop_the_macro():
    sim = SimGame()
    real = sim.state

    async def dead():
        if sim.screen in ('combat', 'result'):
            raise act.ActIOError('gone')
        return await real()
    sim.state = dead
    result = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert result['ok'] is False and result['reason'].startswith('io_error')


def test_commit_without_time_for_fire_stops_at_the_forecast_for_a_separate_call():
    sim = SimGame()

    def tight():
        return 49.0 if sim.screen == 'forecast' else float('inf')
    sim.time_left = tight
    result = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert result['ok'] is True and result['phase'] == 'forecast'
    assert result['fire_separately'] is True and 'start' not in sim.log


def test_the_deadline_stops_the_macro_before_an_input_it_could_not_finish():
    sim = SimGame(time_left=12.0)
    result = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert result['ok'] is False and result['reason'] == 'act_deadline'
    assert 'start' not in sim.log


def test_duplicate_weapon_names_need_a_slot_and_the_slot_picks_the_row():
    sim = SimGame()
    sim.weapons.append({'slot': 4, 'name': 'BeamRifle', 'min_range': 1, 'max_range': 8,
                        'max_ammo': 0, 'ammo': None, 'en_cost': 5, 'flags': {'p': True}})
    ambiguous = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert ambiguous['ok'] is False and ambiguous['reason'] == 'ambiguous_weapon'
    assert ambiguous['facts']['slots'] == [3, 4] and sim.log == []
    wanted = instruction(move_to=[5, 7], attack={'weapon': 'BeamRifle', 'slot': 4,
                                                 'target_object': 2000})
    result = run(act.run_act(wanted, sim, commit=True))
    assert result['ok'] is True and sim.weapon['slot'] == 4 and sim.log.count('down') == 3
    wrong = instruction(move_to=[5, 7], attack={'weapon': 'Vulcan', 'slot': 3,
                                                'target_object': 2000})
    assert run(act.run_act(wrong, SimGame(), commit=True))['reason'] == 'unknown_weapon'


def test_a_weapon_without_ammo_or_en_cost_is_fired_and_confirmed_by_the_result_dialog():
    sim = SimGame()
    sim.weapons[2].update(max_ammo=0, ammo=None, en_cost=0)
    request = instruction(attack={'weapon': 'BeamRifle', 'target_object': 2000})
    sim.units[2].update(tile_x=6, tile_y=8)         # four tiles from the unit at (5, 5)
    result = run(act.run_act(request, sim, commit=True))
    assert result['ok'] is True and result['phase'] == 'done'
    fire = next(s for s in result['stages'] if s['stage'] == 'fire')
    assert fire['facts']['confirmed_by'] == 'result_dialog' and sim.log.count('start') == 1
    assert sim.units[0]['counted_as_unmoved'] is False


def test_unexpected_data_errors_become_a_stage_report_not_an_exception():
    sim = SimGame()
    real = sim.read_weapons
    calls = []

    async def shrinking(unit_object):
        calls.append(1)
        answer = await real(unit_object)
        if len(calls) >= 2:
            answer['weapons'] = answer['weapons'][:1]      # the list changed after the plan
        return answer
    sim.read_weapons = shrinking
    result = run(act.run_act(MOVE_ATTACK, sim, commit=True))
    assert result['ok'] is False and result['stage'] == 'fire'
    assert result['reason'].startswith('unexpected_data:') and result['needs_screenshot'] is True


def test_weapon_list_that_opens_on_another_row_is_walked_from_that_row():
    sim = SimGame()
    real = sim.press

    async def press(button, frames=2):
        await real(button, frames)
        if sim.screen == 'weapon_list' and button == 'circle' and sim.row == 0:
            sim.row = 1                              # the list reopened on the last-used row
    sim.press = press
    result = run(act.run_act(MOVE_ATTACK, sim, commit=False))
    assert result['ok'] is True and sim.weapon['name'] == 'BeamRifle'
    assert sim.log.count('down') == 1 and sim.log.count('up') == 0
