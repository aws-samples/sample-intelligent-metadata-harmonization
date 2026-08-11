#!/bin/bash
# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

set -e

# Get the project root directory (4 levels up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# Activate virtual environment
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "Activated Python virtual environment"
else
    echo "No virtual environment found, using system Python"
fi

# Configuration
THREADS="1"
HOST="0.0.0.0"
PORT="8080"
RELOAD=""

# Load env vars from .env file
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(cat "$PROJECT_ROOT/.env" | sed 's/^/export /')
    echo "Loaded environment variables from .env file"
    RELOAD="--reload"
fi

# Start the metadata harmonization API
echo "Starting metadata harmonization API server..."
exec uvicorn --workers "$THREADS" --host "$HOST" --port "$PORT" $RELOAD "metadata_harmonization_api.api.main:app"
