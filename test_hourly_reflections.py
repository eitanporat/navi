#!/usr/bin/env python3
"""
Integration Test for Hourly Reflection System
This script tests the hourly reflection scheduler to verify it works correctly.
"""

import os
import sys
import asyncio
import json
import tempfile
from unittest.mock import Mock, AsyncMock
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from navi.core.scheduler.hourly_reflection_scheduler import HourlyReflectionScheduler
from navi.core.state.manager import StateManager


class TestReflectionSystem:
    """Test the hourly reflection system"""
    
    def __init__(self):
        self.test_results = []
    
    def log_test(self, test_name, passed, details=""):
        """Log test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   {details}")
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
    
    async def test_scheduler_initialization(self):
        """Test that scheduler can be created and configured"""
        try:
            # Create mock bot
            mock_bot = Mock()
            mock_bot.send_message = AsyncMock()
            
            # Create scheduler
            scheduler = HourlyReflectionScheduler(
                bot=mock_bot,
                check_interval_seconds=5  # Short interval for testing
            )
            
            # Verify properties
            assert scheduler.bot == mock_bot
            assert scheduler.check_interval == 5
            assert not scheduler.running
            
            self.log_test("Scheduler Initialization", True, "Scheduler created successfully")
            return scheduler
            
        except Exception as e:
            self.log_test("Scheduler Initialization", False, f"Error: {e}")
            return None
    
    async def test_telegram_mappings_loading(self, scheduler):
        """Test loading telegram user mappings"""
        if not scheduler:
            self.log_test("Telegram Mappings Loading", False, "No scheduler available")
            return
        
        try:
            # Create temporary mappings file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                test_mappings = {
                    "123456789": {"email": "test@example.com"},
                    "987654321": {"email": "user2@example.com"}
                }
                json.dump(test_mappings, f)
                mappings_file = f.name
            
            # Override the mappings path
            scheduler.telegram_mappings_path = mappings_file
            
            # Test loading
            mappings = scheduler._load_telegram_mappings()
            
            # Verify results
            assert len(mappings) == 2
            assert mappings["123456789"] == "test@example.com"
            assert mappings["987654321"] == "user2@example.com"
            
            # Cleanup
            os.unlink(mappings_file)
            
            self.log_test("Telegram Mappings Loading", True, f"Loaded {len(mappings)} user mappings")
            
        except Exception as e:
            self.log_test("Telegram Mappings Loading", False, f"Error: {e}")
    
    async def test_reflection_prompt_building(self, scheduler):
        """Test building reflection prompts with user context"""
        if not scheduler:
            self.log_test("Reflection Prompt Building", False, "No scheduler available")
            return
        
        try:
            # Create test state
            test_state = {
                'chat_history': [
                    {
                        'role': 'user',
                        'parts': [{'text': 'I want to exercise more regularly'}],
                        'timestamp': '2025-07-06T10:00:00'
                    },
                    {
                        'role': 'model',
                        'parts': [{'text': 'Great goal! Let me help you create a plan.'}],
                        'timestamp': '2025-07-06T10:01:00'
                    }
                ],
                'goals': [
                    {
                        'goal_id': 1,
                        'title': 'Exercise 3x per week',
                        'category': 'health',
                        'bot_goal_assesment_percentage': 25,
                        'user_goal_assesment_percentage': 30
                    }
                ],
                'tasks': [
                    {
                        'task_id': 1,
                        'description': 'Go to gym',
                        'status': 'PENDING',
                        'goal_id': 1,
                        'due_date': '2025-07-07'
                    },
                    {
                        'task_id': 2,
                        'description': 'Buy workout clothes',
                        'status': 'COMPLETED',
                        'goal_id': 1
                    }
                ]
            }
            
            # Build prompt
            prompt = scheduler._build_comprehensive_reflection_prompt(test_state, "test@example.com")
            
            # Verify prompt contains expected elements
            required_elements = [
                "HOURLY REFLECTION TIME",
                "test@example.com",
                "Goals: 1",
                "Tasks: 2",
                "Recent messages: 2",
                "DECISION: Should I message this user now"
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in prompt:
                    missing_elements.append(element)
            
            if missing_elements:
                self.log_test("Reflection Prompt Building", False, f"Missing elements: {missing_elements}")
            else:
                self.log_test("Reflection Prompt Building", True, "Prompt contains all required elements")
                print(f"   Prompt length: {len(prompt)} characters")
            
        except Exception as e:
            self.log_test("Reflection Prompt Building", False, f"Error: {e}")
    
    async def test_response_validation(self, scheduler):
        """Test validation and fixing of AI responses"""
        if not scheduler:
            self.log_test("Response Validation", False, "No scheduler available")
            return
        
        try:
            # Test valid response
            valid_response = Mock()
            valid_response.message_text = "Hey! How's your exercise goal going?"
            valid_response.strategize_text = "User is working on fitness. Good time for encouragement."
            
            corrected = scheduler._validate_and_fix_response(valid_response, "test@example.com")
            
            assert corrected.message_text == valid_response.message_text
            assert corrected.strategize_text == valid_response.strategize_text
            assert len(corrected.formatting_corrections) == 0
            
            # Test response with no strategize (should become silent)
            invalid_response = Mock()
            invalid_response.message_text = "Hello!"
            invalid_response.strategize_text = None
            
            corrected_invalid = scheduler._validate_and_fix_response(invalid_response, "test@example.com")
            
            assert corrected_invalid.message_text is None  # Should become silent
            assert len(corrected_invalid.formatting_corrections) > 0
            
            # Test overly long message (should become silent)
            long_response = Mock()
            long_response.message_text = "A" * 801  # Over limit
            long_response.strategize_text = "Some analysis"
            
            corrected_long = scheduler._validate_and_fix_response(long_response, "test@example.com")
            
            assert corrected_long.message_text is None  # Should become silent
            assert any("too long" in correction for correction in corrected_long.formatting_corrections)
            
            self.log_test("Response Validation", True, "All validation scenarios work correctly")
            
        except Exception as e:
            self.log_test("Response Validation", False, f"Error: {e}")
    
    async def test_chat_history_logging(self, scheduler):
        """Test logging to chat history"""
        if not scheduler:
            self.log_test("Chat History Logging", False, "No scheduler available")
            return
        
        try:
            # Create mock state manager
            mock_state = {'chat_history': []}
            mock_sm = Mock()
            mock_sm.get_state.return_value = mock_state
            
            # Test adding to chat history
            timestamp = datetime.now().isoformat()
            scheduler._add_to_chat_history(
                mock_sm,
                "user",
                "[SYSTEM: Hourly Reflection Check] Test reflection prompt",
                timestamp
            )
            
            # Verify state was accessed
            mock_sm.get_state.assert_called_once()
            
            # Test logging reflection
            reflection_data = {
                "timestamp": timestamp,
                "ai_analysis": "User is making progress",
                "action_taken": "message_sent",
                "message_content": "Great job!",
                "tool_executions": ["list_tasks"],
                "formatting_corrections": []
            }
            
            scheduler._log_reflection(mock_sm, reflection_data)
            
            # Verify save was called
            mock_sm.save_state.assert_called_once()
            
            self.log_test("Chat History Logging", True, "Chat history and reflection logging work")
            
        except Exception as e:
            self.log_test("Chat History Logging", False, f"Error: {e}")
    
    async def test_scheduler_start_stop(self, scheduler):
        """Test starting and stopping the scheduler"""
        if not scheduler:
            self.log_test("Scheduler Start/Stop", False, "No scheduler available")
            return
        
        try:
            # Test starting
            await scheduler.start()
            assert scheduler.running is True
            assert scheduler._task is not None
            
            # Let it run briefly
            await asyncio.sleep(0.1)
            
            # Test stopping
            await scheduler.stop()
            assert scheduler.running is False
            
            self.log_test("Scheduler Start/Stop", True, "Scheduler starts and stops correctly")
            
        except Exception as e:
            self.log_test("Scheduler Start/Stop", False, f"Error: {e}")
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🧪 Testing NAVI Hourly Reflection System")
        print("=" * 50)
        
        # Initialize
        scheduler = await self.test_scheduler_initialization()
        
        # Run tests
        await self.test_telegram_mappings_loading(scheduler)
        await self.test_reflection_prompt_building(scheduler)
        await self.test_response_validation(scheduler)
        await self.test_chat_history_logging(scheduler)
        await self.test_scheduler_start_stop(scheduler)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result['passed'])
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "✅" if result['passed'] else "❌"
            print(f"{status} {result['test']}")
        
        print(f"\n🎯 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Hourly reflection system is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the implementation.")
            return False


async def main():
    """Run the test suite"""
    tester = TestReflectionSystem()
    success = await tester.run_all_tests()
    
    print("\n" + "=" * 50)
    print("💡 What This Tests:")
    print("- Scheduler initialization and configuration")
    print("- Loading user mappings from Telegram")
    print("- Building contextual reflection prompts")
    print("- Validating and fixing AI responses")
    print("- Logging to chat history for UI display")
    print("- Starting and stopping the scheduler")
    
    print("\n🚀 To test with real deployment:")
    print("1. Ensure Telegram bot is running")
    print("2. Check logs for 'hourly reflection' messages")
    print("3. Look at /conversations in web UI for system prompts")
    print("4. Verify proactive messages in Telegram")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)