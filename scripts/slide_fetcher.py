import os
import json
import requests
from typing import List, Dict

def fetch_section_info(course_id: str) -> List[Dict]:
    """Fetches section info for a given course ID."""
    response = requests.get(f"https://courses.voll-ki.fau.de/api/get-section-info/{course_id}")
    response.raise_for_status()
    return response.json()

def fetch_slides(course_id: str, section_id: str) -> List[Dict]:
    """Fetches slides for a given section ID."""
    response = requests.get(f"https://courses.voll-ki.fau.de/api/get-slides/{course_id}/{section_id}")
    response.raise_for_status()
    return response.json().get(section_id, [])

def process_section(course_id: str, section: Dict) -> Dict:
    """Processes a section to include only FRAME-type slides."""
    slides = fetch_slides(course_id, section["id"])
    frame_slides = [
        slide for slide in slides if slide["slideType"] == "FRAME"
    ]

    children = [
        process_section(course_id, child) for child in section.get("children", [])
    ]

    return {
        "sectionId": section["id"],
        "slides": frame_slides,
        "children": children
    }

def get_all_slides(course_id: str) -> Dict:
    """Fetches and processes all slides for a course."""
    sections = fetch_section_info(course_id)
    return {
        "courseId": course_id,
        "sections": [process_section(course_id, section) for section in sections]
    }

def save_to_disk(course_id: str, data: Dict, output_dir: str = "course_data"):
    """Saves course data to a JSON file on disk."""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{course_id}_slides.json")
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def load_from_disk(course_id: str, output_dir: str = "course_data") -> Dict:
    """Loads course data from a JSON file on disk."""
    file_path = os.path.join(output_dir, f"{course_id}_slides.json")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data for course {course_id} not found locally.")
    with open(file_path, "r") as f:
        return json.load(f)

def main():
    course_id = "ai-1"

    try:
        data = load_from_disk(course_id)
        print(f"Loaded data for course {course_id} from disk.")
    except FileNotFoundError:
        print(f"Data for course {course_id} not found locally. Fetching from API...")
        data = get_all_slides(course_id)
        save_to_disk(course_id, data)
        print(f"Data for course {course_id} saved locally.")
        

if __name__ == "__main__":
    main()
