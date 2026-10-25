import asyncio
import struct

import pytest

from psp_buddy import spirits


def pilot_blob(level=36, sp=55, max_sp=95, triples=((6, 1, 15), (9, 7, 20), (18, 31, 35),
                                                   (1, 47, 35), (2, 58, 50), (11, 64, 55))):
    """Setsuna's pilot runtime on 23 Oct (m9livesp1 dump 2), only the decoded fields set."""
    blob = bytearray(spirits.PILOT_BLOB_SIZE)
    struct.pack_into('<H', blob, spirits.MAX_SP_OFFSET, max_sp)
    struct.pack_into('<H', blob, spirits.SP_OFFSET, sp)
    blob[spirits.LEVEL_OFFSET] = level
    triples = tuple(triples) + ((0, 255, 255),) * (6 - len(triples))
    for i, triple in enumerate(triples):
        blob[spirits.SPIRITS_OFFSET + 3 * i:spirits.SPIRITS_OFFSET + 3 * i + 3] = bytes(triple)
    return bytes(blob)


def test_decode_matches_setsunas_spirit_screen():
    info = spirits.decode_pilot(pilot_blob())
    assert (info['level'], info['sp'], info['max_sp']) == (36, 55, 95)
    learned = [s for s in info['spirits'] if s['learned']]
    assert [(s['name'], s['cost'], s['row']) for s in learned] == [
        ('Focus', 15, 0), ('Sense', 20, 1), (None, 35, 2)]
    assert [s['row'] for s in info['spirits'] if not s['learned']] == [None, None, None]


def test_empty_slots_are_skipped():
    info = spirits.decode_pilot(pilot_blob(triples=((25, 1, 1), (34, 1, 20))))
    assert [s['id'] for s in info['spirits']] == [25, 34]


@pytest.mark.parametrize('blob', [
    pilot_blob(sp=96, max_sp=95),
    pilot_blob(level=0),
    pilot_blob(triples=((9, 20, 20), (6, 1, 15)) + ((0, 255, 255),) * 4),   # levels must not fall
    pilot_blob(triples=((6, 1, 0),) + ((0, 255, 255),) * 5),                 # zero cost
    pilot_blob()[:-1],
])
def test_implausible_records_are_refused(blob):
    with pytest.raises(ValueError):
        spirits.decode_pilot(blob)


def choose(**kw):
    active = kw.pop('active', ())
    return spirits.choose_spirit(spirits.decode_pilot(pilot_blob(**kw)), active=active)


def test_sense_first():
    assert choose() == {'spirit': 'Sense', 'id': 9, 'cost': 20, 'row': 1}


def test_focus_when_sense_is_unaffordable():
    assert choose(sp=19) == {'spirit': 'Focus', 'id': 6, 'cost': 15, 'row': 0}


def test_focus_when_sense_is_not_learned():
    assert choose(triples=((6, 1, 15), (9, 40, 20))) == {
        'spirit': 'Focus', 'id': 6, 'cost': 15, 'row': 0}


def test_none_when_sp_is_short_or_nothing_learned():
    assert choose(sp=14) is None
    assert choose(triples=((7, 1, 10), (18, 15, 20))) is None


def test_an_active_spirit_is_not_cast_again():
    assert choose(active={'Sense'})['spirit'] == 'Focus'
    assert choose(active={'Sense', 'Focus'}) is None


def test_read_follows_actor_to_pilot_runtime():
    blob = pilot_blob()
    memory = {0x09000008: struct.pack('<I', 0x08E6AB88), 0x08E6AB8C: struct.pack('<I', 0x08EAA038),
              0x08EAA038: blob}

    async def read(address, size):
        return memory[address][:size]

    info = asyncio.run(spirits.read_pilot_spirits(read, 0x09000000))
    assert info['sp'] == 55 and info['spirits'][1]['name'] == 'Sense'


def with_effects(blob, mask):
    blob = bytearray(blob)
    struct.pack_into('<H', blob, spirits.EFFECTS_OFFSET, mask)
    return bytes(blob)


def test_active_effects_come_from_the_effect_mask():
    # 24 Oct live cast (m9livesp3): Sense set the mask 0 -> 0x44 (Flash bit 2, Aim bit 6)
    assert spirits.decode_pilot(pilot_blob())['active'] == []
    sensed = spirits.decode_pilot(with_effects(pilot_blob(sp=35), 0x44))
    # Sense's Flash bit is Alert's bit too (M12 hypothesis), so Alert reads active as well
    assert sensed['active'] == ['Alert', 'Sense'] and sensed['effects'] == 0x44
    assert spirits.choose_spirit(sensed) == {'spirit': 'Focus', 'id': 6, 'cost': 15, 'row': 0}
    focused = spirits.decode_pilot(with_effects(pilot_blob(), 0x64))
    assert focused['active'] == ['Alert', 'Focus', 'Sense']
    assert spirits.choose_spirit(focused) is None
    # one of the two Sense effects left (e.g. Aim used up) does not count as Sense active
    assert spirits.decode_pilot(with_effects(pilot_blob(), 0x04))['active'] == ['Alert']


# ---- M12: Sense > Focus > Alert > Invincible, one per attack (user, 25 Oct) -------------------
# Ids 3 (Alert) and 5 (Invincible) are an offline hypothesis (spirit-recon note, 25 Oct).

def test_alert_when_the_pilot_has_neither_sense_nor_focus():
    # 149304848-like list without Sense/Focus: Alert (id 3) first
    assert choose(triples=((3, 1, 10), (7, 15, 20), (5, 20, 25))) == {
        'spirit': 'Alert', 'id': 3, 'cost': 10, 'row': 0}


def test_invincible_when_it_is_the_only_one_learned():
    assert choose(triples=((5, 1, 15), (7, 27, 20))) == {
        'spirit': 'Invincible', 'id': 5, 'cost': 15, 'row': 0}


def test_alert_after_focus_and_sense_are_used_or_unaffordable():
    triples = ((6, 1, 15), (9, 7, 20), (3, 10, 10), (5, 20, 25))
    assert choose(triples=triples, active={'Sense', 'Focus'})['spirit'] == 'Alert'
    assert choose(triples=triples, sp=12)['spirit'] == 'Alert'
    used = {'Sense', 'Focus', 'Alert'}
    assert choose(triples=triples, sp=30, active=used)['spirit'] == 'Invincible'


def test_sense_still_comes_first_when_all_four_are_learned():
    triples = ((3, 1, 10), (5, 1, 15), (6, 1, 15), (9, 1, 20))
    assert choose(triples=triples) == {'spirit': 'Sense', 'id': 9, 'cost': 20, 'row': 3}


def test_invincible_reads_active_from_its_own_bit():
    assert spirits.decode_pilot(with_effects(pilot_blob(), 0x10))['active'] == ['Invincible']
