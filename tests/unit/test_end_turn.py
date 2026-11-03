import asyncio
import copy

import pytest

from psp_buddy import end_turn
from psp_buddy.act import ActIOError

ALLY, FOE = 0, 12


def unit(obj, x, y, group=ALLY, hp=5000, en=100, ready=False):
    return {'object': obj, 'tile_x': x, 'tile_y': y, 'raw_menu_group_byte': group, 'hp': hp,
            'en': en, 'counted_as_unmoved': ready}


def state(units, turn=7, cursor=(5, 5)):
    return {'turn': {'turn': turn}, 'cursor': {'x': cursor[0], 'y': cursor[1]},
            'map': {'width': 24, 'height': 34}, 'units': copy.deepcopy(units)}


class EnemyPhaseSim:
    """map -> system menu -> "End phase?" -> N enemy screens (one Circle each) -> turn T+1."""

    def __init__(self, screens=3, **flags):
        self.units = [unit(1, 5, 5, ready=True), unit(2, 6, 5), unit(3, 9, 9, FOE, ready=False)]
        self.turn, self.cursor, self.screen = 7, [5, 5], 'map'
        self.player_turn = 7                         # M13: the turn the player (agent) is in
        self.screens, self.flags, self.log = screens, flags, []
        self.reads = 0

    async def read_weapons(self, obj):              # M13: turn_next reads foe mech names
        return {'object': obj, 'mech_name': '', 'weapons': []}

    async def press(self, button, frames=2):
        self.log.append(button)
        step = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}.get(button)
        if step:                                     # the helper's own cursor walk
            assert self.screen == 'map' and self.turn == self.player_turn, (
                'direction pressed off the map')
            self.cursor = [self.cursor[0] + step[0], self.cursor[1] + step[1]]
            return
        assert button in ('circle', 'cross'), button
        if self.screen == 'map' and button == 'circle' and self.turn > self.player_turn:
            raise AssertionError('Circle pressed on the new player phase map')
        if self.screen == 'map' and button == 'circle':
            occupied = any((u['tile_x'], u['tile_y']) == tuple(self.cursor) for u in self.units)
            self.screen = 'unit_menu' if occupied else 'system_menu'
        elif self.screen == 'system_menu' and button == 'circle':
            self.screen = 'confirm'
        elif self.screen == 'system_menu' and button == 'cross':
            self.screen = 'map'
        elif self.screen == 'confirm' and button == 'circle':
            self.screen = 'enemy'
        elif self.screen == 'enemy' and button == 'circle':
            if self.flags.get('endless'):
                return
            self.screens -= 1
            if self.screens == 1 and self.flags.get('hit_ally'):
                self.units[1]['hp'] -= 1200
            if self.screens == 1 and self.flags.get('destroy_ally'):
                self.units[1]['hp'] = 0
            if self.screens == self.flags.get('lose_when', 1) and self.flags.get('lose_ally'):
                del self.units[1]
            if self.screens == 1 and self.flags.get('kill_foe'):
                self.units[-1]['hp'] = 0
            if self.screens == 1 and self.flags.get('restart'):
                self.turn = 1                   # lose condition met: the stage starts again
            if self.screens <= 0:
                self.turn += 2 if self.flags.get('jump') else 1
                self.screen = 'map'
                self.pending_reset = 0 if self.flags.get('no_reset') else 1

    async def goto(self, tile):
        self.log.append(f'goto{tuple(tile)}')
        if self.flags.get('goto_fails'):
            return {'reached': False, 'cursor': {'x': self.cursor[0], 'y': self.cursor[1]}}
        self.cursor = list(tile)
        return {'reached': True, 'cursor': {'x': tile[0], 'y': tile[1]}}

    async def state(self):
        self.reads += 1
        if self.flags.get('unreadable') and self.screen == 'enemy':
            raise ActIOError('read failed')
        if self.screen == 'enemy' and self.screens in self.flags.get('scene_at', ()):
            # Story scene (23 Oct live: "OZ Soldier" dialogue): the map state is not readable.
            raise ActIOError('battle state not readable now: cursor tile outside the map')
        if self.turn > self.player_turn:
            self.new_reads = getattr(self, 'new_reads', 0) + 1
            if self.flags.get('pan_reads', 0) >= self.new_reads:
                # The camera pans to the new phase: the cursor reads outside the map briefly.
                raise ActIOError('battle state not readable now: cursor tile outside the map')
            if self.flags.get('turn_start_scene') and self.new_reads >= 2:
                raise ActIOError('battle state not readable now: cursor tile outside the map')
        if getattr(self, 'pending_reset', 0) > 0:
            self.pending_reset -= 1
        elif self.turn > self.player_turn and not self.flags.get('no_reset'):
            for u in self.units:
                if u['raw_menu_group_byte'] == ALLY:
                    u['counted_as_unmoved'] = True
                    u['en'] = min(u['en'] + 5, 150)
        return state(self.units, self.turn, tuple(self.cursor))

    async def sleep(self, seconds):
        pass

    def time_left(self):
        return self.flags.get('time_left', float('inf'))


