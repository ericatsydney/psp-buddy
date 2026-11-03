import asyncio

from test_plan_act import Game

from psp_buddy import plan_act, spirits
from psp_buddy.policy import parse_policy
from psp_buddy.turn import TurnLog

SPIRIT_POLICY = parse_policy('use sense then focus before attacking')
SETSUNA = [(6, 'Focus', 15), (9, 'Sense', 20), (18, None, 35)]      # 23 Oct spirit screen


class Spirited(Game):
    """SimGame plus the Spirit command as seen live on 23/24 Oct: Command menu Move / Attack /
    Spirit / Info, the list opens on row 0, one Circle casts (no Yes/No) and the game returns to
    the map with the unit unmoved, SP down by the cost and the effect bits set."""

    def __init__(self, sp=55, **flags):
        super().__init__(**flags)
        self.sp, self.effects, self.spirit_cursor = sp, 0, 0
        self.list_rows = list(SETSUNA)

    async def press(self, button, frames=2):
        if self.screen == 'unit_menu' and button == 'circle' and (
                self.entries[self.entry] == 'Spirit'):
            self.log.append(button)
            if self.flags.get('two_pilots'):          # a pilot screen comes first
                self.screen, self.pilot = 'pilot_select', 0
                return
            self.screen, self.spirit_cursor = 'spirit_list', self.flags.get('opens_on', 0)
            return
        if self.screen == 'pilot_select':
            self.log.append(button)
            if button in ('up', 'down'):
                self.pilot = 1 if button == 'down' else 0
            elif button == 'cross':
                self.screen = 'unit_menu'
            elif button == 'circle':
                self.screen, self.spirit_cursor = 'spirit_list', 0
                self.list_owner = self.pilot
            return
        if self.screen == 'unit_menu' and button == 'cross' and self.flags.get('menu_stuck'):
            self.log.append(button)
            return
        if self.screen == 'spirit_list':
            self.log.append(button)
            if button in ('up', 'down'):
                step = 1 if button == 'down' else -1
                self.spirit_cursor = max(0, min(len(self.list_rows) - 1,
                                                self.spirit_cursor + step))
            elif button == 'cross':
                self.screen = 'pilot_select' if self.flags.get('two_pilots') else 'unit_menu'
            elif button == 'circle' and getattr(self, 'list_owner', 0):
                pass                                     # the second pilot's SP is not read
            elif button == 'circle' and not self.flags.get('cast_ignored'):
                _, name, cost = self.list_rows[self.spirit_cursor]
                self.sp -= self.flags.get('charged', cost)
                if not self.flags.get('mask_stuck'):
                    self.effects |= spirits.EFFECT_BITS.get(name, 0)
                self.screen = 'map'
            return
        if self.screen == 'unit_menu' and button in ('up', 'down') and (
                self.flags.get('menu_row_stuck')):
            self.log.append(button)
            return
        was = self.screen
        await super().press(button, frames)
        if (was == 'map' and self.screen == 'unit_menu' and self.acting
                and not self.acting.get('moved')):
            self.entries = (['Move', 'Attack', 'Morph', 'Spirit', 'Info'] if self.flags.get('morph')
                            else ['Move', 'Attack', 'Spirit', 'Info'])
        if self.screen == 'unit_menu' and self.entries[self.entry] == 'Morph' and (
                button == 'circle'):
            raise AssertionError('Morph chosen: the unit would transform')

    async def read_weapons(self, unit_object):
        answer = await super().read_weapons(unit_object)
        return {**answer, 'mech_name': self.flags.get('mech', 'Gundam 00')}

    async def command_menu(self):
        if self.flags.get('menu_unreadable', 0) > 0:     # an implausible read (None)
            self.flags['menu_unreadable'] -= 1
            return None
        if self.screen == 'unit_menu':
            return self.entry, len(self.entries)
        return 0, 4                                 # stale after the menu closed (24 Oct dump)

    async def spirits(self, unit_object):
        self.log.append(f'spirits({unit_object})')
        rows = [{'id': i, 'name': n, 'learn_level': 1, 'cost': c, 'learned': True, 'row': r}
                for r, (i, n, c) in enumerate(self.list_rows)]
        active = sorted(n for n, b in spirits.EFFECT_BITS.items() if self.effects & b == b)
        return {'level': 36, 'sp': self.sp, 'max_sp': 95, 'spirits': rows,
                'effects': self.effects, 'active': active}

    async def state(self):
        answer = await super().state()
        if self.flags.get('screens'):          # the helper's UI-pool screen name (M15)
            answer['screen'] = {'map': 'no_menu', 'unit_menu': 'unit_commands',
                                'spirit_list': 'spirit_list'}.get(self.screen, 'unknown')
            # M16 recon (3 Nov, 00 Raiser): pilot select is window 0x08E4D090, the list 0x08E4D208.
            pilots = [0x08E4D090] if self.flags.get('two_pilots') else []
            answer['ui_windows'] = [0x08E4BD0C] + {
                'unit_menu': [0x08E4BDDC], 'pilot_select': [0x08E4BDDC, *pilots],
                'spirit_list': [0x08E4BDDC, *pilots, 0x08E4D208]}.get(self.screen, [])
        return answer

    async def goto(self, tile):
        if self.screen in ('unit_menu', 'pilot_select', 'spirit_list'):     # cursor locked
            self.log.append(f'goto{tuple(tile)}')
            return {'reached': False, 'cursor': {'x': self.cursor[0], 'y': self.cursor[1]}}
        return await super().goto(tile)

    async def spirit_cursor_bytes(self):
        if self.screen == 'spirit_list':
            return [self.spirit_cursor, self.spirit_cursor]
        return [1, 0]                            # the map in the 24 Oct dump

    async def hit(self):
        answer = await super().hit()
        if answer.get('state') == 'hit' and self.effects & 0x40:     # Aim: a sure hit
            return {'state': 'hit', 'hit': 100}
        return answer


