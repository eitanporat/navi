# Google OAuth Setup for NAVI - Get Refresh Tokens

## Step 1: Create OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select your project
3. Go to "APIs & Services" → "Credentials"
4. Click "Create Credentials" → "OAuth 2.0 Client IDs"
5. Choose "Desktop Application" 
6. Name it "NAVI Desktop"
7. Download the JSON file
8. **Important:** Rename it to `credentials.json` and put it in the `src/` folder

## Step 2: Enable Required APIs

1. Go to "APIs & Services" → "Library"
2. Enable these APIs:
   - ✅ Google Calendar API
   - ✅ Google Tasks API

## Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Choose "External" (unless you have Google Workspace)
3. Fill in required fields:
   - App name: "NAVI"
   - User support email: Your email
   - Developer contact: Your email
4. Add scopes:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/tasks`
5. Add test users (your email) if app is not published

## Step 4: Test the OAuth Flow

```bash
cd src
python reauth_user.py ethan.porat@gmail.com
```

This will:
- Open browser for Google OAuth
- Show consent screen (click "Allow")
- Save credentials with refresh token
- Test calendar access

## Step 5: Verify Refresh Token

Check that the token file now has a refresh_token:
```bash
cat users/ethan.porat@gmail.com/token.json | grep refresh_token
```

You should see: `"refresh_token": "1//04..."`

## What This Fixes

✅ **Persistent Access** - No more "credentials expired" errors  
✅ **Auto-Refresh** - Tokens refresh automatically  
✅ **One-Time Setup** - User only authenticates once  
✅ **Works with Telegram Bot** - Calendar commands will work

## Troubleshooting

- **"App not verified" warning**: Click "Advanced" → "Go to NAVI (unsafe)"
- **Missing scopes**: Add Calendar and Tasks scopes in OAuth consent screen
- **"redirect_uri_mismatch"**: OAuth client must be "Desktop Application" type