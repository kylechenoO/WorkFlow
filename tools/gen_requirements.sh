#!/bin/bash

declare -x PROJ_PATH=$(dirname $(dirname $(realpath $0)))
source ${PROJ_PATH}/bin/activate
pip freeze > ${PROJ_PATH}/requirements.txt
deactivate
