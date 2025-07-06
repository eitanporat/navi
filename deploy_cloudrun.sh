#!/bin/bash

# NAVI Google Cloud Run Deployment Script
# Your credentials are already configured!

set -e

# Configuration - Set your project ID here
PROJECT_ID=${PROJECT_ID:-"your-project-id-here"}

if [ "$PROJECT_ID" = "your-project-id-here" ]; then
    echo "❌ Please set PROJECT_ID environment variable or edit this script"
    echo "   export PROJECT_ID=your-actual-project-id"
    exit 1
fi

echo "🚀 NAVI Cloud Run Deployment"
echo "============================="
echo "📋 Using existing credentials from credentials.json"
echo "🔑 Project: $PROJECT_ID"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Install it:"
    echo "curl https://sdk.cloud.google.com | bash"
    echo "Then run: exec -l $SHELL"
    exit 1
fi

# Set project
echo "🔧 Setting up Google Cloud project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔌 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build and push to Google Container Registry
echo "🏗️  Building Docker image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/navi-app .

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy navi-app \
  --image gcr.io/$PROJECT_ID/navi-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 4999 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --set-env-vars BASE_URL=https://navi-app-RANDOM.a.run.app,FLASK_DEBUG=False,PORT=4999 \
  --set-secrets="TELEGRAM_BOT_TOKEN=telegram-bot-token:latest" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest" \
  --set-secrets="GOOGLE_CLIENT_ID=google-client-id:latest" \
  --set-secrets="GOOGLE_CLIENT_SECRET=google-client-secret:latest" \
  --set-secrets="FLASK_SECRET_KEY=flask-secret-key:latest"

# Get the service URL
SERVICE_URL=$(gcloud run services describe navi-app --region=us-central1 --format='value(status.url)')

echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================"
echo "🌐 Your NAVI app is live at: $SERVICE_URL"
echo "🤖 Telegram bot is running in the background"
echo ""
echo "📝 IMPORTANT: Update Google OAuth redirect URI:"
echo "   1. Go to: https://console.cloud.google.com/apis/credentials"
echo "   2. Edit your OAuth 2.0 Client"
echo "   3. Add redirect URI: $SERVICE_URL/auth/callback"
echo "   4. Save changes"
echo ""
echo "🧪 Test your deployment:"
echo "   1. Visit: $SERVICE_URL"
echo "   2. Test Google authentication"
echo "   3. Get auth code from Settings"
echo "   4. Send code to your Telegram bot"
echo ""
echo "📊 Monitor logs: gcloud run logs tail navi-app --region=us-central1"
echo "🔄 Update app: Run this script again"
echo ""
echo "💰 Cost: ~$0.50-2/month for personal use (pay per request)"
echo "🎉 Enjoy your deployed NAVI assistant!"