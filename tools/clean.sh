#!/bin/bash

declare -x PROJ_PATH=$(dirname $(dirname $(realpath $0)))
rm -rvf $(find ${PROJ_PATH} -name '__pycache__*' | xargs)
rm -rvf ${PROJ_PATH}/bin/{activate,activate.csh,activate.fish,Activate.ps1,f2py,fab,flask,inv,invoke,normalizer,pip,pip3,pip3.12,pyjson5,python,python3,python3.12,django-admin,gunicorn,sqlformat,gunicornc}
rm -rvf ${PROJ_PATH}/lib/python3.12
rm -rvf ${PROJ_PATH}/lib64
rm -rvf ${PROJ_PATH}/{pyvenv.cfg,gunicorn.ctl}
rm -rvf ${PROJ_PATH}/etc/{ssh,ssl}
