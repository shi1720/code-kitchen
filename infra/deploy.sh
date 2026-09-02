#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# OfferLoop — one-shot deployment to Google Cloud.
#
#   PROJECT_ID=my-project ./infra/deploy.sh
#
# What it does, in order:
#   1. Enables the required APIs
#   2. Creates the Firestore database (native mode)
#   3. Creates two service accounts:
#        offerloop-run       — the Cloud Run service identity
#        offerloop-scheduler — the identity Cloud Scheduler calls with
#   4. Builds & deploys the container to Cloud Run from source (Cloud Build)
#   5. Creates the hourly Cloud Scheduler job that drives the nudge engine,
#      authenticated with an OIDC token the API verifies
#
# Prereqs: gcloud CLI authenticated with owner/editor on the project.
# Firebase Auth (Google provider) is enabled in the console — see
# docs/DEPLOYMENT.md step 3.
# ---------------------------------------------------------------------------
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID=your-gcp-project}"
REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-offerloop}"
FIREBASE_WEB_CONFIG="${FIREBASE_WEB_CONFIG:-}"

RUN_SA="offerloop-run@${PROJECT_ID}.iam.gserviceaccount.com"
SCHED_SA="offerloop-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud config set project "${PROJECT_ID}"

echo "==> 1/5 Enabling APIs"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  cloudscheduler.googleapis.com \
  aiplatform.googleapis.com \
  identitytoolkit.googleapis.com

echo "==> 2/5 Firestore database"
gcloud firestore databases create --location="${REGION}" 2>/dev/null \
  || echo "    (database already exists)"

echo "==> 3/5 Service accounts & IAM"
gcloud iam service-accounts create offerloop-run \
  --display-name="OfferLoop Cloud Run service" 2>/dev/null || true
gcloud iam service-accounts create offerloop-scheduler \
  --display-name="OfferLoop Cloud Scheduler caller" 2>/dev/null || true

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUN_SA}" --role="roles/datastore.user" --quiet >/dev/null
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUN_SA}" --role="roles/aiplatform.user" --quiet >/dev/null
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUN_SA}" --role="roles/firebaseauth.admin" --quiet >/dev/null

echo "==> 4/5 Deploying to Cloud Run (build from source)"
gcloud run deploy "${SERVICE}" \
  --source . \
  --region "${REGION}" \
  --service-account "${RUN_SA}" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --set-env-vars "OFFERLOOP_APP_MODE=live" \
  --set-env-vars "OFFERLOOP_GCP_PROJECT=${PROJECT_ID}" \
  --set-env-vars "OFFERLOOP_USE_VERTEX=true" \
  --set-env-vars "OFFERLOOP_VERTEX_LOCATION=global" \
  --set-env-vars "OFFERLOOP_SCHEDULER_SERVICE_ACCOUNT=${SCHED_SA}" \
  --set-env-vars "^@^OFFERLOOP_FIREBASE_WEB_CONFIG=${FIREBASE_WEB_CONFIG}"

URL="$(gcloud run services describe "${SERVICE}" --region "${REGION}" --format='value(status.url)')"
echo "    Service live at: ${URL}"

echo "==> 5/5 Cloud Scheduler — hourly nudge scan"
gcloud run services add-iam-policy-binding "${SERVICE}" \
  --region "${REGION}" \
  --member="serviceAccount:${SCHED_SA}" \
  --role="roles/run.invoker" --quiet >/dev/null

gcloud scheduler jobs create http offerloop-nudge-scan \
  --location "${REGION}" \
  --schedule "0 * * * *" \
  --time-zone "Asia/Kolkata" \
  --uri "${URL}/api/tasks/nudge-scan" \
  --http-method POST \
  --oidc-service-account-email "${SCHED_SA}" \
  --oidc-token-audience "${URL}" 2>/dev/null \
  || gcloud scheduler jobs update http offerloop-nudge-scan \
       --location "${REGION}" \
       --schedule "0 * * * *" \
       --uri "${URL}/api/tasks/nudge-scan" \
       --oidc-service-account-email "${SCHED_SA}" \
       --oidc-token-audience "${URL}"

echo
echo "Done. OfferLoop is live at ${URL}"
echo "Next: enable the Google sign-in provider in Firebase Auth (docs/DEPLOYMENT.md)."
