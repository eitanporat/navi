#!/bin/bash

echo "🛑 Killing all NAVI processes..."

# Kill web UI processes
echo "   Stopping Web UI processes..."
lsof -ti:4999 | xargs kill -9 2>/dev/null
pkill -f "run_web.py" 2>/dev/null
pkill -f "web_ui.py" 2>/dev/null

# Kill Telegram bot processes  
echo "   Stopping Telegram Bot processes..."
pkill -f "run_telegram.py" 2>/dev/null
pkill -f "telegram_bot.py" 2>/dev/null

# Kill any run_all.py processes
echo "   Stopping run_all.py processes..."
pkill -f "run_all.py" 2>/dev/null

# Kill any Python processes that might be NAVI related
echo "   Final cleanup..."
ps aux | grep -E "(navi|NAVI)" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null

echo "✅ All NAVI processes killed"
echo "💡 You can now restart with: python run_all.py"