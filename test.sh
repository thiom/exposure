#!/usr/bin/env bash
# Runs the tests with one command. Works on macOS and Linux.
#
# Usage:
#   ./test.sh                        unit tests, Robot Framework tests and pylint
#   ./test.sh unit                   only the unit tests
#   ./test.sh robot                  only the Robot Framework tests (browser)
#   ./test.sh lint                   only pylint
#   ./test.sh tests.test_comments    only the given unit tests
#
# The tests use their own databases and never touch database.db.
# Each mode installs only the tools it needs into the virtual environment.
#
# Environment variables:
#   PORT=5002                 port of the Robot Framework test server
#   SKIP_BROWSER_INSTALL=1    do not install the test browser
#   WITH_DEPS=1               also install the system libraries Chromium needs
#                             on Linux (uses sudo)
set -euo pipefail

cd "$(dirname "$0")"

mode="${1:-all}"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required but was not found." >&2
    exit 1
fi

if [ ! -x venv/bin/python ]; then
    echo "Creating virtual environment..."
    rm -rf venv
    if ! python3 -m venv venv; then
        rm -rf venv
        echo "Could not create the virtual environment." >&2
        echo "On Debian and Ubuntu, install it with: sudo apt install python3-venv" >&2
        exit 1
    fi
fi

# installs the given packages unless the given modules can already be imported
install() {
    local modules="$1"
    shift
    if ! venv/bin/python -c "import $modules" 2>/dev/null; then
        echo "Installing $*..."
        venv/bin/pip install -q "$@"
    fi
}

# checks the Python version of the virtual environment, e.g. require_python 3 11 pylint
require_python() {
    local major="$1" minor="$2" tool="$3"
    if ! venv/bin/python -c "import sys; sys.exit(sys.version_info < ($major, $minor))"; then
        echo "$tool needs Python $major.$minor or newer, but the virtual" >&2
        echo "environment uses $(venv/bin/python --version)." >&2
        echo "Remove the venv directory and run again with a newer python3." >&2
        return 1
    fi
}

run_unit() {
    require_python 3 9 Flask || return 1
    install flask flask
    echo "Running unit tests..."
    venv/bin/python -m unittest ${@+"$@"}
}

run_lint() {
    require_python 3 10 Pylint || return 1
    install "flask, pylint" flask pylint
    echo "Running pylint..."
    venv/bin/pylint ./*.py tests story_tests
}

server_pid=""

# stops the test server when the script exits, also when the tests fail
stop_server() {
    if [ -n "$server_pid" ]; then
        kill "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
        server_pid=""
    fi
}
trap stop_server EXIT

run_robot() {
    local port="${PORT:-5002}"
    local url="http://127.0.0.1:$port"

    if ! command -v curl >/dev/null 2>&1; then
        echo "curl is required for the Robot Framework tests." >&2
        return 1
    fi
    require_python 3 11 "The Robot Framework Browser library" || return 1
    # robotframework-browser-batteries brings its own Node.js for the Browser library
    install "flask, robot, Browser, BrowserBatteries" flask robotframework \
        robotframework-browser robotframework-browser-batteries

    if curl -s -o /dev/null "$url"; then
        echo "Port $port is already in use. Stop the running application or set PORT." >&2
        return 1
    fi

    if [ -z "${SKIP_BROWSER_INSTALL:-}" ]; then
        echo "Installing the test browser (only downloads on the first run)..."
        if [ -n "${WITH_DEPS:-}" ]; then
            venv/bin/rfbrowser install --with-deps chromium
        else
            venv/bin/rfbrowser install chromium
        fi
    fi

    echo "Starting the application..."
    venv/bin/python story_tests/server.py "$port" > robot_server.log 2>&1 &
    server_pid=$!

    for _ in $(seq 1 30); do
        if [ "$(curl -s -o /dev/null -w '%{http_code}' "$url/login")" = "200" ]; then
            break
        fi
        if ! kill -0 "$server_pid" 2>/dev/null; then
            echo "The application did not start:" >&2
            cat robot_server.log >&2
            return 1
        fi
        sleep 1
    done

    if [ "$(curl -s -o /dev/null -w '%{http_code}' "$url/login")" != "200" ]; then
        echo "The application did not answer in $url" >&2
        cat robot_server.log >&2
        return 1
    fi

    echo "Running Robot Framework tests..."
    local status=0
    venv/bin/robot --variable HEADLESS:true --variable "SERVER:127.0.0.1:$port" story_tests \
        || status=1
    stop_server
    if [ $status -ne 0 ] && [ "$(uname)" = "Linux" ] && [ -z "${WITH_DEPS:-}" ]; then
        echo "If the browser did not start, Chromium may be missing system libraries:" >&2
        echo "run again with WITH_DEPS=1 ./test.sh robot" >&2
    fi
    return $status
}

case "$mode" in
    all)
        # run everything even if one part fails, and fail if any part fails
        status=0
        run_unit || status=1
        echo
        run_robot || status=1
        echo
        run_lint || status=1
        exit $status
        ;;
    unit) run_unit ;;
    robot) run_robot ;;
    lint) run_lint ;;
    *) run_unit ${@+"$@"} ;;
esac
