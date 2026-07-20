import feedparser
import requests
import json
import re
from requests.auth import HTTPBasicAuth
import time
import calendar
import concurrent.futures
import os
import html
import urllib3
import io
from PIL import Image
from urllib.parse import quote, urljoin, urlparse
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= CONFIGURATION (환경 변수 설정) =================
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
WP_USERNAME = os.getenv("WP_USERNAME")
if not WP_USERNAME:
    WP_USERNAME = "inhoe.an@gmail.com"
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

# WP_SITE_URL 설정
WP_SITE_URL = os.getenv("WP_SITE_URL")
if not WP_SITE_URL:
    WP_SITE_URL = "https://ajken.mycafe24.com"
WP_SITE_URL = WP_SITE_URL.rstrip("/")

# 보장된 기본 이미지 ID (워드프레스 미디어 라이브러리 내 실제 ID)
GUARANTEED_MEDIA_ID = 5680 
DEFAULT_IMAGE_URL = "https://ajken.mycafe24.com/wp-content/uploads/2026/05/thedigitalartist-security.jpg"

# 공통 헤더
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
session = requests.Session()
session.headers.update(COMMON_HEADERS)

import asyncio
from playwright.sync_api import sync_playwright

def get_image_from_webpage_robustly(url):
    """Playwright를 사용하여 기사 원본 주소에서 이미지를 안정적으로 추출합니다."""
    if not url or not url.startswith("http"): return None
    print(f"  Playwright를 이용한 이미지 정밀 추출 시도: {url}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=COMMON_HEADERS["User-Agent"])
            page = context.new_page()
            try:
                # domcontentloaded만 기다려도 메타 태그는 대부분 로드됨
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                final_url = page.url
                html_content = page.content()
                
                # og:image 또는 twitter:image 추출
                match = re.search(r'<meta [^>]*property=["\']og:image["\'] [^>]*content=["\']([^"\']+)["\']', html_content)
                if not match:
                    match = re.search(r'<meta [^>]*content=["\']([^"\']+)["\'] [^>]*property=["\']og:image["\']', html_content)
                if not match:
                    match = re.search(r'<meta [^>]*name=["\']twitter:image["\'] [^>]*content=["\']([^"\']+)["\']', html_content)
                if not match:
                    match = re.search(r'<meta [^>]*content=["\']([^"\']+)["\'] [^>]*name=["\']twitter:image["\']', html_content)
                
                if match:
                    img_url = match.group(1)
                    img_url = html.unescape(img_url)
                    if img_url.startswith('/'): img_url = urljoin(final_url, img_url)
                    # 구글 뉴스 기본 아이콘 및 트래커 제외 (단, The Hacker News 등이 사용하는 blogger 제외)
                    if ("googleusercontent.com" in img_url and "blogger" not in img_url) or "feedburner.com" in img_url:
                        return None
                    return img_url
            except Exception as e:
                print(f"    Playwright 내부 오류: {e}")
            finally:
                browser.close()
    except Exception as e:
        print(f"    Playwright 시작 오류: {e}")
    return None

def resolve_google_url(url):
    """구글 뉴스 리다이렉트 URL을 실제 기사 URL로 변환합니다."""
    if "news.google.com" not in url: return url
    try:
        with requests.get(url, timeout=5, allow_redirects=True, headers=COMMON_HEADERS, stream=True) as res:
            return res.url
    except:
        return url

def init_session():
    try:
        res = session.get(WP_SITE_URL, timeout=10, verify=False)
        print(f"세션 초기화 완료 (Status: {res.status_code})")
    except: pass

def normalize_url(url):
    """URL을 중복 비교용으로 정규화합니다 (공백/프래그먼트 제거, 끝 슬래시 제거, 소문자화)."""
    if not url:
        return ""
    u = str(url).strip().split('#')[0].rstrip('/')
    return u.lower()


def get_recent_posts_info():
    """워드프레스에서 최근 포스팅된 글의 제목과 본문 내 출처 URL을 가져옵니다 (중복 방지용).

    제목은 매 실행마다 AI가 새로 생성하므로 식별자로 부적합합니다. 따라서 본문에 포함된
    원본 기사 URL(`<a href='...' target='_blank'>매체명</a>`)을 정규화하여 별도로 수집해,
    같은 기사가 다시 포스팅되는 것을 URL 기준으로 차단합니다.
    """
    print("최근 포스팅된 뉴스 제목/출처 확인 중...")
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    params = {"per_page": 30, "status": "publish"}  # 당일을 넘어선 교차 중복까지 비교
    titles, source_urls = [], set()
    try:
        res = session.get(endpoint, auth=auth, params=params, timeout=20, verify=False)
        if res.status_code == 200:
            posts = res.json()
            for post in posts:
                titles.append(html.unescape(post['title']['rendered']))
                content_html = post.get('content', {}).get('rendered', '') or ''
                for href in re.findall(r"href=['\"]([^'\"]+)['\"]", content_html):
                    if href.startswith("http"):
                        source_urls.add(normalize_url(href))
            print(f"  -> 최근 {len(titles)}개 포스트 로드 완료 (출처 URL {len(source_urls)}개 추출).")
            return titles, source_urls
    except Exception as e:
        print(f"최근 포스트 정보 가져오기 실패: {e}")
    return titles, source_urls

def get_image_from_webpage(url):
    """기사 원본 주소에서 og:image 또는 twitter:image 태그를 추출합니다."""
    if not url or not url.startswith("http"): return None
    try:
        # 타임아웃을 20초로 연장하고 리다이렉트를 허용함
        res = requests.get(url, timeout=20, headers=COMMON_HEADERS, verify=False, allow_redirects=True)
        if res.status_code == 200:
            html_content = res.text
            # og:image 추출 (더 유연한 정규식 사용)
            match = re.search(r'<meta [^>]*property=["\']og:image["\'] [^>]*content=["\']([^"\']+)["\']', html_content)
            if not match:
                match = re.search(r'<meta [^>]*content=["\']([^"\']+)["\'] [^>]*property=["\']og:image["\']', html_content)
            
            # twitter:image 추출
            if not match:
                match = re.search(r'<meta [^>]*name=["\']twitter:image["\'] [^>]*content=["\']([^"\']+)["\']', html_content)
            if not match:
                match = re.search(r'<meta [^>]*content=["\']([^"\']+)["\'] [^>]*name=["\']twitter:image["\']', html_content)
            
            # image_src (Link rel) 추출
            if not match:
                match = re.search(r'<link [^>]*rel=["\']image_src["\'] [^>]*href=["\']([^"\']+)["\']', html_content)

            if match:
                img_url = match.group(1)
                img_url = html.unescape(img_url)
                if img_url.startswith('/'): img_url = urljoin(url, img_url)
                return img_url
    except Exception as e:
        print(f"  -> 웹페이지 이미지 추출 중 오류 ({url[:30]}...): {e}")
    return None

def get_image_via_microlink(url):
    """Microlink API로 기사 대표 이미지를 추출합니다.

    BleepingComputer 등 Cloudflare로 봇을 차단하는 사이트는 requests/Playwright(헤드리스)로
    og:image를 가져올 수 없다. Microlink는 페이지를 실제로 렌더링해 대표 이미지를 반환하며,
    구글뉴스 RSS 리다이렉트 URL도 실제 기사로 해석해 이미지를 준다. 무인증 무료 티어 사용.
    """
    if not url or not url.startswith("http"):
        return None
    try:
        res = requests.get("https://api.microlink.io/", params={"url": url},
                           headers=COMMON_HEADERS, timeout=40, verify=False)
        if res.status_code == 200:
            data = res.json().get("data", {}) or {}
            img = (data.get("image") or {}).get("url")
            if img and img.startswith("http"):
                # 구글 기본 아이콘/피드 트래커는 제외 (blogger 이미지는 허용)
                if ("googleusercontent.com" in img and "blogger" not in img) or "feedburner.com" in img:
                    return None
                print(f"  -> Microlink 이미지 추출 성공: {img[:60]}...")
                return img
    except Exception as e:
        print(f"  -> Microlink 이미지 추출 실패: {e}")
    return None

def calculate_score(entry):
    score = 0
    title = entry['title'].lower()
    
    # 1. 전략 및 정책 영향도 가중치 (Overwhelming Priority)
    strategic_keywords = {
        'strategy': 40, 'policy': 40, 'regulation': 40, 'strategic': 35,
        'investment': 30, 'm&a': 35, 'acquisition': 30, 'merger': 30,
        'standard': 25, 'framework': 25, 'nist': 35, 'sec': 35, 'cisa': 35,
        'government': 20, 'national': 25, 'global': 20, 'market': 20,
        'ai safety': 45, 'ai governance': 40, 'quantum-safe': 35,
        'compliance': 25, 'directive': 25, 'legislation': 35,
        'mythos': 45, 'glasswing': 45, 'red teaming': 35,
        'agentic': 45, 'autonomous': 40, 'covert': 35, 'botnet': 30,
        'soho': 25, 'nsa': 30, 'advisory': 25, 'state-level': 30
    }
    
    # 2. 산업 리더 및 빅테크 가중치 (High Priority)
    tech_leaders = {
        'microsoft': 15, 'google': 15, 'apple': 15, 'palo alto': 15, 
        'crowdstrike': 15, 'openai': 20, 'anthropic': 25, 'nvidia': 20,
        'cisco': 10, 'amazon': 10, 'aws': 10, 'meta': 10
    }
    
    # 3. 기술적 세부 사항 가중치 (Negligible Priority)
    technical_keywords = {
        'vulnerability': 2, 'exploit': 2, 'malware': 2, 'ransomware': 2,
        'breach': 3, 'cyberattack': 3, 'zero-day': 4, 'cve': 1
    }

    for kw, points in strategic_keywords.items():
        if kw in title: score += points
    for kw, points in tech_leaders.items():
        if kw in title: score += points
    for kw, points in technical_keywords.items():
        if kw in title: score += points
    
    # 24시간 이내 기사라면 동일한 시의성 점수 부여 (중복 제거용)
    score += 10 # 24h freshness base score

    if "Expert_" in entry['search_category']:
        score += 5
        
    return score

def get_rss_news():
    """feeds.json에서 직접 RSS 피드와 검색 카테고리를 읽어와 최신 기사 목록을 가져옵니다 (최근 24시간 이내)."""
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
    
    # 시간 필터링 기준 (현재 시간으로부터 24시간 전)
    now = time.time()
    day_in_seconds = 24 * 60 * 60

    korean_media_blacklist = [
        "koreaherald.com", "koreatimes.co.kr", "koreatimes.com", "en.yna.co.kr", "yna.co.kr",
        "koreajoongangdaily.joins.com", "english.chosun.com", "pulsenews.co.kr", "kedglobal.com",
        "koreaittimes.com", "businesskorea.co.kr", "koreabizwire.com", "donga.com", "hani.co.kr",
        "kyunghyang.com", "maeil.co.kr", "joins.com", "etnews.com", "zdnet.co.kr", "boannews.com",
        "dailysecu.com", "ddaily.co.kr", "digitaltoday.co.kr", "zdnet.com", "korea.net", "arirang.com"
    ]
    korean_source_blacklist = [
        "보안뉴스", "데일리시큐", "전자신문", "디지털데일리", "ZDNet Korea", "아이뉴스24", "디지털타임스",
        "지디넷코리아", "지디넷", "연합뉴스", "뉴시스", "동아일보", "중앙일보", "조선일보", "매일경제", "한국경제",
        "한겨레", "경향신문", "KBS", "MBC", "SBS", "YTN", "JTBC"
    ]
    exclude_sites = " ".join([f"-site:{site}" for site in korean_media_blacklist])

    def extract_image(entry):
        # 1. 미디어 태그 탐색
        if 'media_content' in entry and entry.media_content: return entry.media_content[0]['url']
        if 'media_thumbnail' in entry and entry.media_thumbnail: return entry.media_thumbnail[0]['url']
        
        # 2. 본문(summary, description, content)에서 이미지 태그 탐색
        content = getattr(entry, 'summary', '') + getattr(entry, 'description', '')
        if 'content' in entry:
            for c in entry.content:
                content += c.value
        
        img_match = re.search(r'<img [^>]*src="([^"]+)"', content)
        if img_match:
            img_url = img_match.group(1)
            # 1x1 픽셀 추적 이미지 등 무시
            if "feedburner.com" in img_url and "/~" in img_url: return None
            return img_url
        return None

    # 직접 피드 수집
    for source_name, rss_url in direct_feeds.items():
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:20]:
                is_recent = False
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    if now - calendar.timegm(entry.published_parsed) < day_in_seconds:
                        is_recent = True
                
                # 직접 피드에서도 한국어 포함 기사 엄격 제외
                if is_recent and (re.search('[가-힣]', entry.title) or any(ks in entry.title for ks in korean_source_blacklist)):
                    is_recent = False
                
                # FeedBurner 원본 링크가 있으면 그것을 사용 (매칭 정확도 향상)
                actual_link = getattr(entry, 'feedburner_origlink', entry.link)
                
                # 블랙리스트 도메인 체크
                if is_recent:
                    link_lower = actual_link.lower()
                    if any(site in link_lower for site in korean_media_blacklist):
                        is_recent = False
                
                # 출처 이름 체크
                source_title = entry.source.get('title', '') if hasattr(entry, 'source') else ''
                if is_recent:
                    if any(ks in source_title for ks in korean_source_blacklist) or re.search('[가-힣]', source_title):
                        is_recent = False

                if is_recent and actual_link not in seen_links:
                    all_entries.append({
                        "title": entry.title,
                        "link": actual_link,
                        "published": getattr(entry, 'published', time.ctime()),
                        "search_category": f"Expert_{source_name}",
                        "rss_image": extract_image(entry)
                    })
                    seen_links.add(actual_link)
        except: pass

    # 구글 뉴스 검색
    for category_name, keywords in search_categories.items():
        query = " OR ".join([f'"{k}"' if " " in k else k for k in keywords])
        full_query = f"({query}) -site:co.kr -site:kr {exclude_sites} when:1d"
        rss_url = f"https://news.google.com/rss/search?q={quote(full_query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:15]:
                is_recent = True
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    if now - calendar.timegm(entry.published_parsed) > day_in_seconds:
                        is_recent = False
                
                # 제목에서 한국어 및 한국 매체명 체크
                if is_recent and (re.search('[가-힣]', entry.title) or any(ks in entry.title for ks in korean_source_blacklist)):
                    is_recent = False
                
                # 출처 이름 체크
                source_title = entry.source.get('title', '') if hasattr(entry, 'source') else ''
                if is_recent:
                    if any(ks in source_title for ks in korean_source_blacklist) or re.search('[가-힣]', source_title):
                        is_recent = False
                
                # 구글 리다이렉트 URL 해제 및 도메인 체크
                if is_recent:
                    actual_link = resolve_google_url(entry.link)
                    # URL 정규화: 쿼리 파라미터 제거 및 끝 슬래시 제거
                    actual_link = actual_link.split('?')[0].split('#')[0].rstrip('/')
                    
                    link_lower = actual_link.lower()
                    if any(site in link_lower for site in korean_media_blacklist):
                        is_recent = False
                    
                    if is_recent and actual_link not in seen_links:
                        all_entries.append({
                            "title": entry.title,
                            "link": actual_link,
                            "published": getattr(entry, 'published', time.ctime()),
                            "search_category": category_name,
                            "rss_image": extract_image(entry)
                        })
                        seen_links.add(actual_link)
        except: pass

    # 모든 기사에 대해 점수 계산
    for entry in all_entries:
        entry['score'] = calculate_score(entry)

    # 점수 순으로 정렬
    all_entries.sort(key=lambda x: x['score'], reverse=True)

    # 중복 기사 및 매체 쿼터 관리
    final_candidates = []
    source_counts = {}
    seen_keywords = [] # 중복 기사 방지용

    def is_duplicate(new_title):
        # 제목의 주요 명사구/단어 3개 이상이 겹치면 중복으로 간주 (간이 로직)
        words = set(re.findall(r'\w{4,}', new_title.lower())) # 4글자 이상 단어만 추출
        for existing_words in seen_keywords:
            if len(words.intersection(existing_words)) >= 3:
                return True
        return False

    for entry in all_entries:
        source = entry['search_category']
        
        # 매체별 최대 5개로 완화 (안정적인 10개 확보를 위함)
        if source_counts.get(source, 0) >= 5:
            continue
            
        # 중복 기사(내용이 겹치는 다른 매체 기사) 제외
        if is_duplicate(entry['title']):
            continue
        
        final_candidates.append(entry)
        source_counts[source] = source_counts.get(source, 0) + 1
        seen_keywords.append(set(re.findall(r'\w{4,}', entry['title'].lower())))
        
        if len(final_candidates) >= 40:
            break

    print(f"총 {len(all_entries)}개 수집 -> 중복 제거 및 가치 평가 후 {len(final_candidates)}개 후보 선정.")
    return final_candidates