def run(coro):
    return asyncio.run(coro)


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        self.now += 1.0
        return self.now


def ended(sim):
    """Open the menu, confirm End Turn and return a fresh phase record."""
    opened = run(end_turn.open_menu(sim, run(sim.state())))
    assert opened['ok'] is True and sim.screen == 'system_menu'
    phase = end_turn.Phase(run(sim.state()), clock=Clock())
    confirmed = run(end_turn.confirm(sim, phase))
    assert confirmed['ok'] is True and sim.screen == 'enemy'
    return phase


# ---- pure parts --------------------------------------------------------------------------

def test_empty_tile_is_the_nearest_free_tile_to_the_cursor():
    st = state([unit(1, 5, 5), unit(2, 6, 5), unit(3, 5, 4, FOE)])
    assert end_turn.empty_tile(st) == [4, 5]            # (5,4) and (6,5) are taken
    dead = state([unit(1, 5, 5, hp=0)])
    assert end_turn.empty_tile(dead) == [5, 5]          # a destroyed unit leaves its tile free
    corner = state([unit(1, 0, 0)], cursor=(0, 0))
    assert end_turn.empty_tile(corner) in ([1, 0], [0, 1])


def test_checks_stop_only_on_ally_loss_or_a_turn_jump():
    start = state([unit(1, 5, 5), unit(2, 6, 5), unit(3, 9, 9, FOE)])
    assert end_turn.check(start, state([unit(1, 5, 5), unit(2, 6, 5, hp=10),
                                        unit(3, 9, 9, FOE, hp=0)])) is None
    assert end_turn.check(start, state([unit(1, 5, 5), unit(2, 6, 5, hp=0),
                                        unit(3, 9, 9, FOE)])) == 'ally_destroyed'
    assert end_turn.check(start, state([unit(1, 5, 5), unit(3, 9, 9, FOE)])) == 'unit_lost'
    assert end_turn.check(start, state(start['units'], turn=9)) == 'turn_jump'
    assert end_turn.check(start, state(start['units'], turn=6)) == 'stage_restart'
    assert end_turn.check(start, {'units': []}) == 'unknown_state'


def test_finished_needs_the_next_turn_and_every_living_ally_unmoved():
    start = state([unit(1, 5, 5), unit(3, 9, 9, FOE)])
    assert not end_turn.finished(start, state([unit(1, 5, 5, ready=True)], turn=7))
    assert not end_turn.finished(start, state([unit(1, 5, 5, ready=False)], turn=8))
    assert end_turn.finished(start, state([unit(1, 5, 5, ready=True), unit(9, 1, 1, hp=0)],
                                          turn=8))


def test_deltas_report_hp_and_en_changes_per_unit():
    start = state([unit(1, 5, 5), unit(3, 9, 9, FOE, hp=8000)])
    now = state([unit(1, 5, 5, hp=3800, en=105), unit(3, 9, 9, FOE, hp=0)])
    assert end_turn.deltas(start, now) == [
        {'object': 1, 'group': ALLY, 'hp': [5000, 3800], 'en': [100, 105]},
        {'object': 3, 'group': FOE, 'hp': [8000, 0]}]


# ---- macro ---------------------------------------------------------------------------------

def test_open_menu_walks_to_an_empty_tile_and_presses_circle_once():
    sim = EnemyPhaseSim()
    opened = run(end_turn.open_menu(sim, run(sim.state())))
    assert opened == {'ok': True, 'phase': 'menu_open', 'tile': [5, 4], 'turn': 7}
    assert sim.log == ['goto(5, 4)', 'circle'] and sim.screen == 'system_menu'


