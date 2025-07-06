# NAVI Project - Claude Assistant Context

## Project Overview
NAVI is a personal productivity assistant that helps users manage goals, tasks, and calendars through integration with Google services. The project includes both a web interface and a Telegram bot.

## Current Status
- **Main Feature**: Telegram bot with simple code-based authentication
- **Recently Completed**: Package reorganization with proper Python package structure
- **Current Task**: Ready to use! Complete authentication flow implemented with new package structure

## Key Files and Structure

### NEW PACKAGE STRUCTURE (Reorganized July 2025)
```
navi/                           # Main package
├── __init__.py                 # Package exports and version
├── core/                       # Core business logic
│   ├── auth/                   # Authentication modules
│   │   ├── base.py            # Google OAuth (navi_auth)
│   │   └── telegram_auth.py   # Telegram authentication
│   ├── engine/                 # Conversation engine
│   │   └── conversation.py    # Main AI engine
│   ├── state/                  # State management
│   │   └── manager.py         # StateManager class
│   └── tools/                  # Business logic tools
│       ├── goals.py           # Goal management
│       ├── tasks.py           # Task management
│       ├── calendar_tools.py  # Calendar integration
│       └── utilities.py       # Date/time and utilities
├── interfaces/                 # User interfaces
│   ├── adapters.py            # Interface base classes
│   ├── cli/                   # Command-line interface
│   │   ├── interface.py       # CLI implementation
│   │   └── ui.py              # Rich UI components
│   ├── telegram/              # Telegram bot
│   │   └── bot.py             # Telegram bot implementation
│   └── web/                   # Web interface
│       ├── app.py             # Flask application
│       ├── templates/         # HTML templates
│       └── static/            # Static files
└── config/                    # Configuration
    └── prompts.py             # AI system prompts
```

### New Entry Points (Root Directory)
- `run_cli.py` - Start CLI interface
- `run_web.py` - Start web UI
- `run_telegram.py` - Start Telegram bot
- `run_all.py` - Start all services
- `start_navi.sh` - Bash script using new package structure

### Deprecated Files (moved to deprecated/ folder)
- `deprecated/src/` - All original source files moved here
- `deprecated/start_navi.sh` - Original startup script
- `deprecated/test_simple_auth.py` - Test files

### Configuration Files
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (not tracked in git)
- `credentials.json` - Google OAuth credentials (not tracked in git)

## Authentication System

### Current Implementation: Simple Code Authentication
The Telegram bot uses a simple 6-digit code system for authentication:

1. **Web Authentication**: User visits http://localhost:4999 and authenticates with Google
2. **Code Generation**: 6-digit code generated in Settings page (30-minute expiration)
3. **Copy Code**: User copies code to clipboard (works on desktop and mobile)
4. **Telegram Bot**: User sends `/start` to bot, then sends the 6-digit code
5. **Account Linking**: Links Telegram user to existing NAVI Google account

### File Storage
- `telegram_auth_codes.json` - Stores authentication codes with expiration
- `telegram_mappings.json` - Maps Telegram user IDs to Google email accounts
- `users/[email]/` - User-specific data directories
- `users/[email]/token.json` - Google OAuth tokens
- `users/[email]/state.json` - User state and preferences

## Environment Variables Required

### Essential
- `TELEGRAM_BOT_TOKEN` - Telegram bot token from BotFather
- `GEMINI_API_KEY` - Google Gemini API key for AI features
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to Google service account credentials (optional)

### Optional
- `TELEGRAM_BOT_USERNAME` - Bot username for display in settings (optional)

