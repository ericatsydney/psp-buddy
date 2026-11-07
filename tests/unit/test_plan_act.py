import asyncio
import json
from pathlib import Path

from test_act import SimGame

from psp_buddy import act, plan_act
from psp_buddy.models import Policy
from psp_buddy.policy import parse_policy

POLICY = Policy()
POWER = {'Vulcan': 1000, 'Grenade': 2000, 'BeamRifle': 3000}


class Game(SimGame):
    def __init__(self, **flags):
        super().__init__(**flags)
        for u in self.units:
            u['max_hp'] = u['hp']
        for w in self.weapons:
            w['power'] = POWER[w['name']]


def run(coro):
    return asyncio.run(coro)


def test_attack_from_current_tile_fires_after_agreeing_forecast(tmp_path: Path):
    sim, log = Game(), tmp_path / 'damage-log.jsonl'
    result = run(plan_act.plan_and_act(sim, POLICY, 1000, hits={2000: 42}, damage_log=log))
    assert result['ok'] and result['phase'] == 'fired'
    assert result['plan']['act']['attack'] == {'weapon': 'Grenade', 'slot': 1,
                                               'target_object': 2000}
    assert sim.log.count('start') == 1 and sim.screen == 'map'
    record = json.loads(log.read_text(encoding='utf-8'))
    assert record['forecast_hit'] == 42 and record['power'] == 2000 and record['target'] == 2000


def test_forced_mismatch_refuses_to_fire_and_backs_out():
    sim = Game()
    result = run(plan_act.plan_and_act(sim, POLICY, 1000, hits={2000: 60}))   # screen shows 42
    assert result['ok'] is False and result['phase'] == 'declined'
    assert result['reason'] == 'forecast_differs_from_plan'
    assert 'start' not in sim.log and sim.screen == 'map'
    assert sim.units[0]['counted_as_unmoved'] is True


def test_hit_changing_between_target_and_forecast_is_declined():
    class Shifty(Game):
        calls = 0

        async def hit(self):
            answer = await super().hit()
            if self.screen == 'forecast':
                answer = {'state': 'hit', 'hit': 43}
            return answer

    sim = Shifty()
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['reason'] == 'hit_changed_between_target_and_forecast'
    assert 'start' not in sim.log and sim.screen == 'map'


def test_zero_hit_is_not_fired():
    gate = plan_act.forecast_gate(
        {'attack': {'weapon': 'W', 'target_object': 1}},
        {'stages': [{'stage': 'plan', 'facts': {'target': 1, 'weapon': 'W'}},
                    {'stage': 'target', 'facts': {'hit': 0}},
                    {'stage': 'forecast', 'facts': {'hit': 0}}]}, {})
    assert gate == 'hit_too_low'


def test_out_of_reach_foe_opens_move_range_once_then_moves_and_attacks():
    sim = Game()
    sim.units[2]['tile_y'] = 12                 # 7 tiles away: only reachable after a move
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['ok'] and result['phase'] == 'fired' and result['moved'] is True
    act = result['plan']['act']
    assert act['attack']['weapon'] == 'BeamRifle' and act['move_to'] == [5, 8]
    assert (sim.units[0]['tile_x'], sim.units[0]['tile_y']) == (5, 8)


def test_a_move_range_drawn_late_is_still_used_for_the_plan():
    # Fast reads (1 Nov) can read the state before the game draws the range.
    sim = Game(range_late=2)
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['ok'] and result['moved'] is True


def test_nothing_in_reach_even_with_moves_is_a_handover_with_no_attack():
    sim = Game()
    sim.units[2]['tile_y'] = 30
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result == {'ok': False, 'phase': 'handover', 'reason': 'no_target'}
    assert 'start' not in sim.log and sim.screen == 'map'


def test_injured_unit_hands_over_without_input():
    sim = Game()
    sim.units[0]['hp'] = 1000
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['reason'] == 'retreat_needed' and sim.log == []


def test_no_time_left_to_fire_backs_out_instead():
    sim = Game(time_left=50)
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['phase'] == 'declined' and result['reason'] == 'no_time_to_fire'
    assert 'start' not in sim.log and sim.screen == 'map'


