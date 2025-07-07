"""
Utility Tools
Date/time, user details, conversation state, and progress tracking utilities
"""

from datetime import datetime
from ..state.manager import StateManager


def set_user_timezone(state_manager: StateManager, timezone: str):
    """Set user's timezone preference"""
    state = state_manager.get_state()
    if 'user_preferences' not in state:
        state['user_preferences'] = {}
    state['user_preferences']['timezone'] = timezone
    state_manager.save_state()
    return f"Timezone set to {timezone}"


def get_user_timezone(state_manager: StateManager) -> str:
    """Get user's timezone preference, with fallback to UTC"""
    state = state_manager.get_state()
    user_prefs = state.get('user_preferences', {})
    return user_prefs.get('timezone', 'UTC')


def validate_timezone(timezone_str: str) -> bool:
    """Validate if timezone string is valid"""
    try:
        import zoneinfo
        zoneinfo.ZoneInfo(timezone_str)
        return True
    except:
        # Common timezone fallbacks
        common_timezones = [
            'UTC', 'America/New_York', 'America/Los_Angeles', 'Europe/London', 
            'Europe/Paris', 'Asia/Tokyo', 'Asia/Jerusalem', 'Australia/Sydney',
            'Europe/Berlin', 'Asia/Shanghai', 'America/Chicago'
        ]
        return timezone_str in common_timezones


def get_current_date(state_manager: StateManager):
    """Get the current date in DD/MM/YY format using user's timezone"""
    user_tz = get_user_timezone(state_manager)
    try:
        import zoneinfo
        from datetime import datetime
        tz = zoneinfo.ZoneInfo(user_tz)
        now = datetime.now(tz)
    except:
        # Fallback to UTC if timezone parsing fails
        now = datetime.now()
    return f"Today's date: {now.strftime('%d/%m/%y')} (DD/MM/YY format, {user_tz} timezone)"


def get_current_datetime(state_manager: StateManager):
    """Get the current date and time in DD/MM/YY HH:MM format using user's timezone"""
    user_tz = get_user_timezone(state_manager)
    try:
        import zoneinfo
        from datetime import datetime
        tz = zoneinfo.ZoneInfo(user_tz)
        now = datetime.now(tz)
    except:
        # Fallback to UTC if timezone parsing fails
        now = datetime.now()
    return f"Current date and time: {now.strftime('%d/%m/%y %H:%M')} (DD/MM/YY HH:MM format, {user_tz} timezone)"


def add_user_detail(state_manager: StateManager, detail_key: str, detail_value: str):
    """Saves a fundamental detail about the user, like their name, age, or location."""
    state = state_manager.get_state()
    if 'user_details' not in state:
        state['user_details'] = {}
    
    state['user_details'][detail_key] = detail_value
    return f"Saved user detail: {detail_key} = {detail_value}."


def update_conversation_stage(state_manager: StateManager, new_stage: str):
    """Updates the current stage of the conversation."""
    state = state_manager.get_state()
    state['conversation_stage'] = new_stage
    return f"Stage updated to '{new_stage}'."


def add_progress_tracker(state_manager: StateManager, task_id: int, check_in_time: str):
    """
    Schedules a progress check-in for a task.
    """
    state = state_manager.get_state()
    tracker_id = state['metadata']['next_progress_tracker_id']
    state['metadata']['next_progress_tracker_id'] += 1

    new_tracker = {
        "tracker_id": tracker_id,
        "task_id": task_id,
        "check_in_time": check_in_time,
        "status": "PENDING"
    }

    state['progress_trackers'].append(new_tracker)
    return f"Progress tracker {tracker_id} scheduled for task {task_id} at {check_in_time}."


def list_progress_trackers(state_manager: StateManager):
    """Lists all progress trackers"""
    trackers = state_manager.get_state().get('progress_trackers', [])
    if not trackers:
        return "No progress trackers set up yet."
    
    tracker_list = []
    for tracker in trackers:
        task_id = tracker.get('task_id', 'Unknown')
        check_in_time = tracker.get('check_in_time', 'Unknown')
        status = tracker.get('status', 'Unknown')
        tracker_list.append(f"- Tracker ID {tracker['tracker_id']}: Task {task_id} at {check_in_time} (Status: {status})")
    
    return "\n" + "\n".join(tracker_list)


def update_progress_tracker(state_manager: StateManager, tracker_id: int, field_to_update: str, new_value: str):
    """Updates a specific field of a progress tracker"""
    state = state_manager.get_state()
    trackers = state.get('progress_trackers', [])
    
    for tracker in trackers:
        if tracker.get('tracker_id') == tracker_id:
            tracker[field_to_update] = new_value
            return f"Updated progress tracker {tracker_id}."
    
    return f"Error: Progress tracker with ID {tracker_id} not found."


def add_insight(state_manager: StateManager, insight_text: str, insight_type: str = "general"):
    """Adds an insight or reflection to the user's data"""
    state = state_manager.get_state()
    if 'insights' not in state:
        state['insights'] = []
    
    insight = {
        "insight_id": len(state['insights']) + 1,
        "text": insight_text,
        "type": insight_type,
        "timestamp": datetime.now().isoformat()
    }
    
    state['insights'].append(insight)
    return f"Added insight: {insight_text}"


# Utility functions dictionary for tool registration
utility_functions = {
    "get_current_date": get_current_date,
    "get_current_datetime": get_current_datetime,
    "add_user_detail": add_user_detail,
    "update_conversation_stage": update_conversation_stage,
    "add_progress_tracker": add_progress_tracker,
    "list_progress_trackers": list_progress_trackers,
    "update_progress_tracker": update_progress_tracker,
    "add_insight": add_insight,
    "set_user_timezone": set_user_timezone,
    "get_user_timezone": get_user_timezone,
}