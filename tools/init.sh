#!/bin/bash

declare -x PROJ_PATH=$(dirname $(dirname $(realpath $0)))
/opt/miniforge/bin/python -m venv .
