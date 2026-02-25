#!/bin/bash

## =============================================================
## WorkFlow Platform Upgrade Script (v0.0.2 → v0.0.3)
##
## Upgrades the platform to v0.0.3:
##   1. Stops services
##   2. Applies incremental database changes (tools/upgrade.sql)
##   3. Starts services
##
## Usage: bash tools/upgrade.sh
## =============================================================

## resolve project root directory
declare -x PROJ_PATH=$(dirname $(dirname $(realpath $0)))

## activate project venv
source "${PROJ_PATH}/bin/activate"

## parse db config from global.json
DB_HOST=$(python3 -c "import json5; c=json5.load(open('${PROJ_PATH}/etc/global.json')); print(c['db']['host'])")
DB_PORT=$(python3 -c "import json5; c=json5.load(open('${PROJ_PATH}/etc/global.json')); print(c['db']['port'])")
DB_USER=$(python3 -c "import json5; c=json5.load(open('${PROJ_PATH}/etc/global.json')); print(c['db']['username'])")
DB_PASS=$(python3 -c "import json5; c=json5.load(open('${PROJ_PATH}/etc/global.json')); print(c['db']['password'])")
DB_NAME=$(python3 -c "import json5; c=json5.load(open('${PROJ_PATH}/etc/global.json')); print(c['db']['database'])")

echo "=== WorkFlow Platform Upgrade (v0.0.2 → v0.0.3) ==="
echo "Host: ${DB_HOST}:${DB_PORT}"
echo "Database: ${DB_NAME}"
echo ""

## step 1: stop services
echo "[1/3] Stopping services..."
"${PROJ_PATH}/bin/service.sh" stop
if [ $? -ne 0 ]; then
    echo "WARNING: Failed to stop services (may not be running)"
fi
echo "Done."

## step 2: apply incremental database changes
## (creates new tables, seeds data, records Django migration — all in SQL)
echo "[2/3] Applying database changes..."
mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -p"${DB_PASS}" < "${PROJ_PATH}/tools/upgrade.sql"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to apply database changes"
    exit 1
fi
echo "Done."

## step 3: start services
echo "[3/3] Starting services..."
"${PROJ_PATH}/bin/service.sh" start
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start services"
    exit 1
fi

## verify
sleep 2
"${PROJ_PATH}/bin/service.sh" status

echo ""
echo "=== Upgrade complete ==="
