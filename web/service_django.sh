#!/bin/bash

## resolve project root directory
declare -x PROJ_PATH=$(dirname $(dirname $(realpath $0)))

## activate project venv
source "${PROJ_PATH}/bin/activate"

## start django development server
exec python "${PROJ_PATH}/web/manage.py" runserver 0.0.0.0:8000
