import os
import json
from collections import defaultdict
from config import COURSE_IDS, SLIDES_OUTPUT_DIR

def compute_time_per_slide_and_section(course_id):
    input_file = os.path.join(SLIDES_OUTPUT_DIR, f"{course_id}_updated_extracted_content.json")
    if not os.path.exists(input_file):
        print(f"[WARN] File not found: {input_file}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        content = json.load(f)

    slide_durations = defaultdict(float)
    section_durations = defaultdict(float)

    for clip_id, clip_data in content.items():
        entries = clip_data.get("extracted_content", {})
        for ts, entry in entries.items():
            start = entry.get("start_time")
            end = entry.get("end_time")
            slide = entry.get("slideUri")
            section = entry.get("sectionUri")

            if start is None or end is None or not slide:
                continue

            duration = float(end) - float(start)
            slide_durations[slide] += duration
            if section:
                section_durations[section] += duration

    print(f"\n== Time per Slide for course {course_id} ==")
    for slide, total_time in sorted(slide_durations.items(), key=lambda x: -x[1]):
        print(f"{slide}: {total_time:.2f} seconds")

    print(f"\n== Time per Section for course {course_id} ==")
    for section, total_time in sorted(section_durations.items(), key=lambda x: -x[1]):
        print(f"{section}: {total_time:.2f} seconds")

def main():
    for course_id in COURSE_IDS:
        compute_time_per_slide_and_section(course_id)

if __name__ == "__main__":
    main()