def test_back_out_failure_is_reported_not_raised():
    from psp_buddy import act

    class Flaky(Game):
        async def press(self, button, frames=2):
            if button == 'cross':
                raise act.ActIOError('press budget exhausted')
            await super().press(button, frames)

    result = run(plan_act.plan_and_act(Flaky(), POLICY, 1000, hits={2000: 99}))
    assert result['ok'] is False and result['phase'] == 'declined'
    assert result['back_out_failed'] is True


def test_unexpected_data_is_a_failure_report_not_an_exception():
    class Broken(Game):
        async def read_weapons(self, unit_object):
            raise KeyError('weapons')

    result = run(plan_act.plan_and_act(Broken(), POLICY, 1000))
    assert result['ok'] is False and result['phase'] == 'failed'


def test_unwritable_damage_log_does_not_lose_the_fired_result(tmp_path: Path):
    sim = Game()
    result = run(plan_act.plan_and_act(sim, POLICY, 1000, damage_log=tmp_path))   # a directory
    assert result['ok'] is True and result['phase'] == 'fired' and 'log_error' in result
    assert sim.log.count('start') == 1


def test_min_hit_from_the_caller_declines_a_low_forecast():
    sim = Game()
    result = run(plan_act.plan_and_act(sim, POLICY, 1000, min_hit=50))       # screen shows 42
    assert result['phase'] == 'declined' and result['reason'] == 'hit_too_low'
    assert 'start' not in sim.log and sim.screen == 'map'


def test_decline_after_a_move_says_the_unit_stays_moved_and_waits():
    # MVP rule (user, 22 Oct): a moved unit that cannot finish its attack chooses Standby.
    sim = Game()
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000, min_hit=90))
    assert result['phase'] == 'declined' and result['moved'] is True
    assert result['standby'] is True and sim.screen == 'map'
    assert (sim.units[0]['tile_x'], sim.units[0]['tile_y']) == (5, 8)
    assert sim.units[0]['counted_as_unmoved'] is False and sim.log[-2:] == ['up', 'circle']


def test_overlay_not_centred_on_the_unit_means_no_move_plan():
    sim = Game(range_stale=True)
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result == {'ok': False, 'phase': 'handover', 'reason': 'no_target'}
    assert sim.screen == 'map' and 'start' not in sim.log


def test_overlay_is_skipped_when_there_is_no_time_to_move_and_fire():
    sim = Game(time_left=50)
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['reason'] == 'no_target' and sim.log == []


def test_greyed_weapon_is_excluded_and_the_next_one_is_fired():
    # Force Impulse (22 Oct live): the chosen weapon is greyed out, the target select never opens.
    sim = Game(grey_rows=(1,))                  # Grenade (row 1) is the planned median weapon
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['ok'] and result['phase'] == 'fired'
    assert result['plan']['act']['attack']['weapon'] != 'Grenade'
    assert result['excluded'] == [1]
    assert sim.log.count('start') == 1 and sim.screen == 'map'


def test_every_weapon_greyed_ends_as_a_failed_report_after_bounded_retries():
    sim = Game(grey_rows=(0, 1, 2))
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['ok'] is False and result['phase'] in ('failed', 'handover')
    assert 'start' not in sim.log and sim.screen == 'map'
    assert len(result.get('excluded', [])) <= plan_act.MAX_REPLANS


def test_replan_is_not_tried_after_the_unit_has_moved():
    sim = Game(grey_rows=(2,))
    sim.units[2]['tile_y'] = 12                 # only BeamRifle (row 2, P) reaches: needs a move
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['ok'] is False and result['phase'] == 'failed'
    assert 'excluded' not in result or result['excluded'] == []
    assert result['moved'] is True and result['standby'] is True
    assert sim.units[0]['counted_as_unmoved'] is False and sim.screen == 'map'


class PostMove(Game):
    """Exposes the post-move menu (row, count) read at 0x08E4BEB4, as the live helper does."""

    async def post_move_menu(self):
        if self.screen == 'unit_menu' and self.acting is not None and self.acting.get('moved'):
            return self.entry, len(self.entries)
        return None


