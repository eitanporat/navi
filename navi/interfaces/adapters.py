"""
NAVI Interface Adapters
Thin presentation layers over the unified conversation engine
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from telegram import Update
from telegram.ext import ContextTypes

# Local imports - updated for new package structure
from ..core.engine.conversation import NaviConversationEngine, NaviResponse
from ..core.state.manager import StateManager


logger = logging.getLogger(__name__)


class NaviInterface(ABC):
    """Abstract base class for NAVI interfaces"""
    
    def __init__(self, engine: NaviConversationEngine):
        self.engine = engine
    
    @abstractmethod
    async def handle_user_input(self, user_input: str, context: Dict[str, Any] = None):
        """Handle user input and respond appropriately"""
        pass


class NaviCLIInterface(NaviInterface):
    """CLI interface adapter using Rich UI"""
    
    def __init__(self, engine: NaviConversationEngine):
        super().__init__(engine)
    
    async def handle_user_input(self, user_input: str, context: Dict[str, Any] = None):
        """Process user input and display response using Rich UI"""
        try:
            # Process message through engine
            response = await self.engine.process_message(user_input, context)
            
            # Display response using Rich UI
            self._display_response(response)
            
            # Save state after processing
            self.engine.save_state()
            
        except Exception as e:
            logger.error(f"CLI error processing input: {e}")
            # Import UI locally to avoid circular imports during transition
            from .cli.ui import display_error
            display_error(f"I encountered an error: {str(e)}")
    
    def _display_response(self, response: NaviResponse):
        """Display response using Rich UI with colored blocks"""
        # Import UI locally to avoid circular imports during transition
        from .cli.ui import display_error, display_model_thought_process
        
        if response.error:
            display_error(f"Error: {response.error}")
            return
        
        # Build raw response text for UI processing
        raw_response = ""
        if response.strategize_text:
            raw_response += f"<strategize>{response.strategize_text}</strategize>\n"
        if response.message_text:
            raw_response += f"<message>{response.message_text}</message>"
        
        # Use existing UI function to display with colored blocks
        display_model_thought_process(raw_response)
    
    def run_conversation_loop(self):
        """Run the main CLI conversation loop"""
        # Import UI locally to avoid circular imports during transition
        from .cli.ui import display_welcome, get_user_input, display_goodbye, display_error
        
        display_welcome()
        
        while True:
            try:
                user_input = get_user_input()
                if user_input.lower() in ["quit", "exit"]:
                    display_goodbye()
                    break
                if not user_input.strip():
                    continue
                
                # Handle special commands first
                if user_input.startswith('/'):
                    if self._handle_command(user_input):
                        continue
                
                # Process regular message
                asyncio.run(self.handle_user_input(user_input))
                
            except KeyboardInterrupt:
                display_goodbye()
                break
            except Exception as e:
                logger.error(f"Unhandled CLI exception: {e}")
                display_error("An unexpected error occurred. Please try again.")
    
    def _handle_command(self, command: str) -> bool:
        """Handle CLI commands - returns True if command was handled"""
        # Import locally to avoid circular imports during transition
        from ..core.auth import navi_auth
        from .cli.ui import display_info, display_success, display_warning
        
        command = command.lower().strip()
        
        if command in ['/help', '/?']:
            display_info("""
Available Commands:
• /help, /?         - Show this help
• /goals            - List all your goals  
• /tasks            - List all your tasks
• /events           - List upcoming events
• /calendar         - Check calendar status
• /status           - Show progress status
• /auth, /login     - Re-authenticate
• /whoami, /user    - Show current user
• /switch           - Switch users

