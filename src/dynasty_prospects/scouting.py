"""Scouting/consensus big board rankings.

No unified API covers big boards (NFLMockDraftDatabase, PFF, The Draft
Network, ESPN, etc). Track these as dated snapshots you upload manually --
rankings shift throughout the season, so history matters more than a
single current value.
"""

import pandas as pd

COLUMNS = ["player_name", "position", "school", "source", "snapshot_date", "rank", "tier_grade"]


def empty_schema() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)


def append_snapshot(existing: pd.DataFrame, csv_path: str) -> pd.DataFrame:
    new_snapshot = pd.read_csv(csv_path)
    return pd.concat([existing, new_snapshot], ignore_index=True)