def test_standby_is_one_up_from_attack_on_a_longer_post_move_menu():
    # 26 Oct live, stage 33: Methuss's post-move menu is Attack / Repair / Standby; the menu wraps
    # (31 Oct recon m14rec3), so one Up from Attack reaches Standby whatever the length.
    sim = PostMove(grey_rows=(2,), moved_entries=('Attack', 'Repair', 'Standby'))
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['phase'] == 'failed' and result['moved'] is True
    assert result['standby'] is True and sim.screen == 'map'
    assert sim.units[0]['counted_as_unmoved'] is False
    assert 'down' not in sim.log[-4:] and sim.log[-2:] == ['up', 'circle']


def test_standby_is_not_confirmed_when_the_menu_cursor_is_not_on_it():
    class Stuck(PostMove):
        async def post_move_menu(self):
            return (0, len(self.entries)) if self.screen == 'unit_menu' else None

    sim = Stuck(grey_rows=(2,), moved_entries=('Attack', 'Repair', 'Standby'))
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['standby'] is False and 'circle' != sim.log[-1]
    assert sim.units[0]['counted_as_unmoved'] is True


def test_no_up_is_pressed_when_the_post_move_menu_is_not_seen():
    class Unseen(PostMove):
        async def post_move_menu(self):
            return None

    sim = Unseen(grey_rows=(2,))
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['standby'] is False and 'up' not in sim.log


def test_a_standby_the_game_does_not_confirm_is_reported_and_closed():
    sim = Game(grey_rows=(2,), menu_standby_ignored=True)
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['phase'] == 'failed' and result['moved'] is True
    assert result['standby'] is False and sim.units[0]['counted_as_unmoved'] is True
    assert sim.log[-1] == 'cross'


def test_a_failure_that_did_not_back_out_does_not_press_standby():
    sim = Game(menu_window=1)                   # the weapon list looks too short: no back-out
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['outcome']['stage'] == 'attack_menu' and result['moved'] is True
    assert 'standby' not in result and sim.log[-1] == 'circle'


def test_a_failure_before_any_move_does_not_press_standby(monkeypatch):
    monkeypatch.setattr(plan_act, 'MAX_REPLANS', 0)
    sim = Game(grey_rows=(1,))                  # Grenade (row 1) is the planned median weapon
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['phase'] == 'failed' and result['moved'] is False and 'standby' not in result


def test_standby_is_not_pressed_without_time_for_it(monkeypatch):
    monkeypatch.setattr(plan_act, 'STANDBY_NEEDS', 10 ** 6)     # no time left for Standby
    sim = Game(time_left=500)
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000, min_hit=90))
    assert result['phase'] == 'declined' and result['moved'] is True
    assert result['standby'] is False and sim.units[0]['counted_as_unmoved'] is True
    assert sim.log[-3:] == ['cross', 'cross', 'cross']


class Named(Game):
    NAMES = {1000: 'Gundam・00', 1001: 'Z Gundam', 2000: 'Mercurius', 2001: 'Taurus'}

    def __init__(self, **flags):
        super().__init__(**flags)
        self.weapon_reads: list[int] = []
        self.units[3].update(tile_x=6, tile_y=8)       # the grunt is in Grenade reach too

    async def read_weapons(self, unit_object):
        self.weapon_reads.append(unit_object)
        return {**await super().read_weapons(unit_object), 'mech_name': self.NAMES[unit_object]}


def test_named_boss_is_attacked_after_the_grunt_and_names_are_cached():
    from psp_buddy.policy import parse_policy
    policy = parse_policy('target non-bosses before bosses')
    plain = run(plan_act.plan_and_act(Named(), POLICY, 1000))
    assert plain['plan']['act']['attack']['target_object'] == 2000     # tie broken by object
    sim, names = Named(), {}
    result = run(plan_act.plan_and_act(sim, policy, 1000, boss_names=['Mercurius'],
                                       mech_names=names))
    assert result['ok'] and result['plan']['act']['attack']['target_object'] == 2001
    assert names == {2000: 'Mercurius', 2001: 'Taurus'}
    assert (sim.weapon_reads.count(2000), sim.weapon_reads.count(2001)) == (1, 1)
    again = Named()
    run(plan_act.plan_and_act(again, policy, 1000, boss_names=['Mercurius'], mech_names=names))
    assert {2000, 2001}.isdisjoint(again.weapon_reads)        # foe names come from the cache


