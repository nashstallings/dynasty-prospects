# Dynasty Prospects Pipeline

Builds a BigQuery-backed prospect dataset for the 2027 NFL Draft class, for dynasty rookie draft prep.

## How this repo fits together

- **`src/dynasty_prospects/`** — the actual pipeline logic (data pulls, transforms, BigQuery writes). Edit this in Claude Code.
- **`notebooks/colab_runner.ipynb`** — a thin notebook that clones this repo, installs it, and calls `dynasty_prospects.run()`. Runs in Colab so you get GCP auth for free. This notebook should rarely need edits — logic changes belong in `src/`.

## Local dev (Claude Code)

```bash
pip install -e .
```

Then edit modules under `src/dynasty_prospects/`, test locally, commit, push.

## Running in Colab

1. Open `notebooks/colab_runner.ipynb` in Colab (or `File > Open notebook > GitHub` and paste this repo's URL).
2. Run all cells. It clones the repo fresh each run, so it always uses whatever is on `main`.
3. If this repo is **private**, add a GitHub personal access token as a Colab secret named `GITHUB_TOKEN` (key icon in the left sidebar) before running — the clone cell picks it up automatically. Public repos need nothing extra.

## Tables produced

| Table | Source | Notes |
|---|---|---|
| `dim_prospect` | derived | Master player list, seeded from current-season stat participants |
| `fact_recruiting` | CFBD | HS composite star rating, national/position rank |
| `fact_college_stats` | CFBD | Season-level production stats |
| `fact_team_talent` | CFBD | Team talent composite (context feature) |
| `fact_combine_testing` | manual/nfl_data_py | Empty for current class until Feb 2027 combine |
| `fact_scouting_rankings` | manual | Dated big-board snapshots — no API exists for this |

## Known gotchas

- `cfbd` has renamed API methods across versions before (`get_recruiting_players` → `get_recruits`). Version is pinned in `requirements.txt` — if you bump it, diff the method list first:
  ```bash
  python -c "import cfbd; print([m for m in dir(cfbd.RecruitingApi) if not m.startswith('_')])"
  ```
- Player identity isn't unified across CFBD endpoints and manual scouting CSVs — `dim_prospect.prospect_id` joins on name + school, which needs occasional manual cleanup for transfers/nicknames.
