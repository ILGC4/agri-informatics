#!/bin/bash
# Script to check farm alert script for common errors

SCRIPT_PATH="/home/smurfs/agri-info/Utils/update_farm_alerts_db.py"

echo "=== Checking for SQL errors in the farm alerts script ==="
# Check for trailing commas in SQL UPDATE statements
grep -n "SET.*,\s*WHERE" "$SCRIPT_PATH" && echo "ERROR: Found trailing comma in SQL UPDATE statement" || echo "No SQL comma errors found"

# Check for other common issues
echo -e "\n=== Checking script paths ==="
grep -n "script_dir\|project_dir" "$SCRIPT_PATH" | head -5

echo -e "\n=== Checking for logger initialization issues ==="
grep -n "getLogger\|logger=" "$SCRIPT_PATH" | head -10

echo -e "\n=== Checking database connection parameters ==="
grep -n "DB_PARAMS\|DB_PARAMS_SYNC" "$SCRIPT_PATH" | head -6
