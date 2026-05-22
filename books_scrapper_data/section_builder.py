"""
Extract paper-builder sections from Testmaker HTML pages.

Generic across all subjects:
- Discovers every section by walking <a class="list-group-item active"> headings.
- The section `key` is a slugified version of the actual heading text.
- Categorizes each section by the STRUCTURE of what follows the heading
  (multipart long-question vs simple count table vs board-pattern repeater).
- Captures optional fields like OR groups when present.

Reads every .html file from:
    config_page/config_page_html/

Writes a corresponding .json file to:
    config_page/config_page_json/

Usage:
    python extract_sections.py
    python extract_sections.py --input-dir custom/in --output-dir custom/out
"""

import argparse
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup


# ---------- helpers ----------

def clean_text(value):
    """Collapse whitespace and strip trailing periods."""
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", value).strip()
    text = text.rstrip(".").strip()
    return text


def parse_int(value, default=None):
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default


def extract_id_from_brackets(name_attr):
    """e.g. 'question[738]' -> 738, 'or_group[104]' -> 104."""
    if not name_attr:
        return None
    m = re.search(r"\[(\d+)\]", name_attr)
    return int(m.group(1)) if m else None


def slugify(text):
    """
    'Subjective With Board Pattern' -> 'subjective_with_board_pattern'
    Removes punctuation/icons, collapses whitespace, lowercases.
    """
    if not text:
        return ""
    # Strip non-alphanumeric (keeping spaces and underscores).
    cleaned = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    cleaned = cleaned.strip().lower()
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("_")


# ---------- section heading discovery ----------

def find_section_headings(soup):
    """
    Return every <a class="list-group-item active"> on the page.
    These are the section headings (Objective, Subjective ..., etc.).
    """
    return soup.find_all("a", class_=lambda c: c and "list-group-item" in c and "active" in c)


def find_associated_block(heading):
    """
    Given a section heading <a>, find the structural block it owns:
    - The <table> that follows it (most sections), OR
    - The <div class="clone-tab"> when the heading is inside one
      (the Long Question block).

    Returns a dict {"kind": "table"|"clone-tab", "element": <element>} or None.
    """
    # Case A: heading sits INSIDE a <div class="clone-tab"> — that whole div is
    # the section block (Long Question According to Board Pattern).
    parent_clone = heading.find_parent("div", class_="clone-tab")
    if parent_clone is not None:
        return {"kind": "clone-tab", "element": parent_clone}

    # Case B: heading is followed by a <table>. Walk forward through siblings
    # (and into wrappers like <div class="table-responsive">) until we hit
    # either a table, another heading, or the next clone-tab.
    cursor = heading
    for _ in range(20):
        sibling = cursor.find_next_sibling()
        if sibling is None:
            # Step up if no more siblings here.
            cursor = cursor.parent
            if cursor is None:
                return None
            continue

        # If we walked into another section heading, give up.
        if sibling.name == "a" and "list-group-item" in (sibling.get("class") or []):
            return None

        # If it's a clone-tab, treat it as that section's block.
        if sibling.name == "div" and "clone-tab" in (sibling.get("class") or []):
            return {"kind": "clone-tab", "element": sibling}

        # If it's a table, use it.
        if sibling.name == "table":
            return {"kind": "table", "element": sibling}

        # If it wraps a table (e.g., div.table-responsive), pull that out.
        if hasattr(sibling, "find"):
            inner_table = sibling.find("table")
            if inner_table is not None:
                # But avoid grabbing a table that belongs to a later section.
                next_heading = sibling.find("a", class_=lambda c: c and "list-group-item" in c and "active" in c)
                if next_heading is None:
                    return {"kind": "table", "element": inner_table}

        cursor = sibling

    return None


# ---------- row parsers ----------

def collect_or_group_options(table):
    """
    If the table has OR-group dropdowns, return the unique options list.
    """
    options = []
    seen = set()
    for select in table.find_all("select", attrs={"name": re.compile(r"or_group\[\d+\]")}):
        for opt in select.find_all("option"):
            val = parse_int(opt.get("value"))
            name = clean_text(opt.get_text())
            if val is None or not name or val in seen:
                continue
            seen.add(val)
            options.append({"type_id": val, "name": name})
    return options


def find_type_name_in_row(row):
    """
    The 'Question Type' column always contains plain text (no inputs/selects).
    Walk the row's <td>s and pick the first non-numeric, non-control cell.
    """
    for cell in row.find_all("td"):
        if cell.find(["input", "select", "button", "a"]):
            continue
        text = clean_text(cell.get_text())
        if not text or text.isdigit():
            continue
        return text
    return ""


