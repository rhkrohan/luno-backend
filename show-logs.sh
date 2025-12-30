#!/bin/bash

# Script to tail all log files in a directory continuously
# Usage: ./show-logs.sh [log_directory]
# Default log directory is ./logs if not specified

# Color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default log directory
LOG_DIR="${1:-./logs}"

echo -e "${GREEN}=== Log Viewer ===${NC}"
echo -e "${BLUE}Watching logs in: ${LOG_DIR}${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Check if directory exists
if [ ! -d "$LOG_DIR" ]; then
    echo -e "${RED}Error: Directory '$LOG_DIR' does not exist${NC}"
    echo -e "${YELLOW}Creating directory: $LOG_DIR${NC}"
    mkdir -p "$LOG_DIR"
    echo -e "${YELLOW}Directory created. Add log files to $LOG_DIR and run this script again.${NC}"
    exit 0
fi

# Find all log files
LOG_FILES=$(find "$LOG_DIR" -type f \( -name "*.log" -o -name "*.out" -o -name "*.err" \) 2>/dev/null)

# Check if any log files exist
if [ -z "$LOG_FILES" ]; then
    echo -e "${YELLOW}No log files found in $LOG_DIR${NC}"
    echo -e "${YELLOW}Looking for files with extensions: .log, .out, .err${NC}"
    echo ""
    echo -e "${BLUE}Watching for new log files... (Press Ctrl+C to stop)${NC}"
    # Watch the directory for new files
    while true; do
        sleep 2
        NEW_FILES=$(find "$LOG_DIR" -type f \( -name "*.log" -o -name "*.out" -o -name "*.err" \) 2>/dev/null)
        if [ ! -z "$NEW_FILES" ]; then
            echo -e "${GREEN}Log files detected! Starting tail...${NC}"
            exec "$0" "$@"
        fi
    done
else
    echo -e "${GREEN}Found log files:${NC}"
    echo "$LOG_FILES" | while read -r file; do
        echo -e "  ${BLUE}▸${NC} $file"
    done
    echo ""
    echo -e "${GREEN}Starting to tail all logs...${NC}"
    echo "-----------------------------------"
    echo ""

    # Tail all log files with file names
    # Using -F to follow files even if they're rotated
    tail -F $LOG_FILES 2>/dev/null
fi
