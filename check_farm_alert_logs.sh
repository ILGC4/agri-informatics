#!/bin/bash
# Script to check farm alert logs

LOG_DIR="/home/smurfs/agri-info/logs"
MAIN_LOG="$LOG_DIR/farm_alerts_cron.log"
TEST_LOG="$LOG_DIR/farm_alerts_test.log"
NDVI_LOG="$LOG_DIR/gee_ndvi_health.log"
HARVEST_LOG="$LOG_DIR/gee_harvest_readiness.log"
WATERLOGGING_LOG="$LOG_DIR/gee_waterlogging.log"

echo "=== Farm Alerts Log Status ==="

if [ -f "$TEST_LOG" ]; then
    echo "Test log exists: $(ls -lh "$TEST_LOG")"
    echo "Test log contents:"
    cat "$TEST_LOG"
    echo -e "\n----------------------\n"
fi

echo "Main cron log:"
if [ -f "$MAIN_LOG" ]; then
    echo "  - File exists: $(ls -lh "$MAIN_LOG")"
    echo "  - Last 10 lines:"
    tail -n 10 "$MAIN_LOG"
else
    echo "  - File does not exist yet"
fi

echo -e "\nNDVI Health log:"
if [ -f "$NDVI_LOG" ]; then
    echo "  - File exists: $(ls -lh "$NDVI_LOG")"
    echo "  - Last modified: $(date -r "$NDVI_LOG")"
    echo "  - Last 5 lines:"
    tail -n 5 "$NDVI_LOG"
else
    echo "  - File does not exist yet"
fi

echo -e "\nHarvest Readiness log:"
if [ -f "$HARVEST_LOG" ]; then
    echo "  - File exists: $(ls -lh "$HARVEST_LOG")"
    echo "  - Last modified: $(date -r "$HARVEST_LOG")"
    echo "  - Last 5 lines:"
    tail -n 5 "$HARVEST_LOG"
else
    echo "  - File does not exist yet"
fi

echo -e "\nWaterlogging log:"
if [ -f "$WATERLOGGING_LOG" ]; then
    echo "  - File exists: $(ls -lh "$WATERLOGGING_LOG")"
    echo "  - Last modified: $(date -r "$WATERLOGGING_LOG")"
    echo "  - Last 5 lines:"
    tail -n 5 "$WATERLOGGING_LOG"
else
    echo "  - File does not exist yet"
fi

echo -e "\nCheck crontab entries:"
crontab -l