def test_open_menu_stops_without_circle_when_the_cursor_cannot_reach_the_tile():
    sim = EnemyPhaseSim(goto_fails=True)
    opened = run(end_turn.open_menu(sim, run(sim.state())))
    assert opened['ok'] is False and opened['reason'] == 'cursor_did_not_reach_tile'
    assert 'circle' not in sim.log and sim.screen == 'map'


def test_a_whole_enemy_phase_with_circle_only_reaches_the_next_turn():
    sim = EnemyPhaseSim(screens=4, hit_ally=True)
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase))
    assert result['ok'] is True and result['phase'] == 'done'
    assert result['turn'] == [7, 8] and result['presses'] == 4
    assert set(sim.log[2:]) == {'circle'} and sim.screen == 'map'
    hit = next(d for d in result['deltas'] if d['object'] == 2)
    assert hit['hp'] == [5000, 3800]
    report = end_turn.report(phase)
    assert report['done'] is True and report['stopped'] is None
    assert report['turn'] == [7, 8] and report['damaged_allies'] == [2]
    assert report['destroyed'] == []


def test_a_destroyed_foe_is_reported_not_a_stop():
    sim = EnemyPhaseSim(screens=3, kill_foe=True)
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase))
    assert result['phase'] == 'done' and end_turn.report(phase)['destroyed'] == [3]


@pytest.mark.parametrize('flag,reason', [('destroy_ally', 'ally_destroyed'),
                                         ('lose_ally', 'unit_lost'), ('jump', 'turn_jump')])
def test_suspicious_memory_stops_the_phase(flag, reason):
    sim = EnemyPhaseSim(screens=3, **{flag: True})
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase))
    assert result['ok'] is False and result['phase'] == 'stopped' and result['reason'] == reason
    assert phase.stopped == reason
    again = run(end_turn.advance(sim, phase))            # a stopped phase sends nothing more
    assert again['reason'] == reason and again['presses'] == result['presses']


def test_a_call_ends_at_its_press_cap_and_the_next_call_continues(monkeypatch):
    monkeypatch.setattr(end_turn, 'CALL_PRESSES', 2)
    sim = EnemyPhaseSim(screens=5)
    phase = ended(sim)
    first = run(end_turn.advance(sim, phase))
    assert first['ok'] is True and first['phase'] == 'continue' and first['presses'] == 2
    while (step := run(end_turn.advance(sim, phase)))['phase'] == 'continue':
        pass
    assert step['phase'] == 'done' and step['presses'] == 5


def test_a_call_with_too_little_time_left_presses_nothing():
    sim = EnemyPhaseSim(screens=3)
    phase = ended(sim)
    sim.flags['time_left'] = 1.0
    result = run(end_turn.advance(sim, phase))
    assert result['phase'] == 'continue' and result['presses'] == 0


def test_the_whole_phase_budget_stops_an_endless_phase(monkeypatch):
    monkeypatch.setattr(end_turn, 'PHASE_PRESSES', 6)
    sim = EnemyPhaseSim(endless=True)
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase))
    assert result['phase'] == 'stopped' and result['reason'] == 'phase_budget'
    assert result['presses'] == 6


def test_the_new_turn_is_never_pressed_on_and_unclear_counters_stop():
    sim = EnemyPhaseSim(screens=2, no_reset=True)
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase))       # the sim raises if Circle hits turn 8
    assert result['phase'] == 'stopped' and result['reason'] == 'player_phase_unclear'
    assert result['presses'] == 2


def test_confirm_presses_circle_twice_and_a_phase_needs_a_readable_start():
    sim = EnemyPhaseSim()
    phase = end_turn.Phase(run(sim.state()), clock=Clock())
    run(end_turn.confirm(sim, phase))
    assert sim.log == ['circle', 'circle'] and phase.confirmed is True
    with pytest.raises(ValueError):
        end_turn.Phase({'units': []}, clock=Clock())


# ---- accepted losses (user decision 23 Oct: option 1) -------------------------------------

@pytest.mark.parametrize('flag', ['destroy_ally', 'lose_ally'])
def test_accepted_losses_are_reported_and_the_phase_goes_on(flag):
    sim = EnemyPhaseSim(screens=3, **{flag: True})
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase, accept_losses=True))
    assert result['ok'] is True and result['phase'] == 'done' and result['turn'] == [7, 8]
    assert phase.losses == {2: 'ally_destroyed' if flag == 'destroy_ally' else 'unit_lost'}
    assert end_turn.report(phase)['losses'] == {'2': phase.losses[2]}


