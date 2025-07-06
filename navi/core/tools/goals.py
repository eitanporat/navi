"""
Goal Management Tools
Handles creation, updates, and listing of user goals
"""

from ..state.manager import StateManager


def _find_goal_by_id(goals, goal_id):
    """Finds a goal in a list by its ID."""
    for goal in goals:
        if goal.get('goal_id') == goal_id:
            return goal
    return None


def add_goal(state_manager: StateManager, title: str, category: str, description: str, end_condition: str, due_date: str, importance: str, urgency: str):
    """Adds a new goal to the state."""
    state = state_manager.get_state()
    goal_id = state['metadata']['next_goal_id']
    state['goals'].append({
        "goal_id": goal_id, "title": title, "category": category, "description": description,
        "end_condition": end_condition, "due_date": due_date, "importance": importance, "urgency": urgency,
        "bot_goal_assesment_percentage": 0, "user_goal_assesment_percentage": 0, "goal_log": []
    })
    state['metadata']['next_goal_id'] += 1
    return f"Added goal '{title}' with ID {goal_id}."


def update_goal(state_manager: StateManager, goal_id: int, field_to_update: str, new_value: str):
    """Updates a specific field of a goal."""
    state = state_manager.get_state()
    goal = _find_goal_by_id(state['goals'], goal_id)
    if goal:
        goal[field_to_update] = new_value
        return f"Updated goal {goal_id}."
    return f"Error: Goal with ID {goal_id} not found."


def calculate_goal_progress(state_manager: StateManager, goal_id: int):
    """Calculate bot assessment percentage based on completed tasks for a goal"""
    state = state_manager.get_state()
    tasks = state.get('tasks', [])
    
    # Get all tasks for this goal
    goal_tasks = [task for task in tasks if task.get('goal_id') == goal_id]
    
    if not goal_tasks:
        return 0
    
    # Count completed tasks
    completed_tasks = [task for task in goal_tasks if task.get('status') == 'COMPLETED']
    
    # Calculate percentage
    progress_percentage = int((len(completed_tasks) / len(goal_tasks)) * 100)
    return progress_percentage


def update_goal_progress_on_task_completion(state_manager: StateManager, goal_id: int, task_description: str):
    """Automatically update goal progress when a task is completed"""
    from datetime import datetime
    
    # Calculate new bot assessment percentage
    new_percentage = calculate_goal_progress(state_manager, goal_id)
    
    # Update bot assessment
    update_goal(state_manager, goal_id, 'bot_goal_assesment_percentage', str(new_percentage))
    
    # Add entry to goal log
    state = state_manager.get_state()
    goal = _find_goal_by_id(state['goals'], goal_id)
    
    if goal:
        log_entry = f"{datetime.now().strftime('%d/%m/%y')}: Completed '{task_description}' - Goal now {new_percentage}% complete"
        
        # Initialize goal_log if it doesn't exist
        if 'goal_log' not in goal:
            goal['goal_log'] = []
        
        goal['goal_log'].append(log_entry)
        
        return f"Goal progress updated: {new_percentage}% complete. Added to goal log."
    
    return "Error: Goal not found for progress update."


def update_user_goal_assessment(state_manager: StateManager, goal_id: int, user_percentage: int):
    """Update user's self-assessment of goal progress"""
    return update_goal(state_manager, goal_id, 'user_goal_assesment_percentage', str(user_percentage))


def list_goals(state_manager: StateManager):
    """Lists all goals from the state."""
    goals = state_manager.get_state().get('goals', [])
    if not goals:
        return "No goals have been set yet."
    return "\n" + "\n".join([f"- ID {g['goal_id']}: {g['title']} (Category: {g['category']})" for g in goals])


def check_goal_completion(state_manager: StateManager, goal_id: int):
    """Check if a goal has all required fields and return completion status"""
    goals = state_manager.get_state().get('goals', [])
    goal = _find_goal_by_id(goals, goal_id)
    
    if not goal:
        return f"Goal with ID {goal_id} not found.", False
    
    required_fields = ['title', 'category', 'description', 'end_condition', 'due_date', 'importance']
    missing_fields = []
    
    for field in required_fields:
        if not goal.get(field) or goal.get(field) == "":
            missing_fields.append(field)
    
    if missing_fields:
        return f"Goal ID {goal_id} is missing: {', '.join(missing_fields)}", False
    else:
        return f"Goal ID {goal_id} '{goal['title']}' is COMPLETE with all required fields.", True


