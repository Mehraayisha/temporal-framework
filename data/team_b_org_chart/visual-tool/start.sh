#!/bin/bash
# Start the Privacy Firewall Visual Demo Tool

echo "🛡️ Privacy Firewall Visual Demo Tool"
echo "===================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup first:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if API is running
echo "Checking if Privacy Firewall API is running..."
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "✅ API is running on port 8000"
else
    echo "❌ API not running! Start it first:"
    echo "   cd .."
    echo "   python -m uvicorn api.rest_api:app --reload --port 8000"
    echo ""
    echo "Press Enter after starting the API, or Ctrl+C to cancel..."
    read
fi

# Start Streamlit
echo "🚀 Starting visual demo tool..."
echo "Open your browser to: http://localhost:8501"
echo ""
streamlit run app.py