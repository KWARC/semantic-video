import os
import json
import requests
import re
from typing import Any, List, Dict, TypedDict
from urllib.parse import quote
from config import OCR_EXTRACTED_FILE_PATH
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from config import (
    COURSE_API_BASE_URL,
    COURSE_IDS,
    NEXT_PUBLIC_FLAMS_URL,
    SLIDES_OUTPUT_DIR,
    SLIDES_EXPIRY_DAYS,
    COURSE_IDS,
    ALL_COURSES_CLIPS_JSON
)

COURSE_NOTES_URIS: Dict[str, str] = {}

def fetch_slides(course_id: str, section_id: str) -> List[Dict]:
    encoded_section_id = quote(section_id, safe='')
    url = f"{COURSE_API_BASE_URL}/get-slides?courseId={course_id}&sectionIds={encoded_section_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get(section_id, {}).get("slides", [])

def fetch_toc(course_id:str)->List[Dict]:
    notes_uri=COURSE_NOTES_URIS.get(course_id)
    encoded_uri = quote(notes_uri, safe='')
    url = f"{NEXT_PUBLIC_FLAMS_URL}/content/toc?uri={encoded_uri}"
    response = requests.get(url)
    response.raise_for_status()
    toc_response = response.json()
    if isinstance(toc_response, list) and len(toc_response) > 1:
        return toc_response[1]
    else:
        raise ValueError("Unexpected TOC format from API")
class SectionSlides(TypedDict):
    section_uri: str
    slides: List[Dict]
    
def get_frame_slides_by_section(toc_elems: List[Dict], course_id: str) -> Dict[str, SectionSlides]:
    by_section = {}
    for elem in toc_elems:
        if elem.get("type") == "Section":
            sec_id = elem["id"]
            sec_uri = elem.get("uri", "")
            sec_title=elem.get("title","")
            slide_elements = fetch_slides(course_id,sec_id)
            frame_slides = []
            for slide in slide_elements:
                if not isinstance(slide, dict):
                    print(f"[Warning] Skipping non-dict slide in section {sec_id}: {slide}")
                    continue
                if slide.get("slideType") == "FRAME" and "slide" in slide:
                    frame_slides.append(slide["slide"])

            by_section[sec_id] = {
                "section_uri": sec_uri,
                "section_title":sec_title,
                "slides": frame_slides
            }
        if "children" in elem and isinstance(elem["children"], list):
            child_sections = get_frame_slides_by_section(elem["children"], course_id)
            by_section.update(child_sections)
    return by_section

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


def get_all_slides(course_id: str) -> Dict:
    toc_data=fetch_toc(course_id)
    frame_slides_by_section = get_frame_slides_by_section(toc_data,course_id)
    return {
        "courseId": course_id,
        "sections": frame_slides_by_section,
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

def process_section(section_id: str,section_uri:str,section_title:str, slides: List[Dict]) -> List[Dict]:
    processed_slides = []
    for slide in slides:
        raw_slide_content = html_to_text(slide.get("html", ""))
        raw_slide_content = remove_last_line_if_frame(raw_slide_content)
        cleaned_slide_content = clean_text(raw_slide_content)
        processed_slides.append({
            "sectionId": section_id,
            "sectionUri":section_uri,
            "sectionTitle":section_title,
            "slideUri": slide.get("uri", ""),
            "slideContent": cleaned_slide_content,
            "html": slide.get("html", ""),
        })
    return processed_slides

def process_slides(input_file: str, output_file: str):
    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)
    slides_by_section = data.get("sections", {})
    processed_data = []
    for section_id, section_info in slides_by_section.items():
        section_uri = section_info.get("section_uri", "")
        section_title=section_info.get("section_title","")
        slides = section_info.get("slides", [])
        processed_data.extend(process_section(section_id,section_uri,section_title,slides))
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(processed_data, file, ensure_ascii=False, indent=4)

    print(f"Processed slides have been saved to {output_file}")


def is_cache_valid(file_path: str) -> bool:
    if not os.path.exists(file_path):
        return False
    file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    return datetime.now() - file_mod_time < timedelta(days=SLIDES_EXPIRY_DAYS)

def parse_course_notes_uris(raw_data: List[Any]) -> Dict[str, str]:
    course_notes_uris: Dict[str, str] = {}

    for section in raw_data:
        if isinstance(section, list):
            for item in section:
                if isinstance(item, dict) and item.get("type") == "course":
                    acronym = item.get("acronym", "").lower()
                    notes_uri = item.get("notes", "")
                    if acronym and notes_uri:
                        course_notes_uris[acronym] = notes_uri
    return course_notes_uris

def get_course_notes_uris() -> Dict[str, str]:
    url = f"{NEXT_PUBLIC_FLAMS_URL}/api/index"
    try:
        response = requests.post(url)
        response.raise_for_status()
        data = response.json()
        return parse_course_notes_uris(data)
    except Exception as e:
        print(f"Failed to fetch course notes URIs: {e}")
        return {}

def main():
    global COURSE_NOTES_URIS
    COURSE_NOTES_URIS = get_course_notes_uris()
    with open(ALL_COURSES_CLIPS_JSON, "r", encoding="utf-8") as f:
        all_data = json.load(f)


    for course_id in COURSE_IDS:
        course_info = all_data.get(course_id, {})
        for semester_key in course_info:
            original_slides_file = os.path.join(
            SLIDES_OUTPUT_DIR, f"{course_id}_{semester_key}_slides.json"
        )
        processed_slides_file = os.path.join(
            SLIDES_OUTPUT_DIR, f"{course_id}_{semester_key}_processed_slides.json"
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
