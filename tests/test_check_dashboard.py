from dynasty_prospects.check_dashboard import check


def _prospect(position="QB"):
    return {"prospect_id": "p", "player_name": "P", "position": position}


def _dashboard(positions):
    return {"prospects": [_prospect(pos) for pos in positions]}


def test_rejects_zero_prospects():
    problems = check(None, {"prospects": []})
    assert any("0 prospects" in p for p in problems)


def test_rejects_narrow_position_diversity():
    problems = check(None, _dashboard(["QB", "QB", "QB"]))
    assert any("distinct positions" in p for p in problems)


def test_accepts_healthy_first_build():
    problems = check(None, _dashboard(["QB", "RB", "WR", "TE", "DB", "OL"]))
    assert problems == []


def test_rejects_a_shrunk_rebuild():
    before = _dashboard(["QB", "RB", "WR", "TE", "DB", "OL"] * 20)
    after = _dashboard(["QB", "RB", "WR", "TE", "DB", "OL"])
    problems = check(before, after)
    assert any("prospect count fell" in p for p in problems)


def test_accepts_stable_rebuild():
    before = _dashboard(["QB", "RB", "WR", "TE", "DB", "OL"] * 20)
    after = _dashboard(["QB", "RB", "WR", "TE", "DB", "OL"] * 19)
    problems = check(before, after)
    assert problems == []
