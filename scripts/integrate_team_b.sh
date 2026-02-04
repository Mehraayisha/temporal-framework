#!/usr/bin/env bash
# Integrate a Team B package (zip or folder) into the Privacy Firewall repo (POSIX)
# Usage: ./integrate_team_b.sh /path/to/team_b_org_chart.zip [--start-docker]

set -euo pipefail

PATH_ARG=${1:-}
START_DOCKER=false
if [ "${2:-}" = "--start-docker" ]; then
  START_DOCKER=true
fi

if [ -z "$PATH_ARG" ]; then
  echo "Usage: $0 /path/to/team_b_org_chart.zip_or_folder [--start-docker]"
  exit 1
fi

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$REPO_ROOT"

TARGET_DIR="$REPO_ROOT/data/team_b_org_chart"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

if [[ "$PATH_ARG" == *.zip ]]; then
  echo "Extracting zip to $TARGET_DIR..."
  unzip -q "$PATH_ARG" -d "$TARGET_DIR"
else
  echo "Copying folder contents to $TARGET_DIR..."
  cp -r "$PATH_ARG"/* "$TARGET_DIR" || true
fi

ORG_DATA_SRC="$TARGET_DIR/org_data.json"
if [ ! -f "$ORG_DATA_SRC" ]; then
  echo "Warning: org_data.json not found in Team B package at $ORG_DATA_SRC"
else
  ORG_DATA_DST="$REPO_ROOT/data/org_data.json"
  if [ -f "$ORG_DATA_DST" ]; then
    BAK="$ORG_DATA_DST.bak.$(date +%Y%m%d%H%M%S)"
    cp "$ORG_DATA_DST" "$BAK"
    echo "Backed up existing org_data.json to $BAK"
  fi
  cp -f "$ORG_DATA_SRC" "$ORG_DATA_DST"
  echo "Copied Team B org_data.json to data/org_data.json"

  if [ -f "data/ingestion.py" ]; then
    echo "Running data/ingestion.py to load Team B org data..."
    python data/ingestion.py
  else
    echo "Warning: data/ingestion.py not found; please load your data manually."
  fi
fi

if [ "$START_DOCKER" = true ]; then
  if command -v docker >/dev/null 2>&1; then
    echo "Starting docker-compose services..."
    docker-compose up -d
  else
    echo "Warning: docker not found. Skipping docker-compose."
  fi
fi

if [ -f "api/rest_api.py" ]; then
  echo "Starting API on port 8000 (background)..."
  nohup python -m uvicorn api.rest_api:app --port 8000 >/dev/null 2>&1 &
  echo "API started (background). Use curl http://localhost:8000/api/v1/health to verify."
else
  echo "Warning: api/rest_api.py not found. Start the API manually when ready."
fi

echo "Team B integration script finished."