def fix_truncated_json(json_str):
    """끊어진 JSON 문자열을 괄호 매칭을 기반으로 분석하여 미완성인 마지막 객체를 잘라내고 강제 완성합니다."""
    json_str = json_str.strip()
    if not json_str: return "[]"
    
    try:
        import json
        json.loads(json_str)
        return json_str
    except: pass
    
    stack = []
    in_string = False
    escaped = False
    last_valid_object_end = -1
    
    for i, char in enumerate(json_str):
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == '{':
                stack.append(('{', i))
            elif char == '}':
                if stack:
                    top_char, top_idx = stack.pop()
                    # 최상위 배열([)이 항상 스택에 남아있으므로, 객체가 완전히 닫혔을 때는
                    # 스택 길이가 0이 아니라 1(바깥쪽 배열만 남은 상태)이 된다.
                    if top_char == '{' and len(stack) == 1:
                        last_valid_object_end = i
            elif char == '[':
                stack.append(('[', i))
            elif char == ']':
                if stack:
                    top_char, top_idx = stack.pop()
    
    if last_valid_object_end != -1:
        repaired = json_str[:last_valid_object_end+1].strip()
        if repaired.endswith(','):
            repaired = repaired[:-1].strip()
        if not repaired.startswith('['):
            repaired = '[' + repaired
        repaired += ']'
        return repaired
        
    # 미완성 객체 마크다운 밖에서도 괄호 매칭 복구 (폴백)
    fixed_chars = []
    stack = []
    in_string = False
    escaped = False
    
    for char in json_str:
        fixed_chars.append(char)
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char in ('[', '{'):
                stack.append(char)
            elif char in (']', '}'):
                if stack:
                    top = stack[-1]
                    if (char == ']' and top == '[') or (char == '}' and top == '{'):
                        stack.pop()
    
    if in_string:
        fixed_chars.append('"')
        
    while stack:
        top = stack.pop()
        if top == '[':
            temp_str = "".join(fixed_chars).strip()
            if temp_str.endswith(','):
                fixed_chars = list(temp_str[:-1])
            fixed_chars.append(']')
        elif top == '{':
            temp_str = "".join(fixed_chars).strip()
            if temp_str.endswith(','):
                fixed_chars = list(temp_str[:-1])
            fixed_chars.append('}')
            
    return "".join(fixed_chars)

