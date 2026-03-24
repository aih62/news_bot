import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "inhoe.an@gmail.com")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

def discover_meta_keys():
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    print("1. 워드프레스 REST API '글(Post)' 스키마 분석 중...")
    try:
        # OPTIONS 요청을 통해 허용되는 필드와 메타 키 확인
        res = requests.options(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, verify=False, timeout=20)
        if res.status_code == 200:
            schema = res.json()
            meta_properties = schema.get('schema', {}).get('properties', {}).get('meta', {}).get('properties', {})
            print(f"✅ 확인된 메타 필드 목록: {list(meta_properties.keys())}")
            
            if "_harikrutfiwu_url" in meta_properties:
                print("-> _harikrutfiwu_url 필드가 API에 등록되어 있습니다!")
            if "harikrutfiwu_url" in meta_properties:
                print("-> harikrutfiwu_url (언더바 없음) 필드가 등록되어 있습니다!")
        else:
            print(f"❌ 스키마 조회 실패: {res.status_code}")
    except Exception as e:
        print(f"❌ 스키마 조회 에러: {e}")

    print("\n2. 변형된 키로 최종 테스트 포스팅 중...")
    test_image_url = "https://picsum.photos/1200/630"
    payload = {
        "title": "메타 키 최종 정밀 테스트",
        "content": "이 테스트는 가능한 모든 변형 키를 사용합니다.",
        "status": "publish",
        "meta": {
            "_harikrutfiwu_url": test_image_url,
            "harikrutfiwu_url": test_image_url,  # 언더바 제거 버전
            "external_image_url": test_image_url,
            "fifu_image_url": test_image_url
        }
    }
    
    try:
        res = requests.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, verify=False, timeout=30)
        if res.status_code in [200, 201]:
            data = res.json()
            print(f"✅ 포스팅 성공: {data.get('link')}")
            print(f"저장된 결과: {json.dumps(data.get('meta'), indent=2)}")
        else:
            print(f"❌ 포스팅 실패: {res.status_code}")
    except Exception as e:
        print(f"❌ 에러: {e}")

if __name__ == "__main__":
    discover_meta_keys()