def test_a_phase_stopped_by_a_loss_resumes_only_when_the_loss_is_accepted():
    sim = EnemyPhaseSim(screens=3, destroy_ally=True)
    phase = ended(sim)
    assert run(end_turn.advance(sim, phase))['reason'] == 'ally_destroyed'
    assert run(end_turn.advance(sim, phase))['reason'] == 'ally_destroyed'   # still stopped
    resumed = run(end_turn.advance(sim, phase, accept_losses=True))
    assert resumed['phase'] == 'done' and phase.losses == {2: 'ally_destroyed'}


def test_accepting_losses_never_excuses_a_turn_jump():
    sim = EnemyPhaseSim(screens=3, jump=True, destroy_ally=True)
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase, accept_losses=True))
    assert result['phase'] == 'stopped' and result['reason'] == 'turn_jump'
    again = run(end_turn.advance(sim, phase, accept_losses=True))
    assert again['reason'] == 'turn_jump'


def test_a_story_scene_without_readable_state_is_advanced_with_circle():
    sim = EnemyPhaseSim(screens=5, scene_at=(4, 3))     # two scene screens mid-phase
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase))
    assert result['phase'] == 'done' and result['turn'] == [7, 8] and result['presses'] == 5
    assert end_turn.report(phase)['scene_presses'] == 2


def test_an_endless_unreadable_scene_stops_at_its_cap(monkeypatch):
    monkeypatch.setattr(end_turn, 'SCENE_PRESSES', 3)
    sim = EnemyPhaseSim(screens=20, unreadable=True)
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase, accept_losses=True))
    assert result['phase'] == 'stopped' and result['reason'] == 'scene_too_long'
    assert result['presses'] == 3


# ---- defeat and stage restart (23 Oct live: blind Circles took the default retry) -----------

def test_a_falling_turn_counter_is_a_stage_restart_stop():
    sim = EnemyPhaseSim(screens=4, restart=True)
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase, accept_losses=True))
    assert result['phase'] == 'stopped' and result['reason'] == 'stage_restart'
    assert result['presses'] == 3
    start = state([unit(1, 5, 5)])
    assert end_turn.check(start, state([unit(1, 5, 5)], turn=1)) == 'stage_restart'
    assert end_turn.check(start, state([unit(1, 5, 5)], turn=9)) == 'turn_jump'


def test_an_unreadable_scene_after_an_accepted_loss_stops_at_once():
    # The defeat sequence starts with a dialogue right after the loss: never Circle through it.
    sim = EnemyPhaseSim(screens=5, lose_ally=True, lose_when=3, scene_at=(2, 1))
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase, accept_losses=True))
    assert result['phase'] == 'stopped' and result['reason'] == 'scene_after_loss'
    assert phase.losses == {2: 'unit_lost'} and phase.scene_presses == 0
    again = run(end_turn.advance(sim, phase, accept_losses=True))      # not excused by the flag
    assert again['reason'] == 'scene_after_loss' and again['presses'] == result['presses']


def test_a_scene_without_any_loss_is_still_advanced():
    sim = EnemyPhaseSim(screens=5, scene_at=(3, 2))
    phase = ended(sim)
    assert run(end_turn.advance(sim, phase, accept_losses=True))['phase'] == 'done'


# ---- review fixes (25 Oct) ------------------------------------------------------------------

def test_deltas_list_a_unit_gone_from_the_list_as_lost():
    # 23 Oct live: destroyed units vanish from the unit list instead of reading HP 0.
    start = state([unit(1, 5, 5), unit(3, 9, 9, FOE, hp=8000), unit(4, 1, 1, FOE, hp=0)])
    now = state([unit(1, 5, 5)])
    assert end_turn.deltas(start, now) == [
        {'object': 3, 'group': FOE, 'hp': [8000, None], 'lost': True}]


def test_units_gone_from_the_list_are_reported_destroyed():
    sim = EnemyPhaseSim(screens=3, lose_ally=True)
    phase = ended(sim)
    assert run(end_turn.advance(sim, phase))['reason'] == 'unit_lost'
    report = end_turn.report(phase)
    assert report['destroyed'] == [2]
    assert {'object': 2, 'group': ALLY, 'hp': [5000, None], 'lost': True} in report['deltas']