def run(coro):
    return asyncio.run(coro)


CAST_SENSE = ['goto(5, 5)', 'circle', 'down', 'down', 'circle', 'down', 'circle']
ON_MAP = ['goto(4, 5)', 'goto(5, 5)']        # the cursor moves: no menu is open


def test_sense_is_cast_before_the_attack_and_verified_from_memory():
    sim = Spirited()
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['ok'] and result['phase'] == 'fired'
    spirit = result['spirit']
    assert spirit['status'] == 'cast' and spirit['spirit'] == 'Sense' and spirit['cost'] == 20
    assert spirit['sp'] == [55, 35] and spirit['effect_confirmed'] is True
    presses = [e for e in sim.log if not e.startswith('spirits')]
    assert presses[:len(CAST_SENSE)] == CAST_SENSE
    after = presses[len(CAST_SENSE):len(CAST_SENSE) + 4]
    assert after == ON_MAP + ['goto(5, 5)', 'circle']               # map proven, then reselect
    assert spirit['on_map'] is True
    assert sim.sp == 35 and sim.log.count('start') == 1
    assert spirit['list_bytes'] == [[0, 0], [1, 1]]      # diagnostics: open, then on the row


def test_the_sure_hit_after_sense_does_not_count_as_a_forecast_mismatch():
    sim = Spirited()
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000, hits={2000: 42}))
    assert result['ok'] and result['phase'] == 'fired' and result['forecast']['hit'] == 100


def test_focus_is_cast_when_sense_is_not_affordable():
    sim = Spirited(sp=18)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['spirit']['spirit'] == 'Focus' and result['spirit']['sp'] == [18, 3]
    presses = [e for e in sim.log if not e.startswith('spirits')]
    assert presses[:6] == ['goto(5, 5)', 'circle', 'down', 'down', 'circle', 'circle']
    assert result['ok'] and result['phase'] == 'fired'


