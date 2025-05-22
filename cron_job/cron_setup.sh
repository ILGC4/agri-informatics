#!/bin/bash

# Set up cron jobs for satellite image collection
# Create temporary crontab file
TEMP_CRONTAB=$(mktemp)

# Get current crontab
crontab -l > "$TEMP_CRONTAB" 2>/dev/null || echo "" > "$TEMP_CRONTAB"

# Define paths with absolute paths
PROJECT_DIR="/home/smurfs/agri-info"
SCRIPT_PATH="$PROJECT_DIR/Utils/satellite_gee.py"
LOG_DIR="$PROJECT_DIR/logs"

# Use the full path to the Python interpreter in your conda environment
CONDA_PYTHON="/home/smurfs/miniforge3/envs/smurfs/bin/python"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Define cron job commands with error redirection
SENTINEL2_CMD="cd $PROJECT_DIR && $CONDA_PYTHON $SCRIPT_PATH S2 >> $LOG_DIR/sentinel2_cron.log 2>&1"
SENTINEL1_CMD="cd $PROJECT_DIR && $CONDA_PYTHON $SCRIPT_PATH S1 >> $LOG_DIR/sentinel1_cron.log 2>&1"
LANDSAT_CMD="cd $PROJECT_DIR && $CONDA_PYTHON $SCRIPT_PATH L9 >> $LOG_DIR/landsat_cron.log 2>&1"

# Check if cron jobs already exist and remove old versions
sed -i "/\/satellite_gee\.py S2/d" "$TEMP_CRONTAB"
sed -i "/\/satellite_gee\.py S1/d" "$TEMP_CRONTAB"
sed -i "/\/satellite_gee\.py L9/d" "$TEMP_CRONTAB"

# minute hour day month weekday
# Add jobs with times in the future
echo "35 17 * * * $SENTINEL2_CMD" >> "$TEMP_CRONTAB"
echo "Added Sentinel-2 cron job (daily at 5:35 PM)"

# Add Sentinel-1 job
echo "30 17 * * * $SENTINEL1_CMD" >> "$TEMP_CRONTAB"
echo "Added Sentinel-1 cron job (daily at 5:30 PM)"

# Add Landsat job 
echo "27 17 * * * $LANDSAT_CMD" >> "$TEMP_CRONTAB"
echo "Added Landsat cron job (daily at 5:27 PM)"

# Add Landsat cron test job using full path to echo
echo "46 17 * * * /bin/echo 'cron test $(date)' >> $LOG_DIR/landsat_cron.log" >> "$TEMP_CRONTAB"
echo "Added Landsat cron test job (daily at 5:46 PM, using /bin/echo)"

# Install new crontab
crontab "$TEMP_CRONTAB"
echo "Cron jobs installed successfully"

# Remove temporary file
rm "$TEMP_CRONTAB"

echo "To view current cron jobs, run: crontab -l"