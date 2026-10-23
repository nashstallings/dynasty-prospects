# Dynasty Prospects

Builds a BigQuery-backed prospect dataset for the 2027 NFL Draft class, for dynasty rookie
draft prep, and a read-only dashboard for browsing it.

## How this repo fits together

- **`src/dynasty_prospects/`** — pipeline logic (data pulls, transforms, BigQuery writes) and
  the dashboard's data export. Edit this in Claude Code.
- **`notebooks/colab_runner.ipynb`** — a thin notebook that clones this repo, installs it, and
  calls `dynasty_prospects.run()`. Runs in Colab so you get GCP auth for free. Useful for
  manual/ad-hoc runs (e.g. after uploading a scouting snapshot); the scheduled refresh below
  covers the routine case.
- **`web/`** — the dashboard's static frontend (vanilla JS, no build step). Published to GitHub
  Pages as-is; `web/data/dashboard.json` lives inside it for exactly that reason.

## Local dev (Claude Code)

```bash
pip install -e .
pip install --no-deps nfl_data_py==0.3.3  # see the note in requirements.txt
```

Then edit modules under `src/dynasty_prospects/`, test locally (`pytest`), commit, push.

## Running the pipeline in Colab

1. Open `notebooks/colab_runner.ipynb` in Colab (or `File > Open notebook > GitHub` and paste this repo's URL).
2. Run all cells. It clones the repo fresh each run, so it always uses whatever is on `main`.
3. If this repo is **private**, add a GitHub personal access token as a Colab secret named `GITHUB_TOKEN` (key icon in the left sidebar) before running — the clone cell picks it up automatically. Public repos need nothing extra.

## The dashboard

`web/` is a small, fully public, **read-only** browse/filter view over the pipeline's BigQuery
tables — no sign-in, no editing, no server at all. It's a fully static site: `index.html`
fetches `web/data/dashboard.json`, a pre-baked file built by
`python -m dynasty_prospects.export_dashboard_data` from `dim_prospect` and the fact tables
(see that module's docstring for how it joins them — there's no shared `prospect_id` across
tables, so it matches on normalized player name and flags genuinely ambiguous name collisions
rather than silently guessing).

**Where it lives:** `https://nashstallings.github.io/dynasty-prospects/` once Pages is enabled
below — a predictable URL from the start, unlike a Cloud Run service URL.

### Deploy it

**One-time, in the repo's GitHub settings:** Settings → Pages → Build and deployment → Source →
**GitHub Actions**. That's the only manual step; everything else is `.github/workflows/deploy.yml`
(`actions/deploy-pages`, GitHub's own keyless Pages deployment — no GCP identity needed to
publish the site itself).

**For the scheduled data refresh** (below), which does need BigQuery access, one script from
[Cloud Shell](https://shell.cloud.google.com):

```bash
./infra/setup-github-oidc.sh  # lets Actions touch BigQuery without storing a key
```

Then add these under **Settings → Secrets and variables → Actions**:

| Type | Name | Value |
| --- | --- | --- |
| Variable | `GCP_WORKLOAD_IDENTITY_PROVIDER` | printed by `setup-github-oidc.sh` |
| Variable | `GCP_DEPLOY_SERVICE_ACCOUNT` | printed by `setup-github-oidc.sh` |
| Secret | `CFBD_API_KEY` | your [collegefootballdata.com](https://collegefootballdata.com/key) key |

Push to `main` and the site publishes (`.github/workflows/deploy.yml`). GitHub Pages is free for
a public repo.

### Keeping the data fresh

`.github/workflows/refresh.yml` runs weekly (Monday 13:00 UTC, plus manual dispatch): it
re-runs the CFBD pipeline, writes BigQuery, rebuilds `web/data/dashboard.json`, sanity-checks
the result (`check_dashboard.py` — refuses an empty or suspiciously shrunk pull), and if
anything changed, commits and triggers a republish. Weekly rather than daily, unlike
`nfl-2026-projections`' nflverse refresh — recruiting/stats/talent data doesn't turn over
day-to-day the way NFL rosters do.

Manually uploaded scouting snapshots (see below) are untouched by this — the pipeline
deliberately excludes `fact_scouting_rankings` from its routine write.

### Run it locally anyway

```bash
python -m dynasty_prospects.export_dashboard_data   # needs `gcloud auth application-default login`
python -m http.server --directory web 8000           # http://127.0.0.1:8000
```

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
- Player identity isn't unified across CFBD endpoints and manual scouting CSVs. `dim_prospect.prospect_id` is built from name + current team (`matching.py`). The other fact tables carry no `prospect_id` of their own, so `export_dashboard_data.py` matches them back by normalized name alone (not name + school — a transfer's older stats shouldn't get silently dropped just because the school changed). Two different people who happen to share a normalized name at the same point in time (same recruiting class, same combine year, etc.) get flagged `ambiguous_match: true` in the dashboard rather than silently merged — check those by hand.
