"""
NAVI Telegram Bot - Unified Architecture Version
Streamlined Telegram bot using the unified conversation engine
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv

# Local imports - updated for new package structure
from ...core.auth.telegram_auth import TelegramSimpleAuth
from ..adapters import create_telegram_interface
from ...core.state.manager import StateManager

# Load environment variables from project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Setup logging with absolute paths
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(PROJECT_ROOT, 'telegram_bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Setup error logging
error_logger = logging.getLogger('telegram_errors')
error_handler = logging.FileHandler(os.path.join(PROJECT_ROOT, 'telegram_errors.log'))
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
error_handler.setFormatter(error_formatter)
error_logger.addHandler(error_handler)


class NaviTelegramBot:
    """NAVI Telegram Bot using unified architecture"""
    
    def __init__(self):
        self.telegram_auth = TelegramSimpleAuth()
        self.user_interfaces: Dict[int, object] = {}  # user_id -> NaviTelegramInterface
        
        # Setup Gemini API
        try:
            api_key = os.environ['GEMINI_API_KEY']
            genai.configure(api_key=api_key)
        except KeyError:
            logger.critical("GEMINI_API_KEY environment variable not set.")
            sys.exit(1)
    
    def get_user_interface(self, user_id: int) -> Optional[object]:
        """Get or create user interface"""
        if user_id in self.user_interfaces:
            return self.user_interfaces[user_id]
        
        # Check if user is authenticated
        user_email = self.telegram_auth.get_user_email_from_telegram(user_id)
        if not user_email:
            return None
        
        # Create interface for authenticated user
        try:
            interface = create_telegram_interface(user_email)
            self.user_interfaces[user_id] = interface
            logger.info(f"Created interface for user {user_id} ({user_email})")
            return interface
        except Exception as e:
            logger.error(f"Failed to create interface for user {user_id}: {e}")
            return None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "there"
        
        logger.info(f"Start command from user {user_id}")
        
        # Check if already authenticated
        user_email = self.telegram_auth.get_user_email_from_telegram(user_id)
        if user_email:
            await update.message.reply_text(
                f"Welcome back, {user_name}! 🎉\n"
                f"You're already connected as {user_email}.\n\n"
                "Just send me a message and I'll help you with goals, tasks, and calendar events!"
            )
            return
        
        # Not authenticated - show auth instructions
        base_url = os.environ.get('BASE_URL', 'http://localhost:4999')
        welcome_text = f"""
Hi {user_name}! 👋 Welcome to NAVI!

I'm your personal productivity assistant. I can help you with:
📋 Goal setting and tracking
✅ Task management  
📅 Calendar events
💡 Productivity insights

**To get started:**
1. Visit {base_url} in your browser
2. Login with Google to authenticate
3. Go to Settings and generate a 6-digit code
4. Send me that code here

