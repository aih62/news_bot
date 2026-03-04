import feedparser
import requests
import json
import re
from requests.auth import HTTPBasicAuth
import time
import os
from urllib.parse import quote

# ================= CONFIGURATION (환경 변수 설정) =================
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
WP_USERNAME = os.getenv("WP_USERNAME")
if not WP_USERNAME:
    WP_USERNAME = "inhoe.an@gmail.com" # 성공 확인된 계정명
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

# WP_SITE_URL이 비어있거나 None인 경우를 대비한 처리
WP_SITE_URL = os.getenv("WP_SITE_URL")
if not WP_SITE_URL:
    WP_SITE_URL = "https://ajken.mycafe24.com"
WP_SITE_URL = WP_SITE_URL.rstrip("/")

# 기본 이미지 URL (이미지가 없을 때 사용)
DEFAULT_IMAGE_URL = "http://ajken.mycafe24.com/wp-content/uploads/2026/03/thedigitalartist-security-4868167_1920.jpg"

def get_rss_news():
    """feeds.json에서 직접 RSS 피드와 검색 카테고리를 읽어와 최신 기사 목록을 가져옵니다."""
    print(f"현재 작업 디렉토리: {os.getcwd()}")
    print("feeds.json 로드 중...")
    try:
        with open("feeds.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            direct_feeds = config.get("direct_feeds", {})
            search_categories = config.get("search_categories", {})
    except Exception as e:
        print(f"feeds.json 로드 실패: {e}")
        return []

    all_entries = []
    seen_links = set()

    def extract_image(entry):
        """RSS 항목에서 실제 이미지 URL을 추출합니다."""
        # 1. media:content 또는 media:thumbnail 확인
        if 'media_content' in entry and entry.media_content:
            return entry.media_content[0]['url']
        if 'media_thumbnail' in entry and entry.media_thumbnail:
            return entry.media_thumbnail[0]['url']
        # 2. 본문(description/summary) 내 <img> 태그 확인
        content = getattr(entry, 'summary', '') + getattr(entry, 'description', '')
        img_match = re.search(r'<img [^>]*src="([^"]+)"', content)
        if img_match:
            return img_match.group(1)
        return None

    # 1. 보안 전문 매체 직접 RSS 파싱 (최신 실전 정보)
    for source_name, rss_url in direct_feeds.items():
        print(f"[{source_name}] 직접 RSS 수집 중...")
        try:
            feed = feedparser.parse(rss_url)
            count = 0
            for entry in feed.entries[:15]:
                if entry.link not in seen_links:
                    all_entries.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": getattr(entry, 'published', time.ctime()),
                        "search_category": f"Expert_{source_name}",
                        "rss_image": extract_image(entry)
                    })
                    seen_links.add(entry.link)
                    count += 1
            print(f"  -> {count}개 기사 발견")
        except Exception as e:
            print(f"  -> [{source_name}] 읽기 실패: {e}")

    # 2. 구글 뉴스 키워드 검색 (광범위한 검색)
    for category_name, keywords in search_categories.items():
        query = " OR ".join([f'"{k}"' if " " in k else k for k in keywords])
        encoded_query = quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
        
        print(f"[{category_name}] 구글 뉴스 검색 중...")
        try:
            feed = feedparser.parse(rss_url)
            count = 0
            for entry in feed.entries[:15]:
                if entry.link not in seen_links:
                    all_entries.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": getattr(entry, 'published', time.ctime()),
                        "search_category": category_name,
                        "rss_image": extract_image(entry)
                    })
                    seen_links.add(entry.link)
                    count += 1
            print(f"  -> {count}개 기사 발견")
        except Exception as e:
            print(f"  -> [{category_name}] 읽기 실패: {e}")
            
    print(f"총 {len(all_entries)}개의 고유 기사 수집 완료.")
    return all_entries

