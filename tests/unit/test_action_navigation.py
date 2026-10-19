# ruff: noqa: F811
import asyncio
import hashlib

import pytest
from test_capture import owned, picture  # noqa: F401
from test_debugger import FakeTransport

from psp_buddy.debugger import DebuggerAdapter

DECL = {'unit': 'Destiny', 'actions': ['move', 'standby'], 'destination_tile': [19, 6]}
ATTACK = {'unit': 'Destiny', 'actions': ['attack'], 'weapon_name': 'Beam Rifle',
          'target_name': 'Zaku'}


def setup(owned, tmp_path, declaration=DECL):
    from psp_buddy.info_navigation import InfoNavigation
    session, _ = owned
    transport = FakeTransport()
    adapter = DebuggerAdapter(transport)
    adapter._assert_bound = session.assert_bound

    async def observe():
        return {'unit': 'Destiny', 'hp': 5200}

    stages = []

    async def stage(n):
        stages.append(n)
        return {'stage': n}

    dumps = []

    async def dump(n):
        dumps.append(n)
        return {'file': f'ram-{n:02d}.bin'}

    reads = []

    async def read_state(n):
        reads.append(n)
        return {'turn': 7, 'cursor': {'x': 3, 'y': 4}}

    service = InfoNavigation(session, adapter, (19, 5), tmp_path / 'evidence', observe,
                             declaration=declaration, observe_stage=stage, dump_ram=dump,
                             occupied_tiles=[(19, 5), (18, 4)], read_state=read_state)
    root = session.memstick_root / 'PSP/SCREENSHOT'
    root.mkdir(exist_ok=True)
    counter = [0]

    def frame(context, **extra):
        counter[0] += 1
        path = root / f'f{counter[0]}.png'
        data = picture()
        path.write_bytes(data)
        return dict(sequence=extra.pop('sequence'), screen_file=path.name,
                    screen_sha256=hashlib.sha256(data).hexdigest(), context=context, **extra)

    return service, transport, frame, stages


def press(service, frame, seq, context, purpose, button='circle', **extra):
    return service.execute('press', frame(context, sequence=seq, button=button, duration=2,
                                          purpose=purpose, **extra))


def test_actions_refused_without_declaration(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path, declaration=None)
    with pytest.raises(ValueError):
        asyncio.run(press(service, frame, 1, 'unit_commands', 'open_move',
                          highlighted_entry='Move'))
    assert not transport.sent


def test_move_then_standby_flow(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path)

    async def scenario():
        await press(service, frame, 1, 'unit_commands', 'open_move', highlighted_entry='Move')
        await press(service, frame, 2, 'move_range', 'move_cursor', button='down')
        await press(service, frame, 3, 'move_range', 'confirm_move', destination_tile=[19, 6])
        await press(service, frame, 4, 'unit_commands', 'standby_after_move',
                    highlighted_entry='Standby')
        with pytest.raises(ValueError):
            await press(service, frame, 5, 'move_range', 'confirm_move',
                        destination_tile=[19, 6])
    asyncio.run(scenario())


@pytest.mark.parametrize('purpose,context,extra', [
    ('confirm_move', 'move_range', dict(destination_tile=[9, 9])),
    ('open_attack', 'unit_commands', dict(highlighted_entry='Attack')),
    ('standby_after_move', 'unit_commands', dict(highlighted_entry='Standby')),
    ('confirm_move', 'move_range', dict(destination_tile=[True, 6])),
    ('open_move', 'unit_commands', dict(highlighted_entry='Attack')),
])
def test_wrong_action_refused_before_io(owned, tmp_path, purpose, context, extra):
    service, transport, frame, _ = setup(owned, tmp_path)
    with pytest.raises(ValueError):
        asyncio.run(press(service, frame, 1, context, purpose, **extra))
    assert not transport.sent


