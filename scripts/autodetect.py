import json
import os
from config import CURRENT_SEM_JSON,ALL_COURSES_CLIPS_JSON, SLIDES_OUTPUT_DIR
from datetime import datetime

def load_all_clips():
    with open(ALL_COURSES_CLIPS_JSON, "r") as f:
        return json.load(f)

def update_current_sem():
    EXTRACTED_CONTENT_DIR = SLIDES_OUTPUT_DIR
    TIME_WINDOW_MS = 12 * 60 * 60 * 1000  # 12 hours in milliseconds

    with open(CURRENT_SEM_JSON, 'r') as f:
        current_sem = json.load(f)
        print(f"Loaded {len(current_sem)} courses from {CURRENT_SEM_JSON}")

    all_clips = load_all_clips()

    
    clip_timestamp_map = {}
    for course_id, course_clips in all_clips.items():
        timestamps = []
        for clip in course_clips["clips"]:
            recording_dt = datetime.strptime(clip["recording_date"], "%Y-%m-%d")
            recording_ts = int(recording_dt.timestamp() * 1000)
            timestamps.append((recording_ts, clip["clip_id"]))
        clip_timestamp_map[course_id] = timestamps

    for course_id, course_entries in current_sem.items():
        print(f"\nProcessing course: {course_id}")

        extracted_file_path = os.path.join(EXTRACTED_CONTENT_DIR, f"{course_id}_updated_extracted_content.json")
        if not os.path.exists(extracted_file_path):
            print(f"WARNING: Extracted file not found for course {course_id}. Skipping this course.")
            continue

        with open(extracted_file_path, 'r', encoding='utf-8') as ef:
            extracted_content = json.load(ef)

        matched_count = 0
        course_clips = clip_timestamp_map.get(course_id, [])

        for entry in course_entries:
            raw_ts = entry['timestamp_ms']
            timestamp_ms = raw_ts if raw_ts > 1e12 else raw_ts * 1000
           
            matched_clip_id = None
            closest_diff = TIME_WINDOW_MS + 1

            for recorded_ts, clip_id in course_clips:
                diff = abs(recorded_ts - timestamp_ms)
                if diff <= TIME_WINDOW_MS and diff < closest_diff:
                    if clip_id in extracted_content:
                        matched_clip_id = clip_id
                        closest_diff = diff

            if not matched_clip_id:
                continue

            clip_data = extracted_content[matched_clip_id]['extracted_content']
            last_valid_sectionUri = ""
            last_valid_slideUri = ""
          
            for ts in sorted(clip_data.keys(), key=lambda x: float(x)):
                sectionUri = clip_data[ts].get('sectionUri', '')
                slideUri = clip_data[ts].get('slideUri', '')
                if sectionUri:
                    last_valid_sectionUri = sectionUri
                    last_valid_slideUri = slideUri

            entry['autoDetected'] = {
                "clipId": matched_clip_id,
                "sectionUri": last_valid_sectionUri,
                "slideUri": last_valid_slideUri
            }

            matched_count += 1

        print(f"Updated {matched_count}/{len(course_entries)} entries for {course_id}")

    with open(CURRENT_SEM_JSON, 'w', encoding='utf-8') as f:
        json.dump(current_sem, f, indent=2)

    print(f"\n{CURRENT_SEM_JSON} successfully updated!")

def main():
    update_current_sem()

if __name__ == "__main__":
    main()
