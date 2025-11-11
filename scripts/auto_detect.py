import json
import os
from config import CURRENT_SEM_JSON,ALL_COURSES_CLIPS_JSON, SLIDES_OUTPUT_DIR
from datetime import datetime, timezone

def load_all_clips():
    with open(ALL_COURSES_CLIPS_JSON, "r") as f:
        return json.load(f)

def update_current_sem():
    TIME_WINDOW_MS = 24 * 60 * 60 * 1000  # 24 hours in milliseconds

    with open(CURRENT_SEM_JSON, 'r') as f:
        current_sem = json.load(f)
        print(f"Loaded {len(current_sem)} courses from {CURRENT_SEM_JSON}")

    all_clips = load_all_clips()

    
    clip_timestamp_map = {}
    for course_id, semester_map in all_clips.items():
        timestamps = []
        for semester_label, course_clips in semester_map.items():
            for clip in course_clips.get("clips", []):
                recording_date_str = clip.get("recording_date")
                if not recording_date_str:
                    print(f"Skipping clip {clip.get('clip_id', 'unknown')} (no recording_date) in {course_id}")
                    continue
                try:
                    recording_dt = datetime.strptime(recording_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    print(f"Skipping clip {clip.get('clip_id', 'unknown')} (invalid date: {recording_date_str}) in {course_id}")
                    continue
                recording_ts = int(recording_dt.timestamp() * 1000)
                timestamps.append((recording_ts, clip["clip_id"]))
        clip_timestamp_map[course_id] = timestamps

    for course_id, course_entries in current_sem.items():
        print(f"\nProcessing course: {course_id}")

        if course_id not in all_clips:
            print(f"Skipping {course_id}, not found in all_clips.")
            continue

        for semester_key in all_clips[course_id]:
            print(f"  Semester: {semester_key}")

            extracted_file_path = os.path.join(
                SLIDES_OUTPUT_DIR,
                f"{course_id}_{semester_key}_updated_extracted_content.json"
             )

            if not os.path.exists(extracted_file_path):
                print(f"  WARNING: {extracted_file_path} not found. Skipping.")
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
                nearest_diff = float("inf")
                nearest_clip_id = None
                nearest_signed_diff = None
                for recorded_ts, clip_id in course_clips:
                    diff = timestamp_ms - recorded_ts
                    abs_diff = abs(diff)
                    if abs_diff < nearest_diff:
                            nearest_diff = abs_diff
                            nearest_clip_id = clip_id
                            nearest_signed_diff=diff

                    if 0 <= diff <= TIME_WINDOW_MS:
                        print("        ✅ Within 24h window! Clip Id:",clip_id)
                        if str(clip_id) in extracted_content and diff < closest_diff:
                            matched_clip_id = str(clip_id)
                            closest_diff = diff

                if matched_clip_id:
                    print(f"✅ Matched clip {matched_clip_id} (Δ={closest_diff / (1000*60*60):.2f}h)")
                else:
                    direction = "after" if nearest_signed_diff > 0 else "before"
                    print(f"❌ No match (closest clip={nearest_clip_id}, Δ={nearest_diff / (1000*60*60):.2f}h {direction})")                
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
