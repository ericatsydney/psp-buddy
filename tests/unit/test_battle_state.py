import struct

import pytest

from psp_buddy.battle_state import (
    CELL_SIZE,
    decode_cursor,
    decode_map,
    decode_turn,
    reachable_tiles,
)


def cells(width, height, terrain=None, cost=None):
    blob = bytearray(CELL_SIZE * width * height)
    for (x, y), value in (terrain or {}).items():
        blob[CELL_SIZE * (y * width + x)] = value
    for (x, y), value in (cost or {}).items():
        blob[CELL_SIZE * (y * width + x) + 12] = value
    return bytes(blob)


def test_decode_map_terrain_and_cost_rows():
    blob = cells(4, 3, terrain={(0, 0): 1, (1, 0): 2, (3, 2): 18}, cost={(1, 1): 1, (2, 1): 12})
    state = decode_map(blob, 4, 3)
    assert state['width'] == 4 and state['height'] == 3
    assert state['terrain_rows'] == ['12..', '....', '...i']          # base-36, 0 -> '.'
    assert state['cost_rows'] == ['....', '.1c.', '....']
    assert state['terrain_classes'] == {'1': 'space', '2': 'asteroid', 'i': 'debris'}


def test_reachable_tiles_come_from_nonzero_costs():
    state = decode_map(cells(4, 3, cost={(1, 1): 1, (2, 1): 2}), 4, 3)
    assert reachable_tiles(state) == [{'x': 1, 'y': 1, 'cost': 1}, {'x': 2, 'y': 1, 'cost': 2}]


@pytest.mark.parametrize('width,height', [(0, 3), (3, 0), (65, 20), (1025, 1), (-1, 3)])
def test_decode_map_rejects_bad_dimensions(width, height):
    with pytest.raises(ValueError):
        decode_map(b'', width, height)


def test_decode_map_rejects_wrong_blob_size():
    with pytest.raises(ValueError):
        decode_map(bytes(CELL_SIZE * 11), 4, 3)


def test_decode_cursor_and_turn():
    assert decode_cursor(struct.pack('<HH', 19, 5), 24, 34) == {'x': 19, 'y': 5}
    assert decode_turn(struct.pack('<HH', 8, 0x97)) == {'turn': 8, 'running_total': 0x97}


@pytest.mark.parametrize('x,y', [(24, 0), (0, 34), (65535, 65535)])
def test_decode_cursor_rejects_out_of_range(x, y):
    with pytest.raises(ValueError):
        decode_cursor(struct.pack('<HH', x, y), 24, 34)


@pytest.mark.parametrize('turn', [0, 1000])
def test_decode_turn_rejects_implausible_turn(turn):
    with pytest.raises(ValueError):
        decode_turn(struct.pack('<HH', turn, 1))


def test_decode_blob_length_checks():
    with pytest.raises(ValueError):
        decode_cursor(b'\x00\x00', 24, 34)
    with pytest.raises(ValueError):
        decode_turn(b'\x01')