def repair_json_fields(json_str):
    """JSON 문자열 내 필드 값 내부의 이스케이프되지 않은 큰따옴표를 이스케이프 처리합니다."""
    import re
    cleaned = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
    
    def escape_inside(match):
        field_part = match.group(1)
        val_part = match.group(2)
        end_part = match.group(3)
        # 이스케이프되지 않은 큰따옴표를 찾아서 \"로 변환
        val_part_fixed = re.sub(r'(?<!\\)"', r'\"', val_part)
        return f'{field_part}"{val_part_fixed}"{end_part}'

    cleaned = re.sub(r'("title"\\s*:\\s*)"([\\s\\S]*?)"(\\s*,\\s*"content")', escape_inside, cleaned)
    cleaned = re.sub(r'("content"\\s*:\\s*)"([\\s\\S]*?)"(\\s*,\\s*"tags")', escape_inside, cleaned)
    cleaned = re.sub(r'("image_url"\\s*:\\s*)"([\\s\\S]*?)"(\\s*,\\s*"source_url")', escape_inside, cleaned)
    cleaned = re.sub(r'("source_url"\\s*:\\s*)"([\\s\\S]*?)"(\\s*\\})', escape_inside, cleaned)
    return cleaned


# ══════════════════════════════════════════════════════════════════════
#  Perplexity 2단계 파이프라인 (선정 → 기사별 본문 생성)
#   - 구조화 출력(json_schema)으로 API가 JSON 무결성을 보장 → 따옴표 깨짐 원천 차단
#   - 응답을 잘게 나눠 truncation(잘림) 원천 차단, 실패는 건별로 격리
# ══════════════════════════════════════════════════════════════════════
PPLX_ENDPOINT = "https://api.perplexity.ai/chat/completions"


def _pplx_chat(data, timeout=180):
    """Perplexity Chat Completions 호출 후 message content(str)를 반환한다."""
    headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}
    res = requests.post(PPLX_ENDPOINT, headers=headers, json=data, timeout=timeout)
    res.raise_for_status()
    return res.json()['choices'][0]['message']['content']