def test_attack_fields_must_match(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path, ATTACK)

    async def scenario():
        await press(service, frame, 1, 'unit_commands', 'open_attack',
                    highlighted_entry='Attack')
        # a target cannot be chosen, and combat cannot start, before a weapon is selected
        with pytest.raises(ValueError):
            await press(service, frame, 2, 'target_select', 'choose_target',
                        target_name='Zaku')
        await press(service, frame, 2, 'weapon_list', 'select_weapon', weapon_name='Beam Rifle')
        with pytest.raises(ValueError):
            await press(service, frame, 3, 'target_select', 'choose_target',
                        target_name='Gelgoog')
        # Start needs a chosen target; circle never starts combat
        with pytest.raises(ValueError):
            await press(service, frame, 3, 'attack_forecast', 'confirm_attack',
                        button='start', target_name='Zaku')
        await press(service, frame, 3, 'target_select', 'choose_target', target_name='Zaku')
        with pytest.raises(ValueError):
            await press(service, frame, 4, 'attack_forecast', 'confirm_attack',
                        target_name='Zaku')
        with pytest.raises(ValueError):
            await press(service, frame, 4, 'attack_forecast', 'confirm_attack',
                        button='start', target_name='Gelgoog')
        await press(service, frame, 4, 'attack_forecast', 'confirm_attack',
                    button='start', target_name='Zaku')
        with pytest.raises(ValueError):
            await press(service, frame, 5, 'attack_forecast', 'confirm_attack',
                        button='start', target_name='Zaku')
    asyncio.run(scenario())


def test_budget_and_observe_non_terminal(owned, tmp_path):
    service, transport, frame, stages = setup(owned, tmp_path)

    async def scenario():
        for seq in range(1, 41):
            await press(service, frame, seq, 'move_range', 'move_cursor', button='up')
        with pytest.raises(ValueError):
            await press(service, frame, 41, 'move_range', 'move_cursor', button='up')
    asyncio.run(scenario())
    service, _, frame, stages = setup(owned, tmp_path)

    async def observing():
        result = await service.execute('observe', frame('map', sequence=1))
        assert result['stage'] == 1 and stages == [1]
        await press(service, frame, 2, 'move_range', 'move_cursor', button='down')
    asyncio.run(observing())


def test_pre_io_refusal_is_a_refusal_type(owned, tmp_path):
    from psp_buddy.navigation_mailbox import NavigationRefused
    service, transport, frame, _ = setup(owned, tmp_path)
    with pytest.raises(NavigationRefused):
        asyncio.run(press(service, frame, 1, 'move_range', 'confirm_move',
                          destination_tile=[9, 9]))
    assert not transport.sent
    # the service stays usable after a refusal
    asyncio.run(press(service, frame, 1, 'move_range', 'move_cursor', button='down'))


RECON = {'unit': 'Destiny', 'actions': ['attack_recon']}


def test_attack_recon_allows_viewing_but_never_confirming(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path, RECON)

    async def scenario():
        await press(service, frame, 1, 'unit_commands', 'open_attack',
                    highlighted_entry='Attack')
        await press(service, frame, 2, 'weapon_list', 'select_weapon', button='down')
        await press(service, frame, 3, 'weapon_list', 'select_weapon', weapon_name='Beam Rifle')
        await press(service, frame, 4, 'target_select', 'select_target', button='right')
        for seq, purpose, context, extra in (
                (5, 'confirm_attack', 'attack_forecast', dict(button='start', target_name='Zaku')),
                (5, 'choose_target', 'target_select', dict(target_name='Zaku')),
                (5, 'open_move', 'unit_commands', dict(highlighted_entry='Move')),
                (5, 'confirm_move', 'move_range', dict(destination_tile=[19, 6])),
                (5, 'standby_after_move', 'unit_commands', dict(highlighted_entry='Standby'))):
            with pytest.raises(ValueError):
                await press(service, frame, seq, context, purpose, **extra)
        await press(service, frame, 5, 'target_select', 'cancel', button='cross')
    asyncio.run(scenario())


@pytest.mark.parametrize('bad', [
    {'unit': 'Destiny', 'actions': ['attack_recon', 'attack']},
    {'unit': 'Destiny', 'actions': ['attack_recon'], 'weapon_name': 'x'},
])
def test_recon_declaration_is_exact(owned, tmp_path, bad):
    with pytest.raises(ValueError):
        setup(owned, tmp_path, bad)


MOVE_ATTACK = {'unit': 'Z Gundam', 'actions': ['move', 'attack'], 'destination_tile': [14, 15],
               'weapon_name': 'Beam Rifle', 'target_name': 'tile(12,17)'}


def test_move_then_attack_flow_and_ordering(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path, MOVE_ATTACK)

    async def scenario():
        await press(service, frame, 1, 'unit_commands', 'open_move', highlighted_entry='Move')
        # attack steps are refused until the declared move is confirmed
        with pytest.raises(ValueError):
            await press(service, frame, 2, 'unit_commands', 'open_attack',
                        highlighted_entry='Attack')
        await press(service, frame, 2, 'move_range', 'confirm_move', destination_tile=[14, 15])
        with pytest.raises(ValueError):  # Standby was not declared
            await press(service, frame, 3, 'unit_commands', 'standby_after_move',
                        highlighted_entry='Standby')
        await press(service, frame, 3, 'unit_commands', 'open_attack',
                    highlighted_entry='Attack')
        await press(service, frame, 4, 'weapon_list', 'select_weapon', weapon_name='Beam Rifle')
        await press(service, frame, 5, 'target_select', 'choose_target',
                    target_name='tile(12,17)')
        await press(service, frame, 6, 'attack_forecast', 'confirm_attack', button='start',
                    target_name='tile(12,17)')
    asyncio.run(scenario())


