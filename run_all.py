#!/usr/bin/env python3
"""
NAVI All Services Entry Point
Starts both web UI and Telegram bot with proper signal handling
"""

import sys
import os
import subprocess
import signal
import time
import threading
import atexit

# Add the project root to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Global process list for cleanup
RUNNING_PROCESSES = []


def cleanup_existing_processes():
    """Kill existing NAVI processes"""
    print("🔄 Stopping existing processes...")
    
    # Kill processes on port 4999 (web UI)
    try:
        subprocess.run(['lsof', '-ti:4999'], capture_output=True, check=True, text=True)
        subprocess.run(['lsof', '-ti:4999', '|', 'xargs', 'kill', '-9'], shell=True)
        print("   ✅ Stopped existing web UI processes")
    except subprocess.CalledProcessError:
        pass  # No processes running on port 4999
    
    # Kill existing telegram bot processes
    try:
        subprocess.run(['pkill', '-f', 'telegram_bot.py'], check=True)
        print("   ✅ Stopped existing Telegram bot processes")
    except subprocess.CalledProcessError:
        pass  # No telegram bot processes running
    
    # Kill existing run_telegram.py processes
    try:
        subprocess.run(['pkill', '-f', 'run_telegram.py'], check=True)
        print("   ✅ Stopped existing run_telegram.py processes")
    except subprocess.CalledProcessError:
        pass  # No run_telegram.py processes running
    
    time.sleep(2)


def cleanup_processes():
    """Clean up all running processes"""
    global RUNNING_PROCESSES
    
    if not RUNNING_PROCESSES:
        return
    
    print("🛑 Stopping NAVI services...")
    
    for process in RUNNING_PROCESSES[:]:  # Copy list to avoid modification during iteration
        try:
            if process.poll() is None:  # Process is still running
                print(f"   Terminating process {process.pid}...")
                
                # Try graceful termination first
                process.terminate()
                
                # Wait up to 5 seconds for graceful shutdown
                try:
                    process.wait(timeout=5)
                    print(f"   ✅ Process {process.pid} terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown failed
                    print(f"   🔥 Force killing process {process.pid}...")
                    process.kill()
                    process.wait()
                    print(f"   ✅ Process {process.pid} killed")
                
                RUNNING_PROCESSES.remove(process)
        except Exception as e:
            print(f"   ⚠️  Error stopping process {process.pid}: {e}")
    
    # Additional cleanup using system commands
    print("🧹 Final cleanup...")
    try:
        # Kill any remaining processes on port 4999
        subprocess.run(['pkill', '-f', 'run_web.py'], capture_output=True)
        subprocess.run(['pkill', '-f', 'run_telegram.py'], capture_output=True)
        subprocess.run(['lsof', '-ti:4999'], capture_output=True, text=True, check=True)
        subprocess.run(['lsof', '-ti:4999', '|', 'xargs', 'kill', '-9'], shell=True, capture_output=True)
    except:
        pass
    
    print("✅ All NAVI services stopped")


def start_services():
    """Start web UI and Telegram bot services"""
    global RUNNING_PROCESSES
    
    try:
        # Start Web UI
        print("🌐 Starting Web UI on http://localhost:4999...")
        web_process = subprocess.Popen([
            sys.executable, 'run_web.py'
        ], 
        stdout=subprocess.DEVNULL,  # Suppress output to make Ctrl+C work better
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid  # Create new process group
        )
        RUNNING_PROCESSES.append(web_process)
        print(f"   ✅ Web UI started (PID: {web_process.pid})")
        
        # Wait a moment for web UI to start
        time.sleep(3)
        
        # Start Telegram Bot
        print("🤖 Starting Telegram Bot...")
        telegram_process = subprocess.Popen([
            sys.executable, 'run_telegram.py'
        ],
        stdout=subprocess.DEVNULL,  # Suppress output to make Ctrl+C work better
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid  # Create new process group
        )
        RUNNING_PROCESSES.append(telegram_process)
        print(f"   ✅ Telegram Bot started (PID: {telegram_process.pid})")
        
        # Wait a moment for everything to initialize
        time.sleep(2)
        
        print("")
        print("🎉 NAVI System Started Successfully!")
        print("================================")
        print("📱 Web UI: http://localhost:4999")
        print("🤖 Telegram Bot: Running (check your bot)")
        print("")
        print("📋 Next Steps:")
        print("1. Visit http://localhost:4999 in your browser")
        print("2. Login with Google to authenticate")
        print("3. Go to Settings to get your Telegram auth code")
        print("4. Send /start to the Telegram bot and enter your code")
        print("")
        print(f"🔧 Process IDs:")
        print(f"   Web UI: {web_process.pid}")
        print(f"   Telegram Bot: {telegram_process.pid}")
        print("")
        print("💡 Tips for stopping NAVI:")
        print("   • Press Ctrl+C once and wait")
        print("   • If that doesn't work, press Ctrl+C again")
        print("   • Or use: ./kill_navi.sh")
        print("")
        print("🔴 NAVI is running... (Press Ctrl+C to stop)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error starting services: {e}")
        cleanup_processes()
        return False


def signal_handler(sig, frame):
    """Handle Ctrl+C signal for graceful shutdown"""
    print("\n🛑 Received shutdown signal...")
    cleanup_processes()
    sys.exit(0)


def main():
    """Main entry point for all services"""
    print("🚀 Starting NAVI System...")
    print("================================")
    
    # Register cleanup function to run on exit
    atexit.register(cleanup_processes)
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Clean up any existing processes
    cleanup_existing_processes()
    
    # Start services
    success = start_services()
    
    if not success:
        print("❌ Failed to start services")
        sys.exit(1)
    
    # Monitor processes and wait
    try:
        while True:
            # Check if any process has died
            alive_processes = []
            for process in RUNNING_PROCESSES:
                if process.poll() is None:
                    alive_processes.append(process)
                else:
                    print(f"⚠️  Process {process.pid} has terminated unexpectedly")
            
            # Update the running processes list
            RUNNING_PROCESSES[:] = alive_processes
            
            # If all processes died, exit
            if not RUNNING_PROCESSES:
                print("❌ All services have stopped")
                break
            
            time.sleep(1)
    except KeyboardInterrupt:
        # This should be caught by the signal handler, but just in case
        print("\n🛑 Keyboard interrupt received...")
        cleanup_processes()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        cleanup_processes()
        sys.exit(1)


if __name__ == "__main__":
    main()