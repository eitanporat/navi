"""
Calendar Integration Tools
Handles Google Calendar operations including events, scheduling
"""

import datetime
from ..state.manager import StateManager
from .utilities import get_user_timezone


def _get_calendar_service(state_manager: StateManager = None):
    """Get authenticated Google Calendar service using integrated auth"""
    # Import locally to avoid circular imports during reorganization
    from ..auth.base import navi_auth
    
    # Try to get user email from state manager
    user_email = None
    if state_manager:
        # Check if the state manager has user_email attribute
        if hasattr(state_manager, 'user_email'):
            user_email = state_manager.user_email
        else:
            # Try to extract from state manager's state
            state = state_manager.get_state()
            user_details = state.get('user_details', {})
            user_email = user_details.get('email')
    
    return navi_auth.get_calendar_service(user_email)


def _parse_datetime(date_string, for_api_query=False):
    """Parse date string in DD/MM/YY HH:MM format to ISO datetime with timezone
    
    Args:
        date_string: Date string in DD/MM/YY HH:MM format
        for_api_query: If True, adds UTC timezone for Google Calendar API queries
                      If False, uses local timezone for event creation
    """
    try:
        # Handle DD/MM/YY HH:MM format
        if len(date_string.split()) == 2:
            date_part, time_part = date_string.split()
            day, month, year = date_part.split('/')
            hour, minute = time_part.split(':')
            
            # Convert 2-digit year to 4-digit
            if len(year) == 2:
                year = '20' + year
            
            dt = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute))
        else:
            # Handle DD/MM/YY format (date only)
            day, month, year = date_string.split('/')
            
            # Convert 2-digit year to 4-digit
            if len(year) == 2:
                year = '20' + year
                
            dt = datetime.datetime(int(year), int(month), int(day))
        
        # Return appropriate timezone format
        if for_api_query:
            # For Google Calendar API queries, we need UTC timezone
            return dt.isoformat() + 'Z'
        else:
            # For event creation, we still need to add timezone info, but treat as local time
            # Adding 'Z' but the calling context should specify timezone separately
            return dt.isoformat()
    except Exception as e:
        print(f"Date parsing error: {e} for input: {date_string}")
        return None


def list_events(state_manager: StateManager, start_date: str, end_date: str):
    """Lists calendar events between start_date and end_date (DD/MM/YY format)"""
    try:
        service = _get_calendar_service(state_manager)
    except Exception as e:
        return f"❌ Calendar service error: {str(e)}"
    
    if not service:
        return "❌ Google Calendar authentication issue. Please try restarting Navi or use the '/auth' command to re-authenticate."
    
    try:
        start_iso = _parse_datetime(start_date + " 00:00", for_api_query=True)
        end_iso = _parse_datetime(end_date + " 23:59", for_api_query=True)
        
        if not start_iso or not end_iso:
            return "Error: Invalid date format. Please use DD/MM/YY format."
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_iso,
            timeMax=end_iso,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"No events found between {start_date} and {end_date}."
        
        event_list = []
        for event in events:
            start_time = event['start'].get('dateTime', event['start'].get('date'))
            end_time = event['end'].get('dateTime', event['end'].get('date'))
            summary = event.get('summary', 'No Title')
            event_list.append(f"- {start_time} to {end_time}: {summary}")
        
        return f"Events from {start_date} to {end_date}:\n" + "\n".join(event_list)
        
    except Exception as e:
        return f"Error fetching calendar events: {str(e)}"


