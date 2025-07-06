"""
Test suite for HourlyReflectionScheduler
Tests the automated hourly reflection system that sends proactive AI-generated check-ins
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import TelegramError

from navi.core.scheduler.hourly_reflection_scheduler import HourlyReflectionScheduler
from navi.core.state.manager import StateManager
from navi.core.engine.conversation import NaviResponse


class TestHourlyReflectionScheduler:
    """Test the HourlyReflectionScheduler functionality"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock Telegram bot"""
        bot = Mock(spec=Bot)
        bot.send_message = AsyncMock()
        return bot
    
    @pytest.fixture
    def scheduler(self, mock_bot):
        """Create scheduler instance"""
        return HourlyReflectionScheduler(
            bot=mock_bot,
            check_interval_seconds=10  # Short interval for testing
        )
    
    @pytest.fixture
    def mock_state_manager(self):
        """Create mock state manager"""
        sm = Mock(spec=StateManager)
        sm.get_state.return_value = {
            'chat_history': [
                {
                    'role': 'user',
                    'parts': [{'text': 'I want to exercise more'}],
                    'timestamp': '2025-07-06T10:00:00'
                }
            ],
            'goals': [
                {
                    'goal_id': 1,
                    'title': 'Exercise regularly',
                    'category': 'health',
                    'bot_goal_assesment_percentage': 30,
                    'user_goal_assesment_percentage': 25
                }
            ],
            'tasks': [
                {
                    'task_id': 1,
                    'description': 'Go to gym',
                    'status': 'PENDING',
                    'goal_id': 1,
                    'due_date': '2025-07-07'
                }
            ]
        }
        sm.save_state = Mock()
        return sm
    
    @pytest.fixture
    def mock_telegram_mappings(self, tmp_path):
        """Create mock telegram mappings file"""
        mappings_file = tmp_path / "telegram_mappings.json"
        mappings_data = {
            "123456789": {"email": "test@example.com"},
            "987654321": {"email": "user2@example.com"}
        }
        mappings_file.write_text(json.dumps(mappings_data))
        return str(mappings_file)
    
    @pytest.fixture
    def mock_conversation_engine(self):
        """Create mock conversation engine"""
        engine = Mock()
        engine.save_state = Mock()
        return engine
    
    def test_scheduler_initialization(self, mock_bot):
        """Test scheduler initializes correctly"""
        scheduler = HourlyReflectionScheduler(mock_bot, check_interval_seconds=3600)
        
        assert scheduler.bot == mock_bot
        assert scheduler.check_interval == 3600
        assert not scheduler.running
        assert scheduler._task is None
    
    @pytest.mark.asyncio
    async def test_start_stop_scheduler(self, scheduler):
        """Test starting and stopping the scheduler"""
        # Test start
        await scheduler.start()
        assert scheduler.running is True
        assert scheduler._task is not None
        
        # Test stop
        await scheduler.stop()
        assert scheduler.running is False
    
    @pytest.mark.asyncio
    async def test_scheduler_loop_error_handling(self, scheduler):
        """Test scheduler handles errors gracefully"""
        with patch.object(scheduler, '_run_hourly_reflections', side_effect=Exception("Test error")):
            scheduler.running = True
            
            # This should not raise an exception
            await scheduler._run_scheduler()
    
    @pytest.mark.asyncio
    async def test_load_telegram_mappings(self, scheduler, mock_telegram_mappings):
        """Test loading telegram mappings"""
        with patch.object(scheduler, 'telegram_mappings_path', mock_telegram_mappings):
            mappings = scheduler._load_telegram_mappings()
            
            assert len(mappings) == 2
            assert mappings["123456789"] == "test@example.com"
            assert mappings["987654321"] == "user2@example.com"
    
    @pytest.mark.asyncio
    async def test_load_telegram_mappings_file_not_found(self, scheduler):
        """Test handling missing telegram mappings file"""
        with patch.object(scheduler, 'telegram_mappings_path', '/nonexistent/file.json'):
            mappings = scheduler._load_telegram_mappings()
            assert mappings == {}
    
    @pytest.mark.asyncio
    @patch('navi.core.scheduler.hourly_reflection_scheduler.StateManager')
    @patch('navi.core.scheduler.hourly_reflection_scheduler.NaviConversationEngine')
    async def test_process_user_reflection_sends_message(self, mock_engine_class, mock_sm_class, scheduler, mock_state_manager, mock_conversation_engine):
        """Test reflection that results in sending a proactive message"""
        # Setup mocks
        mock_sm_class.return_value = mock_state_manager
        mock_engine_class.return_value = mock_conversation_engine
        
        # Mock AI response that decides to send a message
        ai_response = Mock()
        ai_response.tool_executions = []
        
        corrected_response = Mock()
        corrected_response.message_text = "Hey! How's your exercise goal going? Ready to hit the gym today?"
        corrected_response.strategize_text = "User mentioned wanting to exercise more. Task is pending. Good time for encouragement."
        corrected_response.formatting_corrections = []
        
        mock_conversation_engine.process_message = AsyncMock(return_value=ai_response)
        
        with patch.object(scheduler, '_validate_and_fix_response', return_value=corrected_response):
            with patch.object(scheduler, '_send_proactive_message') as mock_send:
                with patch.object(scheduler, '_add_to_chat_history') as mock_add_history:
                    with patch.object(scheduler, '_log_reflection') as mock_log:
                        await scheduler._process_user_reflection("123456789", "test@example.com")
                        
                        # Verify message was sent
                        mock_send.assert_called_once_with(
                            "123456789", 
                            "test@example.com", 
                            "Hey! How's your exercise goal going? Ready to hit the gym today?"
                        )
                        
                        # Verify chat history was updated (both prompt and response)
                        assert mock_add_history.call_count == 2
                        
                        # Verify reflection was logged
                        mock_log.assert_called_once()
                        log_call = mock_log.call_args[0][1]
                        assert log_call['action_taken'] == 'message_sent'
                        assert log_call['message_content'] == corrected_response.message_text
    
    @pytest.mark.asyncio
    @patch('navi.core.scheduler.hourly_reflection_scheduler.StateManager')
    @patch('navi.core.scheduler.hourly_reflection_scheduler.NaviConversationEngine')
    async def test_process_user_reflection_silent(self, mock_engine_class, mock_sm_class, scheduler, mock_state_manager, mock_conversation_engine):
        """Test reflection that results in silent reflection (no message sent)"""
        # Setup mocks
        mock_sm_class.return_value = mock_state_manager
        mock_engine_class.return_value = mock_conversation_engine
        
        # Mock AI response that decides to stay silent
        ai_response = Mock()
        ai_response.tool_executions = []
        
        corrected_response = Mock()
        corrected_response.message_text = None  # No message to send
        corrected_response.strategize_text = "User is making good progress. Last interaction was recent. Better to wait."
        corrected_response.formatting_corrections = []
        
        mock_conversation_engine.process_message = AsyncMock(return_value=ai_response)
        
        with patch.object(scheduler, '_validate_and_fix_response', return_value=corrected_response):
            with patch.object(scheduler, '_send_proactive_message') as mock_send:
                with patch.object(scheduler, '_add_to_chat_history') as mock_add_history:
                    with patch.object(scheduler, '_log_reflection') as mock_log:
                        await scheduler._process_user_reflection("123456789", "test@example.com")
                        
                        # Verify no message was sent
                        mock_send.assert_not_called()
                        
                        # Verify chat history was still updated (prompt and strategize thoughts)
                        assert mock_add_history.call_count == 2
                        
                        # Verify reflection was logged
                        mock_log.assert_called_once()
                        log_call = mock_log.call_args[0][1]
                        assert log_call['action_taken'] == 'silent_reflection'
                        assert log_call['message_content'] is None
    
    @pytest.mark.asyncio
    async def test_send_proactive_message_success(self, scheduler, mock_bot):
        """Test successful sending of proactive message"""
        message = "Hey! How's your goal progress?"
        
        await scheduler._send_proactive_message("123456789", "test@example.com", message)
        
        mock_bot.send_message.assert_called_once_with(
            chat_id="123456789",
            text=message,
            parse_mode='Markdown'
        )
    
    @pytest.mark.asyncio
    async def test_send_proactive_message_telegram_error(self, scheduler, mock_bot):
        """Test handling Telegram API errors"""
        mock_bot.send_message.side_effect = TelegramError("Rate limit exceeded")
        
        # Should not raise exception
        await scheduler._send_proactive_message("123456789", "test@example.com", "Test message")
    
    @pytest.mark.asyncio
    async def test_send_proactive_message_removes_xml_tags(self, scheduler, mock_bot):
        """Test that XML tags are removed from messages"""
        message_with_tags = "<strategize>This is thinking</strategize>Hello! <message>This is the actual message</message>"
        expected_clean = "This is thinkingHello! This is the actual message"
        
        await scheduler._send_proactive_message("123456789", "test@example.com", message_with_tags)
        
        mock_bot.send_message.assert_called_once()
        actual_message = mock_bot.send_message.call_args[1]['text']
        assert actual_message == expected_clean
    
    @pytest.mark.asyncio
    async def test_send_proactive_message_empty_after_cleaning(self, scheduler, mock_bot):
        """Test handling of messages that are empty after XML tag removal"""
        message_only_tags = "<strategize></strategize><message></message>"
        
        await scheduler._send_proactive_message("123456789", "test@example.com", message_only_tags)
        
        # Should not send message if empty after cleaning
        mock_bot.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_proactive_message_too_long(self, scheduler, mock_bot):
        """Test handling of messages that are too long"""
        long_message = "A" * 1001  # Over 1000 character limit
        
        await scheduler._send_proactive_message("123456789", "test@example.com", long_message)
        
        # Should not send message if too long
        mock_bot.send_message.assert_not_called()
    
    def test_validate_and_fix_response_valid(self, scheduler):
        """Test validation of properly formatted response"""
        response = Mock()
        response.message_text = "Hello! How are you doing?"
        response.strategize_text = "User needs encouragement."
        
        corrected = scheduler._validate_and_fix_response(response, "test@example.com")
        
        assert corrected.message_text == "Hello! How are you doing?"
        assert corrected.strategize_text == "User needs encouragement."
        assert corrected.formatting_corrections == []
    
    def test_validate_and_fix_response_no_strategize(self, scheduler):
        """Test handling of response with no strategize content"""
        response = Mock()
        response.message_text = "Hello!"
        response.strategize_text = None
        
        corrected = scheduler._validate_and_fix_response(response, "test@example.com")
        
        assert corrected.message_text is None  # Should default to silent
        assert "No strategize content found" in corrected.formatting_corrections[0]
    
    def test_validate_and_fix_response_message_too_long(self, scheduler):
        """Test handling of overly long messages"""
        response = Mock()
        response.message_text = "A" * 801  # Over 800 character limit
        response.strategize_text = "Some analysis"
        
        corrected = scheduler._validate_and_fix_response(response, "test@example.com")
        
        assert corrected.message_text is None  # Should default to silent
        assert "Message too long" in corrected.formatting_corrections[0]
    
    def test_build_comprehensive_reflection_prompt(self, scheduler, mock_state_manager):
        """Test building of reflection prompt with user context"""
        state = mock_state_manager.get_state()
        
        prompt = scheduler._build_comprehensive_reflection_prompt(state, "test@example.com")
        
        # Verify prompt contains key elements
        assert "HOURLY REFLECTION TIME" in prompt
        assert "test@example.com" in prompt
        assert "Goals: 1" in prompt
        assert "Tasks: 1" in prompt
        assert "Recent messages: 1" in prompt
        assert "DECISION: Should I message this user now" in prompt
    
    def test_add_to_chat_history(self, scheduler, mock_state_manager):
        """Test adding messages to chat history"""
        timestamp = datetime.now().isoformat()
        
        scheduler._add_to_chat_history(
            mock_state_manager, 
            "user", 
            "Test message", 
            timestamp
        )
        
        # Verify the state was accessed
        mock_state_manager.get_state.assert_called_once()
        
        # Verify the structure of the message added
        state = mock_state_manager.get_state()
        assert 'chat_history' in state
    
    def test_log_reflection(self, scheduler, mock_state_manager):
        """Test logging reflection data"""
        reflection_data = {
            "timestamp": datetime.now().isoformat(),
            "ai_analysis": "User is doing well",
            "action_taken": "message_sent",
            "message_content": "Great job!",
            "tool_executions": ["list_tasks"],
            "formatting_corrections": []
        }
        
        scheduler._log_reflection(mock_state_manager, reflection_data)
        
        # Verify state was accessed and saved
        mock_state_manager.get_state.assert_called_once()
        mock_state_manager.save_state.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('navi.core.scheduler.hourly_reflection_scheduler.StateManager')
    @patch('navi.core.scheduler.hourly_reflection_scheduler.NaviConversationEngine')
    async def test_run_hourly_reflections_multiple_users(self, mock_engine_class, mock_sm_class, scheduler, mock_telegram_mappings):
        """Test running reflections for multiple users"""
        with patch.object(scheduler, 'telegram_mappings_path', mock_telegram_mappings):
            with patch.object(scheduler, '_process_user_reflection') as mock_process:
                await scheduler._run_hourly_reflections()
                
                # Should process both users
                assert mock_process.call_count == 2
                
                # Verify correct parameters
                calls = mock_process.call_args_list
                assert ("123456789", "test@example.com") in [call[0] for call in calls]
                assert ("987654321", "user2@example.com") in [call[0] for call in calls]
    
    @pytest.mark.asyncio
    async def test_trigger_reflection_now_user_exists(self, scheduler, mock_telegram_mappings):
        """Test manually triggering reflection for specific user"""
        with patch.object(scheduler, 'telegram_mappings_path', mock_telegram_mappings):
            with patch.object(scheduler, '_process_user_reflection') as mock_process:
                await scheduler.trigger_reflection_now("test@example.com")
                
                # Should process the specific user
                mock_process.assert_called_once_with("123456789", "test@example.com")
    
    @pytest.mark.asyncio
    async def test_trigger_reflection_now_user_not_found(self, scheduler, mock_telegram_mappings):
        """Test manually triggering reflection for non-existent user"""
        with patch.object(scheduler, 'telegram_mappings_path', mock_telegram_mappings):
            with patch.object(scheduler, '_process_user_reflection') as mock_process:
                await scheduler.trigger_reflection_now("nonexistent@example.com")
                
                # Should not process any user
                mock_process.assert_not_called()


@pytest.mark.integration
class TestHourlyReflectionIntegration:
    """Integration tests for the hourly reflection system"""
    
    @pytest.mark.asyncio
    async def test_full_reflection_cycle(self):
        """Test a complete reflection cycle end-to-end"""
        # This would be a more complex test that uses real components
        # For now, we'll simulate the key integration points
        
        # Create real scheduler with mock bot
        mock_bot = Mock(spec=Bot)
        mock_bot.send_message = AsyncMock()
        
        scheduler = HourlyReflectionScheduler(mock_bot, check_interval_seconds=1)
        
        # Mock the file system components
        with patch.object(scheduler, '_load_telegram_mappings') as mock_load:
            mock_load.return_value = {"123": "test@example.com"}
            
            with patch.object(scheduler, '_process_user_reflection') as mock_process:
                # Start and run one cycle
                await scheduler.start()
                await asyncio.sleep(1.1)  # Wait for one cycle
                await scheduler.stop()
                
                # Verify it attempted to process users
                mock_process.assert_called()


if __name__ == "__main__":
    # Run with: python -m pytest tests/unit/test_core/test_hourly_reflection_scheduler.py -v
    pytest.main([__file__, "-v"])