def test_one_unreadable_read_on_the_new_turn_map_is_not_pressed():
    # A single unreadable read may be a camera pan over the turn T+1 map, not a dialogue.
    sim = EnemyPhaseSim(screens=2, pan_reads=1)
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase))       # the sim raises if Circle hits turn 8
    assert result['phase'] == 'done' and result['presses'] == 2


def test_a_scene_at_the_start_of_the_new_turn_stops_for_the_agent():
    sim = EnemyPhaseSim(screens=2, turn_start_scene=True)
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase))       # never Circled: turn 8 is up
    assert result['phase'] == 'stopped' and result['reason'] == 'scene_at_new_turn'
    assert result['presses'] == 2


class WindowSim(EnemyPhaseSim):
    """Each enemy screen is a forecast window ('unknown' in the UI pool); directions are logged."""

    async def state(self):
        answer = await super().state()
        answer['screen'] = 'unknown' if self.screen == 'enemy' else 'no_menu'
        answer['ui_windows'] = [1] if self.screen == 'enemy' else []
        return answer

    async def press(self, button, frames=2):
        if self.screen == 'enemy' and button in ('up', 'down', 'left', 'right'):
            self.log.append(button)
            return
        await super().press(button, frames)


def test_a_recon_stop_halts_at_the_next_window_after_a_press():
    # M16 recon (3 Nov): stop at an enemy-attack forecast to look at it before any choice.
    sim = WindowSim(screens=3)
    phase = ended(sim)
    first = run(end_turn.advance(sim, phase, stop_at_window=True))
    assert first['phase'] == 'window' and first['screen'] == 'unknown'
    assert sim.log.count('circle') == 4 and sim.screens == 2      # one enemy Circle so far
    again = run(end_turn.advance(sim, phase, stop_at_window=True))
    assert again['phase'] == 'window' and sim.screens == 1
    done = run(end_turn.advance(sim, phase))
    assert done['phase'] == 'done'


# ---- M16 Evade (user, 3 Nov: "if the foe hit rate more than 30%, choose eva") ------------------
# Recon m16-rec-enemy: each enemy attack shows forecast window 0x08E4C81C, menu Start / Anim /
# Support (greyed, skipped) / Move with its cursor u32 at 0x08E4C898 (0 Start, 3 Move); Move opens
# SELECT-ACTION (window 0x08E4CD80) Atk. / Def. / Eva. with its cursor at 0x08E4CDB8; Eva. halves
# the hit (35 -> 17) and the cursor returns to Start.

class ReactionSim(EnemyPhaseSim):
    def __init__(self, hits=(35, 20, 56), **flags):
        super().__init__(screens=len(hits), **flags)
        self.hits, self.row, self.action, self.menu = list(hits), 0, 0, 'forecast'
        self.chosen, self.defended = [], []

    def current(self):
        return len(self.hits) - self.screens

    async def state(self):
        answer = await super().state()
        windows = []
        if self.screen == 'enemy':
            windows = [end_turn.FORECAST_WINDOW]
            if self.menu == 'action':
                windows.append(end_turn.ACTION_WINDOW)
        answer['ui_windows'] = [0x08E4BD0C, *windows]
        answer['screen'] = 'unknown' if windows else 'no_menu'
        return answer

    async def hit(self):
        if self.screen != 'enemy':
            return {'state': 'unknown', 'hit': None}
        hit = self.hits[self.current()]
        if self.flags.get('evade_ignored'):
            return {'state': 'hit', 'hit': hit}
        return {'state': 'hit', 'hit': hit // 2 if self.current() in self.chosen else hit}

    async def reaction_cursors(self):
        return self.row, self.action

    async def press(self, button, frames=2):
        if self.screen == 'enemy' and button in ('up', 'down', 'cross') or (
                self.screen == 'enemy' and self.menu == 'action'):
            self.log.append(button)
            step = {'down': 1, 'up': -1}.get(button, 0)
            if self.menu == 'forecast':
                rows = [0, 1, 3] if not self.flags.get('support') else [0, 1, 2, 3]
                if self.flags.get('stuck'):
                    return
                self.row = rows[(rows.index(self.row) + step) % len(rows)]
            elif button == 'circle':
                if self.action == 2:
                    self.chosen.append(self.current())
                if self.action == 1:
                    self.defended.append(self.current())
                self.menu, self.row = 'forecast', 0
            elif button == 'cross':
                self.menu = 'forecast'
            else:
                self.action = max(0, min(2, self.action + step))
            return
        if self.screen == 'enemy' and button == 'circle' and self.row == 3:
            self.log.append(button)
            self.menu, self.action = 'action', 0
            return
        if self.screen == 'enemy' and button == 'circle':
            assert self.row == 0, 'Start must be highlighted'
        await super().press(button, frames)


def test_evade_is_chosen_only_above_the_hit_limit_and_confirmed_by_the_lower_hit():
    sim = ReactionSim(hits=(35, 20, 56))
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase, evade_above=30))
    assert result['phase'] == 'done' and sim.chosen == [0, 2]
    assert [r['action'] for r in phase.reactions] == ['evade', 'default', 'evade']
    assert phase.reactions[0] == {'hit': [35, 17], 'action': 'evade', 'confirmed': True}
    assert end_turn.report(phase)['reactions'] == phase.reactions


