#!/bin/bash

declare -x PROJ_PATH=$(dirname $(dirname $(realpath $0)))
declare -x PROJ_BIN="${PROJ_PATH}/bin"
declare -x OLD_PATH=''

## change path on activate
sed -i -e "s|export VIRTUAL_ENV=.*$|export VIRTUAL_ENV=${PROJ_PATH}|g" ${PROJ_BIN}/activate
sed -i -e "s|set -gx VIRTUAL_ENV .*$|set -gx VIRTUAL_ENV ${PROJ_PATH}|g" ${PROJ_BIN}/activate.fish
sed -i -e "s|setenv VIRTUAL_ENV .*$|setenv VIRTUAL_ENV ${PROJ_PATH}|g" ${PROJ_BIN}/activate.csh

## change the python path
for fn in $(grep -Rni '^#!' ${PROJ_BIN}/* 2> /dev/null | awk -F':' '{ print $1; }')
do
    sed -i -e "s|^#!.*$|#!${PROJ_BIN}/python|g" ${fn}

done

