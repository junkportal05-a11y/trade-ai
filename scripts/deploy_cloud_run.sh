#!/bin/bash
# ==============================================================================
# APEXTRADE AI — One-Click Google Cloud Run Deployment (Linux/macOS)
# ==============================================================================
# Prerequisites:
#   1. Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install
#   2. Run: gcloud auth login && gcloud auth application-default login
#   3. Create a GCP project: gcloud projects create YOUR_PROJECT_ID
#   4. Enable billing on the project
#   5. Set project: gcloud config set project YOUR_PROJECT_ID
# ==============================================================================

set -euo pipefail

echo
echo "=============================================================================="
echo "APEXTRADE AI — Google Cloud Run Deployment"
echo "=============================================================================="
echo

# Check if gcloud is available
if ! command -v gcloud &> /dev/null; then
    echo "ERROR: gcloud CLI not found. Please install Google Cloud SDK first."
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID from config or prompt
PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
if [[ -z "$PROJECT_ID" ]]; then
    read -p "Enter your GCP Project ID: " PROJECT_ID
    if [[ -z "$PROJECT_ID" ]]; then
        echo "ERROR: Project ID is required."
        exit 1
    fi
    gcloud config set project "$PROJECT_ID"
fi

echo
echo "Deploying to project: $PROJECT_ID"
echo "Region: us-central1"
echo "Service: apextrade-backend"
echo

# Deploy to Cloud Run (Free Tier optimized)
gcloud run deploy apextrade-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --set-env-vars ENVIRONMENT=production \
  --timeout 300 \
  --concurrency 80

if [[ $? -ne 0 ]]; then
    echo
    echo "ERROR: Deployment failed. Check the output above for details."
    exit 1
fi

echo
echo "=============================================================================="
echo "DEPLOYMENT SUCCESSFUL!"
echo "=============================================================================="
echo

# Get service URL
SERVICE_URL=$(gcloud run services describe apextrade-backend --region=us-central1 --format="value(status.url)" 2>/dev/null || echo "")

if [[ -n "$SERVICE_URL" ]]; then
    echo "Your backend is now live at:"
    echo "  $SERVICE_URL"
else
    echo "Your backend is now live. Get URL with:"
    echo "  gcloud run services describe apextrade-backend --region=us-central1 --format='value(status.url)'"
fi

echo
echo "Next steps:"
echo "1. Set required environment variables in Cloud Run console:"
echo "   - DATABASE_URL (Supabase/Neon PostgreSQL)"
echo "   - GEMINI_API_KEY (Google AI Studio)"
echo "   - REDIS_URL or UPSTASH_REDIS_URL (Upstash)"
echo "   - SENTRY_DSN (optional, Sentry.io)"
echo "   - JWT_SECRET, FERNET_KEYS, ADMIN_KEY (generate secure values)"
echo "2. Update frontend .env with VITE_API_URL=$SERVICE_URL"
echo "3. Deploy frontend to Vercel/Netlify"
echo