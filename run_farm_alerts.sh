#!/bin/bash

# Path definitions
PROJECT_DIR="/home/smurfs/agri-info"
SCRIPT_PATH="$PROJECT_DIR/Utils/update_farm_alerts_db.py"
LOG_DIR="$PROJECT_DIR/logs"
CONDA_PYTHON="/home/smurfs/miniforge3/envs/smurfs/bin/python"

# Make sure log directory exists
mkdir -p "$LOG_DIR"

# Log file
LOG_FILE="$LOG_DIR/farm_alerts_cron.log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Start execution
log_message "====== FARM ALERTS CRON JOB STARTED ======"
log_message "Working directory: $(pwd)"
log_message "Current user: $(whoami)"
log_message "Environment variables:"
env | sort >> "$LOG_FILE"

# Change to project directory
cd "$PROJECT_DIR"
log_message "Changed to directory: $(pwd)"

# Run the Python script
log_message "Running Python script: $SCRIPT_PATH"
"$CONDA_PYTHON" "$SCRIPT_PATH" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
log_message "Python script completed with exit code: $EXIT_CODE"

# Check if the script execution produced expected log files
log_message "Checking for updated log files..."

# List of log files to check
NDVI_LOG="$LOG_DIR/gee_ndvi_health.log"
HARVEST_LOG="$LOG_DIR/gee_harvest_readiness.log"
WATERLOGGING_LOG="$LOG_DIR/gee_waterlogging.log"

if [ -f "$NDVI_LOG" ]; then
    NDVI_MOD_TIME=$(stat -c "%y" "$NDVI_LOG")
    log_message "NDVI log file exists, last modified: $NDVI_MOD_TIME"
else
    log_message "WARNING: NDVI log file does not exist!"
fi

if [ -f "$HARVEST_LOG" ]; then
    HARVEST_MOD_TIME=$(stat -c "%y" "$HARVEST_LOG")
    log_message "Harvest log file exists, last modified: $HARVEST_MOD_TIME"
else
    log_message "WARNING: Harvest log file does not exist!"
fi

if [ -f "$WATERLOGGING_LOG" ]; then
    WATERLOGGING_MOD_TIME=$(stat -c "%y" "$WATERLOGGING_LOG")
    log_message "Waterlogging log file exists, last modified: $WATERLOGGING_MOD_TIME"
else
    log_message "WARNING: Waterlogging log file does not exist!"
fi

log_message "====== FARM ALERTS CRON JOB COMPLETED ======"
