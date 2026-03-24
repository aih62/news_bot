import requests
from requests.auth import HTTPBasicAuth
import os
import json
import html
from dotenv import load_dotenv

load_dotenv()

WP_USERNAME = os.getenv("WP_USERNAME") or "inhoe.an@gmail.com"
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
WP_SITE_URL = os.getenv("WP_SITE_URL") or "https://ajken.mycafe24.com"
WP_SITE_URL = WP_SITE_URL.rstrip("/")

def get_recent_posts():
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    params = {"per_page": 30, "status": "publish"}
    try:
        res = requests.get(endpoint, auth=auth, params=params, timeout=20, verify=False)
        if res.status_code == 200:
            posts = res.json()
            for post in posts:
                print(f"[{post['date']}] {html.unescape(post['title']['rendered'])}")
        else:
            print(f"Error: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    get_recent_posts()