def add_event(state_manager: StateManager, event_description: str, start_time: str, end_time: str, recurrence: str = None):
    """Adds a new event to Google Calendar
    
    Args:
        state_manager: State manager instance
        event_description: Description of the event
        start_time: Start time in DD/MM/YY HH:MM format (or DD/MM/YY for all-day)
        end_time: End time in DD/MM/YY HH:MM format (or DD/MM/YY for all-day)
        recurrence: Optional recurrence rule (e.g., "DAILY", "WEEKLY", "MONTHLY")
    """
    try:
        service = _get_calendar_service(state_manager)
    except Exception as e:
        return f"❌ Calendar service error: {str(e)}"
    
    if not service:
        return "❌ Google Calendar authentication issue. Please try restarting Navi or use the '/auth' command to re-authenticate."
    
    try:
        # Check if this is an all-day event (no time specified)
        is_all_day = len(start_time.split()) == 1 and len(end_time.split()) == 1
        
        if is_all_day:
            # All-day event - use date format
            try:
                # Parse DD/MM/YY format for all-day events
                day, month, year = start_time.split('/')
                if len(year) == 2:
                    year = '20' + year
                start_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                
                day, month, year = end_time.split('/')
                if len(year) == 2:
                    year = '20' + year
                end_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                
                event = {
                    'summary': event_description,
                    'start': {
                        'date': start_date,
                    },
                    'end': {
                        'date': end_date,
                    },
                }
            except Exception:
                return "Error: Invalid date format for all-day event. Please use DD/MM/YY format."
        else:
            # Timed event
            start_iso = _parse_datetime(start_time)
            end_iso = _parse_datetime(end_time)
            
            if not start_iso or not end_iso:
                return "Error: Invalid time format. Please use DD/MM/YY HH:MM format."
            
            event = {
                'summary': event_description,
                'start': {
                    'dateTime': start_iso,
                    'timeZone': get_user_timezone(state_manager),
                },
                'end': {
                    'dateTime': end_iso,
                    'timeZone': get_user_timezone(state_manager),
                },
            }
        
        # Add recurrence if specified
        if recurrence:
            recurrence_rule = None
            if recurrence.upper() == "DAILY":
                recurrence_rule = "RRULE:FREQ=DAILY"
            elif recurrence.upper() == "WEEKLY":
                recurrence_rule = "RRULE:FREQ=WEEKLY"
            elif recurrence.upper() == "MONTHLY":
                recurrence_rule = "RRULE:FREQ=MONTHLY"
            elif recurrence.upper().startswith("DAILY_COUNT="):
                # For limited daily recurrence like "DAILY_COUNT=30" for 30 days
                count = recurrence.upper().split("=")[1]
                recurrence_rule = f"RRULE:FREQ=DAILY;COUNT={count}"
            elif recurrence.upper().startswith("RRULE:"):
                # Custom RRULE
                recurrence_rule = recurrence.upper()
            
            if recurrence_rule:
                event['recurrence'] = [recurrence_rule]
        
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        
        recurrence_info = f" (recurring {recurrence.lower()})" if recurrence else ""
        event_type = "All-day event" if is_all_day else "Event"
        return f"{event_type} '{event_description}' created successfully for {start_time} to {end_time}{recurrence_info}. Event ID: {created_event.get('id')}"
        
    except Exception as e:
        return f"Error creating calendar event: {str(e)}"


def add_daily_event(state_manager: StateManager, event_description: str, start_date: str, duration_days: int = 30):
    """Creates a daily recurring all-day event (perfect for habits like 'read 10 pages daily')
    
    Args:
        state_manager: State manager instance
        event_description: Description of the daily event (e.g., "Read 10 pages")
        start_date: Start date in DD/MM/YY format
        duration_days: How many days to repeat (default 30 days)
    """
    try:
        service = _get_calendar_service(state_manager)
    except Exception as e:
        return f"❌ Calendar service error: {str(e)}"
    
    if not service:
        return "❌ Google Calendar authentication issue. Please try restarting Navi or use the '/auth' command to re-authenticate."
    
    try:
        # Parse start date - handle the format from get_current_date()
        if "Today's date:" in start_date:
            # Extract just the date part from "Today's date: 06/07/25 (DD/MM/YY format)"
            date_part = start_date.split(":")[1].strip().split()[0]
            day, month, year = date_part.split('/')
        else:
            # Direct date format
            day, month, year = start_date.split('/')
        
        if len(year) == 2:
            year = '20' + year
        start_date_iso = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # For all-day events, end date is the same as start date
        event = {
            'summary': event_description,
            'start': {
                'date': start_date_iso,
            },
            'end': {
                'date': start_date_iso,
            },
            'recurrence': [f"RRULE:FREQ=DAILY;COUNT={duration_days}"]
        }
        
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        
        return f"Daily habit '{event_description}' created successfully! Will repeat for {duration_days} days starting {start_date}. Event ID: {created_event.get('id')}"
        
    except Exception as e:
        return f"Error creating daily event: {str(e)}"


