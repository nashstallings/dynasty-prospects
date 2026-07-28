"""Team talent composite -- context feature for player counting stats."""

import cfbd
from cfbd.rest import ApiException
import pandas as pd


def fetch_team_talent(api_client: cfbd.ApiClient, years: list[int]) -> pd.DataFrame:
    teams_api = cfbd.TeamsApi(api_client)
    rows = []
    for yr in years:
        try:
            resp = teams_api.get_talent(year=yr)
            for t in resp:
                rows.append({"team": t.team, "season": t.year, "talent_composite": t.talent})
        except ApiException as e:
            print(f"Error fetching talent {yr}: {e}")
    return pd.DataFrame(rows)
