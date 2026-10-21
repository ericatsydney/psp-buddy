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
    assert result['ok'] and result['phase'] == 'fired'
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
    sim = Game(time_left=60)
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


def test_decline_after_a_move_says_the_unit_stays_moved():
    sim = Game()
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000, min_hit=90))
    assert result['phase'] == 'declined' and result['moved'] is True
    assert (sim.units[0]['tile_x'], sim.units[0]['tile_y']) == (5, 8)


def test_overlay_not_centred_on_the_unit_means_no_move_plan():
    sim = Game(range_stale=True)
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result == {'ok': False, 'phase': 'handover', 'reason': 'no_target'}
    assert sim.screen == 'map' and 'start' not in sim.log


def test_overlay_is_skipped_when_there_is_no_time_to_move_and_fire():
    sim = Game(time_left=60)
    sim.units[2]['tile_y'] = 12
    result = run(plan_act.plan_and_act(sim, POLICY, 1000))
    assert result['reason'] == 'no_target' and sim.log == []
