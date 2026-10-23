"""Turn bookkeeping over live read dicts (M9): ordering, skip/done, classification, report."""

import json
from pathlib import Path
from typing import Any

import pytest

from psp_buddy.turn import TurnLog, next_unit, ready_allies, report


def unit(obj: int, x: int, y: int, group: int, hp: int = 1000, *, ready: bool = True,
         max_hp: int = 1000) -> dict[str, Any]:
    return {"object": obj, "tile_x": x, "tile_y": y, "raw_menu_group_byte": group, "hp": hp,
            "max_hp": max_hp, "en": 50, "counted_as_unmoved": ready,
            "counter_value": 1 if ready else 0}


def state(*units: dict[str, Any]) -> dict[str, Any]:
    return {"turn": {"turn": 7}, "units": list(units)}


FOE = unit(900, 10, 10, 12)
FIRED = {"ok": True, "phase": "fired",
         "plan": {"act": {"attack": {"weapon": "W", "slot": 1, "target_object": 900}}},
         "forecast": {"hit": 47, "tile": [10, 10]},
         "outcome": {"deltas": [{"object": 1, "en": [230, 225]}]}}


def test_ready_allies_are_ordered_by_distance_to_the_nearest_foe_then_object() -> None:
    st = state(unit(3, 10, 12, 0), unit(1, 10, 14, 0), unit(2, 10, 12, 0), FOE,
               unit(800, 40, 40, 12))
    assert [u["object"] for u in ready_allies(st)] == [2, 3, 1]


def test_only_living_ready_allies_count() -> None:
    st = state(unit(1, 1, 1, 0), unit(2, 1, 2, 0, ready=False), unit(3, 1, 3, 0, hp=0),
               unit(4, 1, 4, 4), unit(5, 1, 5, 12))      # third force and foe are not allies
    assert [u["object"] for u in ready_allies(st)] == [1]


def test_without_foes_allies_are_ordered_by_object() -> None:
    st = state(unit(5, 1, 1, 0), unit(2, 9, 9, 0))
    assert [u["object"] for u in ready_allies(st)] == [2, 5]


def test_next_unit_skips_logged_units_and_reports_done() -> None:
    st = state(unit(1, 10, 11, 0), unit(2, 10, 12, 0), FOE)
    log = TurnLog()
    first = next_unit(st, log)
    assert first == {"unit_object": 1, "remaining": 2, "skipped": {}, "done": False,
                     "stopped": None}
    log.record(1, {"ok": False, "phase": "handover", "reason": "no_target"})
    second = next_unit(st, log)
    assert second["unit_object"] == 2 and second["remaining"] == 1
    assert second["skipped"] == {1: "no_target"}
    log.record(2, {"ok": False, "phase": "handover", "reason": "retreat_needed"})
    done = next_unit(st, log)
    assert done["done"] is True and done["unit_object"] is None and done["remaining"] == 0


def test_fired_unit_drops_out_because_its_counter_is_spent() -> None:
    log = TurnLog()
    assert log.record(1, FIRED) == "fired"
    st = state(unit(1, 10, 11, 0, ready=False), unit(2, 10, 12, 0), FOE)
    assert next_unit(st, log)["unit_object"] == 2
    entry = log.entries[0]
    assert (entry["unit"], entry["outcome"], entry["weapon"], entry["target"], entry["hit"]) == (
        1, "fired", "W", 900, 47)
    assert entry["deltas"] == [{"object": 1, "en": [230, 225]}]


@pytest.mark.parametrize("reason", ["no_target", "retreat_needed", "unit_not_ready",
                                    "unit_not_ally"])
def test_handover_reasons_that_skip(reason: str) -> None:
    log = TurnLog()
    assert log.record(1, {"ok": False, "phase": "handover", "reason": reason}) == "skipped"
    assert log.skipped == {1: reason} and log.stopped is None


@pytest.mark.parametrize("result,reason", [
    ({"ok": False, "phase": "failed", "moved": True, "standby": True,
      "plan": {"act": {"move_to": [1, 2]}},
      "outcome": {"stage": "target", "reason": "cursor_did_not_reach_tile"}},
     "target:cursor_did_not_reach_tile"),
    ({"ok": False, "phase": "declined", "reason": "hit_too_low", "moved": True,
      "standby": True, "back_out_failed": False}, "declined:hit_too_low"),
])
def test_a_moved_unit_that_waited_is_handled_not_a_stop(result: dict[str, Any],
                                                       reason: str) -> None:
    log = TurnLog()
    assert log.record(1, result) == "standby"
    assert log.stopped is None and log.entries[0]["reason"] == reason
    assert log.entries[0]["moved"] is True


