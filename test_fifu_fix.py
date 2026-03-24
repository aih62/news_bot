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

def test_underscore_meta():
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    cloudinary_url = "https://res.cloudinary.com/djanrdmrg/image/upload/v1773129079/test_posts/sqwzm7ealmsjjaeygo87.png"
    
    print("언더바(_) 포함 메타 키로 FIFU 강제 연동 테스트 중...")
    payload = {
        "title": f"FIFU Underscore Test ({int(time.time())})",
        "content": "이 테스트는 _fifu_image_url 메타 키를 직접 사용하여 이미지가 출력되는지 확인합니다.",
        "status": "publish",
        "featured_media": 0,
        "meta": {
            "fifu_image_url": cloudinary_url,
            "_fifu_image_url": cloudinary_url, # 숨겨진 키 추가
            "fifu_image_alt": "Underscore Test"
        }
    }
    
    try:
        res = requests.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30, verify=False)
        if res.status_code in [200, 201]:
            print(f"✅ 포스팅 성공! URL: {res.json().get('link')}")
        else:
            print(f"❌ 실패: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    test_underscore_meta()
