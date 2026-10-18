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

    service = InfoNavigation(session, adapter, (19, 5), tmp_path / 'evidence', observe,
                             declaration=declaration, observe_stage=stage)
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
        for seq in range(1, 25):
            await press(service, frame, seq, 'move_range', 'move_cursor', button='up')
        with pytest.raises(ValueError):
            await press(service, frame, 25, 'move_range', 'move_cursor', button='up')
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
