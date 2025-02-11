import os
import json
from rapidfuzz import fuzz, process
from config import OCR_EXTRACTED_FILE_PATH, SLIDES_OUTPUT_DIR, COURSE_IDS
from utils import clean_text


if not all([OCR_EXTRACTED_FILE_PATH, SLIDES_OUTPUT_DIR]):
    raise EnvironmentError("Missing required environment variables. Check .env.local.")

for course_id in COURSE_IDS:
    processed_slides_file_path = os.path.join(
        SLIDES_OUTPUT_DIR, f"{course_id}_processed_slides.json"
    )
    ocr_extracted_file_path = os.path.join(
        OCR_EXTRACTED_FILE_PATH, f"{course_id}_extracted_content.json"
    )

    if not os.path.exists(processed_slides_file_path):
        print(f"Processed slides file not found: {processed_slides_file_path}")
        continue

    if not os.path.exists(ocr_extracted_file_path):
        print(f"OCR extracted file not found: {ocr_extracted_file_path}")
        continue

    with open(processed_slides_file_path, "r", encoding="utf-8") as slides_file:
        slides = json.load(slides_file)

    with open(ocr_extracted_file_path, "r", encoding="utf-8") as results_file:
        results = json.load(results_file)

    text_data = []
    for video_id, video_data in results.items():
        if "extracted_content" in video_data:
            for timestamp, text_entry in video_data["extracted_content"].items():
                ocr_text = clean_text(text_entry["ocr_slide_content"])
                if len(ocr_text) >= 100:
                    text_data.append(
                        {
                            "start_time": text_entry["start_time"],
                            "end_time": text_entry["end_time"],
                            "ocr_slide_content": ocr_text,
                            "video_id": video_id,
                        }
                    )

    for slide in slides:
        if slide.get("slideType") != "FRAME":
            continue

        slide_text = slide["slideContent"]
        ocr_slide_contents = [entry["ocr_slide_content"] for entry in text_data]

        best_match = process.extractOne(
            slide_text, ocr_slide_contents, scorer=fuzz.token_set_ratio
        )

        if best_match:
            matched_text, match_score = best_match[0], best_match[1]

            if match_score > 70:
                matched_entry = next(
                    entry
                    for entry in text_data
                    if entry["ocr_slide_content"] == matched_text
                )

                slide["start_time"] = matched_entry["start_time"]
                slide["end_time"] = matched_entry["end_time"]
                slide["video_id"] = matched_entry["video_id"]

    with open(processed_slides_file_path, "w", encoding="utf-8") as output_file:
        json.dump(slides, output_file, indent=4, ensure_ascii=False)

    print(
        f"Slides updated with timestamps and URLs successfully for course {course_id}!"
    )