def test_decline_without_a_move_is_a_skip_with_the_reason() -> None:
    log = TurnLog()
    result = {"ok": False, "phase": "declined", "reason": "hit_too_low", "moved": False,
              "back_out_failed": False, "forecast": {"hit": 30, "tile": [1, 1]}}
    assert log.record(1, result) == "skipped"
    assert log.skipped == {1: "declined:hit_too_low"} and log.entries[0]["hit"] == 30


@pytest.mark.parametrize("result,reason", [
    ({"ok": False, "phase": "declined", "reason": "hit_too_low", "moved": True,
      "back_out_failed": False}, "declined_after_move"),
    ({"ok": False, "phase": "declined", "reason": "hit_too_low", "moved": False,
      "back_out_failed": True}, "back_out_failed"),
    ({"ok": False, "phase": "failed", "reason": "io_error: x"}, "io_error: x"),
    ({"ok": False, "phase": "failed", "outcome": {"stage": "move", "reason": "en_not_charged"}},
     "move:en_not_charged"),
    ({"ok": False, "phase": "failed", "plan": {"act": {"move_to": [1, 2]}},
      "outcome": {"stage": "target", "reason": "target_not_hittable"}},
     "target:target_not_hittable"),                      # already moved
    ({"ok": False, "phase": "failed",
      "outcome": {"stage": "fire", "reason": "start_not_confirmed"}},
     "fire:start_not_confirmed"),                        # the attack may have started
    ({"ok": False, "phase": "handover", "reason": "unknown_weapons"}, "unknown_weapons"),
    ({"ok": True, "phase": "something_new"}, "unexpected_phase:something_new"),
])
def test_results_that_stop_the_turn(result: dict[str, Any], reason: str) -> None:
    log = TurnLog()
    assert log.record(1, result) == "stop"
    assert log.stopped == reason and log.skipped == {}
    st = state(unit(1, 10, 11, 0), FOE)
    stopped = next_unit(st, log)
    assert stopped["stopped"] == reason and stopped["unit_object"] is None
    assert stopped["done"] is False


def test_unreadable_state_stops_without_input() -> None:
    answer = next_unit({"turn": {"turn": 7}}, TurnLog())
    assert answer["unit_object"] is None and answer["stopped"].startswith("unknown_state")
    bad = state({"object": 1, "raw_menu_group_byte": 0, "hp": None, "tile_x": 1, "tile_y": 1,
                 "counted_as_unmoved": True})
    assert next_unit(bad, TurnLog())["stopped"].startswith("unknown_state")


def test_report_summarises_the_turn() -> None:
    log = TurnLog()
    log.record(1, FIRED)
    log.record(2, {"ok": False, "phase": "handover", "reason": "no_target"})
    st = state(unit(1, 10, 11, 0, ready=False), unit(2, 10, 12, 0), unit(3, 10, 13, 0), FOE)
    rep = report(log, st)
    assert rep["turn"] == 7 and rep["fired"] == 1 and rep["skipped"] == {2: "no_target"}
    assert rep["remaining"] == [3] and rep["stopped"] is None and rep["done"] is False
    assert len(rep["entries"]) == 2
    json.dumps(rep)                                      # serialisable (int keys become strings)


RETAINED = (Path(__file__).parents[2] / "local/move-attack-trial-20261017/spd4-run-20261021T2046"
            / "navigation-mailbox/nav-response-45abc2d4cbd8477e98354fd20c415286.json")


@pytest.mark.skipif(not RETAINED.exists(), reason="retained local run not present")
def test_retained_live_state_has_twenty_ready_allies_nearest_first() -> None:
    live = json.loads(RETAINED.read_text(encoding="utf-8"))["result"]
    ordered = ready_allies(live)
    assert len(ordered) == 20
    foes = [u for u in live["units"] if u["raw_menu_group_byte"] == 12]

    def nearest(u: dict[str, Any]) -> int:
        return min(abs(u["tile_x"] - f["tile_x"]) + abs(u["tile_y"] - f["tile_y"]) for f in foes)

    distances = [nearest(u) for u in ordered]
    assert distances == sorted(distances)


@pytest.mark.parametrize("stage", ["plan", "select", "attack_menu", "weapon", "target", "forecast"])
def test_failure_before_any_move_or_fire_is_a_skip(stage: str) -> None:
    log = TurnLog()
    result = {"ok": False, "phase": "failed",
              "plan": {"act": {"attack": {"weapon": "W", "slot": 1, "target_object": 9}}},
              "outcome": {"ok": False, "stage": stage, "reason": "cursor_did_not_reach_tile"}}
    assert log.record(1, result) == "skipped"
    assert log.skipped == {1: f"{stage}:cursor_did_not_reach_tile"} and log.stopped is None
    st = state(unit(1, 10, 11, 0), unit(2, 10, 12, 0), FOE)
    assert next_unit(st, log)["unit_object"] == 2