def update_event(state_manager: StateManager, event_id: str, field_to_update: str, new_value: str):
    """Updates a specific field of an existing calendar event"""
    try:
        service = _get_calendar_service(state_manager)
    except Exception as e:
        return f"❌ Calendar service error: {str(e)}"
    
    if not service:
        return "❌ Google Calendar authentication issue. Please try restarting Navi or use the '/auth' command to re-authenticate."
    
    try:
        # First, get the existing event
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Update the specified field
        if field_to_update.lower() == 'title' or field_to_update.lower() == 'summary':
            event['summary'] = new_value
        elif field_to_update.lower() == 'description':
            event['description'] = new_value
        elif field_to_update.lower() == 'start_time':
            start_iso = _parse_datetime(new_value)
            if not start_iso:
                return "Error: Invalid time format. Please use DD/MM/YY HH:MM format."
            event['start']['dateTime'] = start_iso
            event['start']['timeZone'] = get_user_timezone(state_manager)
        elif field_to_update.lower() == 'end_time':
            end_iso = _parse_datetime(new_value)
            if not end_iso:
                return "Error: Invalid time format. Please use DD/MM/YY HH:MM format."
            event['end']['dateTime'] = end_iso
            event['end']['timeZone'] = get_user_timezone(state_manager)
        elif field_to_update.lower() == 'location':
            event['location'] = new_value
        else:
            return f"Error: Field '{field_to_update}' is not supported for updates. Supported fields: title, description, start_time, end_time, location"
        
        # Update the event
        updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        
        return f"Event '{event.get('summary', 'Unknown')}' updated successfully. Field '{field_to_update}' changed to '{new_value}'."
        
    except Exception as e:
        if "Not Found" in str(e):
            return f"Error: Event with ID '{event_id}' not found."
        return f"Error updating calendar event: {str(e)}"


def delete_event(state_manager: StateManager, event_id: str):
    """Deletes a calendar event by its ID"""
    try:
        service = _get_calendar_service(state_manager)
    except Exception as e:
        return f"❌ Calendar service error: {str(e)}"
    
    if not service:
        return "❌ Google Calendar authentication issue. Please try restarting Navi or use the '/auth' command to re-authenticate."
    
    try:
        # First, get the event details to show what we're deleting
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        event_title = event.get('summary', 'Untitled Event')
        
        # Delete the event
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        
        return f"Event '{event_title}' (ID: {event_id}) deleted successfully."
        
    except Exception as e:
        if "Not Found" in str(e):
            return f"Error: Event with ID '{event_id}' not found."
        return f"Error deleting calendar event: {str(e)}"


def get_event_details(state_manager: StateManager, event_id: str):
    """Gets detailed information about a specific calendar event"""
    try:
        service = _get_calendar_service(state_manager)
    except Exception as e:
        return f"❌ Calendar service error: {str(e)}"
    
    if not service:
        return "❌ Google Calendar authentication issue. Please try restarting Navi or use the '/auth' command to re-authenticate."
    
    try:
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Format the event details
        title = event.get('summary', 'Untitled Event')
        description = event.get('description', 'No description')
        location = event.get('location', 'No location specified')
        
        # Format start and end times
        start_time = event['start'].get('dateTime', event['start'].get('date', 'Unknown'))
        end_time = event['end'].get('dateTime', event['end'].get('date', 'Unknown'))
        
        # Get attendees if any
        attendees = event.get('attendees', [])
        attendee_list = ', '.join([a.get('email', 'Unknown') for a in attendees]) if attendees else 'No attendees'
        
        # Get creator info
        creator = event.get('creator', {}).get('email', 'Unknown')
        
        # Get last modified time
        updated = event.get('updated', 'Unknown')
        
        details = f"""📅 Event Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 Title: {title}
🕐 Start: {start_time}
🕐 End: {end_time}
📍 Location: {location}
📝 Description: {description}
👥 Attendees: {attendee_list}
👤 Creator: {creator}
🔄 Last Updated: {updated}
🆔 Event ID: {event_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return details
        
    except Exception as e:
        if "Not Found" in str(e):
            return f"Error: Event with ID '{event_id}' not found."
        return f"Error fetching calendar event details: {str(e)}"


# Calendar functions dictionary for tool registration
calendar_functions = {
    "list_events": list_events,
    "add_event": add_event,
    "update_event": update_event,
    "delete_event": delete_event,
    "get_event_details": get_event_details,
    "add_daily_event": add_daily_event,
}