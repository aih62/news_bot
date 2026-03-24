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

def test_content_embed():
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    # 기존에 성공했던 Cloudinary 이미지 주소 활용
    cloudinary_url = "https://res.cloudinary.com/djanrdmrg/image/upload/v1773129079/test_posts/sqwzm7ealmsjjaeygo87.png"
    
    print("본문 삽입 방식으로 이미지 출력 테스트 중...")
    
    # 본문 맨 앞에 이미지 태그 삽입
    img_tag = f'<img src="{cloudinary_url}" alt="News Image" style="width:100%; max-width:800px; height:auto; display:block; margin:0 auto 20px auto; border-radius:10px; shadow: 0 4px 8px rgba(0,0,0,0.1);">'
    content = img_tag + "<p>이 포스트는 이미지를 본문에 직접 삽입하여 출력을 보장하는 테스트입니다. 이미지는 외부(Cloudinary) 서버에서 불러오므로 카페24 용량을 사용하지 않습니다.</p>"
    
    payload = {
        "title": f"Content Embed Test ({int(time.time())})",
        "content": content,
        "status": "publish",
        "featured_media": PLACEHOLDER_ID # 목록용 기본 이미지
    }
    
    try:
        res = requests.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30, verify=False)
        if res.status_code in [200, 201]:
            print(f"✅ 포스팅 성공! URL: {res.json().get('link')}")
            print("사이트에서 게시글을 클릭해 본문에 구글 로고가 크게 나오는지 확인해 주세요.")
        else:
            print(f"❌ 실패: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    test_content_embed()
