"""Shared CFBD API client setup.

cfbd's method names have changed across versions before (e.g.
get_recruiting_players -> get_recruits in 5.20.x). This module pins the
version at the point of use in requirements.txt -- if you bump it, re-check
method names against the installed package with:

    python -c "import cfbd; print([m for m in dir(cfbd.RecruitingApi) if not m.startswith('_')])"
"""

import cfbd


def get_client(api_key: str) -> cfbd.ApiClient:
    api_key = api_key.strip()
    if not api_key or not api_key.isascii():
        raise ValueError(
            "CFBD_API_KEY looks wrong (empty or contains non-ASCII characters) -- "
            "re-enter just the key from https://collegefootballdata.com/key, "
            "nothing else pasted in."
        )
    configuration = cfbd.Configuration(
        host="https://api.collegefootballdata.com",
        access_token=api_key,
    )
    return cfbd.ApiClient(configuration)
