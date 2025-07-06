#!/bin/bash

# NAVI Build and Push Script
# This script builds NAVI using cloud build services

set -e

echo "🚀 NAVI Cloud Build Script"
echo "========================="

# Check if we're building for a specific platform
PLATFORM=${1:-"google-cloud"}

case $PLATFORM in
    "google-cloud")
        echo "🌍 Building with Google Cloud Build..."
        
        # Check if gcloud is installed
        if ! command -v gcloud &> /dev/null; then
            echo "❌ gcloud CLI not found. Please install it first:"
            echo "curl https://sdk.cloud.google.com | bash"
            exit 1
        fi
        
        # Get project ID
        PROJECT_ID=$(gcloud config get-value project)
        if [ -z "$PROJECT_ID" ]; then
            echo "❌ No Google Cloud project set. Run: gcloud config set project YOUR_PROJECT_ID"
            exit 1
        fi
        
        echo "📝 Building for project: $PROJECT_ID"
        
        # Build and push to Google Container Registry
        gcloud builds submit --tag gcr.io/$PROJECT_ID/navi-app .
        
        echo "✅ Build completed! Image: gcr.io/$PROJECT_ID/navi-app"
        echo "🚀 Deploy with: gcloud run deploy navi-app --image gcr.io/$PROJECT_ID/navi-app"
        ;;
        
    "heroku")
        echo "👵 Building with Heroku Container Registry..."
        
        # Check if heroku CLI is installed
        if ! command -v heroku &> /dev/null; then
            echo "❌ Heroku CLI not found. Please install it first:"
            echo "brew tap heroku/brew && brew install heroku"
            exit 1
        fi
        
        # Check if app name is provided
        if [ -z "$2" ]; then
            echo "❌ Please provide Heroku app name:"
            echo "./build_and_push.sh heroku YOUR_APP_NAME"
            exit 1
        fi
        
        APP_NAME=$2
        echo "📝 Building for Heroku app: $APP_NAME"
        
        # Login to Heroku Container Registry
        heroku container:login
        
        # Build and push
        heroku container:push web --app $APP_NAME
        heroku container:release web --app $APP_NAME
        
        echo "✅ Build completed! App: https://$APP_NAME.herokuapp.com"
        ;;
        
    "aws")
        echo "☁️ Building with AWS CodeBuild..."
        
        # Check if AWS CLI is installed
        if ! command -v aws &> /dev/null; then
            echo "❌ AWS CLI not found. Please install it first:"
            echo "brew install awscli"
            exit 1
        fi
        
        # Check if repository URI is provided
        if [ -z "$2" ]; then
            echo "❌ Please provide ECR repository URI:"
            echo "./build_and_push.sh aws YOUR_ACCOUNT.dkr.ecr.REGION.amazonaws.com/navi-app"
            exit 1
        fi
        
        REPO_URI=$2
        REGION=$(echo $REPO_URI | cut -d'.' -f4)
        
        echo "📝 Building for ECR: $REPO_URI"
        
        # Login to ECR
        aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REPO_URI
        
        # Build and push
        docker build -t navi-app .
        docker tag navi-app:latest $REPO_URI:latest
        docker push $REPO_URI:latest
        
        echo "✅ Build completed! Image: $REPO_URI:latest"
        ;;
        
    *)
        echo "❌ Unknown platform: $PLATFORM"
        echo "Supported platforms: google-cloud, heroku, aws"
        echo ""
        echo "Usage:"
        echo "  ./build_and_push.sh google-cloud"
        echo "  ./build_and_push.sh heroku YOUR_APP_NAME"
        echo "  ./build_and_push.sh aws YOUR_ECR_URI"
        exit 1
        ;;
esac

echo "🎉 Done! Your NAVI app is ready to deploy."
echo ""
echo "📝 Don't forget to:"
echo "1. Set your environment variables in the deployment platform"
echo "2. Update Google OAuth redirect URIs to your production domain"
echo "3. Test the deployment!"