#!/bin/bash

declare -x PROJ_PATH=$(dirname $(dirname $(realpath $0)))
rm -rvf $(find ${PROJ_PATH} -name '__py*' | xargs)
