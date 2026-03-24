import requests
import os
import re
import time
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import urllib3

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# .env 로드
load_dotenv()

# 설정 로드
WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "inhoe.an@gmail.com")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")

# Cloudinary 설정
if CLOUDINARY_URL:
    match = re.match(r"cloudinary://([^:]+):([^@]+)@(.+)", CLOUDINARY_URL)
    if match:
        api_key, api_secret, cloud_name = match.groups()
        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret, secure=True)
        print(f"Cloudinary 설정 완료: {cloud_name}")

def test_full_process():
    # 1. 테스트 이미지
    test_image_url = "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"
    
    # 2. Cloudinary 업로드
    print(f"Cloudinary 업로드 중: {test_image_url}")
    try:
        up_res = cloudinary.uploader.upload(test_image_url, folder="test_posts")
        cloudinary_url = up_res.get('secure_url')
        print(f"✅ Cloudinary 업로드 성공: {cloudinary_url}")
    except Exception as e:
        print(f"❌ Cloudinary 업로드 실패: {e}")
        return

    # 3. 워드프레스 포스팅 (FIFU 방식)
    print("워드프레스 포스팅 시도 중...")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    payload = {
        "title": f"Cloudinary 연동 테스트 포스트 ({int(time.time())})",
        "content": "이 포스트는 Cloudinary와 FIFU 연동을 테스트하기 위해 생성되었습니다.",
        "status": "publish",
        "featured_media": 0, # 중요: 0으로 설정하여 외부 URL 사용
        "meta": {
            "fifu_image_url": cloudinary_url,
            "fifu_image_alt": "Cloudinary Test Image"
        }
    }
    
    try:
        res = requests.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30, verify=False)
        if res.status_code in [200, 201]:
            print(f"✅ 포스팅 성공! URL: {res.json().get('link')}")
        else:
            print(f"❌ 포스팅 실패: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ 포스팅 예외: {e}")

if __name__ == "__main__":
    test_full_process()
