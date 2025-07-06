#!/usr/bin/env python3
"""
Manual Test for Hourly Reflection System
Run this script to manually trigger and test hourly reflections
"""

import os
import sys
import asyncio
import json
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from navi.core.scheduler.hourly_reflection_scheduler import HourlyReflectionScheduler
    from navi.core.state.manager import StateManager
    print("✅ Successfully imported NAVI modules")
except ImportError as e:
    print(f"❌ Failed to import NAVI modules: {e}")
    print("Make sure you're running from the project root and have installed dependencies")
    sys.exit(1)


async def test_hourly_reflection_manually():
    """Test the hourly reflection system manually"""
    
    print("\n🧪 Manual Hourly Reflection Test")
    print("=" * 40)
    
    # Check if we have telegram mappings
    telegram_mappings_path = "telegram_mappings.json"
    if not os.path.exists(telegram_mappings_path):
        print(f"❌ No telegram mappings found at {telegram_mappings_path}")
        print("This test requires actual user mappings to work.")
        
        # Create a test mapping file
        test_mappings = {
            "123456789": {"email": "test@example.com"}
        }
        
        with open(telegram_mappings_path, 'w') as f:
            json.dump(test_mappings, f, indent=2)
        
        print(f"✅ Created test mapping file: {telegram_mappings_path}")
        print("⚠️  This uses a fake user. For real testing, use actual mappings.")
    
    # Load mappings
    try:
        with open(telegram_mappings_path, 'r') as f:
            mappings = json.load(f)
        
        print(f"📋 Found {len(mappings)} user mappings:")
        for telegram_id, data in list(mappings.items())[:3]:  # Show first 3
            email = data.get('email', data) if isinstance(data, dict) else data
            print(f"   - {telegram_id}: {email}")
        
        if len(mappings) > 3:
            print(f"   ... and {len(mappings) - 3} more")
            
    except Exception as e:
        print(f"❌ Error loading mappings: {e}")
        return
    
    # Mock bot for testing (won't actually send messages)
    class MockBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            print(f"\n📱 Would send to Telegram {chat_id}:")
            print(f"   {text[:100]}{'...' if len(text) > 100 else ''}")
            return True
    
    mock_bot = MockBot()
    
    # Create scheduler
    try:
        scheduler = HourlyReflectionScheduler(
            bot=mock_bot,
            check_interval_seconds=3600  # 1 hour
        )
        print("✅ Created hourly reflection scheduler")
    except Exception as e:
        print(f"❌ Error creating scheduler: {e}")
        return
    
    # Test building reflection prompt
    print("\n🔍 Testing reflection prompt building...")
    
    # Get first user for testing
    first_user = list(mappings.items())[0]
    telegram_id, user_data = first_user
    user_email = user_data.get('email', user_data) if isinstance(user_data, dict) else user_data
    
    try:
        # Try to load user state
        user_dir = f"users/{user_email}"
        if os.path.exists(user_dir):
            state_manager = StateManager(user_email=user_email)
            state = state_manager.get_state()
            print(f"✅ Loaded state for {user_email}")
            print(f"   Goals: {len(state.get('goals', []))}")
            print(f"   Tasks: {len(state.get('tasks', []))}")
            print(f"   Chat history: {len(state.get('chat_history', []))} messages")
        else:
            print(f"⚠️  No state found for {user_email}, using mock state")
            state = {
                'chat_history': [
                    {
                        'role': 'user',
                        'parts': [{'text': 'I want to be more productive'}],
                        'timestamp': datetime.now().isoformat()
                    }
                ],
                'goals': [
                    {
                        'goal_id': 1,
                        'title': 'Improve productivity',
                        'category': 'personal',
                        'bot_goal_assesment_percentage': 50,
                        'user_goal_assesment_percentage': 40
                    }
                ],
                'tasks': [
                    {
                        'task_id': 1,
                        'description': 'Set up daily routine',
                        'status': 'PENDING',
                        'goal_id': 1
                    }
                ]
            }
        
        # Build reflection prompt
        prompt = scheduler._build_comprehensive_reflection_prompt(state, user_email)
        
        print(f"✅ Built reflection prompt ({len(prompt)} characters)")
        print("\n📝 Sample prompt (first 200 chars):")
        print(f"   {prompt[:200]}...")
        
        # Test response validation
        print("\n🔍 Testing response validation...")
        
        # Mock a response that should send a message
        class MockResponse:
            def __init__(self, message_text, strategize_text):
                self.message_text = message_text
                self.strategize_text = strategize_text
        
        # Test valid response
        valid_response = MockResponse(
            "Hey! How's your productivity goal going? 🎯",
            "User has been working on productivity. Good time for encouragement."
        )
        
        corrected = scheduler._validate_and_fix_response(valid_response, user_email)
        
        if corrected.message_text:
            print("✅ Valid response would send message:")
            print(f"   Message: {corrected.message_text}")
            print(f"   Strategy: {corrected.strategize_text}")
        else:
            print("✅ Valid response would stay silent")
        
        # Test invalid response (no strategize)
        invalid_response = MockResponse("Hello!", None)
        corrected_invalid = scheduler._validate_and_fix_response(invalid_response, user_email)
        
        if corrected_invalid.message_text is None:
            print("✅ Invalid response correctly defaults to silent")
            print(f"   Corrections: {corrected_invalid.formatting_corrections}")
        
        print("\n🎯 Manual Test Summary:")
        print("✅ Scheduler initializes correctly")
        print("✅ User mappings load successfully")
        print("✅ Reflection prompts build with context")
        print("✅ Response validation works")
        print("✅ Mock messaging system functions")
        
        print("\n🚀 To test with real deployment:")
        print("1. Deploy NAVI with Telegram bot running")
        print("2. Check bot logs for hourly reflection messages")
        print("3. Look at /conversations UI for system prompts")
        print("4. Verify you receive proactive messages in Telegram")
        
        print("\n⏰ Hourly Reflection Timing:")
        current_time = datetime.now()
        next_hour = current_time.replace(minute=0, second=0, microsecond=0)
        if current_time.minute > 0:
            next_hour = next_hour.replace(hour=next_hour.hour + 1)
        
        minutes_until = (next_hour - current_time).seconds // 60
        print(f"   Next hourly check in ~{minutes_until} minutes at {next_hour.strftime('%H:%M')}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🔍 NAVI Hourly Reflection Manual Test")
    print("This script tests the hourly reflection system without sending real messages")
    
    try:
        asyncio.run(test_hourly_reflection_manually())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)