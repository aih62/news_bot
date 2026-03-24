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

def test_specific_plugin_keys():
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    test_image_url = f"https://picsum.photos/seed/{int(time.time())}/1200/630"
    
    print(f"--- 특정 플러그인 키(_harikrutfiwu_url) 집중 테스트 ---")
    print(f"사용할 이미지: {test_image_url}")
    
    payload = {
        "title": f"정밀 타겟 테스트 ({time.strftime('%H:%M:%S')})",
        "content": "이 테스트는 _harikrutfiwu_url 키가 API를 통해 전달되는지 확인합니다. (WP REST API Controller 설정 필요)",
        "status": "publish",
        "meta": {
            "_harikrutfiwu_url": test_image_url,  # External URL Featured Image 플러그인용
            "fifu_image_url": test_image_url,      # FIFU 플러그인용 (공개 키)
            "_fifu_image_url": test_image_url      # FIFU 플러그인용 (비공개 키)
        }
    }
    
    try:
        res = requests.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30, verify=False)
        
        if res.status_code in [200, 201]:
            data = res.json()
            print(f"✅ 포스팅 생성 완료: {data.get('link')}")
            print("서버가 저장한 메타 필드 목록:")
            print(json.dumps(data.get('meta'), indent=2))
            
            # 응답에 _harikrutfiwu_url이 포함되어 있는지 확인
            if "_harikrutfiwu_url" in data.get('meta', {}):
                print("\n🎉 성공! _harikrutfiwu_url이 정상적으로 등록되었습니다.")
            else:
                print("\n⚠️ 주의: _harikrutfiwu_url이 응답에 없습니다. WP REST API Controller에서 해당 필드를 'Write' 가능하게 설정하셨나요?")
        else:
            print(f"❌ 실패: {res.status_code}")
            print(res.text)
            
    except Exception as e:
        print(f"❌ 에러: {e}")

if __name__ == "__main__":
    test_specific_plugin_keys()
