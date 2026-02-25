#!/bin/bash

## =============================================================
## WorkFlow Platform Upgrade Script
##
## Upgrades the platform to the latest version:
##   1. Stops services
##   2. Applies incremental database schema changes
##   3. Runs Django migrations
##   4. Seeds data for existing users
##   5. Starts services
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

echo "=== WorkFlow Platform Upgrade ==="
echo "Host: ${DB_HOST}:${DB_PORT}"
echo "Database: ${DB_NAME}"
echo ""

## step 1: stop services
echo "[1/5] Stopping services..."
"${PROJ_PATH}/bin/service.sh" stop
if [ $? -ne 0 ]; then
    echo "WARNING: Failed to stop services (may not be running)"
fi
echo "Done."

## step 2: apply incremental DDL changes (idempotent via IF NOT EXISTS)
echo "[2/5] Applying database schema changes..."
mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -p"${DB_PASS}" < "${PROJ_PATH}/tools/upgrade.sql"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to apply database schema changes"
    exit 1
fi
echo "Done."

## step 3: run Django migrations
echo "[3/5] Running Django migrations..."
python "${PROJ_PATH}/web/manage.py" migrate accounts
if [ $? -ne 0 ]; then
    echo "ERROR: Django migration failed"
    exit 1
fi
echo "Done."

## step 4: seed UserProfile for existing users (idempotent)
echo "[4/5] Seeding user profiles..."
python "${PROJ_PATH}/web/manage.py" shell -c "
from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.utils import timezone
now = timezone.now()
count = 0
for u in User.objects.all():
    _, created = UserProfile.objects.get_or_create(user=u, defaults={'password_changed_at': now})
    if created:
        count += 1
        print('  Created profile: %s' % u.username)
print('Seeded %d new user profile(s).' % count)
"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to seed user profiles"
    exit 1
fi
echo "Done."

## step 5: start services
echo "[5/5] Starting services..."
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
