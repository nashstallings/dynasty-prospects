#!/usr/bin/env bash
# Deploy the dashboard to Cloud Run.
#
# Run from Cloud Shell, or anywhere gcloud is authenticated. Expects
# ./infra/bootstrap.sh to have run first -- it checks for what that creates
# rather than creating it, so this path and the GitHub Actions one cannot drift.
#
#   ./infra/deploy.sh
#
# No sign-in gate to check here, unlike nfl-2026-projections: this dashboard
# is fully public and read-only, so there's no unsafe-exposure case to refuse.

set -euo pipefail

PROJECT="${PROJECT:-ff-python-api}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-dynasty-prospects}"
RUNTIME_SA="${RUNTIME_SA:-dynasty-prospects-run}"

SA_EMAIL="${RUNTIME_SA}@${PROJECT}.iam.gserviceaccount.com"

echo "project ${PROJECT} · region ${REGION} · service ${SERVICE}"

if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT}" >/dev/null 2>&1; then
  echo "missing the ${SA_EMAIL} service account -- run ./infra/bootstrap.sh first" >&2
  exit 1
fi

gcloud run deploy "${SERVICE}" \
  --project="${PROJECT}" \
  --region="${REGION}" \
  --source=. \
  --service-account="${SA_EMAIL}" \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=2 \
  --memory=512Mi \
  --quiet

URL="$(gcloud run services describe "${SERVICE}" --project="${PROJECT}" --region="${REGION}" --format='value(status.url)')"

# A green deploy only means the revision was accepted. This proves it boots.
echo "  waiting for ${URL}/api/healthz"
for _ in $(seq 1 30); do
  if curl -fsS "${URL}/api/healthz" >/dev/null 2>&1; then
    echo "  healthy"
    break
  fi
  sleep 2
done

echo
echo "Deployed: ${URL}"
