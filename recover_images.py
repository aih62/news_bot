import requests
from requests.auth import HTTPBasicAuth
import os
import json
from dotenv import load_dotenv
import urllib3

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# .env 로드
load_dotenv()

WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "inhoe.an@gmail.com")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
DEFAULT_IMAGE_ID = 3221

def recover_featured_images():
    print(f"--- {WP_SITE_URL} 포스트 이미지 설정 복구 시작 ---")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    
    # 최근 10개 포스트 조회
    params = {"per_page": 10, "status": "publish"}
    
    try:
        res = requests.get(endpoint, auth=auth, params=params, timeout=20, verify=False)
        if res.status_code == 200:
            posts = res.json()
            updated_count = 0
            
            for post in posts:
                p_id = post['id']
                p_media_id = post['featured_media']
                p_title = post['title']['rendered']
                
                # 특성 이미지가 기본 이미지(3221)인 경우만 처리
                if p_media_id == DEFAULT_IMAGE_ID:
                    print(f"\n[복구 대상 발견] ID: {p_id} | {p_title}")
                    print(f"  - 현재 특성 이미지 ID: {p_media_id} (기본 이미지)")
                    
                    # featured_media를 0으로 업데이트하여 FIFU가 작동하도록 함
                    update_payload = {"featured_media": 0}
                    up_res = requests.post(f"{endpoint}/{p_id}", auth=auth, json=update_payload, timeout=20, verify=False)
                    
                    if up_res.status_code == 200:
                        print(f"  -> 복구 완료: 특성 이미지 ID를 0으로 변경했습니다.")
                        updated_count += 1
                    else:
                        print(f"  -> 복구 실패: {up_res.status_code}")
                else:
                    print(f"[스킵] ID: {p_id} (이미 다른 이미지 ID({p_media_id})가 설정되어 있음)")
            
            print(f"\n--- 복구 완료! 총 {updated_count}개의 포스트가 수정되었습니다. ---")
        else:
            print(f"조회 실패: {res.status_code}")
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    recover_featured_images()
