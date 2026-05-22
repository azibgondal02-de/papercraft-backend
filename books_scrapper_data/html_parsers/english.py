from bs4 import BeautifulSoup
import re


def clean(text):
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    return " ".join(text.strip().split())


def parse_english_2025(html: str):
    soup = BeautifulSoup(html, "html.parser")
    result = []

    # only chapter blocks inside the form area
    blocks = soup.select("form#chapters-form div.alert")

    for block in blocks:
        # skip top bootstrap alerts like Class / warning
        if "alert-success" in block.get("class", []):
            continue
        if "alert-danger" in block.get("class", []):
            continue

        ul = block.find("ul")
        if not ul:
            continue

        # -------------------------
        # CHAPTER TITLE
        # -------------------------
        chapter_title = ""
        b = block.select_one("div.checkbox b")
        if b:
            chapter_title = clean(b.get_text())

        # detect english / urdu bucket
        has_urdu = bool(re.search(r'[\u0600-\u06FF]', chapter_title))

        chapter = {
            "chapter_id": "",
            "chapter_name_en": chapter_title if not has_urdu else "",
            "chapter_name_ur": chapter_title if has_urdu else "",
            "topics": []
        }

        # -------------------------
        # TOPICS
        # -------------------------
        for li in ul.select("li"):
            inp = li.select_one("input[name='ch[]']")
            if not inp:
                continue

            topic_id = clean(inp.get("value", ""))

            # remove input text, get visible topic text
            text_holder = li.find("div", style=lambda x: x and "font-size:15px" in x)
            topic_text = ""

            if text_holder:
                topic_text = clean(text_holder.get_text(" ", strip=True))
            else:
                topic_text = clean(li.get_text(" ", strip=True))

            # skip empty
            if not topic_text:
                continue

            topic_has_urdu = bool(re.search(r'[\u0600-\u06FF]', topic_text))

            chapter["topics"].append({
                "id": topic_id,
                "name_en": topic_text if not topic_has_urdu else "",
                "name_ur": topic_text if topic_has_urdu else ""
            })

        if chapter["topics"]:
            result.append(chapter)

    return result


