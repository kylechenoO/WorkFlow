#!/bin/bash
##
## WorkFlow Service Manager
## Usage: service.sh {start|stop|restart|status} [backend|frontend]
##        If no service name given, operates on both backend and frontend.
##

## resolve project root directory
declare -x PROJ_PATH=$(dirname $(dirname $(realpath $0)))

## load service config
source "${PROJ_PATH}/etc/service.conf"

## service definitions
declare -A SVC_PORT=( [backend]="${BACKEND_PORT:-5001}" [frontend]="${FRONTEND_PORT:-5002}" )
declare -A SVC_HOST=( [backend]="${BACKEND_HOST:-0.0.0.0}" [frontend]="${FRONTEND_HOST:-0.0.0.0}" )
declare -A SVC_WORKERS=( [backend]="${BACKEND_WORKERS:-1}" [frontend]="${FRONTEND_WORKERS:-4}" )
declare -A SVC_THREADS=( [backend]="${BACKEND_THREADS:-4}" [frontend]="${FRONTEND_THREADS:-4}" )
declare -A SVC_TIMEOUT=( [backend]="${BACKEND_TIMEOUT:-120}" [frontend]="${FRONTEND_TIMEOUT:-120}" )
declare -A SVC_LOG_LEVEL=( [backend]="${BACKEND_LOG_LEVEL:-info}" [frontend]="${FRONTEND_LOG_LEVEL:-info}" )
declare -A SVC_ACCESS_LOG=( [backend]="${BACKEND_ACCESS_LOG:--}" [frontend]="${FRONTEND_ACCESS_LOG:--}" )
declare -A SVC_ERROR_LOG=( [backend]="${BACKEND_ERROR_LOG:--}" [frontend]="${FRONTEND_ERROR_LOG:--}" )
declare -A SVC_CHDIR=( [backend]="${PROJ_PATH}" [frontend]="${PROJ_PATH}/web" )
declare -A SVC_APP=( [backend]="bin.WorkFlow:create_app()" [frontend]="wfsite.wsgi:application" )
declare -A SVC_LABEL=( [backend]="Backend (Flask API)" [frontend]="Frontend (Django UI)" )

## ---------------------------------------------------------------
## get pid of service listening on given port
## ---------------------------------------------------------------
get_pid() {
    local port=$1
    local pid=$(lsof -ti "tcp:${port}" 2>/dev/null | head -1)
    echo "${pid}"
}

## ---------------------------------------------------------------
## start a single service
## ---------------------------------------------------------------
do_start() {
    local svc=$1
    local port=${SVC_PORT[$svc]}
    local pid=$(get_pid "${port}")

    if [ -n "${pid}" ]; then
        echo "[${SVC_LABEL[$svc]}] Already running (pid ${pid}, port ${port})"
        return 0
    fi

    echo -n "[${SVC_LABEL[$svc]}] Starting on port ${port} ... "

    ## activate project venv
    source "${PROJ_PATH}/bin/activate"

    gunicorn \
        --bind "${SVC_HOST[$svc]}:${port}" \
        --workers "${SVC_WORKERS[$svc]}" \
        --threads "${SVC_THREADS[$svc]}" \
        --timeout "${SVC_TIMEOUT[$svc]}" \
        --log-level "${SVC_LOG_LEVEL[$svc]}" \
        --access-logfile "${SVC_ACCESS_LOG[$svc]}" \
        --error-logfile "${SVC_ERROR_LOG[$svc]}" \
        --chdir "${SVC_CHDIR[$svc]}" \
        --daemon \
        "${SVC_APP[$svc]}"

    ## verify it started
    sleep 1
    local new_pid=$(get_pid "${port}")
    if [ -n "${new_pid}" ]; then
        echo "OK (pid ${new_pid})"
    else
        echo "FAILED"
        return 1
    fi
}

## ---------------------------------------------------------------
## stop a single service
## ---------------------------------------------------------------
do_stop() {
    local svc=$1
    local port=${SVC_PORT[$svc]}
    local pid=$(get_pid "${port}")

    if [ -z "${pid}" ]; then
        echo "[${SVC_LABEL[$svc]}] Not running"
        return 0
    fi

    echo -n "[${SVC_LABEL[$svc]}] Stopping (pid ${pid}) ... "
    kill "${pid}" 2>/dev/null

    ## wait for process to exit
    for i in $(seq 1 20); do
        if ! kill -0 "${pid}" 2>/dev/null; then
            echo "OK"
            return 0
        fi
        sleep 0.2
    done

    ## force kill if still alive
    kill -9 "${pid}" 2>/dev/null
    echo "OK (forced)"
}

## ---------------------------------------------------------------
## restart a single service
## ---------------------------------------------------------------
do_restart() {
    local svc=$1
    do_stop "${svc}"
    do_start "${svc}"
}

## ---------------------------------------------------------------
## show status of a single service
## ---------------------------------------------------------------
do_status() {
    local svc=$1
    local port=${SVC_PORT[$svc]}
    local pid=$(get_pid "${port}")

    if [ -n "${pid}" ]; then
        echo "[${SVC_LABEL[$svc]}] Running (pid ${pid}, port ${port})"
    else
        echo "[${SVC_LABEL[$svc]}] Stopped (port ${port})"
    fi
}

## ---------------------------------------------------------------
## main
## ---------------------------------------------------------------
ACTION=$1
TARGET=$2

if [ -z "${ACTION}" ]; then
    echo "Usage: $0 {start|stop|restart|status} [backend|frontend]"
    exit 1
fi

## determine which services to operate on
if [ -n "${TARGET}" ]; then
    if [ "${TARGET}" != "backend" ] && [ "${TARGET}" != "frontend" ]; then
        echo "Error: unknown service '${TARGET}'. Use 'backend' or 'frontend'."
        exit 1
    fi
    TARGETS="${TARGET}"
else
    TARGETS="backend frontend"
fi

case "${ACTION}" in
    start)
        for svc in ${TARGETS}; do do_start "${svc}"; done
        ;;
    stop)
        for svc in ${TARGETS}; do do_stop "${svc}"; done
        ;;
    restart)
        for svc in ${TARGETS}; do do_restart "${svc}"; done
        ;;
    status)
        for svc in ${TARGETS}; do do_status "${svc}"; done
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status} [backend|frontend]"
        exit 1
        ;;
esac
