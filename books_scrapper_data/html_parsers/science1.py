from bs4 import BeautifulSoup

def science_subject_parser(html: str):
    soup = BeautifulSoup(html, "html.parser")

    chapters = []

    chapter_blocks = soup.select(".alert")

    for block in chapter_blocks:
        chapter_checkbox = block.select_one(".chapter-checkbox")
        if not chapter_checkbox:
            continue

        chapter_id = chapter_checkbox.get("data-chapter-id")

        chapter_title_en = None
        chapter_title_ur = None

        b_tag = block.select_one("b")
        if b_tag:
            chapter_title_en = b_tag.get_text(strip=True)

        ur_span = block.select_one("div > span[dir='rtl']")
        if ur_span:
            chapter_title_ur = ur_span.get("title") or ur_span.get_text(strip=True)

        topics = []

        topic_inputs = block.select("input.topic-checkbox")

        for t in topic_inputs:
            topic_id = t.get("value")

            label = t.find_parent("label")
            span_tags = label.find_all("span") if label else []

            name_en = None
            name_ur = None

            if len(span_tags) >= 1:
                name_en = span_tags[0].get_text(strip=True)

            # RTL span is usually sibling in same div
            rtl_span = t.find_parent("div").find("span", attrs={"dir": "rtl"})
            if rtl_span:
                name_ur = rtl_span.get("title") or rtl_span.get_text(strip=True)

            if topic_id:
                topics.append({
                    "id": topic_id,
                    "name_en": name_en,
                    "name_ur": name_ur
                })

        if chapter_id:
            chapters.append({
                "chapter_id": chapter_id,
                "chapter_name_en": chapter_title_en,
                "chapter_name_ur": chapter_title_ur,
                "topics": topics
            })

    return chapters


