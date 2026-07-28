"""College season production stats, pulled long then pivoted wide."""

import cfbd
from cfbd.rest import ApiException
import pandas as pd


def fetch_season_stats(api_client: cfbd.ApiClient, seasons: list[int], season_type: str = "regular") -> pd.DataFrame:
    stats_api = cfbd.StatsApi(api_client)
    rows = []
    for yr in seasons:
        try:
            resp = stats_api.get_player_season_stats(year=yr, season_type=season_type)
            for s in resp:
                rows.append({
                    "player_name": s.player,
                    "team": s.team,
                    "season": yr,
                    "category": s.category,
                    "stat_type": s.stat_type,
                    "stat_value": s.stat,
                })
        except ApiException as e:
            print(f"Error fetching stats {yr}: {e}")
    return pd.DataFrame(rows)


def pivot_wide(df_stats_long: pd.DataFrame) -> pd.DataFrame:
    return (
        df_stats_long
        .pivot_table(index=["player_name", "team", "season"],
                     columns="stat_type", values="stat_value", aggfunc="first")
        .reset_index()
    )
