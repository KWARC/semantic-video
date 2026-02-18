import json
import os
import re
import unicodedata
from typing import Optional, Tuple

from rapidfuzz import fuzz, process
from config import (
    OCR_EXTRACTED_FILE_PATH,
    SLIDES_OUTPUT_DIR,
    COURSE_IDS,
    ALL_COURSES_CLIPS_JSON,
)


def _int_env(name: str, default: int) -> int:
    val = os.getenv(name)
    return int(val) if val and val.isdigit() else default


def _get_match_config() -> dict:
    return {
        "min_ocr_length": _int_env("MATCH_MIN_OCR_LENGTH", 50),
        "low_confidence_threshold": _int_env("MATCH_LOW_THRESHOLD", 55),
        "short_slide_threshold": _int_env("MATCH_SHORT_SLIDE_THRESHOLD", 85),
        "sequential_search_window": _int_env("MATCH_SEQUENTIAL_WINDOW", 15),
        "sequential_boost": _int_env("MATCH_SEQUENTIAL_BOOST", 5),
    }


def clean_text(text: str) -> str:
    text = re.sub(r"[\u201c\u201d\u2022\u00bb\u2014\u2013]", "", text)
    text = re.sub(r"\s+", " ", text.strip())
    return text


def normalize_ocr_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}", "", text)
    text = re.sub(r"\d{2}[./\-]\d{2}[./\-]\d{2,4}", "", text)
    text = re.sub(r"^\d+\s*[.)]\s*", "", text)
    text = re.sub(r"\s*\d+\s*$", "", text)
    text = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219]", " ", text)
    text = re.sub(r"[\u2014\u2013\u2212]", "-", text)
    text = re.sub(r"\s+", " ", text.strip())
    return text


def prepare_for_matching(text: str) -> str:
    return normalize_ocr_text(clean_text(text))


def compute_ensemble_score(ocr_text: str, slide_text: str) -> float:
    if not slide_text:
        return 0.0
    scores = [
        fuzz.token_set_ratio(ocr_text, slide_text),
        fuzz.token_sort_ratio(ocr_text, slide_text),
        fuzz.partial_ratio(ocr_text, slide_text),
        fuzz.ratio(ocr_text, slide_text),
    ]
    weights = [0.35, 0.25, 0.30, 0.10]
    return sum(s * w for s, w in zip(scores, weights))


def find_best_match(
    ocr_text: str,
    all_slides: list,
    slide_texts: list,
    last_matched_index: Optional[int],
    config: dict,
) -> Tuple[Optional[dict], float, Optional[int]]:
    if not ocr_text or not all_slides:
        return None, 0.0, None

    is_short = len(ocr_text) < 100
    threshold = (
        config["short_slide_threshold"]
        if is_short
        else config["low_confidence_threshold"]
    )

    pre_limit = min(20, len(all_slides))
    try:
        extracted = process.extract(
            ocr_text,
            slide_texts,
            scorer=fuzz.token_set_ratio,
            limit=pre_limit,
        )
    except Exception:
        extracted = [(t, 0, i) for i, t in enumerate(slide_texts)][:pre_limit]

    candidate_indices = set()
    for item in extracted:
        idx = item[2] if len(item) >= 3 else None
        if isinstance(idx, int) and 0 <= idx < len(all_slides):
            candidate_indices.add(idx)

    if last_matched_index is not None:
        window = config["sequential_search_window"]
        for i in range(
            max(0, last_matched_index - window),
            min(len(all_slides), last_matched_index + window + 1),
        ):
            candidate_indices.add(i)

    best_slide = None
    best_score = 0.0
    best_index = None

    for idx in sorted(candidate_indices):
        slide = all_slides[idx]
        slide_text = slide.get("cleaned_slide_content", "")
        if not slide_text:
            continue
        score = compute_ensemble_score(ocr_text, slide_text)
        if last_matched_index is not None:
            if abs(idx - last_matched_index) <= config["sequential_search_window"]:
                score += config["sequential_boost"]
        if score > best_score:
            best_score = score
            best_slide = slide
            best_index = idx

    if best_score < threshold:
        return None, best_score, None

    if is_short and best_score < config["short_slide_threshold"]:
        return None, best_score, None

    return best_slide, best_score, best_index