def _parse_lenient(content):
    """구조화 출력 응답 문자열을 JSON 객체로 파싱한다.
    기본 파싱 실패 시 json-repair로 복구, 그래도 실패하면 None을 반환한다."""
    if not content:
        return None
    s = content.strip()
    if "```json" in s:
        s = s.split("```json")[1].split("```")[0].strip()
    elif "```" in s:
        s = s.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        try:
            from json_repair import repair_json
            return repair_json(s, return_objects=True)
        except Exception:
            return None


# 도메인 → 표기용 매체명 (미등록 도메인은 2차 도메인 캐피털라이즈로 폴백)
_SOURCE_NAME_MAP = {
    "thehackernews.com": "The Hacker News",
    "cyberscoop.com": "CyberScoop",
    "axios.com": "Axios",
    "darkreading.com": "Dark Reading",
    "bleepingcomputer.com": "BleepingComputer",
    "bankinfosecurity.com": "BankInfoSecurity",
    "the-decoder.com": "The Decoder",
    "wired.com": "Wired",
    "reuters.com": "Reuters",
    "bloomberg.com": "Bloomberg",
    "techcrunch.com": "TechCrunch",
    "theregister.com": "The Register",
    "securityweek.com": "SecurityWeek",
    "therecord.media": "The Record",
    "arstechnica.com": "Ars Technica",
    "zdnet.com": "ZDNET",
    "venturebeat.com": "VentureBeat",
    "scmagazine.com": "SC Media",
    "helpnetsecurity.com": "Help Net Security",
    "infosecurity-magazine.com": "Infosecurity Magazine",
}


def _source_name_from_url(url):
    """URL에서 표기용 매체명을 추출한다(미등록 도메인은 2차 도메인 캐피털라이즈)."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return "출처"
    if host.startswith("www."):
        host = host[4:]
    if host in _SOURCE_NAME_MAP:
        return _SOURCE_NAME_MAP[host]
    parts = host.split(".")
    if len(parts) >= 2:
        return parts[-2].capitalize()
    return host or "출처"


_SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "selected": {"type": "array", "items": {"type": "integer"}}
    },
    "required": ["selected"],
}


def select_top_news(news_list, recent_titles, want=10):
    """[1단계] 후보 중 상위 want개의 index만 구조화 출력으로 선정한다.
    응답이 매우 작아 잘림/깨짐이 없다. 선정 실패 시 점수순 상위 want개로 폴백한다."""
    indexed = [
        {"index": i, "title": n.get("title", ""), "source": n.get("search_category", "")}
        for i, n in enumerate(news_list)
    ]
    prompt = f"""당신은 글로벌 보안 인텔리전스 기업의 '수석 분석가'입니다.
아래 후보 뉴스에서 한국 정부 보안 정책 담당자에게 가장 가치 있는 상위 {want}개를 선정하십시오.

[선정 가중치]
1. 기업 전략·시장 지배력(M&A, 플랫폼 통합, 기술 로드맵): Palo Alto Networks, CrowdStrike, Microsoft, Zscaler, Google Cloud, Anthropic/OpenAI 등 [40%]
2. AI 보안·미래 기술(에이전틱 AI 위협, AI 안전성 프레임워크, 양자내성암호, 클라우드 네이티브 보안) [25%]
3. 글로벌 규제·정책(미국 사이버 EO, EU AI Act, 각국 AI 안전 법안, 국제 표준) [20%]
4. 파급력·시급성(대규모 취약점, 공급망 공격에 대한 즉각적 경고) [15%]

[제외/중복 규칙]
- 아래 '이미 게시된 제목'과 동일한 사건은 제외: {json.dumps(recent_titles, ensure_ascii=False)}
- 동일 사건을 다룬 후보가 여럿이면 정보가치가 가장 높은 1개만 선정하여, 결과적으로 서로 다른 {want}개 사건이 되도록 구성할 것.
- 한국 매체/한국어 기사는 제외(사전 필터되었으나 재확인).

선정한 후보의 index 번호 {want}개를 정수 배열로만 반환하십시오.

후보 목록:
{json.dumps(indexed, ensure_ascii=False)}
"""
    data = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "보안 뉴스 큐레이션 전문가입니다. 반드시 지정된 JSON 스키마로만 답합니다."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1000,
        "response_format": {"type": "json_schema", "json_schema": {"schema": _SELECTION_SCHEMA}},
    }
    selected = []
    try:
        parsed = _parse_lenient(_pplx_chat(data, timeout=120))
        raw = parsed.get("selected", []) if isinstance(parsed, dict) else parsed
        seen = set()
        for idx in (raw or []):
            try:
                i = int(idx)
            except (TypeError, ValueError):
                continue
            if 0 <= i < len(news_list) and i not in seen:
                seen.add(i)
                selected.append(news_list[i])
            if len(selected) >= want:
                break
    except Exception as e:
        print(f"  -> 선정 단계 오류: {e}")

    if not selected:
        print(f"  -> 선정 실패 → 점수순 상위 {want}개로 폴백합니다.")
        selected = news_list[:want]
    else:
        print(f"  -> {len(selected)}개 기사 선정 완료.")
    return selected


# 본문 작성 가이드라인 (기존 프롬프트 품질 기준을 그대로 계승)
_WRITING_GUIDE = """[작성 가이드라인 - 엄격 준수]
- [제목]: 실제 뉴스 헤드라인처럼 자연스럽고 임팩트 있는 전략적 제목(60자 이내).
  - [종결 방식 — 최우선 규칙]
    - (기본) 제목은 반드시 명사/명사형(체언)으로 종결. 예: ~확보, ~전환, ~돌입, ~착수, ~공개, ~노출, ~비상, ~격화, ~예고.
    - (허용) 부득이한 경우에만 현재형 동사 종결('~한다', '~밝혀', '~드러나', '~뒤흔들어')을 사용.
    - [절대 금지] '~함', '~됨', '~하였음', '~라고 함' 등 개조식 보고서체 종결. 헤드라인이 아니라 회의록처럼 읽히므로 절대 사용 금지.
  - 명사 나열 금지: 딱딱한 명사구 나열을 피하고 주체와 핵심 액션을 문장처럼 배치.
  - 핵심 정보 전면 배치: 사건의 주체(기업/기관)와 핵심 액션을 제목 앞부분에.
  - 인용부호 강조: 핵심 키워드·제품명·발언은 작은따옴표('')로 강조. (예: 팔로알토네트웍스 'PAN-OS' 치명적 결함 노출)
  - 말줄임표 구조화: "[핵심 사실]… [파장/부연]" 형태로 말줄임표(…)를 적극 활용. (예: GPT-5.5·Mythos, 자율 해킹 '인간 전문가급' 도달… 공격·방어 균형 붕괴)
