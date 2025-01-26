import os
from dotenv import load_dotenv

load_dotenv(".env.local")

COURSE_API_BASE_URL = os.getenv("COURSE_API_BASE_URL")
COURSE_ID = os.getenv("COURSE_ID", "ai-1")
FRAME_PROCESSING_SLEEP_TIME = os.getenv("FRAME_PROCESSING_SLEEP_TIME", "0.1")
OCR_EXTRACTED_FILE_PATH = os.getenv("OCR_EXTRACTED_FILE_PATH", "./data/cache/extracted_contents.json")
PROCESSED_OUTPUT_FILE_PATH = os.getenv("PROCESSED_OUTPUT_FILE_PATH", "./data/slides/ai-1_processed_slides.json")
SLIDES_EXPIRY_DAYS = int(os.getenv("SLIDES_EXPIRY_DAYS", 7))
SLIDES_OUTPUT_DIR = os.getenv("SLIDES_OUTPUT_DIR","./data/slides")
VIDEO_DOWNLOAD_DIR = os.getenv("VIDEO_DOWNLOAD_DIR", "./data/videos")

os.makedirs("./data/cache", exist_ok=True)
os.makedirs("./data/videos", exist_ok=True)
os.makedirs("./data/slides", exist_ok=True)
