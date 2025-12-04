#!/bin/bash

echo "Starting Mock Claude API Server..."
echo

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo
echo "Starting server on port 8001..."
python server.py --port 8001 --delay 0.02
