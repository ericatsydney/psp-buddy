from psp_buddy import press_budget as pb


def test_walk_is_the_manhattan_length_of_the_path():
    assert pb.walk([(3, 4), (5, 1)]) == 5
    assert pb.walk([(0, 0), (2, 0), (2, 3), (0, 3)]) == 7
    assert pb.walk([(1, 1)]) == 0
    assert pb.walk([]) == 0


def test_reach_unit_reserves_the_proof_walks():
    # cursor (0,0) -> unit (4,3) = 7 taps, then the planner's own walks are checked later
    assert pb.reach_unit((0, 0), (4, 3)) == 7 + pb.PROOF_PRESSES


def test_act_cost_covers_move_target_and_margin():
    cost = pb.act_cost((5, 5), destination=(5, 8), target=(7, 9))
    assert cost == 3 + 3 + pb.ACTION_MARGIN
    assert pb.act_cost((5, 5), destination=None, target=(5, 7)) == 2 + pb.ACTION_MARGIN
    assert pb.act_cost((5, 5), destination=(6, 5), target=None) == 1 + pb.ACTION_MARGIN


def test_spirit_cast_adds_its_proof_walk():
    plain = pb.act_cost((5, 5), destination=None, target=(5, 7))
    assert pb.act_cost((5, 5), destination=None, target=(5, 7), spirit=True) == (
        plain + pb.PROOF_PRESSES)


def test_fits_compares_with_what_is_left():
    assert pb.fits(10, used=390, budget=400)
    assert not pb.fits(11, used=390, budget=400)
    assert not pb.fits(1, used=400, budget=400)
