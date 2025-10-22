from datetime import datetime
import os
import json
import requests
from config import COURSE_IDS, FAU_TV_API_BASE_URL, FAU_TV_COURSE_IDS, OCR_EXTRACTED_FILE_PATH


COURSE_MAP = {
    course_id: FAU_TV_COURSE_IDS.get(course_id)
    for course_id in COURSE_IDS
    if FAU_TV_COURSE_IDS.get(course_id) 
}

all_courses_clips_path = os.path.join(
    OCR_EXTRACTED_FILE_PATH, "all_courses_clips.json"
)



def fetch_clips(fau_id):
    api_url = f"{FAU_TV_API_BASE_URL}/{fau_id}/clips"
    clips_detail = []

    while api_url:
        response = requests.get(api_url)
        response.raise_for_status()
        json_data = response.json()

        for clip in json_data.get("data", []):
            iso_recording_date = clip.get("time_taken") or clip.get("uploaded_date") or ""
            if iso_recording_date:
                try:
                    dt = datetime.fromisoformat(iso_recording_date.replace("Z", "+00:00"))
                    recording_date = dt.strftime("%Y-%m-%d")
                except ValueError:
                    recording_date = iso_recording_date  
            else:
                recording_date = ""

            clips_detail.append({
                "clip_id": clip.get("id"),
                "recording_date": recording_date
            })

        api_url = json_data.get("links", {}).get("next")

    return clips_detail

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
