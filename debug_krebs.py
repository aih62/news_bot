import requests
import re

url = "https://krebsonsecurity.com/2026/03/how-ai-assistants-are-moving-the-security-goalposts/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    res = requests.get(url, headers=headers, timeout=10, verify=False)
    print(f"Status Code: {res.status_code}")
    html = res.text
    
    # meta 태그들 출력
    meta_tags = re.findall(r'<meta [^>]+>', html)
    print("\n--- Meta Tags ---")
    for tag in meta_tags:
        if 'og:image' in tag or 'twitter:image' in tag or 'thumbnail' in tag:
            print(tag)
            
except Exception as e:
    print(f"Error: {e}")
