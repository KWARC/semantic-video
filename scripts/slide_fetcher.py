import os
import json
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from config import COURSE_API_BASE_URL, COURSE_ID, SLIDES_OUTPUT_DIR, SLIDES_EXPIRY_DAYS


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


def process_section(course_id: str, section: Dict) -> Dict:
    """Processes a section to include only FRAME-type slides."""
    slides = fetch_slides(course_id, section["id"])
    frame_slides = [slide for slide in slides if slide["slideType"] == "FRAME"]

    children = [
        process_section(course_id, child) for child in section.get("children", [])
    ]

    return {"sectionId": section["id"], "slides": frame_slides, "children": children}


def get_all_slides(course_id: str) -> Dict:
    sections = fetch_section_info(course_id)
    return {
        "courseId": course_id,
        "sections": [process_section(course_id, section) for section in sections],
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
    """Processes slides by cleaning fields and converting HTML to text."""
    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    def process_section(section):
        """Processes a section recursively to extract relevant fields from slides."""
        processed_slides = []
        if "slides" in section:
            for slide in section["slides"]:
                processed_slides.append(
                    {
                        "slideContent": html_to_text(slide.get("slideContent", "")),
                        "sectionId": slide.get("sectionId", ""),
                        "archive": slide.get("archive", ""),
                        "filepath": slide.get("filepath", ""),
                    }
                )
        # Recursively process children
        if "children" in section:
            for child in section["children"]:
                processed_slides.extend(process_section(child))
        return processed_slides

    processed_data = []
    for section in data.get("sections", []):
        processed_data.extend(process_section(section))

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(processed_data, file, ensure_ascii=False, indent=4)

    print(f"Processed slides have been saved to {output_file}")


def is_cache_valid(file_path: str) -> bool:
    if not os.path.exists(file_path):
        return False
    file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    return datetime.now() - file_mod_time < timedelta(days=SLIDES_EXPIRY_DAYS)


def main():
    course_id = COURSE_ID

    original_slides_file = os.path.join(SLIDES_OUTPUT_DIR, f"{course_id}_slides.json")
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

    print("Processing slides to clean and simplify data...")
    process_slides(original_slides_file, processed_slides_file)
    print(f"Processed slides saved at {processed_slides_file}.")


if __name__ == "__main__":
    main()
