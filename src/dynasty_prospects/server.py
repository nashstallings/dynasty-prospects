"""Serves the read-only dashboard: the static page plus the pre-baked dashboard.json.

Fully public, no auth, no writes -- this process never talks to BigQuery.
data/dashboard.json is built ahead of time by export_dashboard_data.py (see
that module and .github/workflows/refresh.yml) and just served as a file.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"
DATA_DIR = ROOT / "data"

app = FastAPI(title="Dynasty Prospects", docs_url=None, redoc_url=None)


@app.middleware("http")
async def revalidate(request, call_next):
    """See nfl-2026-projections/src/projections/server.py's identical middleware
    for why this exists: Starlette's StaticFiles sends no Cache-Control at all,
    so a browser invents its own freshness window and can silently keep serving
    a deploy from before the last refresh. no-cache forces a conditional request
    (a 304 with no body, cheap) instead."""
    response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-cache")
    return response


@app.get("/api/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True, "dashboard_data": (DATA_DIR / "dashboard.json").exists()}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


# Mounted last so /api/* above wins. dashboard.json is served from /data so the
# page works when opened directly off the filesystem too, without the server.
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


def main() -> int:
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not (DATA_DIR / "dashboard.json").exists():
        logger.warning(
            "data/dashboard.json is missing -- run `python -m dynasty_prospects.export_dashboard_data`"
        )
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    logger.info("dashboard on http://%s:%s", host, port)
    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
