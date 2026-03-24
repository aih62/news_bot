import requests
from requests.auth import HTTPBasicAuth
import os
import time
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "inhoe.an@gmail.com")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
PLACEHOLDER_ID = 3221

def test_placeholder():
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    cloudinary_url = "https://res.cloudinary.com/djanrdmrg/image/upload/v1773129079/test_posts/sqwzm7ealmsjjaeygo87.png"
    
    print("플레이스홀더 미디어 ID와 함께 포스팅 테스트 중...")
    payload = {
        "title": f"Placeholder Test ({int(time.time())})",
        "content": "이 포스트는 featured_media를 3221로 설정하고 FIFU URL을 지정한 테스트입니다.",
        "status": "publish",
        "featured_media": PLACEHOLDER_ID,
        "meta": {
            "fifu_image_url": cloudinary_url,
            "fifu_image_alt": "Placeholder Test"
        }
    }
    
    try:
        res = requests.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30, verify=False)
        if res.status_code in [200, 201]:
            print(f"✅ 포스팅 성공! URL: {res.json().get('link')}")
            print("사이트에서 이 포스트의 이미지가 구글 로고(Cloudinary)로 나오는지 확인해 주세요.")
        else:
            print(f"❌ 실패: {res.status_code}")
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    test_placeholder()
