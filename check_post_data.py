import requests
from requests.auth import HTTPBasicAuth
import os
import json
import html
from dotenv import load_dotenv

# .env 로드
load_dotenv()

WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "inhoe.an@gmail.com")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

def check_recent_posts():
    print(f"--- {WP_SITE_URL} 최근 포스트 데이터 조회 중 ---")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    # 최신 5개 포스트 조회
    params = {"per_page": 5, "status": "publish"}
    
    try:
        res = requests.get(endpoint, auth=auth, params=params, timeout=20)
        if res.status_code == 200:
            posts = res.json()
            for post in posts:
                p_id = post['id']
                p_date = post['date']
                p_media_id = post['featured_media']
                p_title = html.unescape(post['title']['rendered'])
                
                # 메타 데이터(FIFU URL 등) 확인
                # 참고: 기본적으로 meta는 API 응답에 포함되지 않을 수 있으므로 개별 조회 시도
                fifu_url = "N/A"
                if 'meta' in post:
                    fifu_url = post['meta'].get('fifu_image_url', 'N/A')
                else:
                    # 메타 정보만 따로 상세 조회
                    m_res = requests.get(f"{endpoint}/{p_id}", auth=auth, timeout=10)
                    if m_res.status_code == 200:
                        fifu_url = m_res.json().get('meta', {}).get('fifu_image_url', 'N/A')

                # 미디어 라이브러리에 업로드된 실제 이미지 URL 확인
                media_url = "N/A"
                if p_media_id > 0:
                    media_res = requests.get(f"{WP_SITE_URL}/wp-json/wp/v2/media/{p_media_id}", auth=auth, timeout=10)
                    if media_res.status_code == 200:
                        media_url = media_res.json().get('source_url', 'N/A')

                print(f"\n[ID: {p_id}] {p_title}")
                print(f"  - 발행일: {p_date}")
                print(f"  - 특성 이미지 ID (Featured Media ID): {p_media_id}")
                print(f"  - 실제 이미지 URL (Media Library): {media_url}")
                print(f"  - FIFU 외부 이미지 URL (Meta Field): {fifu_url}")
                
                # 불일치 여부 판단
                if p_media_id == 3221:
                    print("  ⚠️ 경고: 현재 기본 이미지(3221)가 설정되어 있습니다. (실제 이미지 업로드 실패 가능성)")
                elif str(p_media_id) == "0":
                    print("  ⚠️ 알림: 특성 이미지가 설정되지 않았습니다.")
        else:
            print(f"데이터 조회 실패: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_recent_posts()
