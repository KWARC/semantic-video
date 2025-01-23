import json
from rapidfuzz import fuzz, process


with open("data/slides/processed_ai-1_slides.json", "r", encoding="utf-8") as slides_file:
    slides = json.load(slides_file)

with open("data/Results.json", "r", encoding="utf-8") as results_file:
    results = json.load(results_file)

text_data = []
for result in results:
    video_name = result["video_name"]
    for key, text_entry in result["text_data"].items():
        start_time = text_entry["start_time"] + 1
        text_data.append({
            "video_name": video_name,
            "start_time": start_time,
            "end_time": text_entry["end_time"],
            "text_value": text_entry["text_value"]
        })

for slide in slides:
    slide_text = slide["slideContent"]

    text_values = [entry["text_value"] for entry in text_data]

    best_match = process.extractOne(
        slide_text,
        text_values,
        scorer=fuzz.token_set_ratio
    )

    if best_match:
        matched_text, match_score = best_match[0], best_match[1]

        if match_score > 50:  # Adjust the threshold as needed
            matched_entry = next(
                entry for entry in text_data if entry["text_value"] == matched_text
            )

            slide["video_name"] = matched_entry["video_name"]
            slide["start_time"] = matched_entry["start_time"]
            slide["end_time"] = matched_entry["end_time"]

with open("data/slides/processed_ai-1_slides.json", "w", encoding="utf-8") as slides_file:
    json.dump(slides, slides_file, indent=4, ensure_ascii=False)

print("Slides updated with timestamps successfully!")
