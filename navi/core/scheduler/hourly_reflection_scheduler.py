"""
Hourly Reflection Scheduler
Sends comprehensive reflection prompts every hour for AI-driven proactive user engagement
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram import Bot
from telegram.error import TelegramError

from ..state.manager import StateManager
from ..engine.conversation import NaviConversationEngine

logger = logging.getLogger(__name__)


class HourlyReflectionScheduler:
    """Handles hourly reflection analysis and optional proactive messaging"""
    
    def __init__(self, bot: Bot, check_interval_seconds: int = 3600):
        """
        Initialize the hourly reflection scheduler
        
        Args:
            bot: Telegram bot instance for sending notifications
            check_interval_seconds: How often to run reflections (default 1 hour)
        """
        self.bot = bot
        self.check_interval = check_interval_seconds
        self.running = False
        self._task = None
        self.telegram_mappings_path = os.path.join(
            os.path.dirname(__file__), '..', '..', '..', 'telegram_mappings.json'
        )
        
    async def start(self):
        """Start the hourly reflection scheduler"""
        if self.running:
            logger.warning("Hourly reflection scheduler already running")
            return
            
        self.running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(f"Hourly reflection scheduler started (checking every {self.check_interval}s)")
        
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Hourly reflection scheduler stopped")
        
    async def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                await self._run_hourly_reflections()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in hourly reflection scheduler loop: {e}")
                await asyncio.sleep(self.check_interval)
                
    async def _run_hourly_reflections(self):
        """Run hourly reflections for all users"""
        try:
            # Load telegram mappings to get user emails
            telegram_mappings = self._load_telegram_mappings()
            
            logger.info(f"Running hourly reflections for {len(telegram_mappings)} users")
            
            for telegram_id, user_email in telegram_mappings.items():
                try:
                    await self._process_user_reflection(telegram_id, user_email)
                except Exception as e:
                    logger.error(f"Error processing reflection for user {user_email}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in run_hourly_reflections: {e}")
            
    async def _process_user_reflection(self, telegram_id: str, user_email: str):
        """Process hourly reflection for a specific user"""
        try:
            # Get user's state
            state_manager = StateManager(user_email=user_email)
            state = state_manager.get_state()
            
            # Create conversation engine for this user
            engine = NaviConversationEngine(state_manager)
            
            # Build comprehensive reflection prompt
            reflection_prompt = self._build_comprehensive_reflection_prompt(state, user_email)
            
            # Generate AI reflection response
            response = await engine.process_message(reflection_prompt)
            
            # CRITICAL: Validate and fix AI response formatting
            corrected_response = self._validate_and_fix_response(response, user_email)
            
            # Check if AI decided to send a message (after correction)
            if corrected_response.message_text:
                # AI decided to reach out to user
                await self._send_proactive_message(telegram_id, user_email, corrected_response.message_text)
                
                # Add to chat history for conversation UI
                # Mark as system prompt
                self._add_to_chat_history(state_manager, 
                    role="user",
                    content=f"[SYSTEM: Hourly Reflection Check]\n{reflection_prompt}",
                    timestamp=datetime.now().isoformat()
                )
                
                # Add AI response to chat history (including strategize thoughts)
                full_response = ""
                if corrected_response.strategize_text:
                    full_response += f"<strategize>{corrected_response.strategize_text}</strategize>\n"
                if corrected_response.message_text:
                    full_response += f"<message>{corrected_response.message_text}</message>"
                
                self._add_to_chat_history(state_manager,
                    role="model", 
                    content=full_response,
                    timestamp=datetime.now().isoformat()
                )
                
                # Log this reflection with message sent
                self._log_reflection(state_manager, {
                    "timestamp": datetime.now().isoformat(),
                    "ai_analysis": corrected_response.strategize_text or "No strategic analysis",
                    "action_taken": "message_sent",
                    "message_content": corrected_response.message_text,
                    "tool_executions": [exec["name"] for exec in response.tool_executions] if response.tool_executions else [],
                    "formatting_corrections": getattr(corrected_response, 'formatting_corrections', [])
                })
            else:
                # AI decided to stay silent - still log to chat history
                self._add_to_chat_history(state_manager,
                    role="user",
                    content=f"[SYSTEM: Hourly Reflection Check - Silent]\n{reflection_prompt}",
                    timestamp=datetime.now().isoformat()
                )
                
                # Add AI's strategize thoughts even for silent reflections
                if corrected_response.strategize_text:
                    self._add_to_chat_history(state_manager,
                        role="model",
                        content=f"<strategize>{corrected_response.strategize_text}</strategize>",
                        timestamp=datetime.now().isoformat()
                    )
                
                # Log this reflection as silent
                self._log_reflection(state_manager, {
                    "timestamp": datetime.now().isoformat(),
                    "ai_analysis": corrected_response.strategize_text or "Silent reflection completed",
                    "action_taken": "silent_reflection",
                    "message_content": None,
                    "tool_executions": [exec["name"] for exec in response.tool_executions] if response.tool_executions else [],
                    "formatting_corrections": getattr(corrected_response, 'formatting_corrections', [])
                })
            
            # Save the updated state after reflection
            engine.save_state()
            
            logger.info(f"Completed hourly reflection for {user_email} - Action: {'message_sent' if corrected_response.message_text else 'silent_reflection'}")
            
        except Exception as e:
            logger.error(f"Error processing user reflection for {user_email}: {e}")
            
    def _build_comprehensive_reflection_prompt(self, state: Dict, user_email: str) -> str:
        """Build a concise hourly reflection prompt"""
        current_time = datetime.now()
        
        # Get recent conversation data
        chat_history = state.get('chat_history', [])
        goals = state.get('goals', [])
        tasks = state.get('tasks', [])
        recent_messages = [msg for msg in chat_history if msg.get('role') == 'user'][-10:]  # Last 10 user messages
        last_user_message = recent_messages[-1] if recent_messages else None
        
        # Calculate time since last message
        hours_since_last_message = "unknown"
        if last_user_message and last_user_message.get('timestamp'):
            try:
                last_msg_time = datetime.fromisoformat(last_user_message['timestamp'].replace('Z', '+00:00'))
                hours_since_last_message = (current_time - last_msg_time).total_seconds() / 3600
            except:
                pass
        
        # Build simplified prompt
        prompt = f"""🚨 HOURLY REFLECTION TIME 🚨

