#!/bin/bash

# Exit on error
set -e

# Install system dependencies if needed
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo "Installing Node.js and npm..."
    sudo apt-get update
    sudo apt-get install -y nodejs npm
fi

if ! command -v python3 &> /dev/null; then
    echo "Installing Python3..."
    sudo apt-get update
    sudo apt-get install -y python3-venv
fi

# Create and activate Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Setting up Python virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt

# Start backend server
echo "Starting backend server..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd ../frontend

# Clean up existing node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Set NODE_OPTIONS for legacy OpenSSL provider
export NODE_OPTIONS=--openssl-legacy-provider

# Install dependencies with specific steps to handle version conflicts
echo "Installing npm-force-resolutions..."
npm install --save-dev npm-force-resolutions

echo "Running npm install with forced resolutions..."
npm install --legacy-peer-deps --no-audit

# Start frontend server
echo "Starting frontend server..."
npm start &
FRONTEND_PID=$!

# Function to handle script termination
cleanup() {
    echo "Shutting down servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    deactivate  # Deactivate Python virtual environment
    exit 0
}

# Register the cleanup function for script termination
trap cleanup SIGINT SIGTERM

# Keep the script running
wait $BACKEND_PID $FRONTEND_PID