- [서브 헤드라인]: 파급효과 중심의 한 문장 요약(<h3> 사용).
- [핵심 내용 요약]: <ul><li> 구조 사용.
  - [다각적 분석 체계]: 반드시 정확히 5개의 <li> 항목을 다음 비중으로 구성.
    - ① 핵심 사건/기술 개요(2개): 가장 핵심적인 사건·기술 메커니즘·발표 실체를 육하원칙 기반으로 충실히 서술.
    - ② 구체적 데이터 및 근거(1개): 기사에 언급된 수치(%), 금액($), 버전, 공격 규모 등 정량 데이터를 반드시 포함.
    - ③ 전략적 배경 및 파급효과(2개): 배경과 산업계/정책 영향을 심층 분석.
  - [정보 밀도 — 필수]: 각 <li>는 120자 내외(100~140자, 최대 150자 — 절대 초과 금지)로 간결하게 작성. 1~2문장으로 압축하되, 반드시 구체적 팩트(고유명사·기술명·표준·수치·버전 등)를 1개 이상 담아 짧아도 정보가 분명하게 할 것. 길이를 채우려 배경을 늘어놓지 말 것.
  - [인과관계 서술]: "[실제 발생한 사건/기술 상세] -> [변화된 현상] -> [전략적/정책적 의미]" 순으로 완결.
  - [추상 표현 지양]: '혁신적', '상당한 영향', '기대됨' 대신 구체적 메커니즘·정책 근거로 서술.
  - 모든 문장은 '~다', '~하다', '~이다' 등 격식 있는 서술형 어미로 종결.
  - 출처 번호([1], [web:1] 등) 및 인용 표시는 절대 포함하지 말 것.
- [전문가 코멘트]: <blockquote> 사용. 정책 담당자를 위한 행동 권고를 포함해 100자 내외.
- [주요 용어 설명]: 전문가 코멘트 아래에 별도의 <p>로 구성. 형식: <strong>주요 용어:</strong> 용어(의미), 용어(의미)
- [HTML 태그 속성값]: 반드시 작은따옴표(')를 사용."""


_CONTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "content": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "content", "tags"],
}


def generate_article(candidate):
    """[2단계] 선정된 기사 1건에 대해 제목/HTML본문/태그를 구조화 출력으로 생성한다.
    응답이 작아 잘림이 없고, 한 건이 실패해도 나머지 기사에는 영향이 없다(장애 격리)."""
    src_url = candidate.get("link", "")
    prompt = f"""당신은 글로벌 보안 인텔리전스 기업의 '수석 분석가'이자 복잡한 기술 이슈를 정책적 가치로 전환하는 '보안 에듀케이터'입니다.
아래 기사를 웹에서 조사하여, 한국 정부 보안 정책 담당자가 즉각적 의사결정에 활용할 수 있는 분석을 작성하십시오.

[독자 페르소나: 한국 정부 정책 담당자]
- 기술 디테일보다 "이 변화가 한국 보안 산업 육성과 국가 안보에 어떤 기회·위기인가"를 파악하고자 함.
- 비전문가도 이해하도록 IT 전문 용어는 정책적 의미로 치환해 서술.

{_WRITING_GUIDE}

[대상 기사]
- 제목: {candidate.get('title','')}
- 출처 URL: {src_url}

[간결·고밀도 지침 — 매우 중요]
- 각 불릿은 120자 내외(최대 150자)로 짧게 쓰되, 반드시 구체적 팩트(고유명사·제품·기관·수치·버전 등)를 1개 이상 담아 정보 밀도를 유지하십시오.
- 짧은 길이가 곧 빈약함은 아닙니다. 막연한 표현·중복 설명·불필요한 배경 나열을 제거하고 핵심 사실만 압축하십시오.
- 웹 검색 정보가 부족하면 도메인 지식으로 핵심 사실을 보완하되, 길이를 억지로 늘리지 말고 간결함을 유지하십시오.
- 독자는 짧은 시간에 스캔하듯 읽습니다. 한 불릿이 150자를 넘기면 반드시 더 짧게 다듬으십시오.

아래 세 필드를 생성하십시오.
- title: 위 가이드라인을 따른 전략적 한국어 헤드라인(60자 이내).
- content: <h3>서브헤드라인</h3><ul><li>…5개, 각 120자 내외…</li></ul><blockquote>전문가 코멘트</blockquote><p><strong>주요 용어:</strong> 용어(의미), 용어(의미)</p> 형식의 HTML 문자열. **출처(<a>) 링크 줄은 넣지 마십시오(시스템이 자동으로 추가합니다).**
- tags: 핵심 키워드 5개.
"""
    data = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "보안 뉴스 분석 전문가입니다. 반드시 지정된 JSON 스키마로만 답합니다."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 4000,
        "response_format": {"type": "json_schema", "json_schema": {"schema": _CONTENT_SCHEMA}},
    }
    parsed = _parse_lenient(_pplx_chat(data, timeout=180))
    if not isinstance(parsed, dict) or not parsed.get("title") or not parsed.get("content"):
        raise ValueError("본문 생성 결과가 유효하지 않음")
    title = str(parsed["title"]).strip()
    body = str(parsed["content"]).strip()
    tags = [str(t).strip() for t in (parsed.get("tags") or []) if str(t).strip()][:5]
    # 출처 줄은 정확한 URL로 프로그램에서 부착(모델의 URL 환각 차단)
    src_name = _source_name_from_url(src_url)
    body += f"<p>출처: <a href='{src_url}' target='_blank'>{src_name}</a></p>"
    return {
        "title": title,
        "content": body,
        "tags": tags,
        "image_url": candidate.get("rss_image") or "",
        "source_url": src_url,
    }


def analyze_news_with_perplexity(news_list, recent_titles):
    """[리팩터링] 2단계 파이프라인으로 최상급 품질·고신뢰 뉴스 분석을 수행한다.
      1단계 select_top_news : 상위 10개 선정(작은 구조화 출력 → 잘림/깨짐 없음)
      2단계 generate_article: 기사별 본문 생성(작은 응답 → 잘림 없음, 실패는 건별 격리)
    구조화 출력(json_schema)으로 JSON 무결성을 API가 보장한다."""
    if not news_list:
        return []
    limited_news = news_list[:40]
    print(f"Perplexity AI 분석 중 ({len(limited_news)}개 후보)...")

    selected = select_top_news(limited_news, recent_titles, want=10)
    total = len(selected)

    # 2단계는 서로 독립적인 호출이므로 병렬 실행(rate limit 고려 워커 4개).
    #  - 순서 보존: 인덱스로 결과를 슬롯에 채운 뒤 성공분만 순서대로 수집
    #  - 장애 격리: 한 건 예외는 해당 슬롯만 None 처리하고 나머지는 정상 진행
    def _worker(idx, cand):
        return idx, generate_article(cand)

    slots = [None] * total
    max_workers = min(4, total) or 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_worker, i, c): (i, c) for i, c in enumerate(selected)}
        done = 0
        for fut in concurrent.futures.as_completed(futures):
            i, cand = futures[fut]
            done += 1
            label = cand.get("title", "")[:40]
            try:
                _, article = fut.result()
                slots[i] = article
                print(f"  -> [{done}/{total}] 본문 생성 완료: {article['title'][:30]}")
            except Exception as e:
                print(f"  -> [{done}/{total}] 본문 생성 실패(건너뜀): {label} ({e})")

    results = [a for a in slots if a]
    print(f"최종 {len(results)}개 기사 생성 완료.")
    return results


