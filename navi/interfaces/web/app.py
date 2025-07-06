"""
NAVI Web UI - Simple Flask interface for viewing NAVI data
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import json
import os
from datetime import datetime

# Local imports - updated for new package structure
from ...core.state.manager import StateManager
from ...core.auth.base import navi_auth
from ...core.tools import list_events, list_goals, list_tasks
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import secrets

# Allow HTTP for localhost development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# Configure session for HTTPS
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# OAuth 2.0 configuration
# Use path relative to project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
GOOGLE_CLIENT_SECRETS_FILE = os.path.join(PROJECT_ROOT, "credentials.json")
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks',
    'openid',
    'email',
    'profile'
]

# OAuth client config from environment variables
def get_oauth_config():
    """Get OAuth configuration from environment variables"""
    base_url = os.environ.get('BASE_URL', 'http://localhost:4999')
    return {
        "web": {
            "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
            "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"{base_url}/auth/callback"]
        }
    }

def is_test_mode():
    """Check if app is running in test mode (no auth required)"""
    return os.environ.get('NAVI_TEST_MODE', 'false').lower() == 'true'

def get_test_user_email():
    """Get test user email for development"""
    return os.environ.get('NAVI_TEST_USER_EMAIL', 'test@example.com')

def is_authenticated():
    """Check if user is authenticated"""
    if is_test_mode():
        return True
    result = 'user_email' in session and session['user_email']
    print(f"DEBUG is_authenticated: session={dict(session)}, result={result}, test_mode={is_test_mode()}")
    return result

def get_current_user_state():
    """Get state manager for current authenticated user"""
    if not is_authenticated():
        return None
    
    if is_test_mode():
        user_email = get_test_user_email()
    else:
        user_email = session['user_email']
    
    state_manager = StateManager(user_email=user_email)
    return state_manager

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
@require_auth
def home():
    """Home page with navigation"""
    if is_test_mode():
        user_name = "Test User"
    else:
        user_name = session.get('user_name')
    return render_template('home.html', user_name=user_name)

@app.route('/login')
def login():
    """Login page"""
    if is_authenticated():
        return redirect(url_for('home'))
    if is_test_mode():
        # In test mode, redirect directly to home
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/auth/google')
def auth_google():
    """Start Google OAuth flow"""
    oauth_config = get_oauth_config()
    flow = Flow.from_client_config(
        oauth_config,
        scopes=SCOPES
    )
    # Force HTTPS for production
    callback_url = url_for('auth_callback', _external=True)
    if os.environ.get('BASE_URL'):
        # Use BASE_URL for production deployment
        callback_url = os.environ.get('BASE_URL').rstrip('/') + '/auth/callback'
    flow.redirect_uri = callback_url
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force consent screen to get refresh token
    )
    
    session['state'] = state
    return redirect(authorization_url)

@app.route('/auth/callback')
def auth_callback():
    """Handle Google OAuth callback"""
    try:
        # Manual token exchange to bypass scope validation
        from urllib.parse import parse_qs, urlparse
        import requests
        
        # Extract code from callback URL
        parsed_url = urlparse(request.url)
        params = parse_qs(parsed_url.query)
        code = params.get('code', [None])[0]
        
        if not code:
            return "Error: No authorization code received", 400
        
        # Get client credentials from environment
        oauth_config = get_oauth_config()
        client_id = oauth_config['web']['client_id']
        client_secret = oauth_config['web']['client_secret']
        redirect_uri = url_for('auth_callback', _external=True)
        if os.environ.get('BASE_URL'):
            # Use BASE_URL for production deployment
            redirect_uri = os.environ.get('BASE_URL').rstrip('/') + '/auth/callback'
        
        # Exchange code for tokens manually
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(token_url, data=token_data)
        tokens = response.json()
        
        if 'error' in tokens:
            return f"Token exchange error: {tokens['error']}", 400
        
        # Create credentials object manually
        from google.oauth2.credentials import Credentials
        credentials = Credentials(
            token=tokens['access_token'],
            refresh_token=tokens.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=tokens.get('scope', '').split()
        )
        
        # Get user info
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        user_email = user_info.get('email')
        if not user_email:
            return "Error: Could not get user email", 400
        
        # Save credentials
        navi_auth._save_credentials(user_email, credentials)
        
        # Set session
        session['user_email'] = user_email
        session['user_name'] = user_info.get('name', user_email)
        
        return redirect(url_for('home'))
        
    except Exception as e:
        return f"Authentication error: {str(e)}", 400

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/conversations')
@require_auth
def conversations():
    """Display chat history"""
    user_name = session.get('user_name')
    return render_template('conversations.html', user_name=user_name)

@app.route('/api-calls')
@require_auth
def api_calls():
    """Display API/tool usage"""
    user_name = session.get('user_name')
    return render_template('api_calls.html', user_name=user_name)

@app.route('/goals-tasks')
@require_auth
def goals_tasks():
    """Display goals and tasks"""
    user_name = session.get('user_name')
    return render_template('goals_tasks.html', user_name=user_name)

@app.route('/calendar')
@require_auth
def calendar_view():
    """Display calendar with tasks"""
    if is_test_mode():
        user_name = "Test User"
    else:
        user_name = session.get('user_name')
    return render_template('calendar.html', user_name=user_name)

@app.route('/profile')
@require_auth
def profile():
    """Display user profile"""
    user_name = session.get('user_name')
    return render_template('profile.html', user_name=user_name)

@app.route('/progress-trackers')
@require_auth
def progress_trackers():
    """Display progress trackers page"""
    user_name = session.get('user_name')
    return render_template('progress_trackers.html', user_name=user_name)

@app.route('/settings')
@require_auth
def settings():
    """Display settings page"""
    user_email = session.get('user_email')
    user_name = session.get('user_name')
    bot_username = os.environ.get('TELEGRAM_BOT_USERNAME', 'your_navi_bot')
    
    return render_template('settings.html', 
                         user_email=user_email,
                         user_name=user_name,
                         bot_username=bot_username)

# API Endpoints for data

@app.route('/api/conversations')
@require_auth
def api_conversations():
    """Get chat history data with tool calls in chronological order"""
    try:
        sm = get_current_user_state()
        if not sm:
            return jsonify({'error': 'Not authenticated'}), 401
            
        state = sm.get_state()
        chat_history = state.get('chat_history', [])
        tool_executions = state.get('tool_execution_log', [])
        gemini_api_log = state.get('gemini_api_log', [])
        
        # Combine chat messages and tool calls in chronological order
        all_items = []
        
        # Process chat history
        model_message_index = 0  # Track model messages for API log matching
        for msg in chat_history:
            if msg.get('role') in ['user', 'model']:
                # Extract text from parts
                text_content = ""
                function_calls = []
                
                for part in msg.get('parts', []):
                    if isinstance(part, dict):
                        if 'text' in part:
                            text_content += part['text']
                        elif 'function_call' in part:
                            function_calls.append(part['function_call'])
                
                # Get the correct timestamp based on message role
                actual_timestamp = msg.get('timestamp', '')
                
                if msg.get('role') == 'user' and text_content:
                    # For user messages: extract actual conversation time from content
                    import re
                    time_match = re.search(r'Current Time: ([0-9T:.-]+)', text_content)
                    if time_match:
                        actual_timestamp = time_match.group(1)
                        # Ensure it has timezone info
                        if not actual_timestamp.endswith('+00:00') and not 'Z' in actual_timestamp:
                            actual_timestamp += '+00:00'
                
                elif msg.get('role') == 'model':
                    # For model messages: use Gemini API log timestamp
                    if model_message_index < len(gemini_api_log):
                        actual_timestamp = gemini_api_log[model_message_index].get('timestamp', actual_timestamp)
                        model_message_index += 1
                
                # Parse timestamp properly
                if actual_timestamp:
                    try:
                        from datetime import datetime
                        # Parse UTC timestamp
                        dt = datetime.fromisoformat(actual_timestamp.replace(' UTC', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        formatted_time = actual_timestamp
                else:
                    formatted_time = 'Unknown time'
                
                all_items.append({
                    'type': 'message',
                    'role': msg.get('role'),
                    'content': text_content,
                    'function_calls': function_calls,
                    'timestamp': actual_timestamp,
                    'formatted_timestamp': formatted_time
                })
        
        # Process tool executions
        for tool_exec in tool_executions:
            timestamp = tool_exec.get('timestamp', '')
            if timestamp:
                try:
                    from datetime import datetime
                    # Parse UTC timestamp
                    dt = datetime.fromisoformat(timestamp.replace(' UTC', '+00:00'))
                    formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    formatted_time = timestamp
            else:
                formatted_time = 'Unknown time'
            
            all_items.append({
                'type': 'tool_call',
                'tool_name': tool_exec.get('tool_name', ''),
                'args': tool_exec.get('args', {}),
                'result': tool_exec.get('result', ''),
                'timestamp': timestamp,
                'formatted_timestamp': formatted_time
            })
        
        # Sort all items by timestamp (convert to datetime for proper sorting)
        def parse_timestamp_for_sorting(item):
            timestamp = item.get('timestamp', '')
            if timestamp:
                try:
                    # Parse ISO timestamp
                    return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    # Fallback to string sorting if parsing fails
                    return datetime.min
            return datetime.min
        
        all_items.sort(key=parse_timestamp_for_sorting)
        
        return jsonify(all_items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/api-calls')
@require_auth
def api_api_calls():
    """Get comprehensive API call data including tool executions and Gemini API calls"""
    try:
        sm = get_current_user_state()
        if not sm:
            return jsonify({'error': 'Not authenticated'}), 401
            
        state = sm.get_state()
        chat_history = state.get('chat_history', [])
        
        # Get tool execution logs (includes results!)
        tool_executions = state.get('tool_execution_log', [])
        
        # Get Gemini API call logs
        gemini_api_calls = state.get('gemini_api_log', [])
        
        # Combine all API-related data
        all_api_calls = []
        
        # Add tool executions with results
        for tool_exec in tool_executions:
            all_api_calls.append({
                'type': 'tool_execution',
                'name': tool_exec.get('tool_name', ''),
                'args': tool_exec.get('args', {}),
                'result': tool_exec.get('result', ''),
                'timestamp': tool_exec.get('timestamp', 'Unknown time')
            })
        
        # Add Gemini API calls
        for api_call in gemini_api_calls:
            all_api_calls.append({
                'type': 'gemini_api_call',
                'name': api_call.get('call_type', ''),
                'input_preview': api_call.get('input_preview', ''),
                'response_preview': api_call.get('response_preview', ''),
                'response_time_ms': api_call.get('response_time_ms', 0),
                'tokens_in': api_call.get('tokens_in', 0),
                'tokens_out': api_call.get('tokens_out', 0),
                'timestamp': api_call.get('timestamp', 'Unknown time')
            })
        
        
        # Sort by timestamp (newest first)
        all_api_calls.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify(all_api_calls)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/goals-tasks')
@require_auth
def api_goals_tasks():
    """Get goals and tasks data with progress information"""
    try:
        sm = get_current_user_state()
        if not sm:
            return jsonify({'error': 'Not authenticated'}), 401
            
        state = sm.get_state()
        
        goals = state.get('goals', [])
        tasks = state.get('tasks', [])
        
        # Import the enhanced goal functions
        from ...core.tools.goals import calculate_goal_progress
        
        # Group tasks by goal and add progress data
        goals_with_tasks = []
        for goal in goals:
            goal_tasks = [task for task in tasks if task.get('goal_id') == goal.get('goal_id')]
            
            # Calculate progress data
            bot_assessment = goal.get('bot_goal_assesment_percentage', 0)
            bot_assessment = int(bot_assessment) if bot_assessment else 0
            
            user_assessment = goal.get('user_goal_assesment_percentage', 0)
            user_assessment = int(user_assessment) if user_assessment else 0
            
            # Progress percentages (no need for emoji bars, we'll use CSS)
            
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
            
            # Count task statuses
            completed_tasks = [t for t in goal_tasks if t.get('status') == 'COMPLETED']
            pending_tasks = [t for t in goal_tasks if t.get('status') == 'PENDING']
            
            # Get goal log
            goal_log = goal.get('goal_log', [])
            
            # Enhanced goal data
            enhanced_goal = dict(goal)
            enhanced_goal.update({
                'bot_assessment': bot_assessment,
                'user_assessment': user_assessment,
                'status_emoji': status_emoji,
                'completed_count': len(completed_tasks),
                'pending_count': len(pending_tasks),
                'total_tasks': len(goal_tasks),
                'goal_log': goal_log[-3:] if goal_log else []  # Last 3 entries
            })
            
            goals_with_tasks.append({
                'goal': enhanced_goal,
                'tasks': goal_tasks
            })
        
        return jsonify({
            'goals': goals_with_tasks,
            'orphan_tasks': [task for task in tasks if not any(task.get('goal_id') == g.get('goal_id') for g in goals)]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar')
@require_auth
def api_calendar():
    """Get calendar data - ONLY EVENTS (no tasks per UI requirements)"""
    try:
        sm = get_current_user_state()
        if not sm:
            return jsonify({'error': 'Not authenticated'}), 401
            
        # Calendar items will only contain events, no tasks
        calendar_items = []
        
        # Try to get Google Calendar events
        events_count = 0
        try:
            from datetime import date, timedelta
            today = date.today()
            start_date = today.strftime("%d/%m/%y")
            end_date = (today + timedelta(days=30)).strftime("%d/%m/%y")
            
            import logging
            app.logger.info(f"DEBUG: Calendar API calling list_events with start_date={start_date}, end_date={end_date}")
            events_result = list_events(sm, start_date, end_date)
            app.logger.info(f"DEBUG: list_events returned: {events_result}")
            app.logger.info(f"DEBUG: events_result type: {type(events_result)}")
            app.logger.info(f"DEBUG: events_result length: {len(events_result) if events_result else 'None'}")
            
            # Parse events from the result string
            if events_result and "Events from" in events_result:
                print(f"DEBUG: Parsing events from result string")
                # Split by newlines and parse each event
                lines = events_result.strip().split('\n')
                print(f"DEBUG: Found {len(lines)} lines to parse")
                for line in lines[1:]:  # Skip the header line
                    print(f"DEBUG: Processing line: '{line}'")
                    if line.strip() and line.startswith('- '):
                        # Parse event line format: "- 2025-07-13T14:30:00+03:00 to 2025-07-13T15:30:00+03:00: Event Title"
                        event_line = line[2:]  # Remove "- "
                        if ': ' in event_line:
                            datetime_part, title = event_line.split(': ', 1)
                            print(f"DEBUG: Parsed event - datetime_part: '{datetime_part}', title: '{title}'")
                            
                            # Parse start and end times
                            if ' to ' in datetime_part:
                                start_str, end_str = datetime_part.split(' to ', 1)
                            else:
                                # Fallback for old format or all-day events
                                start_str = datetime_part
                                end_str = datetime_part
                            
                            print(f"DEBUG: Parsed times - start: '{start_str}', end: '{end_str}'")
                            
                            # Create event item with unique ID
                            event_item = {
                                'type': 'event',
                                'title': title,
                                'start': start_str,
                                'end': end_str,
                                'all_day': False,
                                'id': f'event_{events_count}',
                                'html_link': f'https://calendar.google.com/calendar/u/0/r/eventedit?text={title}'
                            }
                            calendar_items.append(event_item)
                            events_count += 1
                            print(f"DEBUG: Added event to calendar_items: {event_item}")
                        else:
                            print(f"DEBUG: Skipping malformed event line (no colon): '{event_line}'")
            else:
                app.logger.info(f"DEBUG: No events found or unexpected result format. events_result type: {type(events_result)}")
                app.logger.info(f"DEBUG: Full events_result content: {repr(events_result)}")
                
                # Try to test calendar integration with a simple test
                app.logger.info("DEBUG: Testing calendar authentication...")
                try:
                    from ...core.tools.calendar_tools import _get_calendar_service
                    service = _get_calendar_service(sm)
                    if service:
                        app.logger.info("DEBUG: Calendar service obtained successfully")
                    else:
                        app.logger.info("DEBUG: Calendar service is None - authentication issue")
                except Exception as auth_error:
                    app.logger.error(f"DEBUG: Calendar authentication error: {auth_error}")
                    
        except Exception as e:
            print(f"Error fetching calendar events: {e}")
            import traceback
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            # Calendar integration optional - don't fail the whole request
        
        # Add debug info to the response for troubleshooting
        debug_info = {
            'start_date': start_date if 'start_date' in locals() else 'not_set',
            'end_date': end_date if 'end_date' in locals() else 'not_set', 
            'events_result': events_result if 'events_result' in locals() else 'not_set',
            'events_result_type': str(type(events_result)) if 'events_result' in locals() else 'not_set'
        }
        
        result = {
            'items': calendar_items,
            'events_count': events_count,
            'debug': debug_info
        }
        print(f"DEBUG: Final calendar API response: {result}")
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user')
@require_auth
def api_user():
    """Get current user info"""
    try:
        sm = get_current_user_state()
        if not sm:
            return jsonify({'error': 'Not authenticated'}), 401
            
        state = sm.get_state()
        user_details = state.get('user_details', {})
        
        return jsonify({
            'email': session.get('user_email'),
            'name': session.get('user_name'),
            'details': user_details,
            'conversation_stage': state.get('conversation_stage', '')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress-trackers')
@require_auth
def api_progress_trackers():
    """Get progress trackers data with task and goal information"""
    try:
        sm = get_current_user_state()
        if not sm:
            return jsonify({'error': 'Not authenticated'}), 401
            
        state = sm.get_state()
        trackers = state.get('progress_trackers', [])
        tasks = state.get('tasks', [])
        goals = state.get('goals', [])
        
        # Helper function to find task by ID
        def find_task_by_id(task_id):
            for task in tasks:
                if task.get('task_id') == task_id:
                    return task
            return None
        
        # Helper function to find goal by ID
        def find_goal_by_id(goal_id):
            for goal in goals:
                if goal.get('goal_id') == goal_id:
                    return goal
            return None
        
        # Separate task-specific trackers from general check-ins
        task_trackers = []
        general_checkins = []
        
        for tracker in trackers:
            task_id = tracker.get('task_id')
            
            if task_id == 0 or task_id == 0.0:
                # General check-in (no specific task)
                general_checkins.append({
                    'tracker_id': tracker.get('tracker_id'),
                    'task_id': task_id,
                    'check_in_time': tracker.get('check_in_time'),
                    'status': tracker.get('status', 'PENDING')
                })
            else:
                # Task-specific tracker
                task = find_task_by_id(task_id)
                if task:
                    goal = find_goal_by_id(task.get('goal_id'))
                    task_trackers.append({
                        'tracker_id': tracker.get('tracker_id'),
                        'task_id': task_id,
                        'check_in_time': tracker.get('check_in_time'),
                        'status': tracker.get('status', 'PENDING'),
                        'task': {
                            'title': task.get('title', task.get('description', 'Untitled Task')),
                            'description': task.get('description', ''),
                            'goal_id': task.get('goal_id'),
                            'status': task.get('status', 'UNKNOWN')
                        },
                        'goal': {
                            'title': goal.get('title', 'Unknown Goal') if goal else 'No Goal',
                            'category': goal.get('category', 'Uncategorized') if goal else 'Uncategorized'
                        } if goal else None
                    })
                else:
                    # Task not found, treat as orphaned tracker
                    task_trackers.append({
                        'tracker_id': tracker.get('tracker_id'),
                        'task_id': task_id,
                        'check_in_time': tracker.get('check_in_time'),
                        'status': tracker.get('status', 'PENDING'),
                        'task': {
                            'title': f'Task #{task_id} (Not Found)',
                            'description': 'This task no longer exists',
                            'goal_id': None,
                            'status': 'MISSING'
                        },
                        'goal': None
                    })
        
        return jsonify({
            'task_trackers': task_trackers,
            'general_checkins': general_checkins
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-auth-code', methods=['POST'])
def generate_auth_code():
    """Generate a new authentication code for Telegram bot"""
    try:
        # Debug session
        print(f"DEBUG: Session contents: {dict(session)}")
        print(f"DEBUG: User email: {session.get('user_email')}")
        print(f"DEBUG: Is authenticated: {is_authenticated()}")
        import random
        import string
        import logging
        from datetime import datetime, timedelta
        
        # Setup auth logging
        auth_logger = logging.getLogger('auth')
        auth_log_path = os.path.join(PROJECT_ROOT, 'auth.log')
        auth_handler = logging.FileHandler(auth_log_path)
        auth_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        auth_logger.addHandler(auth_handler)
        auth_logger.setLevel(logging.INFO)
        
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Generate 6-digit code
        code = ''.join(random.choices(string.digits, k=6))
        
        # Set expiration time (30 minutes)
        expiry = datetime.now() + timedelta(minutes=30)
        
        # Load existing codes
        codes_file = os.path.join(PROJECT_ROOT, 'telegram_auth_codes.json')
        try:
            with open(codes_file, 'r') as f:
                codes_data = json.load(f)
        except FileNotFoundError:
            codes_data = {}
        
        # Store new code
        codes_data[code] = {
            'email': user_email,
            'expires_at': expiry.isoformat(),
            'used': False
        }
        
        # Save codes
        with open(codes_file, 'w') as f:
            json.dump(codes_data, f, indent=2)
        
        # Log the generated code
        auth_logger.info(f"WEB_UI: Generated auth code '{code}' for user {user_email}, expires at {expiry.isoformat()}")
        
        return jsonify({
            'code': code,
            'expiry': expiry.strftime('%H:%M:%S'),
            'success': True
        })
    except Exception as e:
        auth_logger.error(f"WEB_UI: Error generating auth code for {user_email}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-auth-code')
def get_current_auth_code():
    """Get current valid authentication code"""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Load codes
        codes_file = os.path.join(PROJECT_ROOT, 'telegram_auth_codes.json')
        try:
            with open(codes_file, 'r') as f:
                codes_data = json.load(f)
        except FileNotFoundError:
            return jsonify({'code': None, 'expiry': None})
        
        # Find valid code for this user
        from datetime import datetime
        now = datetime.now()
        
        for code, data in codes_data.items():
            if (data['email'] == user_email and 
                not data['used'] and 
                datetime.fromisoformat(data['expires_at']) > now):
                
                expiry_time = datetime.fromisoformat(data['expires_at'])
                return jsonify({
                    'code': code,
                    'expiry': expiry_time.strftime('%H:%M:%S')
                })
        
        return jsonify({'code': None, 'expiry': None})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_web_app():
    """Run the web application"""
    port = int(os.environ.get('PORT', 4999))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    base_url = os.environ.get('BASE_URL', f'http://localhost:{port}')
    
    print(f"🚀 Starting NAVI Web UI with OAuth authentication on {base_url}")
    print("📝 Users will be redirected to login page and must authenticate with Google")
    app.run(debug=debug, host='0.0.0.0', port=port)


if __name__ == '__main__':
    run_web_app()