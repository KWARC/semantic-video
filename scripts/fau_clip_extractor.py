from datetime import datetime
import os
import json
import re
import requests
from bs4 import BeautifulSoup
from config import COURSE_IDS, FAU_TV_BASE_URL, FAU_TV_COURSE_IDS, OCR_EXTRACTED_FILE_PATH


COURSE_MAP = {
    course_id: FAU_TV_COURSE_IDS.get(course_id)
    for course_id in COURSE_IDS
    if FAU_TV_COURSE_IDS.get(course_id) 
}

all_courses_clips_path = os.path.join(
    OCR_EXTRACTED_FILE_PATH, "all_courses_clips.json"
)


def fetch_clips_details(fau_id):

    course_url = f"{FAU_TV_BASE_URL}/course/id/{fau_id}"
    r = requests.get(course_url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    clips_detail = []

    course_url_name = None  
    for li in soup.select("li[data-tooltip]"):

        clip_info_cells = li.find_all("div", recursive=False)
        date_span = clip_info_cells[4].find("span")  
        recording_date = date_span.get_text(strip=True) if date_span else ""


        form = li.find("form", action=True)
        if not form:
            continue
        lecture_url = form["action"]

        if course_url_name is None:
            course_slug_match = re.search(r"/series/([^/]+)/", lecture_url)
            course_url_name = course_slug_match.group(1) if course_slug_match else None

        clip_page = requests.get(lecture_url).text
        clip_soup = BeautifulSoup(clip_page, "html.parser")
        clip_title_div = clip_soup.find("div", id="clip-title")
        clip_id = None
        if clip_title_div:
            match = re.search(r"ID:(\d+)", clip_title_div.get_text())
            if match:
                clip_id = match.group(1)


        clips_detail.append({
            "recording_date": recording_date,
            "clip_id": clip_id,
            "lecture_url": lecture_url
        })

    return {
        "course_url_name": course_url_name,
        "clips_detail": clips_detail
    }

def main():
    all_data = {}
    for course_id in COURSE_IDS:
        semester_map = FAU_TV_COURSE_IDS.get(course_id, {})
        if not isinstance(semester_map, dict):
            print(f"[WARN] Skipping {course_id}: not semesterized")
            continue

        for semester_label, fau_course_id in semester_map.items():
            if not fau_course_id or fau_course_id in {"_", "not available", "NA"}:
                print(f"Skipping {course_id} ({semester_label}) — Invalid FAU ID.")
                continue

            print(f"Extracting clip from course {course_id} ({semester_label})")

            clips_data = fetch_clips_details(fau_course_id)
            course_url_name = clips_data["course_url_name"]
            clips_detail = clips_data["clips_detail"]

        # save as: all_data["ai-1"]["WS24-25"] = {...}
            all_data.setdefault(course_id, {})[semester_label] = {
                "fau_course_id": fau_course_id,
                "fau_course_url_name":course_url_name,
                "clips": clips_detail
             }

    clips_directory = os.path.dirname(all_courses_clips_path)
    if clips_directory: 
        os.makedirs(clips_directory, exist_ok=True)

    with open(all_courses_clips_path, "w", encoding="utf-8") as output_file:
        json.dump(all_data, output_file, indent=2,ensure_ascii=False)

if __name__ == "__main__":
    main()
