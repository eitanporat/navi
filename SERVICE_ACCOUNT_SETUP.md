# Google Service Account Setup for NAVI

## Option 1: Service Account with Domain-Wide Delegation (Recommended for organizations)

### Step 1: Create Service Account
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select your project
3. Go to "IAM & Admin" → "Service Accounts"
4. Click "Create Service Account"
5. Name: `navi-service-account`
6. Enable "Enable Google Workspace Domain-wide Delegation"
7. Click "Create and Continue"

### Step 2: Generate Key
1. Click on your service account
2. Go to "Keys" tab
3. Click "Add Key" → "Create new key"
4. Choose "JSON" format
5. Download the file as `service_account.json`
6. Move it to your NAVI `src/` directory

### Step 3: Enable APIs
1. Go to "APIs & Services" → "Library"
2. Enable these APIs:
   - Google Calendar API
   - Google Tasks API

### Step 4: Configure Domain-Wide Delegation (if using Google Workspace)
1. Go to [Google Admin Console](https://admin.google.com/)
2. Security → API Controls → Domain-wide Delegation
3. Add new with your service account Client ID
4. OAuth Scopes:
   ```
   https://www.googleapis.com/auth/calendar
   https://www.googleapis.com/auth/tasks
   ```

## Option 2: Application Default Credentials (Simpler for personal use)

### Step 1: Install Google Cloud CLI
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### Step 2: Authenticate
```bash
gcloud auth login
gcloud auth application-default login
```

### Step 3: Set Default Project
```bash
gcloud config set project YOUR_PROJECT_ID
```

## Option 3: Environment Variable Credentials

### Set environment variable
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service_account.json"
```

## Testing Your Setup

Run the test script:
```bash
cd src
python service_account_auth.py
```

## Integration with NAVI

The service account provides:
- ✅ **Persistent access** - No token expiration
- ✅ **No user interaction** - Fully automated
- ✅ **Multiple users** - Can impersonate different users
- ✅ **All Google APIs** - Calendar, Tasks, Gmail, etc.

## Next Steps

1. Choose your preferred authentication method
2. Follow the setup steps above
3. Test with the provided script
4. Update NAVI's auth.py to use service account authentication