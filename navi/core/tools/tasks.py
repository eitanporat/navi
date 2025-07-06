"""
Task Management Tools
Handles creation, updates, and listing of user tasks
"""

from ..state.manager import StateManager


def _find_task_by_id(tasks, task_id):
    """Finds a task in a list by its ID."""
    for task in tasks:
        if task.get('task_id') == task_id:
            return task
    return None


def add_task(state_manager: StateManager, goal_id: int, title: str, description: str, measure_of_success: str, start_time: str, end_time: str, importance: str, urgency: str, due_date: str = None):
    """Adds a new task to a goal and automatically creates calendar event."""
    state = state_manager.get_state()
    task_id = state['metadata']['next_task_id']
    
    # Create the task
    task = {
        "task_id": task_id, "goal_id": goal_id, "title": title, "description": description, "measure_of_success": measure_of_success,
        "start_time": start_time, "end_time": end_time, "due_date": due_date, "importance": importance,
        "urgency": urgency, "status": "PENDING", "task_log": [], "calendar_event_id": None
    }
    state['tasks'].append(task)
    state['metadata']['next_task_id'] += 1
    
    # Automatically add to Google Calendar
    calendar_result = None
    try:
        from .calendar_tools import add_event
        calendar_result = add_event(state_manager, title, start_time, end_time)
        
        # Extract event ID from calendar result if successful
        if "Event ID:" in calendar_result:
            event_id = calendar_result.split("Event ID: ")[1].strip()
            task["calendar_event_id"] = event_id
        
    except Exception as e:
        calendar_result = f"Task created but calendar integration failed: {str(e)}"
    
    # Return combined result
    task_result = f"Added task '{title}' with ID {task_id}."
    if calendar_result and "successfully" in calendar_result:
        return f"{task_result} Calendar event created: {calendar_result}"
    elif calendar_result:
        return f"{task_result} Calendar warning: {calendar_result}"
    else:
        return task_result


def update_task(state_manager: StateManager, task_id: int, field_to_update: str, new_value: str):
    """Updates a specific field of a task, e.g., its status."""
    state = state_manager.get_state()
    task = _find_task_by_id(state['tasks'], task_id)
    if not task:
        return f"Error: Task with ID {task_id} not found."
    
    # Store old value to check if status changed to COMPLETED
    old_value = task.get(field_to_update)
    task[field_to_update] = new_value
    
    # If task was just marked as completed, update goal progress
    if (field_to_update.lower() == 'status' and 
        new_value.upper() == 'COMPLETED' and 
        old_value.upper() != 'COMPLETED'):
        
        goal_id = task.get('goal_id')
        task_title = task.get('title', task.get('description', 'Unknown task'))
        
        if goal_id:
            # Import here to avoid circular imports
            from .goals import update_goal_progress_on_task_completion
            progress_display = update_goal_progress_on_task_completion(state_manager, goal_id, task_title)
            
            return f"🎉 Task completed: '{task_title}'!\n\n{progress_display}"
    
    return f"Updated task {task_id}."


def list_tasks(state_manager: StateManager, filter_by_status: str = None):
    """Lists all tasks, optionally filtering by status (e.g., 'PENDING', 'COMPLETED')."""
    tasks = state_manager.get_state().get('tasks', [])
    if filter_by_status:
        tasks = [t for t in tasks if t.get('status', '').lower() == filter_by_status.lower()]
    if not tasks:
        message = "No tasks found."
        if filter_by_status:
            message = f"No tasks with status '{filter_by_status}' found."
        return message
    return "\n" + "\n".join([f"- ID {t['task_id']}: {t.get('title', t['description'])} (Status: {t['status']})" for t in tasks])


def display_tasks_for_user(state_manager: StateManager):
    """Display tasks in a user-friendly format without technical details"""
    from .goals import _find_goal_by_id
    
    tasks = state_manager.get_state().get('tasks', [])
    goals = state_manager.get_state().get('goals', [])
    
    if not tasks:
        return "You don't have any tasks yet! Want to add some?"
    
    # Group tasks by status for better organization
    pending_tasks = [t for t in tasks if t.get('status', '').upper() == 'PENDING']
    in_progress_tasks = [t for t in tasks if t.get('status', '').upper() == 'IN_PROGRESS']
    completed_tasks = [t for t in tasks if t.get('status', '').upper() == 'COMPLETED']
    
    result = []
    
    # Show active tasks (pending + in progress)
    active_tasks = pending_tasks + in_progress_tasks
    if active_tasks:
        result.append("📋 *Your current tasks:*")
        for task in active_tasks:
            # Find associated goal
            goal_name = ""
            if task.get('goal_id'):
                goal = _find_goal_by_id(goals, task['goal_id'])
                if goal:
                    goal_name = f" (for {goal['title']})"
            
            # Use emojis for status instead of text
            status_emoji = "🔄" if task.get('status') == 'IN_PROGRESS' else "⏳"
            task_title = task.get('title', task['description'])
            result.append(f"{status_emoji} {task_title}{goal_name}")
    
    # Show completed tasks if any
    if completed_tasks:
        result.append("\n✅ *Recently completed:*")
        for task in completed_tasks[-3:]:  # Show last 3 completed
            goal_name = ""
            if task.get('goal_id'):
                goal = _find_goal_by_id(goals, task['goal_id'])
                if goal:
                    goal_name = f" (for {goal['title']})"
            task_title = task.get('title', task['description'])
            result.append(f"✅ {task_title}{goal_name}")
    
    if not result:
        return "You don't have any tasks yet! Want to add some?"
    
    return "\n".join(result)


# Task functions dictionary for tool registration
task_functions = {
    "add_task": add_task,
    "update_task": update_task,
    "list_tasks": list_tasks,
    "display_tasks_for_user": display_tasks_for_user,
}