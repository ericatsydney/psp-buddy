import asyncio

import pytest

from psp_buddy.weapons import (
    AMMO_UNIT,
    decode_name,
    decode_weapon_record,
    read_unit_weapons,
)

# Bytes copied from the protected live dumps of 20 Oct 2026 (wpn1/wpn2 runs).
DESTINY = {
    0x091C02D0: '94c0cd08bc85e60878aae608f82fe608',                     # actor
    0x08E685BC: 'b8d9c6081034e9082445e708',                             # roster entry
    0x08C6D9B8: 'c50000004c4afa08',                                     # mech def (id, name*)
    0x08FA4A4C: '82638285829382948289828e8299814082668295828e82848281828d00',
    0x08E93410: ('9411000000000000000100000100010001010201030791009100e80312030000'
                 '0000c500000000005014000050140000e600e600000000000926000001000000'
                 '0050500020050000e040000040000000'),
    0x08E74524: ('5097c9087c97c908a897c908d497c9080098c908' + '00' * 64
                 + '6a89ec086c89ec086e89ec087089ec087289ec087489ec087689ec087889ec08'
                 + '7a89ec087c89ec087e89ec088089ec088289ec088489ec088689ec088889ec08'
                 + '8a89ec088c89ec088e89ec089089ec089289ec08'),
    0x08E6AA78: 'dc9dc7086089ea08',                                     # pilot descriptor
    0x08EA89EE: '24010c05090116010201000000000000',                     # pilot skills (+0x8E)
    0x08C99750: ('f83bfa08103cfa0840006c070102190000000a00000101010201000000000000'
                 '090000000000000001000000'),
    0x08FA3BF8: '8250825681448254828d828d826282688276827200',
    0x08C9977C: ('085aa208085aa2084100540b02060f0005000800000101010301000000000000'
                 '020000000000000002000000'),
    0x08A25A08: '826782898264828e8285829282878299826182858281828d82668295828e00',
    0x08C997A8: ('155ba208155ba20802001c0c01040f000a000005000101010201000000000000'
                 '030400000000000003000000'),
    0x08A25B15: '82718270826c8255824f82658265828c82818293828882648284828782858251' + '00',
    0x08C997D4: ('085aa208085aa2084300041003070a0000000023000101010301000000000000'
                 '020000000000000004000000'),
    0x08C99800: ('365ba208365ba20804006810010214000f0000236e0101010201000000000000'
                 '03000000000000008374838b'),
    0x08A25B36: '82608292828f828e8284828982878288829482728297828f8292828400',
    # Parts table records 8 (Hi-SpecRadar, range +1), 37 (Propellant T), 29 (D-Extractor) + names.
    0x08C5A954: ('6289c508000000000000000000000001000000000000000000000000000000007b89c508'
                 '7b89c5087b89c508'),
    0x08C58962: '82678289814582728290828582838271828182848281829200',
    0x08C5AE50: ('2993c508020000000000000000000000000000000000000001000000000000004293c508'
                 '4293c5084293c508'),
    0x08C59329: '826f8292828f82908285828c828c8281828e829481458273' + '00',
    0x08C5ACF0: ('e88fc50800000000000096000000000000000000000000000000c80082000000d0dafa08'
                 '20dbfa0870dbfa08'),
    0x08C58FE8: '826381458264829882948292828182838294828f829200',
    0x08EC896A: ('5a00480000000000000000000000000000000000000000000000000000000000'
                 '00000000000000000000'),
}

