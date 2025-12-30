# AWS EC2 Deployment - Quick Start

This guide provides a quick overview of deploying your Luno backend to AWS EC2.

## Prerequisites

- AWS account
- EC2 key pair (.pem file)
- OpenAI API key
- Firebase credentials JSON file

## Quick Deployment (Automated)

### 1. Launch EC2 Instance

1. Go to AWS Console > EC2 > Launch Instance
2. **Settings:**
   - Name: `luno-backend`
   - AMI: Ubuntu Server 22.04 LTS
   - Instance Type: `t3.medium` (or `t3.small` for testing)
   - Key pair: Create/select your SSH key
   - Storage: 20 GB gp3

3. **Security Group - Add these inbound rules:**
   - SSH (22) - Your IP only
   - HTTP (80) - 0.0.0.0/0
   - HTTPS (443) - 0.0.0.0/0

4. Launch instance and note the public IP

### 2. Connect to Instance

```bash
ssh -i /path/to/your-key.pem ubuntu@YOUR_EC2_IP
```

### 3. Upload Your Code

**Option A: Using Git (Recommended)**
```bash
# On EC2
git clone https://github.com/yourusername/luno-backend.git /tmp/luno-backend
```

**Option B: Using SCP (From local machine)**
```bash
# From your local machine
cd /Users/rohankhan/Desktop/Luno
scp -i /path/to/your-key.pem -r backend ubuntu@YOUR_EC2_IP:/tmp/luno-backend
```

### 4. Run Automated Deployment Script

```bash
# On EC2
cd /tmp/luno-backend
chmod +x scripts/deploy_ec2.sh
./scripts/deploy_ec2.sh
```

The script will:
- Install all system dependencies
- Set up Python environment
- Configure nginx
- Create systemd service
- Optionally install SSL certificate

**During deployment, you'll need to provide:**
- OpenAI API key
- Domain name (optional, can use IP)
- Email for SSL certificate (if using domain)

### 5. Upload Firebase Credentials

```bash
# From local machine
scp -i /path/to/your-key.pem firebase-credentials.json ubuntu@YOUR_EC2_IP:/tmp/

# On EC2
sudo mv /tmp/firebase-credentials.json /opt/luno/backend/
sudo chown luno:luno /opt/luno/backend/firebase-credentials.json
sudo chmod 600 /opt/luno/backend/firebase-credentials.json

# Restart service
sudo systemctl restart luno
```

### 6. Test Deployment

```bash
# Test backend
curl http://YOUR_EC2_IP/
# Should return: "ESP32 Toy Backend is running..."

# Test in browser
# Open: http://YOUR_EC2_IP/test
```

## Manual Deployment

If you prefer manual control, follow the detailed guide:
[AWS EC2 Deployment Guide](docs/AWS_EC2_DEPLOYMENT.md)

## Post-Deployment

### View Logs
```bash
# Application logs
sudo journalctl -u luno -f

# Nginx logs
sudo tail -f /var/log/nginx/luno_access.log
```

### Restart Services
```bash
# Restart application
sudo systemctl restart luno

# Restart nginx
sudo systemctl restart nginx
```

### Update Application
```bash
# Pull latest code
cd /opt/luno/backend
sudo -u luno git pull

# Restart service
sudo systemctl restart luno
```

## Using Custom Domain

### 1. Configure DNS
- Create an A record pointing to your EC2 IP
- Wait for DNS propagation (5-30 minutes)

### 2. Install SSL Certificate
```bash
sudo certbot --nginx -d yourdomain.com
```

### 3. Update Simulator
Edit `/opt/luno/backend/simulators/esp32_test_simulator.html` line 338:
```html
value="https://yourdomain.com">
```

## Architecture Overview

```
┌─────────────┐
│   Internet  │
└──────┬──────┘
       │
┌──────▼──────────────┐
│   Nginx (Port 80)   │
│   Reverse Proxy     │
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│ Gunicorn (Port 5005)│
│   Flask App         │
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│   Backend Services  │
│ - Whisper STT       │
│ - GPT               │
│ - TTS               │
│ - Firestore         │
└─────────────────────┘
```

## Estimated Costs

- **t3.medium**: ~$30/month
- **Storage (30GB)**: ~$3/month
- **Data transfer**: ~$5-20/month
- **Total**: ~$40-55/month

*Use t3.small (~$15/month) for lower-traffic deployments*

## Common Commands

```bash
# View service status
sudo systemctl status luno

# View logs
sudo journalctl -u luno -f

# Restart application
sudo systemctl restart luno

# Check nginx config
sudo nginx -t

# Monitor resources
htop
```

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u luno -n 100
```

### Check if ports are listening
```bash
sudo netstat -tlnp | grep -E ':(80|5005)'
```

### Test gunicorn directly
```bash
sudo su - luno
cd /opt/luno/backend
source venv/bin/activate
python app.py
```

## Security Checklist

- [ ] SSH restricted to your IP
- [ ] Firewall configured (Security Groups)
- [ ] SSL certificate installed
- [ ] Firebase credentials secured (600 permissions)
- [ ] Environment variables secured (600 permissions)
- [ ] Regular system updates scheduled
- [ ] Rate limiting enabled

## Next Steps

1. Set up monitoring (CloudWatch)
2. Configure automatic backups
3. Set up staging environment
4. Implement CI/CD pipeline
5. Configure CloudFront CDN (optional)

## Support

For detailed documentation:
- [Full Deployment Guide](docs/AWS_EC2_DEPLOYMENT.md)
- [Main README](README.md)
- [Session Management](docs/SESSION_MANAGEMENT.md)
- [Authentication](docs/AUTHENTICATION.md)

---

**Note:** The simulator currently uses ngrok for testing. After EC2 deployment, you can update the backend URL in the simulator to point to your EC2 instance.
