"""Combine/athletic testing.

For a current draft class, this table stays empty until the actual combine
runs (Feb of the draft year). Use fetch_historical() to backfill past
classes for model training.
"""

import pandas as pd

COLUMNS = [
    "player_name", "position", "school", "forty", "vertical", "broad_jump",
    "three_cone", "shuttle", "bench_press", "height", "weight", "combine_year",
]


def empty_schema() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)


def fetch_historical(years: list[int]) -> pd.DataFrame:
    """Requires: pip install nfl_data_py"""
    import nfl_data_py as nfl
    return nfl.import_combine_data(years=years)
