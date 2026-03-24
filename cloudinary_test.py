import cloudinary
import cloudinary.uploader
import os
import re
from dotenv import load_dotenv

# 현재 파일 위치 기준으로 .env 로드
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Cloudinary 설정
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")

if not CLOUDINARY_URL:
    print("CLOUDINARY_URL이 .env에 설정되어 있지 않습니다.")
else:
    # URL에서 직접 정보 추출 (정규식 사용)
    # 형식: cloudinary://API_KEY:API_SECRET@CLOUD_NAME
    match = re.match(r"cloudinary://([^:]+):([^@]+)@(.+)", CLOUDINARY_URL)
    if match:
        api_key, api_secret, cloud_name = match.groups()
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        print("Cloudinary 정보가 명시적으로 설정되었습니다.")
    else:
        print("URL 형식이 올바르지 않습니다.")

def test_upload():
    test_image = "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"
    try:
        print(f"\n테스트 이미지 업로드 시도: {test_image}")
        response = cloudinary.uploader.upload(test_image, folder="test_folder")
        print("✅ 업로드 성공!")
        print(f"결과 URL: {response['secure_url']}")
        return True
    except Exception as e:
        print(f"❌ 업로드 실패: {e}")
        return False

if __name__ == "__main__":
    test_upload()
