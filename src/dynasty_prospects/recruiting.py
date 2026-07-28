"""HS recruiting pedigree: composite star rating, national rank, position rank."""

import cfbd
from cfbd.rest import ApiException
import pandas as pd


def fetch_recruiting(api_client: cfbd.ApiClient, years: list[int]) -> pd.DataFrame:
    recruiting_api = cfbd.RecruitingApi(api_client)
    rows = []
    for yr in years:
        try:
            resp = recruiting_api.get_recruits(year=yr)
            for p in resp:
                rows.append({
                    "recruit_name": p.name,
                    "hs_class_year": yr,
                    "position": p.position,
                    "stars": p.stars,
                    "national_rank": p.ranking,
                    "rating": p.rating,
                    "committed_school": p.committed_to,
                    "home_state": p.state_province,
                })
        except ApiException as e:
            print(f"Error fetching recruiting {yr}: {e}")
    return pd.DataFrame(rows)
