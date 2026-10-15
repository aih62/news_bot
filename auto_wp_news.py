import feedparser
import requests
import json
import re
from requests.auth import HTTPBasicAuth
import time
import calendar
import concurrent.futures
import os
import sys
import html
import urllib3
import io
from PIL import Image
from urllib.parse import quote, urljoin, urlparse, parse_qs, unquote
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
#  ※ 기존 5680은 삭제되어 404 → featured_media=0(이미지 없음)으로 폴백되던 문제를 수정.
#    반드시 미디어 라이브러리에 실제 존재하는 ID를 유지할 것.
GUARANTEED_MEDIA_ID = 3199
DEFAULT_IMAGE_URL = "https://ajken.mycafe24.com/wp-content/uploads/2026/03/news_img_1773008245.jpg"

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

def _decode_google_news_url(url, timeout=20):
    """news.google.com/rss/articles/CBMi... 형식(base64 인코딩)의 URL을
    구글 내부 batchexecute API로 원문 기사 URL로 디코딩한다. 실패 시 None.
    (단순 리다이렉트·정규식으로는 풀리지 않는 최신 포맷 전용 해제 경로)"""
    try:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2 or parts[-2] not in ("articles", "read"):
            return None
        art_id = parts[-1]
        # 1) 기사 페이지에서 서명(sg)·타임스탬프(ts) 취득
        r = requests.get(f"https://news.google.com/rss/articles/{art_id}",
                         headers=COMMON_HEADERS, timeout=timeout, verify=False)
        m_sg = re.search(r'data-n-a-sg="([^"]+)"', r.text)
        m_ts = re.search(r'data-n-a-ts="([^"]+)"', r.text)
        if not (m_sg and m_ts):
            return None
        sig, ts = m_sg.group(1), m_ts.group(1)
        # 2) batchexecute 페이로드 구성 및 호출
        inner = ('["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,'
                 'null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
                 '"%s",%s,"%s"]') % (art_id, ts, sig)
        freq = json.dumps([[["Fbv4je", inner]]])
        r2 = requests.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                     "User-Agent": COMMON_HEADERS.get("User-Agent", "Mozilla/5.0")},
            data={"f.req": freq}, timeout=timeout, verify=False)
        # 3) 응답 파싱: 빈 줄로 구분된 두 번째 청크의 중첩 JSON에서 URL 추출
        try:
            arr = json.loads(r2.text.split("\n\n")[1])
            decoded = json.loads(arr[0][2])[1]
            if decoded and decoded.startswith("http"):
                return decoded
        except Exception:
            m = re.search(r'garturlres.{0,8}(https?://[^\\"]+)', r2.text)
            if m:
                return m.group(1)
    except Exception as e:
        print(f"  -> Google 원문 디코딩 실패: {e}")
    return None


def resolve_google_url(url, deep=False):
    """구글 뉴스 리다이렉트 URL을 실제 기사 URL로 변환합니다.
    deep=True면 신뢰도 높은 batchexecute 디코더를 우선 시도하고, 실패 시 빠른 방법(쿼리·리다이렉트·정규식)으로 폴백합니다."""
    if not url or "news.google.com" not in url.lower(): return url
    # [최우선] deep 모드에서는 batchexecute 디코더가 가장 정확하므로 먼저 시도한다.
    #  (빠른 정규식 경로는 페이지 내 임의 URL(gstatic 등)을 오탐할 수 있어 후순위로 둔다.)
    if deep:
        decoded = _decode_google_news_url(url)
        if decoded and "news.google.com" not in urlparse(decoded).netloc.lower():
            return decoded
    try:
        parsed = urlparse(url)
        query_url = parse_qs(parsed.query).get("url", [None])[0]
        if query_url and "news.google.com" not in query_url:
            return unquote(query_url)
        patterns = [
            r'<link[^>]+rel=["\'][^"\']*canonical[^"\']*["\'][^>]+href=["\']([^"\']+)',
            r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:url["\']',
        ]
        request_urls = [url]
        # /read/는 RSS용 /rss/articles/ 엔드포인트로 바꾸면 redirect가
        # 정상 동작하는 경우가 많습니다.
        if "/read/" in parsed.path:
            article_id = parsed.path.rsplit("/read/", 1)[1]
            request_urls.append(f"https://news.google.com/rss/articles/{article_id}?oc=5")
        for request_url in request_urls:
            with requests.get(request_url, timeout=15, allow_redirects=True,
                              headers=COMMON_HEADERS, verify=False) as res:
                if "news.google.com" not in urlparse(res.url).netloc.lower():
                    return res.url
                page = res.text or ""
            # canonical / og:url 만 신뢰한다. (페이지의 임의 https URL을 긁으면
            #  Angular 등 프레임워크 링크(예: angular.dev/license)를 원문으로 오인하므로 사용하지 않는다.)
            candidates = []
            for pattern in patterns:
                candidates.extend(re.findall(pattern, page, re.I))
            asset_hosts = ("google.com", "googleusercontent.com", "gstatic.com",
                           "google-analytics.com", "googletagmanager.com", "googleapis.com",
                           "schema.org", "w3.org", "youtube.com", "ytimg.com", "doubleclick.net")
            asset_exts = (".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2")
            for candidate in candidates:
                candidate = unquote(html.unescape(candidate).replace('\\u0026', '&')).rstrip('.,;)')
                host = urlparse(candidate).netloc.lower()
                path_l = urlparse(candidate).path.lower()
                if (candidate.startswith("http") and host and
                        "news.google.com" not in host and
                        not any(a in host for a in asset_hosts) and
                        not path_l.endswith(asset_exts)):
                    return candidate
    except Exception as e:
        print(f"  -> Google News 원문 URL 해제 실패: {e}")
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

# 구글 뉴스 검색어를 이 개수씩 나눠 호출한다. 7개를 넘기면 when:1d가 무시되므로
# 여유를 두고 6개로 잡는다(실측 근거는 get_rss_news의 검색 구간 주석 참조).
KEYWORDS_PER_QUERY = 6


# 이 사이트 후보 대부분에 등장해 '사건'을 식별하지 못하는 단어.
# 이런 단어가 중복 판정을 좌우하면 서로 다른 사건이 중복으로 묶인다.
_DEDUP_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "has", "have", "its", "into", "onto",
    "new", "now", "say", "says", "said", "how", "why", "what", "who", "can", "could", "will",
    "ai", "cyber", "cybersecurity", "security", "secure", "securities", "tech", "technology",
    "attack", "attacks", "attacker", "attackers", "threat", "threats", "hack", "hackers",
    "flaw", "flaws", "bug", "bugs", "vulnerability", "vulnerabilities", "exploit", "exploited",
    "exploits", "patch", "patches", "patched", "fix", "fixes", "fixed", "update", "updates",
    "launch", "launches", "launched", "unveils", "unveil", "announces", "announced", "releases",
    "release", "released", "introduces", "adds", "report", "reports", "reveals", "warns",
    "data", "user", "users", "customer", "customers", "company", "companies", "firm", "firms",
    "tool", "tools", "platform", "model", "models", "system", "systems", "service", "services",
    "risk", "risks", "issue", "issues", "news", "market", "global", "million", "billion",
    # 벤더·기관명은 이 사이트에 상시 등장하며 그 자체로는 사건을 특정하지 못한다.
    # ('Microsoft'와 'Windows'를 공유한다는 이유로 무관한 두 기사가 묶인 사례가 있었다)
    "microsoft", "google", "amazon", "apple", "meta", "cisco", "openai", "anthropic",
    "aws", "azure", "windows", "claude", "chatgpt", "gemini", "cisa", "nist", "nsa",
}


def _dedup_tokens(text):
    """제목/URL에서 사건 식별용 토큰을 뽑아 (고유명사·식별자, 일반어)로 나눈다.

    'GPT-5.6-Cyber', 'SMA1000', 'CVE-2026-8037'처럼 숫자·하이픈이 섞인 토큰과
    'Astra', 'SonicWall' 같은 고유명사가 사건을 가장 정확히 식별한다.
    (기존 로직은 \\w{4,}로 잘라 'GPT-5.6-Cyber'를 버렸고, 소문자로 뭉개
     고유명사와 일반어를 구분하지 못해 같은 발표를 별개 사건으로 판정했다.)

    URL slug처럼 대소문자 정보가 없는 입력에서는 고유명사를 알 수 없으므로,
    그 경우 일반어 비교와 식별자 비교에 의존한다."""
    # 제목과 URL slug를 같은 형태로 정규화한다.
    #  slug는 하이픈이 단어 구분자이므로 그대로 두면 통째로 한 토큰이 되어 비교가 되지 않는다.
    norm = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")

    # 버전·모델·CVE·KB 번호. 사건 자체를 가리키므로 빈도와 무관하게 강한 신호로 쓴다.
    #  (여러 매체가 다룰수록 빈도가 올라가는데, 그것이 곧 같은 사건이라는 증거다.
    #   'gpt-5.6-cyber'와 slug의 'gpt-5-6-cyber'가 같은 형태로 모인다.)
    #  뒤따르는 단어를 1개로 제한한다. 제한이 없으면 slug 꼬리를 통째로 삼켜
    #  'gpt-5-6-cyber-to-help-defenders-...'가 하나의 토큰이 되어 비교가 무의미해진다.
    strong = set(re.findall(r"cve-\d{4}-\d+|kb\d{5,}|[a-z]{2,}(?:-\d+){1,3}(?:-[a-z]{2,})?", norm))

    content = {t for t in norm.split("-")
               if len(t) >= 3 and not t.isdigit() and t not in _DEDUP_STOPWORDS}
    return strong, content


def _build_distinctive_filter(titles):
    """후보 전체에서 흔한 토큰을 걸러내는 판별 함수를 만든다.

    말뭉치가 그날의 후보 목록이므로 임계값이 자동으로 보정된다.
    'Microsoft'가 후보 여럿에 등장하는 날에는 Microsoft가 식별력을 잃어
    무관한 마이크로소프트 기사끼리 묶이는 일을 막는다."""
    df = {}
    for t in titles:
        _, content = _dedup_tokens(t)
        for tok in content:
            df[tok] = df.get(tok, 0) + 1
    limit = max(2, int(len(titles) * 0.15))
    return lambda tok: df.get(tok, 0) <= limit


def _same_event(tokens_a, tokens_b, is_distinctive):
    """두 제목이 같은 사건을 다루는지 판정한다."""
    strong_a, content_a = tokens_a
    strong_b, content_b = tokens_b

    # 같은 버전·모델·CVE·KB 번호를 다루면 같은 사건이다.
    if strong_a & strong_b:
        return True

    # 나머지는 흔한 토큰을 걸러낸 뒤 겹치는 신호가 2개 이상일 때만 같은 사건으로 본다.
    # (1개만으로 판정하면 'Microsoft'·'Windows'를 공유하는 무관한 기사끼리 묶인다.)
    shared = {t for t in (content_a & content_b) if is_distinctive(t)}
    return len(shared) >= 2