def test_budget_is_forty_and_directional_frames_shared_four_times(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path, MOVE_ATTACK)

    async def scenario():
        shared = frame('move_range', sequence=1, button='down', duration=2,
                       purpose='move_cursor')
        for seq in range(1, 5):
            args = dict(shared, sequence=seq)
            await service.execute('press', args)
        with pytest.raises(ValueError):
            await service.execute('press', dict(shared, sequence=5))
        for seq in range(5, 41):
            await press(service, frame, seq, 'move_range', 'move_cursor', button='up')
        with pytest.raises(ValueError):
            await press(service, frame, 41, 'move_range', 'move_cursor', button='up')
    asyncio.run(scenario())


def test_dismiss_result_only_after_a_declared_attack(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path, ATTACK)

    async def scenario():
        with pytest.raises(ValueError):  # nothing has been attacked yet
            await press(service, frame, 1, 'result', 'dismiss_result')
        await press(service, frame, 1, 'unit_commands', 'open_attack',
                    highlighted_entry='Attack')
        await press(service, frame, 2, 'weapon_list', 'select_weapon', weapon_name='Beam Rifle')
        await press(service, frame, 3, 'target_select', 'choose_target', target_name='Zaku')
        await press(service, frame, 4, 'attack_forecast', 'confirm_attack', button='start',
                    target_name='Zaku')
        with pytest.raises(ValueError):  # wrong context / button
            await press(service, frame, 5, 'map', 'dismiss_result')
        with pytest.raises(ValueError):
            await press(service, frame, 5, 'result', 'dismiss_result', button='start')
        await press(service, frame, 5, 'result', 'dismiss_result')
    asyncio.run(scenario())


def test_dismiss_result_refused_in_recon_and_without_declaration(owned, tmp_path):
    for declaration in (RECON, None):
        service, transport, frame, _ = setup(owned, tmp_path, declaration)
        with pytest.raises(ValueError):
            asyncio.run(press(service, frame, 1, 'result', 'dismiss_result'))
        assert not transport.sent


@pytest.mark.parametrize('context', ['unit_commands', 'result'])
def test_cancel_not_allowed_on_command_menu_or_result(owned, tmp_path, context):
    service, transport, frame, _ = setup(owned, tmp_path)
    with pytest.raises(ValueError):
        asyncio.run(press(service, frame, 1, context, 'cancel', button='cross'))
    assert not transport.sent


def test_dump_is_read_only_counted_and_bounded(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path)

    async def scenario():
        for n in range(1, 25):
            result = await service.execute('dump', frame('map', sequence=n))
            assert result['file'] == f'ram-{n:02d}.bin' and result['dump'] == n
        with pytest.raises(ValueError):
            await service.execute('dump', frame('map', sequence=25))
    asyncio.run(scenario())
    assert not transport.sent  # dumps send no input


def test_dump_refused_without_a_dump_reader(owned, tmp_path):
    from psp_buddy.info_navigation import InfoNavigation
    service, transport, frame, _ = setup(owned, tmp_path)
    bare = InfoNavigation(owned[0], service._adapter, (19, 5), tmp_path / 'e2',
                          service._verify)
    with pytest.raises(ValueError):
        asyncio.run(bare.execute('dump', frame('map', sequence=1)))


SYSTEM_RECON = {'unit': 'Destiny', 'actions': ['system_recon']}
END_TURN = {'unit': 'Destiny', 'actions': ['end_turn'], 'entry_label': 'Phase End'}


def test_system_recon_views_but_never_confirms(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path, SYSTEM_RECON)

    async def scenario():
        with pytest.raises(ValueError):  # a unit is on this tile
            await press(service, frame, 1, 'map', 'open_system_menu', cursor_tile=[19, 5])
        await press(service, frame, 1, 'map', 'open_system_menu', cursor_tile=[3, 3])
        await press(service, frame, 2, 'system_menu', 'system_menu_move', button='down')
        for purpose, kwargs in (('end_turn', dict(highlighted_entry='Phase End')),
                                ('open_move', dict(highlighted_entry='Move'))):
            with pytest.raises(ValueError):
                await press(service, frame, 3, 'system_menu', purpose, **kwargs)
        await press(service, frame, 3, 'system_menu', 'cancel', button='cross')
    asyncio.run(scenario())


