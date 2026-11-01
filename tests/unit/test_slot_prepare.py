import pytest

from psp_buddy import retry, slot_prepare

ALLY, NPC, FOE = 0, 1, 13
SHA = 'b' * 64


def unit(obj, group=ALLY, hp=5000, mech=197, pilot=208, ready=True, x=5, y=5):
    return {'object': obj, 'raw_menu_group_byte': group, 'hp': hp, 'en': 100, 'sp': 50,
            'mech_id': mech, 'pilot_id': pilot, 'tile_x': x, 'tile_y': y,
            'counted_as_unmoved': ready}


def state(units, turn=5):
    return {'turn': {'turn': turn}, 'units': units}


# ---- choose_anchor ---------------------------------------------------------------------------

def test_anchor_is_the_lowest_object_living_player_ally():
    units = [unit(30, mech=1, pilot=1), unit(10, mech=2, pilot=2), unit(20, mech=3, pilot=3)]
    assert slot_prepare.choose_anchor(units)['object'] == 10


def test_anchor_skips_dead_npc_and_foe_units():
    units = [unit(1, hp=0, mech=1, pilot=1), unit(2, group=NPC, mech=2, pilot=2),
             unit(3, group=FOE, mech=3, pilot=3), unit(4, mech=4, pilot=4)]
    assert slot_prepare.choose_anchor(units)['object'] == 4


def test_anchor_skips_duplicate_identities():
    units = [unit(1, mech=7, pilot=8), unit(1, mech=7, pilot=8), unit(2, mech=9, pilot=9)]
    assert slot_prepare.choose_anchor(units)['object'] == 2


def test_anchor_skips_units_with_unreadable_identity():
    bad = unit(1)
    del bad['pilot_id']
    assert slot_prepare.choose_anchor([bad, unit(2, mech=5, pilot=6)])['object'] == 2


def test_no_usable_ally_refuses():
    with pytest.raises(slot_prepare.PrepareRefused) as err:
        slot_prepare.choose_anchor([unit(1, hp=0), unit(2, group=FOE)])
    assert err.value.reason == 'no_anchor_ally'


# ---- retry.snapshot (mid-turn saves) ---------------------------------------------------------

def test_snapshot_accepts_a_mid_turn_state():
    s = state([unit(1, mech=1, pilot=1), unit(2, mech=2, pilot=2, ready=False)])
    snap = retry.snapshot(s, SHA)
    assert snap['turn'] == 5 and [u['unmoved'] for u in snap['units']] == [True, False]
    assert retry.mismatches(snap, s) == []


def test_snapshot_still_checks_hash_and_units():
    with pytest.raises(ValueError):
        retry.snapshot(state([unit(1)]), 'nothex')
    with pytest.raises(ValueError):
        retry.snapshot(state([]), SHA)


# ---- manifest --------------------------------------------------------------------------------

def test_manifest_has_todays_keys_plus_opening():
    s = state([unit(40, mech=197, pilot=208), unit(50, group=FOE, mech=0, pilot=0)])
    m = slot_prepare.manifest(s, file='ULJS00460_1.01_2.ppst', sha256=SHA, source='C:/x.ppst',
                              at='2026-10-24T11:16', opening={'screen': 'target_select'})
    assert m['file'] == 'ULJS00460_1.01_2.ppst' and m['sha256'] == SHA
    assert m['source'] == 'C:/x.ppst'
    assert m['fixture'] == {'object': 40, 'mech_id': 197, 'pilot_id': 208, 'hp': 5000, 'en': 100,
                            'sp': 50}
    assert m['retry'] == retry.snapshot(s, SHA)
    assert m['opening'] == {'screen': 'target_select'}
    assert m['prepared_by'] == 'm15 prepare'
    assert 'object 40' in m['fixture_source']
