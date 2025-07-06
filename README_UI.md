# NAVI Web UI

A simple web interface for the NAVI personal productivity assistant.

## Quick Start

1. **Install dependencies** (if not already installed):
   ```bash
   pip install flask requests
   ```

2. **Start the web UI**:
   ```bash
   cd /Users/eporat/Projects/navi
   python start_ui.py
   ```

3. **Open your browser** to:
   ```
   http://localhost:5000
   ```

## Features

### 📱 4 Main Pages:

1. **Home** (`/`) - Overview and user information
2. **Conversations** (`/conversations`) - Chat history with NAVI
3. **API Calls** (`/api-calls`) - Function calls and tool usage
4. **Goals & Tasks** (`/goals-tasks`) - Goals with associated tasks
5. **Calendar** (`/calendar`) - Tasks displayed on calendar view

### 🔧 Technical Details:

- **Backend**: Flask web server reading from existing `state.json` files
- **Frontend**: Vanilla HTML/CSS/JavaScript (no frameworks)
- **Data Source**: Existing NAVI state files in `src/users/*/state.json`
- **Port**: 5000 (configurable)

## File Structure

```
src/
├── web_ui.py              # Flask server
├── templates/             # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── home.html         # Home page
│   ├── conversations.html # Chat history
│   ├── api_calls.html    # Function calls
│   ├── goals_tasks.html  # Goals and tasks
│   └── calendar.html     # Calendar view
└── static/               # CSS/JS (if needed)
```

## API Endpoints

- `GET /api/conversations` - Chat history data
- `GET /api/api-calls` - Function call data
- `GET /api/goals-tasks` - Goals and tasks data
- `GET /api/calendar` - Calendar items
- `GET /api/user` - Current user information

## Features

✅ **Completed**:
- Responsive design for mobile/desktop
- Real-time data from existing NAVI state
- Clean, modern interface
- Task dates displayed on calendar
- Color-coded goals/tasks by importance/status
- Function call tracking with syntax highlighting

🚀 **Future Enhancements**:
- Edit goals/tasks via UI
- Real-time chat with NAVI
- Google Calendar integration
- Dark mode toggle
- Export/import functionality

## Troubleshooting

- **Port already in use**: Change port in `start_ui.py`
- **No data displayed**: Check that NAVI has been used and state files exist
- **Calendar not showing tasks**: Ensure tasks have proper date formats (DD/MM/YY HH:MM)

## Development

The UI is designed to be simple and fast to iterate on. All data is read-only from existing NAVI state files, so it's safe to experiment without affecting your NAVI data.