def test_no_affordable_spirit_attacks_without_pressing_spirit_keys():
    sim = Spirited(sp=10)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['spirit']['status'] == 'none'
    assert result['ok'] and sim.sp == 10
    presses = [e for e in sim.log if not e.startswith('spirits')]
    assert presses[:4] == ['goto(5, 5)', 'circle', 'down', 'circle']     # straight to Attack


def test_without_the_policy_clause_nothing_is_cast_or_read():
    sim = Spirited()
    result = run(plan_act.plan_and_act(sim, plan_act.Policy(), 1000))
    assert 'spirit' not in result and sim.sp == 55
    assert not any(e.startswith('spirits') for e in sim.log)


def test_a_unit_without_an_attack_plan_casts_nothing():
    sim = Spirited()
    for foe in sim.units[2:]:
        foe['tile_y'] = 30                       # out of reach even after a move
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['phase'] == 'handover' and sim.sp == 55
    assert 'spirit_list' not in str(sim.log) and sim.log.count('down') == 0


def test_a_list_opening_on_another_row_casts_the_wrong_spirit_and_stops():
    # m11live1 (24 Oct): the two cursor-row candidates did not track the list on a fresh
    # launch, so they are recorded only; the SP check catches a wrong row instead.
    sim = Spirited(opens_on=1)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['phase'] == 'failed' and result['reason'] == 'spirit_mismatch'
    assert result['spirit']['sp'] == [55, 20] and 'start' not in sim.log


def test_a_cast_that_spends_nothing_is_skipped_and_the_list_closed():
    sim = Spirited(cast_ignored=True)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['spirit']['status'] == 'skipped'
    assert result['spirit']['reason'] == 'cast_not_confirmed'
    presses = [e for e in sim.log if not e.startswith('spirits')]
    assert presses[len(CAST_SENSE):len(CAST_SENSE) + 4] == ['cross', 'cross'] + ON_MAP
    assert result['ok'] and result['phase'] == 'fired'


def test_an_sp_drop_that_differs_from_the_cost_stops_the_act():
    sim = Spirited(charged=35)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['ok'] is False and result['phase'] == 'failed'
    assert result['reason'] == 'spirit_mismatch' and result['spirit']['sp'] == [55, 20]
    assert 'start' not in sim.log
    log = TurnLog()
    assert log.record(1000, result) == 'stop' and log.stopped == 'spirit_mismatch'


def test_an_unchanged_effect_mask_is_reported_but_the_attack_goes_on():
    sim = Spirited(mask_stuck=True)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['spirit']['status'] == 'cast'
    assert result['spirit']['effect_confirmed'] is False
    assert result['ok'] and result['phase'] == 'fired'


def test_no_time_for_a_spirit_skips_it_without_presses():
    sim = Spirited(time_left=70)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['spirit'] == {'status': 'skipped', 'reason': 'no_time'}
    presses = [e for e in sim.log if not e.startswith('spirits')]
    assert sim.sp == 55 and presses[:4] == ['goto(5, 5)', 'circle', 'down', 'circle']


def test_a_deep_row_is_not_walked():
    sim = Spirited()
    sim.list_rows = [(1, None, 5), (2, None, 5), (3, None, 5), (4, None, 5), (9, 'Sense', 20)]
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['spirit'] == {'status': 'skipped', 'reason': 'row_too_deep', 'spirit': 'Sense',
                                'row': 4}
    assert sim.sp == 55 and result['ok']


def test_an_io_without_spirit_reads_skips_the_spirit():
    sim = Game()
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['spirit'] == {'status': 'skipped', 'reason': 'no_spirit_reader'}
    assert result['ok'] and result['phase'] == 'fired'


def test_the_turn_report_keeps_the_spirit_outcome():
    sim = Spirited()
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    log = TurnLog()
    assert log.record(1000, result) == 'fired'
    assert log.entries[0]['spirit']['spirit'] == 'Sense'