💡 Tip: Just talk naturally! NAVI understands conversational requests.
            """, "NAVI Commands")
            return True
        
        elif command == '/goals':
            from ..core.tools import list_goals
            result = list_goals(self.engine.state_manager)
            display_info(result, "Your Goals")
            return True
        
        elif command == '/tasks':
            from ..core.tools import list_tasks
            result = list_tasks(self.engine.state_manager)
            display_info(result, "Your Tasks")
            return True
        
        elif command == '/events':
            from ..core.tools import list_events
            import datetime
            today = datetime.date.today()
            next_week = today + datetime.timedelta(days=7)
            start_date = today.strftime("%d/%m/%y")
            end_date = next_week.strftime("%d/%m/%y")
            result = list_events(self.engine.state_manager, start_date, end_date)
            display_info(result, f"Upcoming Events ({start_date} to {end_date})")
            return True
        
        elif command == '/calendar':
            service = navi_auth.get_calendar_service()
            if service:
                display_success("Calendar Integration: ✅ Connected")
            else:
                display_warning("Calendar Integration: ❌ Not connected\nUse '/auth' to re-authenticate")
            return True
        
        elif command == '/status':
            from ..core.tools import list_goals, list_tasks
            goals = list_goals(self.engine.state_manager)
            tasks = list_tasks(self.engine.state_manager)
            display_info(f"Goals: {goals}\nTasks: {tasks}", "Progress Status")
            return True
        
        elif command in ['/auth', '/login']:
            display_info("Re-authentication not yet implemented in unified interface")
            return True
        
        elif command in ['/whoami', '/user']:
            # Get current user from state manager
            user_email = getattr(self.engine.state_manager, 'user_email', 'Unknown')
            display_info(f"Current user: {user_email}", "User Info")
            return True
        
        else:
            display_warning(f"Unknown command: {command}\nUse '/help' to see available commands")
            return True


class NaviTelegramInterface(NaviInterface):
    """Telegram interface adapter"""
    
    def __init__(self, engine: NaviConversationEngine):
        super().__init__(engine)
    
    async def handle_user_input(self, user_input: str, context: Dict[str, Any] = None):
        """Process user input and return response for Telegram"""
        try:
            # Process message through engine
            response = await self.engine.process_message(user_input, context)
            
            # Save state after processing
            self.engine.save_state()
            
            return response
            
        except Exception as e:
            logger.error(f"Telegram error processing input: {e}")
            return NaviResponse(
                message_text="Sorry, I encountered an error processing your message. Please try again!",
                error=str(e)
            )
    
    async def handle_telegram_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Telegram message update"""
        try:
            user_message = update.message.text
            user_id = update.effective_user.id
            
            logger.info(f"Processing Telegram message from user {user_id}: {user_message}")
            
            # Process through engine
            response = await self.handle_user_input(user_message)
            
            # Format response for Telegram
            telegram_text = self._format_for_telegram(response)
            
            # Add tool execution info in dev mode
            if response.tool_executions:
                tools_info = "\n\n" + "\n".join(response.tool_executions)
                telegram_text += tools_info
            
            # Send response
            await self._send_telegram_response(update, telegram_text)
            
        except Exception as e:
            logger.error(f"Failed to handle Telegram message: {e}")
            await update.message.reply_text(
                "🤖 Sorry, I encountered an error processing your message. Please try again!"
            )
    
    def _format_for_telegram(self, response: NaviResponse) -> str:
        """Format response for Telegram (message text only, with markdown)"""
        if response.error:
            return f"❌ Error: {response.error}"
        
        return response.message_text or "🤖 I'm processing your request..."
    
    async def _send_telegram_response(self, update: Update, text: str):
        """Send response to Telegram with proper formatting"""
        try:
            # Split long messages if needed
            if len(text) > 4096:
                chunks = [text[i:i+4096] for i in range(0, len(text), 4096)]
                for chunk in chunks:
                    await update.message.reply_text(chunk, parse_mode='Markdown')
            else:
                await update.message.reply_text(text, parse_mode='Markdown')
                
        except Exception as markdown_error:
            # If markdown parsing fails, send as plain text
            logger.warning(f"Markdown parsing failed, sending as plain text: {markdown_error}")
            if len(text) > 4096:
                chunks = [text[i:i+4096] for i in range(0, len(text), 4096)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(text)


class NaviWebInterface(NaviInterface):
    """Web interface adapter (for future implementation)"""
    
    def __init__(self, engine: NaviConversationEngine):
        super().__init__(engine)
    
    async def handle_user_input(self, user_input: str, context: Dict[str, Any] = None):
        """Process user input and return JSON response for web"""
        try:
            response = await self.engine.process_message(user_input, context)
            self.engine.save_state()
            
            # Return structured response for web API
            return {
                "message": response.message_text,
                "strategize": response.strategize_text,
                "tool_executions": response.tool_executions,
                "error": response.error
            }
            
        except Exception as e:
            logger.error(f"Web error processing input: {e}")
            return {
                "message": "Sorry, I encountered an error processing your message.",
                "error": str(e)
            }


# Factory function for creating engines
def create_navi_engine(user_email: str) -> NaviConversationEngine:
    """Factory function to create a NAVI conversation engine for a user"""
    state_manager = StateManager(user_email=user_email)
    return NaviConversationEngine(state_manager)


# Factory functions for creating interfaces
def create_cli_interface(user_email: str) -> NaviCLIInterface:
    """Create CLI interface for a user"""
    engine = create_navi_engine(user_email)
    return NaviCLIInterface(engine)


def create_telegram_interface(user_email: str) -> NaviTelegramInterface:
    """Create Telegram interface for a user"""
    engine = create_navi_engine(user_email)
    return NaviTelegramInterface(engine)


def create_web_interface(user_email: str) -> NaviWebInterface:
    """Create Web interface for a user"""
    engine = create_navi_engine(user_email)
    return NaviWebInterface(engine)