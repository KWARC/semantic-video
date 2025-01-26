import os
import json
import requests
import re
import cv2


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


def extract_clip_ids(file_path, course_name):
    with open(file_path, "r") as file:
        data = json.load(file)

    if course_name in data:
        clip_ids = [
            entry["clipId"]
            for entry in data[course_name]
            if "clipId" in entry and entry["clipId"].strip()
        ]
        return clip_ids
    else:
        return []


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


def extract_download_links(content):
    regex = r'<a href="([^"]+/get/file[^"]*\?[^"]*download=1[^"]*)"[^\>]*>([^<]*)<\/a>'
    matches = re.findall(regex, content)
    links = [{"url": match[0], "label": match[1].strip()} for match in matches]
    return links


def find_slides_and_audio_link(links):
    for link in links:
        if link["label"].startswith("Folien & Audio") or link["label"].startswith(
            "Slides & Audio"
        ):
            return link["url"]
    if len(links) > 2:
        print(
            f"""// There are multiple video versions. Eg "Slides & video", "Slides only" etc.
         // Hope that the second link is always "Slides & Audio": {links[1]['url']}"""
        )
        return links[1]["url"]
    return None


def get_clip_info(clip_id):
    try:
        clip_url = f"https://www.fau.tv/clip/id/{clip_id}"
        response = requests.get(clip_url)
        response.raise_for_status()

        clip_page_content = response.text
        links = extract_download_links(clip_page_content)

        if not links:
            print(
                f"Video link not found for clip ID: {clip_id}. Continuing with the next link."
            )
            return None

        slides_and_audio_link = find_slides_and_audio_link(links)
        if not slides_and_audio_link:
            print(
                f"No slides and audio link found for clip ID: {clip_id}. Continuing with the next link."
            )
            return None

        return slides_and_audio_link

    except requests.exceptions.RequestException as e:
        print(
            f"Failed to fetch clip data for clip ID: {clip_id}. Error: {str(e)}. Continuing with the next link."
        )
        return None
