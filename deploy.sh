#!/bin/bash

# NAVI Deployment Script
# This script deploys NAVI to a DigitalOcean droplet

set -e

echo "🚀 NAVI Deployment Script"
echo "========================"

# Check if SERVER_IP is provided
if [ -z "$1" ]; then
    echo "Usage: ./deploy.sh <SERVER_IP>"
    echo "Example: ./deploy.sh 192.168.1.100"
    exit 1
fi

SERVER_IP=$1
echo "📡 Deploying to server: $SERVER_IP"

# Create deployment directory on server
echo "📁 Creating deployment directory..."
ssh root@$SERVER_IP "mkdir -p /opt/navi"

# Copy project files to server
echo "📤 Uploading project files..."
rsync -avz --progress \
    --exclude 'navi_venv/' \
    --exclude '.git/' \
    --exclude '__pycache__/' \
    --exclude '*.log' \
    --exclude 'deprecated/' \
    --exclude '.venv/' \
    . root@$SERVER_IP:/opt/navi/

# Install Docker on server if not installed
echo "🐳 Installing Docker on server..."
ssh root@$SERVER_IP << 'EOF'
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    apt-get update
    apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io
    systemctl start docker
    systemctl enable docker
    echo "Docker installed successfully!"
else
    echo "Docker already installed."
fi

# Install Docker Compose if not installed
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose installed successfully!"
else
    echo "Docker Compose already installed."
fi
EOF

# Build and run the application
echo "🏗️ Building and starting NAVI..."
ssh root@$SERVER_IP << 'EOF'
cd /opt/navi

# Stop any existing containers
docker-compose down 2>/dev/null || true

# Build the new image
docker build -t navi-app .

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.production .env
    echo "⚠️  Please edit /opt/navi/.env with your actual credentials!"
fi

# Start the application
docker-compose up -d

# Show status
echo "📊 Application status:"
docker-compose ps

echo "📋 Application logs (last 20 lines):"
docker-compose logs --tail=20

echo "✅ NAVI deployed successfully!"
echo "🌐 Web interface will be available at: http://$HOSTNAME:4999"
echo "🤖 Telegram bot is running in the background"
echo ""
echo "⚠️  Next steps:"
echo "1. Edit /opt/navi/.env with your actual credentials"
echo "2. Update Google OAuth redirect URIs to your domain"
echo "3. Restart with: docker-compose restart"
EOF

echo "🎉 Deployment completed!"
echo "📝 Remember to:"
echo "   1. SSH to server: ssh root@$SERVER_IP"
echo "   2. Edit credentials: nano /opt/navi/.env"
echo "   3. Restart app: cd /opt/navi && docker-compose restart"
echo "   4. Check logs: docker-compose logs -f"