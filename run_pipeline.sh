#!/bin/bash

# Set the full path to the project directory
PROJECT_DIR="/srv/semantic-video"

# Set the full path to the Python virtual environment
VENV_DIR="$PROJECT_DIR/venv"

# Set the full path to the Python script
FAU_CLIP_EXTRACTOR="$PROJECT_DIR/scripts/fau_clip_extractor.py"
SLIDE_FETCHER_SCRIPT="$PROJECT_DIR/scripts/slide_fetcher.py"
VIDEO_TEXT_EXTRACTOR_SCRIPT="$PROJECT_DIR/scripts/video_text_extractor.py"
SLIDE_MATCHER_SCRIPT="$PROJECT_DIR/scripts/slide_matcher.py"
AUTODETECT_SCRIPT="$PROJECT_DIR/scripts/auto_detect.py"


# Change to the project directory
cd "$PROJECT_DIR" || exit

# Activate the virtual environment

source "$VENV_DIR/bin/activate"

"$VENV_DIR/bin/python" "$FAU_CLIP_EXTRACTOR" && echo "$FAU_CLIP_EXTRACTOR executed successfully!" || { echo "Error executing $FAU_CLIP_EXTRACTOR"; exit 1; }
"$VENV_DIR/bin/python" "$SLIDE_FETCHER_SCRIPT" && echo "$SLIDE_FETCHER_SCRIPT executed successfully!" || { echo "Error executing $SLIDE_FETCHER_SCRIPT"; exit 1; }
"$VENV_DIR/bin/python" "$VIDEO_TEXT_EXTRACTOR_SCRIPT" && echo "$VIDEO_TEXT_EXTRACTOR_SCRIPT executed successfully!" || { echo "Error executing $VIDEO_TEXT_EXTRACTOR_SCRIPT"; exit 1; }
"$VENV_DIR/bin/python" "$SLIDE_MATCHER_SCRIPT" && echo "$SLIDE_MATCHER_SCRIPT executed successfully!" || { echo "Error executing $SLIDE_MATCHER_SCRIPT"; exit 1; }
"$VENV_DIR/bin/python" "$AUTODETECT_SCRIPT" && echo "$AUTODETECT_SCRIPT executed successfully!" || { echo "Error in autodetect"; exit 1; }
echo "All scripts ran successfully!"
