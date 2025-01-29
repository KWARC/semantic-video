import os
from dotenv import load_dotenv

load_dotenv(".env.local")

COURSE_API_BASE_URL = os.getenv("COURSE_API_BASE_URL")
COURSE_ID = os.getenv("COURSE_ID", "ai-1")
FRAME_PROCESSING_SLEEP_TIME = os.getenv("FRAME_PROCESSING_SLEEP_TIME", "0.1")
OCR_EXTRACTED_FILE_PATH = os.getenv("OCR_EXTRACTED_FILE_PATH", f"./data/cache/{COURSE_ID}_extracted_contents.json")
PROCESSED_SLIDES_FILE_PATH = os.getenv("PROCESSED_SLIDES_FILE_PATH", f"./data/slides/{COURSE_ID}_processed_slides.json")
SLIDES_EXPIRY_DAYS = int(os.getenv("SLIDES_EXPIRY_DAYS", 7))
SLIDES_OUTPUT_DIR = os.getenv("SLIDES_OUTPUT_DIR", "./data/slides")
VIDEO_DOWNLOAD_DIR = os.getenv("VIDEO_DOWNLOAD_DIR", "./data/videos")

COURSE_IDS = os.getenv("COURSE_IDS", "")

os.makedirs("./data/cache", exist_ok=True)
os.makedirs("./data/videos", exist_ok=True)
os.makedirs("./data/slides", exist_ok=True)
