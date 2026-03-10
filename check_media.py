
import requests
from requests.auth import HTTPBasicAuth
import os

WP_USERNAME = "inhoe.an@gmail.com"
WP_APP_PASSWORD = "ISPe NJZf FCSb Qwh3 MPf2 ZPds"
WP_SITE_URL = "https://ajken.mycafe24.com"

def check_recent_media():
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    res = requests.get(f"{WP_SITE_URL}/wp-json/wp/v2/media?per_page=10", auth=auth)
    
    if res.status_code == 200:
        media_list = res.json()
        print(f"--- 최근 업로드된 미디어 {len(media_list)}개 ---")
        for m in media_list:
            print(f"ID: {m['id']} | Title: {m['title']['rendered']} | URL: {m['source_url']}")
    else:
        print(f"에러: {res.status_code}")
        print(res.text)

if __name__ == "__main__":
    check_recent_media()
