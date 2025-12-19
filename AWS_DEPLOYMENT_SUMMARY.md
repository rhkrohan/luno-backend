# AWS EC2 Deployment - Summary

I've created a complete AWS EC2 deployment setup for your Luno backend and ESP32 simulator.

## What's Been Created

### 📚 Documentation
1. **`docs/AWS_EC2_DEPLOYMENT.md`** - Comprehensive deployment guide with:
   - EC2 instance setup
   - Security group configuration
   - Server setup instructions
   - Nginx reverse proxy setup
   - SSL/TLS configuration
   - Systemd service management
   - Monitoring and troubleshooting

2. **`DEPLOYMENT_QUICKSTART.md`** - Quick reference guide for rapid deployment

### 🔧 Configuration Files

1. **`config/luno.service`** - Systemd service file for process management
   - Auto-restart on failure
   - Proper user permissions
   - Resource limits

2. **`config/nginx.conf`** - Nginx reverse proxy configuration
   - Rate limiting (10 req/sec)
   - Security headers
   - All API endpoints properly routed
   - Support for 50MB uploads
   - 300s timeout for AI processing

3. **`.env.example`** - Environment variables template
   - Copy to `.env` and fill in your values

### 🚀 Automation Scripts

1. **`scripts/deploy_ec2.sh`** - Automated deployment script
   - Installs all dependencies
   - Sets up Python environment
   - Configures nginx and systemd
   - Handles environment setup
   - Makes deployment easy!

## Your Current Setup

Your simulator already has the correct ngrok backend URL:
```
https://pseudomedically-obese-lanette.ngrok-free.dev
```

This is preserved in `simulators/esp32_test_simulator.html` line 338.

## Quick Deployment Steps

### 1. Launch EC2 Instance
```
Instance Type: t3.medium (or t3.small for testing)
AMI: Ubuntu 22.04 LTS
Storage: 20-30 GB
Security Groups: SSH (22), HTTP (80), HTTPS (443)
```

### 2. Connect and Upload Code
```bash
# SSH into instance
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Upload your code (from local machine)
scp -i your-key.pem -r backend ubuntu@YOUR_EC2_IP:/tmp/luno-backend
```

### 3. Run Automated Deployment
```bash
# On EC2 instance
cd /tmp/luno-backend
chmod +x scripts/deploy_ec2.sh
./scripts/deploy_ec2.sh
```

The script will:
- Install all dependencies (Python, nginx, etc.)
- Set up application user
- Create virtual environment
- Configure nginx reverse proxy
- Set up systemd service
- Optionally install SSL certificate

### 4. Upload Firebase Credentials
```bash
# From local machine
scp -i your-key.pem firebase-credentials.json ubuntu@YOUR_EC2_IP:/tmp/

# On EC2
sudo mv /tmp/firebase-credentials.json /opt/luno/backend/
sudo chown luno:luno /opt/luno/backend/firebase-credentials.json
sudo chmod 600 /opt/luno/backend/firebase-credentials.json
sudo systemctl restart luno
```

### 5. Test
```bash
# Test backend
curl http://YOUR_EC2_IP/

# Open simulator in browser
http://YOUR_EC2_IP/test
```

## Architecture on AWS EC2

```
┌─────────────────────────────────────────┐
│          Internet / ESP32 Devices       │
└───────────────┬─────────────────────────┘
                │
                │ Port 80/443
                ▼
┌─────────────────────────────────────────┐
│         AWS EC2 Instance                │
│  ┌──────────────────────────────┐       │
│  │   Nginx (Reverse Proxy)      │       │
│  │   - Rate limiting            │       │
│  │   - SSL/TLS termination      │       │
│  │   - Static file serving      │       │
│  └──────────┬───────────────────┘       │
│             │ Port 5005                 │
│             ▼                           │
│  ┌──────────────────────────────┐       │
│  │   Gunicorn (WSGI Server)     │       │
│  │   - 4 workers                │       │
│  │   - 2 threads per worker     │       │
│  └──────────┬───────────────────┘       │
│             │                           │
│             ▼                           │
│  ┌──────────────────────────────┐       │
│  │   Flask Application          │       │
│  │   - Audio processing         │       │
│  │   - STT (Whisper)           │       │
│  │   - GPT integration         │       │
│  │   - TTS synthesis           │       │
│  │   - Session management      │       │
│  └──────────┬───────────────────┘       │
│             │                           │
└─────────────┼───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│     External Services                   │
│  - Firebase/Firestore (sessions, auth)  │
│  - OpenAI API (GPT, Whisper, TTS)      │
│  - Deepgram (optional STT)             │
└─────────────────────────────────────────┘
```