Z_GUNDAM_LIST = {
    0x091C02B0: '94c0cd083882e60828a8e6086832e608',
    0x08E68238: 'a0c4c608a01ce908c012e708',
    0x08C6C4A0: '7a0000001848fa08',
    0x08FA4818: '8279814082668295828e82848281828d00',
    0x08E91CA0: ('9411000000000000000100000100010003010200020691007300e8030b000000'
                 '00007a00000000005c1200005c120000aa008000000000000000000001000000'
                 '0200000000000000c000800000000000'),
    0x08E712C0: ('f859c908245ac90800000000505ac9087c5ac908a85ac908d45ac908005bc908' + '00' * 52
                 + '1c7dec081e7dec08207dec08227dec08247dec08267dec08287dec082a7dec08'
                 + '2c7dec082e7dec08307dec08327dec08347dec08367dec08387dec083a7dec08'
                 + '3c7dec083e7dec08407dec08427dec08447dec08'),
    0x08E6A828: 'f692c708a857ea08',
    0x08EA5836: '22040d050b0100000000000000000000',
    0x08C959F8: ('3751a2083751a2084000d00701021e000a000a00000101010101000000000000'
                 '090000000000000001000000'),
    0x08A25137: '82758295828c82838281828e82628281828e828e828f828e00',
    0x08C95A24: ('ba50a208ba50a20841008c0a01050a00fbff0600000101010201000000000000'
                 '000400000000000003000000'),
    0x08A250BA: '826682928285828e828182848285826b82818295828e8283828882858292' + '00',
    0x08C95A50: ('5051a2085051a2084300f00a02040f0005000a00000101010301000000000000'
                 '030000000000000004000000'),
    0x08A25150: '826182858281828d827182898286828c828500',
    0x08C95A7C: ('6351a2086351a2080400540b010214000a000005000101010101000000000000'
                 '030400000000000005000000'),
    0x08A25163: '826182858281828d8272828182828285829200',
    0x08C95AA8: ('7651a2087651a2080500ac0d01030a00140000146e0101010201000000000000'
                 '030000000000000006000000'),
    0x08A25176: '826182858281828d8262828f828e828682958293828500',
    0x08C95AD4: ('8d51a2088d51a20846006810020705000a000028000101010301000000000000'
                 '020000000000000007000000'),
    0x08A2518D: '8267829982908144826c828582878281826b82818295828e828382888285829200',
    0x08C95B00: ('ae51a208ae51a20807009411020314000a000032820101010100000000000000'
                 '030b0401020000008372815b'),
    0x08A251AE: '82678299829082858292826182858281828d8272828182828285829200',
    0x08EC7D1C: ('5a00360000005100000000000000000000000000000000000000000000000000'
                 '000000000000000000'),
}


class Memory:
    """Sparse RAM: mapped bytes plus up to 64 zero bytes of slack after each segment (for names)."""

    def __init__(self, segments, overrides=None):
        self.bytes = {}
        for start, text in segments.items():
            for offset, value in enumerate(bytes.fromhex(text)):
                self.bytes[start + offset] = value
        for start, text in segments.items():
            end = start + len(bytes.fromhex(text))
            for address in range(end, end + 64):
                self.bytes.setdefault(address, 0)
        for address, data in (overrides or {}).items():
            for offset, value in enumerate(data):
                assert address + offset in self.bytes
                self.bytes[address + offset] = value
        self.reads = []

    async def read(self, address, size):
        self.reads.append((address, size))
        try:
            return bytes(self.bytes[a] for a in range(address, address + size))
        except KeyError:
            raise AssertionError(f'unmapped read {address:#x}+{size}') from None


def probe(segments, actor, overrides=None):
    memory = Memory(segments, overrides)
    return asyncio.run(read_unit_weapons(memory.read, actor)), memory


