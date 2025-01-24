from flask import Flask, jsonify, request
import requests
import re

app = Flask(__name__)



def extract_download_links(content):
    regex = r'<a href="([^"]+/get/file[^"]*\?[^"]*download=1[^"]*)"[^\>]*>([^<]*)<\/a>'
    matches = re.findall(regex, content)
    links = [{"url": match[0], "label": match[1].strip()} for match in matches]
    return links

def find_slides_and_audio_link(links):
    for link in links:
        if link["label"].startswith("Folien & Audio") or link["label"].startswith("Slides & Audio"):
            return link["url"]
    if len(links) > 2:
        print(f'''// There are multiple video versions. Eg "Slides & video", "Slides only" etc.
         // Hope that the second link is always "Slides & Audio": {links[1]['url']}''')
        return links[1]["url"]
    return None 

@app.route('/get-clip-info', methods=['GET'])
def get_clip_info():
    clip_id = request.args.get('clipId')
    if not clip_id:
        return jsonify({"error": "clipId query parameter is required"}), 400

    try:
        clip_url = f"https://www.fau.tv/clip/id/{clip_id}"
        response = requests.get(clip_url)
        response.raise_for_status()  
        clip_page_content = response.text

        links = extract_download_links(clip_page_content)
        if not links:
            return jsonify({"error": "No download links found"}), 404

        slides_and_audio_link = find_slides_and_audio_link(links)
        if not slides_and_audio_link:
            return jsonify({"error": "No valid link found"}), 404

        return jsonify({
            "clipId": clip_id,
            "slidesAndAudioLink": slides_and_audio_link
        })

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to fetch clip data: {str(e)}"}), 500


@app.route("/api/slides", methods=["GET"])
def get_slides():
    # Logic to retrieve slide data
    return jsonify({"message": "Here are your slides!"})

@app.route("/api/sections", methods=["GET"])
def get_sections():
    # Logic to retrieve section data
    return jsonify({"message": "Here are your sections!"})

@app.route("/api/slides", methods=["POST"])
def get_fau_clip_info():
    data = request.get_json()
    # Logic to get video clip info
    return jsonify({"message": "Clip Info fetched successfully!", "data": data})

if __name__ == "__main__":
    app.run(debug=True)
