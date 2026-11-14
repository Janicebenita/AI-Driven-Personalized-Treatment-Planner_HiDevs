#!/usr/bin/env bash
# Invoke from the repository root after cloud access and billing are approved.
set -euo pipefail
project_id="${1:?Usage: bash deploy/cloud-run.sh PROJECT_ID [REGION]}"
region="${2:-asia-south1}"
if [[ ! "$project_id" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]]; then
  echo 'Invalid project ID' >&2
  exit 1
fi
gcloud run deploy careweave \
  --project "$project_id" \
  --source . \
  --region "$region" \
  --port 8080 \
  --cpu 2 \
  --memory 2Gi \
  --concurrency 8 \
  --min 0 \
  --max 1 \
  --timeout 3600 \
  --no-allow-unauthenticated \
  --set-env-vars 'GROQ_MODEL=llama-3.3-70b-versatile,HF_HUB_OFFLINE=1' \
  --quiet
