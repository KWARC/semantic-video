import cv2
import pytesseract
import time
import json
import datetime
import os
from rapidfuzz import fuzz
from utils import (
    download_video,
    load_cache,
    save_cache,
    get_clip_info,
    extract_clip_ids,
    verify_video_integrity,
)
from config import OCR_EXTRACTED_FILE_PATH, VIDEO_DOWNLOAD_DIR, FRAME_PROCESSING_SLEEP_TIME, COURSE_IDS


def setup_video_capture(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    # print(f"Video FPS: {video_path}*************{fps}")
    return cap, fps


def get_video_metadata(video_path):
    video_name = video_path.split("/")[-1]
    processing_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return video_name, processing_datetime


def crop_frame_to_remove_watermark(frame):
    height, width, _ = frame.shape
    watermark_height_percentage = 0.05
    watermark_height = int(height * watermark_height_percentage)
    cropped_frame = frame[0 : height - watermark_height, 0:width]
    return cropped_frame


def differentiate_frame(last_frame, current_frame):
    current_gray_frame = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    if (
        last_frame is None
        or cv2.norm(last_frame, current_gray_frame, cv2.NORM_L2) > 4000
    ):
        return True, current_gray_frame
    return False, None


def binary_search_frame_change(cap, start_time, end_time, fps, last_frame):
    while end_time - start_time > 1 / fps:
        mid_time = (start_time + end_time) / 2
        cap.set(cv2.CAP_PROP_POS_MSEC, mid_time * 1000)
        ret, frame = cap.read()
        if not ret:
            break
        cropped_frame = crop_frame_to_remove_watermark(frame)
        is_different, current_gray_frame = differentiate_frame(
            last_frame, cropped_frame
        )
        if is_different:
            end_time = mid_time
        else:
            start_time = mid_time
    return round(end_time, 2)


def save_results(
    video_name,
    text_dict,
    total_time,
    processing_datetime,
    results_file=os.getenv("RESULTS_FILE_PATH"),
):

    output_data = {
        "video_name": video_name,
        "text_data": text_dict,
        "total_processing_time_seconds": total_time,
        "processing_datetime": processing_datetime,
    }
    if os.path.exists(results_file):
        with open(results_file, "r") as f:
            existing_data = json.load(f)
        existing_data.append(output_data)
        with open(results_file, "w") as f:
            json.dump(existing_data, f, indent=4)
    else:
        with open(results_file, "w") as f:
            json.dump([output_data], f, indent=4)
    print(f"Extracted text saved to {results_file}")


def is_text_extension_of_last_slide(
    last_extracted_text, current_text, similarity_threshold
):
    if not current_text:
        return False
    if not last_extracted_text:
        return False
    similarity = fuzz.partial_ratio(last_extracted_text, current_text)
    return similarity > similarity_threshold


def save_partial_results(course_id,semester_key,clip_id, extracted_content):
    results_file = f"data/cache/{course_id}_{semester_key}_extracted_content.json"
    if os.path.exists(results_file):
        with open(results_file, "r") as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    if clip_id not in existing_data:
        existing_data[clip_id] = {"extracted_content": {}}

    existing_extracted_content = existing_data[clip_id]["extracted_content"]
    new_extracted = {str(k): v for k, v in extracted_content.items()}
    existing_extracted_content.update(new_extracted)
    with open(results_file, "w") as f:
        json.dump(existing_data, f, indent=4, ensure_ascii=False)



def extract_text_from_video(video_path, course_id, clip_id, start_time=0):
    cap, fps = setup_video_capture(video_path)
    video_name, processing_datetime = get_video_metadata(video_path)
    text_dict = {}
    interval_seconds = 10
    last_frame = None
    similarity_threshold = 60

    # Inform the user and seek the video to the correct position if start_time is provided
    if start_time > 0:
        print(f"Seeking video to start time: {start_time} seconds...")
        cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)

    text_dict = process_video_frames(
        cap, fps, interval_seconds, last_frame, similarity_threshold, course_id, clip_id, start_time
    )

    cap.release()
    cv2.destroyAllWindows()

    return text_dict



def process_video_frames(cap, fps, interval_seconds, last_frame, similarity_threshold, course_id, clip_id, start_time):
    next_check_time = start_time
    text_dict = {}
    video_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    sleep_time = float(FRAME_PROCESSING_SLEEP_TIME)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if current_time >= next_check_time:
            text_dict, last_frame = process_single_frame(
                cap,
                frame,
                fps,
                last_frame,
                current_time,
                text_dict,
                similarity_threshold,
            )
            next_check_time += interval_seconds
            if sleep_time > 0:
                time.sleep(sleep_time)  # Add delay between frame processing

            # Save partial results
            save_partial_results(course_id,semester_key, clip_id, text_dict)

            # Display progress
            progress = (current_time / video_duration) * 100
            print(f"Processing progress: {progress:.2f}%")

    if text_dict:
        last_key = max(text_dict.keys())
        text_dict[last_key]["end_time"] = video_duration

    return text_dict


