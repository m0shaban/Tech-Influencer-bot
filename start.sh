#!/bin/bash

# Create images directory
mkdir -p images/generated

# Start Telegram bot in background
python main.py &

# Start FastAPI server (serves images + proxies to Streamlit)
python combined_server.py