def test_destiny_weapons_decode_in_menu_order_with_effective_power():
    unit, _ = probe(DESTINY, 0x091C02D0)
    assert unit['mech_id'] == 197 and unit['mech_name'] == 'Destiny Gundam'
    assert (unit['hp'], unit['max_hp'], unit['en'], unit['max_en']) == (5200, 5200, 230, 230)
    assert unit['upgrade_level_candidate'] == 3
    assert unit['pilot_skills'] == [{'id': 36, 'level': 1}, {'id': 12, 'level': 5},
                                    {'id': 9, 'level': 1}, {'id': 22, 'level': 1},
                                    {'id': 2, 'level': 1}]
    names = [w['name'] for w in unit['weapons']]
    assert names == ['17.5mmCIWS', 'HiEnergyBeamGun', 'RQM60FFlashEdge2', 'HiEnergyBeamGun',
                     'ArondightSword']
    # The 20 Oct screen: 2200 3200 3400 4400 4500.
    assert [w['power'] for w in unit['weapons']] == [2200, 3200, 3400, 4400, 4500]
    ciws, gun, edge, big, sword = unit['weapons']
    assert (ciws['base_power'], ciws['min_range'], ciws['max_range_base']) == (1900, 1, 2)
    assert unit['parts'] == [{'id': 9, 'name': 'Hi・SpecRadar', 'range_bonus': 1, 'weapon_power': 0,
                              'will_required': 0},
                             {'id': 38, 'name': 'Propellant・T', 'range_bonus': 0,
                              'weapon_power': 0, 'will_required': 0}]
    # The 20 Oct screen: 1~3 2~7 1~5 3~8 1~3 (base max range + Hi-SpecRadar).
    assert [w['max_range'] for w in unit['weapons']] == [3, 7, 5, 8, 3]
    assert ciws['range_bonus_resolved'] is True
    assert (ciws['ammo'], ciws['max_ammo'], ciws['ammo_raw']) == (10, 10, 90)
    assert (ciws['hit'], ciws['crit']) == (25, 0)
    assert ciws['flags'] == {'p': True, 'beam': False, 's': True, 'shooting': True,
                             'map': False, 'condition': False}
    assert gun['ammo'] == 8 and gun['flags']['p'] is False and gun['flags']['beam'] is True
    assert edge['ammo'] is None and edge['en_cost'] == 5 and edge['flags']['p'] is True
    assert big['en_cost'] == 35 and big['terrain'] == 'AACA' and big['max_range_base'] == 7
    assert sword['will'] == 110 and sword['flags']['shooting'] is False
    assert [w['slot'] for w in unit['weapons']] == [0, 1, 2, 3, 4]


def test_z_gundam_list_skips_the_empty_slot_and_reads_current_ammo():
    unit, _ = probe(Z_GUNDAM_LIST, 0x091C02B0)
    assert unit['mech_name'] == 'Z Gundam' and unit['upgrade_level_candidate'] == 0
    assert [w['slot'] for w in unit['weapons']] == [0, 1, 3, 4, 5, 6, 7]
    rifle = unit['weapons'][2]
    assert rifle['name'] == 'BeamRifle'
    assert (rifle['power'], rifle['min_range'], rifle['max_range']) == (2800, 2, 4)
    assert unit['parts'] == []
    assert (rifle['ammo'], rifle['max_ammo']) == (9, 10)
    grenade = unit['weapons'][1]
    assert grenade['crit'] == -5 and grenade['flags']['p'] is False
    assert unit['pilot_skills'][0] == {'id': 34, 'level': 4}


def test_decode_name_is_full_width_shift_jis():
    assert decode_name(bytes.fromhex('8279814082668295828e82848281828d00ff')) == 'Z Gundam'
    for bad in (b'\x00abc', b'\x82', b'x' * 80, b'\x07\x00'):
        with pytest.raises(ValueError):
            decode_name(bad)


# Strike Freedom records from RAM dump m9livex05 ram-01 (22 Oct): SuperDragoon is shown as a MAP
# weapon (bytes 27-31 hold its area); Combo-Assault is one of the three weapons the menu hides.
SUPER_DRAGOON = bytes.fromhex(
    'ef59a208ef59a2084200ac0d01051e00140002008c0402020301000200020'
    '10d0202000000000000030000 00'.replace(' ', ''))


def test_map_and_hidden_condition_flags_come_from_the_record_tail():
    flags = decode_weapon_record(SUPER_DRAGOON, 2)['flags']
    assert flags['map'] is True and flags['condition'] is False
    combo = bytearray(SUPER_DRAGOON)
    combo[8] = 0x46                                 # slot 6
    combo[26:32] = bytes([1, 0, 0, 0, 0, 0])
    flags = decode_weapon_record(bytes(combo), 6)['flags']
    assert flags['map'] is False and flags['condition'] is True