def test_a_pilot_screen_is_closed_with_extra_crosses_proven_by_the_cursor():
    # m11live2 (24 Oct): a unit whose Spirit opened another screen first was left on the
    # Command menu after two Crosses; the cursor walk now proves the map before the attack.
    sim = Spirited(two_pilots=True)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    spirit = result['spirit']
    assert spirit['status'] == 'skipped' and spirit['reason'] == 'cast_not_confirmed'
    assert spirit['on_map'] is True and sim.sp == 55
    presses = [e for e in sim.log if not e.startswith('spirits')]
    assert presses[len(CAST_SENSE):len(CAST_SENSE) + 5] == [
        'cross', 'cross', 'goto(4, 5)', 'cross', 'goto(4, 5)']
    assert result['ok'] and result['phase'] == 'fired'


def test_menus_that_never_close_stop_the_turn_without_attack_presses():
    sim = Spirited(two_pilots=True, menu_stuck=True)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['ok'] is False and result['reason'] == 'spirit_menus_not_closed'
    assert result['spirit']['on_map'] is False
    assert 'start' not in sim.log and sim.log.count('cross') == 4
    log = TurnLog()
    assert log.record(1000, result) == 'stop'


def test_z_gundams_morph_entry_is_passed_over_by_the_screen_checked_row():
    # User, 24 Oct: Z Gundam's Command menu is Move / Attack / Morph / Spirit / Info (screenshot
    # m11menu1); Down x2 chose Morph. With 5 entries the row comes from the checked table.
    sim = Spirited(morph=True, mech='Z Gundam')
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['spirit']['status'] == 'cast' and result['spirit']['menu'] == [3, 5]
    presses = [e for e in sim.log if not e.startswith('spirits')]
    assert presses[:8] == ['goto(5, 5)', 'circle', 'down', 'down', 'down', 'circle', 'down',
                           'circle']
    assert result['ok'] and result['phase'] == 'fired'


def test_an_unknown_menu_layout_closes_the_menu_before_any_entry_is_chosen():
    sim = Spirited(morph=True, mech='Arios Gundam')
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    spirit = result['spirit']
    assert spirit['status'] == 'skipped' and spirit['reason'] == 'menu_layout_unknown'
    assert spirit['entries'] == 5 and spirit['on_map'] is True
    presses = [e for e in sim.log if not e.startswith('spirits')]
    assert presses[:3] == ['goto(5, 5)', 'circle', 'cross']
    assert result['ok'] and result['phase'] == 'fired' and sim.sp == 55


def test_an_unknown_layout_proves_the_map_from_memory_without_a_sideways_walk():
    # User, 1 Nov: the cursor stepped sideways and back after every closed Command menu.
    # A Cross from the Command menu cannot start a dialogue, so memory is enough here.
    sim = Spirited(morph=True, mech='Arios Gundam', screens=True)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['spirit']['on_map'] is True
    presses = [e for e in sim.log if not e.startswith('spirits')]
    assert presses[:5] == ['goto(5, 5)', 'circle', 'cross', 'goto(5, 5)', 'circle']
    assert result['ok'] and result['phase'] == 'fired'


def test_without_a_screen_reading_the_sideways_walk_still_proves_the_map():
    sim = Spirited(morph=True, mech='Arios Gundam')
    run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    presses = [e for e in sim.log if not e.startswith('spirits')]
    assert presses[:5] == ['goto(5, 5)', 'circle', 'cross', 'goto(4, 5)', 'goto(5, 5)']


