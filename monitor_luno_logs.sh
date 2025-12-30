#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Log directory
LOG_DIR="/var/log/luno"

# Function to display header
show_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}   Luno Service Log Monitor${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Function to list all log files
list_log_files() {
    echo -e "${YELLOW}Log files being monitored:${NC}"
    echo ""

    if [ -d "$LOG_DIR" ]; then
        local log_files=($(find "$LOG_DIR" -type f -name "*.log" 2>/dev/null))

        if [ ${#log_files[@]} -eq 0 ]; then
            echo -e "${RED}✗ No log files found in $LOG_DIR${NC}"
            return 1
        fi

        for log_file in "${log_files[@]}"; do
            local size=$(du -h "$log_file" 2>/dev/null | cut -f1)
            local lines=$(wc -l < "$log_file" 2>/dev/null)
            echo -e "  ${GREEN}✓${NC} $log_file"
            echo -e "    Size: ${CYAN}$size${NC} | Lines: ${CYAN}$lines${NC}"
        done

        echo ""
        return 0
    else
        echo -e "${RED}✗ Log directory $LOG_DIR does not exist${NC}"
        return 1
    fi
}

# Function to check if service is running
check_service_status() {
    echo -e "${YELLOW}Service Status:${NC}"

    if systemctl is-active --quiet luno.service 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Luno service is running"
    else
        echo -e "  ${RED}✗${NC} Luno service is NOT running"
    fi

    local worker_count=$(pgrep -f "gunicorn.*app:app" | wc -l)
    if [ "$worker_count" -gt 0 ]; then
        echo -e "  ${GREEN}✓${NC} Gunicorn workers: ${CYAN}$worker_count${NC}"
    else
        echo -e "  ${RED}✗${NC} No gunicorn workers running"
    fi

    echo ""
}

# Function to tail logs with colored output
tail_logs() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}   Tailing logs (Ctrl+C to stop)${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    # Use tail -f with multiple files
    # The -f flag follows the files as they grow
    # Using --pid=$$ ensures tail exits when this script exits
    tail -f \
        "$LOG_DIR/access.log" \
        "$LOG_DIR/error.log" \
        2>/dev/null | while read -r line; do

        # Color code based on content
        if [[ "$line" =~ "==> /var/log/luno/access.log <==" ]]; then
            echo -e "${CYAN}$line${NC}"
        elif [[ "$line" =~ "==> /var/log/luno/error.log <==" ]]; then
            echo -e "${MAGENTA}$line${NC}"
        elif [[ "$line" =~ (ERROR|Error|error) ]]; then
            echo -e "${RED}$line${NC}"
        elif [[ "$line" =~ (WARNING|Warning|warning) ]]; then
            echo -e "${YELLOW}$line${NC}"
        elif [[ "$line" =~ (INFO|Info) ]]; then
            echo -e "${BLUE}$line${NC}"
        elif [[ "$line" =~ "GET|POST|PUT|DELETE|PATCH" ]]; then
            echo -e "${GREEN}$line${NC}"
        else
            echo "$line"
        fi
    done
}

# Main execution
show_header
check_service_status

if list_log_files; then
    echo -e "${YELLOW}Starting log monitoring in 2 seconds...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""
    sleep 2
    tail_logs
else
    echo ""
    echo -e "${RED}Cannot monitor logs. Please check if:${NC}"
    echo "  1. The luno service has been started"
    echo "  2. The log directory exists: $LOG_DIR"
    echo "  3. You have permission to read the log files"
    echo ""
    exit 1
fi
