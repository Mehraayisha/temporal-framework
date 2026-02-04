#!/usr/bin/env python3
"""
Run the AI Privacy Firewall REST API

This script starts the FastAPI server using Uvicorn.

Usage:
    python run_api.py                  # Development mode with auto-reload
    python run_api.py --production     # Production mode
"""

import sys
import uvicorn

if __name__ == "__main__":
    # Check if production mode
    production = "--production" in sys.argv
    
    if production:
        print("Starting API in PRODUCTION mode...")
        uvicorn.run(
            "api.rest_api:app",
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    else:
        print("Starting API in DEVELOPMENT mode...")
        print("API will be available at: http://localhost:8000")
        print("Interactive docs at: http://localhost:8000/docs")
        print("Alternative docs at: http://localhost:8000/redoc")
        print()
        uvicorn.run(
            "api.rest_api:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