def test_default_boss_names_apply_when_the_policy_asks_for_non_bosses_first():
    from psp_buddy.policy import parse_policy
    result = run(plan_act.plan_and_act(Named(), parse_policy('target non-bosses before bosses'),
                                       1000))
    assert result['plan']['act']['attack']['target_object'] == 2001


def test_a_pending_dialogue_is_finished_before_the_next_plan():
    from test_act import ContinueAttack
    sim = ContinueAttack(continue_skill=False, kills=False)
    for u in sim.units:
        u['max_hp'] = u['hp']
    for w in sim.weapons:
        w['power'] = POWER[w['name']]
    sim.screen, sim.lines = 'dialogue', 4
    result = run(plan_act.plan_and_act(sim, POLICY, 1000, settle_first=True))
    assert result['dialogue_settled'] == {'settled': True, 'presses': 4}
    assert result['ok'] and result['phase'] == 'fired'
    assert sim.log[:4] == ['goto(4, 5)', 'circle', 'goto(4, 5)', 'circle']


def test_a_settle_that_progresses_but_does_not_finish_waits_for_the_next_call():
    from test_act import ContinueAttack
    sim = ContinueAttack(continue_skill=False, kills=False, time_left=75)
    sim.screen, sim.lines = 'dialogue', 500
    result = run(plan_act.plan_and_act(sim, POLICY, 1000, settle_first=True))
    assert result['phase'] == 'dialogue_pending' and result['dialogue_settled']['presses'] > 0
    assert 'start' not in sim.log


# ---- M12 protected units (user, 25 Oct: a lost ally only Standbys on the retry) --------------

def test_a_protected_unit_is_left_alone_with_no_input():
    sim = Game()
    result = run(plan_act.plan_and_act(sim, POLICY, 1000, protected={1000}))
    assert result == {'ok': False, 'phase': 'handover', 'reason': 'protected', 'moved': False}
    assert sim.log == []


def test_an_unprotected_unit_still_fires():
    sim = Game()
    result = run(plan_act.plan_and_act(sim, POLICY, 1000, protected={1001}, hits={2000: 42}))
    assert result['phase'] == 'fired'


def test_a_move_that_lands_on_another_tile_ends_with_standby():
    # 31 Oct live (m14s33h): the unit moved one tile short of the plan and the turn stopped with
    # its Attack / Standby menu open.
    class Slips(PostMove):
        async def press(self, button, frames=2):
            if self.screen == 'move_range' and button == 'circle':
                self.cursor = [self.cursor[0], self.cursor[1] - 1]
            await super().press(button, frames)

    sim = Slips()
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['phase'] == 'failed' and result['outcome']['reason'] == 'move_not_confirmed'
    assert result['moved'] is True and result['standby'] is True
    assert sim.units[0]['counted_as_unmoved'] is False and sim.screen == 'map'


def test_a_move_not_confirmed_on_the_same_tile_presses_nothing_more():
    class Stays(PostMove):
        async def press(self, button, frames=2):
            if self.screen == 'move_range' and button == 'circle':
                self.log.append(button)
                return                                   # the game ignored the Circle
            await super().press(button, frames)

    sim = Stays()
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['outcome']['reason'] == 'move_not_confirmed' and 'standby' not in result
    assert sim.log[-1] == 'circle'


# M16 ally safety (3 Nov): turn-1 hold and advance toward the foes when nothing is in reach.
SAFETY = parse_policy('hold units without focus or sense on turn 1; '
                      'advance toward foes when none is in reach')


class Turn(PostMove):
    """A chosen turn number and, optionally, the acting pilot's spirit list."""

    def __init__(self, turn=7, spirits=None, **flags):
        super().__init__(**flags)
        self.turn, self.pilot = turn, spirits
        self.sp, self.active = 50, ()

    async def state(self):
        answer = await super().state()
        answer['turn'] = {'turn': self.turn}
        return answer

    async def spirits(self, unit_object):
        self.log.append('spirits')
        if self.pilot is None:
            raise act.ActIOError('no spirit reader in this trial')
        return {'sp': self.sp, 'active': list(self.active),
                'spirits': [{'id': i + 1, 'name': n, 'learned': True, 'cost': 20, 'row': i}
                            for i, n in enumerate(self.pilot)]}


def far(sim):
    sim.units[2]['tile_y'] = 30          # (5,30); foe 2001 at (12,12) is the nearest
    return sim


