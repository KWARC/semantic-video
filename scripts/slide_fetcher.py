import os
import json
import requests
import re
from typing import List, Dict
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from config import (
    COURSE_API_BASE_URL,
    COURSE_IDS,
    SLIDES_OUTPUT_DIR,
    SLIDES_EXPIRY_DAYS,
    COURSE_IDS,
)


def fetch_section_info(course_id: str) -> List[Dict]:
    url = f"{COURSE_API_BASE_URL}/get-section-info/{course_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_slides(course_id: str, section_id: str) -> List[Dict]:
    url = f"{COURSE_API_BASE_URL}/get-slides/{course_id}/{section_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get(section_id, [])


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    return text


def remove_last_line_if_frame(slide_content: str) -> str:
    lines = slide_content.strip().split("\n")

    if lines and (
        re.search(r"\d{4}-\d{2}-\d{2}", lines[-1])
        or re.search(r"Michael\s*Kohlhase", lines[-1])
    ):
        lines = lines[:-1]

    return "\n".join(lines)


def process_section(
    course_id: str, section: Dict, slide_index_tracker: Dict[str, int]
) -> List[Dict]:
    """Processes a section recursively to assign slide indices and extract relevant fields."""
    slides = fetch_slides(course_id, section["id"])

    if section["id"] not in slide_index_tracker:
        slide_index_tracker[section["id"]] = 0

    processed_slides = []
    for slide in slides:
        slide_index_tracker[section["id"]] += 1
        raw_slide_content = html_to_text(slide.get("slideContent", ""))

        if slide.get("slideType", "") == "FRAME":
            cleaned_slide_content = remove_last_line_if_frame(raw_slide_content)
        cleaned_slide_content = clean_text(raw_slide_content)

        processed_slides.append(
            {
                "sectionId": section["id"],
                "slideIndex": slide_index_tracker[section["id"]],
                "slideContent": cleaned_slide_content,
                "slideType": slide.get("slideType", ""),
                "title": section.get("title", ""),
                "archive": slide.get("archive", ""),
                "filepath": slide.get("filepath", ""),
            }
        )

    for child_section in section.get("children", []):
        processed_slides.extend(
            process_section(course_id, child_section, slide_index_tracker)
        )

    return processed_slides


def get_all_slides(course_id: str) -> Dict:
    sections = fetch_section_info(course_id)
    return {
        "courseId": course_id,
        "sections": sections,
    }


def save_to_disk(file_path: str, data: Dict):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


def load_from_disk(file_path: str) -> Dict:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found.")
    with open(file_path, "r") as f:
        return json.load(f)


def html_to_text(html_content):
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()


def process_slides(input_file: str, output_file: str):
    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    slide_index_tracker = {section["id"]: 0 for section in data.get("sections", [])}

    processed_data = []
    for section in data.get("sections", []):
        processed_data.extend(
            process_section(data["courseId"], section, slide_index_tracker)
        )

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(processed_data, file, ensure_ascii=False, indent=4)

    print(f"Processed slides have been saved to {output_file}")


def is_cache_valid(file_path: str) -> bool:
    if not os.path.exists(file_path):
        return False
    file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    return datetime.now() - file_mod_time < timedelta(days=SLIDES_EXPIRY_DAYS)


def main():
    for course_id in COURSE_IDS:
        original_slides_file = os.path.join(
            SLIDES_OUTPUT_DIR, f"{course_id}_slides.json"
        )
        processed_slides_file = os.path.join(
            SLIDES_OUTPUT_DIR, f"{course_id}_processed_slides.json"
        )

        if is_cache_valid(original_slides_file):
            try:
                data = load_from_disk(original_slides_file)
                print(f"Loaded original slides for course {course_id} from disk.")
            except FileNotFoundError:
                print(
                    f"Original slides for course {course_id} not found locally. Fetching from API..."
                )
                data = get_all_slides(course_id)
                save_to_disk(original_slides_file, data)
                print(
                    f"Original slides for course {course_id} saved locally at {original_slides_file}."
                )
        else:
            print(
                f"Cache expired or original slides for course {course_id} not found locally. Fetching from API..."
            )
            data = get_all_slides(course_id)
            save_to_disk(original_slides_file, data)
            print(
                f"Original slides for course {course_id} saved locally at {original_slides_file}."
            )

        print(f"Processing slides for course {course_id} to clean and simplify data...")
        process_slides(original_slides_file, processed_slides_file)
        print(
            f"Processed slides for course {course_id} saved at {processed_slides_file}."
        )


if __name__ == "__main__":
    main()
