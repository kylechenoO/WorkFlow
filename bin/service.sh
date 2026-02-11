#!/bin/bash

## resolve project root directory
declare -x PROJ_PATH=$(dirname $(dirname $(realpath $0)))

## load service config
source "${PROJ_PATH}/etc/service.conf"

## activate project venv
source "${PROJ_PATH}/bin/activate"

## start gunicorn
exec gunicorn \
    --bind "${HOST}:${PORT}" \
    --workers "${WORKERS}" \
    --threads "${PROCESSES}" \
    --timeout "${TIMEOUT}" \
    --log-level "${LOG_LEVEL}" \
    --access-logfile "${ACCESS_LOG}" \
    --error-logfile "${ERROR_LOG}" \
    --chdir "${PROJ_PATH}" \
    "bin.WorkFlow:create_app()"
