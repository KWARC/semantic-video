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

def download_video(video_url, output_path):
    response = requests.get(video_url, stream=True)
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            f.write(chunk)
    print(f"Downloaded video to {output_path}")
