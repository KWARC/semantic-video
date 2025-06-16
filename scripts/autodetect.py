import json
import os

from config import CURRENT_SEM_JSON


# CURRENT_SEM_FILE = os.getenv("CURRENT_SEM_JSON", "current-sem.json")
EXTRACTED_CONTENT_DIR = "data/slides"  

# Load current-sem.json
with open(CURRENT_SEM_JSON, 'r') as f:
    current_sem = json.load(f)
    print(f"Loaded {len(current_sem)} courses from {CURRENT_SEM_JSON}")

# Loop through all courses inside current-sem.json
for course_id, course_entries in current_sem.items():
    print(f"Processing course: {course_id}")

    
    extracted_file_path = os.path.join(EXTRACTED_CONTENT_DIR, f"{course_id}_updated_extracted_content.json")

    if not os.path.exists(extracted_file_path):
        print(f"WARNING: Extracted file not found for course {course_id}. Skipping this course.")
        continue

    with open(extracted_file_path, 'r', encoding='utf-8') as ef:
        extracted_content = json.load(ef)

    for entry in course_entries:
        clip_id = entry['clipId']
        timestamp_ms = entry['timestamp_ms']

        
        last_valid_sectionUri = ""
        last_valid_slideUri = ""

        # Try to find matched section/slide info for this clipId
        if clip_id in extracted_content:
            clip_data = extracted_content[clip_id]['extracted_content']
            for timestamp in sorted(clip_data.keys(), key=lambda x: float(x)):
                sectionUri = clip_data[timestamp].get('sectionUri', '')
                slideUri = clip_data[timestamp].get('slideUri', '')
                if sectionUri:
                    last_valid_sectionUri = sectionUri
                    last_valid_slideUri = slideUri

        # Directly update the entry with autoDetected
        entry['autoDetected'] = {
            "clipId": clip_id,
            "sectionUri": last_valid_sectionUri,
            "slideUri": last_valid_slideUri
        }


with open(CURRENT_SEM_JSON, 'w', encoding='utf-8') as f:
    json.dump(current_sem, f, indent=2)

print(f"{CURRENT_SEM_JSON} successfully updated!")
