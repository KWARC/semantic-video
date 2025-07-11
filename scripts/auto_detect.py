import json
import os
from config import CURRENT_SEM_JSON,ALL_COURSES_CLIPS_JSON, SLIDES_OUTPUT_DIR
from datetime import datetime, timezone

def load_all_clips():
    with open(ALL_COURSES_CLIPS_JSON, "r") as f:
        return json.load(f)
    
def get_latest_valid_slide(clip_data: dict, min_duration: float = 59.0):
    valid_slides = []
    seen_slide_uris = set()

    sorted_timestamps = sorted(clip_data.keys(), key=lambda x: float(x))

    for ts in sorted_timestamps:
        data = clip_data[ts]

        section_uri = data.get("sectionUri", "")
        slide_uri = data.get("slideUri", "")

        if not section_uri or not slide_uri:
            continue
        if slide_uri in seen_slide_uris:
            continue

        start_time = float(data.get("start_time", ts))
        end_time = float(data.get("end_time", start_time))
        duration = end_time - start_time

        if duration < min_duration:
            continue

        valid_slides.append({
            "sectionUri": section_uri,
            "slideUri": slide_uri,
            "start_time": start_time,
            "end_time": end_time
        })
        seen_slide_uris.add(slide_uri)

    return valid_slides[-1] if valid_slides else None

def check_section_completed(clip_data: dict, current_slide: dict, clip_id: str = None) -> bool:
    current_end_time = current_slide["end_time"]

    sorted_keys = sorted((float(k), k) for k in clip_data.keys())
    for timestamp_float, timestamp_str in sorted_keys:
        if timestamp_float < current_end_time:
            continue

        next_data = clip_data[timestamp_str]

        if any(k in next_data for k in ("sectionId", "sectionUri", "slideUri")):
            print(f"[clipId={clip_id}] Found next slide at {timestamp_str} → sectionCompleted = False")
            return False

    print(f"{clip_id}- True")
    return True

def update_current_sem():
    TIME_WINDOW_MS = 24 * 60 * 60 * 1000  # 24 hours in milliseconds

    with open(CURRENT_SEM_JSON, 'r') as f:
        current_sem = json.load(f)
        print(f"Loaded {len(current_sem)} courses from {CURRENT_SEM_JSON}")

    all_clips = load_all_clips()

    
    clip_timestamp_map = {}
    for course_id, course_clips in all_clips.items():
        timestamps = []
        for clip in course_clips["clips"]:
            recording_dt = datetime.strptime(clip["recording_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            recording_ts = int(recording_dt.timestamp() * 1000)
            timestamps.append((recording_ts, clip["clip_id"]))
        clip_timestamp_map[course_id] = timestamps

    for course_id, course_entries in current_sem.items():
        print(f"\nProcessing course: {course_id}")

        extracted_file_path = os.path.join(SLIDES_OUTPUT_DIR, f"{course_id}_updated_extracted_content.json")
        if not os.path.exists(extracted_file_path):
            print(f"WARNING: Extracted file not found for course {course_id}. Skipping this course.")
            continue

        with open(extracted_file_path, 'r', encoding='utf-8') as ef:
            extracted_content = json.load(ef)

        matched_count = 0
        course_clips = clip_timestamp_map.get(course_id, [])
        if course_id in {"ai-1", "ai-2"}:
            course_clips = course_clips[1:]

        for entry in course_entries:
            raw_ts = entry['timestamp_ms']
            timestamp_ms = raw_ts if raw_ts > 1e12 else raw_ts * 1000
           
            matched_clip_id = None
            closest_diff = TIME_WINDOW_MS + 1

            for recorded_ts, clip_id in course_clips:
                diff = timestamp_ms - recorded_ts

                if 0 <= diff <= TIME_WINDOW_MS:
                    if clip_id in extracted_content and diff < closest_diff:
                        matched_clip_id = clip_id
                        closest_diff = diff

            if not matched_clip_id:
                continue

            clip_data = extracted_content[matched_clip_id]['extracted_content']
            latest_slide = get_latest_valid_slide(clip_data, min_duration=59.0)
            if latest_slide:
                section_completed = check_section_completed(clip_data, latest_slide,matched_clip_id)
                print({section_completed})
                entry['autoDetected'] = {
                    "clipId": matched_clip_id,
                    "sectionUri": latest_slide["sectionUri"],
                    "slideUri": latest_slide["slideUri"],
                    "sectionCompleted": section_completed
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
