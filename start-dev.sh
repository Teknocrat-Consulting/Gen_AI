#!/bin/bash

# Development server startup script
echo "Starting Flight Booking Assistant Development Server..."
echo "Project root: $(pwd)"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Please run this script from the Gen_AI project root directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Installing dependencies..."
    uv sync
fi

# Start the server
echo "Starting server on http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "Press Ctrl+C to stop"
echo ""

uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000