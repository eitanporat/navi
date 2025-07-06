# 🐳 NAVI Docker Deployment Guide

## 🚀 **I've Done Everything I Can - Here's What YOU Need to Do:**

### **Web Commands You Must Run:**

1. **Get a DigitalOcean Droplet** (or any Ubuntu server):
   - Go to https://cloud.digitalocean.com/
   - Create a new droplet (Ubuntu 22.04, $6/month)
   - Note your server's IP address

2. **Get Google OAuth Credentials**:
   - Go to https://console.cloud.google.com/
   - APIs & Services → Credentials → Create OAuth 2.0 Client
   - Add redirect URI: `https://YOUR_DOMAIN/auth/callback`
   - Copy Client ID and Client Secret

### **Terminal Commands You Run:**

```bash
# 1. Deploy to your server (replace IP with your server's IP)
./deploy.sh 192.168.1.100

# 2. SSH to your server and edit environment variables
ssh root@192.168.1.100
nano /opt/navi/.env

# 3. Restart the app
cd /opt/navi && docker-compose restart
```

## 🔧 **What I've Already Set Up:**

✅ **Complete Docker Configuration**
- Multi-stage Dockerfile optimized for production
- Docker Compose with proper volumes and networking
- Health checks and restart policies

✅ **Deployment Scripts**
- `deploy.sh` - Automated server deployment
- `build_and_push.sh` - Cloud build integration
- All dependencies and configuration files

✅ **Environment Configuration**
- `.env.production` with your current tokens
- All NAVI code updated for production URLs
- Proper logging and error handling

✅ **Production Optimizations**
- Non-root user containers
- Efficient build caching
- Proper file permissions
- Resource optimization

## 🚀 Production Deployment Options

### Option 1: DigitalOcean Droplet

1. **Create a Droplet** (Ubuntu 22.04, $6/month)
2. **Install Docker**:
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose
   sudo systemctl start docker
   sudo systemctl enable docker
   sudo usermod -aG docker $USER
   ```
3. **Upload your project**:
   ```bash
   scp -r . root@your-droplet-ip:/opt/navi
   ```
4. **Deploy**:
   ```bash
   cd /opt/navi
   sudo docker-compose up -d
   ```

### Option 2: AWS ECS (Elastic Container Service)

1. **Push to ECR**:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com
   docker build -t navi-app .
   docker tag navi-app:latest your-account.dkr.ecr.us-east-1.amazonaws.com/navi-app:latest
   docker push your-account.dkr.ecr.us-east-1.amazonaws.com/navi-app:latest
   ```

2. **Create ECS Service** with the pushed image

### Option 3: Google Cloud Run

1. **Build and push**:
   ```bash
   gcloud builds submit --tag gcr.io/your-project/navi-app
   ```

2. **Deploy**:
   ```bash
   gcloud run deploy navi-app \
     --image gcr.io/your-project/navi-app \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 4999 \
     --set-env-vars BASE_URL=https://your-service-url.run.app,TELEGRAM_BOT_TOKEN=your_token,GEMINI_API_KEY=your_key
   ```

### Option 4: Heroku (Container)

1. **Install Heroku CLI and login**
2. **Create app and deploy**:
   ```bash
   heroku create your-navi-app
   heroku container:push web --app your-navi-app
   heroku container:release web --app your-navi-app
   
   # Set environment variables
   heroku config:set BASE_URL=https://your-navi-app.herokuapp.com --app your-navi-app
   heroku config:set TELEGRAM_BOT_TOKEN=your_token --app your-navi-app
   heroku config:set GEMINI_API_KEY=your_key --app your-navi-app
   ```

## 🔧 Environment Variables

**Required:**
- `BASE_URL` - Your app's public URL (e.g., https://your-domain.com)
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `GEMINI_API_KEY` - Google AI API key
- `GOOGLE_CLIENT_ID` - OAuth client ID
- `GOOGLE_CLIENT_SECRET` - OAuth client secret
- `FLASK_SECRET_KEY` - Random secret key for Flask sessions

**Optional:**
- `TELEGRAM_BOT_USERNAME` - Bot username for display
- `FLASK_DEBUG` - Set to `False` for production
- `PORT` - Port number (default: 4999)

## 📝 Post-Deployment Steps

1. **Update Google OAuth Settings**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to APIs & Services > Credentials
   - Edit your OAuth 2.0 Client
   - Update redirect URI to: `https://your-domain.com/auth/callback`

2. **Test the Deployment**:
   - Visit your app URL
   - Test Google authentication
   - Test Telegram bot authentication flow

3. **Monitor Logs**:
   ```bash
   docker-compose logs -f
   # Or for single container:
   docker logs -f container_name
   ```

## 🛠️ Troubleshooting

### Common Issues:

1. **Port binding errors**: Make sure port 4999 is available
2. **Environment variables not set**: Check your .env file
3. **Google OAuth errors**: Verify redirect URIs match your domain
4. **Bot not responding**: Check TELEGRAM_BOT_TOKEN is correct

### Health Check:
```bash
curl -f http://localhost:4999/health
```

### View Container Status:
```bash
docker-compose ps
```

## 🔒 Security Best Practices

1. **Use HTTPS in production** (required for Telegram webhooks)
2. **Set strong FLASK_SECRET_KEY**
3. **Use environment variables for all secrets**
4. **Run containers as non-root user** (already configured)
5. **Keep your base images updated**

## 🎯 Best Deployment Choice

**For simplicity and cost**: DigitalOcean Droplet ($6/month)
**For scalability**: Google Cloud Run (pay-per-use)
**For enterprise**: AWS ECS with Application Load Balancer

## 📊 Resource Requirements

- **Minimum**: 1 CPU, 1GB RAM, 10GB storage
- **Recommended**: 2 CPU, 2GB RAM, 20GB storage
- **Network**: ~100MB/month for typical usage

Your NAVI app is now ready for production! 🚀