def test_decode_weapon_record_rejects_bad_sizes_and_ranges():
    record = bytearray(bytes.fromhex(DESTINY[0x08C99750]))
    assert decode_weapon_record(bytes(record), 0)['base_power'] == 1900
    with pytest.raises(ValueError):
        decode_weapon_record(bytes(record[:40]), 0)
    with pytest.raises(ValueError, match='slot'):
        decode_weapon_record(bytes(record), 1)
    for offset, value in ((12, 0), (12, 3), (13, 100)):
        broken = bytearray(record)
        broken[offset] = value
        with pytest.raises(ValueError):
            decode_weapon_record(bytes(broken), 0)


@pytest.mark.parametrize('address,data', [
    (0x091C02D4, b'\x00\x00\x00\x00'),                 # roster pointer null
    (0x091C02D4, b'\x00\x00\x00\x0b'),                 # roster pointer outside user RAM
    (0x08E685C4, b'\x26\x45\xe7\x08'),                 # weapon list misaligned
    (0x08E74524, b'\x52\x97\xc9\x08'),                 # weapon record misaligned
])
def test_bad_pointers_are_refused(address, data):
    with pytest.raises(ValueError):
        probe(DESTINY, 0x091C02D0, {address: data})


def test_weapon_in_wrong_slot_is_refused():
    # Put Destiny's slot-1 record into slot 0.
    with pytest.raises(ValueError, match='slot'):
        probe(DESTINY, 0x091C02D0, {0x08E74524: bytes.fromhex('7c97c908')})


def test_actor_must_be_aligned_user_ram():
    for actor in (0x091C02D1, 0x07000000, 0x0A000000):
        with pytest.raises(ValueError):
            probe(DESTINY, actor)


def test_ammo_unit_is_nine_shots_per_counter_step():
    assert AMMO_UNIT == 9


def test_ammo_above_the_base_maximum_is_reported_not_refused():
    # An ammo-capacity part can raise the maximum: 15 shots on a base-10 weapon.
    unit, _ = probe(DESTINY, 0x091C02D0, {0x08EC896A: bytes.fromhex('8700')})
    assert unit['weapons'][0]['ammo'] == 15 and unit['weapons'][0]['max_ammo'] == 10


def test_unreadable_pilot_leaves_skills_empty_but_weapons_readable():
    unit, _ = probe(DESTINY, 0x091C02D0, {0x08E6AA7C: bytes(4)})     # pilot runtime null
    assert unit['pilot_skills'] is None and len(unit['weapons']) == 5


def test_implausible_upgrade_candidate_is_reported_but_not_applied():
    unit, _ = probe(DESTINY, 0x091C02D0, {0x08E9342D: bytes([0x40])})
    assert unit['upgrade_level_candidate'] == 64
    assert [w['power'] for w in unit['weapons']] == [1900, 2900, 3100, 4100, 4200]
    assert all(w['power_resolved'] is False for w in unit['weapons'])


def test_conditional_part_power_is_not_applied_but_reported():
    # Slot 2 holds D-Extractor (id 30): WeaponPower+200 only at will 130+.
    unit, _ = probe(DESTINY, 0x091C02D0, {0x08E9344A: bytes([30])})
    assert unit['parts'][2]['name'] == 'D・Extractor' and unit['parts'][2]['will_required'] == 130
    assert [w['power'] for w in unit['weapons']] == [2200, 3200, 3400, 4400, 4500]
    assert unit['conditional_power_bonus'] == 200


def test_unknown_part_id_is_refused():
    with pytest.raises(ValueError, match='part'):
        probe(DESTINY, 0x091C02D0, {0x08E93449: bytes([0xF0])})


def test_high_newtype_level_marks_range_unresolved():
    # Pilot skill 34 (Newtype-like) at level 7+ can add range for some weapons: not modelled.
    unit, _ = probe(DESTINY, 0x091C02D0, {0x08EA89EE: bytes([34, 8])})
    assert all(w['range_bonus_resolved'] is False for w in unit['weapons'])