# 매체마다 수치가 달라지는 정례 사건. 토큰 비교로는 잡히지 않아 서명으로 식별한다.
#  (2026-10-15: 같은 Patch Tuesday를 다룬 3건이 1,400 / 1,411 / 1,413으로 수치가
#   갈려 strong 토큰이 전부 달라지고, 식별 단어인 microsoft·patch·flaws는 모두
#   _DEDUP_STOPWORDS에 있어 공통 토큰이 'record' 하나뿐이었다. 선정 프롬프트에
#   'Patch Tuesday'가 이름까지 적혀 있었는데도 3건이 통과했으므로, LLM 판단이 아니라
#   결정론적 차단이 필요하다.)
#  서명은 한 가지 사건 유형을 가리킬 뿐이므로, 같은 서명이 둘 이상 나왔을 때만
#  뒤의 것을 버린다. 혼자 걸린 서명은 아무것도 떨어뜨리지 않아 오탐 비용이 낮다.
_RECURRING_EVENT_RULES = [
    # (서명, 제목에 모두 있어야 하는 패턴)
    ("ms-patch-tuesday", [r"\bpatch tuesday\b"]),
    ("ms-patch-tuesday", [r"\bmicrosoft\b", r"\bpatch\w*\b", r"\b\d{2,4}\b",
                          r"\b(cve|cves|flaw|flaws|vulnerabilit\w+)\b"]),
    ("android-bulletin", [r"\bandroid\b", r"\bsecurity (bulletin|update|patch)\b"]),
    ("oracle-cpu",       [r"\boracle\b", r"\bcritical patch update\b"]),
    ("sap-patch-day",    [r"\bsap\b", r"\b(patch day|security notes?)\b"]),
    ("chrome-stable",    [r"\bchrome\b", r"\bstable (channel )?update\b"]),
]


def _recurring_signature(text):
    """정례 사건의 서명을 반환한다(해당 없으면 None).

    제목과 URL slug 모두에 쓰이므로 하이픈·쉼표를 공백으로 normalize한 뒤 본다.
    '1,400'은 '1 400'이 되므로 다시 붙여 수치로 인식시키고, CVE 식별자의 연도가
    수치로 오인되지 않도록 먼저 제거한다."""
    t = re.sub(r"[^a-z0-9]+", " ", str(text).lower())
    t = re.sub(r"\bcve \d{4} \d+\b", " cve ", t)      # CVE 연도를 수치로 세지 않는다
    t = re.sub(r"(?<=\b\d) (?=\d{3}\b)", "", t)        # '1 400' -> '1400'
    for key, patterns in _RECURRING_EVENT_RULES:
        if all(re.search(p, t) for p in patterns):
            return key
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
        # AI가 보안 산업을 바꾸는 각도. 기존 표에는 기술 주제어만 있어
        #  "벤더가 AI로 탐지력을 바꿨다"류 기사가 가점을 받지 못했다.
        'ai-powered': 40, 'ai-driven': 40, 'ai-assisted': 35,
        'agentic soc': 45, 'weaponized ai': 40, 'autonomous hacking': 45,
        'frontier model': 45, 'shadow ai': 40, 'ai security': 35, 'copilot': 30,
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

    # 단어 경계로 매칭한다. 부분문자열 매칭이던 시절 'sec'(35점)가 Secretary·second·
    # sector·prosecutor에, 'national'(25점)이 International에 걸려
    # "Secretary of State announces second sector review"가 50점을 받았다.
    def _hit(kw):
        return re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", title) is not None

    for table in (strategic_keywords, tech_leaders, technical_keywords):
        for kw, points in table.items():
            if _hit(kw):
                score += points
    
    # 24시간 이내 기사라면 동일한 시의성 점수 부여 (중복 제거용)
    score += 10 # 24h freshness base score

    if "Expert_" in entry['search_category']:
        score += 5
        
    return score

def get_rss_news(recent_urls=None):
    """feeds.json에서 직접 RSS 피드와 검색 카테고리를 읽어와 최신 기사 목록을 가져옵니다 (최근 24시간 이내).

    recent_urls를 받으면 이미 게시한 기사의 URL slug에서 사건 토큰을 뽑아,
    같은 발표를 다른 매체가 보도한 후보를 교차일 기준으로 걸러낸다."""
    print("feeds.json 로드 중...")
    try:
        with open("feeds.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            vuln_feeds = config.get("vuln_feeds", {})
            industry_feeds = config.get("industry_feeds", {})
            # 과거 형식(direct_feeds 단일 묶음) 호환. 성격을 알 수 없으므로
            # 보수적으로 취약점군 쿼터를 적용한다.
            legacy_feeds = config.get("direct_feeds", {})
            direct_feeds = {**legacy_feeds, **vuln_feeds, **industry_feeds}
            # 출처 라벨(Expert_*)별 쿼터. search_category 라벨 자체는 바꾸지 않아
            # 점수 보너스와 선정 프롬프트의 source 표기가 그대로 유지된다.
            feed_quota = {f"Expert_{n}": VULN_FEED_QUOTA for n in legacy_feeds}
            feed_quota.update({f"Expert_{n}": VULN_FEED_QUOTA for n in vuln_feeds})
            feed_quota.update({f"Expert_{n}": INDUSTRY_FEED_QUOTA for n in industry_feeds})
            # 수집 창도 같은 기준으로 나눈다(source_name 기준 — 직접 피드 루프가 쓴다).
            feed_recency = {n: RECENCY_VULN_FEED for n in legacy_feeds}
            feed_recency.update({n: RECENCY_VULN_FEED for n in vuln_feeds})
            feed_recency.update({n: RECENCY_INDUSTRY_FEED for n in industry_feeds})
            search_categories = config.get("search_categories", {})
    except Exception as e:
        print(f"feeds.json 로드 실패: {e}")
        return []

    all_entries = []
    seen_links = set()
    
    # 시간 필터링 기준 (현재 시간으로부터 24시간 전)
    now = time.time()

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

    def extract_summary(entry):
        """RSS가 제공하는 본문 요약을 보관한다(원문 스크래핑 실패 시 폴백 근거로 사용)."""
        text = getattr(entry, 'summary', '') or getattr(entry, 'description', '') or ''
        if 'content' in entry and entry.content:
            longest = max((c.value for c in entry.content), key=len, default='')
            if len(longest) > len(text):
                text = longest
        return text[:4000]

    def extract_image(entry):
        # 1. 미디어 태그 탐색
        # 일부 피드(Wired)는 media_content에 url 키가 없어 KeyError로 수집 전체가 중단됐다.
        if 'media_content' in entry and entry.media_content:
            u = entry.media_content[0].get('url')
            if u: return u
        if 'media_thumbnail' in entry and entry.media_thumbnail:
            u = entry.media_thumbnail[0].get('url')
            if u: return u
        
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
        recency_window = feed_recency.get(source_name, RECENCY_VULN_FEED)
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                # 조용한 실패를 막는다. Threatpost가 약 4년, Schneier가 URL 오류로
                # 아무것도 내지 않는 상태였는데 except: pass 때문에 드러나지 않았다.
                print(f"  [피드 비어 있음] {source_name} (HTTP {getattr(feed, 'status', '?')})")
            for entry in feed.entries[:20]:
                is_recent = False
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    if now - calendar.timegm(entry.published_parsed) < recency_window:
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
                        "rss_image": extract_image(entry),
                        "rss_summary": extract_summary(entry)
                    })
                    seen_links.add(actual_link)
        except Exception as e:
            print(f"  [피드 수집 실패] {source_name}: {e}")

    # 구글 뉴스 검색
    #  [중요] 구글 뉴스는 쿼리가 길어지면 when:1d(기간 한정)를 조용히 무시하고
    #  관련도순 과거 기사를 반환한다. 실측: 키워드 6개(174자)면 5건 전부 24h 이내였으나
    #  8개(228자)부터 79건이 오면서 24h 이내가 0건이 되었고, 운영 쿼리(876자)도 0건이었다.
    #  그 결과 이 수집 경로가 사실상 아무것도 기여하지 못했다(2026-08-10 확인).
    #  → 카테고리를 KEYWORDS_PER_QUERY개씩 쪼개 짧은 쿼리 여러 번으로 나눠 호출한다.
    for category_name, keywords in search_categories.items():
        chunks = [keywords[i:i + KEYWORDS_PER_QUERY] for i in range(0, len(keywords), KEYWORDS_PER_QUERY)]
        for chunk in chunks:
            query = " OR ".join([f'"{k}"' if " " in k else k for k in chunk])
            full_query = f"({query}) when:{SEARCH_TIME_WINDOW}"
            rss_url = f"https://news.google.com/rss/search?q={quote(full_query)}&hl=en-US&gl=US&ceid=US:en"
            try:
                feed = feedparser.parse(rss_url)
            except Exception as e:
                print(f"  [검색 실패] {category_name}: {e}")
                continue
            for entry in feed.entries[:15]:
                is_recent = True
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    if now - calendar.timegm(entry.published_parsed) > RECENCY_SEARCH:
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
                            "source_name": (
                                source_title if source_title.strip().lower() not in {"google", "google news"}
                                else _source_name_from_url(actual_link)
                            ),
                            "rss_image": extract_image(entry),
                            "rss_summary": extract_summary(entry)
                        })
                        seen_links.add(actual_link)

    # 모든 기사에 대해 점수 계산
    for entry in all_entries:
        entry['score'] = calculate_score(entry)

    # 점수 순으로 정렬
    all_entries.sort(key=lambda x: x['score'], reverse=True)

    # 중복 기사 및 매체 쿼터 관리
    final_candidates = []
    source_counts = {}

    is_distinctive = _build_distinctive_filter([e['title'] for e in all_entries])
    seen_events = []  # 이미 채택한 사건의 토큰

    # [교차일 중복] 어제 게시한 기사의 원문 URL slug에서 사건 토큰을 뽑아 미리 채워 둔다.
    #  URL 자체 비교는 매체가 다르면 통과해 버리므로(같은 발표를 THN·SecurityWeek가 각각 보도),
    #  slug에 담긴 제품명·버전으로 같은 사건임을 알아낸다.
    seen_signatures = set()  # 이미 채택한 정례 사건의 서명

    for u in (recent_urls or ()):
        slug = str(u).rstrip("/").split("/")[-1]
        if slug:
            seen_events.append(_dedup_tokens(slug))
            sig = _recurring_signature(slug)
            if sig:
                seen_signatures.add(sig)

    for entry in all_entries:
        source = entry['search_category']

        # 출처 성격별 쿼터를 적용한다(상수 주석 참조). 검색 카테고리는 매핑에 없다.
        quota = feed_quota.get(source, SEARCH_CATEGORY_QUOTA)
        if source_counts.get(source, 0) >= quota:
            continue

        # 같은 사건을 다룬 다른 매체 기사 제외
        tokens = _dedup_tokens(entry['title'])
        if any(_same_event(tokens, prev, is_distinctive) for prev in seen_events):
            _stat('dup_event')
            continue

        # 정례 사건은 매체별 수치가 갈려 토큰 비교로 잡히지 않으므로 서명으로 1건만 통과시킨다.
        #  all_entries가 점수 내림차순이라 가장 높은 점수의 기사가 남는다.
        signature = _recurring_signature(entry['title'])
        if signature and signature in seen_signatures:
            print(f"  -> [정례 중복 제외] {signature}: {entry['title'][:60]}")
            _stat('dup_signature')
            continue

        final_candidates.append(entry)
        source_counts[source] = source_counts.get(source, 0) + 1
        seen_events.append(tokens)
        if signature:
            seen_signatures.add(signature)
        
        if len(final_candidates) >= 40:
            break

    print(f"총 {len(all_entries)}개 수집 -> 중복 제거 및 가치 평가 후 {len(final_candidates)}개 후보 선정.")
    _stat('harvested', len(all_entries))
    _stat('candidates', len(final_candidates))
    return final_candidates


