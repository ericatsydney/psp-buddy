import asyncio
import json
from pathlib import Path

from test_act import SimGame

from psp_buddy import plan_act
from psp_buddy.models import Policy

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
    assert sim.units[0]['counted_as_unmoved'] is False and sim.log[-2:] == ['down', 'circle']


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
