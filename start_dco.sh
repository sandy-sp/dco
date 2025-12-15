#!/bin/bash

# Function to kill processes on exit
cleanup() {
    echo "Shutting down DCO..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    exit
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM EXIT

# Load Environment Variables
if [ -f .env ]; then
    export $(cat .env | xargs)
    echo "Loaded configuration from .env"
fi

# 1. Check Backend Dependencies
echo "[1/3] Checking Backend..."
if [ ! -d "backend/venv" ]; then
    echo "Creating Python venv..."
    python3 -m venv backend/venv
    source backend/venv/bin/activate
    pip install -r backend/requirements.txt
else
    source backend/venv/bin/activate
fi

echo "Starting DCO Backend..."
# Run from root so 'backend' package is resolved correctly
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# 2. Check Frontend Dependencies
echo "[2/3] Checking Frontend..."
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing Node modules..."
    cd frontend && npm install && cd ..
fi

echo "Starting DCO Frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo "[3/3] DCO System Online"
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:8000"
echo "Press Ctrl+C to stop."

wait
