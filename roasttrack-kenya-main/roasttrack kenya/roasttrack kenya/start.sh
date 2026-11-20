#!/usr/bin/env bash
set -e

mkdir -p output logs

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
fi

echo "Starting RoastTrack Kenya Simulation Engine..."
.venv/bin/python realtime_simulation.py > logs/realtime-simulation.log 2>&1 &
SIM_PID=$!

sleep 2

echo "Starting Scenario Terminal..."
.venv/bin/python realtime_terminal.py &
TERM_PID=$!

echo "Starting Desktop Dashboard..."
.venv/bin/python scientific_ui.py &
UI_PID=$!

cleanup() {
    echo "Stopping background workers..."
    kill $SIM_PID $TERM_PID $UI_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait $UI_PID