def _legacy_analyze_unused(news_list, recent_titles):
    """[비활성 · 참고용 보존] 기존 단일 호출 분석 로직. 현재 호출되지 않음."""
    if not news_list: return []
    limited_news = news_list[:40]
    print(f"Perplexity AI 분석 중 ({len(limited_news)}개 기사 분석)...")
    
    headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}

    prompt = f"""
    당신은 글로벌 보안 인텔리전스 기업의 '수석 분석가'이자, 복잡한 기술 이슈를 정책적 가치로 전환하는 '보안 에듀케이터'입니다.
    다음 뉴스 리스트에서 **글로벌 보안 뉴스 상위 10개**를 선정하여, 한국 정부 보안 정책 담당자가 즉각적인 의사결정 참고자료로 활용할 수 있도록 요약 및 분석하십시오.

    **[핵심 분석 타겟: 선정 시 가중치 부여]**
    1. **빅테크 및 보안 리딩 기업(Top-Tier):** Palo Alto Networks(플랫폼화), CrowdStrike(EDR/XDR 주도권), Microsoft(SFI 보안 이니셔티브), Zscaler, Google Cloud(Mandiant), Anthropic/OpenAI(AI 보안 및 안전)의 전략적 행보.
    2. **AI 및 차세대 위협:** 에이전틱 AI(Agentic AI)의 자율적 취약점 탐지 및 공격 체계, AI 안전성 프레임워크(Anthropic의 Mythos 등), 생성형 AI 기반 사이버 공격 및 방어 전략.
    3. **국가 안보 및 지능형 인프라 위협:** 국가 배후 해킹 그룹의 은밀한 네트워크(Covert Networks), SOHO 라우터 기반 봇넷(Volt Typhoon 등), 글로벌 공급망 보안 표준 및 규제.
    4. **글로벌 규제 및 정책:** 미국의 사이버 보안 행정명령(EO), EU AI Act 이행, 미국 각 주 정부 단위의 최신 AI 안전 법안(Hawaii, Alabama 등) 및 국제적 규범 변화.

    **※ 핵심 지침: 반드시 아래 뉴스 리스트에서 정확히 10개를 선정하여 JSON 배열을 완성해야 합니다. 1~2개만 선정하고 멈추지 말고, 반드시 10개의 아이템이 모두 포함된 전체 결과를 출력하십시오.**

    **※ 중복 및 필터링 주의사항:**
    - 다음 리스트에 포함된 제목과 완전히 동일한 뉴스만 제외할 것 (유사한 주제라도 다른 관점이면 포함 가능): {json.dumps(recent_titles, ensure_ascii=False)}
    - 완전히 동일한 주제나 사건을 다루는 기사가 여러 개일 경우, 그 중 가장 정보 가치가 높은 1개만 결과에 포함시켜 중복을 피하고, 결과적으로 서로 다른 사건을 다루는 10개의 뉴스가 되도록 구성할 것.
    - **한국 국내 매체(보안뉴스, 데일리시큐, 전자신문, 지디넷코리아 등 모든 한국 매체)는 보도 내용과 상관없이 무조건 선정에서 제외할 것.**
    - **분석 시 추가적인 인터넷 검색을 통해 한국어 기사를 수집하거나 포함하지 말고, 철저히 글로벌(해외) 동향과 국제 규제 위주로만 선정할 것.**
    - **모든 기사의 출처는 반드시 영문 매체(예: Reuters, Bloomberg, TechCrunch, Wired, The Hacker News 등)여야 함.**
    - '글로벌 동향'과 '한국 정책에 미칠 영향'에만 집중할 것.

    **[선정 기준 및 가중치]**
    1. 기업 전략 및 시장 지배력 [40%]: M&A, 플랫폼 통합 전략, 기술 로드맵 변화.
    2. AI 보안 및 미래 기술 [25%]: AI 안전성 가이드라인, 양자 내성 암호, 클라우드 네이티브 보안.
    3. 글로벌 규제 및 정책 [20%]: 주요국의 법제화 및 국제 표준화 동향.
    4. 파급력 및 시급성 [15%]: 대규모 취약점 및 공급망 공격에 대한 즉각적 경고.

    **[독자 페르소나: 한국 정부 정책 담당자]**
    - 기술적 디테일보다는 "이 변화가 한국 보안 산업 육성과 국가 안보에 어떤 기회와 위기인가?"를 파악하고자 함.
    - 비전문가도 이해할 수 있도록 IT 전문 용어는 정책적 의미로 치환하여 서술할 것.

    **[작성 가이드라인 - 엄격 준수]**
    - **[제목]**: **실제 뉴스 헤드라인처럼 자연스럽고 임팩트 있는 전략적 제목 (60자 이내).**
      - **[종결 방식 — 최우선 규칙]**:
        - (기본) 제목은 반드시 **명사/명사형(체언)으로 종결**할 것. 예: ~확보, ~전환, ~돌입, ~착수, ~공개, ~노출, ~비상, ~격화, ~예고.
        - (허용) 부득이한 경우에만 **현재형 동사 종결**('~한다', '~밝혀', '~드러나', '~뒤흔들어')을 사용할 것.
        - **[절대 금지] '~함', '~됨', '~하였음', '~라고 함' 등 개조식 보고서체 종결.** 헤드라인이 아니라 회의록처럼 읽히므로 절대 사용하지 말 것.
      - **명사 나열 금지:** "A의 B에 따른 C의 D..." 처럼 딱딱한 명사구 나열을 피하고, 주체와 핵심 액션을 문장처럼 배치할 것.
      - **핵심 정보 전면 배치:** 사건의 주체(기업/기관)와 핵심 액션을 제목 앞부분에 둘 것.
      - **인용부호 강조:** 핵심 키워드·제품명·발언은 작은따옴표('')로 강조할 것. (예: 팔로알토네트웍스 'PAN-OS' 치명적 결함 노출)
      - **말줄임표 구조화:** "[핵심 사실]… [파장/부연]" 형태로 말줄임표(…)를 적극 활용해 리듬을 줄 것. (예: GPT-5.5·Mythos, 자율 해킹 '인간 전문가급' 도달… 공격·방어 균형 붕괴)
    - **[서브 헤드라인]**: 파급효과 중심의 한 문장 요약 (`<h3>` 사용).
    - **[핵심 내용 요약]**: `<ul><li>` 구조 사용.
      - **[다각적 분석 체계]**: 4개에서 5개의 `<li>` 항목을 다음과 같은 비중으로 구성하여 정보와 분석의 균형을 맞출 것:
        - **① 핵심 사건/기술 개요 (2개 항목):** 해당 뉴스의 가장 핵심적인 사건, 기술적 메커니즘, 발표의 실체를 육하원칙에 기반하여 간결히 요약할 것.
        - **② 구체적 데이터 및 근거 (1개 항목):** 기사에서 언급된 수치(%), 금액($), 버전, 공격 규모 등 정량적 데이터를 반드시 포함할 것.
        - **③ 전략적 배경 및 파급효과 (1~2개 항목):** 해당 사건이 발생한 배경과 산업계/정책에 미칠 영향을 분석할 것.
      - **[정보 밀도]**: 각 `<li>` 항목은 **100자 내외**로 간결하게 작성할 것. 문장 내에 기사에서 언급된 **고유 명사(기업, 기술명, 표준 등)를 2개 이상 포함**하여 팩트 중심의 전문성을 유지하되, 지나치게 길거나 만연한 문장은 피하고 핵심만 압축할 것.
      - **[구체적 인과관계 서술]**: **"[실제 발생한 사건/기술적 상세 내용] -> [이로 인해 변화된 현상] -> [전략적/정책적 의미]"** 순서로 문장이 정교하게 완결되도록 작성할 것.
      - **[추상적 표현 지양]**: '혁신적', '상당한 영향', '기대됨' 등 주관적 형용사 대신, 구체적인 기술적 메커니즘이나 정책적 근거를 바탕으로 서술할 것.
      - 모든 문장은 **'~다', '~하다', '~이다'와 같은 격식 있는 서술형 어미**로 끝맺음할 것.
      - 출처 번호([1], [web:1] 등) 및 인용 표시는 절대 포함하지 말 것.
    - **[전문가 코멘트]**: `<blockquote>` 사용. 정책 담당자를 위한 행동 권고를 포함하여 100자 내외로 작성할 것.
    - **[주요 용어 설명]**: 전문가 코멘트 아래, 출처 바로 위에 별도의 `<p>` 태그로 구성. (형식: `<strong>주요 용어:</strong> 용어(의미), 용어(의미)`)

    **[작성 예시]**
    <h3>NIST, 양자 내성 암호 표준 공식 승인… '국가 안보 암호 체계' 전면 전환 예고</h3>
    <ul>
      <li>미 국립표준기술연구소(NIST)는 양자 컴퓨터의 '쇼어 알고리즘' 공격을 무력화할 격자 기반 암호 ML-KEM 등 3종을 최종 표준으로 승인하고 연방 기관의 전환 가이드라인을 발표하였습니다.</li>
      <li>이는 양자 컴퓨팅이 기존 RSA·ECC 암호 체계를 무력화할 수 있다는 위협에 대응한 조치로, 글로벌 IT 공급망의 보안 표준을 상향 평준화시킬 전망입니다.</li>
      <li>(이하 생략 - 실제 작성 시에는 4~5개의 불렛포인트를 100자 내외로 작성할 것)</li>
    </ul>
    <blockquote>이번 사건은 보안이 단순한 기술적 보완재를 넘어 국가의 디지털 주권을 지키는 핵심 생존 요건이 되었음을 시사하며, 한국 정부는 국내 수출 기업의 경쟁력 확보를 위해 국제 표준과의 정합성 확보에 박차를 가해야 합니다.</blockquote>
    <p><strong>주요 용어:</strong> 양자 내성 암호(양자 컴퓨터의 강력한 연산 공격에도 견딜 수 있도록 설계된 차세대 암호 체계), NIST(미국 표준 기술 연구소로 글로벌 IT 표준을 주도하는 기관)</p>
    <p>출처: <a href='URL' target='_blank'>매체명</a></p>

    **[결과물 형식]**
    아래 JSON 리스트 형식으로만 출력하십시오 (설명 생략).
    - **JSON 무결성**: 모든 문자열 값(title, content 등) 내부에 큰따옴표(")가 포함될 경우, 반드시 역슬래시로 이스케이프(\") 하거나 작은따옴표(')로 대체하십시오. 특히 HTML 태그 내 속성값은 반드시 작은따옴표(')를 사용하십시오.
    [
      {{
        "title": "명사형으로 종결하는 전략적 제목 ('~함/~됨' 금지, 말줄임표(…) 활용)",
        "content": "<h3>서브 헤드라인</h3><ul><li>간결한 문장 1(100자 내외)</li><li>간결한 문장 2(100자 내외)</li>...(총 4~5개)</ul><blockquote>전문가 코멘트</blockquote><p><strong>주요 용어:</strong> 용어(의미), 용어(의미)</p><p>출처: <a href='URL' target='_blank'>매체명</a></p>",
        "tags": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
        "image_url": "URL",
        "source_url": "URL"
      }}
    ]

    대상 뉴스 리스트:
    {json.dumps(limited_news, ensure_ascii=False)}
    """

    data = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "보안 뉴스 분석 전문가입니다. 반드시 JSON 형식으로만 답변하며, 문자열 내의 큰따옴표는 반드시 이스케이프 처리합니다."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 20000
    }

    try:
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=300)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print(f"  -> Perplexity 응답 길이: {len(content)}자")
            
            # JSON 리스트 형태 추출 시도 (Markdown 코드 블록 기호 제거 및 유연한 추출)
            json_str = content.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            # 리스트 대괄호 [ ] 사이의 내용만 추출
            start_idx = json_str.find('[')
            end_idx = json_str.rfind(']')
            if start_idx != -1 and end_idx != -1:
                json_str = json_str[start_idx:end_idx+1]

            try:
                return json.loads(json_str)
            except json.JSONDecodeError as je:
                print(f"JSON 기본 파싱 실패 ({je}), 정제 후 재시도 중...")

                # rfind(']')로 잘라낸 json_str은 응답이 truncate/중간 손상된 경우 객체 중간에서
                # 잘려 복구를 방해하므로, 원본 응답의 첫 '[' 이후 전체를 복구 대상으로 삼는다.
                bracket_start = content.find('[')
                recover_target = content[bracket_start:] if bracket_start != -1 else json_str

                # [1순위] json-repair 라이브러리로 malformed JSON 복구.
                #  잘림, 이스케이프되지 않은 큰따옴표, trailing comma 등 LLM 응답의
                #  다양한 손상 유형을 폭넓게 처리한다.
                try:
                    from json_repair import repair_json
                    repaired = repair_json(recover_target, return_objects=True)
                    if isinstance(repaired, list):
                        # source_url은 중복 제거·이미지 추출에 필수이므로, 이를 갖춘 항목만 채택해
                        # 잘려 완성되지 못한 마지막 항목 등을 안전하게 제외한다.
                        valid = [it for it in repaired
                                 if isinstance(it, dict) and it.get('title')
                                 and it.get('content') and it.get('source_url')]
                        if valid:
                            print(f"  -> json-repair 복구 성공 ({len(valid)}/{len(repaired)}개 유효 항목).")
                            return valid
                except Exception as e_lib:
                    print(f"  -> json-repair 복구 실패: {e_lib}")

                # [2순위] 자체 복구 로직 (라이브러리 미설치 등 폴백)
                try:
                    repaired_json = fix_truncated_json(recover_target)
                    repaired_json = repair_json_fields(repaired_json)
                    return json.loads(repaired_json)
                except Exception as e2:
                    print(f"최종 파싱 실패. 응답 길이: {len(content)}")
                    with open("debug_perplexity_error.txt", "w", encoding="utf-8") as df:
                        df.write(content)
                    print(f"디버그 정보가 debug_perplexity_error.txt에 저장되었습니다.")
                    return []
        else:
            print(f"API 호출 실패 (Status: {response.status_code}): {response.text}")
    except Exception as e:
        print(f"AI 분석 중 예외 발생: {e}")
    return []


