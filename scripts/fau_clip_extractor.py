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

def fetch_clips(fau_id):
    url = f"{FAU_TV_BASE_URL}/course/id/{fau_id}"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    
    out = []
    for div in soup.select("#clips-list .target"):
        anchors = div.find_all("a", href=True)
        clip_id = None
        for a in anchors:
            match = re.search(r"/clip/id/([a-zA-Z0-9]+)", a["href"])
            if match:
                clip_id = match.group(1)
                break  
            else:
                print("Invalid clip href! ",a["href"])

        if not clip_id:
            continue  
        clip_info_row = div.find("div", recursive=False)
        clip_info_cells = clip_info_row.find_all("div", recursive=False)
        if len(clip_info_cells) >= 5:
            recording_date = clip_info_cells[4].get_text(strip=True)
        else:
            recording_date = ""
        out.append({"clip_id": clip_id, "recording_date": recording_date})

    return out


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

            clips = fetch_clips(fau_course_id)

        # save as: all_data["ai-1"]["WS24-25"] = {...}
            all_data.setdefault(course_id, {})[semester_label] = {
                "fau_course_id": fau_course_id,
                "clips": clips
             }

    clips_directory = os.path.dirname(all_courses_clips_path)
    if clips_directory: 
        os.makedirs(clips_directory, exist_ok=True)

    with open(all_courses_clips_path, "w", encoding="utf-8") as output_file:
        json.dump(all_data, output_file, indent=2,ensure_ascii=False)

if __name__ == "__main__":
    main()
