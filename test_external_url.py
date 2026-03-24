import requests
from requests.auth import HTTPBasicAuth
import os
import time
from dotenv import load_dotenv
import urllib3

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# .env 로드
load_dotenv()

WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "inhoe.an@gmail.com")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

def test_external_url_plugin():
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    # 테스트용 고해상도 랜덤 이미지 URL
    test_image_url = f"https://picsum.photos/seed/{int(time.time())}/1200/630"
    
    print(f"--- External URL Featured Image 플러그인 테스트 시작 ---")
    print(f"테스트 이미지: {test_image_url}")
    
    # 1. 일반적인 메타 키(external_image_url)로 시도
    # 2. 혹시 모를 언더바(_) 포함 키도 함께 전송
    payload = {
        "title": f"External URL 플러그인 테스트 ({time.strftime('%Y-%m-%d %H:%M:%S')})",
        "content": "이 포스트는 External URL Featured Image 플러그인 연동을 테스트하기 위해 생성되었습니다. 이미지가 썸네일(특성 이미지)로 잘 보인다면 성공입니다.",
        "status": "publish",
        "featured_media": 0, # 미디어 라이브러리 업로드 안 함
        "meta": {
            "external_image_url": test_image_url,
            "_external_image_url": test_image_url
        }
    }
    
    try:
        print("워드프레스 API 요청 전송 중...")
        res = requests.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30, verify=False)
        
        if res.status_code in [200, 201]:
            post_data = res.json()
            print(f"✅ 포스팅 성공!")
            print(f"포스트 링크: {post_data.get('link')}")
            print(f"포스트 ID: {post_data.get('id')}")
            print("\n위 링크를 브라우저에서 열어 '특성 이미지(썸네일)'가 나오는지 확인해 주세요.")
        else:
            print(f"❌ 포스팅 실패: {res.status_code}")
            print(f"응답 내용: {res.text}")
            
    except Exception as e:
        print(f"❌ 실행 중 예외 발생: {e}")

if __name__ == "__main__":
    test_external_url_plugin()
