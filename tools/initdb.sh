#!/bin/bash

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

echo "=== WorkFlow Database Initialization ==="
echo "Host: ${DB_HOST}:${DB_PORT}"
echo "Database: ${DB_NAME}"
echo ""

## step 1: create database and workflow tables from DDL
echo "[1/5] Creating database and workflow tables..."
mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -p"${DB_PASS}" < "${PROJ_PATH}/tools/workflow.ddl.sql"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to execute DDL script"
    exit 1
fi
echo "Done."

## step 2: run django migrations
echo "[2/5] Running Django migrations..."
## run dependency migrations first (accounts depends on auth + contenttypes)
python "${PROJ_PATH}/web/manage.py" migrate contenttypes
python "${PROJ_PATH}/web/manage.py" migrate auth
python "${PROJ_PATH}/web/manage.py" migrate admin
python "${PROJ_PATH}/web/manage.py" migrate sessions
## fake all app migrations — tables already created by DDL in step 1
python "${PROJ_PATH}/web/manage.py" migrate accounts --fake
python "${PROJ_PATH}/web/manage.py" migrate workflows --fake
python "${PROJ_PATH}/web/manage.py" migrate system --fake
if [ $? -ne 0 ]; then
    echo "ERROR: Django migration failed"
    exit 1
fi
echo "Done."

## step 3: create default groups and roles
echo "[3/5] Creating default groups and roles..."
python "${PROJ_PATH}/web/manage.py" shell -c "
from django.contrib.auth.models import Group
from accounts.models import Role

## create default groups
for name in ['admin', 'user']:
    Group.objects.get_or_create(name=name)
    print('Group: %s' % name)

## create default roles
for name, desc in [('admin', 'Administrator with full access'), ('user', 'Regular user with limited access')]:
    Role.objects.get_or_create(name=name, defaults={'description': desc})
    print('Role: %s' % name)
"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create default groups/roles"
    exit 1
fi
echo "Done."

## step 4: seed permissions and assign defaults
echo "[4/5] Seeding permissions..."
python "${PROJ_PATH}/web/manage.py" shell -c "
from django.contrib.auth.models import Group
from accounts.models import Permission, GroupPermission, Role
from accounts.permissions import PERMISSION_REGISTRY, DEFAULT_USER_PERMS

## create all permission records
perm_objs = {}
for page, action in PERMISSION_REGISTRY:
    obj, _ = Permission.objects.get_or_create(page=page, action=action)
    perm_objs[(page, action)] = obj
    print('Permission: %s.%s' % (page, action))

## admin role + group -> all permissions
admin_role = Role.objects.get(name='admin')
admin_role.permissions.set(perm_objs.values())
print('Assigned %d permissions to admin role' % len(perm_objs))

admin_group = Group.objects.get(name='admin')
for perm in perm_objs.values():
    GroupPermission.objects.get_or_create(group=admin_group, permission=perm)
print('Assigned %d permissions to admin group' % len(perm_objs))

## user role + group -> limited permissions
user_perm_objs = [perm_objs[k] for k in DEFAULT_USER_PERMS]
user_role = Role.objects.get(name='user')
user_role.permissions.set(user_perm_objs)
print('Assigned %d permissions to user role' % len(user_perm_objs))

user_group = Group.objects.get(name='user')
for perm in user_perm_objs:
    GroupPermission.objects.get_or_create(group=user_group, permission=perm)
print('Assigned %d permissions to user group' % len(user_perm_objs))
"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to seed permissions"
    exit 1
fi
echo "Done."

## step 5: create django superuser
echo "[5/5] Creating Django superuser..."
python "${PROJ_PATH}/web/manage.py" createsuperuser
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create superuser"
    exit 1
fi

## assign superuser to admin group and role
python "${PROJ_PATH}/web/manage.py" shell -c "
from django.contrib.auth.models import User, Group
from accounts.models import Role

## find the most recently created superuser
su = User.objects.filter(is_superuser=True).order_by('-date_joined').first()
if su:
    admin_group, _ = Group.objects.get_or_create(name='admin')
    su.groups.add(admin_group)
    admin_role = Role.objects.get(name='admin')
    admin_role.users.add(su)
    print('Assigned %s to admin group and admin role' % su.username)
"

echo ""
echo "=== Database initialization complete ==="
