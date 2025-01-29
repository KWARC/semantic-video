import json
import os
from dotenv import load_dotenv
from rapidfuzz import fuzz, process
from config import OCR_EXTRACTED_FILE_PATH, PROCESSED_SLIDES_FILE_PATH, COURSE_IDS

if not all([OCR_EXTRACTED_FILE_PATH, PROCESSED_SLIDES_FILE_PATH]):
    raise EnvironmentError("Missing required environment variables. Check .env.local.")

course_ids = COURSE_IDS.split(",")

for course_id in course_ids:
    processed_slides_file_path = f"{PROCESSED_SLIDES_FILE_PATH}".replace("{course_id}", course_id)
    ocr_extracted_file_path = f"{OCR_EXTRACTED_FILE_PATH}".replace("{course_id}", course_id)

    with open(processed_slides_file_path, "r", encoding="utf-8") as slides_file:
        slides = json.load(slides_file)

    with open(ocr_extracted_file_path, "r", encoding="utf-8") as results_file:
        results = json.load(results_file)

    text_data = []
    for video_id, video_data in results.items():
        if "extracted_content" in video_data:  # Check if extracted_content exists
            for timestamp, text_entry in video_data["extracted_content"].items():
                text_data.append(
                    {
                        "start_time": text_entry["start_time"],
                        "end_time": text_entry["end_time"],
                        "ocr_slide_content": text_entry["ocr_slide_content"],
                        "video_id": video_id,
                    }
                )

    for slide in slides:
        slide_text = slide["slideContent"]

        ocr_slide_contents = [entry["ocr_slide_content"] for entry in text_data]

        best_match = process.extractOne(
            slide_text, ocr_slide_contents, scorer=fuzz.token_set_ratio
        )

        if best_match:
            matched_text, match_score = best_match[0], best_match[1]

            if match_score > 50:
                matched_entry = next(
                    entry for entry in text_data if entry["ocr_slide_content"] == matched_text
                )

                slide["start_time"] = matched_entry["start_time"]
                slide["end_time"] = matched_entry["end_time"]
                slide["video_id"] = matched_entry["video_id"]

    with open(processed_slides_file_path, "w", encoding="utf-8") as output_file:
        json.dump(slides, output_file, indent=4, ensure_ascii=False)

    print(f"Slides updated with timestamps and URLs successfully for course {course_id}!")
