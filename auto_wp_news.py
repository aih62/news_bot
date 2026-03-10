import feedparser
import requests
import json
import re
from requests.auth import HTTPBasicAuth
import time
import os
import html
import urllib3
from urllib.parse import quote, urljoin
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# .env 로드
load_dotenv()

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= CONFIGURATION (환경 변수 설정) =================
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

# WP_SITE_URL 설정
WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com").rstrip("/")

# Cloudinary 설정
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")
if CLOUDINARY_URL:
    match = re.match(r"cloudinary://([^:]+):([^@]+)@(.+)", CLOUDINARY_URL)
    if match:
        api_key, api_secret, cloud_name = match.groups()
        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret, secure=True)
        print(f"Cloudinary 설정 로드 완료. (Cloud: {cloud_name})")

DEFAULT_IMAGE_URL = "http://ajken.mycafe24.com/wp-content/uploads/2026/03/thedigitalartist-security-4868167_1920.jpg"

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
session = requests.Session()
session.headers.update(COMMON_HEADERS)

def init_session():
    try:
        res = session.get(WP_SITE_URL, timeout=10, verify=False)
        print(f"세션 초기화 완료 (Status: {res.status_code})")
    except: pass

def get_recent_post_titles():
    """워드프레스에서 최근 포스팅된 10개의 제목을 가져옵니다."""
    print("최근 포스팅된 뉴스 제목 확인 중...")
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    params = {"per_page": 10, "status": "publish"}
    try:
        res = session.get(endpoint, auth=auth, params=params, timeout=20, verify=False)
        if res.status_code == 200:
            posts = res.json()
            titles = [html.unescape(post['title']['rendered']) for post in posts]
            print(f"  -> 최근 {len(titles)}개 포스트 제목 로드 완료.")
            return titles
    except Exception as e:
        print(f"최근 포스트 제목 가져오기 실패: {e}")
    return []

def get_image_from_webpage(url):
    """기사 원본 주소에서 이미지를 추출합니다."""
    if not url or not url.startswith("http"): return None
    try:
        res = requests.get(url, timeout=10, headers=COMMON_HEADERS, verify=False)
        if res.status_code == 200:
            html_content = res.text
            match = re.search(r'<meta [^>]*property=["\']og:image["\'] [^>]*content=["\']([^"\']+)["\']', html_content)
            if not match:
                match = re.search(r'<meta [^>]*content=["\']([^"\']+)["\'] [^>]*property=["\']og:image["\']', html_content)
            if not match:
                match = re.search(r'<meta [^>]*name=["\']twitter:image["\'] [^>]*content=["\']([^"\']+)["\']', html_content)
            if match:
                img_url = match.group(1)
                if img_url.startswith('/'): img_url = urljoin(url, img_url)
                return img_url
    except: pass
    return None

def get_rss_news():
    """feeds.json에서 뉴스 목록을 가져옵니다."""
    try:
        with open("feeds.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            direct_feeds = config.get("direct_feeds", {})
            search_categories = config.get("search_categories", {})
    except: return []

    all_entries = []
    seen_links = set()

    def extract_image(entry):
        if 'media_content' in entry and entry.media_content: return entry.media_content[0]['url']
        if 'media_thumbnail' in entry and entry.media_thumbnail: return entry.media_thumbnail[0]['url']
        content = getattr(entry, 'summary', '') + getattr(entry, 'description', '')
        img_match = re.search(r'<img [^>]*src="([^"]+)"', content)
        return img_match.group(1) if img_match else None

    for source_name, rss_url in direct_feeds.items():
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:15]:
                if entry.link not in seen_links:
                    all_entries.append({
                        "title": entry.title, "link": entry.link, "published": getattr(entry, 'published', time.ctime()),
                        "search_category": f"Expert_{source_name}", "rss_image": extract_image(entry)
                    })
                    seen_links.add(entry.link)
        except: pass
    return all_entries

