# Dynasty Prospects Pipeline

Two independent BigQuery-backed pipelines for dynasty fantasy football prep:

- **`dynasty_prospects`** — 2027 NFL Draft class college prospect data (CFBD), for dynasty rookie draft prep.
- **`nfl_data`** — current NFL player data (nflreadpy), a route-share/YPRR proxy, and a Sleeper-projection-based dynasty auction valuation model.

They're split because they pull from unrelated data domains (college vs. pro) and their dependencies conflict (see [Known gotchas](#known-gotchas)).

## How this repo fits together

- **`src/dynasty_prospects/`** / **`src/nfl_data/`** — the actual pipeline logic (data pulls, transforms, BigQuery writes) for each pipeline. Edit these in Claude Code.
- **`notebooks/colab_runner.ipynb`** / **`notebooks/nfl_data_runner.ipynb`** — thin notebooks that clone this repo, install the relevant package, and call `<package>.run()`. Run in Colab so you get GCP auth for free. These notebooks should rarely need edits — logic changes belong in `src/`.

## Local dev (Claude Code)

```bash
pip install -e ".[cfbd]"   # dynasty_prospects
pip install -e ".[nfl]"    # nfl_data
```

Then edit modules under `src/dynasty_prospects/` or `src/nfl_data/`, test locally, commit, push.

## Running in Colab

1. Open `notebooks/colab_runner.ipynb` (college prospects) or `notebooks/nfl_data_runner.ipynb` (NFL/fantasy data) in Colab (or `File > Open notebook > GitHub` and paste this repo's URL).
2. Run all cells. It clones the repo fresh each run, so it always uses whatever is on `main`.
3. If this repo is **private**, add a GitHub personal access token as a Colab secret named `GITHUB_TOKEN` (key icon in the left sidebar) before running — the clone cell picks it up automatically. Public repos need nothing extra.

## Tables produced

### `dynasty_prospects` — BigQuery dataset `dynasty_prospects`

| Table | Source | Notes |
|---|---|---|
| `dim_prospect` | derived | Master player list, seeded from current-season stat participants |
| `fact_recruiting` | CFBD | HS composite star rating, national/position rank |
| `fact_college_stats` | CFBD | Season-level production stats |
| `fact_team_talent` | CFBD | Team talent composite (context feature) |
| `fact_combine_testing` | manual/nfl_data_py | Empty for current class until Feb 2027 combine |
| `fact_scouting_rankings` | manual | Dated big-board snapshots — no API exists for this |

### `nfl_data` — three BigQuery datasets

| Table | Dataset | Source | Notes |
|---|---|---|---|
| `players` | `nflreadpy` | nflreadpy | Skill-position players + cross-platform IDs |
| `player_stats` | `nflreadpy` | nflreadpy | Weekly stats, with a within-week/position PPR rank added |
| `snap_counts` | `nflreadpy` | nflreadpy | Weekly snap share by player |
| `nextgen_stats` | `nflreadpy` | nflreadpy | Passing/receiving/rushing NGS, stacked long |
| `ff_opportunity` | `nflreadpy` | nflreadpy | Weekly opportunity/target-share model output |
| `yprr_proxy` | `dynasty` | derived (nflreadpy) | Estimated YPRR/target rate via a snap-share proxy — see `yprr.py` module docstring for methodology and caveats before trusting the numbers |
| `player_auction_values` | `dynasty_tycoon` | Sleeper + nflreadpy | Age-adjusted, superflex-aware dynasty auction values, priced to a $3000/12-team budget |

All `nfl_data` tables are filtered to `QB`/`RB`/`WR`/`TE` and replaced wholesale on each run — none of them accumulate history the way `fact_scouting_rankings` does.

## Known gotchas

- `cfbd` has renamed API methods across versions before (`get_recruiting_players` → `get_recruits`). Version is pinned in `requirements.txt` — if you bump it, diff the method list first:
  ```bash
  python -c "import cfbd; print([m for m in dir(cfbd.RecruitingApi) if not m.startswith('_')])"
  ```
- Player identity isn't unified across CFBD endpoints and manual scouting CSVs — `dim_prospect.prospect_id` joins on name + school, which needs occasional manual cleanup for transfers/nicknames.
- `cfbd==5.20.1` requires `pydantic<2`; `nflreadpy` requires `pydantic>=2`. They can't be installed together, which is why they're separate `pyproject.toml` extras (`.[cfbd]` / `.[nfl]`) instead of both being base dependencies — installing the wrong extra for what you're running will fail to resolve.
- Sleeper's `gsis_id` field is sparse. `nfl_data.id_matching.resolve_gsis_ids` backfills it by name+position match against nflreadpy's player table, then falls back to a stable synthetic id (`config.SYNTHETIC_GSIS_OVERRIDES` for known cases, else `SL_<sleeper_id>`) for anyone still unmatched — mostly very recent rookies.
