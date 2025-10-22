import os
import json
from typing import List
import requests
import re
import cv2
from config import FAU_TV_OEMBED_BASE_URL,FAU_TV_BASE_URL

def clean_text(text: str) -> str:
    text = re.sub(r"[\u201c\u201d\u2022\u00bb\u2014\u2013]", "", text)
    text = re.sub(r"\s+", " ", text.strip())
    return text

def verify_video_integrity(video_path, full_validation=True):
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"OpenCV cannot open video: {video_path}")
            return False

        ret, _ = cap.read()
        if not ret:
            print(f"OpenCV could not read the first frame: {video_path}")
            cap.release()
            return False

        print(f"Quick verification passed (first frame readable): {video_path}")

        if full_validation:
            print(f"Performing full validation for video: {video_path}")

            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            print(f"Video FPS: {fps}")
            print(f"Expected frame count: {total_frame_count}")

            frame_count = 0
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            while True:
                ret, _ = cap.read()
                if not ret:
                    break
                frame_count += 1

                # Track progress
                progress = (frame_count / total_frame_count) * 100
                if frame_count % 1000 == 0:
                    print(f"Verification progress: {progress:.2f}%")

            cap.release()

            print(f"Actual frame count: {frame_count}")

            if frame_count < total_frame_count:
                print(
                    f"Frame mismatch: expected {total_frame_count}, got {frame_count}. Video might be corrupted."
                )
                return False

            print(f"Full validation passed. Total frames: {frame_count}")

        cap.release()
        return True

    except Exception as e:
        print(f"Error while verifying video: {video_path}, Error: {e}")
        return False


def extract_clip_ids(file_path: str, course_name: str) -> List[str]:
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    course_data = data.get(course_name)
    if not course_data:
        return []
    clips = course_data.get("clips")
    if not isinstance(clips, list):
        return []
    return [
        clip["clip_id"].strip()
        for clip in clips
        if isinstance(clip.get("clip_id"), str) and clip["clip_id"].strip()
    ]


def load_cache(cache_file):
    if cache_file is None:
        return {}
    print(cache_file)
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            content = f.read()
            return json.loads(content) if content else {}
    return {}


def save_cache(cache, cache_file):
    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=4)
    print(f"Saved cache to {cache_file}")


def download_video(url, file_path):
    if not file_path.endswith(".m4v"):
        file_path = f"{file_path}.m4v"

    headers = {}
    if os.path.exists(file_path):
        existing_file_size = os.path.getsize(file_path)
        headers["Range"] = f"bytes={existing_file_size}-"
    else:
        existing_file_size = 0

    try:
        response = requests.get(url, stream=True, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            print(f"URL not found: {url}")
            return None
        else:
            print(f"Failed to download file. HTTP Status: {response.status_code}")
            return None
    except Exception as err:
        print(f"An error occurred: {err}")
        return None

    total_size = int(response.headers.get("content-length", 0)) + existing_file_size
    print(f"Downloading {url} to {file_path} ({total_size // (1024 * 1024)} MB)")

    with open(file_path, "ab") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

    print(f"Download completed: {file_path}")
    return file_path


def get_clip_info(clip_id):
    try:
        clip_url = f"{FAU_TV_OEMBED_BASE_URL}?url={FAU_TV_BASE_URL}/clip/id/{clip_id}&format=json"
        response = requests.get(clip_url)
        response.raise_for_status()
        data = response.json()
        for key in ["file"]:
            if key in data and data[key]:
                return data[key]

        print(f"No video/audio link found for clip ID: {clip_id}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch clip data for clip ID: {clip_id}. Error: {str(e)}")
        return None