# ══════════════════════════════════════════════════════════════════════
#  Perplexity 2단계 파이프라인 (선정 → 기사별 본문 생성)
#   - 구조화 출력(json_schema)으로 API가 JSON 무결성을 보장 → 따옴표 깨짐 원천 차단
#   - 응답을 잘게 나눠 truncation(잘림) 원천 차단, 실패는 건별로 격리
# ══════════════════════════════════════════════════════════════════════
# 출처 성격별 후보 쿼터. 일률 쿼터로는 CVE 밀착 매체를 누를 때 산업 동향 매체도
#  같이 눌려, '취약점 축소'와 '산업 동향 확대'를 동시에 달성할 수 없었다.
#  (2026-10-15 실측: 일률 5건 시절 후보 40건 중 직접 피드 24건에 기업전략 0건·
#   취약점 13건. 일률 3건으로 낮췄을 때는 취약점이 8%로 떨어졌지만 같은 쿼터에
#   묶인 MSSPAlert·TheDecoder 같은 산업 매체도 3건에 갇혔다.)
# 수집 창을 출처 성격별로 다르게 둔다. 24시간 일률 적용은 취약점 보도에 맞춰진
#  기준이고, 업계·정책·위협분석 기사를 구조적으로 배제했다.
#  (2026-10-15 실측 — SecurityWeek compliance 카테고리(취약점 0%, 기업전략·규제 각 3건):
#   24h 0건 / 72h 0건. "LLM security"·"securing AI systems"·"espionage campaign":
#   24h 1~2건 / 72h 5~7건. 제로데이는 어제 것이 중요하지만 EU 규제안이나 인수
#   발표는 사흘 전 것도 그대로 유효하다.)
#  교차일 중복은 recent_urls URL 비교·_same_event 토큰 비교·_recurring_signature
#  세 겹으로 막혀 있어 창을 넓혀도 같은 기사가 재게시될 위험은 낮다.
RECENCY_VULN_FEED = 24 * 60 * 60      # 취약점 보도는 시의성이 핵심
RECENCY_INDUSTRY_FEED = 72 * 60 * 60  # 업계·정책·위협분석
RECENCY_SEARCH = 72 * 60 * 60         # 검색 카테고리(전략·시장·규제)
SEARCH_TIME_WINDOW = "3d"             # 구글 뉴스 when: 파라미터. 로컬 창과 함께 넓혀야 한다.

VULN_FEED_QUOTA = 2        # CVE·CWE·패치·침해 보도 중심 매체
INDUSTRY_FEED_QUOTA = 6    # 보안산업 동향·정책·AI보안 매체
SEARCH_CATEGORY_QUOTA = 8  # 전략·정책·시장 검색 카테고리

# 실행마다 한 줄로 지표를 남긴다. 이 저장소의 품질 문제는 전부 몇 주간 조용히
#  진행된 뒤 사람이 눈치채서 발견됐다(취약점 비중 40%, Patch Tuesday 3중 게시,
#  백스톱 14일 연속 중복 전송, 불릿 2문장 99%). 매 실행 로그에 구성이 찍히면
#  편향 재발을 며칠 안에 알아볼 수 있다.
RUN_STATS = {}


def _stat(key, delta=1):
    RUN_STATS[key] = RUN_STATS.get(key, 0) + delta


# 게시물 주제 분류(지표용 근사치). 선정 쿼터의 4개 범주에 대응한다.
_TOPIC_PATTERNS = [
    ("기업전략", r"(인수|합병|출시|출범|통합|투자|매출|순이익|파트너|제휴|계약|로드맵|상장|시장|스타트업)"),
    ("규제정책", r"(법|법안|규제|지침|의무|표준|공시|당국|위원회|감독|조달|권고|거버넌스)"),
    ("취약점", r"(취약점|결함|패치|제로데이|악용|침해|랜섬웨어|탈취|유출|웹셸|백도어|봇넷|악성|CVE)"),
]


def classify_topic(title):
    for name, pat in _TOPIC_PATTERNS:
        if re.search(pat, title):
            return name
    return "AI·기술"


def print_run_metrics():
    """수집부터 게시까지의 구성을 한 줄로 남긴다(GitHub Actions 로그에서 추적용)."""
    g = RUN_STATS.get
    parts = [
        f"harvested={g('harvested', 0)}",
        f"candidates={g('candidates', 0)}",
        f"selected={g('selected', 0)}",
        f"posted={g('posted', 0)}",
        f"dup_event={g('dup_event', 0)}",
        f"dup_signature={g('dup_signature', 0)}",
        f"dup_posted={g('dup_posted', 0)}",
        f"regenerated={g('regenerated', 0)}",
        f"gen_failed={g('gen_failed', 0)}",
    ]
    for name in ("기업전략", "규제정책", "취약점", "AI·기술"):
        parts.append(f"topic_{name}={g('topic_' + name, 0)}")
    if g('bullet_count', 0):
        parts.append(f"avg_bullet={g('bullet_chars', 0) // g('bullet_count', 1)}")
    print("[METRICS] " + " ".join(parts))


PPLX_ENDPOINT = "https://api.perplexity.ai/chat/completions"


class PerplexityAuthError(RuntimeError):
    """Perplexity 인증·쿼터 오류(401/403).

    재시도로 회복되지 않고 사람이 개입해야 하는 오류이므로 별도 타입으로 올린다.
    2026-09-26~28에 크레딧이 소진되자 401이 일반 예외로 흡수되어, 0건 발행이
    success로 표시된 채 3일간 아무 경보 없이 방치됐다."""


def _pplx_chat(data, timeout=180, max_retries=6):
    """Perplexity Chat Completions 호출 후 message content(str)를 반환한다.
    429(Too Many Requests)·5xx는 지수 백오프로 재시도한다. 품질 재생성이 호출량을 늘려
    분당 한도를 초과하면 첫 호출이 429로 실패해 기사가 통째로 드롭되던 문제를 방지한다.
    (재시도 6회, 대기 5→90초까지 증가시켜 rate-limit 버스트를 더 넓게 흡수한다.)"""
    headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}
    delay = 5.0
    for attempt in range(max_retries + 1):
        res = requests.post(PPLX_ENDPOINT, headers=headers, json=data, timeout=timeout)
        if res.status_code in (401, 403):
            # 재시도 금지: 쿼터 소진·키 폐기는 기다려도 회복되지 않는다.
            raise PerplexityAuthError(f"Perplexity {res.status_code}: {res.text[:200]}")
        if (res.status_code == 429 or res.status_code >= 500) and attempt < max_retries:
            ra = res.headers.get("Retry-After")
            wait = float(ra) if (ra and str(ra).strip().isdigit()) else delay
            print(f"  -> Perplexity {res.status_code} → {wait:.0f}s 후 재시도 ({attempt + 1}/{max_retries})")
            time.sleep(wait)
            delay = min(delay * 2, 90)
            continue
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
    "govinsider.asia": "GovInsider",
    "techpolicy.press": "Tech Policy Press",
    "aijourn.com": "AI Journal",
    "techreviewafrica.com": "Tech Review Africa",
    "newsbytes.ph": "Newsbytes.PH",
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


# 본문 추출 시 제거할 비(非)기사 영역 태그
_ARTICLE_DROP_TAGS = ["script", "style", "nav", "header", "footer", "aside", "form", "figure", "noscript", "iframe"]

# 구독 유도·쿠키 고지 등 본문이 아닌 상용구(추출 결과에서 제외)
_BOILERPLATE_PAT = re.compile(
    r"(subscribe|newsletter|cookie|privacy policy|all rights reserved|sign up|follow us|read more|"
    r"advertisement|share this|related articles)", re.I
)


def fetch_article_text(url, max_chars=6000, timeout=20):
    """기사 URL에서 본문 텍스트를 추출한다.

    모델에 제목·URL만 주면 페이월·봇차단 매체에서 웹검색이 실패해 추측성 일반론이 생성된다.
    실제 원문을 프롬프트에 주입해 수치·고유명사 등 팩트 공급원을 확보하는 것이 목적이다.
    추출 실패(차단·타임아웃·비HTML)는 예외를 던지지 않고 빈 문자열을 반환하며,
    이 경우 호출부는 기존처럼 Perplexity 웹검색에만 의존한다."""
    if not url or not url.startswith("http"):
        return ""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return ""
    try:
        res = requests.get(url, timeout=timeout, headers=COMMON_HEADERS, verify=False, allow_redirects=True)
        if res.status_code != 200:
            return ""
        if "html" not in res.headers.get("Content-Type", "").lower():
            return ""

        # 기사 URL이 홈/섹션 목록으로 리다이렉트된 경우(the-decoder.com 등)는 추출을 포기한다.
        # 목록 페이지에는 <article>이 여러 개 있어 그대로 긁으면 '무관한 다른 기사'를 원문으로
        # 오인해 주입하게 되며, 이는 요약이 부실한 것보다 훨씬 위험하다.
        if urlparse(url).path.strip("/") and not urlparse(res.url).path.strip("/"):
            print(f"  -> 원문 URL이 목록/홈으로 리다이렉트되어 추출 취소: {res.url}")
            return ""

        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(_ARTICLE_DROP_TAGS):
            tag.decompose()

        # 1순위 <article> → 2순위 <p>를 가장 많이 가진 컨테이너 → 3순위 문서 전체
        #  <article>이 여러 개인 레이아웃(관련기사·피드형)에서는 첫 번째가 본문이 아닐 수 있으므로
        #  '긴 문단을 가장 많이 가진' 것을 본문으로 본다.
        articles = soup.find_all("article")
        container = None
        if articles:
            def _long_p(el):
                return sum(1 for p in el.find_all("p") if len(p.get_text(" ", strip=True)) >= 40)
            container = max(articles, key=_long_p)
            if _long_p(container) < 3:
                container = None
        if container is None or len(container.find_all("p")) < 3:
            best, best_count = None, 0
            for cand in soup.find_all(["div", "section", "main"]):
                count = len(cand.find_all("p", recursive=False))
                if count > best_count:
                    best, best_count = cand, count
            container = best if best_count >= 3 else soup

        paras = []
        for p in container.find_all("p"):
            text = p.get_text(" ", strip=True)
            # 40자 미만은 캡션·버튼·꼬리말일 가능성이 높아 버린다
            if len(text) < 40 or _BOILERPLATE_PAT.search(text):
                continue
            paras.append(text)

        body = re.sub(r"\s+", " ", " ".join(paras)).strip()
        # 본문이라 보기 어려운 분량이면 없는 것으로 간주(잘못된 컨테이너 오검출 방지)
        if len(body) < 300:
            return ""
        return body[:max_chars]
    except Exception:
        return ""


_SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "selected": {"type": "array", "items": {"type": "integer"}}
    },
    "required": ["selected"],
}


def select_top_news(news_list, recent_titles, want=10, recent_urls=None):
    """[1단계] 후보 중 상위 want개의 index만 구조화 출력으로 선정한다.
    적합한 기사가 want개에 못 미치면 개수를 채우지 않고 그만큼만 반환한다."""
    indexed = [
        {"index": i, "title": n.get("title", ""), "source": n.get("search_category", "")}
        for i, n in enumerate(news_list)
    ]
    prompt = f"""당신은 글로벌 보안 인텔리전스 기업의 '수석 분석가'입니다.
아래 후보 뉴스에서 한국 정부 보안 정책 담당자에게 가치 있는 기사를 **최대 {want}개까지** 선정하십시오.

[주제 적합성 — 최우선 관문. 여기서 탈락하면 다른 조건이 아무리 좋아도 제외]
- 이 매체는 **사이버보안 · ICT · 인공지능(AI)** 세 분야만 다룹니다.
- 아래에 해당하면 반드시 제외하십시오.
  · 일반 정치·선거·의회 동향(대선 출마, 정당 내분, 인사청문회, 지역구 판세 등)
  · 국제 정세·외교·군사·통상 분쟁 중 사이버·기술 쟁점이 아닌 것
  · 경제·증시·산업 일반, 스포츠, 연예, 사건사고, 기후·재난 그 자체
  · 언론사 칼럼·사설·에디터 노트 등 뉴스가 아닌 논평
  · 국가의 일반 개발·행정 성과 홍보(디지털 전환을 표방해도 기술 실체가 없으면 제외)
- 판별 기준: "이 기사에서 사이버보안·ICT·AI의 구체적 기술·제품·위협·규제·기업 활동이 **주제 자체**인가?"
  주제가 아니라 배경으로만 언급된다면 제외하십시오.
- **한국과 엮을 여지가 있다는 이유로 무관한 기사를 선정하지 마십시오.**

[선정 구성 — 비율 가중치가 아니라 반드시 지킬 건수 쿼터]
1. 기업 전략·시장 지배력(M&A, 투자·실적, 플랫폼 통합, 기술 로드맵): Palo Alto Networks, CrowdStrike, Microsoft, Zscaler, Google Cloud, Anthropic/OpenAI 등 → **4건**
2. AI가 보안 산업을 바꾸는 방식 → **3건**
   · 벤더가 AI를 제품에 넣어 탐지·대응 역량이 실제로 달라진 사례 (예: 특정 기업이 자사 플랫폼에 AI를 도입해 탐지력을 개선)
   · 프런티어 모델의 보안 역량 변화 (예: 최신 모델의 취약점 발견·공격 수행 능력이 크게 올라감)
   · 공격자의 AI 활용으로 공격 속도·규모·정교함이 달라진 사례 (예: AI 도구를 써서 특정 기업·기관을 침해)
   · AI가 보안 인력·지출·경쟁 구도에 주는 구조적 영향
   · 에이전틱 AI 위협, AI 안전성 프레임워크, 양자내성암호 등 미래 기술 의제
   판별 기준: "이 기사를 읽고 보안 산업이 어느 방향으로 바뀌는지 알 수 있는가
3. 글로벌 규제·정책(미국 사이버 EO, EU AI Act, 각국 AI 안전 법안, 국제 표준) → **2건**
4. 파급력·시급성 → **1건 (최대 1건, 초과 절대 금지)**
   - [제외 — 중요] 취약점의 발견·공개·패치 배포·KEV 등재 그 자체는 선정하지 마십시오. 기술적 사실일 뿐 산업이 어떻게 바뀌는지 말해주지 않습니다.
     (제외 예: "Cisco, 핵심 취약점 12건 패치" / "CISA, Ivanti 결함을 KEV에 등재" / "SonicWall SMA1000 취약점 공개" / "Fortra, BoKS 치명적 취약점 패치")
   - [포함] 그 사건이 산업의 대응 방식이나 전제를 바꾼 경우만 선정하십시오.
     (포함 예: "패치 5개월 뒤에도 랜섬웨어 표적 — 패치 중심 대응의 한계" / "공급망 한 지점 침해로 23개국 항만 운영사가 동시 노출")

- [4번 상한이 가장 중요합니다] 개별 취약점·패치·침해 사고 기사가 후보에 아무리 많아도
  그중 파급력이 가장 큰 **1건만** 고르고 나머지는 전부 버리십시오. 후보의 절반이
  취약점 기사인 날이 많은데, 그것은 매체 구성 탓이며 선정 비중의 근거가 아닙니다.
- 특정 범주에 적합한 기사가 쿼터보다 적으면 그 범주는 적은 대로 두고, **다른 범주
  기사로 메우지 마십시오.** 특히 빈자리를 4번으로 채우는 것이 가장 심각한 오류입니다.
- 쿼터를 합쳐 10건이 안 되는 것은 정상입니다. 쿼터를 넘기는 것이 더 나쁩니다.
- [핵심 사건 예외 — 하루 1건까지만] 어떤 사건이 아래 중 하나에 해당하면, 그 사건 1건을
  범주 쿼터와 **별도로** 추가 선정하십시오. 4번 쿼터를 쓰지 않고 추가하는 것입니다.
  · 다수 국가 또는 다수 산업의 기관에 동시에 영향을 주는 사건
  · 핵심 기반시설(전력·통신·금융·항만·의료)이나 공급망 전반을 겨냥한 사건
  · 주요국 정부·규제기관이 공식 경고·긴급 지침을 발령한 사건
  이 예외는 하루 1건이 상한이며, 해당하는 사건이 없으면 쓰지 마십시오. 평범한
  취약점 공개나 단일 기업 침해를 이 예외로 끌어올리는 것은 쿼터 위반과 같습니다.

[제외/중복 규칙]
- 아래 '이미 게시된 제목'과 동일한 사건은 제외: {json.dumps(recent_titles, ensure_ascii=False)}
- 아래는 이미 다룬 기사의 원문 URL입니다. 제목이 한국어로 바뀌어 있어도 이 URL들을 보면 어떤 사건을 이미 보도했는지 알 수 있으니, **같은 사건을 다룬 후보는 매체가 달라도 제외**하십시오.
  {json.dumps(sorted(recent_urls or [])[:40], ensure_ascii=False)}
- [같은 사건 1건 원칙 — 반드시 확인]
  · 여러 매체가 같은 발표·사건을 보도한 경우가 흔합니다. **선정 전에 후보를 사건 단위로 묶고, 각 사건에서 정보가치가 가장 높은 1건만 고르십시오.**
  · 제목 표현이 달라도 같은 사건입니다. (예: "OpenAI Launches GPT-5.6-Cyber with Exploit Development" / "OpenAI Unveils New Cybersecurity Model GPT-5.6-Cyber" → 같은 발표이므로 1건만)
  · 같은 제품명·버전·CVE 번호·기관명이 등장하면 같은 사건일 가능성이 높으니 특히 주의하십시오.
  · Patch Tuesday, 분기 실적, 연례 보고서처럼 매체별 수치가 조금씩 다른 기사도 하나의 사건입니다.
- 한국 매체/한국어 기사는 제외(사전 필터되었으나 재확인).

[개수 규칙 — 매우 중요]
- {want}개를 채우는 것은 목표가 아닙니다. **적합한 기사가 {want}개보다 적으면 적은 대로 반환하십시오.**
- 적합한 기사가 3개뿐이면 3개만, 하나도 없으면 빈 배열을 반환하십시오.
- 개수를 맞추려고 위 '주제 적합성'에서 탈락한 기사를 넣는 것이 가장 심각한 오류입니다.

선정한 후보의 index 번호를 정수 배열로만 반환하십시오.

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
    except PerplexityAuthError:
        # 인증·쿼터 오류는 여기서 삼키지 않고 상위로 올려 워크플로를 실패시킨다.
        raise
    except Exception as e:
        print(f"  -> 선정 단계 오류: {e}")

    # 점수순 상위 want개로 채우는 폴백은 두지 않는다.
    #  calculate_score는 주제 적합성을 보지 않으므로, 후보가 적은 날 그 폴백은
    #  정치·일반 뉴스를 그대로 통과시킨다(2026-08-10 Axios 사례).
    #  선정이 비면 그날은 발행하지 않는 편이 무관한 글을 올리는 것보다 낫다.
    if not selected:
        print("  -> 주제에 적합한 기사가 없어 선정 결과가 비었습니다(발행 없음).")
    elif len(selected) < want:
        print(f"  -> {len(selected)}개만 선정(요청 {want}개). 적합한 기사가 부족해 개수를 채우지 않습니다.")
    else:
        print(f"  -> {len(selected)}개 기사 선정 완료.")
    return selected


# 본문 작성 가이드라인 (기존 프롬프트 품질 기준을 그대로 계승)
_WRITING_GUIDE = """[작성 가이드라인 - 엄격 준수]
- [제목]: 원문 기사의 헤드라인이 말하는 사실을 충실히 옮긴 한국어 제목(60자 이내).
  - [원문 충실성 — 최우선 규칙]
    - 제목은 원문 헤드라인의 **주체·행위·대상**을 그대로 유지할 것. 원문이 "A가 B를 했다"면 제목도 그 사실을 말해야 한다.
    - 원문 기사에 **없는 내용을 제목에 새로 만들어 넣지 말 것.** 제목의 모든 요소는 기사에서 확인돼야 한다.
    - 원문 헤드라인을 번역하듯 옮기되, 한국 독자가 이해할 수 있게 표현만 자연스럽게 다듬는다.
  - [한국 언급 금지 — 필수]
    - **제목에 '한국', '국내', '우리', '정부', '공공', '당국'을 넣지 말 것.** 원문 기사가 실제로 한국(또는 한국 기관·기업)을 다루는 경우에만 예외로 허용한다.
    - 해외 기사에 한국 함의를 붙인 제목은 원문 왜곡이다. (금지 예: "에티오피아, 디지털 주권과 국가 동원…한국에 경고" / "수세, 인도에 오픈소스 AI 인프라…한국도 점검" / "AI가 앞지른 변화 속도…한국 보안정책 6주 전환")
    - 한국에 대한 함의는 본문의 마지막 불릿과 전문가 코멘트에서만 다룰 것. 제목은 사실 전달에 집중한다.
  - [과장 금지] 원문에 없는 평가어('비상', '경고', '위기', '붕괴', '충격')를 습관적으로 붙이지 말 것. 원문이 실제로 경고·긴급 대응을 다룰 때만 사용한다.
  - [말줄임표] 말줄임표(…)는 선택 사항이다. 쓸 경우 뒷절도 **반드시 원문 기사에 담긴 사실**이어야 하며, 추가 해석이나 파장 예측으로 채우지 말 것.
    - (좋은 예: Atlassian 'Rovo' 조작으로 Jira·Confluence 데이터 반출… 7월 8일 서버측 수정)
    - (나쁜 예: Atlassian 'Rovo' 데이터 반출… 공공기관 AI 도입 비상)
  - [종결 방식]
    - (기본) 제목은 명사/명사형(체언)으로 종결. 예: ~확보, ~전환, ~돌입, ~착수, ~공개, ~노출, ~격화, ~예고.
    - (허용) 부득이한 경우에만 현재형 동사 종결('~한다', '~밝혀', '~드러나')을 사용.
    - [절대 금지] '~함', '~됨', '~하였음', '~라고 함' 등 개조식 보고서체 종결. 헤드라인이 아니라 회의록처럼 읽히므로 절대 사용 금지.
  - 명사 나열 금지: 딱딱한 명사구 나열을 피하고 주체와 핵심 액션을 문장처럼 배치.
  - 핵심 정보 전면 배치: 사건의 주체(기업/기관)와 핵심 액션을 제목 앞부분에.
  - 인용부호 강조: 핵심 키워드·제품명·발언은 작은따옴표('')로 강조. (예: 팔로알토네트웍스 'PAN-OS' 치명적 결함 노출)
