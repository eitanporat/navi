#!/usr/bin/env python3
"""
NAVI Production Entry Point
Simple entry point for production deployment without process monitoring
"""

import sys
import os
import threading
import time

# Add the project root to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def start_web_service():
    """Start the web service"""
    try:
        from navi.interfaces.web.app import run_web_app
        print("🌐 Starting Web UI service...")
        run_web_app()
    except Exception as e:
        print(f"❌ Error starting web service: {e}")
        sys.exit(1)

def start_telegram_service():
    """Start the Telegram bot service"""
    try:
        from navi.interfaces.telegram.bot import main as telegram_main
        print("🤖 Starting Telegram Bot service...")
        telegram_main()
    except Exception as e:
        print(f"❌ Error starting telegram service: {e}")
        sys.exit(1)

def main():
    """Main entry point for production"""
    print("🚀 Starting NAVI Production Services...")
    
    # Start Telegram bot in a separate thread
    telegram_thread = threading.Thread(target=start_telegram_service, daemon=True)
    telegram_thread.start()
    
    # Give telegram a moment to start
    time.sleep(2)
    
    print("✅ Telegram bot started in background")
    print("🌐 Starting web service on main thread...")
    
    # Start web service on main thread (this will block)
    start_web_service()

if __name__ == "__main__":
    main()