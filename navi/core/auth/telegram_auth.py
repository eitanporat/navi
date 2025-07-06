"""
Simple Code-Based Authentication for NAVI Telegram Bot
Generates authentication codes in web UI that users can send to bot
"""

import os
import json
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any


class TelegramSimpleAuth:
    """Simple authentication system using codes generated in web UI"""
    
    def __init__(self):
        # Use path relative to project root
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        self.auth_codes_file = os.path.join(self.project_root, 'telegram_auth_codes.json')
        self.telegram_mappings_file = os.path.join(self.project_root, 'telegram_mappings.json')
        self.codes_data = self._load_codes_data()
        self.telegram_mappings = self._load_telegram_mappings()
    
    def _load_codes_data(self) -> Dict[str, Any]:
        """Load authentication codes from file"""
        if os.path.exists(self.auth_codes_file):
            try:
                with open(self.auth_codes_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_codes_data(self):
        """Save authentication codes to file"""
        try:
            with open(self.auth_codes_file, 'w') as f:
                json.dump(self.codes_data, f, indent=2)
        except Exception as e:
            print(f"Error saving codes data: {e}")
    
    def _load_telegram_mappings(self) -> Dict[str, Any]:
        """Load Telegram user mappings from file"""
        if os.path.exists(self.telegram_mappings_file):
            try:
                with open(self.telegram_mappings_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_telegram_mappings(self):
        """Save Telegram user mappings to file"""
        try:
            with open(self.telegram_mappings_file, 'w') as f:
                json.dump(self.telegram_mappings, f, indent=2)
        except Exception as e:
            print(f"Error saving telegram mappings: {e}")
    
    def generate_auth_code(self, user_email: str) -> str:
        """Generate a new authentication code for a user"""
        # Generate 6-digit code
        code = ''.join(secrets.choice(string.digits) for _ in range(6))
        
        # Store with expiration (30 minutes)
        expires_at = (datetime.now() + timedelta(minutes=30)).isoformat()
        
        # Remove any existing codes for this user
        self.codes_data = {k: v for k, v in self.codes_data.items() 
                          if v.get('user_email') != user_email}
        
        # Store new code
        self.codes_data[code] = {
            'user_email': user_email,
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at,
            'used': False
        }
        
        self._save_codes_data()
        return code
    
    def get_user_auth_code(self, user_email: str) -> Optional[str]:
        """Get the current valid authentication code for a user"""
        now = datetime.now()
        
        for code, data in self.codes_data.items():
            if (data.get('user_email') == user_email and 
                not data.get('used', False) and
                datetime.fromisoformat(data.get('expires_at', '')) > now):
                return code
        
        return None
    
    def verify_auth_code(self, telegram_user_id: int, code: str) -> Tuple[bool, Optional[str], str]:
        """
        Verify authentication code from Telegram user
        Returns (success, email, message)
        """
        import logging
        
        # Setup auth logging
        auth_logger = logging.getLogger('auth')
        auth_log_path = os.path.join(self.project_root, 'auth.log')
        auth_handler = logging.FileHandler(auth_log_path)
        auth_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        if not auth_logger.handlers:  # Avoid duplicate handlers
            auth_logger.addHandler(auth_handler)
        auth_logger.setLevel(logging.INFO)
        
        # Reload codes data to get latest
        self.codes_data = self._load_codes_data()
        
        auth_logger.info(f"TELEGRAM_BOT: User {telegram_user_id} attempting auth with code '{code}'")
        auth_logger.info(f"TELEGRAM_BOT: Available codes in system: {list(self.codes_data.keys())}")
        
        if code not in self.codes_data:
            auth_logger.warning(f"TELEGRAM_BOT: Code '{code}' not found in system. Available codes: {list(self.codes_data.keys())}")
            return False, None, "Invalid authentication code"
        
        code_data = self.codes_data[code]
        auth_logger.info(f"TELEGRAM_BOT: Found code data: {code_data}")
        
        # Check if already used
        if code_data.get('used', False):
            auth_logger.warning(f"TELEGRAM_BOT: Code '{code}' already used")
            return False, None, "Authentication code has already been used"
        
        # Check expiration
        expires_at_str = code_data.get('expires_at', '')
        if not expires_at_str:
            auth_logger.error(f"TELEGRAM_BOT: Code '{code}' has no expiration time")
            return False, None, "Invalid authentication code format"
            
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            now = datetime.now()
            auth_logger.info(f"TELEGRAM_BOT: Code expires at {expires_at}, current time {now}")
            
            if now > expires_at:
                auth_logger.warning(f"TELEGRAM_BOT: Code '{code}' expired at {expires_at}")
                return False, None, "Authentication code has expired"
        except ValueError as e:
            auth_logger.error(f"TELEGRAM_BOT: Error parsing expiration time '{expires_at_str}': {e}")
            return False, None, "Invalid authentication code format"
        
        # Mark as used
        code_data['used'] = True
        code_data['used_at'] = datetime.now().isoformat()
        code_data['telegram_user_id'] = telegram_user_id
        self._save_codes_data()
        
        # Get user email
        user_email = code_data.get('email') or code_data.get('user_email')  # Handle both field names
        
        # Store Telegram mapping
        self.telegram_mappings[str(telegram_user_id)] = {
            'email': user_email,
            'authenticated_at': datetime.now().isoformat(),
            'auth_method': 'simple_code'
        }
        self._save_telegram_mappings()
        
        auth_logger.info(f"TELEGRAM_BOT: Successfully authenticated user {telegram_user_id} with email {user_email}")
        
        return True, user_email, "Authentication successful"
    
    def is_telegram_user_authenticated(self, telegram_user_id: int) -> bool:
        """Check if Telegram user is authenticated"""
        return str(telegram_user_id) in self.telegram_mappings
    
    def clear_user_mapping(self, telegram_user_id: int) -> bool:
        """Clear Telegram user mapping"""
        user_id_str = str(telegram_user_id)
        if user_id_str in self.telegram_mappings:
            del self.telegram_mappings[user_id_str]
            self._save_telegram_mappings()
            return True
        return False
    
    def get_user_email_from_telegram(self, telegram_user_id: int) -> Optional[str]:
        """Get user email from Telegram user ID"""
        mapping = self.telegram_mappings.get(str(telegram_user_id))
        return mapping.get('email') if mapping else None
    
    def remove_telegram_user_auth(self, telegram_user_id: int) -> bool:
        """Remove Telegram user authentication mapping"""
        try:
            user_id_str = str(telegram_user_id)
            if user_id_str in self.telegram_mappings:
                del self.telegram_mappings[user_id_str]
                self._save_telegram_mappings()
                return True
            return False
        except Exception as e:
            print(f"Error removing Telegram auth for user {telegram_user_id}: {e}")
            return False
    
    def cleanup_expired_codes(self):
        """Remove expired authentication codes"""
        now = datetime.now()
        expired_codes = []
        
        for code, data in self.codes_data.items():
            expires_at = datetime.fromisoformat(data.get('expires_at', ''))
            if now > expires_at:
                expired_codes.append(code)
        
        for code in expired_codes:
            del self.codes_data[code]
        
        if expired_codes:
            self._save_codes_data()
    
    def list_existing_users(self) -> list:
        """List existing NAVI users (those with user directories)"""
        users = []
        users_dir = os.path.join(self.project_root, 'users')
        
        if os.path.exists(users_dir):
            for user_email in os.listdir(users_dir):
                user_dir = os.path.join(users_dir, user_email)
                if os.path.isdir(user_dir) and '@' in user_email:
                    # Check if user has preferences (indicating they've authenticated)
                    preferences_file = os.path.join(user_dir, 'preferences.json')
                    if os.path.exists(preferences_file):
                        try:
                            with open(preferences_file, 'r') as f:
                                prefs = json.load(f)
                                users.append({
                                    'email': user_email,
                                    'name': prefs.get('user_name', user_email),
                                    'created_at': prefs.get('created_at', '')
                                })
                        except Exception:
                            pass
        
        return users


# Global instance
telegram_simple_auth = TelegramSimpleAuth()