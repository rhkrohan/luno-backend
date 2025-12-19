#!/bin/bash

# Luno Backend - AWS EC2 Deployment Script
# This script automates the deployment process on a fresh EC2 instance

set -e  # Exit on error

echo "========================================="
echo "Luno Backend EC2 Deployment Script"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script as root${NC}"
    echo "Run as: ./deploy_ec2.sh"
    exit 1
fi

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    echo -e "${RED}Cannot detect OS${NC}"
    exit 1
fi

echo "Detected OS: $OS"
echo ""

# Step 1: Update system
echo "Step 1: Updating system packages..."
sudo apt update
sudo apt upgrade -y
print_status "System updated"
echo ""

# Step 2: Install system dependencies
echo "Step 2: Installing system dependencies..."
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    portaudio19-dev \
    python3-pyaudio \
    nginx \
    git \
    curl \
    wget \
    htop \
    certbot \
    python3-certbot-nginx

print_status "System dependencies installed"
echo ""

# Step 3: Create application user
echo "Step 3: Setting up application user..."
if id "luno" &>/dev/null; then
    print_warning "User 'luno' already exists, skipping creation"
else
    sudo adduser --system --group --home /opt/luno luno
    print_status "User 'luno' created"
fi

sudo mkdir -p /opt/luno/backend
sudo chown -R luno:luno /opt/luno
echo ""

# Step 4: Prompt for deployment method
echo "Step 4: How would you like to deploy the code?"
echo "1) Git clone (recommended for production)"
echo "2) Copy from current directory"
read -p "Select option [1-2]: " deploy_method

if [ "$deploy_method" == "1" ]; then
    read -p "Enter Git repository URL: " git_repo
    sudo -u luno git clone $git_repo /opt/luno/backend
    print_status "Code cloned from repository"
