from typing import Any, Optional
import cv2
import pytesseract
import time
import json
import datetime
import os
from rapidfuzz import fuzz
from dotenv import load_dotenv
import requests
from utils import download_video, load_cache, save_cache


load_dotenv(".env.local")

VIDEOS_DIR = os.getenv("VIDEOS_DIR")
# VIDEOS_DIR = os.getenv("VIDEOS_DIR")
# print(f"VIDEOS_DIR: {VIDEOS_DIR}")

CACHE_FILE = os.getenv("CACHE_FILE")


def setup_video_capture(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    # print(f"Video FPS: {fps}")
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


def extract_text_from_video(video_path):
    cap, fps = setup_video_capture(video_path)
    video_name, processing_datetime = get_video_metadata(video_path)
    text_dict = {}
    interval_seconds = 10
    start_time = time.time()
    last_frame = None
    similarity_threshold = 60

    text_dict = process_video_frames(
        cap, fps, interval_seconds, last_frame, similarity_threshold
    )

    cap.release()
    cv2.destroyAllWindows()

    end_time = time.time()
    total_time = end_time - start_time
    # only for debugging purpose (donot remove )
    # save_results(video_name, text_dict, total_time, processing_datetime)
    print(f"Total processing time: {total_time:.2f} seconds")

    return text_dict


def process_video_frames(cap, fps, interval_seconds, last_frame, similarity_threshold):
    next_check_time = 0
    text_dict = {}
    video_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps

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
            # print(
            #     f"Extracted Text at {exact_frame_change_time}s: {current_frame_extracted_text}"
            # )
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
        text_dict[last_key]["text_value"] = current_frame_extracted_text

    else:
        if text_dict:
            last_key = max(text_dict.keys())
            text_dict[last_key]["end_time"] = exact_frame_change_time

        text_dict[exact_frame_change_time] = {
            "start_time": exact_frame_change_time,
            "end_time": exact_frame_change_time,
            "text_value": current_frame_extracted_text,
        }


def process_videos(video_urls):
    cache = load_cache(CACHE_FILE)
    for url in video_urls:
        video_id = url.split("/")[-1].split("?")[0]
        if video_id in cache:
            print(f"Skipping {video_id}, already cached.")
            continue
        if video_id is None:
            return
        video_info = get_fau_clip_info(video_id)
        if video_info:
            video_url_720p = video_info.get("r720")
            if video_url_720p:
                video_path = os.path.join(VIDEOS_DIR, f"{video_id}.mp4")
            if not os.path.exists(video_path):
                download_video(video_url_720p, video_path)
            extracted_text = extract_text_from_video(video_path)
            cache[video_id] = {
                "url": video_url_720p,
                "extracted_text": extracted_text,
            }
            save_cache(cache, CACHE_FILE)


def get_fau_clip_info(clip_id: str) -> dict[str, Any]:
    if not clip_id:
        return
    response = requests.get(
        f"https://courses.voll-ki.fau.de/api/get-fau-clip-info/{clip_id}"
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    video_urls = [
        # "https://www.fau.tv/clip/id/54628",
        "https://www.fau.tv/clip/id/54629",
        # "https://www.fau.tv/clip/id/54630",
    ]
    process_videos(video_urls)
