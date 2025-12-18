#!/usr/bin/env python3
"""
Launcher script for Stock Dashboard
Starts the Flask API server required for the dashboard to function
Run this script before accessing the dashboard
"""

import subprocess
import sys
import time
import os

def main():
    print("=" * 60)
    print("Stock Dashboard Launcher")
    print("=" * 60)
    print("\nStarting the Stock API server...")
    print("The API will run on http://localhost:5001")
    print("\nYou can now access the dashboard at:")
    print("  file:///path/to/PersonalWebsite/dashboard.html")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    print()

    try:
        # Start the Flask API server
        subprocess.run([sys.executable, 'stock_api.py'], cwd=os.path.dirname(os.path.abspath(__file__)))
    except KeyboardInterrupt:
        print("\n\nShutting down the API server...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting the API server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
