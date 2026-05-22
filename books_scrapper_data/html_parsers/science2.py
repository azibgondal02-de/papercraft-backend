from bs4 import BeautifulSoup

def clean(x):
    return x.strip() if x else ""

def science_subject_parser2_v1(html: str):
    soup = BeautifulSoup(html, "html.parser")
    result = []

    for block in soup.select("div.alert"):
        chapter_input = block.select_one("input.chapter-checkbox")
        if not chapter_input:
            continue

        chapter_id = chapter_input.get("value", "")

        # =========================
        # CHAPTER NAME
        # =========================
        en = ""
        ur = ""

        label = block.select_one("div.checkbox")

        if label:
            # Extract Urdu first
            ur_tag = label.select_one("span[dir='rtl']")
            if ur_tag:
                ur = clean(ur_tag.get("title") or ur_tag.get_text())
                ur_tag.extract()

            # Now extract English cleanly
            b_tag = label.select_one("b")
            if b_tag:
                en = clean(b_tag.get_text())
            else:
                raw = label.get_text(" ", strip=True)
                en = clean(raw)

        # =========================
        # TOPICS
        # =========================
        topics = []

        for inp in block.select("input.topic-checkbox"):
            tid = clean(inp.get("value", ""))

            span = inp.find_next("span")
            name_en = ""
            name_ur = ""

            if span:
                name_en = clean(span.get("title") or span.get_text())
                name_ur = clean(span.get_text())

            topics.append({
                "id": tid,
                "name_en": name_en,
                "name_ur": name_ur
            })

        result.append({
            "chapter_id": chapter_id,
            "chapter_name_en": en,
            "chapter_name_ur": ur,
            "topics": topics
        })

    return result