- [서브 헤드라인]: 파급효과 중심의 한 문장 요약(<h3> 사용).
- [핵심 내용 요약]: <ul><li> 구조 사용.
  - [다각적 분석 체계]: 반드시 정확히 6개의 <li> 항목을 다음 비중으로 구성.
    - ① 핵심 사건/기술 개요(2개): 기사 자체의 핵심 사건·기술 메커니즘·발표 실체를 육하원칙 기반으로 충실히 요약할 것. 기사 본문에 실제로 담긴 사실 위주로 서술하고 추측·확대해석은 배제.
    - ② 구체적 데이터 및 근거(1개): 기사에 언급된 실제 숫자(비율 %, 금액 $, 건수, 버전 번호, 공격 규모, 날짜, 벤치마크 점수 등)를 아라비아 숫자로 2개 이상 포함. 숫자 없이 "정량적 근거다"라고만 쓰는 것은 불합격이며, 원문에 수치가 부족하면 웹 조사로 해당 사건과 직접 관련된 통계·규모·시점을 찾아 보완할 것.
      - [수치 날조 금지] 인물 인터뷰·논평처럼 사건 자체에 통계가 없는 기사라면 숫자를 억지로 만들지 말 것. 이때는 발표·임명·발간 시점(연·월), 소속 기관, 직위, 논문·제품의 정확한 명칭 같은 '검증 가능한 특정 사실'로 이 항목을 채울 것.
      - [개수 세기 절대 금지] 기사에 등장한 고유명사·사실의 '개수'를 세어 "4개의 고유 사실이 연결된다", "5개 이상 고유명사가 등장한다"처럼 쓰는 것은 수치가 아니라 작성 규칙의 노출이며 가장 심각한 불합격 사유. 개수 대신 그 사실들의 내용을 직접 서술할 것.
    - ③ 영향 범위 전수 열거(1개): 이 사건의 피해 대상·적용 대상·영향 제품/버전이 3개 이상 식별되면, 이 항목을 그 대상의 '전수 열거'에 쓸 것. 독자의 첫 질문은 "우리가 그 명단에 있는가"이므로, 대상을 몇 개 골라 예시하지 말고 원문에서 확인되는 범위를 빠짐없이 담는다.
      - [열거 압축법] 범주별로 묶고 범주 안에서는 가운뎃점(·)으로 연결할 것. 쉼표는 범주 사이에만 쓴다. (예: "부산신항만(PNC)·BNCT 등 터미널 운영사와 삼주마리타임·동아탱커 등 선박 업체, GNCNet·DGT Busan 등 항만 IT 업체") 이 압축법을 쓰면 긴 열거도 쉼표 3개 안에 들어간다.
      - [마침표는 여전히 1개] 열거가 길어져도 문장을 쪼개지 말 것. 범주를 늘려 한 문장으로 이어간다.
      - [조건부 — 중요] 열거할 대상이 3개 미만이면 이 항목을 ④와 같은 성격(배경·파급)으로 쓰고 일반 길이를 지킬 것. 열거 대상이 없는데 분량을 채우려고 무관한 기업·제품 명칭을 끌어오는 것은 가장 심각한 불합격 사유다.
    - ④ 전략적 배경 및 파급효과(2개): 배경과 산업계/정책 영향을 분석(전체 6개 중 2개로 제한하여 배경·파급의 과다 서술을 방지). 반드시 대상 기사의 사건에서 직접 도출할 것이며, 무관한 다른 사건을 근거로 삼지 말 것.
  - [길이 엄수 — 최우선 규칙]: 각 <li>는 반드시 80~110자로 작성할 것. 원문에 정보가 많아도 가장 중요한 사실만 골라 담고 나머지는 과감히 생략하며, 절대 130자를 넘기지 말 것. 길이 초과는 정보 부족보다 더 심각한 불합격 사유이다.
    - [예외 — 전수 열거 불릿 1개만]: ③을 전수 열거에 쓰는 경우에만 150~220자를 허용한다. 이 예외는 6개 중 1개에만 적용되며, 130자를 넘는 불릿이 2개 이상이면 불합격이다.
  - [한 불릿 한 문장 — 최우선 규칙]: 각 <li>는 마침표가 하나인 한 문장으로 쓸 것. 하나의 사실을 주절로 세우고, 나머지는 연결어미(~며, ~고, ~자, ~는데, ~만큼)·관형절(~하는 X, ~인 X)·인용 통합(~라고 분석했다)으로 그 주절에 붙인다.
  - [문장 분리 금지 — 필수]: 발표 주체와 발표 내용을 두 문장으로 쪼개지 말 것.
    - (금지 예: "GTIG는 CVE-2026-1731을 실제 사례로 제시했다. Hacktron AI가 비인증 OS 명령 주입을 발견했다.")
    - (허용 예: "GTIG가 사례로 든 CVE-2026-1731은 Hacktron AI가 찾은 비인증 OS 명령 주입으로, 공개 4일 뒤 악용됐다.")
  - [액자 문장 금지 — 필수]: "~를 제시했다", "~를 발표했다", "~를 공개했다"처럼 사실 없이 틀만 만드는 문장으로 불릿을 시작하지 말 것. 액자를 걷어내고 내용부터 쓴다.
  - [두 문장 예외]: 두 사실이 인과·대조로 묶이지 않아 한 문장이 억지스러울 때만 두 문장을 허용하며, 이때 둘째 문장은 반드시 앞 문장을 받는 말(이·그·해당·이 가운데·그 결과·다만·반면·따라서)로 시작할 것. 새 주어로 불쑥 시작하는 둘째 문장은 불합격이다. 3문장 이상은 금지한다.
  - [주절 비대화 금지]: 한 문장에 쉼표가 5개를 넘으면 담은 사실이 너무 많다. 덜 중요한 사실을 버릴 것. 나열은 쉼표 대신 가운뎃점(·)으로 묶어 쉼표 수를 줄인다.
  - [정보 밀도]: 짧은 길이 안에서도 구체적 팩트(고유명사·기업명·기관명·제품/기술명·표준·수치·버전·날짜 등)를 2개 이상 담을 것.
  - [빈껍데기 금지 — 필수]: 아래와 같은 '내용 없는 문장'은 절대 금지.
    - 자기지시 표현: "~라는 정량적 근거다", "~이는 기사의 핵심이다", "기사에 따르면 ~라고 전한다"처럼 팩트 대신 팩트가 있다는 사실만 서술하는 문장.
    - 동어반복: 서브 헤드라인이나 앞선 불릿의 내용을 표현만 바꿔 되풀이하는 문장.
    - 원문에서 확인되는 구체 사실(누가·언제·무엇을·얼마나)로 반드시 채울 것.
  - [기사 지칭 금지 — 필수]: 독자는 원문을 읽지 않으므로 "원문은", "기사에는", "같은 기사에서", "기사에 인용된" 등 기사 자체를 가리키는 표현으로 문장을 시작하거나 서술하지 말 것. 사실을 주체(기업·기관·인물)를 주어로 삼아 직접 단언할 것. (금지 예: "기사에는 Flock의 코칭 자료가 담겨 있다." / 허용 예: "Flock의 코칭 자료는 시의원에게 비공개 사전 브리핑을 하도록 지시한다.")
  - [지시문 노출 금지 — 필수]: 이 지침에 쓰인 표현("80~110자", "최소 2개 숫자", "불릿", "정량 데이터", "가이드라인" 등)을 결과물 문장에 절대 포함하지 말 것. 작성 규칙은 결과물에 드러나서는 안 되며, 독자에게는 완성된 분석문만 보여야 한다.
  - [해석의 출처 귀속 — 필수]: 사건의 의미·전망·권고는 가능하면 원문에 등장하는 취재원·기관의 발언으로 귀속해 전달할 것. ("보안업계 관계자는 ~라고 지적했다", "ENISA는 ~라고 권고했다", "GTIG는 ~라고 전망했다")
    - 귀속하면 누가 그렇게 판단했는지가 남아 분석의 책임 소재가 분명해지고, 원문에 없는 처방을 만들어 넣을 여지가 줄어든다.
    - 원문에 그런 발언이 없을 때만 자체 분석으로 서술한다.
  - [처방의 위치 — 필수]: "정부는 ~해야 한다", "~을 의무화해야 한다" 같은 행동 처방은 <blockquote> 전문가 코멘트에만 둘 것. 마지막 불릿은 처방이 아니라 '이 사건이 한국 산업·정책에 미치는 영향'을 사실 기반으로 분석한다.
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


