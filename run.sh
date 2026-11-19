#!/usr/bin/env bash
# Starts the application with one command.
# Creates the virtual environment, installs Flask and creates the database
# when they are missing. Works on macOS and Linux.
#
# Usage: ./run.sh [flask run options, e.g. --debug]
# The port can be changed with the PORT environment variable (default 5001;
# port 5000 is taken by the AirPlay receiver on macOS).
set -euo pipefail

cd "$(dirname "$0")"

port="${PORT:-5001}"

for command in python3 sqlite3; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "$command is required but was not found." >&2
        exit 1
    fi
done

if ! python3 -c "import sys; sys.exit(sys.version_info < (3, 9))"; then
    echo "Python 3.9 or newer is required (found $(python3 --version))." >&2
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

if ! venv/bin/python -c "import flask" 2>/dev/null; then
    echo "Installing Flask..."
    venv/bin/pip install -q flask
fi

if [ ! -f database.db ]; then
    echo "Creating database..."
    sqlite3 database.db < schema.sql
fi

echo "Starting the application at http://127.0.0.1:$port"
exec venv/bin/flask run --port "$port" ${@+"$@"}
