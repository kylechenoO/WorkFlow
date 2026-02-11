#!/bin/bash

declare -x PROJ_PATH=$(dirname $(dirname $(realpath $0)))
source ${PROJ_PATH}/bin/activate
pip download -r ${PROJ_PATH}/requirements.txt -d ${PROJ_PATH}/packages --only-binary=:all:
deactivate
