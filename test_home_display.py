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

def test_fifu_fake_id():
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    cloudinary_url = "https://res.cloudinary.com/djanrdmrg/image/upload/v1773129079/test_posts/sqwzm7ealmsjjaeygo87.png"
    
    print("가짜 썸네일 ID(-1)를 이용한 FIFU 메인 페이지 출력 테스트 중...")
    payload = {
        "title": f"CoverNews Home Test ({int(time.time())})",
        "content": "이 테스트는 메인 페이지(CoverNews 테마)에서 이미지가 보이는지 확인하기 위해 가짜 썸네일 ID를 부여합니다.",
        "status": "publish",
        # _thumbnail_id를 -1로 설정하면 일부 테마에서 FIFU 외부 URL을 인식합니다.
        "meta": {
            "fifu_image_url": cloudinary_url,
            "_fifu_image_url": cloudinary_url,
            "_thumbnail_id": "-1", 
            "fifu_image_alt": "CoverNews Home Test"
        }
    }
    
    try:
        res = requests.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30, verify=False)
        if res.status_code in [200, 201]:
            print(f"✅ 포스팅 성공! URL: {res.json().get('link')}")
            print("메인 페이지(홈)로 이동해서 이 글의 썸네일(구글 로고)이 보이는지 확인해 주세요.")
        else:
            print(f"❌ 실패: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    test_fifu_fake_id()
