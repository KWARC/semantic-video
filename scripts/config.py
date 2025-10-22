import json
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

COURSE_API_BASE_URL = os.getenv("COURSE_API_BASE_URL")
NEXT_PUBLIC_FLAMS_URL=os.getenv("NEXT_PUBLIC_FLAMS_URL")
FAU_TV_BASE_URL = os.getenv("FAU_TV_BASE_URL")
FAU_TV_API_BASE_URL=os.getenv("FAU_TV_API_BASE_URL")
FAU_TV_OEMBED_BASE_URL=os.getenv("FAU_TV_OEMBED_BASE_URL")
COURSE_IDS = os.getenv("COURSE_IDS", "").split(",")
FAU_TV_COURSE_IDS = json.loads(os.getenv("FAU_TV_COURSE_IDS", "{}"))
CURRENT_SEM_JSON = os.getenv("CURRENT_SEM_JSON", "current-sem.json")
FRAME_PROCESSING_SLEEP_TIME = float(os.getenv("FRAME_PROCESSING_SLEEP_TIME", "0.1"))
OCR_EXTRACTED_FILE_PATH = os.getenv("OCR_EXTRACTED_FILE_PATH", "data/cache/")
RESULTS_FILE_PATH = os.getenv("RESULTS_FILE_PATH", "data/results/ocr_results.json")
SLIDES_EXPIRY_DAYS = int(os.getenv("SLIDES_EXPIRY_DAYS", 1))
SLIDES_OUTPUT_DIR = os.getenv("SLIDES_OUTPUT_DIR", "data/slides/")
VIDEO_DOWNLOAD_DIR = os.getenv("VIDEO_DOWNLOAD_DIR", "data/videos/")
ALL_COURSES_CLIPS_JSON = os.getenv("ALL_COURSES_CLIPS_JSON", "data/cache/all_courses_clips.json")

os.makedirs(OCR_EXTRACTED_FILE_PATH, exist_ok=True)
os.makedirs(VIDEO_DOWNLOAD_DIR, exist_ok=True)
os.makedirs(SLIDES_OUTPUT_DIR, exist_ok=True)
