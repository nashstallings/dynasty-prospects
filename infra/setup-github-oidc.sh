#!/usr/bin/env bash
# Let GitHub Actions refresh BigQuery data without storing a service account key.
#
# Creates a Workload Identity pool and provider pinned to this repository, plus
# a service account Actions may impersonate. Run once, from Cloud Shell.
#
# This is BigQuery-only: the dashboard itself deploys to GitHub Pages, which
# has its own built-in, keyless Actions deployment (actions/deploy-pages) and
# needs no GCP identity at all. This identity exists purely so
# .github/workflows/refresh.yml can run the CFBD pipeline (writes) and the
# dashboard export (reads) against BigQuery on a schedule.
#
# Shares the same GCP project (and, if it already exists, the same "github"
# Workload Identity pool) as nfl-2026-projections -- but needs its own
# provider and service account, since a WIF provider's attribute condition is
# pinned to one repository and can't be reused across repos.

set -euo pipefail

PROJECT="${PROJECT:-ff-python-api}"
REPO="${REPO:-nashstallings/dynasty-prospects}"
POOL="${POOL:-github}"
PROVIDER="${PROVIDER:-dynasty-prospects-actions}"
DEPLOYER="${DEPLOYER:-dynasty-prospects-deployer}"
DATASET="${BQ_DATASET:-dynasty_prospects}"

OWNER="${REPO%%/*}"
SA_EMAIL="${DEPLOYER}@${PROJECT}.iam.gserviceaccount.com"
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT}" --format='value(projectNumber)')"

echo "project ${PROJECT} · repo ${REPO}"

gcloud services enable \
  iamcredentials.googleapis.com sts.googleapis.com bigquery.googleapis.com \
  --project="${PROJECT}" --quiet

if ! gcloud iam workload-identity-pools describe "${POOL}" \
  --project="${PROJECT}" --location=global >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "${POOL}" \
    --project="${PROJECT}" --location=global --display-name="GitHub Actions"
else
  echo "  workload identity pool ${POOL} already exists (shared with other repos)"
fi

if ! gcloud iam workload-identity-pools providers describe "${PROVIDER}" \
  --project="${PROJECT}" --location=global --workload-identity-pool="${POOL}" >/dev/null 2>&1; then
  # The attribute condition pins the provider to this repository. Without it,
  # any GitHub repository under this owner could present a token to this pool.
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER}" \
    --project="${PROJECT}" --location=global \
    --workload-identity-pool="${POOL}" \
    --display-name="dynasty-prospects Actions" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition="assertion.repository == '${REPO}'" \
    --issuer-uri="https://token.actions.githubusercontent.com"
fi

if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${DEPLOYER}" \
    --project="${PROJECT}" --display-name="dynasty-prospects refresh (GitHub Actions)"
fi

# jobUser is inherently project-scoped in BigQuery's model (there's no
# per-dataset job-running permission), so it can't be narrowed further.
gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/bigquery.jobUser" \
  --condition=None --quiet >/dev/null
echo "  bigquery.jobUser granted"

# dataEditor scoped to this one dataset, not the project -- the refresh
# workflow's pipeline run and dashboard export have no business touching
# any other dataset.
TMP_POLICY="$(mktemp)"
trap 'rm -f "${TMP_POLICY}"' EXIT
bq --project_id="${PROJECT}" show --format=prettyjson "${PROJECT}:${DATASET}" > "${TMP_POLICY}"
if grep -q "${SA_EMAIL}" "${TMP_POLICY}"; then
  echo "  dataset write access already granted"
else
  python3 - "${TMP_POLICY}" "${SA_EMAIL}" <<'PY'
import json, sys
path, member = sys.argv[1], sys.argv[2]
with open(path) as handle:
    dataset = json.load(handle)
dataset.setdefault("access", []).append({"role": "WRITER", "userByEmail": member})
with open(path, "w") as handle:
    json.dump(dataset, handle)
PY
  bq --project_id="${PROJECT}" update --source "${TMP_POLICY}" "${PROJECT}:${DATASET}"
  echo "  dataset write access granted"
fi

# Narrowed to this one repository: another repo under the same owner, which
# the provider condition would admit if it weren't pinned above, still
# cannot impersonate this service account.
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/attribute.repository/${REPO}" \
  --quiet >/dev/null

cat <<EOF

Done. Add these under Settings → Secrets and variables → Actions → Variables:

  GCP_WORKLOAD_IDENTITY_PROVIDER
    projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/providers/${PROVIDER}

  GCP_DEPLOY_SERVICE_ACCOUNT
    ${SA_EMAIL}

And under Settings → Secrets and variables → Actions → Secrets:

  CFBD_API_KEY    your collegefootballdata.com API key

The refresh workflow (BigQuery) needs all three. Publishing the dashboard
itself is handled separately by GitHub Pages -- see the root README's
"Deploy it" section for that one-time setting.
EOF
