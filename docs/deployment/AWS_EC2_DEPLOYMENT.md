# AWS EC2 Deployment Guide

This guide provides step-by-step instructions for deploying the Luno backend and simulator on AWS EC2.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [EC2 Instance Setup](#ec2-instance-setup)
3. [Server Configuration](#server-configuration)
4. [Application Deployment](#application-deployment)
5. [Domain and SSL Setup](#domain-and-ssl-setup)
6. [Process Management](#process-management)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)

---

## Prerequisites

- AWS account with EC2 access
- Domain name (optional, but recommended for production)
- Firebase credentials JSON file
- OpenAI API key
- SSH client installed locally

---

## EC2 Instance Setup

### 1. Launch EC2 Instance

**Recommended Specifications:**
- **Instance Type**: `t3.medium` or `t3.large` (2-4 vCPUs, 4-8 GB RAM)
  - For testing: `t3.small` or `t3.micro` (free tier)
- **AMI**: Ubuntu Server 22.04 LTS (or Amazon Linux 2023)
- **Storage**: 20-30 GB gp3 SSD
- **Region**: Choose closest to your users

**Steps:**
1. Go to AWS Console > EC2 > Launch Instance
2. Name: `luno-backend-server`
3. Select Ubuntu Server 22.04 LTS AMI
4. Choose instance type (t3.medium recommended)
5. Create or select a key pair for SSH access
6. Configure storage: 20-30 GB

### 2. Configure Security Group

Create a security group with the following inbound rules:

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|--------|-------------|
| SSH | TCP | 22 | Your IP | SSH access |
| HTTP | TCP | 80 | 0.0.0.0/0 | HTTP traffic |
| HTTPS | TCP | 443 | 0.0.0.0/0 | HTTPS traffic |
| Custom TCP | TCP | 5005 | 0.0.0.0/0 | Flask dev (optional, for testing) |

**Security Best Practices:**
- Restrict SSH (port 22) to your IP only
- After deployment, remove port 5005 access
- Enable VPC Flow Logs for monitoring

### 3. Allocate Elastic IP (Optional but Recommended)

1. Go to EC2 > Elastic IPs
2. Allocate new address
3. Associate with your EC2 instance
4. This gives you a static IP address

---

## Server Configuration

### 1. Connect to EC2 Instance

```bash
# SSH into your instance
ssh -i /path/to/your-key.pem ubuntu@YOUR_EC2_IP

# Update system packages
sudo apt update && sudo apt upgrade -y
```

### 2. Install System Dependencies

```bash
# Install Python 3.11 and essential packages
sudo apt install -y python3.11 python3.11-venv python3-pip
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
sudo apt install -y portaudio19-dev python3-pyaudio
sudo apt install -y nginx git curl wget

# Install certbot for SSL (if using domain)
sudo apt install -y certbot python3-certbot-nginx
```

### 3. Create Application User

```bash
# Create dedicated user for running the application
sudo adduser --system --group --home /opt/luno luno

# Switch to application directory
sudo mkdir -p /opt/luno
sudo chown luno:luno /opt/luno
```

---

## Application Deployment

### 1. Upload Application Files

**Option A: Using Git (Recommended)**

```bash
# On EC2 instance
sudo su - luno
cd /opt/luno

# Clone your repository (if using private repo, set up SSH keys first)
git clone https://github.com/yourusername/luno-backend.git
cd luno-backend

# Or if you're continuing manually:
cd /opt/luno
mkdir backend
cd backend
```

**Option B: Using SCP (from your local machine)**

```bash
# From your local machine
scp -i /path/to/your-key.pem -r /Users/rohankhan/Desktop/Luno/backend ubuntu@YOUR_EC2_IP:/tmp/

# On EC2, move files to proper location
sudo mv /tmp/backend/* /opt/luno/backend/
sudo chown -R luno:luno /opt/luno/backend
```

### 2. Set Up Python Virtual Environment

```bash
# As luno user
sudo su - luno
cd /opt/luno/backend

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Create .env file
cd /opt/luno/backend
nano .env
```

**Add the following to `.env`:**

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Flask Configuration
FLASK_ENV=production
PORT=5005
SECRET_KEY=your_secret_key_here

# Firebase Configuration
GOOGLE_APPLICATION_CREDENTIALS=/opt/luno/backend/firebase-credentials.json

# Logging
LOG_LEVEL=INFO

# Optional: If using Deepgram
DEEPGRAM_API_KEY=your_deepgram_key_here
```

```bash
# Set proper permissions
chmod 600 .env
```

### 4. Upload Firebase Credentials

```bash
# From your local machine
scp -i /path/to/your-key.pem /Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json ubuntu@YOUR_EC2_IP:/tmp/

# On EC2
sudo mv /tmp/firebase-credentials.json /opt/luno/backend/
sudo chown luno:luno /opt/luno/backend/firebase-credentials.json
sudo chmod 600 /opt/luno/backend/firebase-credentials.json
```

### 5. Test Application

```bash
# As luno user, test the application
cd /opt/luno/backend
source venv/bin/activate
python app.py
```

If successful, you should see:
```
[INFO] Background session cleanup task started
 * Running on http://0.0.0.0:5005
```

Press `Ctrl+C` to stop the test.

---

## Configure Nginx as Reverse Proxy

### 1. Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/luno
```

**Add the following configuration:**

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

upstream luno_backend {
    server 127.0.0.1:5005 fail_timeout=0;
}

server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;  # Replace with your domain or EC2 public IP

    # Increase client body size for audio uploads
    client_max_body_size 50M;

    # Logging
    access_log /var/log/nginx/luno_access.log;
    error_log /var/log/nginx/luno_error.log;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Serve simulator HTML directly
    location /test {
        root /opt/luno/backend/simulators;
        try_files /esp32_test_simulator.html =404;
    }

    location /simulator {
        root /opt/luno/backend/simulators;
        try_files /simulator.html =404;
    }

    # API endpoints with rate limiting
    location /upload {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://luno_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeouts for long-running requests
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /text_upload {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://luno_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Proxy all other requests to Flask
    location / {
        proxy_pass http://luno_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed later)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 2. Enable Nginx Configuration

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/luno /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

---

## Process Management with Systemd

### 1. Create Systemd Service File

```bash
sudo nano /etc/systemd/system/luno.service
```

**Add the following:**

```ini
[Unit]
Description=Luno Backend Flask Application
After=network.target

[Service]
Type=notify
User=luno
Group=luno
WorkingDirectory=/opt/luno/backend
Environment="PATH=/opt/luno/backend/venv/bin"
EnvironmentFile=/opt/luno/backend/.env

# Use gunicorn for production
ExecStart=/opt/luno/backend/venv/bin/gunicorn \
    --config /opt/luno/backend/config/gunicorn.conf.py \
    --bind 127.0.0.1:5005 \
    --workers 4 \
    --threads 2 \
    --timeout 300 \
    --access-logfile /var/log/luno/access.log \
    --error-logfile /var/log/luno/error.log \
    app:app

# Restart policy
Restart=always
RestartSec=10

# Resource limits
LimitNOFILE=4096

[Install]
WantedBy=multi-user.target
```

### 2. Create Log Directory

```bash
sudo mkdir -p /var/log/luno
sudo chown luno:luno /var/log/luno
```

### 3. Verify Gunicorn Configuration

Check if `config/gunicorn.conf.py` exists. If not, create it:

```bash
sudo su - luno
nano /opt/luno/backend/config/gunicorn.conf.py
```

**Add basic configuration:**

```python
import multiprocessing

# Server socket
bind = "127.0.0.1:5005"

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
threads = 2

# Timeouts
timeout = 300
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "luno-backend"

# Server mechanics
daemon = False
pidfile = None
```

### 4. Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable luno

# Start service
sudo systemctl start luno

# Check status
sudo systemctl status luno

# View logs
sudo journalctl -u luno -f
```

---

## Domain and SSL Setup

### 1. Configure Domain (If Using Custom Domain)

1. Go to your domain registrar
2. Create an A record pointing to your EC2 Elastic IP
3. Wait for DNS propagation (5-30 minutes)

### 2. Install SSL Certificate with Certbot

```bash
# Install SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Follow prompts:
# - Enter email address
# - Agree to terms of service
# - Choose whether to redirect HTTP to HTTPS (recommended: yes)

# Test automatic renewal
sudo certbot renew --dry-run
```

Certbot will automatically:
- Obtain SSL certificate from Let's Encrypt
- Update Nginx configuration
- Set up automatic renewal

### 3. Update Simulator Configuration

Update the backend URL in the simulator HTML file:

```bash
sudo nano /opt/luno/backend/simulators/esp32_test_simulator.html
```

Find line 338 and update:
```html
<input type="text" class="form-input" id="backendUrl"
       value="https://yourdomain.com">
```

---

## Monitoring and Maintenance

### 1. View Application Logs

```bash
# System logs
sudo journalctl -u luno -f

# Application logs
sudo tail -f /var/log/luno/access.log
sudo tail -f /var/log/luno/error.log

# Nginx logs
sudo tail -f /var/log/nginx/luno_access.log
sudo tail -f /var/log/nginx/luno_error.log
```

### 2. Restart Services

```bash
# Restart application
sudo systemctl restart luno

# Restart nginx
sudo systemctl restart nginx

# View status
sudo systemctl status luno
sudo systemctl status nginx
```

### 3. Update Application

```bash
# Pull latest changes (if using git)
sudo su - luno
cd /opt/luno/backend
git pull

# Or upload new files via SCP

# Restart service
exit
sudo systemctl restart luno
```

### 4. Monitor Resources

```bash
# Check CPU and memory usage
htop

# Check disk usage
df -h

# Check application process
ps aux | grep gunicorn
```

### 5. Set Up CloudWatch (Optional)

Install CloudWatch agent for advanced monitoring:

```bash
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb
```

Configure CloudWatch to monitor:
- CPU utilization
- Memory usage
- Disk I/O
- Network traffic
- Application logs

---

## Testing Deployment

### 1. Test Backend Endpoint

```bash
# From local machine
curl http://YOUR_DOMAIN_OR_IP/
# Expected: "ESP32 Toy Backend is running. Broooo its workinggggggggggggg"
```

### 2. Test Simulator

Open browser and navigate to:
```
http://YOUR_DOMAIN_OR_IP/test
```

### 3. Test Authentication

```bash
curl -X GET http://YOUR_DOMAIN_OR_IP/auth/test \
  -H "X-Device-ID: test_toy_1763434576" \
  -H "X-User-Email: test@lunotoys.com"
```

---

## Security Checklist

- [ ] SSH restricted to specific IP addresses
- [ ] Strong SSH key authentication (no password login)
- [ ] Firewall configured (Security Groups)
- [ ] SSL/TLS certificate installed
- [ ] Environment variables secured (600 permissions)
- [ ] Firebase credentials secured (600 permissions)
- [ ] Regular system updates scheduled
- [ ] CloudWatch monitoring enabled
- [ ] Automatic backups configured
- [ ] Rate limiting enabled in Nginx
- [ ] CORS properly configured

---

## Troubleshooting

### Application Won't Start

```bash
# Check service status
sudo systemctl status luno

# View detailed logs
sudo journalctl -u luno -n 100

# Test manually
sudo su - luno
cd /opt/luno/backend
source venv/bin/activate
python app.py
```

### Nginx Errors

```bash
# Check nginx configuration
sudo nginx -t

# View error logs
sudo tail -f /var/log/nginx/luno_error.log
```

### Permission Issues

```bash
# Fix ownership
sudo chown -R luno:luno /opt/luno/backend

# Fix permissions
sudo chmod 600 /opt/luno/backend/.env
sudo chmod 600 /opt/luno/backend/firebase-credentials.json
```

### High Memory Usage

```bash
# Check gunicorn workers
ps aux | grep gunicorn

# Reduce workers in systemd service file
# Change --workers 4 to --workers 2
sudo nano /etc/systemd/system/luno.service
sudo systemctl daemon-reload
sudo systemctl restart luno
```

---

## Backup Strategy

### 1. Database Backups

Firestore is automatically backed up by Google. Configure:
- Export schedule in Firebase Console
- Retention period: 30 days minimum

### 2. Application Backups

```bash
# Create backup script
sudo nano /opt/luno/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/luno/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup application files
tar -czf $BACKUP_DIR/backend_$DATE.tar.gz /opt/luno/backend \
  --exclude='/opt/luno/backend/venv' \
  --exclude='/opt/luno/backend/temp'

# Keep only last 7 days of backups
find $BACKUP_DIR -name "backend_*.tar.gz" -mtime +7 -delete
```

```bash
# Make executable
sudo chmod +x /opt/luno/backup.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
# Add: 0 2 * * * /opt/luno/backup.sh
```

---

## Cost Optimization

**Estimated Monthly Costs:**
- **t3.medium instance**: ~$30/month
- **30 GB EBS storage**: ~$3/month
- **Data transfer**: Variable (estimate $5-20/month)
- **Total**: ~$40-55/month

**Cost-Saving Tips:**
1. Use Reserved Instances (save up to 40%)
2. Stop instances during non-business hours (if applicable)
3. Use t3.small for development/testing
4. Monitor and optimize API usage (OpenAI, Deepgram)
5. Enable CloudWatch alarms for cost alerts

---

## Quick Reference Commands

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
cd /opt/luno/backend && git pull
sudo systemctl restart luno

# Monitor resources
htop
df -h
free -h
```

---

## Next Steps

1. Set up monitoring and alerting
2. Configure automatic backups
3. Implement CI/CD pipeline
4. Set up staging environment
5. Configure WAF (Web Application Firewall)
6. Enable AWS CloudTrail for audit logging

---

For questions or issues, refer to the main [README.md](../README.md) or check application logs.
