import json
import os
from html_parsers.science1 import science_subject_parser
from html_parsers.science2 import science_subject_parser2_v1
from html_parsers.urdu3 import urdu_parser
from html_parsers.english import parse_english_2025

parsers = [science_subject_parser, science_subject_parser2_v1, parse_english_2025, urdu_parser]

html_dir = "chapters_html"
json_dir = "chapters_json"

os.makedirs(json_dir, exist_ok=True)

html_files = [f for f in os.listdir(html_dir) if f.endswith(".html")]
print(f"Found {len(html_files)} HTML files\n")

for html_file in html_files:
    base_name = os.path.splitext(html_file)[0]  # e.g. "9_old_math"
    html_path = os.path.join(html_dir, html_file)
    json_path = os.path.join(json_dir, f"{base_name}.json")

    print(f"Processing: {html_file}")

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    result = None

    for parser in parsers:
        try:
            result = parser(html)
            if result:
                print(f"  ✅ Parser worked: {parser.__name__}")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                break
        except Exception as e:
            print(f"  ❌ Parser failed: {parser.__name__} -> {e}")

    if not result:
        print(f"  ⚠️  No parser worked for: {html_file}")

    print()

print("All done!")