def detect_is_addable(table):
    """
    Returns True when the section has a "+" button to add more rows.
    Looks for the well-known add-row anchors used across the existing JS:
    `addshortquestionrow`, `addmeaningquestionrow`, `addtranslationquestionrow`,
    `multipartQuestion`, etc. — any <a>/<button> with a class that begins
    with `add` and ends with `row` qualifies.
    """
    for el in table.find_all(["a", "button"]):
        classes = el.get("class") or []
        for cls in classes:
            cls_lower = cls.lower()
            if cls_lower.startswith("add") and cls_lower.endswith("row"):
                return True
    return False


def detect_has_solve_field(table):
    """
    Returns True when at least one row has a "Solve" input.
    Detected by input names: `solve[X]` (subjective), `sq_solve[]` /
    `*_solve[]` (board-pattern repeaters), or any input/select with class
    `solve_any`.
    """
    if table.find("input", attrs={"name": re.compile(r"^solve\[\d+\]$")}):
        return True
    if table.find("input", attrs={"name": re.compile(r"^[a-zA-Z_]+_solve\[\]$")}):
        return True
    if table.find(class_="solve_any"):
        return True
    return False


def parse_simple_count_row(row):
    """
    Row shape used by Objective / Subjective sections:
    has an <input name='question[X]' max='N'>.
    """
    count_input = row.find("input", attrs={"name": re.compile(r"question\[\d+\]")})
    if not count_input:
        return None

    type_id = extract_id_from_brackets(count_input.get("name"))
    if type_id is None:
        return None

    total_available = parse_int(
        count_input.get("max") or count_input.get("data-totalcount")
    )

    record = {
        "type_id": type_id,
        "name": find_type_name_in_row(row),
        "total_available": total_available,
    }

    or_select = row.find("select", attrs={"name": re.compile(r"or_group\[\d+\]")})
    if or_select:
        record["or_group_id"] = extract_id_from_brackets(or_select.get("name"))

    return record


def parse_board_repeater_row(row):
    """
    Row shape used by Board-Pattern repeater sections (Short Questions According
    to Board Pattern, Word Meanings According to Board Pattern, Idiomatic Urdu
    Translation, Detail Note on Topics, etc.).

    Anchor: an <input name='*_questions[]' max='N'> + a hidden ID input that
    tells us the question type (and/or a <select data-id='...'>).
    """
    # Anchor by any *[]-bracketed count input (sq_questions[], wm_questions[], …).
    count_input = row.find(
        "input",
        attrs={"name": re.compile(r"^[a-zA-Z_]+_questions\[\]$")},
    )
    if not count_input:
        return None

    total_available = parse_int(
        count_input.get("max") or count_input.get("data-totalcount")
    )

    # type_id can come from a hidden input ending in "_question_id" / "questions_id"
    # (e.g., short_question_id, meaning_question_id, etc.).
    type_id = None
    for hidden in row.find_all("input", attrs={"type": "hidden"}):
        name = (hidden.get("name") or "").lower()
        if "question_id" in name or "questions_id" in name:
            type_id = parse_int(hidden.get("value"))
            if type_id is not None:
                break

    # Fallback: a <select data-id="..."> in the row.
    if type_id is None:
        select = row.find("select", attrs={"data-id": True})
        if select:
            type_id = parse_int(select.get("data-id"))

    if type_id is None:
        return None

    return {
        "type_id": type_id,
        "name": find_type_name_in_row(row),
        "total_available": total_available,
    }


# ---------- section builders ----------

def build_simple_count_section(table):
    """
    Returns the question_types list (and optionally OR-group fields) for a
    table whose rows have name='question[X]' inputs.
    Returns None if no rows matched (so the caller can try other shapes).
    """
    tbody = table.find("tbody") or table
    question_types = []
    for row in tbody.find_all("tr"):
        record = parse_simple_count_row(row)
        if record:
            question_types.append(record)

    if not question_types:
        return None

    payload = {
        "is_addable": detect_is_addable(table),
        "has_solve_field": detect_has_solve_field(table),
        "question_types": question_types,
    }
    or_options = collect_or_group_options(table)
    if or_options:
        payload["has_or_group"] = True
        payload["or_group_options"] = or_options
    return payload


def build_board_repeater_section(table):
    """
    Returns the question_types list for a table whose rows look like the
    'Board Pattern' repeater shape (Word Meanings, Idiomatic, etc.).
    Returns None if no rows matched.
    """
    tbody = table.find("tbody") or table
    question_types = []
    seen_ids = set()
    for row in tbody.find_all("tr"):
        record = parse_board_repeater_row(row)
        if record and record["type_id"] not in seen_ids:
            seen_ids.add(record["type_id"])
            question_types.append(record)

    if not question_types:
        return None

    return {
        "is_addable": detect_is_addable(table),
        "has_solve_field": detect_has_solve_field(table),
        "question_types": question_types,
    }


