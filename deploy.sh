#!/bin/bash

# PlushieAI Production Deployment Script for AWS EC2 t3.micro Ubuntu
set -e

echo "🚀 Starting PlushieAI deployment..."

# Update system
sudo apt update
sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv nginx ffmpeg

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages in virtual environment
pip install -r requirements.txt
pip install gunicorn

# Create log directories
sudo mkdir -p /var/log/gunicorn
sudo chown ubuntu:ubuntu /var/log/gunicorn

# Copy nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/plushie-ai
sudo ln -sf /etc/nginx/sites-available/plushie-ai /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Create systemd service
sudo cp plushie-ai.service /etc/systemd/system/

# Reload systemd and start services
sudo systemctl daemon-reload
sudo systemctl enable plushie-ai
sudo systemctl start plushie-ai
sudo systemctl enable nginx
sudo systemctl restart nginx

# Check status
echo "✅ Checking services..."
sudo systemctl status plushie-ai --no-pager
sudo systemctl status nginx --no-pager

echo "🎉 Deployment complete!"
echo "Your PlushieAI is running at: http://$(curl -s ifconfig.me)"