def process_single_frame(
    cap, frame, fps, last_frame, current_time, text_dict, similarity_threshold
):
    current_cropped_frame = crop_frame_to_remove_watermark(frame)
    if (
        last_frame is not None and len(last_frame.shape) != 2
    ):  # for gray scale image dimension is 2
        last_frame = cv2.cvtColor(last_frame, cv2.COLOR_BGR2GRAY)
    last_extracted_text = (
        pytesseract.image_to_string(last_frame).strip()
        if last_frame is not None
        else ""
    )
    is_different, current_gray_frame = differentiate_frame(
        last_frame, current_cropped_frame
    )

    if is_different:
        exact_frame_change_time = binary_search_frame_change(
            cap, max(0, current_time - 10), current_time, fps, last_frame
        )
        last_frame = current_gray_frame
        current_frame_extracted_text = pytesseract.image_to_string(
            current_gray_frame
        ).strip()

        if current_frame_extracted_text:
            update_text_dict(
                text_dict,
                last_extracted_text,
                current_frame_extracted_text,
                exact_frame_change_time,
                similarity_threshold,
            )
            # only for testing purpose
            output_file_path = "extracted_text_log.txt"

            with open(output_file_path, "a") as log_file:
                log_file.write(
                    f"Extracted Text at {exact_frame_change_time}s: {current_frame_extracted_text}\n"
                )

    return text_dict, last_frame


def update_text_dict(
    text_dict,
    last_extracted_text,
    current_frame_extracted_text,
    exact_frame_change_time,
    similarity_threshold,
):
    is_extension = is_text_extension_of_last_slide(
        last_extracted_text, current_frame_extracted_text, similarity_threshold
    )

    if is_extension:
        last_key = max(text_dict.keys()) if text_dict else exact_frame_change_time

        text_dict[last_key]["end_time"] = exact_frame_change_time
        text_dict[last_key]["ocr_slide_content"] = current_frame_extracted_text

    else:
        if text_dict:
            last_key = max(text_dict.keys())
            text_dict[last_key]["end_time"] = exact_frame_change_time

        text_dict[exact_frame_change_time] = {
            "start_time": exact_frame_change_time,
            "end_time": exact_frame_change_time,
            "ocr_slide_content": current_frame_extracted_text,
        }


def process_videos(clip_ids, course_id, semester_key):
    video_dir = os.path.join(VIDEO_DOWNLOAD_DIR, course_id, semester_key)
    os.makedirs(video_dir, exist_ok=True)

    for clip_id in clip_ids:
        results_file = f"data/cache/{course_id}_{semester_key}_extracted_content.json"
        if os.path.exists(results_file):
            with open(results_file, "r", encoding='utf-8') as f:
                cache = json.load(f)
        else:
            cache = {}
        
        slides_and_audio_url = get_clip_info(clip_id)

        if not slides_and_audio_url:
            print(f"No valid link found for clip ID {clip_id}. Skipping.")
            continue

        temp_video_path = os.path.join(video_dir, f"{clip_id}_tmp.m4v")
        final_video_path = os.path.join(video_dir, f"{clip_id}.m4v")
        
        if not os.path.exists(final_video_path):
            if(course_id=="ai-2"):
                print("Course ai-2 , skipping download")
                continue
            print(f"Downloading video for clip ID: {clip_id}")
            for try_idx in range(10):
                try:
                    download_video(slides_and_audio_url, temp_video_path)
                    break
                except:
                    print('failed:' + clip_id)
                    time.sleep(2*try_idx*try_idx)

            if verify_video_integrity(temp_video_path):
                os.rename(temp_video_path, final_video_path)
                print(f"Successfully downloaded and verified clip ID {clip_id}.")
            else:
                print(f"Failed to verify download for clip ID {clip_id}. Skipping.")
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
                continue
        else:
            print(f"Video for clip ID {clip_id} already downloaded. Skipping download.")
        clip_id = str(clip_id)
        if clip_id in cache:
            if "extracted_content" in cache[clip_id] and cache[clip_id]["extracted_content"]:
                last_entry = max(cache[clip_id]["extracted_content"].keys(), key=float)
                video_path = os.path.join(video_dir, f"{clip_id}.m4v")
                cap, fps = setup_video_capture(video_path)
                video_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
                cap.release()
                if cache[clip_id]["extracted_content"][last_entry]["end_time"] == video_duration:
                    print(f"Skipping {clip_id}, already cached and fully processed.")
                    continue
                else:
                    print(f"Incomplete extraction detected for {clip_id}. Restarting from beginning.")
                    del cache[clip_id] 
                    with open(results_file, "w") as f:
                         json.dump(cache, f, indent=4) 
                    start_time = 0
            else:
                print(f"Text extraction pending for {clip_id}. Proceeding to extract.")
                start_time = 0
        else:
            print(f"Processing clip ID: {clip_id} (not in cache).")
            start_time = 0

        

        print(f"Processing video for text extraction: {final_video_path}")
        extracted_content = extract_text_from_video(final_video_path, course_id, clip_id, start_time)

        save_partial_results(course_id,semester_key, clip_id, extracted_content)

        print(f"Finished processing clip ID {clip_id}. Moving to the next clip.\n")


if __name__ == "__main__":
    all_courses_clips_path = os.path.join(
    OCR_EXTRACTED_FILE_PATH, "all_courses_clips.json"
    )
    with open(all_courses_clips_path, "r", encoding="utf-8") as f:
        all_data = json.load(f)
    for course_id in COURSE_IDS:
        course_info = all_data.get(course_id, {})
        for semester_key in course_info:
            clips = course_info[semester_key].get("clips", [])
            clip_ids = [clip["clip_id"] for clip in clips]
            print(f"Processing course: {course_id} ({semester_key}) with {len(clip_ids)} clips")
            process_videos(clip_ids, course_id,semester_key)