def analyze_news_with_perplexity(news_list):
    """Perplexity AI를 사용하여 뉴스 선정 및 분석을 수행합니다."""
    if not news_list:
        return []
        
    limited_news = news_list[:40]
    print(f"Perplexity AI 분석 중 ({len(news_list)}개 중 상위 {len(limited_news)}개 기사 분석)...")
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    너는 글로벌 보안 인텔리전스 기업의 '수석 분석가'이자 친절한 보안 에듀케이터야.
    다음 뉴스 리스트 중에서 글로벌 보안 뉴스 상위 10개를 선정해 JSON 리스트로 요약해줘.
    주의: 이미지 URL이 확실하지 않으면 "image_url" 필드를 비워둬.

    {json.dumps(limited_news, ensure_ascii=False)}
    """

    data = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "보안 뉴스 분석 전문가입니다. 반드시 JSON 형식으로만 답변합니다."},
            {"role": "user", "content": prompt}
        ]
    }

    for attempt in range(2):
        try:
            response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=300)
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
                return json.loads(json_match.group()) if json_match else json.loads(content)
        except Exception as e:
            print(f"AI 분석 중 예외: {e}")
    return []

# 공통 헤더
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
session = requests.Session()
session.headers.update(COMMON_HEADERS)

def init_session():
    try:
        res = session.get(WP_SITE_URL, timeout=10)
        print(f"세션 초기화 완료 (Status: {res.status_code})")
    except Exception as e:
        print(f"세션 초기화 실패: {e}")

def get_or_create_term(taxonomy, name):
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/{taxonomy}"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    try:
        res = session.get(endpoint, auth=auth, params={"search": name}, timeout=20)
        if res.status_code == 200:
            for term in res.json():
                if term['name'] == name: return term['id']
        res = session.post(endpoint, auth=auth, json={"name": name}, timeout=20)
        if res.status_code in [200, 201]: return res.json()['id']
    except: pass
    return None

def upload_media_from_url(image_url):
    """이미지를 워드프레스에 업로드하고 ID를 반환합니다."""
    if not image_url or not image_url.startswith("http"):
        return None
    print(f"이미지 업로드 시도: {image_url[:60]}...")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    try:
        img_res = session.get(image_url, timeout=20)
        if img_res.status_code != 200: return None
        content_type = img_res.headers.get('Content-Type', 'image/jpeg')
        ext = "png" if "png" in content_type else "jpg"
        filename = f"news_img_{int(time.time())}.{ext}"
        upload_headers = session.headers.copy()
        upload_headers.update({"Content-Disposition": f"attachment; filename={filename}", "Content-Type": content_type})
        up_res = session.post(f"{WP_SITE_URL}/wp-json/wp/v2/media", auth=auth, headers=upload_headers, data=img_res.content, timeout=30)
        if up_res.status_code in [200, 201]:
            return up_res.json().get('id')
    except Exception as e:
        print(f"업로드 중 예외: {e}")
    return None

def post_to_wordpress(news_data, original_news_list):
    """뉴스를 워드프레스에 포스팅합니다."""
    print(f"--- 포스팅 시도: {news_data['title']} ---")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    # 1. 실제 이미지 주소 결정 (RSS 원본 이미지 우선)
    target_image = None
    for item in original_news_list:
        if item['link'] == news_data.get('source_url') and item.get('rss_image'):
            target_image = item['rss_image']
            print(f"기사 원본에서 실제 이미지를 찾았습니다.")
            break
    
    if not target_image:
        target_image = news_data.get('image_url')

    # 2. 이미지 업로드 시도 (실패하거나 깨진 이미지면 기본 이미지 사용)
    media_id = upload_media_from_url(target_image)
    
    if not media_id:
        print("이미지 업로드 실패 또는 주소 없음. 기본 이미지를 사용합니다.")
        media_id = upload_media_from_url(DEFAULT_IMAGE_URL)

    cat_id = get_or_create_term("categories", news_data.get('category', 'News'))
    tag_ids = []
    for t in news_data.get('tags', []):
        tid = get_or_create_term("tags", t); 
        if tid: tag_ids.append(tid)
    
    # 포스팅 페이로드 (본문 강제 삽입 제거하여 중복 방지)
    payload = {
        "title": news_data['title'],
        "content": news_data['content'], # 이미지 태그 없는 순수 분석 내용
        "status": "publish",
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "featured_media": media_id if media_id else 0,
        "meta": {
            "fifu_image_url": target_image if target_image else DEFAULT_IMAGE_URL,
            "_featured_image_url": target_image if target_image else DEFAULT_IMAGE_URL
        }
    }
    
    try:
        res = session.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30)
        if res.status_code in [200, 201]:
            print(f"발행 성공! (ID: {res.json().get('id')})")
        else:
            print(f"발행 실패: {res.status_code}")
    except Exception as e:
        print(f"포스팅 예외: {e}")

def main():
    if not all([PERPLEXITY_API_KEY, WP_USERNAME, WP_APP_PASSWORD]):
        print("에러: 환경 변수 설정 누락")
        return
    init_session()
    news_list = get_rss_news()
    selected_news = analyze_news_with_perplexity(news_list)
    if not selected_news:
        print("선정된 뉴스가 없습니다.")
        return
    for news in selected_news:
        try:
            post_to_wordpress(news, news_list)
            print("다음 포스팅을 위해 5초 대기...")
            time.sleep(5)
        except Exception as e:
            print(f"처리 중 오류: {e}")

if __name__ == "__main__":
    main()
