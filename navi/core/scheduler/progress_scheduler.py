"""
Progress Tracker Scheduler
Monitors progress trackers and sends notifications when check-in times are reached
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Callable
from telegram import Bot
from telegram.error import TelegramError

from ..state.manager import StateManager
from ..tools.utilities import update_progress_tracker, list_progress_trackers
from ..tools.tasks import _find_task_by_id
from ..tools.goals import _find_goal_by_id

logger = logging.getLogger(__name__)


class ProgressTrackerScheduler:
    """Handles scheduling and notifications for progress trackers"""
    
    def __init__(self, bot: Bot, check_interval_seconds: int = 300):
        """
        Initialize the scheduler
        
        Args:
            bot: Telegram bot instance for sending notifications
            check_interval_seconds: How often to check for due trackers (default 5 minutes)
        """
        self.bot = bot
        self.check_interval = check_interval_seconds
        self.running = False
        self._task = None
        self.telegram_mappings_path = os.path.join(
            os.path.dirname(__file__), '..', '..', '..', 'telegram_mappings.json'
        )
        
    async def start(self):
        """Start the scheduler background task"""
        if self.running:
            logger.warning("Scheduler already running")
            return
            
        self.running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(f"Progress tracker scheduler started (checking every {self.check_interval}s)")
        
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Progress tracker scheduler stopped")
        
    async def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                await self._check_all_users()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self.check_interval)
                
    async def _check_all_users(self):
        """Check progress trackers for all users"""
        try:
            # Load telegram mappings to get user emails
            telegram_mappings = self._load_telegram_mappings()
            
            for telegram_id, user_email in telegram_mappings.items():
                try:
                    await self._check_user_trackers(telegram_id, user_email)
                except Exception as e:
                    logger.error(f"Error checking trackers for user {user_email}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in check_all_users: {e}")
            
    async def _check_user_trackers(self, telegram_id: str, user_email: str):
        """Check and process trackers for a specific user"""
        try:
            # Get user's state
            state_manager = StateManager(user_email=user_email)
            state = state_manager.get_state()
            
            # Get all progress trackers
            trackers = state.get('progress_trackers', [])
            current_time = datetime.now()
            
            for tracker in trackers:
                if tracker.get('status') == 'PENDING':
                    # Parse check-in time
                    check_in_time = self._parse_datetime(tracker.get('check_in_time', ''))
                    
                    if check_in_time and current_time >= check_in_time:
                        # Time to send notification!
                        await self._send_progress_notification(
                            telegram_id, user_email, tracker, state_manager
                        )
                        
                        # Update tracker status
                        update_progress_tracker(
                            state_manager, 
                            tracker['tracker_id'], 
                            'status', 
                            'NOTIFIED'
                        )
                        state_manager.save_state()
                        
        except Exception as e:
            logger.error(f"Error checking user trackers for {user_email}: {e}")
            
    async def _send_progress_notification(self, telegram_id: str, user_email: str, 
                                        tracker: Dict, state_manager: StateManager):
        """Send AI-generated progress check-in notification to user"""
        try:
            # Get task and goal information
            state = state_manager.get_state()
            tasks = state.get('tasks', [])
            goals = state.get('goals', [])
            
            task = _find_task_by_id(tasks, tracker['task_id'])
            if not task:
                logger.warning(f"Task {tracker['task_id']} not found for tracker {tracker['tracker_id']}")
                return
                
            # Use AI to generate natural check-in message
            from ..engine.conversation import NaviConversationEngine
            
            # Create conversation engine for this user
            engine = NaviConversationEngine(state_manager)
            
            # Build context for the AI check-in
            task_description = task.get('description', 'Unknown task')
            task_status = task.get('status', 'PENDING')
            check_in_time = tracker.get('check_in_time')
            
            # Get goal context
            goal_title = ""
            if task.get('goal_id'):
                goal = _find_goal_by_id(goals, task['goal_id'])
                goal_title = goal['title'] if goal else ""
            
            # Create a clear SYSTEM-triggered check-in prompt
            check_in_prompt = f"""**SYSTEM NOTIFICATION: AUTOMATED PROGRESS TRACKER TRIGGERED**

This is an AUTOMATED SYSTEM-GENERATED progress check-in that has reached its scheduled time. This is NOT a user request.

**SCHEDULED CHECK-IN DETAILS:**
- Task: "{task_description}" (Status: {task_status})
- Scheduled Time: {check_in_time} 
- Current Time: NOW (check-in time has arrived)
{f'- Associated Goal: {goal_title}' if goal_title else ''}

**SYSTEM INSTRUCTION:** You must now initiate a proactive daily check-in conversation. The user did NOT ask for this - the system is automatically triggering it because the scheduled time has arrived.

