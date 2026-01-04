"""
Uvicorn server launcher for AI Pull-Up Coach backend.

This script starts the FastAPI application using Uvicorn ASGI server.
It displays startup information and available command-line options.

Usage:
    python run.py [--mode debug|debug_no_save|non_debug]
"""

import uvicorn
from main import app
from config import config

if __name__ == "__main__":
    # Print usage information
    print("\n" + "="*60)
    print("🏋️  AI Pull-Up Coach Backend")
    print("="*60)
    print(f"Debug Mode: {config.mode_description}")
    print("\nAvailable modes:")
    print("  python run.py --mode debug        # Debug with frame saving")
    print("  python run.py --mode debug_no_save  # Debug without frame saving") 
    print("  python run.py --mode non_debug      # Minimal logging only")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)