# 이 길이 미만이면 원문 전문이 아니라 RSS 발췌로 보고 웹 조사를 함께 지시한다.
PARTIAL_SOURCE_LEN = 800


def _build_article_prompt(candidate, src_url, source_text, retry_feedback=""):
    """본문 생성용 프롬프트를 조립한다. retry_feedback이 있으면 재생성 지시를 덧붙인다.

    원문 확보 정도에 따라 지시가 달라진다. 전문을 확보했으면 그것을 1차 근거로 못박고,
    발췌뿐이거나 아예 없으면 같은 사건에 한정한 웹 조사를 함께 요구한다."""
    if len(source_text) >= PARTIAL_SOURCE_LEN:
        source_block = f"""[기사 원문 — 아래 사실이 1차 근거이며, 여기 있는 수치·고유명사를 최대한 활용하십시오]
{source_text}
"""
    elif source_text:
        source_block = f"""[기사 발췌 — 원문 전체를 가져오지 못해 일부만 확보했습니다]
{source_text}

- 위 발췌만으로는 6개 불릿을 채울 수 없습니다. **반드시 위 출처 URL과 제목을 웹에서 조사해 이 사건의 구체적 사실을 추가 확보한 뒤 작성하십시오.**
- 조사할 항목: 발표·공개 주체와 시점, 조사 대상과 표본 규모, 구체적 수치와 비율, 등장하는 기업·기관·연구진 이름, 영향 범위, 후속 조치.
- 단, 조사 범위는 '이 사건' 하나로 한정하며, 다른 사건을 끌어와 분량을 채우지 마십시오.
- 조사로도 확인되지 않는 사실은 지어내지 말고, 확인된 사실을 더 깊이 서술하십시오.
"""
    else:
        source_block = """[기사 원문]
- 원문 자동 추출에 실패했습니다. 반드시 위 출처 URL과 제목을 웹에서 조사해 실제 사실을 확보한 뒤 작성하십시오.
- 조사 범위는 '이 사건' 하나로 한정하며, 다른 사건을 끌어와 분량을 채우지 마십시오.
- 조사로도 사실이 확인되지 않으면 추측으로 채우지 말고, 확인된 범위의 사실과 도메인 지식으로 정확하게 서술하십시오.
"""

    retry_block = ""
    if retry_feedback:
        retry_block = f"""
[재작성 요구 — 직전 결과가 아래 사유로 불합격했습니다. 반드시 교정하십시오]
{retry_feedback}
"""

    return f"""당신은 글로벌 보안 인텔리전스 기업의 '수석 분석가'이자 복잡한 기술 이슈를 정책적 가치로 전환하는 '보안 에듀케이터'입니다.
아래 기사 원문을 근거로, 한국 정부 보안 정책 담당자가 즉각적 의사결정에 활용할 수 있는 분석을 작성하십시오.

[독자 페르소나: 한국 정부 정책 담당자]
- 기술 디테일보다 "이 변화가 한국 보안 산업 육성과 국가 안보에 어떤 기회·위기인가"를 파악하고자 함.
- 비전문가도 이해하도록 IT 전문 용어는 정책적 의미로 치환해 서술.

{_WRITING_GUIDE}

[대상 기사]
- 제목: {candidate.get('title','')}
- 출처 URL: {src_url}

{source_block}
[서술 지침 — 매우 중요]
- [길이 최우선] 각 불릿은 반드시 80~110자로 쓰고 절대 130자를 넘기지 마십시오. 원문 정보가 많아도 핵심 사실만 남기고 나머지는 과감히 생략하십시오. 길이 초과는 정보 부족보다 더 심각한 문제입니다.
- [전수 열거 불릿] 피해 대상·적용 대상·영향 제품이 3개 이상 식별되면 3번째 불릿을 그 대상의 전수 열거에 쓰고, 이 불릿에만 150~220자를 허용합니다. 범주별로 묶어 범주 안에서는 가운뎃점(·)으로 연결하고 쉼표는 범주 사이에만 쓰십시오. 열거 대상이 3개 미만이면 이 불릿을 배경·파급으로 쓰고 일반 길이를 지키십시오.
- [해석은 귀속] 의미·전망·권고는 원문의 취재원·기관 발언으로 귀속해 전달하십시오("~관계자는 ~라고 지적했다"). 원문에 그런 발언이 없을 때만 자체 분석으로 쓰고, "정부는 ~해야 한다" 같은 행동 처방은 전문가 코멘트에만 두십시오.
- [한 불릿 한 문장] 각 불릿은 마침표가 하나인 한 문장으로 쓰십시오. 하나의 사실을 주절로 세우고, 나머지는 연결어미(~며, ~고, ~자, ~는데, ~만큼)·관형절(~하는 X, ~인 X)·인용 통합(~라고 분석했다)으로 주절에 붙이십시오.
- 발표 주체와 발표 내용을 두 문장으로 쪼개지 마십시오. "~를 제시했다/발표했다"처럼 사실 없이 틀만 만드는 액자 문장으로 불릿을 시작하지 마십시오.
- 두 사실이 인과·대조로 묶이지 않을 때만 두 문장을 허용하며, 둘째 문장은 반드시 앞 문장을 받는 말(이·그·해당·이 가운데·그 결과·다만·반면)로 시작해야 합니다. 3문장 이상은 금지입니다.
- 나열은 쉼표 대신 가운뎃점(·)으로 묶고, 한 문장에 쉼표가 5개를 넘지 않게 하십시오.
- 짧은 길이 안에서도 구체적 팩트(고유명사·제품·기관·수치·버전 등)를 2개 이상 담으십시오.
- 원문에 담긴 숫자(금액·비율·건수·버전·날짜·규모)는 버리지 말고 본문에 그대로 옮기십시오. 숫자는 이 분석의 신뢰도를 결정하는 핵심 자산입니다.
- [단일 사건 원칙 — 최우선 규칙]: 이 글은 위 '대상 기사' 1건의 사건만 다룹니다. 6개 불릿 전부가 그 하나의 사건을 설명해야 하며, 별개의 사건·다른 기사·무관한 통계를 끌어와 섞는 것은 가장 심각한 오류입니다. 마지막 불릿의 '한국에 대한 함의'도 반드시 이 사건에서 도출하십시오.
- 웹 조사는 오직 '대상 기사에 등장하는 사실'의 확인·보강(해당 기업의 규모, 그 취약점의 CVE 번호, 그 발표의 배경 등)에만 사용하고, 새로운 사건을 가져오는 데 쓰지 마십시오.
- 분량이 부족하면 다른 사건으로 채우지 말고, 같은 사건의 경위·메커니즘·이해관계자·후속 조치를 더 깊이 파고들어 채우십시오.
- 팩트 대신 "~라는 정량적 근거다", "~이 기사의 핵심이다" 같은 자기지시 문장으로 분량을 채우는 것은 불합격 사유입니다.
- 각 불릿은 문법적으로 완결된 한 문장이어야 합니다. 쉼표로 두 절을 잇는 비문("~밝혔다, 이는 ~")을 쓰지 마십시오.
{retry_block}
아래 세 필드를 생성하십시오.
- title: 위 '대상 기사'의 원문 제목이 말하는 사실을 충실히 옮긴 한국어 헤드라인(60자 이내).
  원문에 없는 내용을 넣지 말고, 특히 **'한국·국내·정부·공공'을 제목에 붙이지 마십시오**(원문이 실제로 한국을 다루는 경우만 예외).
  한국에 대한 함의는 본문 마지막 불릿과 전문가 코멘트에서 다루십시오.
- content: <h3>서브헤드라인</h3><ul><li>…6개(사건개요 2·정량데이터 1·영향범위 전수열거 1·배경파급 2), 각 80~110자이고 전수 열거 불릿만 150~220자이며 마침표는 모두 1개…</li></ul><blockquote>전문가 코멘트</blockquote><p><strong>주요 용어:</strong> 용어(의미), 용어(의미)</p> 형식의 HTML 문자열. **출처(<a>) 링크 줄은 넣지 마십시오(시스템이 자동으로 추가합니다).**
- tags: 핵심 키워드 5개.
"""


# 팩트 없이 분량만 채우는 자기지시 표현(품질 검사에서 불합격 사유)
#  '핵심 수치인'은 실제 숫자가 없을 때 억지로 수치처럼 포장하는 상투구라 함께 잡는다.
_HOLLOW_PAT = re.compile(
    r"(정량적 근거(이)?다|기사의 핵심은|기사에 따르면|보도했다는 점|라고 전한다|"
    r"시사하는 바가 크다|주목할 필요가 있다|핵심 (수치|숫자)[는이]|정량 지표는)"
)

# 독자가 원문을 읽지 않는데도 기사·제목을 가리키는 표현(직접 서술로 교체 대상)
_META_REF_PAT = re.compile(
    r"(원문은|원문에는|원문에서는|기사에는|기사에서는|기사 발췌|발췌에 따르면|같은 기사에서|"
    r"기사에 인용된|본 기사|라는 제목|제목처럼|보도한 바에|해당 매체는)"
)

# 불릿을 문장 단위로 분리한다(종결어미 '다.' 기준).
_BULLET_SENT_SPLIT = re.compile(r"(?<=다\.)\s+|(?<=다\.)(?=[가-힣A-Z(])")

# 둘째 문장이 앞 문장을 받는지 판정한다. 이 말로 시작하지 않으면 연결이 끊긴 병치다.
#  '이'·'그'류는 뒤에 공백을 요구해 '이스라엘은'·'그린필드'를 오탐하지 않게 한다.
_CONNECTIVE_PAT = re.compile(
    r"^((이|그|해당|같은|이런|그런|이러한|그러한)\s|이를|이로|이에|이와|"
    r"그 결과|이 가운데|그러나|다만|반면|따라서|한편|특히|또한|아울러|결국|동시에)"
)

# 사실 없이 틀만 만드는 선행 문장. 짧은 것만 잡아 정보가 든 문장은 통과시킨다.
#  (실제 사례: "GTIG는 CVE-2026-1731을 실제 사례로 제시했다." 33자)
_SCAFFOLD_PAT = re.compile(r"^.{0,45}?(제시했다|발표했다|공개했다|분석했다|내놓았다|보고했다)\.$")