def test_a_unit_with_nothing_in_reach_advances_then_waits():
    sim = far(Turn(turn=2))
    result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert result['ok'] is True and result['phase'] == 'advanced'
    assert result['moved'] is True and result['standby'] is True
    assert result['plan']['act'] == {'unit_object': 1000, 'move_to': [5, 8]}
    assert (sim.units[0]['tile_x'], sim.units[0]['tile_y']) == (5, 8)
    assert sim.units[0]['counted_as_unmoved'] is False and sim.screen == 'map'
    assert 'start' not in sim.log and sim.log[-2:] == ['up', 'circle']


def test_on_turn_one_a_pilot_without_focus_or_sense_is_held_with_no_input():
    for pilot in (None, ['Alert']):          # unreadable spirits count as none
        sim = far(Turn(turn=1, spirits=pilot))
        result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
        assert result == {'ok': False, 'phase': 'handover', 'reason': 'held_turn_one'}
        assert sim.log == ['spirits'] and sim.units[0]['counted_as_unmoved'] is True


def test_on_turn_one_a_pilot_with_sense_advances():
    sim = far(Turn(turn=1, spirits=['Alert', 'Sense']))
    result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert result['phase'] == 'advanced' and result['standby'] is True


def test_on_turn_one_a_held_pilot_still_attacks_from_its_tile():
    sim = Turn(turn=1)
    result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert result['phase'] == 'fired' and result['moved'] is False


def test_spirits_are_not_read_without_the_safety_clauses():
    sim = far(Turn(turn=1, spirits=['Focus']))
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['reason'] == 'no_target' and 'spirits' not in sim.log


def test_standby_on_a_post_move_menu_with_only_standby_needs_no_up():
    sim = far(Turn(turn=2, moved_entries=('Standby',)))
    result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert result['phase'] == 'advanced' and result['standby'] is True
    assert 'up' not in sim.log and sim.log[-1] == 'circle'


def test_an_advance_that_would_overrun_the_cursor_budget_is_handed_over_unpressed():
    class Tight(Turn):
        def cursor_presses_left(self):
            return 5

    sim = far(Tight(turn=2))
    result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert result['reason'] == 'cursor_budget' and result['moved'] is False
    assert sim.units[0]['counted_as_unmoved'] is True


def test_an_advance_that_lands_on_another_tile_still_ends_with_standby():
    class Slips(Turn):
        async def press(self, button, frames=2):
            if self.screen == 'move_range' and button == 'circle':
                self.cursor = [self.cursor[0], self.cursor[1] - 1]
            await super().press(button, frames)

    sim = far(Slips(turn=2))
    result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert result['phase'] == 'failed' and result['outcome']['reason'] == 'move_not_confirmed'
    assert result['moved'] is True and result['standby'] is True
    assert sim.units[0]['counted_as_unmoved'] is False and sim.screen == 'map'


def test_an_advance_whose_standby_is_not_confirmed_is_reported():
    class Stuck(Turn):
        async def post_move_menu(self):
            return (0, len(self.entries)) if self.screen == 'unit_menu' else None

    sim = far(Stuck(turn=2))
    result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert result['phase'] == 'advanced' and result['standby'] is False
    assert sim.units[0]['counted_as_unmoved'] is True


def test_a_stale_last_row_on_a_two_entry_menu_is_not_trusted():
    class Stale(Turn):
        async def post_move_menu(self):
            return (1, 2) if self.screen == 'unit_menu' else None    # an earlier unit's Standby

    sim = far(Stale(turn=2))
    result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert result['standby'] is False
    assert sim.log[-2:] == ['goto(5, 8)', 'circle'] and 'up' not in sim.log   # only the Move
    assert sim.units[0]['counted_as_unmoved'] is True


def test_spirits_are_read_only_when_the_turn_one_hold_can_apply():
    sim = far(Turn(turn=2, spirits=['Focus']))
    run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert 'spirits' not in sim.log
    advance_only = parse_policy('advance toward foes when none is in reach')
    sim = far(Turn(turn=1, spirits=['Focus']))
    run(plan_act.plan_and_act(sim, advance_only, 1000))
    assert 'spirits' not in sim.log