def test_a_support_entry_takes_one_more_down():
    sim = ReactionSim(hits=(80,), support=True)
    phase = ended(sim)
    assert run(end_turn.advance(sim, phase, evade_above=30))['phase'] == 'done'
    assert sim.chosen == [0] and phase.reactions[0]['confirmed'] is True


def test_without_a_limit_or_a_cursor_reader_the_default_start_is_taken():
    sim = ReactionSim(hits=(80,))
    phase = ended(sim)
    run(end_turn.advance(sim, phase))
    assert sim.chosen == [] and 'down' not in sim.log

    class Blind(ReactionSim):
        reaction_cursors = None

    sim = Blind(hits=(80,))
    phase = ended(sim)
    run(end_turn.advance(sim, phase, evade_above=30))
    assert sim.chosen == [] and phase.reactions[0]['action'] == 'skipped'


def test_a_cursor_that_does_not_reach_move_stays_on_start_and_takes_the_default():
    sim = ReactionSim(hits=(80,), stuck=True)
    phase = ended(sim)
    assert run(end_turn.advance(sim, phase, evade_above=30))['phase'] == 'done'
    assert phase.reactions[0]['action'] == 'skipped' and sim.chosen == []


def test_an_action_menu_that_does_not_open_stops_the_phase_without_start():
    class NoMenu(ReactionSim):
        async def press(self, button, frames=2):
            await super().press(button, frames)
            if self.menu == 'action':
                self.menu = 'forecast'           # the Circle on Move did nothing visible

    sim = NoMenu(hits=(80,))
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase, evade_above=30))
    assert result['phase'] == 'stopped' and result['reason'] == 'reaction_failed'
    assert phase.reactions[0]['reason'] == 'action_menu_not_open' and sim.screens == 1


def test_an_evade_the_hit_does_not_confirm_is_reported_but_play_goes_on():
    sim = ReactionSim(hits=(80,), evade_ignored=True)
    phase = ended(sim)
    assert run(end_turn.advance(sim, phase, evade_above=30))['phase'] == 'done'
    assert phase.reactions[0] == {'hit': [80, 80], 'action': 'evade', 'confirmed': False}


def test_a_certain_hit_gets_defend_and_lower_hits_still_get_evade():
    # m16-i (3 Nov): Eva. left a 100% hit at 100%; user: at 100% choose Def., not Eva.
    sim = ReactionSim(hits=(100, 56, 20))
    phase = ended(sim)
    result = run(end_turn.advance(sim, phase, evade_above=30, defend_at=100))
    assert result['phase'] == 'done' and sim.defended == [0] and sim.chosen == [1]
    assert [r['action'] for r in phase.reactions] == ['defend', 'evade', 'default']
    assert phase.reactions[0] == {'hit': [100, 100], 'action': 'defend', 'confirmed': True}


def test_defend_works_without_an_evade_limit():
    sim = ReactionSim(hits=(80, 100))
    phase = ended(sim)
    assert run(end_turn.advance(sim, phase, defend_at=100))['phase'] == 'done'
    assert [r['action'] for r in phase.reactions] == ['default', 'defend']
    assert sim.defended == [1] and sim.chosen == []
