#!/bin/bash

# Create images directory
mkdir -p images/generated

# Start Telegram bot in background
python main.py &
BOT_PID=$!

# Start Streamlit in background  
streamlit run dashboard.py --server.port 8501 --server.address 127.0.0.1 --server.headless true &
STREAMLIT_PID=$!

# Wait for Streamlit to start
sleep 5

# Start FastAPI proxy server (main port)
uvicorn combined_server:app --host 0.0.0.0 --port ${PORT:-8080}
