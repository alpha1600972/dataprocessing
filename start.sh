#!/bin/bash

set -e  # stop le script en cas d'erreur

VENV_DIR="datadev-venv"

install_packages() {
    echo "Installing required packages..."
    pip install -r requirements.txt
}

create_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment..."
        python3 -m venv $VENV_DIR
    else
        echo "Virtual environment already exists."
    fi
}

activate_venv() {
    echo "Activating virtual environment..."
    source $VENV_DIR/bin/activate
}

start_docker() {
    echo "Starting Docker container..."
    docker-compose -f docker-compose.yml up -d
}

run_pipeline() {
    echo "Running data processing pipeline..."
    python dataprocessing/main.py
}

# Execution flow
create_venv
activate_venv
install_packages
start_docker
run_pipeline

echo "Pipeline executed successfully!"