def test_a_mech_with_an_unknown_layout_is_not_tried_again_in_the_same_run():
    skip: set[str] = set()
    first = Spirited(morph=True, mech='Arios Gundam', screens=True)
    run(plan_act.plan_and_act(first, SPIRIT_POLICY, 1000, spirit_skip=skip))
    assert skip == {'Arios Gundam'}
    again = Spirited(morph=True, mech='Arios Gundam', screens=True)
    result = run(plan_act.plan_and_act(again, SPIRIT_POLICY, 1000, spirit_skip=skip))
    spirit = result['spirit']
    assert spirit['status'] == 'skipped' and spirit['reason'] == 'menu_layout_unknown'
    assert spirit['cached'] is True
    presses = [e for e in again.log if not e.startswith('spirits')]
    assert presses[:2] == ['goto(5, 5)', 'circle'] and 'cross' not in presses
    assert result['ok'] and result['phase'] == 'fired'


def test_an_unreadable_menu_does_not_mark_a_known_mech_as_unknown():
    skip: set[str] = set()
    sim = Spirited(screens=True, menu_unreadable=1)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000, spirit_skip=skip))
    assert result['spirit']['reason'] == 'menu_layout_unknown' and skip == set()


def test_a_command_cursor_that_does_not_reach_spirit_closes_the_menu():
    sim = Spirited(menu_row_stuck=True)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    spirit = result['spirit']
    assert spirit['status'] == 'skipped' and spirit['reason'] == 'command_row_mismatch'
    assert spirit['menu'] == [0, 4] and spirit['on_map'] is True and sim.sp == 55


def test_command_menu_decoding_and_screen_checked_rows():
    import struct

    from psp_buddy import spirit_cast
    assert spirit_cast.decode_command_menu(struct.pack('<II', 5, 3)) == (3, 5)   # Z on Spirit
    assert spirit_cast.decode_command_menu(struct.pack('<II', 4, 2)) == (2, 4)   # 00 on Spirit
    assert spirit_cast.decode_command_menu(struct.pack('<II', 4, 4)) is None
    assert spirit_cast.decode_command_menu(struct.pack('<II', 0, 0)) is None
    assert spirit_cast.spirit_row(4, 'Gundam 00') == 2
    assert spirit_cast.spirit_row(5, 'Z Gundam') == 3
    assert spirit_cast.spirit_row(5, 'Shenlong Gundam') is None


def test_screen_checked_layouts_of_the_m16_recon():
    # 3 Nov recon (m16-rec-*, a screenshot per press): VF-25G and VF-25F with no foe in reach show
    # Move / Land / Morph / Spirit / Info; Arios with a foe in reach Move / Attack / Land / Spirit /
    # Info. Other entry counts of these mechs stay unchecked.
    from psp_buddy import spirit_cast
    for mech in ('VF25GMessiahF・TP', 'VF-25F Messiah F/TP', 'AriosGundam'):
        assert spirit_cast.spirit_row(5, mech) == 3
        assert spirit_cast.spirit_row(6, mech) is None
    assert spirit_cast.spirit_row(4, 'AriosGundam') is None


def test_a_two_pilot_unit_picks_its_first_pilot_then_casts():
    # 3 Nov recon m16-rec-menus: the 00 Raiser's Spirit opens SELECT-PILOT (Setsuna first, the
    # unit's pilot whose SP is read); one Circle opens his list. m16-b skipped it as not confirmed.
    sim = Spirited(two_pilots=True, screens=True)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    spirit = result['spirit']
    assert spirit['status'] == 'cast' and spirit['spirit'] == 'Sense' and spirit['pilot_select']
    assert sim.sp == 35 and result['phase'] == 'fired'
    presses = [e for e in sim.log if not e.startswith('spirits')]
    assert presses[:8] == ['goto(5, 5)', 'circle', 'down', 'down', 'circle', 'circle', 'down',
                           'circle']


