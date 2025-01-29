# Load environment variables from .env.local
export $(grep -v '^#' /path/to/.env.local | xargs)

# Activate virtual environment if needed
# source venv/bin/activate

# Run the scripts sequentially
echo "Starting slide_fetcher..."
python3 /path/to/scripts/slide_fetcher.py || { echo "slide_fetcher failed!"; exit 1; }

echo "Starting video_text_extractor..."
python3 /path/to/scripts/video_text_extractor.py || { echo "video_text_extractor failed!"; exit 1; }

echo "Starting slide_matcher..."
python3 /path/to/scripts/slide_matcher.py || { echo "slide_matcher failed!"; exit 1; }

echo "All scripts executed successfully."
