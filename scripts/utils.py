import os
import json
import requests


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


def download_video(video_url, video_path):
    video_extension = ".mp4"  # Assuming you're downloading .mp4 videos
    video_path_with_extension = f"{video_path}{video_extension}"

    response = requests.get(video_url, stream=True)
    if response.status_code == 200:
        with open(video_path_with_extension, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
        print(f"Downloaded video to {video_path_with_extension}")
    else:
        print(f"Failed to download video: {video_url}")
    return video_path_with_extension