def list_goals_by_category(state_manager: StateManager, category: str):
    """Filters and lists goals by a specific category."""
    goals = state_manager.get_state().get('goals', [])
    filtered_goals = [g for g in goals if g.get('category', '').lower() == category.lower()]
    if not filtered_goals:
        return f"No goals found in the '{category}' category."
    return "\n" + "\n".join([f"- ID {g['goal_id']}: {g['title']}" for g in filtered_goals])


def calculate_goal_progress(state_manager: StateManager, goal_id: int):
    """Calculate progress for a specific goal based on completed tasks"""
    state = state_manager.get_state()
    tasks = state.get('tasks', [])
    goal_tasks = [t for t in tasks if t.get('goal_id') == goal_id]
    
    if not goal_tasks:
        return 0  # No tasks = 0% progress
    
    completed_tasks = [t for t in goal_tasks if t.get('status') == 'COMPLETED']
    progress_percentage = (len(completed_tasks) / len(goal_tasks)) * 100
    return round(progress_percentage)


def display_goals_with_progress(state_manager: StateManager):
    """Display all goals with comprehensive data including progress bars"""
    state = state_manager.get_state()
    goals = state.get('goals', [])
    tasks = state.get('tasks', [])
    
    if not goals:
        return "🎯 **No goals have been set yet.**\n\nReady to create your first goal? Just tell me what you'd like to achieve!"
    
    result = "🎯 **Your Goals Overview**\n\n"
    
    for goal in goals:
        goal_id = goal.get('goal_id')
        title = goal.get('title', 'Untitled Goal')
        category = goal.get('category', 'Uncategorized')
        description = goal.get('description', 'No description')
        end_condition = goal.get('end_condition', 'No end condition defined')
        due_date = goal.get('due_date', 'No due date')
        importance = goal.get('importance', 'Not set')
        
        # Get bot assessment for progress bar (ensure it's an integer)
        bot_assessment = goal.get('bot_goal_assesment_percentage', 0)
        bot_assessment = int(bot_assessment) if bot_assessment else 0
        
        # Create progress bar (10 blocks) based on bot assessment
        filled_blocks = bot_assessment // 10
        empty_blocks = 10 - filled_blocks
        progress_bar = "█" * filled_blocks + "░" * empty_blocks
        
        # Count tasks
        goal_tasks = [t for t in tasks if t.get('goal_id') == goal_id]
        completed_tasks = [t for t in goal_tasks if t.get('status') == 'COMPLETED']
        pending_tasks = [t for t in goal_tasks if t.get('status') == 'PENDING']
        
        # Status emoji based on bot assessment
        if bot_assessment == 100:
            status_emoji = "🏆"
        elif bot_assessment >= 75:
            status_emoji = "🔥"
        elif bot_assessment >= 50:
            status_emoji = "⚡"
        elif bot_assessment >= 25:
            status_emoji = "🚀"
        else:
            status_emoji = "🎯"
        
        result += f"{status_emoji} **{title}** (#{goal_id})\n"
        result += f"📂 Category: {category} | ⭐ Importance: {importance}\n"
        result += f"📋 {description}\n"
        result += f"🎯 Success: {end_condition}\n"
        result += f"📅 Due: {due_date}\n\n"
        
        # Bot assessment (calculated from completed tasks) - already converted to int above
        result += f"🤖 **Bot Assessment: {bot_assessment}%** (based on completed tasks)\n"
        result += f"`{progress_bar}` {bot_assessment}%\n\n"
        
        # User assessment (self-reported)
        user_assessment = goal.get('user_goal_assesment_percentage', 0)
        user_assessment = int(user_assessment) if user_assessment else 0
        if user_assessment > 0:
            user_filled = user_assessment // 10
            user_empty = 10 - user_filled
            user_bar = "█" * user_filled + "░" * user_empty
            result += f"👤 **Your Assessment: {user_assessment}%** (self-reported)\n"
            result += f"`{user_bar}` {user_assessment}%\n\n"
        else:
            result += f"👤 **Your Assessment:** Not set (ask user during next check-in)\n\n"
        
        result += f"📝 **Tasks:** {len(goal_tasks)} total | "
        result += f"✅ {len(completed_tasks)} completed | "
        result += f"⏳ {len(pending_tasks)} pending\n\n"
        
        # Goal log (recent progress milestones)
        goal_log = goal.get('goal_log', [])
        if goal_log:
            result += f"📈 **Recent Progress:**\n"
            # Show last 3 log entries
            for log_entry in goal_log[-3:]:
                result += f"   • {log_entry}\n"
            result += "\n"
        
        result += "─" * 40 + "\n\n"
    
    return result.strip()


