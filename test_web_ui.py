#!/usr/bin/env python3
"""
Test script to run NAVI web UI in debug mode without authentication
This allows easy debugging of the calendar issue
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Run web UI in test mode"""
    # Set test mode environment variables
    os.environ['NAVI_TEST_MODE'] = 'true'
    os.environ['NAVI_TEST_USER_EMAIL'] = 'ethan.porat@gmail.com'  # Use real user email for actual data
    os.environ['FLASK_DEBUG'] = 'true'
    
    print("🧪 Starting NAVI Web UI in TEST MODE")
    print("📧 Test user email: ethan.porat@gmail.com")
    print("🔓 Authentication disabled for debugging")
    print("🌐 Navigate to: http://localhost:4999/calendar")
    print("📝 Check console output for debug information")
    print("-" * 50)
    
    # Import and run the web app
    from navi.interfaces.web.app import run_web_app
    run_web_app()

if __name__ == '__main__':
    main()