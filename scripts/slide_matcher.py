import json
import os
from dotenv import load_dotenv
from rapidfuzz import fuzz, process

load_dotenv(".env.local")

SLIDES_FILE_PATH = os.getenv("SLIDES_FILE_PATH")
OCR_CACHE_FILE_PATH = os.getenv("OCR_CACHE_FILE_PATH")
PROCESSED_OUTPUT_FILE_PATH = os.getenv("PROCESSED_OUTPUT_FILE_PATH")

if not all([SLIDES_FILE_PATH, OCR_CACHE_FILE_PATH, PROCESSED_OUTPUT_FILE_PATH]):
    raise EnvironmentError("Missing required environment variables. Check .env.local.")

with open(SLIDES_FILE_PATH, "r", encoding="utf-8") as slides_file:
    slides = json.load(slides_file)

with open(OCR_CACHE_FILE_PATH, "r", encoding="utf-8") as results_file:
    results = json.load(results_file)

text_data = []
for video_id, video_data in results.items():
    if "extracted_text" in video_data:  # Check if extracted_text exists
        for timestamp, text_entry in video_data["extracted_text"].items():
            text_data.append(
                {
                    "start_time": text_entry["start_time"],
                    "end_time": text_entry["end_time"],
                    "text_value": text_entry["text_value"],
                    "video_id": video_id,
                }
            )

for slide in slides:
    slide_text = slide["slideContent"]

    text_values = [entry["text_value"] for entry in text_data]

    best_match = process.extractOne(
        slide_text, text_values, scorer=fuzz.token_set_ratio
    )

    if best_match:
        matched_text, match_score = best_match[0], best_match[1]

        if match_score > 50:
            matched_entry = next(
                entry for entry in text_data if entry["text_value"] == matched_text
            )

            slide["start_time"] = matched_entry["start_time"]
            slide["end_time"] = matched_entry["end_time"]
            slide["video_id"] = matched_entry["video_id"]

with open(PROCESSED_OUTPUT_FILE_PATH, "w", encoding="utf-8") as output_file:
    json.dump(slides, output_file, indent=4, ensure_ascii=False)

print("Slides updated with timestamps and URLs successfully!")