### Development/Testing
- `NAVI_TEST_MODE` - Set to 'true' to disable authentication (for local debugging)
- `NAVI_TEST_USER_EMAIL` - Email to use in test mode (default: test@example.com)
- `GOOGLE_CLIENT_ID` - Google OAuth client ID for web authentication
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret for web authentication
- `BASE_URL` - Base URL for OAuth redirects (default: http://localhost:4999)

## Running the Application

### Using Reorganized Package Structure

**Start All Services (Recommended):**
```bash
./start_navi.sh
# OR
source navi_venv/bin/activate
python run_all.py
```

**Individual Services (New Structure):**
```bash
# Web Interface Only
source navi_venv/bin/activate
python run_web.py

# Telegram Bot Only  
source navi_venv/bin/activate
python run_telegram.py

# CLI Interface
source navi_venv/bin/activate
python run_cli.py
```

**Development/Testing Mode:**
```bash
# Run web UI without authentication (useful for debugging)
export NAVI_TEST_MODE=true
export NAVI_TEST_USER_EMAIL=your.email@gmail.com
source navi_venv/bin/activate
python run_web.py
```

### Process Management
**Kill existing processes if needed:**
```bash
# Kill any process using port 4999 (web UI)
lsof -ti:4999 | xargs kill -9

# Kill any process using telegram bot
pkill -f "telegram_bot.py"
pkill -f "run_telegram.py"
pkill -f "run_all.py"
```
## 🚨 CRITICAL: Avoid Duplicate Telegram Bots 🚨

**⚠️ IF YOU'RE GETTING DUPLICATE RESPONSES: Kill ALL local processes immediately!**

**NEVER run NAVI locally if it's deployed on GCE!**

### Current Deployment Status:
- **GCE Production**: https://34-56-132-229.nip.io ✅ RUNNING
- **OAuth Redirect URI**: https://34-56-132-229.nip.io/auth/callback ✅ HTTPS WORKING
- **Local Development**: Should be STOPPED when GCE is running

### Before ANY deployment or local run:
1. **Check GCE status**: Is https://34-56-132-229.nip.io running?
2. **If GCE is running**: DO NOT run locally!
3. **If running locally**: STOP before deploying to GCE!

### Kill Commands (ALWAYS run before deploy/start):
```bash
# Kill all NAVI processes before starting new ones
pkill -f "python.*telegram" || true
pkill -f "run_telegram.py" || true
pkill -f "run_all.py" || true
pkill -f "telegram_bot.py" || true
lsof -ti:4999 | xargs kill -9 2>/dev/null || true
```

### Scripts Updated with Safety Checks:
- `deploy_to_gce.sh` - Now kills local processes automatically
- `start_navi.sh` - Now warns about GCE deployment and asks for confirmation

## Deployment (Google Compute Engine)

**Default deployment method**: Google Compute Engine (GCE)
- Use `./deploy_to_gce.sh` to deploy NAVI to GCE
- Already configured with nginx reverse proxy and systemd service
- Includes automatic setup of Python environment and dependencies
- Instance name: `navi-server` in `us-central1-a`
- **Current deployment**: https://34-56-132-229.nip.io ✅ (HTTPS enabled with Let's Encrypt)
- **HTTP redirect**: http://34-56-132-229.nip.io → automatically redirects to HTTPS  
- **OAuth Redirect URI**: https://34-56-132-229.nip.io/auth/callback ✅ READY FOR GOOGLE OAUTH
- **SSL Certificate**: Valid until 2025-10-04 (auto-renews)
- **Status**: FULLY DEPLOYED AND WORKING

**GCE Management Commands**:
```bash
# Start instance (if stopped)
gcloud compute instances start navi-server --zone=us-central1-a --project=your-project-id

# Deploy/update code (IMPORTANT: Kill local bot first!)
pkill -f "python.*telegram" || true  # Kill any local telegram bots
pkill -f "run_telegram.py" || true
pkill -f "run_all.py" || true
./deploy_to_gce.sh

# SSH to instance
gcloud compute ssh navi@navi-server --zone=us-central1-a

# Check service status
gcloud compute ssh navi@navi-server --zone=us-central1-a --command="sudo systemctl status navi"

# View logs
gcloud compute ssh navi@navi-server --zone=us-central1-a --command="sudo journalctl -u navi -f"

# Restart service
gcloud compute ssh navi@navi-server --zone=us-central1-a --command="sudo systemctl restart navi"
```

**Alternative deployment options**:
- Cloud Run: `./deploy_cloudrun.sh` (serverless, **RECOMMENDED** - provides HTTPS automatically)
- DigitalOcean: `./deploy.sh <SERVER_IP>` (VPS deployment)

### ✅ HTTPS Setup on GCE

NAVI is deployed with HTTPS using Let's Encrypt on nip.io domain:

1. **Current HTTPS URL**: https://34-56-132-229.nip.io
2. **SSL Certificate**: Automatically obtained via Let's Encrypt
3. **Auto-renewal**: Certbot handles certificate renewal automatically

**How HTTPS was set up on GCE**:
```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get SSL certificate for nip.io domain
sudo certbot --nginx -d 34-56-132-229.nip.io --non-interactive --agree-tos --email noreply@example.com

# Update BASE_URL to use HTTPS
sed -i 's|BASE_URL=.*|BASE_URL=https://34-56-132-229.nip.io|' .env

# Restart service
sudo systemctl restart navi
```

**Important Notes**:
- The systemd service must include `EnvironmentFile=/opt/navi/.env` to load environment variables properly (including BASE_URL for Telegram bot responses)
- After deployment, nginx SSL configuration may need to be restored manually if overwritten
- Use `sudo certbot --nginx -d 34-56-132-229.nip.io` to reapply SSL if needed

## Next Steps
1. ✅ **COMPLETED: Code Reorganization** - Successfully reorganized codebase into proper packages  
2. 🐛 **IN PROGRESS: Calendar Debug** - Calendar API fetches events correctly but UI shows zero events (debugging frontend JavaScript)
3. **Test the new package structure in production**
4. Implement remaining Telegram bot features:
   - Interactive keyboards for goal/task actions
   - Rich message formatting
   - AI conversation capabilities
   - ✅ **Scheduled notifications** (COMPLETED - Progress Tracker Notifications)
4. ✅ **Deploy to production server** - GCE deployment ready with `./deploy_to_gce.sh`
5. Add error handling for edge cases

## Latest Features ✅

### Automated Progress Tracker Notifications
NAVI includes an automated progress tracking system that sends reminder notifications at scheduled times:

### GTD-Based Daily Check-ups System  
NAVI now proactively maintains Getting Things Done (GTD) methodology through automated daily check-ups:

**Automatic Scheduling:**
- NAVI maintains at least 3 daily check-ups scheduled in advance
- Default timing: Daily at 6 PM (user can adjust preference)
- Never asks permission - schedules automatically using progress tracker system
- Immediately schedules next 3 days when completing a check-up

**GTD Four-Phase Structure:**
1. **Capture & Process** - Review new inputs, commitments, and ideas
2. **Organize & Update** - Task status review, calendar alignment, priority adjustment
3. **Reflect & Learn** - Celebrate wins, analyze obstacles, recognize patterns
4. **Plan & Commit** - Tomorrow's focus, weekly momentum, resource planning

**AI-Generated Conversations:**
- Natural, encouraging tone (collaborative partner, not judgmental)
- Data-driven insights using comprehensive tool analysis
- Context-aware coaching based on user's patterns and progress
- Forward momentum focus - always end with tomorrow's commitment

**Example Check-up Types:**
- **Momentum Building:** Celebrate progress and maintain forward motion
- **Obstacle-Focused:** Address stalled tasks with compassionate problem-solving
- **System Calibration:** Adjust goals and workload based on capacity
- **Energy Optimization:** Align tasks with user's natural energy patterns

**Progress Tracker Functions:**
- `add_progress_tracker(state_manager, task_id, check_in_time)` - Schedule a progress check-in
- `list_progress_trackers(state_manager)` - View all scheduled trackers
- `update_progress_tracker(state_manager, tracker_id, field, new_value)` - Modify tracker details

**Automated AI-Powered Notifications:**
- Background scheduler checks every minute for due progress trackers
- Uses NAVI's conversation engine to generate natural, contextual check-ins
- Follows comprehensive check-in principles from system prompt:
  - Gathers full context using list_tasks(), list_events(), display_goals_with_progress()
  - Applies diagnostic reflection for incomplete tasks (compassionate, not scolding)
  - Offers practical solutions and strategies
  - Feels like a thoughtful friend, not a robotic reminder
- Updates tracker status from PENDING → NOTIFIED
- Saves conversation state after each AI-generated check-in
- **All hourly reflections and progress check-ins are logged to chat history and visible in /conversations UI**
- System prompts are marked with [SYSTEM: Hourly Reflection Check] for clarity
- AI's strategic thinking (<strategize> tags) is displayed in the UI with special formatting

**Tracker Statuses:**
- `PENDING` - Scheduled, waiting for check-in time
- `IN_PROGRESS` - Manually updated by user
- `COMPLETED` - Task progress completed
- `NOTIFIED` - Notification sent, awaiting user response

**Example Usage:**
```python
# Schedule a progress check-in for tomorrow at 3 PM
add_progress_tracker(sm, task_id=5, check_in_time="2025-07-07 15:00")
```

**Notification Message Format:**
```
🔔 Progress Check-In Reminder
📋 Task: [Task Description]
Goal: [Associated Goal Title]
⏰ Scheduled check-in time: [Time]

How is your progress on this task?
[Helpful prompts and suggestions]
```
6. Consider deprecating legacy src/ files after thorough testing

## Code Reorganization Summary (July 2025)
✅ **COMPLETED**: Successfully reorganized NAVI codebase into proper Python packages with:
- Clear separation of concerns (core business logic vs interfaces)
- Focused modules instead of monolithic files
- Professional package structure following Python conventions
- New entry points for clean service startup
- Backward compatibility with legacy src/ files maintained
- All imports updated and tested working
- New startup scripts created

## Git Repository

**Repository**: https://github.com/eitanporat/navi
- ✅ **Secure**: All hardcoded secrets removed, only env var references
- ✅ **Clean**: Fresh repository with no credential history
- ✅ **Audited**: All deployment scripts use environment variables/Secret Manager
- 📝 **Lesson Learned**: Always audit scripts before committing

### Git Workflow
```bash
# Clone repository
git clone git@github.com:eitanporat/navi.git

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "Description of changes"

# Push to GitHub
git push origin feature/your-feature-name

# Create pull request on GitHub
```

### What's in the Repository
- ✅ **Source code**: Complete NAVI package (`navi/`)
- ✅ **Documentation**: Setup guides and comprehensive docs
- ✅ **Deployment**: Scripts for GCE, Cloud Run, Docker
- ✅ **Configuration**: Example environment files
- ✅ **Tests**: Test structure ready for expansion
- ❌ **Credentials**: Safely excluded via .gitignore
- ❌ **User data**: No personal information included
- ❌ **Logs**: Development artifacts excluded

## Memories
- Remember we prefer .env to environment variable!
- Remember to create logs so you can read them to debug!
- **GIT**: Repository recreated securely at https://github.com/eitanporat/navi
- **NEW**: Use `./start_navi.sh` or `python run_all.py` for new package structure!
- Always update claude.md with todos
- **SECURITY**: 🚨 CRITICAL - Never commit credentials! Always use .env and Secret Manager
- **LESSON LEARNED**: Always audit deployment scripts before committing

## Always use robust solutions!!!