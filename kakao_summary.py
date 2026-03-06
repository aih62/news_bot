import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
import html

# ================= CONFIGURATION =================
WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com")
KAKAO_TOKEN_JSON = os.getenv("KAKAO_TOKEN_JSON") # JSON string from GitHub Secrets
REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

def get_today_posts():
    """워드프레스에서 오늘 날짜의 최신 포스트 10개를 가져옵니다."""
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    params = {"per_page": 10, "status": "publish"}
    try:
        res = requests.get(endpoint, params=params, timeout=20)
        if res.status_code == 200:
            posts = res.json()
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_posts = []
            for post in posts:
                # 워드프레스 날짜 형식: "2026-03-06T07:00:00"
                if post['date'].startswith(today_str):
                    today_posts.append(post)
            return today_posts
    except Exception as e:
        print(f"포스트 가져오기 실패: {e}")
    return []

def format_message(posts):
    """포스트 리스트를 카카오톡 메시지 형식으로 변환합니다."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    msg = f"[정보보호 산업 동향 {today_str}]\n\n"
    
    for i, post in enumerate(posts, 1):
        title = html.unescape(post['title']['rendered'])
        content_html = post['content']['rendered']
        soup = BeautifulSoup(content_html, 'html.parser')
        
        # 서브 헤드라인 (h3) 추출
        sub_headline = soup.find('h3').get_text() if soup.find('h3') else "내용 요약"
        
        # 출처 추출 (p 태그 안의 텍스트)
        source_text = ""
        source_p = soup.find('p', string=lambda t: t and '출처:' in t)
        if not source_p:
            # 출처 형식이 <a> 태그를 포함한 경우 등 대비
            for p in soup.find_all('p'):
                if '출처:' in p.get_text():
                    source_text = p.get_text().replace("출처:", "").strip()
                    break
        else:
            source_text = source_p.get_text().replace("출처:", "").strip()
            
        link = post['link']
        
        msg += f"{i}. {title}\n"
        msg += f" - {sub_headline} [{source_text}]\n"
        msg += f" - [기사보기] {link}\n\n"
        
    return msg.strip()

def refresh_kakao_token():
    """리프레시 토큰을 사용하여 액세스 토큰을 갱신합니다."""
    if not KAKAO_TOKEN_JSON or not REST_API_KEY:
        return None
        
    try:
        tokens = json.loads(KAKAO_TOKEN_JSON)
        refresh_token = tokens.get("refresh_token")
        
        url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": REST_API_KEY,
            "refresh_token": refresh_token
        }
        
        res = requests.post(url, data=data)
        if res.status_code == 200:
            new_tokens = res.json()
            # 기존 리프레시 토큰이 유지되는 경우가 많으므로 병합
            if 'refresh_token' not in new_tokens:
                new_tokens['refresh_token'] = refresh_token
            print("카카오 토큰 갱신 성공!")
            return new_tokens
    except Exception as e:
        print(f"토큰 갱신 실패: {e}")
    return None

def send_kakao_memo(message):
    """카카오톡 '나에게 보내기' API를 호출합니다."""
    # 1. 먼저 토큰 갱신 시도
    new_tokens = refresh_kakao_token()
    if not new_tokens:
        print("토큰 갱신에 실패하여 기존 토큰을 사용합니다.")
        if not KAKAO_TOKEN_JSON: return False
        tokens = json.loads(KAKAO_TOKEN_JSON)
    else:
        tokens = new_tokens
        
    access_token = tokens.get("access_token")
    
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 텍스트 메시지 구성 (카카오톡 텍스트 컴포넌트 제약사항 준수)
    template = {
        "object_type": "text",
        "text": message,
        "link": {
            "web_url": WP_SITE_URL,
            "mobile_web_url": WP_SITE_URL
        },
        "button_title": "뉴스 센터 바로가기"
    }
    
    payload = {"template_object": json.dumps(template)}
    
    res = requests.post(url, headers=headers, data=payload)
    if res.status_code == 200:
        print("카카오톡 메시지 전송 성공!")
        return True
    else:
        print(f"전송 실패: {res.status_code}, {res.text}")
        return False

def main():
    posts = get_today_posts()
    if not posts:
        print("오늘 올라온 포스팅이 없습니다.")
        return
        
    message = format_message(posts)
    print("--- 생성된 메시지 ---")
    print(message)
    
    send_kakao_memo(message)

if __name__ == "__main__":
    main()