def test_screen_checked_layouts_of_the_m16_menu_recon():
    # 3 Nov recon m16-rec-menus (screenshots, view only), turn-1 start of m15-s33-noanim.
    from psp_buddy import spirit_cast
    assert spirit_cast.spirit_row(4, 'Z Gundam') == 2          # Move / Morph / Spirit / Info
    assert spirit_cast.spirit_row(5, 'Z Gundam') == 3
    assert spirit_cast.spirit_row(6, 'VF19KaiValkyrieF') == 4   # Move/Sing/Land/Morph/Spirit/Info
    assert spirit_cast.spirit_row(3, 'AltronGundam') == 1       # Move / Spirit / Info
    assert spirit_cast.spirit_row(3, 'DeathscytheHell') == 1
    assert spirit_cast.spirit_row(5, 'WingGundamZero') == 3     # Move/Land/Morph/Spirit/Info


# ---- M16: rows from the menu's entry bitmask (u32 at slot +0x2C, 8 bytes before the count) -----
# Retained dumps (3 Nov check): Gundam 00 Move/Attack/Spirit/Info = bits 2,3,23,27; Z Gundam
# Move/Attack/Morph/Spirit/Info = 2,3,14,23,27; a ship 2,3,23,26,27 (Spirit not above Info);
# post-move Attack/?/Standby = 3,5,25 and Standby/Retrieve = 25,26. Entries list in rising bits.
BITS = {'Move': 2, 'Attack': 3, 'Repair': 5, 'Morph': 14, 'Spirit': 23, 'Standby': 25,
        'Retrieve': 26, 'Info': 27}


def mask(*labels):
    return sum(1 << BITS[label] for label in labels)


def test_entry_rows_come_from_the_bitmask():
    from psp_buddy import spirit_cast
    assert spirit_cast.entry_row(0x0880000C, 4, spirit_cast.SPIRIT_BIT) == 2
    assert spirit_cast.entry_row(0x0880400C, 5, spirit_cast.SPIRIT_BIT) == 3
    assert spirit_cast.entry_row(0x0C80000C, 5, spirit_cast.SPIRIT_BIT) == 2
    assert spirit_cast.entry_row(0x06000000, 2, spirit_cast.STANDBY_BIT) == 0
    assert spirit_cast.entry_row(0x02000028, 3, spirit_cast.STANDBY_BIT) == 2
    assert spirit_cast.entry_row(0x0880000C, 5, spirit_cast.SPIRIT_BIT) is None   # count differs
    assert spirit_cast.entry_row(0x0800000C, 3, spirit_cast.SPIRIT_BIT) is None   # no Spirit


class Masked(Spirited):
    async def menu_masks(self):
        command = mask(*self.entries) if self.screen == 'unit_menu' else 0
        return command, 0


def test_an_unlisted_mech_casts_with_the_row_from_the_bitmask():
    # m16-c turn 2: ten mechs skipped (menus with Attack, 5-7 entries, not in the table).
    sim = Masked(mech='Strike Freedom Gundam', morph=True)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    spirit = result['spirit']
    assert spirit['status'] == 'cast' and spirit['spirit'] == 'Sense' and spirit['menu'] == [3, 5]


def test_a_bitmask_without_spirit_casts_nothing():
    class NoSpirit(Masked):
        async def menu_masks(self):
            return mask('Move', 'Attack', 'Info', 'Morph'), 0

    sim = NoSpirit(mech='Strike Freedom Gundam', morph=True)
    result = run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000))
    assert result['spirit']['status'] == 'skipped' and sim.sp == 55


def test_a_bitmask_miss_does_not_skip_the_mech_for_the_rest_of_the_run():
    # Review 3 Nov: with the mask reader the row is worked out per menu, so one odd read must not
    # put the mech on the per-run skip list (turn 1 would then hold it for good).
    class NoSpirit(Masked):
        async def menu_masks(self):
            return mask('Move', 'Attack', 'Info', 'Morph'), 0

    skip: set[str] = set()
    sim = NoSpirit(mech='Strike Freedom Gundam', morph=True)
    run(plan_act.plan_and_act(sim, SPIRIT_POLICY, 1000, spirit_skip=skip))
    assert skip == set()
