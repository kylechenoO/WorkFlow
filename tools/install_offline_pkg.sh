#!/bin/bash

declare -x PROJ_PATH=$(dirname $(dirname $(realpath $0)))
source ${PROJ_PATH}/bin/activate
pip install --no-index --find-links=${PROJ_PATH}/packages -r ${PROJ_PATH}/requirements.txt
deactivate
