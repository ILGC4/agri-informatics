#!/bin/bash

# This is a one-time test script for the farm alerts cron job
# It will remove itself from crontab after execution

LOG_FILE="/home/smurfs/agri-info/logs/farm_alerts_test.log"
echo "====== FARM ALERTS TEST STARTED: $(date) ======" > $LOG_FILE
echo "Testing Python environment:" >> $LOG_FILE
/home/smurfs/miniforge3/envs/smurfs/bin/python -c "import sys; print('Python version: ' + sys.version)" >> $LOG_FILE 2>&1
/home/smurfs/miniforge3/envs/smurfs/bin/python -c "import ee; print('Earth Engine module available')" >> $LOG_FILE 2>&1

# Test database connection
echo "Testing database connection:" >> $LOG_FILE
/home/smurfs/miniforge3/envs/smurfs/bin/python -c "import psycopg2; conn = psycopg2.connect(dbname='smurf', user='smurfs', password='smurfs123', host='localhost', port=5432); print('Database connection successful'); conn.close()" >> $LOG_FILE 2>&1

echo "Checking if script exists:" >> $LOG_FILE
if [ -f "/home/smurfs/agri-info/Utils/update_farm_alerts_db.py" ]; then
    echo "Script found at /home/smurfs/agri-info/Utils/update_farm_alerts_db.py" >> $LOG_FILE
    echo "First 10 lines of script:" >> $LOG_FILE
    head -10 "/home/smurfs/agri-info/Utils/update_farm_alerts_db.py" >> $LOG_FILE
else
    echo "ERROR: Script not found at /home/smurfs/agri-info/Utils/update_farm_alerts_db.py" >> $LOG_FILE
fi

echo "Removing test job from crontab:" >> $LOG_FILE
crontab -l | grep -v "test_farm_alerts.sh" | crontab -
echo "Test completed" >> $LOG_FILE
echo "====== FARM ALERTS TEST COMPLETED: $(date) ======" >> $LOG_FILE
