import os
import json
import requests
import time


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
    # Ensure the file has the correct extension
    if not file_path.endswith(".mp4") and not file_path.endswith(".m4v"):
        file_path = f"{file_path}.mp4"  # Add .mp4 extension by default
    
    headers = {}
    if os.path.exists(file_path):
        existing_file_size = os.path.getsize(file_path)
        headers["Range"] = f"bytes={existing_file_size}-"
    else:
        existing_file_size = 0

    response = requests.get(url, stream=True, headers=headers, timeout=30)
    if response.status_code not in (200, 206):
        raise Exception(f"Failed to download file. HTTP Status: {response.status_code}")

    total_size = int(response.headers.get("content-length", 0)) + existing_file_size
    print(f"Downloading {url} to {file_path} ({total_size // (1024 * 1024)} MB)")

    with open(file_path, "ab") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1 MB chunks
            if chunk:
                f.write(chunk)

    print(f"Download completed: {file_path}")
    return file_path  # Return the final file path