def test_an_unreadable_turn_field_counts_as_turn_one():
    class Odd(Turn):
        async def state(self):
            answer = await super().state()
            answer['turn'] = 3
            return answer

    sim = far(Odd())
    result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert result['reason'] == 'held_turn_one'


def test_an_advance_that_fails_before_the_move_reports_no_move():
    class NoSelect(Turn):           # the overlay opens, then selecting the unit fails
        async def goto(self, tile):
            if self.screen == 'map' and list(tile) == [5, 5] and 'circle' in self.log:
                return {'reached': False, 'cursor': {'x': 0, 'y': 0}}
            return await super().goto(tile)

    sim = far(NoSelect(turn=2))
    result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert result['phase'] == 'failed' and result['moved'] is False and 'standby' not in result
    assert sim.units[0]['counted_as_unmoved'] is True


# M16 fix (user, 3 Nov, run m16-a): Michel's VF-25G had Sense learned, but its Command menu is
# not screen-checked, so the cast was skipped and it advanced into a counter (4700 -> 1310 HP).
CASTING = parse_policy('use spirits before attacking; hold units without focus or sense on turn 1; '
                       'advance toward foes when none is in reach')


def casting(monkeypatch, answer):
    calls = []

    async def fake_cast(io, state, unit_object, mech_name, spirit_skip=None):
        calls.append(unit_object)
        return answer

    monkeypatch.setattr(plan_act, '_cast', fake_cast)
    return calls


def test_on_turn_one_sense_counts_only_once_it_is_cast(monkeypatch):
    calls = casting(monkeypatch, {'status': 'cast', 'spirit': 'Sense', 'on_map': True})
    sim = far(Turn(turn=1, spirits=['Sense']))
    result = run(plan_act.plan_and_act(sim, CASTING, 1000))
    assert result['phase'] == 'advanced' and result['spirit']['status'] == 'cast'
    assert calls == [1000]


def test_on_turn_one_a_sense_pilot_whose_cast_is_skipped_is_held(monkeypatch):
    calls = casting(monkeypatch, {'status': 'skipped', 'reason': 'menu_layout_unknown',
                                  'on_map': True})
    sim = far(Turn(turn=1, spirits=['Sense']))
    result = run(plan_act.plan_and_act(sim, CASTING, 1000))
    assert result['reason'] == 'held_turn_one' and calls == [1000]
    assert sim.units[0]['counted_as_unmoved'] is True


def test_a_skipped_cast_on_turn_one_still_allows_an_attack_from_the_tile(monkeypatch):
    calls = casting(monkeypatch, {'status': 'skipped', 'reason': 'menu_layout_unknown',
                                  'on_map': True})
    sim = Turn(turn=1, spirits=['Sense'])
    result = run(plan_act.plan_and_act(sim, CASTING, 1000))
    assert result['phase'] == 'fired' and result['moved'] is False and calls == [1000]


def test_an_active_sense_needs_no_cast_and_unaffordable_sense_holds(monkeypatch):
    calls = casting(monkeypatch, {'status': 'cast', 'spirit': 'Focus', 'on_map': True})
    sim = far(Turn(turn=1, spirits=['Sense']))
    sim.active = ('Sense',)
    assert run(plan_act.plan_and_act(sim, CASTING, 1000))['phase'] == 'advanced'
    assert calls == []
    sim = far(Turn(turn=1, spirits=['Sense']))
    sim.sp = 5
    assert run(plan_act.plan_and_act(sim, CASTING, 1000))['reason'] == 'held_turn_one'
    assert calls == []


def test_a_cast_that_left_a_menu_open_stops(monkeypatch):
    casting(monkeypatch, {'status': 'skipped', 'reason': 'x', 'on_map': False})
    sim = far(Turn(turn=1, spirits=['Sense']))
    result = run(plan_act.plan_and_act(sim, CASTING, 1000))
    assert result['phase'] == 'failed' and result['reason'] == 'spirit_menus_not_closed'


def test_no_turn_one_cast_for_a_unit_that_will_retreat(monkeypatch):
    calls = casting(monkeypatch, {'status': 'cast', 'spirit': 'Sense', 'on_map': True})
    sim = far(Turn(turn=1, spirits=['Sense']))
    sim.units[0]['hp'], sim.units[0]['max_hp'] = 1000, 5000
    result = run(plan_act.plan_and_act(sim, CASTING, 1000))
    assert result['reason'] == 'retreat_needed' and calls == []