Let's get you set up! 🚀
        """
        
        # Don't use inline keyboard with localhost URL - Telegram doesn't allow it
        # Just send the welcome text with instructions
        await update.message.reply_text(welcome_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        user_id = update.effective_user.id
        user_message = update.message.text
        
        logger.info(f"Message from user {user_id}: {user_message}")
        
        # Check for authentication code first
        if user_message.isdigit() and len(user_message) == 6:
            await self._handle_auth_code(update, user_message)
            return
        
        # Get user interface
        interface = self.get_user_interface(user_id)
        if not interface:
            base_url = os.environ.get('BASE_URL', 'http://localhost:4999')
            await update.message.reply_text(
                "🔐 You need to authenticate first!\n\n"
                "Please:\n"
                f"1. Visit {base_url}\n"
                "2. Login with Google\n"
                "3. Get your 6-digit code from Settings\n"
                "4. Send me the code"
            )
            return
        
        # Process message through unified interface
        try:
            response = await interface.handle_user_input(user_message)
            
            # Format and send response
            telegram_text = response.message_text or "🤖 I'm processing your request..."
            
            # Add tool execution info in development mode
            if response.tool_executions:
                tools_info = "\n\n" + "\n".join(response.tool_executions)
                telegram_text += tools_info
            
            # Send response
            await self._send_response(update, telegram_text)
            
        except Exception as e:
            logger.error(f"Error processing message for user {user_id}: {e}")
            error_logger.error(f"Message processing error for user {user_id}: {e}")
            await update.message.reply_text(
                "🤖 Sorry, I encountered an error processing your message. Please try again!"
            )
    
    async def _handle_auth_code(self, update: Update, code: str):
        """Handle authentication code"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"
        
        try:
            success, user_email, message = self.telegram_auth.verify_auth_code(user_id, code)
            if success and user_email:
                # Authentication successful - generate personalized welcome message
                welcome_message = await self._generate_welcome_message(user_name, user_email)
                await update.message.reply_text(welcome_message)
                logger.info(f"User {user_id} authenticated as {user_email}")
            else:
                base_url = os.environ.get('BASE_URL', 'http://localhost:4999')
                await update.message.reply_text(
                    "❌ Invalid or expired code.\n\n"
                    "Please:\n"
                    f"1. Visit {base_url}\n"
                    "2. Generate a new 6-digit code\n"
                    "3. Send it to me within 30 minutes"
                )
        except Exception as e:
            logger.error(f"Auth error for user {user_id}: {e}")
            await update.message.reply_text(
                "🤖 Authentication failed. Please try generating a new code."
            )
    
    async def _generate_welcome_message(self, user_name: str, user_email: str) -> str:
        """Generate personalized welcome message using AI"""
        try:
            # For now, let's use the fallback message to avoid function call issues
            # TODO: Fix function call handling in welcome message generation
            return self._get_fallback_welcome_message(user_name, user_email)
            
            # Original AI generation code (disabled for now):
            # interface = create_telegram_interface(user_email)
            # welcome_prompt = f"""Please generate a warm, personalized welcome message for {user_name} who just connected their NAVI account ({user_email}). 
            # The message should:
            # - Be friendly and engaging
            # - Mention their successful connection
            # - Give 2-3 specific examples of what they can ask me
            # - Encourage natural conversation
            # - Include relevant emojis
            # - Be concise but enthusiastic
            # Keep it under 200 words and make it feel personalized and exciting about getting started with NAVI!"""
            # response = await interface.handle_user_input(welcome_prompt)
            # if response and response.message_text:
            #     return response.message_text
                
        except Exception as e:
            logger.error(f"Failed to generate welcome message: {e}")
            return self._get_fallback_welcome_message(user_name, user_email)
    
    def _get_fallback_welcome_message(self, user_name: str, user_email: str) -> str:
        """Fallback welcome message if AI generation fails"""
        return (
            f"🎉 Welcome {user_name}!\n\n"
            f"Successfully connected to your NAVI account: {user_email}\n\n"
            "I'm ready to help! Try asking me:\n"
            "• \"What are my events today?\"\n"
            "• \"Help me set a fitness goal\"\n"
            "• \"Show me my tasks\"\n\n"
            "Just talk naturally - I understand! 😊"
        )
    
    def _format_for_telegram(self, text: str) -> str:
        """Convert NAVI formatting tags to Telegram-compatible formatting"""
        import re
        
        # Convert <strategize> tags to Telegram formatting
        # Replace <strategize>content</strategize> with 🧠 **Strategic Thinking**\ncontent
        strategize_pattern = r'<strategize>(.*?)</strategize>'
        text = re.sub(strategize_pattern, r'🧠 **Strategic Thinking**\n\1', text, flags=re.DOTALL)
        
        # Convert other potential tags if needed
        # <thinking>content</thinking> -> 🤔 **Thinking**\ncontent
        thinking_pattern = r'<thinking>(.*?)</thinking>'
        text = re.sub(thinking_pattern, r'🤔 **Thinking**\n\1', text, flags=re.DOTALL)
        
        return text

    async def _send_response(self, update: Update, text: str):
        """Send response with proper formatting and error handling"""
        try:
            # Format text for Telegram
            formatted_text = self._format_for_telegram(text)
            
            # Split long messages
            if len(formatted_text) > 4096:
                chunks = [formatted_text[i:i+4096] for i in range(0, len(formatted_text), 4096)]
                for chunk in chunks:
                    await update.message.reply_text(chunk, parse_mode='Markdown')
            else:
                await update.message.reply_text(formatted_text, parse_mode='Markdown')
                
        except Exception as markdown_error:
            # If markdown parsing fails, send as plain text
            logger.warning(f"Markdown parsing failed, sending as plain text: {markdown_error}")
            try:
                # Still format for telegram but send as plain text
                formatted_text = self._format_for_telegram(text)
                if len(formatted_text) > 4096:
                    chunks = [formatted_text[i:i+4096] for i in range(0, len(formatted_text), 4096)]
                    for chunk in chunks:
                        await update.message.reply_text(chunk)
                else:
                    await update.message.reply_text(formatted_text)
            except Exception as e:
                logger.error(f"Failed to send response: {e}")
                await update.message.reply_text("🤖 Sorry, I had trouble sending my response.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command - show all available commands and capabilities"""
        help_text = """
🤖 NAVI Help - Complete Capabilities

📋 Available Slash Commands:
/start - Get started with NAVI (authentication setup)
/help - Show this comprehensive help guide
/reset - Reset authentication, message history, and clear all data

🔐 Authentication:
If not set up yet, visit your NAVI web app to get your auth code.

🎯 GOAL MANAGEMENT:
• Create Goals: "I want to learn Spanish" or "Set a fitness goal"
• View Goals: "Show my goals" or "What goals do I have?"
• Update Goals: "Update my fitness goal importance to HIGH"
• Goal Progress: "How am I doing with my goals?"
• Goal Categories: View goals by Health, Career, Learning, etc.
• Goal Completion: Check which goals need more work

✅ TASK MANAGEMENT:
• Create Tasks: "Add a task to read 30 minutes daily"
• View Tasks: "Show my tasks" or "What should I work on?"
• Update Tasks: "Mark task 3 as completed"
• Task Progress: Track PENDING, IN_PROGRESS, COMPLETED status
• Auto-Calendar: Tasks automatically create calendar events

📅 CALENDAR INTEGRATION:
• View Events: "What are my events today?" or "Show next week"
• Create Events: "Schedule lunch with Sarah tomorrow at 1pm"
• Update Events: "Move my 3pm meeting to 4pm"
• Delete Events: "Cancel my dentist appointment"
• Event Details: Get full information about any event
• Daily Events: Set up recurring daily activities

📊 PROGRESS TRACKING & INSIGHTS:
• Progress Trackers: "Set a check-in for my study goal tomorrow"
• View Trackers: "Show my progress check-ins"
• Update Progress: Modify tracker status and timing
• Personal Insights: "Add insight about my productivity patterns"
• User Profile: Update your name, age, job, preferences

🚀 Example Conversations:
• "I want to get fit by summer - help me create a plan"
• "Schedule a team meeting every Tuesday at 2pm"
• "What tasks are due this week?"
• "Update my Spanish learning goal to HIGH importance"
• "Set a progress check-in for my reading goal tomorrow"
• "Show me all my Health category goals"
• "Cancel my 3pm appointment and reschedule for Friday"

💡 Pro Tips:
• Be Specific: "Exercise 3x/week" vs "get fit"
• Natural Language: Talk like you would to a friend
• Ask for Details: I'll help clarify if you need more info
• Goal Categories: Health, Career, Learning, Finance, Relationships, etc.
• Time Format: Use DD/MM/YY HH:MM (e.g., "15/12/25 14:30")

🔧 Need a fresh start?
Use /reset to clear everything and start over

Ready to boost your productivity? Just start talking! 😊
        """
        
        await update.message.reply_text(help_text)
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command - reset auth, message history, and state"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"
        
        logger.info(f"Reset command from user {user_id}")
        
        try:
            # Check if user is authenticated
            user_email = self.telegram_auth.get_user_email_from_telegram(user_id)
            
            if user_email:
                # Clear telegram authentication mapping
                self.telegram_auth.clear_user_mapping(user_id)
                
                # Clear user interface from memory
                if user_id in self.user_interfaces:
                    del self.user_interfaces[user_id]
                
                # Clear user state and conversation history
                sm = StateManager(user_email=user_email)
                sm.reset_all_data()
                
                logger.info(f"Reset completed for user {user_id} ({user_email})")
                
                base_url = os.environ.get('BASE_URL', 'http://localhost:4999')
                await update.message.reply_text(
                    f"🔄 Reset Complete! {user_name}\n\n"
                    "✅ Authentication cleared\n"
                    "✅ Message history cleared\n"
                    "✅ Goals and tasks cleared\n"
                    "✅ Conversation state reset\n\n"
                    "You'll need to authenticate again:\n"
                    f"1. Visit {base_url}\n"
                    "2. Login with Google\n"
                    "3. Get a new 6-digit code\n"
                    "4. Send it to me\n\n"
                    "Ready for a fresh start! 🚀"
                )
            else:
                base_url = os.environ.get('BASE_URL', 'http://localhost:4999')
                await update.message.reply_text(
                    "🤔 You're not currently authenticated, so there's nothing to reset!\n\n"
                    "To get started:\n"
                    f"1. Visit {base_url}\n"
                    "2. Login with Google\n"
                    "3. Get your 6-digit code\n"
                    "4. Send it to me"
                )
                
        except Exception as e:
            logger.error(f"Error during reset for user {user_id}: {e}")
            await update.message.reply_text(
                "🤖 Sorry, I encountered an error during reset. Please try again or contact support."
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        # Handle different callback data
        if query.data == "get_auth_code":
            base_url = os.environ.get('BASE_URL', 'http://localhost:4999')
            await query.message.reply_text(
                f"🔗 Please visit {base_url} to authenticate and get your code!"
            )
    
    def run(self):
        """Run the Telegram bot"""
        try:
            bot_token = os.environ['TELEGRAM_BOT_TOKEN']
        except KeyError:
            logger.critical("TELEGRAM_BOT_TOKEN environment variable not set.")
            sys.exit(1)
        
        logger.info("Starting NAVI Telegram Bot...")
        logger.info(f"Bot token configured (last 4 chars): ...{bot_token[-4:]}")
        
        # Create application
        application = Application.builder().token(bot_token).build()
        
        # Log successful connection
        logger.info("Telegram application created successfully")
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("reset", self.reset_command))
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Initialize and start progress tracker scheduler
        from ...core.scheduler import ProgressTrackerScheduler, HourlyReflectionScheduler
        self.progress_scheduler = ProgressTrackerScheduler(
            bot=application.bot,
            check_interval_seconds=300  # Check every 5 minutes for production
        )
        
        # Initialize hourly reflection scheduler
        self.hourly_reflection_scheduler = HourlyReflectionScheduler(
            bot=application.bot,
            check_interval_seconds=3600  # Check every hour
        )
        
        # Start schedulers when bot starts
        async def post_init(application):
            await self.progress_scheduler.start()
            await self.hourly_reflection_scheduler.start()
            logger.info("Progress tracker and hourly reflection schedulers started")
            
        # Stop schedulers when bot stops
        async def post_shutdown(application):
            await self.progress_scheduler.stop()
            await self.hourly_reflection_scheduler.stop()
            logger.info("Progress tracker and hourly reflection schedulers stopped")
            
        application.post_init = post_init
        application.post_shutdown = post_shutdown
        
        # Run the bot
        logger.info("Starting bot polling...")
        try:
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"Bot polling failed: {e}")
            raise


def main():
    """Main function"""
    bot = NaviTelegramBot()
    bot.run()


if __name__ == "__main__":
    main()