import requests
import json
import re
from urllib.parse import unquote
from html_parsers.science1 import science_subject_parser
from html_parsers.science2 import science_subject_parser2_v1
from html_parsers.urdu3 import urdu_parser
from html_parsers.english import parse_english_2025

# ========================
# CONFIGURATION
# ========================
CURL_TEMPLATE = """
curl 'https://testmaker.pk/paper_board.php?h=questions' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Accept-Language: en-GB,en-US;q=0.9,en;q=0.8' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
  -b 'PHPSESSID=02c0a280072b97620944f6f9faee1c89; _gid=GA1.2.1136247170.1777563795; _ga_R56GJNW3K9=GS2.1.s1777657566$o10$g0$t1777657638$j60$l0$h0; _ga=GA1.1.2036651462.1776935423; _ga_LK0WS1G801=GS2.1.s1777669101$o23$g1$t1777672069$j38$l0$h0' \
  -H 'Origin: https://testmaker.pk' \
  -H 'Referer: https://testmaker.pk/paper_board.php?class_id=31&subject_id=2&pattern=short_syllabus&ch%5B%5D=4577&ch%5B%5D=4578&ch%5B%5D=4579&ch%5B%5D=4580&ch%5B%5D=4581&ch%5B%5D=4582&ch%5B%5D=4583&ch%5B%5D=4584&ch%5B%5D=4585&ch%5B%5D=4586&ch%5B%5D=4587&ch%5B%5D=8045&ch%5B%5D=4588&ch%5B%5D=4589&ch%5B%5D=4590&ch%5B%5D=4591&ch%5B%5D=4592&ch%5B%5D=4593&ch%5B%5D=4594&ch%5B%5D=4595&ch%5B%5D=4736&ch%5B%5D=10313&ch%5B%5D=4735&ch%5B%5D=4731&ch%5B%5D=4732&ch%5B%5D=4733&ch%5B%5D=4724&ch%5B%5D=4734&ch%5B%5D=4825&ch%5B%5D=4826&ch%5B%5D=4824&ch%5B%5D=4827&ch%5B%5D=4828&ch%5B%5D=4830&ch%5B%5D=4831&ch%5B%5D=4832&ch%5B%5D=4833&ch%5B%5D=4834&exercise_question%5B%5D=1&exercise_question%5B%5D=0&exercise_question%5B%5D=2&exercise_question%5B%5D=3&exercise_question%5B%5D=4' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -H 'sec-ch-ua: "Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --data-raw 'id=ID_PLACEHOLDER&chapters_no=&chapter_ids=4577%2C4578%2C4579%2C4580%2C4581%2C4582%2C4583%2C4584%2C4585%2C4586%2C4587%2C8045%2C4588%2C4589%2C4590%2C4591%2C4592%2C4593%2C4594%2C4595%2C4736%2C10313%2C4735%2C4731%2C4732%2C4733%2C4724%2C4734%2C4825%2C4826%2C4824%2C4827%2C4828%2C4830%2C4831%2C4832%2C4833%2C4834&exercise_question=1%2C0%2C2%2C3%2C4&ex_ids=&topics=0&pattern=short_syllabus&class_id=31'
"""
x = "ID_PLACEHOLDER"
idd = [
    1, 2, 27, 738, 124, 121, 123, 161, 175, 127, 122, 126, 125, 1010, 255, 257, 258, 259, 677
]

sub_name = "9_old_urdu"

# ========================
# PARSE CURL COMMAND
# ========================
def parse_curl(curl_cmd):
    """Extract URL, headers, cookies, and data from curl command"""
    
    # Extract URL
    url_match = re.search(r"curl\s+'([^']+)'", curl_cmd)
    url = url_match.group(1) if url_match else None
    
    # Extract headers
    headers = {}
    for match in re.finditer(r"-H\s+'([^:]+):\s*([^']+)'", curl_cmd):
        headers[match.group(1)] = match.group(2)
    
    # Extract cookies
    cookies = {}
    cookie_match = re.search(r"-b\s+'([^']+)'", curl_cmd)
    if cookie_match:
        cookie_str = cookie_match.group(1)
        for cookie in cookie_str.split('; '):
            if '=' in cookie:
                key, value = cookie.split('=', 1)
                cookies[key] = value
    
    # Extract POST data (handle both --data-raw and --data)
    data = None
    data_match = re.search(r"--data(?:-raw)?\s+\$?'(.+)'(?:\s|$)", curl_cmd, re.DOTALL)
    if data_match:
        data = data_match.group(1)
        # URL decode the data
        data = unquote(data)
    
    return url, headers, cookies, data

# ========================
# PROCESS EACH ID
# ========================
sum = 0
for idx, request_id in enumerate(idd, 1):
    print(f"\n{'='*60}")
    print(f"Processing [{idx}/{len(idd)}]: ID={request_id} | {sub_name}")
    print(f"{'='*60}\n")
    
    # Generate curl with current ID
    curl_command = CURL_TEMPLATE.replace('ID_PLACEHOLDER', str(request_id))
    
    questions_json_path = f"data/{sub_name}/{request_id}_{sub_name}.json"
    
    # Parse curl
    url, headers, cookies, data = parse_curl(curl_command)
    
    print(f"ID: {request_id}")
    print("URL:", url)
    print("Headers:", len(headers), "items")
    print("Cookies:", len(cookies), "items")
    print("Data length:", len(data) if data else 0)
    print("\nData preview:", data[:200] if data else "None")
    print()
    
    # Create session with cookies
    session = requests.Session()
    session.cookies.update(cookies)
    
    # Make the request
    response = session.post(url, headers=headers, data=data)
    
    print("Status Code:", response.status_code)
    print("Response preview:", response.text[:500])
    
    # Save response
    try:
        response_data = response.json()
        
        if response_data.get("Success") == "false":
            print(f"\n❌ API ERROR: {response_data.get('Msg')}")
        else:
            print("\n✅ SUCCESS!")
            print("Questions Count:", len(response_data.get("Record", [])))
            sum += len(response_data.get("Record", []))
            
            with open(questions_json_path, "w", encoding="utf-8") as f:
                json.dump(response_data, f, ensure_ascii=False, indent=2)
            
            print(f"Saved to: {questions_json_path}")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("Response is not JSON")

print(f"\n{'='*60}")
print(f"ALL DONE! Processed {len(idd)} requests")
print(f"Sum = {sum}")
print(f"{'='*60}")