**CURRENT TIME:** {current_time.strftime('%Y-%m-%d %H:%M:%S')} ({current_time.strftime('%A')})

**CONTEXT:**
- User: {user_email}
- Last message: {hours_since_last_message} hours ago
- Goals: {len(goals)}
- Tasks: {len(tasks)}
- Recent messages: {len(recent_messages)}

**TASK:** This is your hourly reflection time to decide whether to proactively message this user or stay silent.

**MANDATORY RESPONSE FORMAT:**
1. **Silent reflection:** Use ONLY <strategize> tags
2. **Proactive message:** Use <strategize> AND <message> tags
3. **NO text outside these tags!**

**ANALYSIS REQUIRED:**
Apply the comprehensive hourly reflection analysis framework from your system prompt to:
- Review user communication patterns
- Analyze goals & progress 
- Check task & commitment status
- Evaluate calendar & scheduling
- Assess behavioral patterns
- Consider time & context awareness
- Identify proactive opportunities
- Plan communication strategy
- Review contextual considerations
- Apply decision framework

**DECISION:** Should I message this user now or maintain silent support?

**EXAMPLES:**
Silent: <strategize>User last responded 6 hours ago and I already sent a helpful message about their swimming goal. They need time to process. Decision: Stay silent.</strategize>

Message: <strategize>User mentioned wanting to go swimming twice weekly but hasn't scheduled sessions this week. Wednesday is good timing for a gentle reminder.</strategize>
<message>Hey! Noticed you wanted to go swimming twice this week but haven't scheduled any sessions yet. Want me to help you find some good times?</message>

