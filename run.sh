#!/bin/bash
# PureRoute v2 Decision Engine Launcher
cd "$(dirname "$0")"

if [ -d "venv" ]; then
    echo "Starting PureRoute v2 Streamlit Dashboard with venv..."
    ./venv/bin/streamlit run app.py --server.port 8501 --server.headless true
else
    echo "Starting PureRoute v2 Streamlit Dashboard with system python..."
    streamlit run app.py --server.port 8501 --server.headless true
fi