# 한국어 본문에 올 이유가 없는 문자(생성 중 다른 언어가 새어 나온 흔적).
#  실제 사례: 2026-10-01자 CRA 기사의 "조치 उपलब्ध 후 14일 내".
#  한자는 정상 표기로 쓰일 수 있어 제외하고, 데바나가리·키릴·아랍·히브리·태국·가나만 잡는다.
_FOREIGN_SCRIPT_PAT = re.compile(
    r"[\u0900-\u097F\u0400-\u04FF\u0600-\u06FF\u0590-\u05FF\u0E00-\u0E7F\u3040-\u30FF]"
)

# 종결어미 뒤에 쉼표로 다음 절을 이어붙인 비문("~밝혔다, 이는 ~")
_COMMA_SPLICE_PAT = re.compile(r"(했다|밝혔다|이다|였다|었다|된다|한다|졌다|난다|왔다|린다),\s")

# 작성 지침이 결과물에 새어 나온 흔적(명백한 결함이므로 반드시 재생성).
#  '가이드라인'·'정량 데이터'는 보안 정책 글에서 정상적으로 쓰이는 어휘이므로 제외한다.
#  (실제 오탐 사례: "보안 조달·가이드라인에 반영해야 한다")
_RUBRIC_LEAK_PAT = re.compile(
    r"(\d{2,3}\s*~\s*\d{3}\s*자|\d+\s*자 내외|최소 \d+개 숫자|\d+개 이상 고유명사|"
    r"\d+개의? 고유 ?(사실|명사)|고유명사가 등장|불릿|작성 지침|육하원칙|서브 헤드라인)"
)

# 임계값은 실제 게시물 표본으로 보정했다.
#  - 부실 사례(2026-08-06자): 불릿 81~88자, 합계 512자
#  - 개선 후 출력: 불릿 113~142자, 합계 769자
# 두 분포 사이에 문턱을 두어, 정상 품질에는 불필요한 재생성(API 2배 비용)이 걸리지 않게 한다.
# 프롬프트가 모델에 제시하는 목표는 80~110자(마침표 1개)이며, 아래 합격 창은 그보다 넓다.
#  프롬프트의 길이 문구를 바꿀 때는 이 상수들과 재생성 피드백 문구(80~110자)를
#  함께 맞춰야 한다. 예전에 지시가 100~130 / 150~200 / 130~170으로 갈려 있었다.
#  목표를 85~115에서 80~110으로 내린 근거: 1문장 전환 후 실측 분포가 60~111자,
#  중앙 81자였다(2026-10-10~13 불릿 192개). 85자 하한은 62%가 미달해 지시가
#  현실과 어긋나 있었다.
#  열거 불릿만 상한을 따로 둔다. 역할에 따라 필요한 분량이 2배까지 차이 나는데,
#  단일 상한을 쓰면 '피해 대상 전수 열거'가 구조적으로 불가능해진다
#  (참고 사례: 국내 항만·해운 9곳 명단 193자, 고유명사 18개, 쉼표 3개).
MIN_BULLET_LEN = 70        # 개별 불릿 하한
MAX_BULLET_LEN = 130       # 일반 불릿 상한(초과 시 주절 비대로 간주해 재생성 유도)
MAX_LIST_BULLET_LEN = 220  # 전수 열거 불릿 1개에만 허용하는 상한
MIN_TOTAL_LEN = 480    # 불릿 합계 하한(개별은 통과해도 전체 분량이 얇은 경우를 잡는다)
MIN_DIGIT_BULLETS = 1  # 아라비아 숫자를 포함해야 하는 불릿의 최소 개수


# 제목에 들어가면 안 되는 '한국 함의' 표현. 원문이 한국을 다루는 기사에서는
# 본문에 한국 기관명이 실제로 등장하므로, 호출부에서 그 경우를 예외 처리한다.
_TITLE_KOREA_PAT = re.compile(r"(한국|국내|우리나라|정부|공공|당국|과기정통부|KISA)")


def _inspect_title(title, body=""):
    """제목이 원문 사실에 충실한지 검사한다.

    해외 기사에 '…한국에 경고'처럼 한국 함의를 붙이는 것은 원문 왜곡이므로 막는다.
    실제로 한국을 다룬 기사(본문에 한국이 반복 등장)는 예외로 통과시킨다."""
    reasons = []
    if not title:
        return ["- 제목이 비어 있습니다."]

    hit = _TITLE_KOREA_PAT.search(title)
    if hit:
        # 본문에서 한국이 2회 이상 언급되면 기사 자체가 한국 사안으로 보고 허용
        korea_in_body = len(re.findall(r"한국|국내|우리나라", re.sub(r"<[^>]+>", " ", body)))
        if korea_in_body < 2:
            reasons.append(
                f"- 제목에 '{hit.group()}'이(가) 들어갔습니다. 원문이 한국을 다루지 않는데 한국 함의를 붙이면 "
                f"원문 왜곡입니다. 제목에서 빼고 원문 사실만 쓰십시오(한국 함의는 본문에서 다룸)."
            )

    if len(title) > 60:
        reasons.append(f"- 제목이 {len(title)}자로 60자를 넘었습니다.")

    if re.search(r"(함|됨|하였음|라고 함)$", title.strip()):
        reasons.append("- 제목이 개조식 보고서체로 끝납니다. 명사형(체언)으로 종결하십시오.")

    return reasons


def _inspect_article_quality(body):
    """생성된 HTML 본문의 정보 밀도를 검사해 불합격 사유 목록을 반환한다.

    반환값이 빈 리스트이면 합격. 사유가 있으면 호출부가 그 문구를 그대로
    재생성 프롬프트에 넣어 모델에 무엇이 부족했는지 알린다."""
    reasons = []
    bullets = [re.sub(r"<[^>]+>", "", b).strip() for b in re.findall(r"<li>(.*?)</li>", body, re.S)]

    if len(bullets) < 6:
        reasons.append(f"- 불릿이 {len(bullets)}개뿐입니다. 반드시 6개(사건개요 3·정량데이터 1·배경파급 2)를 작성하십시오.")

    short = [b for b in bullets if len(b) < MIN_BULLET_LEN]
    if short:
        reasons.append(
            f"- {len(short)}개 불릿이 {MIN_BULLET_LEN}자 미만으로 정보가 빈약합니다"
            f"(가장 짧은 것: {len(short[0])}자 \"{short[0][:40]}…\"). 모든 불릿을 80~110자로 채우십시오."
        )

    # 전수 열거 불릿 1개는 MAX_LIST_BULLET_LEN 까지 허용한다. 가장 긴 것 하나를
    # 열거 불릿으로 간주하므로 위치를 몰라도 판정할 수 있고, 열거를 쓰지 않은 날은
    # 자연히 전부 일반 상한으로 검사된다.
    long_b = sorted((b for b in bullets if len(b) > MAX_BULLET_LEN), key=len, reverse=True)
    if long_b:
        if len(long_b[0]) > MAX_LIST_BULLET_LEN:
            reasons.append(
                f"- 가장 긴 불릿이 {len(long_b[0])}자로 전수 열거 상한({MAX_LIST_BULLET_LEN}자)마저 넘었습니다. "
                f"열거 범주를 줄이거나 덜 중요한 대상을 버리십시오(문장을 쪼개지 말 것)."
            )
        if len(long_b) > 1:
            reasons.append(
                f"- {MAX_BULLET_LEN}자를 넘는 불릿이 {len(long_b)}개입니다"
                f"(가장 긴 것: {len(long_b[0])}자). 길게 쓸 수 있는 것은 전수 열거 불릿 1개뿐이므로, "
                f"나머지는 80~110자로 줄이십시오(문장을 쪼개지 말 것)."
            )

    total = sum(len(b) for b in bullets)
    if bullets and total < MIN_TOTAL_LEN:
        reasons.append(
            f"- 불릿 전체 분량이 {total}자로 기준({MIN_TOTAL_LEN}자)에 미달합니다. "
            f"원문의 수치·고유명사·경위를 더 끌어와 각 불릿을 80~110자로 확장하십시오."
        )

    # [한 불릿 한 문장] 두 문장을 연결어 없이 붙이면 논리가 끊긴다(2026-10-01 실측 94%).
    split_bullets = [(b, [x.strip() for x in _BULLET_SENT_SPLIT.split(b) if x.strip()])
                     for b in bullets]

    disjoint = [(b, sn) for b, sn in split_bullets
                if len(sn) >= 2 and not _CONNECTIVE_PAT.match(sn[1])]
    if disjoint:
        _, sn = disjoint[0]
        reasons.append(
            f"- {len(disjoint)}개 불릿이 두 문장을 연결어 없이 붙여 놓았습니다"
            f"(예: \"… {sn[0][-24:]} / {sn[1][:30]}…\"). 연결어미(~며, ~고, ~자, ~는데, ~만큼)나 "
            f"관형절로 한 문장으로 합치고, 불가피할 때만 둘째 문장을 '이·그·해당·그 결과·다만·반면'으로 시작하십시오."
        )

    triple = [b for b, sn in split_bullets if len(sn) >= 3]
    if triple:
        reasons.append(
            f"- {len(triple)}개 불릿이 3문장 이상입니다. 한 문장으로 합치십시오."
        )

    scaffold = [sn[0] for b, sn in split_bullets if len(sn) >= 2 and _SCAFFOLD_PAT.match(sn[0])]
    if scaffold:
        reasons.append(
            f"- {len(scaffold)}개 불릿이 사실 없이 틀만 만드는 문장으로 시작합니다"
            f"(예: \"{scaffold[0]}\"). 액자를 걷어내고 내용부터 쓰십시오."
        )

    comma_heavy = [b for b in bullets if b.count(",") >= 5]
    if comma_heavy:
        reasons.append(
            f"- {len(comma_heavy)}개 불릿이 쉼표 5개 이상으로 주절이 비대합니다. "
            f"나열은 가운뎃점(·)으로 묶고 덜 중요한 사실을 버리십시오."
        )

    foreign = [b for b in bullets if _FOREIGN_SCRIPT_PAT.search(b)]
    if foreign:
        ch = _FOREIGN_SCRIPT_PAT.search(foreign[0]).group()
        reasons.append(
            f"- {len(foreign)}개 불릿에 한국어 본문에 올 수 없는 문자('{ch}')가 섞였습니다. "
            f"해당 부분을 한국어로 다시 쓰십시오."
        )

    with_digits = [b for b in bullets if re.search(r"\d", b)]
    if len(with_digits) < MIN_DIGIT_BULLETS:
        reasons.append("- 아라비아 숫자가 포함된 불릿이 없습니다. 금액·비율·건수·버전·날짜·규모 중 최소 2개를 실제 숫자로 제시하십시오.")

    hollow = [b for b in bullets if _HOLLOW_PAT.search(b)]
    if hollow:
        reasons.append(
            f"- {len(hollow)}개 불릿이 팩트 대신 자기지시 표현으로 채워져 있습니다"
            f"(예: \"{hollow[0][:50]}…\"). 해당 문장을 실제 사실로 교체하십시오."
        )

    meta = [b for b in bullets if _META_REF_PAT.search(b)]
    if meta:
        reasons.append(
            f"- {len(meta)}개 불릿이 '원문은/기사에는' 등 기사 자체를 지칭하는 표현을 씁니다"
            f"(예: \"{meta[0][:50]}…\"). 기업·기관·인물을 주어로 삼아 사실을 직접 단언하십시오."
        )

    splice = [b for b in bullets if _COMMA_SPLICE_PAT.search(b)]
    if splice:
        reasons.append(
            f"- {len(splice)}개 불릿이 종결어미 뒤에 쉼표로 절을 이어붙인 비문입니다"
            f"(예: \"{splice[0][:60]}…\"). '~하며', '~고' 등 연결어미로 자연스럽게 이으십시오."
        )

    leak = [b for b in bullets if _RUBRIC_LEAK_PAT.search(b)]
    if leak:
        reasons.append(
            f"- {len(leak)}개 불릿에 작성 지침 용어가 그대로 노출됐습니다"
            f"(예: \"{leak[0][:60]}…\"). 규칙 표현을 삭제하고 기사 내용만 서술하십시오."
        )

    return reasons


