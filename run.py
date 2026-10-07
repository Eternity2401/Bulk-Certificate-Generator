"""
Application Runner Script.
Allows starting the FastAPI server directly via 'python run.py' from any terminal.
"""
import sys
import os
from pathlib import Path

# Fix Windows console UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Bulk Certificate Generator Backend API...")
    print(f"QR Base URL:      {settings.BASE_URL}")
    print("Dashboard Local:  http://127.0.0.1:8000")
    print("Swagger Docs:     http://127.0.0.1:8000/docs")
    print("=" * 60)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
