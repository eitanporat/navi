"""
Business Logic Tools
Goal, task, calendar management, and utility functionality
"""

from .goals import (
    list_goals, add_goal, update_goal, check_goal_completion, list_goals_by_category,
    calculate_goal_progress, display_goals_with_progress, display_goal_summary,
    update_goal_progress_on_task_completion, update_user_goal_assessment
)
from .tasks import list_tasks, add_task, update_task
from .calendar_tools import list_events, add_event, update_event, delete_event, get_event_details, add_daily_event
from .utilities import (
    get_current_date, get_current_datetime, add_user_detail, 
    update_conversation_stage, add_progress_tracker, list_progress_trackers, 
    update_progress_tracker, add_insight
)

# Import the tool_functions dictionaries for compatibility
from .goals import goal_functions
from .tasks import task_functions 
from .calendar_tools import calendar_functions
from .utilities import utility_functions

# Combine all tool functions
tool_functions = {**goal_functions, **task_functions, **calendar_functions, **utility_functions}

__all__ = [
    # Goals
    'list_goals', 'add_goal', 'update_goal', 'check_goal_completion', 'list_goals_by_category',
    'calculate_goal_progress', 'display_goals_with_progress', 'display_goal_summary',
    'update_goal_progress_on_task_completion', 'update_user_goal_assessment',
    # Tasks
    'list_tasks', 'add_task', 'update_task', 
    # Calendar
    'list_events', 'add_event', 'update_event', 'delete_event', 'get_event_details', 'add_daily_event',
    # Utilities
    'get_current_date', 'get_current_datetime', 'add_user_detail', 
    'update_conversation_stage', 'add_progress_tracker', 'list_progress_trackers', 
    'update_progress_tracker', 'add_insight',
    # Combined functions dictionary
    'tool_functions'
]