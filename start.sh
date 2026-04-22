#!/bin/bash
#set -euo pipefail # Exit immediately if a command exits with a non-zero status, treat unset variables as an error, and prevent errors in a pipeline from being masked.

VENV_DIR="datadev-venv"
PYTHON="python3"
CONTAINER_NAME="postgres_dataprocessing"

trap 'echo "Error occurred"; docker-compose down' EXIT

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

create_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log "Creating virtual environment..."
        $PYTHON -m venv "$VENV_DIR"
    else
        log "Virtual environment already exists."
    fi
}

install_packages() {
    log "Installing required packages..."
    if [ ! -f "requirements.txt" ]; then
        log "Error: requirements.txt not found!"
        return 1
    fi
    "$VENV_DIR/bin/pip" install -r requirements.txt
}

start_docker() {
    log "Starting Docker container..."
    docker-compose -f docker-compose.yml up -d
}

wait_for_docker() {
    log "Waiting for PostgreSQL to be ready..."
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker exec postgres_dataprocessing pg_isready -U ddev > /dev/null 2>&1; then
            log "PostgreSQL is ready."
            return 0
        fi
        ((attempt++))
        sleep 1
    done
    log "PostgreSQL failed to start"
    return 1
}

run_pipeline() {
    log "Running data processing pipeline..."
    "$VENV_DIR/bin/python" main.py
}

# Execution flow
create_venv
install_packages
start_docker
wait_for_docker
run_pipeline

log "Pipeline executed successfully!"
trap - EXIT