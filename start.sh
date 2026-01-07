#!/bin/bash

# Start Telegram bot in background
python main.py &

# Start Streamlit dashboard in foreground
streamlit run dashboard.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.headless=true
