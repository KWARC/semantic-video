import json
import os
from dotenv import load_dotenv
from rapidfuzz import fuzz, process

load_dotenv(".env.local")

slides_file_path = os.getenv("SLIDES_FILE_PATH")
results_file_path = os.getenv("RESULTS_FILE_PATH")
output_file_path = os.getenv("OUTPUT_FILE_PATH")

if not all([slides_file_path, results_file_path, output_file_path]):
    raise EnvironmentError("Missing required environment variables. Check .env.local.")

with open(slides_file_path, "r", encoding="utf-8") as slides_file:
    slides = json.load(slides_file)

with open(results_file_path, "r", encoding="utf-8") as results_file:
    results = json.load(results_file)

text_data = []
for video_id, video_info in results.items():
    url = video_info["url"]
    for key, text_entry in video_info["extracted_text"].items():
        text_data.append(
            {
                "start_time": text_entry["start_time"],
                "end_time": text_entry["end_time"],
                "text_value": text_entry["text_value"],
                "url": url,
            }
        )

for slide in slides:
    slide_text = slide["slideContent"]

    text_values = [entry["text_value"] for entry in text_data]

    best_match = process.extractOne(
        slide_text, text_values, scorer=fuzz.token_set_ratio
    )

    if best_match:
        matched_text, match_score = best_match[0], best_match[1]

        if match_score > 50:
            matched_entry = next(
                entry for entry in text_data if entry["text_value"] == matched_text
            )

            slide["start_time"] = matched_entry["start_time"]
            slide["end_time"] = matched_entry["end_time"]
            slide["url"] = matched_entry["url"]

with open(output_file_path, "w", encoding="utf-8") as output_file:
    json.dump(slides, output_file, indent=4, ensure_ascii=False)

print("Slides updated with timestamps and URLs successfully!")
