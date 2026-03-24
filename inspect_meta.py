import requests
from requests.auth import HTTPBasicAuth
import os
import html
from dotenv import load_dotenv
import urllib3

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# .env 로드
load_dotenv()

WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "inhoe.an@gmail.com")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

def inspect_post_meta():
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    # 최신 3개 포스트 조회
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    params = {"per_page": 3, "status": "publish"}
    
    try:
        res = requests.get(endpoint, auth=auth, params=params, timeout=20, verify=False)
        if res.status_code == 200:
            posts = res.json()
            for post in posts:
                p_id = post['id']
                p_title = html.unescape(post['title']['rendered'])
                p_media_id = post['featured_media']
                
                print(f"\n--- [ID: {p_id}] {p_title} ---")
                print(f"  Featured Media ID: {p_media_id}")
                
                # 메타 데이터 상세 출력
                meta = post.get('meta', {})
                print(f"  Meta (as returned by API): {meta}")
                
                # Cloudinary URL이 들어있는지 확인
                fifu_url = meta.get('fifu_image_url', 'N/A')
                print(f"  fifu_image_url: {fifu_url}")
                
                # 혹시 다른 이름으로 들어있지는 않은지 확인
                for key in meta:
                    if 'fifu' in key.lower() or 'image' in key.lower() or 'url' in key.lower():
                        print(f"  [Found Candidate] {key}: {meta[key]}")

        else:
            print(f"조회 실패: {res.status_code}")
    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    inspect_post_meta()
