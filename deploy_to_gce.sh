#!/bin/bash
# NAVI GCE Deployment Script

INSTANCE_NAME="navi-server"
ZONE="us-central1-a"
PROJECT_DIR="/opt/navi"

echo "🚀 Deploying NAVI to GCE instance..."

# CRITICAL: Kill any local bot processes first to avoid duplicates
echo "🛑 Killing any local NAVI processes..."
pkill -f "python.*telegram" || true
pkill -f "run_telegram.py" || true
pkill -f "run_all.py" || true
pkill -f "telegram_bot.py" || true
lsof -ti:4999 | xargs kill -9 2>/dev/null || true
sleep 2
echo "✅ Local processes killed"

# Wait for instance to be ready
echo "⏳ Waiting for instance to be ready..."
sleep 10

# Create a temporary directory for deployment
echo "📦 Preparing files for deployment..."
TEMP_DIR=$(mktemp -d)
rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='navi_venv' --exclude='logs' --exclude='users' \
  --exclude='*.log' --exclude='token.json' --exclude='state.json' \
  --exclude='.env' --exclude='deprecated' \
  . ${TEMP_DIR}/

# Copy project files to instance
echo "📦 Copying NAVI files to instance..."
gcloud compute scp --recurse \
  ${TEMP_DIR}/* navi@${INSTANCE_NAME}:${PROJECT_DIR} \
  --zone=${ZONE}

# Clean up temp directory
rm -rf ${TEMP_DIR}

# Copy .env.production file if it exists
if [ -f .env.production ]; then
  echo "📄 Copying environment file..."
  gcloud compute scp .env.production navi@${INSTANCE_NAME}:${PROJECT_DIR}/.env --zone=${ZONE}
fi

# Create setup script
cat > setup_navi.sh << 'EOF'
#!/bin/bash
cd /opt/navi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
python3 -m venv navi_venv
source navi_venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs users

# Create empty auth files if they don't exist
touch telegram_auth_codes.json telegram_mappings.json

# Set proper permissions
chown -R navi:navi /opt/navi

# Create systemd service for NAVI
sudo tee /etc/systemd/system/navi.service > /dev/null << 'SERVICE'
[Unit]
Description=NAVI Personal Assistant
After=network.target

[Service]
Type=simple
User=navi
WorkingDirectory=/opt/navi
Environment="PATH=/opt/navi/navi_venv/bin"
ExecStart=/opt/navi/navi_venv/bin/python run_all.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# Configure nginx (basic HTTP first, SSL will be added later)
sudo tee /etc/nginx/sites-available/navi > /dev/null << 'NGINX'
server {
    listen 80;
    server_name 34-56-132-229.nip.io;

    location / {
        proxy_pass http://localhost:4999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

# Enable nginx site
sudo ln -sf /etc/nginx/sites-available/navi /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# Enable and start NAVI service
sudo systemctl daemon-reload
sudo systemctl enable navi
sudo systemctl start navi

# Install certbot for SSL
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# Get SSL certificate and configure HTTPS
sudo certbot --nginx -d 34-56-132-229.nip.io --non-interactive --agree-tos --email noreply@example.com

# If certbot fails to auto-configure, manually configure SSL
if ! sudo nginx -t; then
    echo "📄 Manually configuring SSL..."
    sudo tee /etc/nginx/sites-available/navi > /dev/null << 'SSL_NGINX'
server {
    listen 80;
    server_name 34-56-132-229.nip.io;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name 34-56-132-229.nip.io;

    ssl_certificate /etc/letsencrypt/live/34-56-132-229.nip.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/34-56-132-229.nip.io/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:4999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
SSL_NGINX
    sudo nginx -t && sudo systemctl reload nginx
fi

echo "✅ NAVI setup complete!"
echo "📊 Check service status with: sudo systemctl status navi"
echo "📝 View logs with: sudo journalctl -u navi -f"
EOF

# Copy and run setup script
echo "🔧 Running setup on instance..."
gcloud compute scp setup_navi.sh navi@${INSTANCE_NAME}:${PROJECT_DIR}/setup_navi.sh --zone=${ZONE}
gcloud compute ssh navi@${INSTANCE_NAME} --zone=${ZONE} --command="chmod +x ${PROJECT_DIR}/setup_navi.sh && sudo -u navi ${PROJECT_DIR}/setup_navi.sh"

# Get instance IP
EXTERNAL_IP=$(gcloud compute instances describe ${INSTANCE_NAME} --zone=${ZONE} --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "✅ Deployment complete!"
echo "🌐 NAVI is now running at: http://${EXTERNAL_IP}"
echo ""
echo "📋 Next steps:"
echo "1. Update Google OAuth redirect URIs to include: http://${EXTERNAL_IP}/auth/callback"
echo "2. Access the web UI at: http://${EXTERNAL_IP}"
echo "3. The Telegram bot should be running and responsive"
echo ""
echo "🔧 Useful commands:"
echo "- SSH to instance: gcloud compute ssh navi@${INSTANCE_NAME} --zone=${ZONE}"
echo "- View logs: gcloud compute ssh navi@${INSTANCE_NAME} --zone=${ZONE} --command='sudo journalctl -u navi -f'"
echo "- Restart service: gcloud compute ssh navi@${INSTANCE_NAME} --zone=${ZONE} --command='sudo systemctl restart navi'"

# Clean up
rm -f setup_navi.sh