def test_standby_first_on_a_post_move_menu_is_found_from_the_bitmask():
    # m16-c turn 2: a ship's post-move menu was Standby / Retrieve (cursor on Retrieve after Up);
    # the old "one Up from Attack" rule could not reach Standby. Bits: Standby 25, Retrieve 26.
    class Ship(Turn):
        async def menu_masks(self):
            bits = {'Attack': 3, 'Repair': 5, 'Standby': 25, 'Retrieve': 26}
            moved = (self.screen == 'unit_menu' and self.acting is not None
                     and self.acting.get('moved'))
            return 0, (sum(1 << bits[e] for e in self.entries) if moved else 0)

    sim = far(Ship(turn=2, moved_entries=('Standby', 'Retrieve')))
    result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert result['phase'] == 'advanced' and result['standby'] is True
    assert 'up' not in sim.log and sim.log[-1] == 'circle'
    sim = far(Ship(turn=2, moved_entries=('Attack', 'Repair', 'Standby')))
    result = run(plan_act.plan_and_act(sim, SAFETY, 1000))
    assert result['standby'] is True and sim.log[-3:] == ['down', 'down', 'circle']


def test_foe_reach_is_read_once_per_trial_and_limits_the_move():
    # M16 (user, 3 Nov: limit foes in reach). Foes reach 4 (move 2 + Vulcan 2): every tile from
    # which a moved BeamRifle (2~4) reaches foe 2000 at (5,12) is within its reach, so no move.
    class Reads(Game):
        foe_reads = 0

        async def read_weapons(self, unit_object):
            answer = await super().read_weapons(unit_object)
            if unit_object in (2000, 2001):
                self.foe_reads += 1
                return {**answer, 'move': 2, 'weapons': [dict(w) for w in self.weapons[:1]],
                        'mech_name': 'Zaku'}
            return answer

    policy = parse_policy('end moves within reach of at most 0 foes')
    sim = Reads()
    sim.units[2]['tile_y'] = 12
    cache: dict[int, int] = {}
    result = run(plan_act.plan_and_act(sim, policy, 1000, foe_reach=cache))
    assert cache == {2000: 4, 2001: 4} and sim.foe_reads == 2
    assert result['phase'] == 'handover' and result['reason'] == 'no_target'
    run(plan_act.plan_and_act(sim, policy, 1001, foe_reach=cache))
    assert sim.foe_reads == 2                          # cached for the rest of the trial


def test_boss_names_and_foe_reach_share_one_weapon_read_per_foe():
    # Review 3 Nov: boss detection and the reach limit each read every foe's weapons.
    class Reads(Game):
        foe_reads = 0

        async def read_weapons(self, unit_object):
            answer = await super().read_weapons(unit_object)
            if unit_object in (2000, 2001):
                self.foe_reads += 1
                return {**answer, 'move': 2, 'mech_name': 'Zaku'}
            return answer

    policy = parse_policy('target non-bosses before bosses; '
                          'end moves within reach of at most 2 foes')
    sim = Reads()
    names: dict[int, str] = {}
    reach: dict[int, int] = {}
    run(plan_act.plan_and_act(sim, policy, 1000, mech_names=names, foe_reach=reach))
    assert sim.foe_reads == 2 and set(names) == set(reach) == {2000, 2001}


# M16 (m16-i, 3 Nov): a damaged unit casts Focus/Sense, then attacks safely or moves away.
RETREAT = parse_policy('use spirits before attacking; move damaged units away from foes')


def hurt(sim):
    sim.units[0]['hp'], sim.units[0]['max_hp'] = 1000, 5000
    return sim


def test_a_damaged_unit_casts_then_moves_away_and_waits(monkeypatch):
    calls, seen = [], []

    async def fake_cast(io, state, unit_object, mech_name, spirit_skip=None):
        calls.append(unit_object)
        seen.append(list(io.log))
        return {'status': 'cast', 'spirit': 'Sense', 'on_map': True}

    monkeypatch.setattr(plan_act, '_cast', fake_cast)
    sim = hurt(far(Turn(turn=2)))
    result = run(plan_act.plan_and_act(sim, RETREAT, 1000))
    assert result['phase'] == 'advanced' and result['standby'] is True
    assert result['plan']['expect']['rule'] == 'retreat' and calls == [1000]
    assert not any(step.startswith('goto') for step in seen[0][1:])    # cast before the move
    assert result['spirit']['status'] == 'cast'


