"""
NAVI Authentication System - Simple Google OAuth integration
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from typing import Optional, Dict, Any

# Google API scopes needed - use broad scopes for full access
SCOPES = [
    'https://www.googleapis.com/auth/calendar',  # Full calendar access (includes events)
    'https://www.googleapis.com/auth/tasks'      # Full tasks access
]


class NaviAuth:
    """Simple authentication system for NAVI"""
    
    def __init__(self):
        # Use path relative to project root
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        
        # Prefer desktop credentials, fallback to web credentials
        desktop_creds = os.path.join(self.project_root, 'credentials_desktop.json')
        web_creds = os.path.join(self.project_root, 'credentials.json')
        
        if os.path.exists(desktop_creds):
            self.credentials_file = desktop_creds
        else:
            self.credentials_file = web_creds
            
        self.users_dir = os.path.join(self.project_root, 'users')
        self.current_user = None
        
    def get_google_credentials(self, user_email: str) -> Optional[Credentials]:
        """Get Google credentials for a user"""
        token_path = os.path.join(self.users_dir, user_email, 'token.json')
        
        if os.path.exists(token_path):
            try:
                with open(token_path, 'r') as f:
                    token_data = json.load(f)
                    
                    # Check if refresh_token is missing
                    if 'refresh_token' not in token_data:
                        print(f"Warning: Token for {user_email} missing refresh_token")
                        print(f"User needs to re-authenticate with: python -c \"from navi.core.auth import navi_auth; navi_auth.authenticate_user('{user_email}')\"")
                        return None
                    
                    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
                    
                    # Refresh if needed (this should work now with refresh_token)
                    if creds.expired and creds.refresh_token:
                        print(f"Refreshing expired token for {user_email}...")
                        creds.refresh(Request())
                        self._save_credentials(user_email, creds)
                        print(f"✅ Token refreshed successfully for {user_email}")
                    
                    return creds
            except Exception as e:
                print(f"Error loading credentials for {user_email}: {e}")
                return None
        
        return None
    
    def authenticate_user(self, user_email: str = None) -> Optional[Credentials]:
        """Authenticate user with Google OAuth with refresh token support"""
        if not os.path.exists(self.credentials_file):
            return None
            
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, SCOPES)
            
            # CRITICAL: Request offline access to get refresh token
            # Use run_local_server with specific port that matches redirect URI
            creds = flow.run_local_server(
                port=8080,
                access_type='offline',  # This gets us the refresh token
                prompt='consent'        # Forces consent screen to ensure refresh token
            )
            
            if user_email:
                self._save_credentials(user_email, creds)
            
            return creds
        except Exception as e:
            print(f"OAuth authentication failed: {e}")
            return None
    
    def get_calendar_service(self, user_email: str = None):
        """Get Google Calendar service for a user"""
        # Import build function once at the top of method
        from googleapiclient.discovery import build
        
        # FIRST: Try OAuth credentials (user-specific tokens)
        if user_email:
            creds = self.get_google_credentials(user_email)
            if creds:
                try:
                    service = build('calendar', 'v3', credentials=creds)
                    print(f"✅ Using OAuth credentials for {user_email}")
                    return service
                except Exception as e:
                    print(f"OAuth calendar service failed: {e}")
        
        # FALLBACK: Try service account methods
        try:
            # Try service account with JSON file
            service_account_path = os.path.join(self.project_root, 'service_account.json')
            if os.path.exists(service_account_path):
                from google.oauth2 import service_account
                
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path,
                    scopes=['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/tasks']
                )
                service = build('calendar', 'v3', credentials=credentials)
                print("✅ Using service account credentials")
                return service
            
            # Try Application Default Credentials
            try:
                from google.auth import default
                credentials, project = default(scopes=['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/tasks'])
                service = build('calendar', 'v3', credentials=credentials)
                print("✅ Using Application Default Credentials")
                return service
            except Exception as adc_error:
                print(f"Application Default Credentials failed: {adc_error}")
            
        except Exception as sa_error:
            print(f"Service account auth failed: {sa_error}")
            
            if not user_email:
                raise Exception("No authenticated user found and service account auth failed")
                
            creds = self.get_google_credentials(user_email)
            if not creds:
                raise Exception(f"No valid credentials found for user {user_email} and service account auth failed")
                
            try:
                service = build('calendar', 'v3', credentials=creds)
                return service
            except Exception as e:
                raise Exception(f"Failed to build calendar service: {e}")

    def _save_credentials(self, user_email: str, creds: Credentials):
        """Save credentials to user directory"""
        user_dir = os.path.join(self.users_dir, user_email)
        os.makedirs(user_dir, exist_ok=True)
        
        token_path = os.path.join(user_dir, 'token.json')
        with open(token_path, 'w') as f:
            # Handle both old and new format
            if hasattr(creds, 'to_json'):
                json.dump(json.loads(creds.to_json()), f)
            else:
                # For direct credentials dict
                creds_dict = {
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes
                }
                json.dump(creds_dict, f)

    def initialize_authentication(self) -> bool:
        """Initialize authentication by selecting or authenticating a user"""
        try:
            users = self.list_existing_users()
            
            if not users:
                print("No existing users found. Let's authenticate a new user.")
                user_email = input("Enter your email address: ").strip()
                creds = self.authenticate_user(user_email)
                if creds:
                    self.current_user = user_email
                    return True
                return False
            
            if len(users) == 1:
                # Single user - auto-select
                user_email = users[0]['email']
                print(f"Using existing user: {user_email}")
                creds = self.get_google_credentials(user_email)
                if creds:
                    self.current_user = user_email
                    return True
                else:
                    # Re-authenticate if credentials are invalid
                    print("Credentials expired. Re-authenticating...")
                    creds = self.authenticate_user(user_email)
                    if creds:
                        self.current_user = user_email
                        return True
                return False
            
            # Multiple users - let user choose
            user_email = self.get_user_selection()
            if user_email:
                creds = self.get_google_credentials(user_email)
                if creds:
                    self.current_user = user_email
                    return True
                else:
                    # Re-authenticate if credentials are invalid
                    print("Credentials expired. Re-authenticating...")
                    creds = self.authenticate_user(user_email)
                    if creds:
                        self.current_user = user_email
                        return True
            return False
            
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False

    def list_existing_users(self) -> list:
        """List existing authenticated users"""
        users = []
        if not os.path.exists(self.users_dir):
            return users
        
        for user_dir in os.listdir(self.users_dir):
            user_path = os.path.join(self.users_dir, user_dir)
            token_path = os.path.join(user_path, 'token.json')
            
            if os.path.isdir(user_path) and os.path.exists(token_path):
                # Extract name from email (simple approach)
                name = user_dir.split('@')[0].replace('.', ' ').title()
                users.append({
                    'email': user_dir,
                    'name': name,
                    'path': user_path
                })
        
        return users

    def get_user_selection(self) -> Optional[str]:
        """Let user select from existing users or add new one"""
        users = self.list_existing_users()
        
        if not users:
            return None
        
        print("\nAvailable users:")
        for i, user in enumerate(users, 1):
            print(f"  {i}. {user['name']} ({user['email']})")
        print(f"  {len(users) + 1}. Add new user")
        
        try:
            choice = input(f"\nSelect user (1-{len(users) + 1}): ").strip()
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(users):
                return users[choice_num - 1]['email']
            elif choice_num == len(users) + 1:
                user_email = input("Enter email for new user: ").strip()
                creds = self.authenticate_user(user_email)
                if creds:
                    return user_email
                return None
            else:
                print("Invalid selection.")
                return None
                
        except (ValueError, KeyboardInterrupt):
            print("Selection cancelled.")
            return None


# Global authentication instance
navi_auth = NaviAuth()