def generate_article(candidate):
    """[2단계] 선정된 기사 1건에 대해 제목/HTML본문/태그를 구조화 출력으로 생성한다.
    응답이 작아 잘림이 없고, 한 건이 실패해도 나머지 기사에는 영향이 없다(장애 격리).

    원문 본문을 직접 스크래핑해 프롬프트에 주입하고, 생성 결과의 정보 밀도를 검사해
    미달이면 불합격 사유를 알려 1회 재생성한다."""
    src_url = candidate.get("link", "")
    # 구글 뉴스 리다이렉트 URL이면 원문 기사 URL로 해제한다.
    #  → 출처명(매체)·대표 이미지·Perplexity 조사 모두 'Google'이 아닌 원본 기준으로 동작한다.
    if src_url and "news.google.com" in src_url.lower():
        resolved = resolve_google_url(src_url, deep=True)
        if resolved and "news.google.com" not in urlparse(resolved).netloc.lower():
            print(f"  -> 구글 URL 원문 해제: {_source_name_from_url(resolved)}")
            src_url = resolved

    # 원문 본문 확보(실패 시 RSS 요약으로 폴백, 둘 다 없으면 웹검색에만 의존)
    source_text = fetch_article_text(src_url)
    if source_text:
        print(f"  -> 원문 추출 성공({len(source_text)}자): {candidate.get('title','')[:30]}")
    else:
        rss_summary = re.sub(r"<[^>]+>", " ", candidate.get("rss_summary", "") or "")
        source_text = re.sub(r"\s+", " ", rss_summary).strip()[:2000]
        if source_text:
            print(f"  -> 원문 추출 실패 → RSS 요약({len(source_text)}자) 사용: {candidate.get('title','')[:30]}")
        else:
            print(f"  -> 원문·RSS 요약 모두 없음 → 웹검색 의존: {candidate.get('title','')[:30]}")

    def _call(feedback=""):
        data = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": "보안 뉴스 분석 전문가입니다. 반드시 지정된 JSON 스키마로만 답합니다."},
                {"role": "user", "content": _build_article_prompt(candidate, src_url, source_text, feedback)},
            ],
            "max_tokens": 6000,
            "response_format": {"type": "json_schema", "json_schema": {"schema": _CONTENT_SCHEMA}},
        }
        parsed = _parse_lenient(_pplx_chat(data, timeout=180))
        if not isinstance(parsed, dict) or not parsed.get("title") or not parsed.get("content"):
            raise ValueError("본문 생성 결과가 유효하지 않음")
        return parsed

    def _all_reasons(p):
        """제목과 본문을 함께 검사한다(제목의 억지 한국 함의도 재생성 사유)."""
        body_html = str(p.get("content", ""))
        return _inspect_title(str(p.get("title", "")), body_html) + _inspect_article_quality(body_html)

    parsed = _call()
    reasons = _all_reasons(parsed)
    if reasons:
        print(f"  -> 품질 미달로 재생성: {candidate.get('title','')[:30]} ({len(reasons)}개 사유)")
        _stat('regenerated')
        try:
            retried = _call("\n".join(reasons))
            # 재생성이 더 나빠질 수 있으므로 사유가 줄어든 경우에만 채택
            if len(_all_reasons(retried)) < len(reasons):
                parsed = retried
        except Exception as e:
            print(f"  -> 재생성 실패, 1차 결과 사용: {e}")

    title = str(parsed["title"]).strip()
    body = str(parsed["content"]).strip()
    tags = [str(t).strip() for t in (parsed.get("tags") or []) if str(t).strip()][:5]
    # 출처 줄은 정확한 URL로 프로그램에서 부착(모델의 URL 환각 차단)
    src_name = candidate.get("source_name") or _source_name_from_url(src_url)
    body += f"<p>출처: <a href='{src_url}' target='_blank'>{src_name}</a></p>"
    return {
        "title": title,
        "content": body,
        "tags": tags,
        "image_url": candidate.get("rss_image") or "",
        "source_url": src_url,
        "source_name": src_name,
    }


def analyze_news_with_perplexity(news_list, recent_titles, recent_urls=None):
    """[리팩터링] 2단계 파이프라인으로 최상급 품질·고신뢰 뉴스 분석을 수행한다.
      1단계 select_top_news : 상위 10개 선정(작은 구조화 출력 → 잘림/깨짐 없음)
      2단계 generate_article: 기사별 본문 생성(작은 응답 → 잘림 없음, 실패는 건별 격리)
    구조화 출력(json_schema)으로 JSON 무결성을 API가 보장한다."""
    if not news_list:
        return []
    limited_news = news_list[:40]
    print(f"Perplexity AI 분석 중 ({len(limited_news)}개 후보)...")

    selected = select_top_news(limited_news, recent_titles, want=10, recent_urls=recent_urls)
    total = len(selected)

    # 2단계는 서로 독립적인 호출이므로 병렬 실행(Perplexity 분당 요청 한도 회피를 위해 워커 2개).
    #  - 품질 미달 재생성 로직이 호출 수를 늘리므로 동시성을 낮춰 429(Too Many Requests)를 예방
    #  - 순서 보존: 인덱스로 결과를 슬롯에 채운 뒤 성공분만 순서대로 수집
    #  - 장애 격리: 한 건 예외는 해당 슬롯만 None 처리하고 나머지는 정상 진행
    def _worker(idx, cand):
        return idx, generate_article(cand)

    slots = [None] * total
    auth_error = None
    max_workers = min(2, total) or 1
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
            except PerplexityAuthError as e:
                # 인증·쿼터 오류는 남은 건도 전부 실패한다. 건별 격리 대상이 아니다.
                auth_error = e
                print(f"  -> [{done}/{total}] 인증/쿼터 오류: {e}")
            except Exception as e:
                print(f"  -> [{done}/{total}] 본문 생성 실패(건너뜀): {label} ({e})")

    if auth_error:
        raise auth_error

    results = [a for a in slots if a]
    _stat('selected', len(results))
    _stat('gen_failed', total - len(results))
    print(f"최종 {len(results)}개 기사 생성 완료.")
    return results


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
        sys.exit(1)
    init_session()
    
    recent_titles, recent_urls = get_recent_posts_info()
    news_list = get_rss_news(recent_urls)

    # [1차 방어] 이미 게시된 출처 URL을 가진 후보를 AI 분석 전에 사전 제거
    if recent_urls:
        before = len(news_list)
        news_list = [n for n in news_list if normalize_url(n.get('link')) not in recent_urls]
        removed = before - len(news_list)
        if removed:
            print(f"  -> 이미 게시된 기사 {removed}개를 후보에서 사전 제외했습니다.")

    try:
        selected_news = analyze_news_with_perplexity(news_list, recent_titles, recent_urls)
    except PerplexityAuthError as e:
        # 트레이스백만 남기면 로그에서 원인을 찾기 어렵다. 조치 방법까지 적고 실패시킨다.
        print(f"[치명] Perplexity 인증/쿼터 오류로 중단합니다: {e}")
        print("  -> 크레딧 잔액과 API 키를 확인하세요:"
              " https://console.perplexity.ai/project/billing")
        sys.exit(1)

    if not selected_news:
        # 0건은 정상 완료가 아니다. 종료 코드를 남겨 워크플로를 실패시킨다.
        print("선정된 뉴스가 없습니다.")
        sys.exit(1)

    # 뉴스 선정 결과 저장
    save_selected_news_to_json(selected_news)

    # [2차 방어] 포스팅 직전 출처 URL 기준 최종 중복 가드
    #  - recent_urls: 과거(교차일) 중복 차단
    #  - posted_this_run: 같은 실행 배치 내에서 AI가 동일 기사를 중복 선정한 경우 차단
    posted_this_run = set()
    dup_skipped = 0
    post_ok = 0
    post_fail = 0
    for news in selected_news:
        norm = normalize_url(news.get('source_url'))
        if norm and norm in recent_urls:
            print(f"  -> [중복 건너뜀] 이미 게시된 기사: {news.get('title')}")
            dup_skipped += 1
            continue
        if norm and norm in posted_this_run:
            print(f"  -> [중복 건너뜀] 이번 실행에서 중복 선정된 기사: {news.get('title')}")
            dup_skipped += 1
            continue
        try:
            post_to_wordpress(news, news_list)
            if norm:
                posted_this_run.add(norm)
            post_ok += 1
            _stat('posted')
            _stat('topic_' + classify_topic(news.get('title', '')))
            for b in re.findall(r"<li>(.*?)</li>", str(news.get('content', '')), re.S):
                _stat('bullet_count')
                _stat('bullet_chars', len(re.sub(r"<[^>]+>", "", b).strip()))
            time.sleep(5)
        except Exception as e:
            print(f"처리 중 오류: {e}")
            post_fail += 1

    # [요약] 왜 최종 게시 수가 목표(10)와 다른지 로그에 한눈에 남긴다.
    generated = len(selected_news)
    print(
        f"[요약] 선정 목표 10 → 생성 성공 {generated} "
        f"(생성 단계 드롭 {10 - generated}) → 중복 탈락 {dup_skipped} → "
        f"게시 성공 {post_ok}"
        + (f", 게시 실패 {post_fail}" if post_fail else "")
    )
    _stat('dup_posted', dup_skipped)
    print_run_metrics()

    # 한 건도 올리지 못했다면 success로 끝내지 않는다. 뉴스가 없는 날과
    # 파이프라인이 깨진 날을 워크플로 결과만으로 구분할 수 있어야 한다.
    if post_ok == 0:
        print("게시 성공 0건 → 실패로 종료합니다.")
        sys.exit(1)

if __name__ == "__main__":
    main()
