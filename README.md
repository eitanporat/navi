# NAVI - Personal Productivity Assistant

NAVI is an AI-powered personal productivity assistant that helps you manage goals, tasks, and calendars through both a web interface and Telegram bot integration. Built with Python and powered by Google's Gemini AI.

## Features

- 🎯 **Goal Management**: Set, track, and achieve personal goals with AI guidance
- ✅ **Task Management**: Break goals into actionable tasks with progress tracking
- 📅 **Calendar Integration**: Google Calendar sync and event management
- 🤖 **Telegram Bot**: Conversational AI assistant via Telegram
- 🌐 **Web Interface**: Modern web UI for comprehensive management
- 📊 **Progress Tracking**: Automated check-ins and reflection prompts
- 🔐 **Secure Authentication**: Google OAuth 2.0 integration

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud Project with enabled APIs
- Telegram Bot Token
- Gemini API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone git@github.com:eitanporat/navi.git
   cd navi
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv navi_venv
   source navi_venv/bin/activate  # Linux/Mac
   # or
   navi_venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys and configuration
   # ⚠️ CRITICAL: Never commit .env files with real credentials!
   ```

5. **Set up Google OAuth:**
   - Follow instructions in `OAUTH_SETUP.md`
   - Place `credentials.json` in project root

6. **Run NAVI:**
   ```bash
   ./start_navi.sh
   # or
   python run_all.py
   ```

## Deployment

### Google Compute Engine (Recommended)

```bash
# Deploy to GCE with HTTPS
./deploy_to_gce.sh
```

### Google Cloud Run

```bash
# Serverless deployment
./deploy_cloudrun.sh
```

### Docker

```bash
# Build and run with Docker
docker build -t navi-app .
docker run -p 4999:4999 --env-file .env navi-app
```

## Usage

### Web Interface
- Visit: `http://localhost:4999` (or your deployed URL)
- Authenticate with Google
- Manage goals, tasks, and calendar events

### Telegram Bot
1. Get authentication code from web interface Settings
2. Send `/start` to your Telegram bot
3. Send the 6-digit code to link your account
4. Start conversing with NAVI!

## Project Structure

```
navi/
├── navi/                    # Main package
│   ├── core/               # Core business logic
│   │   ├── auth/           # Authentication modules
│   │   ├── engine/         # AI conversation engine
│   │   ├── scheduler/      # Background schedulers
│   │   ├── state/          # State management
│   │   └── tools/          # Business logic tools
│   └── interfaces/         # User interfaces
│       ├── cli/            # Command-line interface
│       ├── telegram/       # Telegram bot
│       └── web/            # Web interface
├── tests/                  # Test suite
├── docs/                   # Documentation
└── scripts/                # Utility scripts
```

## Configuration

Key environment variables:

- `TELEGRAM_BOT_TOKEN`: Telegram bot token from BotFather
- `GEMINI_API_KEY`: Google Gemini API key
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `BASE_URL`: Base URL for OAuth redirects

See `.env.example` for complete configuration options.

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
- Follow PEP 8
- Use type hints
- Add docstrings for public methods

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Documentation

- `CLAUDE.md` - Comprehensive development documentation
- `OAUTH_SETUP.md` - Google OAuth setup guide
- `SERVICE_ACCOUNT_SETUP.md` - Service account configuration
- `DOCKER_DEPLOY.md` - Docker deployment guide

## Architecture

NAVI uses a modular architecture with:

- **Core Engine**: AI conversation processing with Gemini
- **State Management**: User data and conversation history
- **Multiple Interfaces**: Web UI, Telegram bot, CLI
- **Background Schedulers**: Automated check-ins and reflections
- **Tool System**: Extensible business logic tools

## License

Created by Eitan Porat (@eitanporat)

## Support

For issues and feature requests, please use the GitHub issue tracker.