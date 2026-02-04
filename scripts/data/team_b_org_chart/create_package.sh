#!/bin/bash
# Create a clean zip package for distribution
# Excludes virtual environments, logs, cache files, and other unnecessary files

echo "📦 Creating clean Privacy Firewall package..."

PROJECT_DIR="/home/christo/Desktop/Skyber Work/team_b_org_chart"
OUTPUT_DIR="/home/christo/Desktop"
PACKAGE_NAME="privacy_firewall_integration"

cd "$PROJECT_DIR"

# Create the zip file excluding unnecessary files
zip -r "$OUTPUT_DIR/${PACKAGE_NAME}.zip" . \
    -x "*.git*" \
    -x "*__pycache__*" \
    -x "*.venv/*" \
    -x "*venv/*" \
    -x "*.env" \
    -x "*logs/*.log" \
    -x "*logs/audit_*.jsonl" \
    -x "*.pytest_cache*" \
    -x "*neo4j_data/*" \
    -x "*.coverage*" \
    -x "*htmlcov/*" \
    -x "*visual-tool/venv/*" \
    -x "*visual-tool/__pycache__/*" \
    -x "*.pyc" \
    -x "*.pyo" \
    -x "*.egg-info/*"

echo ""
echo "✅ Package created: $OUTPUT_DIR/${PACKAGE_NAME}.zip"

# Show what's included
echo ""
echo "📋 Package contents:"
unzip -l "$OUTPUT_DIR/${PACKAGE_NAME}.zip" | head -20
echo "... (showing first 20 files)"

# Show file size
echo ""
echo "📊 Package size:"
ls -lh "$OUTPUT_DIR/${PACKAGE_NAME}.zip" | awk '{print $5 " - " $9}'

echo ""
echo "🎯 Your friend can now:"
echo "1. Extract: unzip ${PACKAGE_NAME}.zip" 
echo "2. Setup: pip install -r requirements.txt"
echo "3. Run: docker-compose up -d && python data/ingestion.py"
echo "4. Start API: python -m uvicorn api.rest_api:app --port 8000"