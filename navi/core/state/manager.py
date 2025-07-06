"""
State Manager
Handles loading and saving the application state to and from user-specific state files
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class StateManager:
    """Handles loading and saving the application state to and from user-specific state files."""

    def __init__(self, filepath='state.json', user_email=None):
        if user_email:
            # Use user-specific state file
            user_dir = os.path.join('users', user_email)
            if not os.path.exists(user_dir):
                os.makedirs(user_dir, exist_ok=True)
            self.filepath = os.path.join(user_dir, 'state.json')
        else:
            # Use global state file (fallback)
            self.filepath = filepath
            
        self.user_email = user_email
        self.state = self.load_state()

    def get_default_state(self):
        """Returns the default structure for the state."""
        return {
            "metadata": {"next_goal_id": 1, "next_task_id": 1, "next_progress_tracker_id": 1},
            "user_details": {},
            "user_preferences": {"timezone": None},
            "conversation_stage": "Introduction & Onboarding",
            "goals": [],
            "tasks": [],
            "progress_trackers": [],
            "hourly_reflections": [],
            "chat_history": []
        }

    def load_state(self):
        """
        Loads state from the JSON file, validating its structure and cleaning it before returning.
        """
        logger.debug("Attempting to load state from %s", self.filepath)
        if not os.path.exists(self.filepath):
            logger.debug("State file not found. Creating a new one.")
            state = self.get_default_state()
            self.state = state # Set internal state before saving
            self.save_state()
            return state
        
        try:
            with open(self.filepath, 'r') as f:
                raw_file_content = f.read()
                if not raw_file_content.strip():
                    logger.debug("state.json is empty. Starting with default state.")
                    return self.get_default_state()
                
                f.seek(0)
                loaded_data = json.load(f)

                # --- THE CRITICAL FIX ---
                # Ensure the loaded data is a dictionary, not a list or something else.
                if not isinstance(loaded_data, dict):
                    logger.warning("state.json contains invalid data (not a dictionary). Starting fresh.")
                    return self.get_default_state()

                logger.debug("JSON data loaded from state.json:\n%s", json.dumps(loaded_data, indent=2))

                if 'chat_history' in loaded_data and isinstance(loaded_data['chat_history'], list):
                    clean_history = self._clean_history_data(loaded_data['chat_history'])
                    loaded_data['chat_history'] = clean_history
                
                # Ensure all required fields exist (add missing fields from default state)
                default_state = self.get_default_state()
                for key, default_value in default_state.items():
                    if key not in loaded_data:
                        loaded_data[key] = default_value
                        logger.info(f"Added missing field '{key}' to existing state")
                
                logger.debug("State data after cleaning (to be used by app):\n%s", json.dumps(loaded_data, indent=2))

                return loaded_data

        except (json.JSONDecodeError, IOError) as e:
            logger.error("Error loading or parsing state file: %s. Starting with a default state.", e)
            return self.get_default_state()

    def save_state(self):
        """Saves the current internal state to the JSON file."""
        serializable_state = self._serialize_live_state(self.state)
        
        logger.debug("Saving the following state to state.json:\n%s", json.dumps(serializable_state, indent=2))
        
        with open(self.filepath, 'w') as f:
            json.dump(serializable_state, f, indent=4)

    def get_state(self):
        """Returns a direct reference to the current in-memory state object."""
        return self.state

    def _serialize_live_state(self, state_dict):
        """
        Creates a copy of the state from live objects that is safe for JSON.
        """
        serializable_copy = {}
        for key, value in state_dict.items():
            if key == 'chat_history':
                history_as_dicts = [self._content_obj_to_dict(c) for c in value]
                serializable_copy[key] = self._clean_history_data(history_as_dicts)
            else:
                serializable_copy[key] = value
        
        return serializable_copy
    
    def _content_obj_to_dict(self, content):
        """
        Converts a live Content object OR a dict to a serializable dict, adding a timestamp if missing.
        This ensures all history entries are timestamped upon saving.
        """
        if isinstance(content, dict):
            # It's an existing dictionary from a previous session
            content_dict = content
        else:
            # It's a new Content object from this session, convert it to a dictionary
            role = getattr(content, 'role', None)
            parts = getattr(content, 'parts', [])
            
            part_dicts = []
            for p in parts:
                part_dict = {}
                if hasattr(p, 'text') and p.text:
                    part_dict['text'] = p.text
                if hasattr(p, 'function_call') and p.function_call:
                    part_dict['function_call'] = {
                        'name': p.function_call.name,
                        'args': dict(p.function_call.args)
                    }
                if part_dict:
                    part_dicts.append(part_dict)

            if not part_dicts:
                return {} # Return empty dict for invalid/empty content

            content_dict = {"role": role, "parts": part_dicts}

        # Ensure a timestamp exists, adding one if it's a new message
        if 'timestamp' not in content_dict:
            content_dict['timestamp'] = datetime.utcnow().isoformat()
        
        return content_dict

    def _clean_history_data(self, history_data):
        """Takes a list of dictionaries and filters out any invalid entries."""
        clean_history = []
        if not isinstance(history_data, list):
            return []

        for content in history_data:
            if not isinstance(content, dict) or 'role' not in content or 'parts' not in content:
                continue
            
            if not isinstance(content.get('parts'), list):
                continue

            valid_parts = [part for part in content['parts'] if isinstance(part, dict) and part]
            
            if valid_parts:
                # Re-assign valid parts and append the whole entry (including timestamp)
                content['parts'] = valid_parts
                clean_history.append(content)
        return clean_history
    
    def reset_all_data(self):
        """Reset all user data including state, goals, tasks, and conversation history"""
        logger.info(f"Resetting all data for user {self.user_email}")
        
        # Reset to default state
        self.state = self.get_default_state()
        self.save_state()
        
        # Clear other user files if they exist
        if self.user_email:
            user_dir = os.path.join('users', self.user_email)
            
            # Clear additional user files
            files_to_clear = ['api_calls.json', 'preferences.json']
            for filename in files_to_clear:
                filepath = os.path.join(user_dir, filename)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        logger.info(f"Cleared {filepath}")
                    except Exception as e:
                        logger.error(f"Error clearing {filepath}: {e}")
        
        logger.info(f"Reset completed for user {self.user_email}")