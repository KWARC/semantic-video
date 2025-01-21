import json
from bs4 import BeautifulSoup


def html_to_text(html_content):
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()


def process_slides(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    def process_section(section):
        """
        Processes a section recursively to extract relevant fields from slides.
        """
        processed_slides = []
        if "slides" in section:
            for slide in section["slides"]:
                processed_slides.append(
                    {
                        "slideContent": html_to_text(slide.get("slideContent", "")),
                        "sectionId": slide.get("sectionId", ""),
                        "archive": slide.get("archive", ""),
                        "filepath": slide.get("filepath", ""),
                    }
                )
        # Recursively process children
        if "children" in section:
            for child in section["children"]:
                processed_slides.extend(process_section(child))
        return processed_slides

    processed_data = []
    for section in data.get("sections", []):
        processed_data.extend(process_section(section))

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(processed_data, file, ensure_ascii=False, indent=4)

    print(f"Processed data has been saved to {output_file}")
