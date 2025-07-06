"""
CLI Interface Implementation
Command-line interface using Rich UI and the unified conversation engine
"""

import asyncio
import logging
from typing import Dict, Any

from ..adapters import NaviCLIInterface
from ...core.engine.conversation import NaviConversationEngine


logger = logging.getLogger(__name__)


def run_cli_interface(user_email: str):
    """Run the CLI interface for a specific user"""
    from ..adapters import create_cli_interface
    
    try:
        # Create CLI interface
        cli_interface = create_cli_interface(user_email)
        
        # Run the conversation loop
        cli_interface.run_conversation_loop()
        
    except Exception as e:
        logger.error(f"Failed to run CLI interface: {e}")
        print(f"Error starting CLI interface: {e}")


if __name__ == "__main__":
    # For testing purposes
    import sys
    if len(sys.argv) > 1:
        user_email = sys.argv[1]
    else:
        user_email = input("Enter user email: ").strip()
    
    run_cli_interface(user_email)