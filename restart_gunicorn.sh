#!/bin/bash

echo "Stopping Gunicorn..."
pkill -f "gunicorn.*app:app"

# Wait for processes to fully stop
sleep 2

echo "Starting Gunicorn..."
cd /home/ec2-user/backend
source venv/bin/activate
gunicorn --bind 127.0.0.1:5005 \
    --workers 4 \
    --threads 2 \
    --timeout 300 \
    --access-logfile /var/log/luno/access.log \
    --error-logfile /var/log/luno/error.log \
    --daemon \
    app:app

# Wait for startup
sleep 2

# Check if Gunicorn is running
if pgrep -f "gunicorn.*app:app" > /dev/null; then
    echo "✓ Gunicorn restarted successfully"
    echo "Workers running:"
    pgrep -f "gunicorn.*app:app" | wc -l
else
    echo "✗ Failed to start Gunicorn"
    exit 1
fi
