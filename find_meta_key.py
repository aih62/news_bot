import requests
from requests.auth import HTTPBasicAuth
import os
import time
from dotenv import load_dotenv
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "inhoe.an@gmail.com")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

def find_correct_meta_key():
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    test_image_url = f"https://picsum.photos/seed/{int(time.time())}/1200/630"
    
    print(f"--- 메타 키 정밀 탐색 테스트 시작 ---")
    
    # 주요 외부 이미지 플러그인들이 사용하는 모든 가능한 키 조합
    payload = {
        "title": f"메타 키 탐색 테스트 ({time.strftime('%H:%M:%S')})",
        "content": "이 포스트는 여러 플러그인의 메타 키를 테스트합니다. 이미지가 보인다면 그 중 하나가 정답입니다.",
        "status": "publish",
        "meta": {
            "external_image_url": test_image_url,
            "_external_image_url": test_image_url,
            "fifu_image_url": test_image_url,
            "_fifu_image_url": test_image_url,
            "nelio_external_featured_image_url": test_image_url,
            "_nelio_external_featured_image_url": test_image_url,
            "external_url": test_image_url,
            "_external_url": test_image_url
        }
    }
    
    try:
        res = requests.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30, verify=False)
        
        if res.status_code in [200, 201]:
            data = res.json()
            print(f"✅ 테스트 포스트 생성 완료: {data.get('link')}")
            print(f"서버가 반환한 메타 데이터: {json.dumps(data.get('meta'), indent=2)}")
            print("\n위 링크를 확인해 보세요. 이미지가 보인다면 성공입니다!")
        else:
            print(f"❌ 실패: {res.status_code}")
            print(res.text)
            
    except Exception as e:
        print(f"❌ 에러: {e}")

if __name__ == "__main__":
    find_correct_meta_key()
