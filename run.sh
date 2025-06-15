#!/bin/bash

# --- Start FastAPI Backend ---
echo "Starting FastAPI backend..."
# Ensure you are in the project root or adjust path to src/main.py
# --reload is good for development; remove for production
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload &

# Store the PID of the FastAPI process
FASTAPI_PID=$!
echo "FastAPI backend started with PID: $FASTAPI_PID"

# Give FastAPI a moment to start up
sleep 5

# --- Start Streamlit Frontend ---
echo "Starting Streamlit frontend..."
# Ensure you are in the project root or adjust path to src/streamlit_app.py
streamlit run src/streamlit_app.py

# --- Cleanup ---
# This part will only run when Streamlit is closed.
echo "Streamlit frontend closed. Stopping FastAPI backend (PID: $FASTAPI_PID)..."
kill $FASTAPI_PID
echo "FastAPI backend stopped."
