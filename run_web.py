#!/usr/bin/env python3
"""
NAVI Web UI Entry Point
Runs the Flask web interface
"""

import sys
import os

# Add the project root to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from navi.interfaces.web.app import run_web_app


def main():
    """Main web UI entry point"""
    print("🚀 Starting NAVI Web UI")
    run_web_app()


if __name__ == "__main__":
    main()