import json

import pytest

from psp_buddy import retry

ALLY, FOE = 0, 12


def unit(obj, x, y, group=ALLY, hp=5000, en=100, ready=True):
    return {'object': obj, 'tile_x': x, 'tile_y': y, 'raw_menu_group_byte': group, 'hp': hp,
            'en': en, 'counted_as_unmoved': ready}


def state(units=None, turn=7):
    units = units if units is not None else [unit(1, 5, 5), unit(2, 6, 5),
                                             unit(3, 9, 9, FOE, ready=False)]
    return {'turn': {'turn': turn}, 'units': units}


SHA = 'a' * 64


# ---- manifest --------------------------------------------------------------------------------

def test_manifest_records_turn_and_every_unit():
    m = retry.manifest(state(), SHA)
    assert m['sha256'] == SHA and m['turn'] == 7
    assert m['units'][0] == {'object': 1, 'group': ALLY, 'hp': 5000, 'en': 100, 'tile': [5, 5],
                             'unmoved': True}
    assert len(m['units']) == 3


def test_manifest_needs_a_player_phase_start():
    with pytest.raises(ValueError):            # an ally has already acted
        retry.manifest(state([unit(1, 5, 5), unit(2, 6, 5, ready=False)]), SHA)
    with pytest.raises(ValueError):
        retry.manifest({'units': []}, SHA)
    with pytest.raises(ValueError):
        retry.manifest(state(), 'nothex')


def test_a_relaunch_matches_only_the_same_state():
    m = retry.manifest(state(), SHA)
    assert retry.mismatches(m, state()) == []
    moved = state([unit(1, 5, 6), unit(2, 6, 5), unit(3, 9, 9, FOE, ready=False)])
    assert retry.mismatches(m, moved) == ['1 tile [5, 5] -> [5, 6]']
    hurt = state([unit(1, 5, 5), unit(2, 6, 5, hp=10), unit(3, 9, 9, FOE, ready=False)])
    assert retry.mismatches(m, hurt) == ['2 hp 5000 -> 10']
    assert retry.mismatches(m, state(turn=8)) == ['turn 7 -> 8']
    assert retry.mismatches(m, state(state()['units'][:2])) == ['3 missing']
    assert retry.mismatches(m, {'units': []}) == ['state unreadable']


# ---- ledger ----------------------------------------------------------------------------------

def ledger(**kw):
    return retry.Ledger(retry.manifest(state(), SHA), **kw)


def test_the_first_attempt_protects_nobody_and_a_clean_turn_is_done():
    book = ledger()
    assert book.start().protected == ()
    assert book.finish({'phase': 'done', 'turn': [7, 8]}) == 'done'
    assert book.attempts[0].outcome == 'done' and book.done


def test_a_lost_ally_is_protected_on_the_next_attempt():
    book = ledger()
    book.start()
    assert book.finish({'phase': 'stopped', 'reason': 'ally_destroyed'}, lost=[2]) == 'retry'
    second = book.start()
    assert second.number == 2 and second.protected == (2,)
    assert book.finish({'phase': 'stopped', 'reason': 'unit_lost'}, lost=[1]) == 'retry'
    assert book.start().protected == (1, 2)


def test_at_most_three_retries():
    book = ledger()
    for n in range(1, 4):
        book.start()
        assert book.finish({'phase': 'stopped', 'reason': 'unit_lost'}, lost=[n]) == 'retry'
    book.start()
    assert book.finish({'phase': 'stopped', 'reason': 'unit_lost'}, lost=[9]) == 'give_up'
    assert len(book.attempts) == 4 and book.gave_up == 'retries_used'
    with pytest.raises(ValueError):
        book.start()


def test_a_loss_with_nothing_new_to_protect_gives_up():
    # The game replays deterministically (m11cp4): the same choices lose the same way.
    book = ledger()
    book.start()
    book.finish({'phase': 'stopped', 'reason': 'unit_lost'}, lost=[2])
    book.start()
    assert book.finish({'phase': 'stopped', 'reason': 'unit_lost'}, lost=[2]) == 'give_up'
    assert book.gave_up == 'nothing_new_to_protect'
    book2 = ledger()
    book2.start()
    assert book2.finish({'phase': 'stopped', 'reason': 'ally_destroyed'}, lost=[]) == 'give_up'


@pytest.mark.parametrize('reason', ['scene_at_new_turn', 'turn_jump', 'stage_restart',
                                    'phase_budget', 'player_phase_unclear', 'io_error: x'])
def test_other_stops_give_up(reason):
    book = ledger()
    book.start()
    assert book.finish({'phase': 'stopped', 'reason': reason}, lost=[2]) == 'give_up'
    assert book.gave_up == reason


def test_a_forced_retry_is_recorded_and_protects_nobody_new():
    book = ledger()
    book.start()
    assert book.finish({'phase': 'done', 'turn': [7, 8]}, forced=True) == 'retry'
    assert book.attempts[0].outcome == 'forced_retry'
    assert book.start().protected == ()


def test_finish_needs_a_started_attempt():
    book = ledger()
    with pytest.raises(ValueError):
        book.finish({'phase': 'done'})


def test_report_and_its_write_errors(tmp_path):
    book = ledger()
    book.start()
    book.finish({'phase': 'stopped', 'reason': 'unit_lost'}, lost=[2])
    data = retry.report(book)
    assert data['checkpoint']['sha256'] == SHA and data['max_retries'] == 3
    assert data['attempts'][0] == {'number': 1, 'protected': [], 'outcome': 'lost',
                                   'reason': 'unit_lost', 'lost': [2]}
    assert retry.write_report(book, tmp_path / 'retry-report.json') is None
    assert json.loads((tmp_path / 'retry-report.json').read_text(encoding='utf-8')) == data
    assert retry.write_report(book, tmp_path / 'missing' / 'x' / 'r.json') is not None


# ---- losses outside the enemy phase (review 25 Oct) -----------------------------------------

def test_lost_allies_compares_the_checkpoint_with_the_end_state():
    m = retry.manifest(state(), SHA)
    after = state([unit(1, 5, 5, ready=False), unit(3, 9, 9, FOE, ready=False)], turn=8)
    assert retry.lost_allies(m, after) == [2]                  # vanished (destroyed by a counter)
    down = state([unit(1, 5, 5), unit(2, 6, 5, hp=0), unit(3, 9, 9, FOE, hp=0)], turn=8)
    assert retry.lost_allies(m, down) == [2]                   # foes never count
    assert retry.lost_allies(m, state(turn=8)) == []
    with pytest.raises(ValueError):
        retry.lost_allies(m, {'units': []})


def test_a_done_phase_with_a_lost_ally_is_still_a_defeat():
    book = ledger()
    book.start()
    assert book.finish({'phase': 'done', 'turn': [7, 8]}, lost=[2]) == 'retry'
    assert book.attempts[0].outcome == 'lost' and not book.done
    assert book.start().protected == (2,)