def analyze_news_with_perplexity(news_list, recent_titles):
    """Perplexity AI를 사용하여 최상급 품질의 뉴스 분석을 수행합니다."""
    if not news_list: return []
    limited_news = news_list[:40]
    print(f"Perplexity AI 분석 중 ({len(limited_news)}개 기사 분석)...")
    
    headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}

    prompt = f"""
    너는 글로벌 보안 인텔리전스 기업의 '수석 분석가'이자 친절한 보안 에듀케이터야.
    한국 정부 정책 담당자가 빠르게 동향을 파악할 수 있도록 글로벌 보안 뉴스 상위 10개를 선정해 요약해줘.
    
    [독자 페르소나] 정책 담당자 (기술 용어는 쉽게 풀고, 정책적 시사점 강조)
    
    [작성 형식]
    - 제목: 최대 60자 이내의 전략적 헤드라인
    - 본문: <h3>서브헤드라인</h3>, <ul><li>요약내용</li></ul> (4-6개 항목, 각 120자 이상 풍부하게), <blockquote>전문가 코멘트</blockquote>, <p>출처</p>
    
    **중복 방지:** {json.dumps(recent_titles, ensure_ascii=False)} 제목과 유사한 사건 제외.
    
    결과는 순수 JSON 리스트 형식으로 응답해.
    대상 뉴스 리스트: {json.dumps(limited_news, ensure_ascii=False)}
    """

    data = {"model": "sonar", "messages": [{"role": "system", "content": "보안 뉴스 분석 전문가. JSON 응답 전용."}, {"role": "user", "content": prompt}]}

    try:
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=300)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            return json.loads(json_match.group()) if json_match else json.loads(content)
    except Exception as e: print(f"AI 분석 예외: {e}")
    return []

def upload_to_cloudinary(image_url):
    """이미지를 Cloudinary에 업로드하고 secure_url을 반환합니다."""
    if not CLOUDINARY_URL or not image_url or not image_url.startswith("http"): return None
    try:
        print(f"Cloudinary 업로드 시도: {image_url[:50]}...")
        response = cloudinary.uploader.upload(image_url, folder="news_bot")
        return response.get('secure_url')
    except Exception as e: print(f"Cloudinary 실패: {e}"); return None

def get_or_create_term(taxonomy, name):
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/{taxonomy}"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    try:
        res = session.get(endpoint, auth=auth, params={"search": name}, timeout=20, verify=False)
        if res.status_code == 200 and res.json(): return res.json()[0]['id']
        res = session.post(endpoint, auth=auth, json={"name": name}, timeout=20, verify=False)
        if res.status_code in [200, 201]: return res.json()['id']
    except: pass
    return None

def post_to_wordpress(news_data, original_news_list):
    """뉴스를 워드프레스에 포스팅합니다. (사용자 분석 기반 FIFU 최적화 버전)"""
    print(f"--- 포스팅 시도: {news_data['title']} ---")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    # 1. 이미지 URL 결정
    target_image = None
    source_url = news_data.get('source_url')
    for item in original_news_list:
        if item['link'] == source_url and item.get('rss_image'):
            target_image = item['rss_image']
            break
    if not target_image: target_image = get_image_from_webpage(source_url)
    if not target_image: target_image = news_data.get('image_url')

    # 2. Cloudinary 업로드 (카페24 용량 절약)
    final_image_url = upload_to_cloudinary(target_image) or target_image or DEFAULT_IMAGE_URL

    cat_id = get_or_create_term("categories", news_data.get('category', 'News'))
    tag_ids = [get_or_create_term("tags", t) for t in news_data.get('tags', [])]
    tag_ids = [tid for tid in tag_ids if tid]
    
    # 3. 포스팅 데이터 구성 (FIFU 연동 최적화)
    payload = {
        "title": news_data['title'],
        "content": news_data.get('content', '내용 없음'),
        "status": "publish",
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "featured_media": 0, # 중요: 0으로 설정하여 워드프레스 내부 미디어 무시
        "meta": {
            "fifu_image_url": final_image_url,
            "_fifu_image_url": final_image_url, # 숨겨진 메타 필드 추가
            "fifu_image_alt": news_data['title'][:50]
        }
    }
    
    try:
        res = session.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30, verify=False)
        if res.status_code in [200, 201]:
            print(f"발행 성공! {res.json().get('link')}")
        else: print(f"발행 실패: {res.status_code} - {res.text}")
    except Exception as e: print(f"포스팅 예외: {e}")

def main():
    if not all([PERPLEXITY_API_KEY, WP_USERNAME, WP_APP_PASSWORD]): return
    init_session()
    recent_titles = get_recent_post_titles()
    news_list = get_rss_news()
    selected_news = analyze_news_with_perplexity(news_list, recent_titles)
    if not selected_news: return
    for news in selected_news:
        post_to_wordpress(news, news_list)
        time.sleep(5)

if __name__ == "__main__":
    main()
