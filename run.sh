#!/bin/bash
# Wrapper script to run the video concatenation tool

# Activate virtual environment
source venv/bin/activate

# Run the Python script with all passed arguments
python concat-videos.py "$@" 