def test_a_damaged_unit_with_no_safer_tile_casts_and_stays(monkeypatch):
    calls = casting(monkeypatch, {'status': 'cast', 'spirit': 'Focus', 'on_map': True})
    monkeypatch.setattr(plan_act, 'plan_attack',
                        lambda *a, **k: {'handover': True, 'reason': 'retreat_stay'})
    sim = hurt(Turn(turn=2))
    result = run(plan_act.plan_and_act(sim, RETREAT, 1000))
    assert result['reason'] == 'retreat_stay' and calls == [1000]
    assert result['spirit']['spirit'] == 'Focus'


def test_a_damaged_unit_whose_cast_leaves_a_menu_open_stops(monkeypatch):
    casting(monkeypatch, {'status': 'skipped', 'reason': 'x', 'on_map': False})
    sim = hurt(far(Turn(turn=2)))
    result = run(plan_act.plan_and_act(sim, RETREAT, 1000))
    assert result['phase'] == 'failed' and result['reason'] == 'spirit_menus_not_closed'
    assert sim.units[0]['counted_as_unmoved'] is True


def test_a_retreat_without_the_spirit_clause_casts_nothing(monkeypatch):
    calls = casting(monkeypatch, {'status': 'cast', 'spirit': 'Sense', 'on_map': True})
    sim = hurt(far(Turn(turn=2)))
    result = run(plan_act.plan_and_act(sim, parse_policy('move damaged units away from foes'),
                                       1000))
    assert result['phase'] == 'advanced' and calls == []


def test_a_retreat_over_the_cursor_budget_casts_nothing(monkeypatch):
    # Review 3 Nov: the cast must not run before a cursor_budget refusal ("nothing pressed").
    class Tight(Turn):
        def cursor_presses_left(self):
            return 5

    calls = casting(monkeypatch, {'status': 'cast', 'spirit': 'Sense', 'on_map': True})
    sim = hurt(far(Tight(turn=2)))
    result = run(plan_act.plan_and_act(sim, RETREAT, 1000))
    assert result['reason'] == 'cursor_budget' and calls == []


def test_the_retreat_clause_alone_reads_foe_reach():
    # Review 3 Nov: without the limit clause the retreat still needs each foe's reach.
    class Reads(Turn):
        foe_reads = 0

        async def read_weapons(self, unit_object):
            answer = await super().read_weapons(unit_object)
            if unit_object in (2000, 2001):
                self.foe_reads += 1
                return {**answer, 'move': 2, 'weapons': [dict(w) for w in self.weapons[:1]]}
            return answer

    sim = hurt(far(Reads(turn=2)))
    cache: dict[int, int] = {}
    run(plan_act.plan_and_act(sim, parse_policy('move damaged units away from foes'), 1000,
                              foe_reach=cache))
    assert sim.foe_reads == 2 and set(cache) == {2000, 2001}


class BigGrunt(Named):
    """Mercurius has far more max HP than two other foes, so the HP rule alone makes it a boss."""
    NAMES = {**Named.NAMES, 2002: 'Taurus'}

    def __init__(self, **flags):
        super().__init__(**flags)
        far = next(u for u in self.units if u['object'] == 2001)
        self.units.append({**far, 'object': 2002, 'tile_x': 30, 'tile_y': 30})   # out of reach
        for u in self.units:
            if u['object'] == 2000:
                u['max_hp'] = 99999


def test_boss_factor_zero_keeps_only_the_named_bosses():
    from psp_buddy.policy import parse_policy
    policy = parse_policy('target non-bosses before bosses')
    by_hp = run(plan_act.plan_and_act(BigGrunt(), policy, 1000, boss_names=['Nobody']))
    assert by_hp['plan']['act']['attack']['target_object'] == 2001
    named = run(plan_act.plan_and_act(BigGrunt(), policy, 1000, boss_names=['Nobody'],
                                      boss_factor=0))
    assert named['plan']['act']['attack']['target_object'] == 2000
