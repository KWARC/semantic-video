
import requests
from typing import List, Dict
from config import (
    COURSE_API_BASE_URL,
)


def fetch_section_info():
    url = f"{COURSE_API_BASE_URL}/get-coverage-timeline"
    response = requests.get(url)
    print("Status code :", response.status_code)
    print("Response text :", response.text)

    return response.json()

def main():
    section_info = fetch_section_info()
    print(section_info)

if __name__ == "__main__":
    main()