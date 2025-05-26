# Cron Job Directory Documentation (cron_job)

## Overview
This directory contains shell scripts responsible for automating satellite data collection and farm alert processing tasks. It manages scheduled obs that run at specific times to collect satellite imagery, process agricultural data, and update farm alert databases automatically.

## Script Files
1. cron_setup.sh
   - **Purpose:** Sets up automated satellite image collection jobs
      - Configures cron jobs for three satellite data sources: Sentinel-2, Sentinel-1, and Landsat-9
      - Schedules daily data collection at different times (5:27 PM, 5:30 PM, and 5:35 PM)
      - Creates log directories and removes any existing satellite collection jobs before adding new ones
      - Includes a test job to verify cron functionality
      - Uses conda Python environment located at /home/smurfs/miniforge3/envs/smurfs/bin/python 

2. farm_alerts_cron.sh
   - **Purpose:** Sets up automated farm alert processing tasks
      - Creates a wrapper script (run_farm_alerts.sh) for farm alert jobs
      - Configures cron job to run farm alerts at 2:05 AM daily
      - Sets up environment variables (PATH, SHELL, PYTHONPATH, HOME, LANG) in crontab
      - Includes a test job that runs 3 minutes after execution for immediate verification
      - Provides comprehensive logging and monitoring capabilities

3. run_farm_alerts.sh
   - **Purpose:** Wrapper scipt that executes farm alert processing
      - Runs the Python script update_farm_alerts_db.py to process farm alerts
      - Provides detailed logging of execution status, environment variables, and directory changes
      - Monitors and reports on expected log files (NDVI, harvest readiness, waterlogging)
      - Records execution start/end times and exit codes for debugging
      - Ensures proper working directory and environment setup

4. test_farm_alerts.sh
   - **Purpose:** One-time diagnostic script for farm alert system
      - Tests Python environment and Earth Engine module availability
      - Verifies database connectivity to PostgreSQL database
      - Checks if the farm alert processing script exists and displays its first 10 lines
      - Self-removes from crontab after execution to prevent repeated runs
      - Creates detailed test log for troubleshooting setup issues

## Key Features
- Automated Scheduling: All scripts use cron for time-based job execution
- Comprehensive Logging: Each job creates detailed logs in /home/smurfs/agri-info/logs/
- Environment Management: Proper conda environment activation and path configuration
- Error Handling: Scripts include error redirection and exit code monitoring
- Self-Management: Scripts can add/remove themselves from crontab as needed

## File Dependencies
- Python Scripts: satellite_gee.py and update_farm_alerts_db.py in the Utils directory
- Conda Environment: /home/smurfs/miniforge3/envs/smurfs/
- Database: PostgreSQL database named 'smurf'
- Project Directory: /home/smurfs/agri-info/