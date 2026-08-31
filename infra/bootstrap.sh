#!/usr/bin/env bash
# One-time Google Cloud setup. Everything a deploy assumes already exists.
#
# Run once, from anywhere gcloud is authenticated -- Cloud Shell is easiest.
# Safe to re-run: every step is skipped if it is already done.
#
#   ./infra/bootstrap.sh
#
# Unlike nfl-2026-projections, there's no BigQuery table to create here --
# the dynasty_prospects dataset and its tables already exist, written by the
# pipeline (see src/dynasty_prospects/pipeline.py / notebooks/colab_runner.ipynb).
# This just enables the APIs a deploy needs and creates the service account
# the Cloud Run SERVICE runs as. That account gets no BigQuery role at all:
# the running service is a static page plus a pre-baked JSON file and never
# calls BigQuery -- only the scheduled refresh workflow does, as the
# deployer service account (see setup-github-oidc.sh).

set -euo pipefail

PROJECT="${PROJECT:-ff-python-api}"
RUNTIME_SA="${RUNTIME_SA:-dynasty-prospects-run}"

SA_EMAIL="${RUNTIME_SA}@${PROJECT}.iam.gserviceaccount.com"

echo "project ${PROJECT}"

# artifactregistry is needed because `gcloud run deploy --source` builds an
# image and pushes it there; without it the first deploy fails during the
# build rather than at validation.
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  bigquery.googleapis.com \
  --project="${PROJECT}" --quiet

if gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT}" >/dev/null 2>&1; then
  echo "  runtime service account exists"
else
  gcloud iam service-accounts create "${RUNTIME_SA}" \
    --project="${PROJECT}" \
    --display-name="Dynasty prospects dashboard (Cloud Run)"
  echo "  runtime service account created"
fi

cat <<EOF

Done. ${SA_EMAIL} exists and needs no extra roles -- the service it runs
only ever reads its own bundled files.

Next: ./infra/setup-github-oidc.sh to let GitHub Actions deploy and refresh
data, or run ./infra/deploy.sh to deploy from here.
EOF
