"""
NAVI Unified Conversation Engine
Shared core logic for CLI, Telegram, and future interfaces
"""

import os
import re
import json
import time
import logging
import functools
import inspect
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool, generation_types

# Local imports - updated for new package structure
from ..state.manager import StateManager
from ..tools import tool_functions
from ...config.prompts import system_prompt


logger = logging.getLogger(__name__)


@dataclass
class NaviResponse:
    """Structured response from NAVI conversation engine"""
    message_text: str
    strategize_text: Optional[str] = None
    analyze_text: Optional[str] = None
    tool_executions: List[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.tool_executions is None:
            self.tool_executions = []


class NaviToolManager:
    """Manages tool declarations, binding, and execution"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.executable_tools = self._create_executable_tools()
        self.tool_declarations = self._create_tool_declarations()
    
    def _create_executable_tools(self) -> Dict[str, callable]:
        """Create executable tools with state manager bound"""
        return {
            name: functools.partial(func, state_manager=self.state_manager) 
            for name, func in tool_functions.items()
        }
    
    def _create_tool_declarations(self) -> List[FunctionDeclaration]:
        """Create Gemini tool declarations from functions"""
        declarations = []
        type_mapping = {str: 'STRING', int: 'INTEGER', bool: 'BOOLEAN', float: 'NUMBER'}
        
        for func in tool_functions.values():
            signature = inspect.signature(func)
            properties, required = {}, []
            
            for name, param in signature.parameters.items():
                if name == 'state_manager':
                    continue
                model_type = type_mapping.get(param.annotation, 'STRING')
                properties[name] = {'type': model_type, 'description': ''}
                if param.default is inspect.Parameter.empty:
                    required.append(name)
            
            declarations.append(FunctionDeclaration(
                name=func.__name__,
                description=func.__doc__,
                parameters={
                    'type': 'OBJECT',
                    'properties': properties,
                    'required': required
                }
            ))
        
        return declarations
    
    async def execute_tools(self, response) -> List[Dict[str, Any]]:
        """Execute all function calls in a response and return results"""
        function_calls = []
        if (response.candidates and 
            response.candidates[0].content and 
            response.candidates[0].content.parts):
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)
        
        if not function_calls:
            return []
        
        logger.info(f"Executing {len(function_calls)} tool(s)")
        
        # Execute all function calls and prepare results for AI
        gemini_tool_results = []
        execution_log = []
        
        for func_call in function_calls:
            tool_name = func_call.name
            tool_args = dict(func_call.args) if func_call.args else {}
            
            if tool_name in self.executable_tools:
                try:
                    result = self.executable_tools[tool_name](**tool_args)
                    execution_log.append(f"**running tool `{tool_name}`...**")
                    
                    # Prepare result for AI (Gemini format)
                    gemini_tool_results.append({
                        "function_response": {
                            "name": tool_name,
                            "response": {"result": result}
                        }
                    })
                    
                    # Log the execution
                    self._log_tool_execution(tool_name, tool_args, result)
                    logger.info(f"Tool {tool_name} executed successfully")
                    
                except Exception as e:
                    execution_log.append(f"❌ {tool_name} (failed)")
                    gemini_tool_results.append({
                        "function_response": {
                            "name": tool_name,
                            "response": {"result": f"ERROR: {str(e)}"}
                        }
                    })
                    self._log_tool_execution(tool_name, tool_args, f"ERROR: {str(e)}")
                    logger.error(f"Tool {tool_name} failed: {e}")
            else:
                execution_log.append(f"❓ {tool_name} (not found)")
                gemini_tool_results.append({
                    "function_response": {
                        "name": tool_name,
                        "response": {"result": "ERROR: Tool not found"}
                    }
                })
                logger.warning(f"Tool {tool_name} not found")
        
        return gemini_tool_results
    
    def _log_tool_execution(self, tool_name: str, args: Dict[str, Any], result: str):
        """Log tool execution to state manager"""
        try:
            if 'tool_execution_log' not in self.state_manager.state:
                self.state_manager.state['tool_execution_log'] = []
            
            # Add the tool result to the log
            self.state_manager.state['tool_execution_log'].append({
                'tool_name': tool_name,
                'args': args,
                'result': result,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Keep only the last 100 tool executions
            if len(self.state_manager.state['tool_execution_log']) > 100:
                self.state_manager.state['tool_execution_log'] = \
                    self.state_manager.state['tool_execution_log'][-100:]
        except Exception as e:
            logger.error(f"Failed to log tool execution: {e}")
    


class NaviResponseProcessor:
    """Processes AI responses and extracts structured information"""
    
    @staticmethod
    def process_response(response) -> NaviResponse:
        """Process AI response and extract structured information"""
        try:
            # Extract text parts from response, handling function calls properly
            raw_response_text = ""
            
            try:
                # Try the simple approach first
                raw_response_text = response.text if response.text else ""
            except (ValueError, AttributeError):
                # Response contains function calls or has no direct text, extract manually
                text_parts = []
                if (response.candidates and 
                    response.candidates[0].content and 
                    response.candidates[0].content.parts):
                    for part in response.candidates[0].content.parts:
                        # Only extract text parts, skip function calls
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                raw_response_text = ''.join(text_parts)
            
            # Extract structured components
            strategize_text = NaviResponseProcessor._extract_section(raw_response_text, 'strategize')
            message_text = NaviResponseProcessor._extract_section(raw_response_text, 'message')
            
            # Fallback if no message tags found
            if not message_text and raw_response_text:
                message_text = raw_response_text.strip()
            
            return NaviResponse(
                message_text=message_text or "I'm processing your request...",
                strategize_text=strategize_text,
                analyze_text=None  # No longer used
            )
            
        except Exception as e:
            logger.error(f"Failed to process response: {e}")
            return NaviResponse(
                message_text="Sorry, I encountered an error processing my response.",
                error=str(e)
            )
    
    @staticmethod
    def _extract_section(text: str, section: str) -> Optional[str]:
        """Extract content from XML-style tags"""
        pattern = f'<{section}>(.*?)</{section}>'
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else None


class NaviContextManager:
    """Manages conversation context and chat history"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
    
    def build_context(self, user_message: str, extra_context: Dict[str, Any] = None) -> str:
        """Build rich conversation context like CLI version"""
        try:
            # Check if this is a SYSTEM message - if so, pass through directly
            if user_message.startswith("**SYSTEM NOTIFICATION:"):
                logger.info("Processing SYSTEM notification - bypassing user context building")
                return user_message
            
            # Get current state for USER messages
            state = self.state_manager.get_state()
            current_stage = state.get('conversation_stage', 'Not Set')
            
            # Get goals summary
            from ..tools.goals import list_goals
            goals_summary = list_goals(self.state_manager)
            
            # Generate simple next stage suggestion
            next_stage_suggestion = self._generate_stage_suggestion(
                user_message, current_stage
            )
            
            # Build timestamp
            turn_timestamp = datetime.now(timezone.utc).isoformat()
            
            # Build rich context message (same format as CLI)
            context_message = f"""---
# CONVERSATION CONTEXT
Current Time: {turn_timestamp}
Current Stage: {current_stage}
Suggested Next Stage: {next_stage_suggestion}
Goals So Far:
{goals_summary}

# USER MESSAGE
{user_message}
---"""
            
            return context_message
            
        except Exception as e:
            logger.error(f"Failed to build context: {e}")
            # Fallback to simple message
            return user_message
    
    def _generate_stage_suggestion(self, user_message: str, current_stage: str) -> str:
        """Generate next stage suggestion without using AI"""
        if current_stage == "Introduction & Onboarding":
            if "goal" in user_message.lower():
                return "Goal Definition"
            elif "task" in user_message.lower():
                return "Task Definition"
            elif "event" in user_message.lower() or "calendar" in user_message.lower():
                return "Calendar Management"
            else:
                return "Introduction & Onboarding"
        else:
            return "Free Form Conversation"


class NaviConversationEngine:
    """Core conversation engine used by all interfaces"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.tool_manager = NaviToolManager(state_manager)
        self.context_manager = NaviContextManager(state_manager)
        self.response_processor = NaviResponseProcessor()
        self.model, self.chat = self._initialize_ai()
    
    def _initialize_ai(self):
        """Initialize AI model and chat with tools"""
        # Create tools
        my_tools = [Tool(function_declarations=self.tool_manager.tool_declarations)]
        
        # Initialize model
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=system_prompt,
            tools=my_tools
        )
        
        # Load saved history
        saved_history = self.state_manager.get_state().get('chat_history', [])
        
        # Apply built-in context management
        try:
            managed_history = self._manage_chat_context_builtin(saved_history)
        except Exception as e:
            logger.warning(f"Context management failed: {e}")
            managed_history = saved_history
        
        # Convert to API format
        api_compatible_history = [
            {'role': msg['role'], 'parts': msg['parts']}
            for msg in managed_history
            if 'role' in msg and 'parts' in msg
        ]
        
        # Start chat with history
        chat = model.start_chat(history=api_compatible_history)
        
        logger.info(f"AI initialized with {len(api_compatible_history)} messages in history")
        return model, chat
    
    def _log_gemini_api_call(self, call_type: str, input_data: Any, response_data: Any, 
                            response_time_ms: int = 0, tokens_in: int = 0, tokens_out: int = 0):
        """Log Gemini API call to state manager"""
        try:
            if 'gemini_api_log' not in self.state_manager.state:
                self.state_manager.state['gemini_api_log'] = []
            
            # Add the API call to the log
            self.state_manager.state['gemini_api_log'].append({
                'call_type': call_type,
                'input_preview': str(input_data)[:200] + "..." if len(str(input_data)) > 200 else str(input_data),
                'response_preview': str(response_data)[:200] + "..." if len(str(response_data)) > 200 else str(response_data),
                'response_time_ms': response_time_ms,
                'tokens_in': tokens_in,
                'tokens_out': tokens_out,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Keep only the last 100 API calls
            if len(self.state_manager.state['gemini_api_log']) > 100:
                self.state_manager.state['gemini_api_log'] = \
                    self.state_manager.state['gemini_api_log'][-100:]
        except Exception as e:
            logger.error(f"Failed to log Gemini API call: {e}")
    
    def _safe_extract_response_text(self, response) -> str:
        """Safely extract text from Gemini response, handling function calls"""
        try:
            return response.text if response.text else ""
        except (ValueError, AttributeError):
            # Response contains function calls, extract only text parts
            text_parts = []
            if (response.candidates and 
                response.candidates[0].content and 
                response.candidates[0].content.parts):
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
            return ''.join(text_parts)
    
    def _safe_count_response_tokens(self, response) -> int:
        """Safely count tokens in response, handling function calls"""
        try:
            text = self._safe_extract_response_text(response)
            return len(text.split()) if text else 0
        except Exception:
            return 0
    
    async def process_message(self, user_message: str, context: Dict[str, Any] = None) -> NaviResponse:
        """Process user message and return structured response"""
        try:
            # Build rich context
            context_message = self.context_manager.build_context(user_message, context)
            
            # Send to AI with timing and logging
            start_time = time.time()
            response = self.chat.send_message(context_message)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Log the initial Gemini API call
            self._log_gemini_api_call(
                call_type="chat.send_message",
                input_data=context_message,
                response_data=self._safe_extract_response_text(response),
                response_time_ms=response_time_ms,
                tokens_in=len(context_message.split()),  # Rough estimate
                tokens_out=self._safe_count_response_tokens(response)
            )
            
            # Handle tool execution loop
            while self._has_function_calls(response):
                tool_results = await self.tool_manager.execute_tools(response)
                if tool_results:
                    # Log follow-up API call for tool results
                    start_time = time.time()
                    response = self.chat.send_message(tool_results)
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    self._log_gemini_api_call(
                        call_type="chat.send_message (tool_results)",
                        input_data=tool_results,
                        response_data=self._safe_extract_response_text(response),
                        response_time_ms=response_time_ms,
                        tokens_in=len(str(tool_results).split()),  # Rough estimate
                        tokens_out=self._safe_count_response_tokens(response)
                    )
                else:
                    break
            
            # Process and return structured response
            return self.response_processor.process_response(response)
            
        except generation_types.StopCandidateException as e:
            logger.error(f"AI generated malformed function call: {e}")
            return NaviResponse(
                message_text="I got a bit confused trying to use my tools. Could you try saying that in a different way?",
                error="StopCandidateException"
            )
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return NaviResponse(
                message_text="Sorry, I encountered an error processing your message. Please try again!",
                error=str(e)
            )
    
    def _has_function_calls(self, response) -> bool:
        """Check if response contains function calls"""
        if not (response.candidates and 
                response.candidates[0].content and 
                response.candidates[0].content.parts):
            return False
        
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                return True
        return False
    
    def save_state(self):
        """Save current chat state"""
        try:
            # Apply built-in context management before saving
            try:
                current_history = self._convert_chat_history()
                managed_history = self._manage_chat_context_builtin(current_history)
                self.state_manager.state['chat_history'] = managed_history
            except Exception as e:
                logger.warning(f"Context management failed during save: {e}")
                # Fallback without context management
                self.state_manager.state['chat_history'] = self._convert_chat_history()
            
            self.state_manager.save_state()
            logger.info("State saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def _convert_chat_history(self) -> List[Dict[str, Any]]:
        """Convert Gemini chat history to state manager format"""
        state_history = []
        
        for msg in self.chat.history:
            msg_dict = {
                'role': msg.role,
                'parts': []
            }
            
            for part in msg.parts:
                part_dict = {}
                if hasattr(part, 'text') and part.text:
                    part_dict['text'] = part.text
                if hasattr(part, 'function_call') and part.function_call:
                    part_dict['function_call'] = {
                        'name': part.function_call.name,
                        'args': dict(part.function_call.args)
                    }
                if part_dict:
                    msg_dict['parts'].append(part_dict)
            
            # Add timestamp if missing
            if not hasattr(msg, 'timestamp'):
                msg_dict['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            if msg_dict['parts']:
                state_history.append(msg_dict)
        
        return state_history
    
    def _manage_chat_context_builtin(self, chat_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Built-in context management - simple token limit handling"""
        # Simple context management: keep last N messages if history is too long
        MAX_MESSAGES = 100  # Reasonable limit for context
        
        if len(chat_history) <= MAX_MESSAGES:
            return chat_history
        
        # Keep system messages and recent user/assistant exchanges
        managed_history = []
        recent_messages = chat_history[-MAX_MESSAGES:]
        
        # Add any system messages from the full history
        for msg in chat_history:
            if msg.get('role') == 'system':
                managed_history.append(msg)
        
        # Add recent messages (excluding any system messages already added)
        for msg in recent_messages:
            if msg.get('role') != 'system':
                managed_history.append(msg)
        
        logger.info(f"Context management: reduced {len(chat_history)} messages to {len(managed_history)}")
        return managed_history