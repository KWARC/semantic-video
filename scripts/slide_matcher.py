import json
import os
import re
from rapidfuzz import fuzz, process
from config import OCR_EXTRACTED_FILE_PATH, SLIDES_OUTPUT_DIR, COURSE_IDS, ALL_COURSES_CLIPS_JSON


def clean_text(text: str) -> str:
    text = re.sub(r"[\u201c\u201d\u2022\u00bb\u2014\u2013]", "", text)
    text = re.sub(r"\s+", " ", text.strip())
    return text


def match_and_update_extracted_content(course_id,semester_key):
    processed_slides_file_path = os.path.join(
        SLIDES_OUTPUT_DIR, f"{course_id}_processed_slides.json"
    )
    ocr_extracted_file_path = os.path.join(
        OCR_EXTRACTED_FILE_PATH, f"{course_id}_{semester_key}_extracted_content.json"
    )
    updated_extracted_file_path = os.path.join(
        SLIDES_OUTPUT_DIR, f"{course_id}_{semester_key}_updated_extracted_content.json"
    )

    if not os.path.exists(processed_slides_file_path):
        print(f"Processed slides file not found: {processed_slides_file_path}")
        return

    if not os.path.exists(ocr_extracted_file_path):
        print(f"OCR extracted file not found: {ocr_extracted_file_path}")
        return

    with open(processed_slides_file_path, "r", encoding="utf-8") as slides_file:
        all_slides = json.load(slides_file)

    with open(ocr_extracted_file_path, "r", encoding="utf-8") as results_file:
        results = json.load(results_file)

    for slide in all_slides:
        slide["cleaned_slide_content"] = clean_text(slide.get("slideContent", ""))

    for video_id, video_data in results.items():
        if "extracted_content" in video_data:
            for timestamp, text_entry in video_data["extracted_content"].items():
                ocr_text = clean_text(text_entry.get("ocr_slide_content", ""))

                if len(ocr_text) >= 100:
                    text_entry["sectionId"] = ""
                    text_entry["sectionUri"] = ""
                    text_entry["sectionTitle"] = ""
                    text_entry["slideUri"] =""
                    text_entry["slideContent"] = ""
                    text_entry["slideHtml"] = ""

                    best_match = process.extractOne(
                        ocr_text,
                        [slide["cleaned_slide_content"] for slide in all_slides],
                        scorer=fuzz.token_set_ratio,
                    )

                    if best_match and best_match[1] > 70:
                        matched_slide = next(
                            slide
                            for slide in all_slides
                            if slide["cleaned_slide_content"] == best_match[0]
                        )

                        text_entry["sectionId"] = matched_slide["sectionId"]
                        text_entry["sectionUri"] = matched_slide["sectionUri"]
                        text_entry["sectionTitle"] = matched_slide["sectionTitle"]
                        text_entry["slideUri"] = matched_slide["slideUri"]
                        text_entry["slideContent"] = matched_slide["slideContent"]
                        text_entry["slideHtml"] = matched_slide["html"]

    with open(updated_extracted_file_path, "w", encoding="utf-8") as output_file:
        json.dump(results, output_file, indent=4, ensure_ascii=False)

    print(
        f"Slides updated and saved to {updated_extracted_file_path} for course {course_id}!"
    )


def main():
    with open(ALL_COURSES_CLIPS_JSON, "r", encoding="utf-8") as f:
        all_data = json.load(f)

    for course_id in COURSE_IDS:
        course_info = all_data.get(course_id, {})
        for semester_key in course_info:
            match_and_update_extracted_content(course_id, semester_key)


if __name__ == "__main__":
    main()