**ACTION REQUIRED:** Initiate a comprehensive GTD daily check-in following these steps:
1. Use display_goals_with_progress(), list_tasks(), and list_events() to gather full context
2. Begin the conversation naturally - acknowledge this is the scheduled check-in time
3. Follow the 4-phase GTD structure: Capture & Process, Organize & Update, Reflect & Learn, Plan & Commit
4. Be encouraging, collaborative, and data-driven
5. End with tomorrow's planning and schedule the next 3 daily check-ups automatically

**IMPORTANT:** The user is NOT requesting a check-in - YOU are initiating it because the scheduled time has arrived."""

            # Add system prompt to chat history with proper formatting
            self._add_to_chat_history(state_manager,
                role="system",
                content=f"<system_prompt>\n[SYSTEM: Progress Tracker Check-In]\n{check_in_prompt}\n</system_prompt>",
                timestamp=datetime.now().isoformat()
            )
            
            # Generate AI response
            response = await engine.process_message(check_in_prompt)
            
            # Add AI response to chat history with proper tags
            if response.strategize_text or response.message_text:
                full_response = ""
                if response.strategize_text:
                    full_response += f"<strategize>{response.strategize_text}</strategize>\n"
                if response.message_text:
                    full_response += f"<message>{response.message_text}</message>"
                
                self._add_to_chat_history(state_manager,
                    role="model",
                    content=full_response,
                    timestamp=datetime.now().isoformat()
                )
            
            # Extract the message text (remove any XML tags)
            if response.message_text:
                message = response.message_text
                # Clean up any XML tags that might remain
                import re
                message = re.sub(r'<[^>]+>', '', message).strip()
            else:
                # Fallback message if AI fails
                message = f"🌟 Hey! Just checking in on your task: {task_description}\n\nHow's it going? I'm here to help if you need to adjust anything or talk through any obstacles!"
            
            # Send the natural AI-generated message
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode='Markdown'
            )
            
            # Save the conversation state after AI interaction
            engine.save_state()
            
            logger.info(f"Sent AI-generated progress notification to {user_email} for task {task['task_id']}")
            
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message to {telegram_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending progress notification: {e}")
            # Fallback to simple message if AI fails
            try:
                fallback_message = f"🌟 Hey! Just checking in on your task: {task.get('description', 'your task')}\n\nHow's it going? I'm here to help!"
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text=fallback_message
                )
                logger.info(f"Sent fallback notification to {user_email}")
            except Exception as fallback_error:
                logger.error(f"Even fallback notification failed: {fallback_error}")
            
    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse datetime string to datetime object"""
        if not datetime_str:
            return None
            
        # Try multiple date formats
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%y %H:%M",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
                
        logger.warning(f"Could not parse datetime: {datetime_str}")
        return None
    
    def _add_to_chat_history(self, state_manager: StateManager, role: str, content: str, timestamp: str):
        """Add a message to chat history for UI display"""
        try:
            state = state_manager.get_state()
            
            # Initialize chat_history if not exists
            if 'chat_history' not in state:
                state['chat_history'] = []
            
            # Create message in the same format as regular conversations
            message = {
                'role': role,
                'parts': [{'text': content}],
                'timestamp': timestamp
            }
            
            state['chat_history'].append(message)
            
            # Don't save here - let the engine save after all updates
            
        except Exception as e:
            logger.error(f"Error adding to chat history: {e}")
        
    def _load_telegram_mappings(self) -> Dict[str, str]:
        """Load telegram ID to email mappings"""
        try:
            import json
            with open(self.telegram_mappings_path, 'r') as f:
                mappings = json.load(f)
                
                # Handle new mapping format: {telegram_id: {email: "...", ...}}
                result = {}
                for tid, data in mappings.items():
                    if isinstance(data, dict) and 'email' in data:
                        result[tid] = data['email']
                    elif isinstance(data, str):
                        # Handle old format: {telegram_id: "email"}
                        result[tid] = data
                        
                return result
        except FileNotFoundError:
            logger.warning("No telegram mappings file found")
            return {}
        except Exception as e:
            logger.error(f"Error loading telegram mappings: {e}")
            return {}
            
    async def check_user_now(self, user_email: str):
        """Manually trigger check for a specific user (for testing)"""
        telegram_mappings = self._load_telegram_mappings()
        
        # Find telegram ID for user
        telegram_id = None
        for tid, email in telegram_mappings.items():
            if email == user_email:
                telegram_id = tid
                break
                
        if telegram_id:
            await self._check_user_trackers(telegram_id, user_email)
            logger.info(f"Manual check completed for {user_email}")
        else:
            logger.warning(f"No telegram ID found for {user_email}")