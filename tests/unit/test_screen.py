import struct

import pytest

from psp_buddy import screen

B = 0x08800000
ROOT, CMD, MENU2, RANGE, WEAPONS, TARGETS, SPIRITS, AMBIENT = (
    0x08E4BD0C, 0x08E4BDDC, 0x08E4BE5C, 0x08E4BF6C, 0x08E4C5C4, 0x08E4C67C, 0x08E4D208, 0x08E4CED4)


def ram_with(objects, *, count=None, cycle=False):
    """A RAM image whose UI pool has `objects` allocated (in node order) and the rest free."""
    ram = bytearray(0x1800000)
    put = lambda a, v: struct.pack_into('<I', ram, a - B, v)  # noqa: E731
    nodes = [screen.NODES_START + 12 * k for k in range(screen.NODE_COUNT)]
    for k, node in enumerate(nodes):
        slot = screen.SLOTS_START + 4 * k
        put(node, slot)
        put(slot, objects[k] if k < len(objects) else 0)
    free = nodes[len(objects):]
    for a, b in zip(free, free[1:], strict=False):
        put(a + 4, b)
    if free:
        put(free[-1] + 4, free[0] if cycle else 0)
        put(screen.FREE_HEAD, free[0])
    put(screen.FREE_COUNT, len(free) if count is None else count)
    return bytes(ram)


@pytest.mark.parametrize('objects, expected', [
    ([ROOT], 'no_menu'),
    ([ROOT, AMBIENT], 'no_menu'),
    ([ROOT, CMD], 'unit_commands'),
    ([ROOT, CMD, RANGE], 'move_range'),
    ([ROOT, CMD, WEAPONS], 'weapon_list'),
    ([ROOT, CMD, WEAPONS, TARGETS], 'target_select'),
    ([ROOT, CMD, MENU2, RANGE], 'post_move_menu'),
    ([ROOT, CMD, SPIRITS], 'spirit_list'),
])
def test_known_window_sets_name_the_screen(objects, expected):
    found = screen.classify(screen.open_windows(ram_with(objects)))
    assert found == expected


def test_order_of_allocation_does_not_matter():
    assert screen.classify(screen.open_windows(ram_with([TARGETS, ROOT, WEAPONS, CMD]))) == (
        'target_select')


@pytest.mark.parametrize('objects', [
    [ROOT, 0x08E4C000], [CMD], [ROOT, WEAPONS], [ROOT, CMD, TARGETS], [ROOT, CMD, CMD]])
def test_anything_else_is_unknown(objects):
    assert screen.classify(screen.open_windows(ram_with(objects))) == 'unknown'


def test_a_free_list_that_disagrees_with_the_count_is_unreadable():
    with pytest.raises(ValueError):
        screen.open_windows(ram_with([ROOT, CMD], count=5))


def test_a_cyclic_free_list_is_unreadable():
    with pytest.raises(ValueError):
        screen.open_windows(ram_with([ROOT, CMD], cycle=True))


def test_layers_count_the_open_menus():
    assert screen.layers('target_select') == 3 and screen.layers('no_menu') == 0
    assert screen.layers('unknown') is None


def test_backout_from_target_select_closes_one_window_per_cross():
    steps = screen.backout('target_select')
    assert [s['expect'] for s in steps] == ['weapon_list', 'unit_commands', 'no_menu']
    assert [s['purpose'] for s in steps] == ['cancel', 'cancel', 'close_command_menu']
    assert all(s['button'] == 'cross' for s in steps)
    assert screen.backout('no_menu') == []


@pytest.mark.parametrize('name', ['unknown', 'post_move_menu', 'spirit_list'])
def test_unproven_back_outs_give_no_steps(name):
    assert screen.backout(name) is None
