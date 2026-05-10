#!/bin/bash
# scripts/deploy.sh
# Rebuilds and redeploys backend and frontend to Cloud Run.
# Uses local Docker build for speed (vs gcloud builds submit).
# Run from project root.

set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="asia-southeast1"
INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe arxiv-db --format="value(connectionName)")
REGISTRY="${REGION}-docker.pkg.dev/$PROJECT_ID/arxiv-rag"

echo "Project:           $PROJECT_ID"
echo "Region:            $REGION"
echo "Cloud SQL:         $INSTANCE_CONNECTION_NAME"
echo "Registry:          $REGISTRY"
echo ""

# Sanity: make sure Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running. Start Docker Desktop and retry."
  exit 1
fi

# Sanity: make sure docker is authenticated for Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# ── Build and push backend ────────────────────────────────────────────────────
# --platform linux/amd64 is critical on Apple Silicon Macs.
# Cloud Run runs AMD64; without this flag your image is ARM64 and crashes.
echo "Building backend image..."
docker build --platform linux/amd64 \
  -f docker/Dockerfile.backend \
  -t $REGISTRY/backend:latest .

echo "Pushing backend image..."
docker push $REGISTRY/backend:latest

# ── Build and push frontend ───────────────────────────────────────────────────
echo "Building frontend image..."
docker build --platform linux/amd64 \
  -f docker/Dockerfile.frontend \
  -t $REGISTRY/frontend:latest .

echo "Pushing frontend image..."
docker push $REGISTRY/frontend:latest

# ── Deploy backend ────────────────────────────────────────────────────────────
# Always use 'gcloud run deploy' with FULL settings (not 'update') —
# 'update' resets unspecified settings to defaults, which breaks
# the Cloud SQL connection.
echo "Deploying backend..."
gcloud run deploy arxiv-backend \
  --image=$REGISTRY/backend:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
  --set-env-vars="DB_HOST=/cloudsql/$INSTANCE_CONNECTION_NAME,DB_PORT=5432,DB_USER=arxiv,DB_NAME=arxiv" \
  --set-secrets="DB_PASSWORD=db-password:latest,GEMINI_API_KEY=gemini-api-key:latest" \
  --memory=1Gi \
  --cpu=1 \
  --max-instances=3 \
  --port=8000

# ── Deploy frontend ───────────────────────────────────────────────────────────
BACKEND_URL=$(gcloud run services describe arxiv-backend --region=$REGION --format="value(status.url)")

echo "Deploying frontend (pointing at backend $BACKEND_URL)..."
gcloud run deploy arxiv-frontend \
  --image=$REGISTRY/frontend:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="API_BASE_URL=$BACKEND_URL" \
  --memory=512Mi \
  --cpu=1 \
  --max-instances=2 \
  --port=8501

FRONTEND_URL=$(gcloud run services describe arxiv-frontend --region=$REGION --format="value(status.url)")

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " Deployment complete"
echo "════════════════════════════════════════════════════════════════"
echo " Backend:  $BACKEND_URL"
echo " Frontend: $FRONTEND_URL"
echo "════════════════════════════════════════════════════════════════"
