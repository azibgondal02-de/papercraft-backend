from bs4 import BeautifulSoup

def clean(x):
    return " ".join(x.strip().split()) if x else ""

def urdu_parser(html: str):
    soup = BeautifulSoup(html, "html.parser")

    result = []

    # Each chapter block
    for block in soup.select("div.alert"):

        # -------------------------
        # CHAPTER ID (from checkall OR fallback "")
        # -------------------------
        chapter_input = block.select_one("input[id^='checkall']")

        chapter_id = ""
        if chapter_input:
            chapter_id = chapter_input.get("value", "")  # usually empty in your case

        # -------------------------
        # CHAPTER NAME (URDU / HEADER)
        # -------------------------
        chapter_name_en = ""
        chapter_name_ur = ""

        header = block.select_one("div.checkbox b")

        if header:
            chapter_name_ur = clean(header.get_text())
            chapter_name_en = ""  # not available in this HTML

        # -------------------------
        # TOPICS (STRICT SCOPING)
        # -------------------------
        topics = []

        for li in block.select("ul > li"):
            inp = li.select_one("input[name='ch[]']")
            span = li.select_one("span")

            if not inp or not span:
                continue

            tid = inp.get("value", "")
            name = clean(span.get_text())

            topics.append({
                "id": tid,
                "name_en": name,
                "name_ur": ""   # not provided in HTML
            })

        # -------------------------
        # FINAL STRUCTURE (ALWAYS SAME)
        # -------------------------
        result.append({
            "chapter_id": chapter_id,
            "chapter_name_en": chapter_name_en,
            "chapter_name_ur": chapter_name_ur,
            "topics": topics
        })

    return result