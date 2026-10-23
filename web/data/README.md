# web/data/

`dashboard.json` lives here once it's been built — it isn't seeded in this repo, since a
placeholder would mean shipping made-up stats under real players' names. It's created by:

```bash
python -m dynasty_prospects.export_dashboard_data
```

(needs `gcloud auth application-default login` against the `ff-python-api` project), or by the
first run of `.github/workflows/refresh.yml`, which commits it going forward. See the "The
dashboard" section of the root README for the full picture.

It lives inside `web/` rather than a sibling `data/` directory so that `web/` is a fully
self-contained static site: GitHub Pages publishes `web/` as-is, and `index.html`/`app.js`
reference this file with a relative path.
