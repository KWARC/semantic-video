import os
import json
import requests
from typing import List, Dict
from dotenv import load_dotenv


import json
from bs4 import BeautifulSoup


def html_to_text(html_content):
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()


def process_slides(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    def process_section(section):
        """
        Processes a section recursively to extract relevant fields from slides.
        """
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

    print(f"Processed data has been saved to {output_file}")



load_dotenv(".env.local")

API_BASE_URL = os.getenv("API_BASE_URL")
DEFAULT_COURSE_ID = os.getenv("DEFAULT_COURSE_ID", "ai-1")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

if not API_BASE_URL:
    raise EnvironmentError("Missing API_BASE_URL environment variable in .env.local.")

def fetch_section_info(course_id: str) -> List[Dict]:
    url = f"{API_BASE_URL}/get-section-info/{course_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def fetch_slides(course_id: str, section_id: str) -> List[Dict]:
    url = f"{API_BASE_URL}/get-slides/{course_id}/{section_id}"
    response = requests.get(url)
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
    sections = fetch_section_info(course_id)
    return {
        "courseId": course_id,
        "sections": [process_section(course_id, section) for section in sections]
    }

def save_to_disk(course_id: str, data: Dict, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{course_id}_slides.json")
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def load_from_disk(course_id: str, output_dir: str) -> Dict:
    file_path = os.path.join(output_dir, f"{course_id}_slides.json")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data for course {course_id} not found locally.")
    with open(file_path, "r") as f:
        return json.load(f)

def main():
    course_id = DEFAULT_COURSE_ID

    try:
        data = load_from_disk(course_id, OUTPUT_DIR)
        print(f"Loaded data for course {course_id} from disk.")
    except FileNotFoundError:
        print(f"Data for course {course_id} not found locally. Fetching from API...")
        data = get_all_slides(course_id)
        save_to_disk(course_id, data, OUTPUT_DIR)
        print(f"Data for course {course_id} saved locally.")
    
    processed_file = os.path.join(OUTPUT_DIR, f"{course_id}_processed_slides.json")
    process_slides(os.path.join(OUTPUT_DIR, f"{course_id}_slides.json"), processed_file)
    print(f"Slides processed and saved to {processed_file}")

if __name__ == "__main__":
    main()
