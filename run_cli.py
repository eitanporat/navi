#!/usr/bin/env python3
"""
NAVI CLI Entry Point
Runs the command-line interface
"""

import sys
import os

# Add the project root to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from navi.interfaces.cli.interface import run_cli_interface
from navi.core.auth import navi_auth


def main():
    """Main CLI entry point"""
    print("🚀 Starting NAVI CLI Interface")
    
    # Initialize authentication
    if not navi_auth.initialize_authentication():
        print("❌ Authentication failed. Exiting.")
        sys.exit(1)
    
    user_email = navi_auth.current_user
    if not user_email:
        print("❌ No authenticated user found. Exiting.")
        sys.exit(1)
    
    print(f"✅ Authenticated as: {user_email}")
    
    # Run the CLI interface
    run_cli_interface(user_email)


if __name__ == "__main__":
    main()