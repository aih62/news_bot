import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def analyze_theme_classes():
    url = "https://ajken.mycafe24.com/microsoft-%ec%82%ac%ec%9d%b4%eb%b2%84-%ea%b3%b5%ea%b2%a9-%ec%a0%84-%ea%b3%bc%ec%a0%95%ec%97%90%ec%84%9c-ai-%ec%95%85%ec%9a%a9-%ea%b8%89%ec%a6%9d-%eb%b3%b4%ea%b3%a0-2/"
    try:
        res = requests.get(url, verify=False, timeout=20)
        html = res.text
        
        print("--- 테마 이미지 관련 클래스 분석 ---")
        keywords = ["featured-image", "post-thumbnail", "attachment-covernews", "single-post-image", "wp-post-image"]
        for kw in keywords:
            if kw in html:
                print(f"찾음: {kw}")
        
        # 실제 img 태그 주변의 class 확인을 위해 일부 추출
        start_idx = html.find("<img")
        if start_idx != -1:
            print("\n상단 이미지 태그 주변 코드:")
            print(html[start_idx:start_idx+300])
            
    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    analyze_theme_classes()
