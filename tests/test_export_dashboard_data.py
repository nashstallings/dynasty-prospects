import pandas as pd

from dynasty_prospects.export_dashboard_data import build_dashboard

EMPTY_COMBINE = pd.DataFrame(columns=[
    "player_name", "position", "school", "forty", "vertical", "broad_jump",
    "three_cone", "shuttle", "bench_press", "height", "weight", "combine_year",
])


def _dashboard(**overrides):
    dim_prospect = overrides.get("dim_prospect", pd.DataFrame(columns=["player_name", "team", "draft_class", "prospect_id"]))
    fact_recruiting = overrides.get("fact_recruiting", pd.DataFrame(columns=["recruit_name", "hs_class_year", "position", "stars", "national_rank", "rating", "committed_school", "home_state"]))
    fact_college_stats = overrides.get("fact_college_stats", pd.DataFrame(columns=["player_name", "team", "season"]))
    fact_team_talent = overrides.get("fact_team_talent", pd.DataFrame(columns=["team", "season", "talent_composite"]))
    fact_combine_testing = overrides.get("fact_combine_testing", EMPTY_COMBINE)
    fact_scouting_rankings = overrides.get("fact_scouting_rankings", pd.DataFrame(columns=["player_name", "position", "school", "source", "snapshot_date", "rank", "tier_grade"]))
    return build_dashboard(
        dim_prospect, fact_recruiting, fact_college_stats,
        fact_team_talent, fact_combine_testing, fact_scouting_rankings,
    )


def test_transferred_player_is_not_flagged_ambiguous():
    """A player's stats across two schools in different seasons is history, not two people."""
    dim_prospect = pd.DataFrame([
        {"player_name": "Marcus Freeman Jr.", "team": "Notre Dame", "draft_class": 2027, "prospect_id": "marcus_freeman_jr_notre_dame"},
    ])
    fact_college_stats = pd.DataFrame([
        {"player_name": "Marcus Freeman Jr.", "team": "Michigan", "season": 2024, "YDS": 800},
        {"player_name": "Marcus Freeman Jr.", "team": "Notre Dame", "season": 2025, "YDS": 1200},
    ])

    payload = _dashboard(dim_prospect=dim_prospect, fact_college_stats=fact_college_stats)

    prospect = payload["prospects"][0]
    assert prospect["ambiguous_match"] is False
    assert [row["team"] for row in prospect["stats"]] == ["Michigan", "Notre Dame"]


def test_repeated_scouting_snapshot_is_not_flagged_ambiguous():
    """Two dated snapshots from the same source for the same player is accumulating history."""
    dim_prospect = pd.DataFrame([
        {"player_name": "Marcus Freeman Jr.", "team": "Notre Dame", "draft_class": 2027, "prospect_id": "marcus_freeman_jr_notre_dame"},
    ])
    fact_scouting_rankings = pd.DataFrame([
        {"player_name": "Marcus Freeman Jr.", "position": "QB", "school": "Notre Dame", "source": "PFF", "snapshot_date": "2026-08-01", "rank": 5, "tier_grade": "1"},
        {"player_name": "Marcus Freeman Jr.", "position": "QB", "school": "Notre Dame", "source": "PFF", "snapshot_date": "2026-08-15", "rank": 3, "tier_grade": "1"},
    ])

    payload = _dashboard(dim_prospect=dim_prospect, fact_scouting_rankings=fact_scouting_rankings)

    prospect = payload["prospects"][0]
    assert prospect["ambiguous_match"] is False
    assert prospect["latest_rank"] == 3
    assert isinstance(prospect["latest_rank"], int)


def test_two_recruits_sharing_a_name_are_flagged_ambiguous():
    """Two distinct recruits in the same class year sharing a normalized name IS ambiguous."""
    dim_prospect = pd.DataFrame([
        {"player_name": "John Smith", "team": "Ohio State", "draft_class": 2027, "prospect_id": "john_smith_ohio_state"},
    ])
    fact_recruiting = pd.DataFrame([
        {"recruit_name": "John Smith", "hs_class_year": 2022, "position": "WR", "stars": 4, "national_rank": 50, "rating": 0.95, "committed_school": "Ohio State", "home_state": "OH"},
        {"recruit_name": "John Smith", "hs_class_year": 2022, "position": "DB", "stars": 3, "national_rank": 400, "rating": 0.85, "committed_school": "Texas", "home_state": "TX"},
    ])

    payload = _dashboard(dim_prospect=dim_prospect, fact_recruiting=fact_recruiting)

    prospect = payload["prospects"][0]
    assert prospect["ambiguous_match"] is True
    assert len(prospect["recruiting"]) == 2


def test_talent_joins_on_team_not_name():
    dim_prospect = pd.DataFrame([
        {"player_name": "Jane Doe", "team": "Ohio State", "draft_class": 2027, "prospect_id": "jane_doe_ohio_state"},
    ])
    fact_team_talent = pd.DataFrame([
        {"team": "Ohio State", "season": 2025, "talent_composite": 950.0},
        {"team": "Texas", "season": 2025, "talent_composite": 999.0},
    ])

    payload = _dashboard(dim_prospect=dim_prospect, fact_team_talent=fact_team_talent)

    prospect = payload["prospects"][0]
    assert len(prospect["talent"]) == 1
    assert prospect["talent"][0]["team"] == "Ohio State"


def test_unmatched_recruiting_row_does_not_crash_and_is_excluded():
    dim_prospect = pd.DataFrame([
        {"player_name": "Jane Doe", "team": "Ohio State", "draft_class": 2027, "prospect_id": "jane_doe_ohio_state"},
    ])
    fact_recruiting = pd.DataFrame([
        {"recruit_name": "Someone Else", "hs_class_year": 2022, "position": "WR", "stars": 4, "national_rank": 50, "rating": 0.95, "committed_school": "Alabama", "home_state": "AL"},
    ])

    payload = _dashboard(dim_prospect=dim_prospect, fact_recruiting=fact_recruiting)

    prospect = payload["prospects"][0]
    assert prospect["recruiting"] == []


def test_empty_dim_prospect_produces_empty_prospect_list():
    payload = _dashboard()
    assert payload["prospects"] == []