def upload_media_from_url(image_url):
    """이미지를 다운로드하여 WebP로 압축한 후 워드프레스에 업로드하고 ID를 반환합니다."""
    if not image_url or not image_url.startswith("http"): return None
    print(f"이미지 처리 및 업로드 시도: {image_url[:50]}...")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    try:
        # 1. 이미지 다운로드
        img_res = requests.get(image_url, timeout=30, headers=COMMON_HEADERS, verify=False)
        if img_res.status_code != 200: return None
        
        # 2. Pillow를 이용한 이미지 최적화 (WebP 변환 및 압축)
        img = Image.open(io.BytesIO(img_res.content))
        
        # RGBA -> RGB 변환 (WebP/JPEG 호환성)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # 리사이징 (너비 기준 최대 800px)
        max_width = 800
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * float(ratio))
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
        # JPEG 바이트 데이터로 변환 (WebP 대신 호환성 높은 JPEG 사용)
        jpg_io = io.BytesIO()
        img.save(jpg_io, format="JPEG", quality=80, optimize=True) # optimize=True로 추가 압축
        image_data = jpg_io.getvalue()
        
        # 3. 워드프레스 업로드
        filename = f"news_img_{int(time.time())}.jpg"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "image/jpeg"
        }
        
        up_res = requests.post(
            f"{WP_SITE_URL}/wp-json/wp/v2/media",
            auth=auth,
            headers=headers,
            data=image_data,
            timeout=40,
            verify=False
        )
        
        if up_res.status_code in [200, 201]:
            media_id = up_res.json().get('id')
            print(f"  -> 이미지 최적화 업로드 완료 (ID: {media_id}, 용량: {len(image_data)//1024}KB, 포맷: JPEG)")
            return media_id
        else:
            print(f"  -> 업로드 실패: {up_res.status_code}")
    except Exception as e:
        print(f"  -> 이미지 처리 중 예외 발생: {e}")
    return None

