#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
RELOAD_DATA=false
BACKEND_DIR="/home/ec2-user/backend"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --reload-data)
            RELOAD_DATA=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --reload-data    Reload test data from Firestore (optional)"
            echo "  -h, --help       Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Luno App Reload & Restart Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Navigate to backend directory
cd "$BACKEND_DIR" || {
    echo -e "${RED}✗ Failed to navigate to backend directory${NC}"
    exit 1
}

# Step 1: Stop luno service (which stops gunicorn)
echo -e "${YELLOW}[1/6] Stopping luno service...${NC}"
sudo systemctl stop luno.service
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Luno service stopped${NC}"
else
    echo -e "${RED}✗ Failed to stop luno service${NC}"
    exit 1
fi
sleep 2

# Verify gunicorn is stopped
if pgrep -f "gunicorn.*app:app" > /dev/null; then
    echo -e "${YELLOW}  Gunicorn still running, force stopping...${NC}"
    pkill -9 -f "gunicorn.*app:app"
    sleep 1
fi
echo ""

# Step 2: Clear Python cache
echo -e "${YELLOW}[2/7] Clearing Python cache...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
echo -e "${GREEN}✓ Python cache cleared${NC}"
echo ""

# Step 3: Fix ffmpeg paths
echo -e "${YELLOW}[3/7] Fixing ffmpeg/ffprobe paths in tts_elevenlabs.py...${NC}"
if [ -f "tts_elevenlabs.py" ]; then
    # Replace ffmpeg and ffprobe references to use full paths
    sed -i 's|"ffmpeg"|"/usr/local/bin/ffmpeg"|g' tts_elevenlabs.py
    sed -i 's|"ffprobe"|"/usr/local/bin/ffprobe"|g' tts_elevenlabs.py
    echo -e "${GREEN}✓ ffmpeg paths fixed${NC}"
else
    echo -e "${YELLOW}  tts_elevenlabs.py not found, skipping...${NC}"
fi
echo ""

# Step 4: Reload data (optional)
if [ "$RELOAD_DATA" = true ]; then
    echo -e "${YELLOW}[4/7] Reloading test data...${NC}"
    if [ -f "scripts/setup_test_data.py" ]; then
        source venv/bin/activate
        python scripts/setup_test_data.py
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Test data reloaded${NC}"
        else
            echo -e "${RED}✗ Failed to reload test data${NC}"
            echo -e "${YELLOW}  Continuing anyway...${NC}"
        fi
        deactivate
    else
        echo -e "${YELLOW}  setup_test_data.py not found, skipping...${NC}"
    fi
else
    echo -e "${YELLOW}[4/7] Skipping data reload (use --reload-data to enable)${NC}"
fi
echo ""

# Step 5: Reload systemd daemon
echo -e "${YELLOW}[5/7] Reloading systemd daemon...${NC}"
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd daemon reloaded${NC}"
echo ""

# Step 6: Start luno service (which starts gunicorn)
echo -e "${YELLOW}[6/7] Starting luno service...${NC}"
sudo systemctl start luno.service
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Luno service started${NC}"
else
    echo -e "${RED}✗ Failed to start luno service${NC}"
    echo ""
    echo -e "${YELLOW}Checking service status:${NC}"
    sudo systemctl status luno.service --no-pager
    exit 1
fi
sleep 3
echo ""

# Step 7: Verify services are running
echo -e "${YELLOW}[7/7] Verifying services...${NC}"
echo ""

# Check luno service
if sudo systemctl is-active --quiet luno.service; then
    echo -e "${GREEN}✓ Luno service is running${NC}"
    SERVICE_STATUS="${GREEN}Active${NC}"
else
    echo -e "${RED}✗ Luno service is not running${NC}"
    SERVICE_STATUS="${RED}Inactive${NC}"
fi

# Check gunicorn processes
GUNICORN_COUNT=$(pgrep -f "gunicorn.*app:app" | wc -l)
if [ "$GUNICORN_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Gunicorn is running (${GUNICORN_COUNT} workers)${NC}"
    GUNICORN_STATUS="${GREEN}Running (${GUNICORN_COUNT} workers)${NC}"
else
    echo -e "${RED}✗ Gunicorn is not running${NC}"
    GUNICORN_STATUS="${RED}Not running${NC}"
fi
echo ""

# Display summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Luno Service:    $SERVICE_STATUS"
echo -e "Gunicorn:        $GUNICORN_STATUS"
echo -e "Data Reloaded:   $([ "$RELOAD_DATA" = true ] && echo -e "${GREEN}Yes${NC}" || echo -e "${YELLOW}No${NC}")"
echo ""

# Show recent logs
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Recent Logs (last 10 lines)${NC}"
echo -e "${BLUE}========================================${NC}"
if [ -f "/var/log/luno/error.log" ]; then
    tail -n 10 /var/log/luno/error.log
else
    echo -e "${YELLOW}No error logs found${NC}"
fi
echo ""

# Final status check
if sudo systemctl is-active --quiet luno.service && [ "$GUNICORN_COUNT" -gt 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}   ✓ Reload & Restart Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "App is running at: ${BLUE}http://127.0.0.1:5005${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}   ✗ Issues Detected${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "Run these commands to troubleshoot:"
    echo "  sudo systemctl status luno.service"
    echo "  sudo journalctl -u luno.service -n 50"
    echo "  tail -f /var/log/luno/error.log"
    echo ""
    exit 1
fi