## Cost Estimate

**Monthly AWS Costs:**
- EC2 t3.medium: ~$30/month
- EBS Storage (30GB): ~$3/month
- Data Transfer: ~$5-20/month
- **Total: ~$40-55/month**

For lower traffic, use t3.small (~$15/month)

## File Structure on EC2

```
/opt/luno/backend/
├── app.py                    # Main Flask application
├── .env                      # Environment variables (you create this)
├── requirements.txt          # Python dependencies
├── firebase-credentials.json # Firebase credentials (you upload this)
├── venv/                     # Python virtual environment
├── config/
│   ├── gunicorn.conf.py     # Gunicorn configuration
│   ├── luno.service         # Systemd service file
│   └── nginx.conf           # Nginx configuration
├── simulators/
│   └── esp32_test_simulator.html
├── scripts/
│   └── deploy_ec2.sh        # Automated deployment
└── docs/
    └── AWS_EC2_DEPLOYMENT.md

/etc/nginx/sites-available/luno     # Nginx config (copied from config/)
/etc/systemd/system/luno.service    # Systemd service (copied from config/)
/var/log/luno/                      # Application logs
```

## Common Commands

```bash
# Service management
sudo systemctl start luno
sudo systemctl stop luno
sudo systemctl restart luno
sudo systemctl status luno

# View logs
sudo journalctl -u luno -f
sudo tail -f /var/log/luno/error.log

# Nginx
sudo systemctl restart nginx
sudo nginx -t

# Update application
cd /opt/luno/backend
sudo -u luno git pull
sudo systemctl restart luno
```

## Security Checklist

- [ ] Restrict SSH to your IP only
- [ ] Use strong SSH keys (no password auth)
- [ ] Configure Security Groups properly
- [ ] Install SSL certificate (Let's Encrypt)
- [ ] Set proper file permissions (600 for .env, firebase credentials)
- [ ] Enable rate limiting (already configured in nginx)
- [ ] Set up CloudWatch monitoring
- [ ] Configure automatic backups
- [ ] Keep system updated (sudo apt update && sudo apt upgrade)

## Switching from ngrok to EC2

After deploying to EC2, to use your EC2 instance instead of ngrok:

1. Update the simulator's backend URL (line 338 in `esp32_test_simulator.html`):
   ```html
   value="http://YOUR_EC2_IP_OR_DOMAIN">
   ```

2. Or keep using ngrok for local development and EC2 for production

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u luno -n 100
```

### Nginx errors
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/luno_error.log
```

### Check if app is running
```bash
ps aux | grep gunicorn
sudo netstat -tlnp | grep 5005
```

## Next Steps

1. **Deploy to EC2** - Follow the quickstart guide
2. **Configure Domain** - Point your domain to EC2 IP
3. **Install SSL** - Run certbot for HTTPS
4. **Set up Monitoring** - CloudWatch or similar
5. **Configure Backups** - Firestore + application files
6. **CI/CD Pipeline** - Automate deployments with GitHub Actions

## Documentation Files

- **Main Guide**: `docs/AWS_EC2_DEPLOYMENT.md`
- **Quick Start**: `DEPLOYMENT_QUICKSTART.md`
- **This Summary**: `AWS_DEPLOYMENT_SUMMARY.md`

## Support

For issues or questions:
1. Check the troubleshooting section in `docs/AWS_EC2_DEPLOYMENT.md`
2. Review application logs: `sudo journalctl -u luno -f`
3. Test manually: `cd /opt/luno/backend && source venv/bin/activate && python app.py`

---

**Ready to deploy?** Start with `DEPLOYMENT_QUICKSTART.md` for step-by-step instructions.
