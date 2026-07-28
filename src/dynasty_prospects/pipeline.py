"""Orchestrates the full prospect data pull -> transform -> BigQuery write."""

import pandas as pd

from . import config
from .cfbd_client import get_client
from .recruiting import fetch_recruiting
from .stats import fetch_season_stats, pivot_wide
from .talent import fetch_team_talent
from . import combine, scouting
from .bigquery_io import write_tables


def build_dim_prospect(df_stats_wide: pd.DataFrame, draft_class: int) -> pd.DataFrame:
    current_season_players = (
        df_stats_wide[df_stats_wide["season"] == df_stats_wide["season"].max()][["player_name", "team"]]
        .drop_duplicates()
    )
    dim_prospect = current_season_players.copy()
    dim_prospect["draft_class"] = draft_class
    dim_prospect["prospect_id"] = (
        dim_prospect["player_name"].str.lower().str.replace(r"[^a-z ]", "", regex=True).str.replace(" ", "_")
        + "_" + dim_prospect["team"].str.lower().str.replace(" ", "_")
    )
    return dim_prospect


def run(cfbd_api_key: str, write_to_bq: bool = True) -> dict[str, pd.DataFrame]:
    api_client = get_client(cfbd_api_key)

    df_recruiting = fetch_recruiting(api_client, config.RECRUITING_CLASS_YEARS)
    df_stats_long = fetch_season_stats(api_client, config.CFBD_SEASONS)
    df_stats_wide = pivot_wide(df_stats_long)
    df_talent = fetch_team_talent(api_client, config.CFBD_SEASONS)
    df_combine = combine.empty_schema()
    df_scouting = scouting.empty_schema()
    dim_prospect = build_dim_prospect(df_stats_wide, config.DRAFT_CLASS)

    tables = {
        "dim_prospect": dim_prospect,
        "fact_recruiting": df_recruiting,
        "fact_college_stats": df_stats_wide,
        "fact_team_talent": df_talent,
        "fact_combine_testing": df_combine,
        "fact_scouting_rankings": df_scouting,
    }

    if write_to_bq:
        write_tables(tables, config.PROJECT_ID, config.DATASET_ID)

    return tables
