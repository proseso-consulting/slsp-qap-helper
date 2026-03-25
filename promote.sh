#!/usr/bin/env bash
# Promote the canary revision to 100% traffic.
# Run after verifying the canary is healthy.
set -euo pipefail

SERVICE="slsp-qap-helper"
REGION="asia-southeast1"
PROJECT="odoo-ocr-487104"

echo "Current traffic:"
gcloud run services describe $SERVICE --region $REGION --project $PROJECT --format="value(status.traffic)"

read -p "Promote latest revision to 100% traffic? [y/N] " confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
    gcloud run services update-traffic $SERVICE --to-latest --region $REGION --project $PROJECT
    echo "Done. Latest revision now serving 100% traffic."
else
    echo "Aborted."
fi