elif [ "$deploy_method" == "2" ]; then
    CURRENT_DIR=$(pwd)
    sudo cp -r $CURRENT_DIR/* /opt/luno/backend/
    sudo chown -R luno:luno /opt/luno/backend
    print_status "Code copied to /opt/luno/backend"
else
    print_error "Invalid option"
    exit 1
fi
echo ""

# Step 5: Set up Python virtual environment
echo "Step 5: Setting up Python virtual environment..."
cd /opt/luno/backend
sudo -u luno python3.11 -m venv venv
sudo -u luno /opt/luno/backend/venv/bin/pip install --upgrade pip
sudo -u luno /opt/luno/backend/venv/bin/pip install -r requirements.txt
print_status "Virtual environment created and dependencies installed"
echo ""

# Step 6: Configure environment variables
echo "Step 6: Configuring environment variables..."
if [ -f /opt/luno/backend/.env ]; then
    print_warning ".env file already exists"
    read -p "Do you want to overwrite it? (y/n): " overwrite
    if [ "$overwrite" != "y" ]; then
        echo "Skipping .env configuration"
    else
        configure_env=true
    fi
else
    configure_env=true
fi

if [ "$configure_env" = true ]; then
    read -p "Enter OpenAI API Key: " openai_key
    read -p "Enter Flask SECRET_KEY (or press Enter to generate): " secret_key

    if [ -z "$secret_key" ]; then
        secret_key=$(openssl rand -hex 32)
        print_status "Generated random SECRET_KEY"
    fi

    sudo tee /opt/luno/backend/.env > /dev/null <<EOF
# OpenAI API Configuration
OPENAI_API_KEY=$openai_key

# Flask Configuration
FLASK_ENV=production
PORT=5005
SECRET_KEY=$secret_key

# Firebase Configuration
GOOGLE_APPLICATION_CREDENTIALS=/opt/luno/backend/firebase-credentials.json

# Logging
LOG_LEVEL=INFO
EOF

    sudo chown luno:luno /opt/luno/backend/.env
    sudo chmod 600 /opt/luno/backend/.env
    print_status "Environment variables configured"
fi
echo ""

# Step 7: Upload Firebase credentials
echo "Step 7: Firebase credentials setup"
if [ -f /opt/luno/backend/firebase-credentials.json ]; then
    print_warning "firebase-credentials.json already exists"
else
    print_warning "Please upload firebase-credentials.json to /opt/luno/backend/"
    echo "You can do this with: scp -i your-key.pem firebase-credentials.json ubuntu@YOUR_IP:/tmp/"
    echo "Then run: sudo mv /tmp/firebase-credentials.json /opt/luno/backend/"
    read -p "Press Enter when done..."
fi

if [ -f /opt/luno/backend/firebase-credentials.json ]; then
    sudo chown luno:luno /opt/luno/backend/firebase-credentials.json
    sudo chmod 600 /opt/luno/backend/firebase-credentials.json
    print_status "Firebase credentials configured"
else
    print_error "Firebase credentials not found - you'll need to add this manually"
fi
echo ""

# Step 8: Create necessary directories
echo "Step 8: Creating necessary directories..."
sudo mkdir -p /var/log/luno
sudo chown luno:luno /var/log/luno
sudo mkdir -p /opt/luno/backups
sudo chown luno:luno /opt/luno/backups
print_status "Directories created"
echo ""

# Step 9: Configure gunicorn (if config doesn't exist)
echo "Step 9: Configuring gunicorn..."
if [ ! -f /opt/luno/backend/config/gunicorn.conf.py ]; then
    sudo mkdir -p /opt/luno/backend/config
    sudo tee /opt/luno/backend/config/gunicorn.conf.py > /dev/null <<'EOF'
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
EOF
    sudo chown luno:luno /opt/luno/backend/config/gunicorn.conf.py
    print_status "Gunicorn configuration created"
else
    print_warning "Gunicorn config already exists"
fi
echo ""

# Step 10: Create systemd service
echo "Step 10: Creating systemd service..."
sudo tee /etc/systemd/system/luno.service > /dev/null <<'EOF'
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

ExecStart=/opt/luno/backend/venv/bin/gunicorn \
    --config /opt/luno/backend/config/gunicorn.conf.py \
    --bind 127.0.0.1:5005 \
    --workers 4 \
    --threads 2 \
    --timeout 300 \
    --access-logfile /var/log/luno/access.log \
    --error-logfile /var/log/luno/error.log \
    app:app

Restart=always
RestartSec=10
LimitNOFILE=4096

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable luno
print_status "Systemd service created and enabled"
echo ""

# Step 11: Configure nginx
echo "Step 11: Configuring nginx..."
read -p "Enter your domain name (or press Enter to use server IP): " domain_name

if [ -z "$domain_name" ]; then
    domain_name="_"
    print_warning "Using default server name (IP address)"
else
    print_status "Using domain: $domain_name"
fi

sudo tee /etc/nginx/sites-available/luno > /dev/null <<EOF
# Rate limiting
limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=10r/s;

upstream luno_backend {
    server 127.0.0.1:5005 fail_timeout=0;
}

server {
    listen 80;
    server_name $domain_name;

    client_max_body_size 50M;

    access_log /var/log/nginx/luno_access.log;
    error_log /var/log/nginx/luno_error.log;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Serve simulator HTML
    location /test {
        alias /opt/luno/backend/simulators/esp32_test_simulator.html;
    }

    location /simulator {
        alias /opt/luno/backend/simulators/simulator.html;
    }

    # API endpoints with rate limiting
    location /upload {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://luno_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /text_upload {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://luno_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location / {
        proxy_pass http://luno_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/luno /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx config
if sudo nginx -t; then
    print_status "Nginx configuration created and tested"
else
    print_error "Nginx configuration test failed"
    exit 1
fi

sudo systemctl restart nginx
print_status "Nginx restarted"
echo ""

# Step 12: Start application
echo "Step 12: Starting application..."
sudo systemctl start luno

# Wait a moment for service to start
sleep 3

if sudo systemctl is-active --quiet luno; then
    print_status "Application started successfully"
else
    print_error "Application failed to start"
    echo "Check logs with: sudo journalctl -u luno -n 50"
    exit 1
fi
echo ""

# Step 13: SSL Certificate (optional)
echo "Step 13: SSL Certificate Setup"
if [ "$domain_name" != "_" ]; then
    read -p "Do you want to install SSL certificate with Let's Encrypt? (y/n): " install_ssl
    if [ "$install_ssl" == "y" ]; then
        read -p "Enter email for SSL certificate: " ssl_email
        sudo certbot --nginx -d $domain_name --non-interactive --agree-tos --email $ssl_email
        print_status "SSL certificate installed"
    else
        print_warning "Skipping SSL installation"
    fi
else
    print_warning "Skipping SSL installation (no domain configured)"
fi
echo ""

# Step 14: Summary
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo -e "${GREEN}Service Status:${NC}"
sudo systemctl status luno --no-pager -l
echo ""
echo -e "${GREEN}Access URLs:${NC}"
if [ "$domain_name" != "_" ]; then
    echo "  Backend: http://$domain_name/"
    echo "  Simulator: http://$domain_name/test"
else
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
    echo "  Backend: http://$PUBLIC_IP/"
    echo "  Simulator: http://$PUBLIC_IP/test"
fi
echo ""
echo -e "${GREEN}Useful Commands:${NC}"
echo "  View logs: sudo journalctl -u luno -f"
echo "  Restart: sudo systemctl restart luno"
echo "  Status: sudo systemctl status luno"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Test the backend: curl http://YOUR_IP/"
echo "  2. Test the simulator: Open http://YOUR_IP/test in browser"
echo "  3. Update simulator with your backend URL"
echo "  4. Configure your domain DNS if not done already"
echo "  5. Review security settings in AWS Security Groups"
echo ""
echo "For detailed documentation, see: docs/AWS_EC2_DEPLOYMENT.md"
echo ""
