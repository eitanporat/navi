#!/bin/bash

# NAVI Startup Script
# Kills existing processes and starts both web UI and Telegram bot using new package structure

echo "🚀 Starting NAVI System..."
echo "================================"

# WARNING about GCE deployment
echo "⚠️  WARNING: If NAVI is deployed on GCE, do NOT run locally!"
echo "   GCE deployment: https://34-56-132-229.nip.io"
echo "   Running both will cause duplicate Telegram bot responses!"
echo ""
read -p "Continue starting local NAVI? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted to avoid duplicate bots"
    exit 1
fi

# Kill existing processes
echo "🔄 Stopping existing processes..."
lsof -ti:4999 | xargs kill -9 2>/dev/null || true
pkill -f "telegram_bot.py" 2>/dev/null || true
pkill -f "web_ui.py" 2>/dev/null || true
pkill -f "run_web.py" 2>/dev/null || true
pkill -f "run_telegram.py" 2>/dev/null || true
pkill -f "run_all.py" 2>/dev/null || true
sleep 2

echo "✅ Existing processes stopped"

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source navi_venv/bin/activate

# Start using the Python entry point
echo "🚀 Starting NAVI services..."
python run_all.py

echo "✅ NAVI startup script completed"