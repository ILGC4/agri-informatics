#!/bin/bash

# Create a wrapper script for the farm alerts job
WRAPPER_SCRIPT="/home/smurfs/agri-info/run_farm_alerts.sh"
cat > "$WRAPPER_SCRIPT" << 'EOF'
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
EOF

# Make script executable
chmod +x "$WRAPPER_SCRIPT"
echo "Created wrapper script at $WRAPPER_SCRIPT"

# Update crontab
CRONTAB_FILE=$(mktemp)
crontab -l | grep -v "FARM ALERTS" > "$CRONTAB_FILE"

# Add environment variables
if ! grep -q "PATH=" "$CRONTAB_FILE"; then
    echo "PATH=/home/smurfs/miniforge3/envs/smurfs/bin:/usr/local/bin:/usr/bin:/bin" >> "$CRONTAB_FILE"
fi
if ! grep -q "SHELL=" "$CRONTAB_FILE"; then
    echo "SHELL=/bin/bash" >> "$CRONTAB_FILE"
fi
if ! grep -q "PYTHONPATH=" "$CRONTAB_FILE"; then
    echo "PYTHONPATH=/home/smurfs/agri-info" >> "$CRONTAB_FILE"
fi
if ! grep -q "HOME=" "$CRONTAB_FILE"; then
    echo "HOME=/home/smurfs" >> "$CRONTAB_FILE"
fi
if ! grep -q "LANG=" "$CRONTAB_FILE"; then
    echo "LANG=en_US.UTF-8" >> "$CRONTAB_FILE"
fi

# Add wrapper script to crontab for both 2:00 AM and an immediate test 
echo "5 2 * * * $WRAPPER_SCRIPT" >> "$CRONTAB_FILE"

# Calculate time for 3 minutes from now
CURRENT_MINUTE=$(date +%M)
TEST_MINUTE=$(( (CURRENT_MINUTE + 3) % 60 ))
CURRENT_HOUR=$(date +%H)
TEST_HOUR=$CURRENT_HOUR
if [[ $TEST_MINUTE -lt $CURRENT_MINUTE ]]; then
    TEST_HOUR=$(( (CURRENT_HOUR + 1) % 24 ))
fi

echo "$TEST_MINUTE $TEST_HOUR * * * $WRAPPER_SCRIPT" >> "$CRONTAB_FILE"
echo "Added test job to run at $TEST_HOUR:$TEST_MINUTE"

# Install crontab
crontab "$CRONTAB_FILE"
rm "$CRONTAB_FILE"

echo "Crontab updated with new entries"
echo "You can check the log file in 3 minutes at: /home/smurfs/agri-info/logs/farm_alerts_cron.log"
echo "Or run the wrapper script manually now with: $WRAPPER_SCRIPT"