def build_multipart_long_section(clone_tab):
    """
    Long Question section: <div class='clone-tab'> with solveMp + parts + choice.
    """
    solve_max = 0
    solve_select = clone_tab.find("select", attrs={"name": "solveMp"})
    if solve_select:
        nums = [
            parse_int(opt.get("value"))
            for opt in solve_select.find_all("option")
            if parse_int(opt.get("value")) is not None
        ]
        solve_max = max(nums) if nums else 0

    choice_options = []
    choice_select = clone_tab.find("select", attrs={"name": "mp_qtype_choice[]"})
    if choice_select:
        for opt in choice_select.find_all("option"):
            val = parse_int(opt.get("value"))
            if val is not None and val not in choice_options:
                choice_options.append(val)

    part_indexes = []
    for el in clone_tab.find_all(attrs={"name": re.compile(r"mp_qtype_p\d+\[\]")}):
        m = re.search(r"mp_qtype_p(\d+)\[\]", el.get("name", ""))
        if m:
            idx = int(m.group(1))
            if idx not in part_indexes:
                part_indexes.append(idx)
    part_indexes.sort()
    parts = [chr(ord("A") + i - 1) for i in part_indexes]

    question_types = []
    seen_ids = set()
    first_part_select = clone_tab.find("select", attrs={"name": "mp_qtype_p1[]"})
    if first_part_select:
        for opt in first_part_select.find_all("option"):
            val = parse_int(opt.get("value"))
            name = clean_text(opt.get_text())
            if val is None or not name or val in seen_ids:
                continue
            seen_ids.add(val)
            question_types.append({"type_id": val, "name": name})

    if not question_types and not parts:
        return None

    return {
        "is_addable": True,           # has the "Add another long question" button
        "has_solve_field": True,      # the section-level solveMp dropdown
        "config": {
            "solve_max": solve_max,
            "choice_options": choice_options,
            "parts": parts,
        },
        "question_types": question_types,
    }


# ---------- top-level orchestration ----------

def extract_sections(html):
    soup = BeautifulSoup(html, "html.parser")

    sections = []
    seen_blocks = set()  # avoid emitting the same clone-tab twice
    order = 0

    for heading in find_section_headings(soup):
        title = clean_text(heading.get_text())
        if not title:
            continue

        block = find_associated_block(heading)
        if block is None:
            continue

        # De-dup: a clone-tab contains its own heading AND may be reachable
        # as the next sibling of an outer heading. Only process it once.
        block_key = id(block["element"])
        if block_key in seen_blocks:
            continue
        seen_blocks.add(block_key)

        payload = None
        if block["kind"] == "clone-tab":
            payload = build_multipart_long_section(block["element"])
        elif block["kind"] == "table":
            # Try the simple-count shape first (most common).
            payload = build_simple_count_section(block["element"])
            if payload is None:
                # Fall through to the board-pattern repeater shape.
                payload = build_board_repeater_section(block["element"])

        if payload is None:
            continue

        order += 1
        section = {
            "key": slugify(title),
            "title": title,
            "order": order,
        }
        section.update(payload)
        sections.append(section)

    return {"sections": sections}


# ---------- batch runner ----------

def process_folder(input_dir: Path, output_dir: Path):
    if not input_dir.is_dir():
        print(f"[error] input folder not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    html_files = sorted(input_dir.glob("*.html")) + sorted(input_dir.glob("*.htm"))
    if not html_files:
        print(f"[warn] no .html files found in {input_dir}", file=sys.stderr)
        return

    success = 0
    failed = 0

    for html_path in html_files:
        out_path = output_dir / (html_path.stem + ".json")
        try:
            html = html_path.read_text(encoding="utf-8")
            result = extract_sections(html)
            out_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            section_count = len(result.get("sections", []))
            print(f"[ok]   {html_path.name} -> {out_path.name} ({section_count} sections)")
            success += 1
        except Exception as e:
            print(f"[fail] {html_path.name}: {e}", file=sys.stderr)
            failed += 1

    print(f"\nDone. {success} succeeded, {failed} failed. Output: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Batch extract paper-builder sections from HTML files.")
    parser.add_argument(
        "--input-dir",
        default="config_page/config_page_html",
        help="Folder containing .html files (default: config_page/config_page_html)",
    )
    parser.add_argument(
        "--output-dir",
        default="config_page/config_page_json",
        help="Folder to write .json files (default: config_page/config_page_json)",
    )
    args = parser.parse_args()

    process_folder(Path(args.input_dir), Path(args.output_dir))


if __name__ == "__main__":
    main()