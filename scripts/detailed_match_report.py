"""
Generate detailed match reports showing:
- Matched entries with slide data
- Unmatched entries where no slide was found
- Section-by-section breakdown
- Video-by-video analysis
- Summary statistics
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SLIDES_OUTPUT_DIR = os.path.join(BASE_DIR, "data/slides/")


def analyze_file(file_path):
    """
    Analyze a single _updated_extracted_content.json file.
    Returns detailed report with matched/unmatched by section and video.
    """
    
    filename = file_path.name
    base_name = filename.replace("_updated_extracted_content.json", "")
    parts = base_name.rsplit("_", 1)
    
    if len(parts) != 2:
        return None
    
    subject_name = parts[0]
    semester_key = parts[1]
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    report = {
        "subject": subject_name,
        "semester": semester_key,
        "videos": {},
        "sections": {}, 
        "summary": {
            "total_candidates": 0,
            "total_matched": 0,
            "total_unmatched": 0,
            "match_percent": 0.0,
            "sections_count": 0,
        }
    }
    
    section_stats = defaultdict(lambda: {
        "matched": [],
        "unmatched": [],
        "stats": {"total": 0, "matched": 0, "unmatched": 0, "match_percent": 0.0}
    })
    
    for video_id, video_data in data.items():
        if "extracted_content" not in video_data:
            continue
        
        video_matched = []
        video_unmatched = []
        
        for timestamp, entry in video_data["extracted_content"].items():
            ocr_text = entry.get("ocr_slide_content", "")

            if len(ocr_text) >= 100:
                entry_info = {
                    "timestamp": timestamp,
                    "ocr_text": ocr_text[:200], 
                    "start_time": entry.get("start_time"),
                    "end_time": entry.get("end_time"),
                }

                if entry.get("slideUri") and entry.get("sectionId"):
                    entry_info["slide_matched"] = {
                        "sectionId": entry.get("sectionId"),
                        "sectionTitle": entry.get("sectionTitle"),
                        "slideUri": entry.get("slideUri"),
                        "slideContent": entry.get("slideContent", "")[:200],
                    }
                    video_matched.append(entry_info)
                    report["summary"]["total_matched"] += 1
     
                    section_id = entry.get("sectionId", "unknown")
                    section_title = entry.get("sectionTitle", "Unknown Section")
                    section_key = f"{section_id}:{section_title}"
                    section_stats[section_key]["matched"].append(entry_info)
                else:

                    video_unmatched.append(entry_info)
                    report["summary"]["total_unmatched"] += 1
                    section_key = "NO_MATCH"
                    section_stats[section_key]["unmatched"].append(entry_info)
                
                report["summary"]["total_candidates"] += 1

        if video_matched or video_unmatched:
            report["videos"][video_id] = {
                "matched": video_matched,
                "unmatched": video_unmatched,
                "stats": {
                    "total": len(video_matched) + len(video_unmatched),
                    "matched": len(video_matched),
                    "unmatched": len(video_unmatched),
                    "match_percent": round(
                        (len(video_matched) / (len(video_matched) + len(video_unmatched)) * 100)
                        if (len(video_matched) + len(video_unmatched)) > 0
                        else 0.0,
                        2
                    ),
                }
            }

    for section_key, section_data in section_stats.items():
        matched_count = len(section_data["matched"])
        unmatched_count = len(section_data["unmatched"])
        total = matched_count + unmatched_count
        
        section_data["stats"] = {
            "total": total,
            "matched": matched_count,
            "unmatched": unmatched_count,
            "match_percent": round(
                (matched_count / total * 100) if total > 0 else 0.0, 2
            )
        }

        if section_key == "NO_MATCH":
            report["sections"][section_key] = {
                "unmatched": section_data["unmatched"],
                "stats": section_data["stats"]
            }
        else:
            report["sections"][section_key] = {
                "matched": section_data["matched"],
                "unmatched": section_data["unmatched"],
                "stats": section_data["stats"]
            }

    total = report["summary"]["total_candidates"]
    if total > 0:
        report["summary"]["match_percent"] = round(
            (report["summary"]["total_matched"] / total) * 100, 2
        )
    
    report["summary"]["sections_count"] = len([s for s in report["sections"].keys() if s != "NO_MATCH"])
    
    return report


def main():
    """
    Auto-detect all _updated_extracted_content.json files and generate detailed reports.
    """
    
    print(f"{'='*70}")
    print(f"Auto-detecting and analyzing all updated_extracted_content files")
    print(f"Section-by-section breakdown included")
    print(f"{'='*70}\n")

    slides_dir = Path(SLIDES_OUTPUT_DIR)
    files = sorted(slides_dir.glob("*_updated_extracted_content.json"))
    
    if not files:
        print(f"❌ No files found matching pattern: *_updated_extracted_content.json")
        print(f"Search directory: {SLIDES_OUTPUT_DIR}")
        return
    
    print(f"✓ Found {len(files)} files to analyze\n")
    
    all_reports = {}
    
    for file_path in files:
        print(f"Processing {file_path.name}...", end=" ")
        
        report = analyze_file(file_path)
        
        if not report:
            print("⚠ Could not parse filename")
            continue
        
        subject = report["subject"]
        semester = report["semester"]
        key = f"{subject}_{semester}"
        
        all_reports[key] = report

        individual_file = os.path.join(SLIDES_OUTPUT_DIR, f"{subject}_{semester}_detailed_match_report.json")
        with open(individual_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        total = report["summary"]["total_candidates"]
        matched = report["summary"]["total_matched"]
        match_percent = report["summary"]["match_percent"]
        sections = report["summary"]["sections_count"]
        
        print(f"✓ {matched}/{total} matched ({match_percent}%) | {sections} sections")
    

    comprehensive_file = os.path.join(SLIDES_OUTPUT_DIR, "all_detailed_match_reports.json")
    with open(comprehensive_file, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print(f"✓ Analysis complete!")
    print(f"{'='*70}")
    print(f"Total analyzed: {len(all_reports)} subject-semester combinations\n")
    
    if all_reports:
        print(f"Detailed breakdown:")
        for key, report in all_reports.items():
            total = report["summary"]["total_candidates"]
            matched = report["summary"]["total_matched"]
            match_percent = report["summary"]["match_percent"]
            sections = report["summary"]["sections_count"]
            print(f"  {key}: {matched}/{total} matched ({match_percent}%) | {sections} sections")
    
    print(f"\nReports saved:")
    print(f"  - Individual: data/slides/{{subject}}_{{semester}}_detailed_match_report.json")
    print(f"  - Comprehensive: {comprehensive_file}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