def display_goal_summary(state_manager: StateManager):
    """Display a quick summary of goals by category with progress"""
    state = state_manager.get_state()
    goals = state.get('goals', [])
    
    if not goals:
        return "No goals set yet. Ready to create your first goal?"
    
    # Group by category
    categories = {}
    for goal in goals:
        category = goal.get('category', 'Uncategorized')
        if category not in categories:
            categories[category] = []
        categories[category].append(goal)
    
    result = "🎯 **Goals Summary by Category**\n\n"
    
    for category, category_goals in categories.items():
        total_progress = sum(calculate_goal_progress(state_manager, g['goal_id']) for g in category_goals)
        avg_progress = round(total_progress / len(category_goals)) if category_goals else 0
        
        # Category emoji mapping
        category_emojis = {
            'Health': '💪',
            'Finance': '💰', 
            'Relationships': '❤️',
            'Career': '🚀',
            'Hobbies': '🎨',
            'Learning': '📚',
            'Personal Development': '🌱',
            'Causes': '🌍'
        }
        
        emoji = category_emojis.get(category, '📂')
        result += f"{emoji} **{category}**: {len(category_goals)} goals (avg {avg_progress}% progress)\n"
        
        for goal in category_goals:
            progress = calculate_goal_progress(state_manager, goal['goal_id'])
            result += f"   • {goal['title']} - {progress}%\n"
        
        result += "\n"
    
    return result.strip()


def update_goal_progress_on_task_completion(state_manager: StateManager, goal_id: int, task_title: str):
    """Update goal progress and log when a task is completed"""
    from datetime import datetime
    
    state = state_manager.get_state()
    goal = _find_goal_by_id(state['goals'], goal_id)
    
    if not goal:
        return f"Goal with ID {goal_id} not found."
    
    # Calculate new bot assessment based on completed tasks
    new_bot_assessment = calculate_goal_progress(state_manager, goal_id)
    goal['bot_goal_assesment_percentage'] = new_bot_assessment
    
    # Add log entry
    current_time = datetime.now().strftime('%d/%m/%y %H:%M')
    log_entry = f"[{current_time}] Task completed: '{task_title}' → Bot assessment: {new_bot_assessment}%"
    goal['goal_log'].append(log_entry)
    
    # Return progress display
    return display_goals_with_progress(state_manager)


def update_user_goal_assessment(state_manager: StateManager, goal_id: int, user_percentage: int):
    """Update user's self-assessment of goal progress"""
    from datetime import datetime
    
    state = state_manager.get_state()
    goal = _find_goal_by_id(state['goals'], goal_id)
    
    if not goal:
        return f"Goal with ID {goal_id} not found."
    
    # Validate percentage
    if not (0 <= user_percentage <= 100):
        return "Please provide a percentage between 0 and 100."
    
    # Update user assessment
    old_assessment = goal.get('user_goal_assesment_percentage', 0)
    goal['user_goal_assesment_percentage'] = user_percentage
    
    # Add log entry
    current_time = datetime.now().strftime('%d/%m/%y %H:%M')
    log_entry = f"[{current_time}] User updated self-assessment: {old_assessment}% → {user_percentage}%"
    goal['goal_log'].append(log_entry)
    
    return f"Updated your assessment for '{goal['title']}' to {user_percentage}%. Thanks for the feedback!"


# Goal functions dictionary for tool registration
goal_functions = {
    "add_goal": add_goal,
    "update_goal": update_goal,
    "list_goals": list_goals,
    "check_goal_completion": check_goal_completion,
    "list_goals_by_category": list_goals_by_category,
    "calculate_goal_progress": calculate_goal_progress,
    "display_goals_with_progress": display_goals_with_progress,
    "display_goal_summary": display_goal_summary,
    "update_goal_progress_on_task_completion": update_goal_progress_on_task_completion,
    "update_user_goal_assessment": update_user_goal_assessment,
}