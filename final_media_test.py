
import requests
import os
import time
from requests.auth import HTTPBasicAuth

# 환경 변수 설정
USERNAME = "inhoe.an@gmail.com"
PASSWORD = "ISPe NJZf FCSb Qwh3 MPf2 ZPds"
SITE_URL = "https://ajken.mycafe24.com"

def test_media_upload():
    # 1. 이미지 준비
    test_image_url = "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"
    print(f"1. 이미지 다운로드: {test_image_url}")
    
    img_res = requests.get(test_image_url)
    if img_res.status_code != 200:
        print(f"다운로드 실패: {img_res.status_code}")
        return

    # 2. 워드프레스 미디어 라이브러리 업로드
    auth = HTTPBasicAuth(USERNAME, PASSWORD)
    filename = f"final_media_test_{int(time.time())}.png"
    
    print(f"2. 워드프레스 업로드 시도 (계정: {USERNAME})...")
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "image/png"
    }
    
    try:
        up_res = requests.post(
            f"{SITE_URL}/wp-json/wp/v2/media",
            auth=auth,
            headers=headers,
            data=img_res.content,
            timeout=30
        )
        
        if up_res.status_code in [200, 201]:
            media_id = up_res.json().get('id')
            print(f"성공! 생성된 Media ID: {media_id}")
            print(f"미디어 URL: {up_res.json().get('source_url')}")
            return media_id
        else:
            print(f"실패 (Status: {up_res.status_code}): {up_res.text}")
            return None
    except Exception as e:
        print(f"예외 발생: {e}")
        return None

if __name__ == "__main__":
    test_media_upload()
