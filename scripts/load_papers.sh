#!/bin/bash
# scripts/load_papers.sh
#
# Runs Phase 2 of the ingestion pipeline end to end:
#   1. Start Cloud SQL (if stopped)
#   2. Wait for it to be RUNNABLE
#   3. Start Cloud SQL Auth Proxy in the background
#   4. Run load_to_cloud.py
#   5. Stop the proxy
#   6. Stop Cloud SQL (if it was stopped at the start)
#
# Run with:
#   ./scripts/load_papers.sh
#
# Set DB_PASSWORD in your environment or .env first.

set -e

PROJECT_ID=$(gcloud config get-value project)
INSTANCE="arxiv-db"
REGION="asia-southeast1"
CONNECTION_NAME="${PROJECT_ID}:${REGION}:${INSTANCE}"

# Check if password is available
if [ -z "$DB_PASSWORD" ]; then
  # Try to load from .env
  if [ -f .env ]; then
    set -a
    source .env
    set +a
  fi
fi

if [ -z "$DB_PASSWORD" ]; then
  echo "Error: DB_PASSWORD not set. Add it to .env or export it."
  exit 1
fi

# Check the initial Cloud SQL state — we'll restore it at the end
INITIAL_STATE=$(gcloud sql instances describe $INSTANCE --format="value(state)")
echo "Initial Cloud SQL state: $INITIAL_STATE"

# Start Cloud SQL if not running
if [ "$INITIAL_STATE" != "RUNNABLE" ]; then
  echo "Starting Cloud SQL..."
  gcloud sql instances patch $INSTANCE --activation-policy=ALWAYS --quiet

  echo "Waiting for Cloud SQL to be ready..."
  for i in {1..30}; do
    STATE=$(gcloud sql instances describe $INSTANCE --format="value(state)")
    if [ "$STATE" = "RUNNABLE" ]; then
      echo "  Cloud SQL is RUNNABLE"
      break
    fi
    echo "  $i: $STATE"
    sleep 5
  done

  if [ "$STATE" != "RUNNABLE" ]; then
    echo "Error: Cloud SQL did not start within 2.5 minutes"
    exit 1
  fi
fi

# Start the proxy in the background
echo "Starting Cloud SQL Auth Proxy..."
cloud-sql-proxy $CONNECTION_NAME &
PROXY_PID=$!
echo "  Proxy PID: $PROXY_PID"

# Give the proxy a moment to bind
sleep 3

# Make sure we always clean up the proxy on exit
cleanup() {
  echo ""
  echo "Cleaning up..."
  if kill -0 $PROXY_PID 2>/dev/null; then
    echo "  Stopping proxy (PID $PROXY_PID)..."
    kill $PROXY_PID
  fi

  # Restore Cloud SQL state
  if [ "$INITIAL_STATE" != "RUNNABLE" ]; then
    echo "  Stopping Cloud SQL (was stopped at start)..."
    gcloud sql instances patch $INSTANCE --activation-policy=NEVER --quiet
  else
    echo "  Leaving Cloud SQL running (was running at start)..."
  fi
}
trap cleanup EXIT

# Run the load
echo ""
echo "Running load script..."
DB_HOST=localhost \
DB_PORT=5432 \
DB_USER=arxiv \
DB_PASSWORD="$DB_PASSWORD" \
DB_NAME=arxiv \
python ingestion/load_to_cloud.py

echo ""
echo "Load complete."
