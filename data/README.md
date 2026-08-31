# data/

`dashboard.json` lives here once it's been built — it isn't seeded in this repo, since a
placeholder would mean shipping made-up stats under real players' names. It's created by:

```bash
python -m dynasty_prospects.export_dashboard_data
```

(needs `gcloud auth application-default login` against the `ff-python-api` project), or by the
first run of `.github/workflows/refresh.yml`, which commits it going forward. See the "The
dashboard" section of the root README for the full picture.

Until it exists, `dynasty_prospects.server` still runs — it logs a warning and `/data/dashboard.json`
404s, which the frontend shows as a friendly "failed to load" message rather than crashing.