def match_and_update_extracted_content(course_id: str, semester_key: str):
    print(f"Matching slides for course: {course_id}, semester: {semester_key}")
    processed_slides_file_path = os.path.join(
        SLIDES_OUTPUT_DIR, f"{course_id}_processed_slides.json"
    )
    ocr_extracted_file_path = os.path.join(
        OCR_EXTRACTED_FILE_PATH, f"{course_id}_{semester_key}_extracted_content.json"
    )
    updated_extracted_file_path = os.path.join(
        SLIDES_OUTPUT_DIR, f"{course_id}_{semester_key}_updated_extracted_content.json"
    )

    if not os.path.exists(processed_slides_file_path):
        print(f"Processed slides file not found: {processed_slides_file_path}")
        return

    if not os.path.exists(ocr_extracted_file_path):
        print(f"OCR extracted file not found: {ocr_extracted_file_path}")
        return

    with open(processed_slides_file_path, "r", encoding="utf-8") as slides_file:
        all_slides = json.load(slides_file)

    with open(ocr_extracted_file_path, "r", encoding="utf-8") as results_file:
        results = json.load(results_file)

    for slide in all_slides:
        raw = slide.get("slideContent", "")
        slide["cleaned_slide_content"] = prepare_for_matching(raw)
    slide_texts = [s.get("cleaned_slide_content", "") for s in all_slides]

    config = _get_match_config()
    total_candidates = 0
    total_matched = 0

    videos = [k for k, v in results.items() if "extracted_content" in v]
    for vi, video_id in enumerate(videos):
        video_data = results[video_id]
        print(f"  Processing video {vi + 1}/{len(videos)}: {video_id}...", flush=True)

        entries = sorted(
            video_data["extracted_content"].items(),
            key=lambda x: float(x[0]),
        )
        last_matched_index = None

        for timestamp, text_entry in entries:
            ocr_text = prepare_for_matching(text_entry.get("ocr_slide_content", ""))

            if len(ocr_text) < config["min_ocr_length"]:
                continue

            total_candidates += 1
            text_entry["sectionId"] = ""
            text_entry["sectionUri"] = ""
            text_entry["sectionTitle"] = ""
            text_entry["slideUri"] = ""
            text_entry["slideContent"] = ""
            text_entry["slideHtml"] = ""

            matched_slide, score, matched_index = find_best_match(
                ocr_text, all_slides, slide_texts, last_matched_index, config
            )

            if matched_slide is not None:
                total_matched += 1
                last_matched_index = matched_index
                text_entry["sectionId"] = matched_slide["sectionId"]
                text_entry["sectionUri"] = matched_slide["sectionUri"]
                text_entry["sectionTitle"] = matched_slide["sectionTitle"]
                text_entry["slideUri"] = matched_slide["slideUri"]
                text_entry["slideContent"] = matched_slide["slideContent"]
                text_entry["slideHtml"] = matched_slide["html"]

    with open(updated_extracted_file_path, "w", encoding="utf-8") as output_file:
        json.dump(results, output_file, indent=4, ensure_ascii=False)

    pct = (total_matched / total_candidates * 100) if total_candidates else 0
    print(
        f"Slides updated: {total_matched}/{total_candidates} matched ({pct:.1f}%) → "
        f"{updated_extracted_file_path}"
    )


def main():
    with open(ALL_COURSES_CLIPS_JSON, "r", encoding="utf-8") as f:
        all_data = json.load(f)
    print("Starting slide matcher...")
    for course_id in COURSE_IDS:
        course_info = all_data.get(course_id, {})
        for semester_key in course_info:
            match_and_update_extracted_content(course_id, semester_key)


if __name__ == "__main__":
    main()
