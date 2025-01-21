# Semantic Video

This project is designed to enhance course notes by semantically linking them with text extracted from video frames of a professor teaching slides. The system uses Optical Character Recognition (OCR) to extract text from the slides in the video, processes the extracted content, and integrates it into the course notes by matching the slide content to relevant sections.

## Features
- Extracts text from video frames of teaching sessions at specified intervals.
- Processes extracted text and semantically matches it to existing course notes.
- Uses frame comparison to skip redundant frames with minimal differences.
- Utilizes Tesseract OCR for text extraction and OpenCV for frame processing. 

## Requirements

- Python 3.6 or higher
- Required Python libraries (listed in `requirements.txt`)

## Setup Instructions

### 1. Clone the Repository

Start by cloning the repository to your local machine:

- git clone [https://github.com/abhishek2021005/ocr-python.git](https://github.com/abhishek2021005/ocr-python.git)

### 2. Create a Virtual Environment

Create a virtual environment to isolate the project dependencies:

- python3 -m venv venv

Activate the virtual environment:

- **macOS/Linux**:
  source venv/bin/activate

- **Windows**:
  venv\Scripts\activate

### 3. Install Dependencies

- pip install -r requirements.txt

### 4. Set the env Variables 

- Create a .env.local file in the root directory of your project and add the following lines:
  
VIDEOS_DIR=./data/videos            #Replace directory name with the actual directory where video files are stored
CACHE_FILE=./data/cache/cache_file.json  # File path for the cache JSON file(adjust file name accordingly)


### 5. Run the script

- python scripts/video_text_extractor.py
  or
- python3 scripts/video_text_extractor.py

### Customize frame interval(optional)

The script processes frames at 10-second intervals by default. You can change the interval by modifying the following line in main.py

- interval_frames = int(fps \* 10) # Change 10 to your desired interval (in seconds)


## License

This project is licensed under the MIT License .