def get_or_create_term(taxonomy, name):
    """카테고리나 태그의 ID를 가져오거나 없으면 생성합니다."""
    endpoints = [
        f"{WP_SITE_URL}/wp-json/wp/v2/{taxonomy}",
        f"{WP_SITE_URL}/index.php?rest_route=/wp/v2/{taxonomy}"
    ]
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    for endpoint in endpoints:
        try:
            res = session.get(endpoint, auth=auth, params={"search": name}, timeout=20, verify=False)
            if res.status_code == 200:
                terms = res.json()
                for term in terms:
                    if term['name'] == name: return term['id']
                post_res = session.post(endpoint, auth=auth, json={"name": name}, timeout=20, verify=False)
                if post_res.status_code in [200, 201]: return post_res.json()['id']
        except: continue
    return None

def post_to_wordpress(news_data, original_news_list):
    """뉴스를 워드프레스에 포스팅합니다. (FIFU 외부 이미지 연동 방식)"""
    print(f"--- 포스팅 시도: {news_data['title']} ---")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    target_image = None
    source_url = news_data.get('source_url', '').rstrip('/')
    for item in original_news_list:
        item_link = item.get('link', '').rstrip('/')
        if item_link == source_url and item.get('rss_image'):
            target_image = item['rss_image']
            break
            
    # 구글 뉴스 기본 아이콘 체크 (The Hacker News의 blogger 이미지는 허용)
    if target_image and "googleusercontent.com" in target_image and "blogger" not in target_image:
        target_image = None

    if not target_image: target_image = get_image_from_webpage(source_url)

    # Cloudflare 차단(BleepingComputer 등) 및 구글뉴스 리다이렉트는 Microlink로 우회 추출
    if not target_image or ("googleusercontent.com" in target_image and "blogger" not in target_image):
        target_image = get_image_via_microlink(source_url)

    # 여전히 없거나 구글 아이콘인 경우 Playwright 정밀 추출 시도
    if not target_image or ("googleusercontent.com" in target_image and "blogger" not in target_image):
        target_image = get_image_from_webpage_robustly(source_url)

    if not target_image: target_image = news_data.get('image_url')

    # 본문 내용 가져오기
    content_body = news_data.get('content', '내용 없음')

    # 전략 A1: 이미지를 직접 업로드하여 특성 이미지로 설정 (가장 안정적)
    media_id = None
    if target_image and target_image.startswith("http"):
        media_id = upload_media_from_url(target_image)
    
    if not media_id:
        print(f"  -> 이미지를 업로드하지 못해 기본 미디어 ID {GUARANTEED_MEDIA_ID}를 사용합니다.")
        media_id = GUARANTEED_MEDIA_ID

    tag_ids = [get_or_create_term("tags", t) for t in news_data.get('tags', [])]
    tag_ids = [tid for tid in tag_ids if tid]
    
    payload = {
        "title": news_data['title'],
        "content": content_body,
        "status": "publish",
        "categories": [21], # 'News' 카테고리 ID 21 고정
        "tags": tag_ids,
        "featured_media": media_id
    }
    
    try:
        res = session.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30, verify=False)
        if res.status_code in [200, 201]:
            print(f"발행 성공! (확인: {res.json().get('link')})")
        else: print(f"발행 실패: {res.status_code} - {res.text}")
    except Exception as e: print(f"포스팅 예외: {e}")

def save_selected_news_to_json(selected_news):
    """선정된 뉴스 결과를 JSON 파일로 저장하여 다른 에이전트가 활용할 수 있도록 합니다."""
    try:
        output_data = []
        for news in selected_news:
            output_data.append({
                "title": news.get("title"),
                "source_url": news.get("source_url"),
                "content": news.get("content"),
                "tags": news.get("tags"),
                "image_url": news.get("image_url")
            })
        
        file_path = "selected_news.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        print(f"뉴스 선정 결과가 {file_path}에 저장되었습니다. ({len(output_data)}개 기사)")
    except Exception as e:
        print(f"JSON 저장 중 오류 발생: {e}")

def main():
    if not all([PERPLEXITY_API_KEY, WP_USERNAME, WP_APP_PASSWORD]):
        print("필수 환경 변수 누락")
        return
    init_session()
    
    recent_titles, recent_urls = get_recent_posts_info()
    news_list = get_rss_news()

    # [1차 방어] 이미 게시된 출처 URL을 가진 후보를 AI 분석 전에 사전 제거
    if recent_urls:
        before = len(news_list)
        news_list = [n for n in news_list if normalize_url(n.get('link')) not in recent_urls]
        removed = before - len(news_list)
        if removed:
            print(f"  -> 이미 게시된 기사 {removed}개를 후보에서 사전 제외했습니다.")

    selected_news = analyze_news_with_perplexity(news_list, recent_titles)

    if not selected_news:
        print("선정된 뉴스가 없습니다.")
        return

    # 뉴스 선정 결과 저장
    save_selected_news_to_json(selected_news)

    # [2차 방어] 포스팅 직전 출처 URL 기준 최종 중복 가드
    #  - recent_urls: 과거(교차일) 중복 차단
    #  - posted_this_run: 같은 실행 배치 내에서 AI가 동일 기사를 중복 선정한 경우 차단
    posted_this_run = set()
    for news in selected_news:
        norm = normalize_url(news.get('source_url'))
        if norm and norm in recent_urls:
            print(f"  -> [중복 건너뜀] 이미 게시된 기사: {news.get('title')}")
            continue
        if norm and norm in posted_this_run:
            print(f"  -> [중복 건너뜀] 이번 실행에서 중복 선정된 기사: {news.get('title')}")
            continue
        try:
            post_to_wordpress(news, news_list)
            if norm:
                posted_this_run.add(norm)
            time.sleep(5)
        except Exception as e: print(f"처리 중 오류: {e}")

if __name__ == "__main__":
    main()