def test_system_menu_refused_without_declaration_or_occupancy(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path, declaration=None)
    with pytest.raises(ValueError):
        asyncio.run(press(service, frame, 1, 'map', 'open_system_menu', cursor_tile=[3, 3]))
    assert not transport.sent


def test_end_turn_needs_label_menu_and_happens_once(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path, END_TURN)

    async def scenario():
        with pytest.raises(ValueError):  # menu not opened yet
            await press(service, frame, 1, 'system_menu', 'end_turn',
                        highlighted_entry='Phase End')
        with pytest.raises(ValueError):  # nothing to advance before End Turn
            await press(service, frame, 1, 'enemy_phase', 'advance_dialog')
        await press(service, frame, 1, 'map', 'open_system_menu', cursor_tile=[3, 3])
        with pytest.raises(ValueError):  # wrong label
            await press(service, frame, 2, 'system_menu', 'end_turn',
                        highlighted_entry='Save')
        await press(service, frame, 2, 'system_menu', 'end_turn',
                    highlighted_entry='Phase End')
        with pytest.raises(ValueError):  # only once
            await press(service, frame, 3, 'system_menu', 'end_turn',
                        highlighted_entry='Phase End')
        await press(service, frame, 3, 'enemy_phase', 'advance_dialog')
    asyncio.run(scenario())


@pytest.mark.parametrize('bad', [
    {'unit': 'Destiny', 'actions': ['end_turn']},
    {'unit': 'Destiny', 'actions': ['end_turn', 'move'], 'entry_label': 'x',
     'destination_tile': [1, 1]},
    {'unit': 'Destiny', 'actions': ['system_recon'], 'entry_label': 'x'},
])
def test_system_declarations_are_exact(owned, tmp_path, bad):
    with pytest.raises(ValueError):
        setup(owned, tmp_path, bad)


def test_state_read_needs_no_screenshot_and_sends_no_input(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path)

    async def scenario():
        first = await service.execute('state', {'sequence': 1})
        assert first['turn'] == 7 and first['sequence'] == 1 and first['state_read'] == 1
        # shares the sequence counter with every other operation
        with pytest.raises(ValueError):
            await service.execute('state', {'sequence': 1})
        with pytest.raises(ValueError):
            await service.execute('state', {'sequence': 2, 'screen_file': 'x.png'})
        await press(service, frame, 2, 'map', 'cursor', button='right')
        await service.execute('state', {'sequence': 3})
    asyncio.run(scenario())
    assert len(transport.sent) > 0  # only the press sent anything


def test_state_reads_are_bounded_and_need_a_reader(owned, tmp_path):
    service, transport, frame, _ = setup(owned, tmp_path)

    async def scenario():
        for n in range(1, 201):
            await service.execute('state', {'sequence': n})
        with pytest.raises(ValueError):
            await service.execute('state', {'sequence': 201})
    asyncio.run(scenario())
    from psp_buddy.info_navigation import InfoNavigation
    bare = InfoNavigation(owned[0], service._adapter, (19, 5), tmp_path / 'e3', service._verify)
    with pytest.raises(ValueError):
        asyncio.run(bare.execute('state', {'sequence': 1}))


def test_state_refusal_and_oversize_keep_the_session_usable(owned, tmp_path):
    from psp_buddy.info_navigation import InfoNavigation
    from psp_buddy.navigation_mailbox import NavigationRefused
    session, _ = owned
    service0, transport, frame, _ = setup(owned, tmp_path)
    modes = ['transient', 'huge', 'ok']

    async def reader(n):
        mode = modes.pop(0)
        if mode == 'transient':
            raise NavigationRefused('map not loaded')
        if mode == 'huge':
            return {'blob': 'x' * 20000}
        return {'turn': 7}

    service = InfoNavigation(session, service0._adapter, (19, 5), tmp_path / 'e4', service0._verify,
                             read_state=reader)

    async def scenario():
        with pytest.raises(NavigationRefused):
            await service.execute('state', {'sequence': 1})
        with pytest.raises(NavigationRefused):          # over the mailbox limit
            await service.execute('state', {'sequence': 1})
        result = await service.execute('state', {'sequence': 1})   # sequence was not consumed
        assert result['turn'] == 7 and result['sequence'] == 1 and result['state_read'] == 1
    asyncio.run(scenario())
    assert (tmp_path / 'e4' / 'agent-navigation-inputs.jsonl').exists()   # the good read is logged