Conduct your analysis now."""

        return prompt
        
    def _validate_and_fix_response(self, response, user_email: str):
        """
        Simple structural validation - no pattern matching.
        Only validates XML tag structure and defaults to safe behavior.
        """
        from dataclasses import dataclass
        from typing import List
        
        @dataclass
        class CorrectedResponse:
            message_text: Optional[str]
            strategize_text: Optional[str]
            formatting_corrections: List[str]
        
        corrections = []
        
        # Get original content
        original_message = response.message_text or ""
        original_strategize = response.strategize_text or ""
        
        # Simple validation: check if we have proper structure
        has_strategize = bool(original_strategize and original_strategize.strip())
        has_message = bool(original_message and original_message.strip())
        
        # If no strategize content at all, this indicates the AI didn't follow instructions
        if not has_strategize:
            corrections.append("No strategize content found - AI didn't follow format")
            # Default to silent reflection with generic strategize content
            corrected_strategize = "Conducted hourly reflection analysis but didn't provide strategic thinking in proper format."
            corrected_message = None
        else:
            corrected_strategize = original_strategize
            corrected_message = original_message if has_message else None
        
        # Additional safety: if there's a message but it's suspiciously long, default to silent
        if corrected_message and len(corrected_message) > 800:
            corrections.append("Message too long - defaulting to silent reflection for safety")
            corrected_message = None
        
        # Log any issues for monitoring (but don't try to "fix" them)
        if corrections:
            logger.warning(f"Response format issues for {user_email}: {corrections}")
            
        # Always log the decision for analysis
        action = "message_planned" if corrected_message else "silent_reflection"
        logger.info(f"Hourly reflection decision for {user_email}: {action}")
        
        # Create corrected response
        corrected = CorrectedResponse(
            message_text=corrected_message,
            strategize_text=corrected_strategize,
            formatting_corrections=corrections
        )
        
        return corrected
        
    def _format_goals_for_analysis(self, goals: List[Dict]) -> str:
        """Format goals for analysis prompt"""
        if not goals:
            return "No goals currently set"
            
        goal_analysis = []
        for goal in goals[:10]:  # Limit to 10 most relevant goals
            status_info = f"Bot Assessment: {goal.get('bot_goal_assesment_percentage', 0)}%, User Assessment: {goal.get('user_goal_assesment_percentage', 0)}%"
            goal_analysis.append(f"- {goal.get('title', 'Untitled')} ({goal.get('category', 'No category')}) - {status_info}")
            
        return '\n'.join(goal_analysis)
        
    def _format_tasks_for_analysis(self, tasks: List[Dict]) -> str:
        """Format tasks for analysis prompt"""
        if not tasks:
            return "No tasks currently set"
            
        pending_tasks = [t for t in tasks if t.get('status') == 'PENDING']
        completed_tasks = [t for t in tasks if t.get('status') == 'COMPLETED']
        in_progress_tasks = [t for t in tasks if t.get('status') == 'IN_PROGRESS']
        
        analysis = f"PENDING: {len(pending_tasks)}, IN_PROGRESS: {len(in_progress_tasks)}, COMPLETED: {len(completed_tasks)}"
        
        # Add some specific overdue/important tasks
        task_details = []
        for task in pending_tasks[:5]:  # Show up to 5 pending tasks
            task_details.append(f"- {task.get('description', 'No description')} (Due: {task.get('due_date', 'No due date')})")
            
        if task_details:
            analysis += f"\nKey Pending Tasks:\n" + '\n'.join(task_details)
            
        return analysis
        
    async def _send_proactive_message(self, telegram_id: str, user_email: str, message: str):
        """Send proactive message to user"""
        try:
            # Only remove XML tags (structural parsing, not content matching)
            import re
            clean_message = re.sub(r'<[^>]+>', '', message).strip()
            
            # Simple safety check: if message is empty after cleaning, don't send
            if not clean_message:
                logger.warning(f"Empty message after XML tag removal for user {user_email}")
                return
            
            # Basic length check for safety (no pattern matching)
            if len(clean_message) > 1000:
                logger.warning(f"Message too long ({len(clean_message)} chars) for user {user_email}, defaulting to silent")
                return
            
            await self.bot.send_message(
                chat_id=telegram_id,
                text=clean_message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Sent proactive hourly reflection message to {user_email}")
            
        except TelegramError as e:
            logger.error(f"Failed to send proactive message to {telegram_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending proactive message: {e}")
            
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
            
            # Don't save here - let the caller save after all updates
            
        except Exception as e:
            logger.error(f"Error adding to chat history: {e}")
    
    def _log_reflection(self, state_manager: StateManager, reflection_data: Dict):
        """Log hourly reflection data to user state"""
        try:
            state = state_manager.get_state()
            
            # Initialize hourly_reflections if not exists
            if 'hourly_reflections' not in state:
                state['hourly_reflections'] = []
                
            # Add new reflection
            state['hourly_reflections'].append(reflection_data)
            
            # Keep only last 24 reflections (24 hours of history)
            state['hourly_reflections'] = state['hourly_reflections'][-24:]
            
            # Save state
            state_manager.save_state()
            
        except Exception as e:
            logger.error(f"Error logging reflection: {e}")
            
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
            
    async def trigger_reflection_now(self, user_email: str):
        """Manually trigger reflection for a specific user (for testing)"""
        telegram_mappings = self._load_telegram_mappings()
        
        # Find telegram ID for user
        telegram_id = None
        for tid, email in telegram_mappings.items():
            if email == user_email:
                telegram_id = tid
                break
                
        if telegram_id:
            await self._process_user_reflection(telegram_id, user_email)
            logger.info(f"Manual hourly reflection completed for {user_email}")
        else:
            logger.warning(f"No telegram ID found for {user_email}")