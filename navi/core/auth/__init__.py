"""
Authentication Module
Google OAuth and Telegram authentication
"""

from .base import NaviAuth, navi_auth
from .telegram_auth import TelegramSimpleAuth

__all__ = ['NaviAuth', 'navi_auth', 'TelegramSimpleAuth']