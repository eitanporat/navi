"""
NAVI - Personal Productivity Assistant
A comprehensive goal, task, and calendar management system with AI assistance
"""

__version__ = "1.0.0"

# Core functionality
from .core import StateManager, NaviConversationEngine
from .core.auth import navi_auth
from .core.tools import tool_functions

# Interface factories
from .interfaces import (
    create_cli_interface, 
    create_telegram_interface, 
    create_web_interface
)

__all__ = [
    'StateManager', 
    'NaviConversationEngine',
    'navi_auth',
    'tool_functions',
    'create_cli_interface',
    'create_telegram_interface', 
    'create_web_interface'
]