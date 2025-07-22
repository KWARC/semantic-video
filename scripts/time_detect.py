import os
import json
from collections import defaultdict
from config import COURSE_IDS, SLIDES_OUTPUT_DIR, OCR_EXTRACTED_FILE_PATH, ALL_COURSES_CLIPS_JSON


def compute_time_per_slide_and_section(course_id,semester_key):
    input_file = os.path.join(
        SLIDES_OUTPUT_DIR, f"{course_id}_{semester_key}_updated_extracted_content.json")
    if not os.path.exists(input_file):
        print(f"[WARN] File not found: {input_file}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        content = json.load(f)

    slide_durations = defaultdict(float)
    section_durations = defaultdict(float)
    section_slide_durations = defaultdict(
        lambda: {"duration": 0.0, "slides": defaultdict(float)})

    for clip_id, clip_data in content.items():
        entries = clip_data.get("extracted_content", {})
        for ts, entry in entries.items():
            start = entry.get("start_time")
            end = entry.get("end_time")
            slide = entry.get("slideUri")
            section = entry.get("sectionUri")

            if start is None or end is None:
                continue

            duration = float(end) - float(start)
            entry["duration"] = round(duration, 2)

            slide_durations[slide] += duration
            if section:
                section_durations[section] += duration
                section_slide_durations[section]["duration"] += duration
                section_slide_durations[section]["slides"][slide] += duration

    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2)
    print(f"[INFO] Updated {input_file} with duration fields.")


def main():
    with open(ALL_COURSES_CLIPS_JSON, "r", encoding="utf-8") as f:
        all_data = json.load(f)

    for course_id in COURSE_IDS:
        course_info = all_data.get(course_id, {})
        for semester_key in course_info:
            compute_time_per_slide_and_section(course_id, semester_key)

if __name__ == "__main__":
    main()
