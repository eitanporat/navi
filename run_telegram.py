#!/usr/bin/env python3
"""
NAVI Telegram Bot Entry Point
Runs the Telegram bot interface
"""

import sys
import os

# Add the project root to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from navi.interfaces.telegram.bot import main as telegram_main


def main():
    """Main Telegram bot entry point"""
    print("🚀 Starting NAVI Telegram Bot")
    telegram_main()


if __name__ == "__main__":
    main()