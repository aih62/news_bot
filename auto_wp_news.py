import feedparser
import requests
import json
import re
from requests.auth import HTTPBasicAuth
import time
import os
import html
import urllib3
import io
from PIL import Image
from urllib.parse import quote, urljoin
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
GUARANTEED_MEDIA_ID = 3221 
DEFAULT_IMAGE_URL = "http://ajken.mycafe24.com/wp-content/uploads/2026/03/thedigitalartist-security-4868167_1920.jpg"

# 공통 헤더
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
    """기사 원본 주소에서 og:image 또는 twitter:image 태그를 추출합니다."""
    if not url or not url.startswith("http"): return None
    try:
        res = requests.get(url, timeout=10, headers=COMMON_HEADERS, verify=False)
        if res.status_code == 200:
            html_content = res.text
            # og:image 추출
            match = re.search(r'<meta [^>]*property=["\']og:image["\'] [^>]*content=["\']([^"\']+)["\']', html_content)
            if not match:
                match = re.search(r'<meta [^>]*content=["\']([^"\']+)["\'] [^>]*property=["\']og:image["\']', html_content)
            
            # twitter:image 추출
            if not match:
                match = re.search(r'<meta [^>]*name=["\']twitter:image["\'] [^>]*content=["\']([^"\']+)["\']', html_content)
            if not match:
                match = re.search(r'<meta [^>]*content=["\']([^"\']+)["\'] [^>]*name=["\']twitter:image["\']', html_content)
            
            if match:
                img_url = match.group(1)
                if img_url.startswith('/'): img_url = urljoin(url, img_url)
                return img_url
    except: pass
    return None

def get_rss_news():
    """feeds.json에서 직접 RSS 피드와 검색 카테고리를 읽어와 최신 기사 목록을 가져옵니다."""
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
                        "title": entry.title,
                        "link": entry.link,
                        "published": getattr(entry, 'published', time.ctime()),
                        "search_category": f"Expert_{source_name}",
                        "rss_image": extract_image(entry)
                    })
                    seen_links.add(entry.link)
        except: pass

    for category_name, keywords in search_categories.items():
        query = " OR ".join([f'"{k}"' if " " in k else k for k in keywords])
        rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            feed = feedparser.parse(rss_url)
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
        except: pass
            
    print(f"총 {len(all_entries)}개의 기사 수집 완료.")
    return all_entries

def analyze_news_with_perplexity(news_list, recent_titles):
    """Perplexity AI를 사용하여 최상급 품질의 뉴스 분석을 수행합니다."""
    if not news_list: return []
    limited_news = news_list[:40]
    print(f"Perplexity AI 분석 중 ({len(limited_news)}개 기사 분석)...")
    
    headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}

    prompt = f"""
    너는 글로벌 보안 인텔리전스 기업의 '수석 분석가'이자 친절한 보안 에듀케이터야.

    다음은 주어진 뉴스 리스트 중에서 **글로벌(해외) 보안 뉴스 상위 10개**를 선정해
    한국 정부 정책 담당자가 빠르게 동향을 파악할 수 있도록 뉴스의 핵심사항을 요약해야 하는 작업이다.

    **※ 중복 방지 주의사항:**
    다음 리스트는 이미 워드프레스에 포스팅된 최신 뉴스 제목들이다:
    {json.dumps(recent_titles, ensure_ascii=False)}
    **위 리스트에 포함된 제목과 동일하거나, 아주 유사한 사건을 다루는 뉴스는 절대 이번 선정 대상에 포함하지 말 것.**

    **※ 주의: 한국 국내 뉴스나 정책은 선정에서 제외하고, 철저히 글로벌 동향 및 국제 규제 위주로 선정할 것.**


    [선정 기준]
    1. 심각성: 글로벌 보안 사고나 취약점의 기술적 위험 수준
    2. 시급성: 즉각적인 대응이나 패치가 필요한 긴급성
    3. 영향력: 대규모 인프라, 기업, 국가 단위의 글로벌 파급력
    4. 정책성: 해외 주요국(미국, EU 등)의 법규, 규제, 정부 정책 등 제도적 변화 여부
    5. 미래가치: 향후 글로벌 보안 패러다임 변화에 대한 시사점


    [독자 페르소나]
    - 독자는 기술 전문가가 아닌 한국 정부의 사이버보안 정책 담당자이다.
    - 독자는 "이 사건이 왜 중요하고, 우리 정책에 어떤 시사점이 있는가"를 알고 싶어한다.
    - 따라서 기술 용어는 반드시 쉬운 말로 풀어쓰고, 정책·외교·경제적 맥락을 강조해 줄 것.


    [각 뉴스 작성 형식]

    [제목]
    - 이 사건·동향·정책의 본질과 파급력이 느껴지는 완성형 문장으로 작성하되, **최대 60자 이내**로 간결하게 작성할 것.
    - 단순 사실 전달이 아닌, 통찰과 경고가 담긴 전략적 헤드라인으로 작성할 것.


    [서브 헤드라인] (<h3> 태그 사용)
    - 핵심 내용과 파급효과를 100자 이내의 한 문장으로 요약할 것.


    [핵심 내용 요약] (<ul><li> 구조 사용)
    - <ul> 태그 내부에 <li> 태그로 항목을 구성할 것.
    - **반드시 4개에서 6개 사이의 <li> 항목으로 구성하여 리포트의 풍부함을 확보할 것.**
    - **중요: 각 <li> 항목은 반드시 중간에 마침표가 없는 '단 하나의 완벽한 문장'으로 구성하되, 정보의 밀도를 위해 최소 120자 이상의 풍부한 내용을 담을 것.**
    - 여러 사실을 연결할 때는 '~하며', '~하고', '~함에 따라', '~인 반면' 등의 연결 어미를 활용하여 문장을 길고 정교하게 구성할 것.
    - **기사에 언급된 핵심 명사(기관명, 인물명, 고유 기술명 등)를 반드시 포함**하여 팩트 위주의 전문적인 내용을 담을 것.
    - 배경 설명은 최소화하되 기사가 전달하는 핵심 사실과 그 기술적/정책적 의미를 인과관계에 맞춰 서술할 것.
    - 모든 문장은 **'~다', '~하다', '~이다'와 같은 격식 있는 서술형 어미**로 끝맺음할 것.
    - 출처 번호([1], [web:1] 등) 및 인용 표시는 절대 포함하지 말 것.

    [작성 예시 - 반드시 이 스타일을 따를 것]
    <h3>NIST의 양자 내성 암호 표준 발표에 따른 국가 안보 암호 체계의 전환 가이드라인</h3>
    <ul>
      <li>미 국립표준기술연구소(NIST)는 수년간의 글로벌 공모를 거쳐 양자 컴퓨터의 연산 공격으로부터 데이터를 안전하게 보호할 수 있는 ML-KEM 등 3종의 양자 내성 암호 알고리즘을 최종 표준으로 공식 승인하며 전 세계 디지털 인프라의 전면적 개편을 선언하였습니다.</li>
      <li>이번 표준 확정은 고성능 양자 컴퓨팅 기술이 기존 RSA 및 ECC 암호 체계를 무력화할 수 있다는 실질적 위협에 대응하기 위한 조치로 전 세계 공공 및 민간 분야의 데이터 보호 체계를 선제적으로 보강하고 글로벌 IT 공급망의 보안 표준을 상향 평준화시키는 결과를 초래할 것입니다.</li>
    </ul>
    <blockquote>이번 사건은 보안이 단순한 기술적 보완재를 넘어 국가의 디지털 주권을 지키는 핵심 생존 요건이 되었음을 시사하며 한국 정부는 국내 수출 기업의 경쟁력 확보를 위해 국제 표준과의 정합성 확보에 박차를 가해야 합니다.</blockquote>


    [전문가 코멘트] (<blockquote> 태그 사용)
    - 형식: "이번 사건은 ~라는 점에서 주목할 필요가 있다. 단기적으로는 ~, 중장기적으로는 ~ 대응이 필요하다."
    - 정책 담당자를 위한 행동 권고를 포함하여 150자 내외로 작성할 것.


    [출처]
    <p>출처: <a href='URL' target='_blank'>매체명</a></p>

    결과는 반드시 아래의 순수 JSON 리스트 형식으로만 응답해 (설명 없이 JSON만).
    특히 **"content" 필드 안에는 <h3>, <ul>, <blockquote>, <p>(출처) 태그가 순서대로 모두 포함된 전체 HTML 본문**을 넣어야 함:
    [
      {{
        "title": "뉴스 제목",
        "content": "<h3>서브헤드라인</h3><ul><li>요약내용</li>...</ul><blockquote>전문가코멘트</blockquote><p>출처: <a href='URL' target='_blank'>매체명</a></p>",
        "tags": ["기사관련키워드1", "기사관련키워드2", "기사관련키워드3", "기사관련키워드4", "기사관련키워드5"],
        "image_url": "직접적인 이미지 파일 URL. 확실하지 않으면 비워둘 것.",
        "source_url": "원본 링크"
      }}
    ]

    대상 뉴스 리스트:
    {json.dumps(limited_news, ensure_ascii=False)}
    """

    data = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "보안 뉴스 분석 전문가입니다. 반드시 JSON 형식으로만 답변합니다."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=300)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            return json.loads(json_match.group()) if json_match else json.loads(content)
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
    source_url = news_data.get('source_url')
    for item in original_news_list:
        if item['link'] == source_url and item.get('rss_image'):
            target_image = item['rss_image']
            break
    if not target_image: target_image = get_image_from_webpage(source_url)
    if not target_image: target_image = news_data.get('image_url')

    # 본문 내용 가져오기
    content_body = news_data.get('content', '내용 없음')

    # 전략 6: 외부 이미지가 있다면 본문 상단에 <img> 태그 삽입 (FIFU가 이를 감지하여 특성 이미지로 설정)
    if target_image and target_image.startswith("http"):
        print(f"  -> 외부 이미지 URL 사용: {target_image[:60]}...")
        # 숨겨진 이미지 태그 삽입 (FIFU 감지용, 중복 노출 방지)
        img_tag = f'<p style="display:none;"><img src="{target_image}" alt="{news_data["title"]}"></p>'
        content_body = img_tag + content_body
        media_id = 0 # 외부 이미지를 사용하므로 워드프레스 미디어 ID는 0(또는 없음)으로 설정
    else:
        print(f"  -> 이미지를 찾지 못해 기본 미디어 ID {GUARANTEED_MEDIA_ID}를 사용합니다.")
        media_id = GUARANTEED_MEDIA_ID

    tag_ids = [get_or_create_term("tags", t) for t in news_data.get('tags', [])]
    tag_ids = [tid for tid in tag_ids if tid]
    
    payload = {
        "title": news_data['title'],
        "content": content_body,
        "status": "publish",
        "categories": [21], # 'News' 카테고리 ID 21 고정
        "tags": tag_ids
    }
    
    # 미디어 ID가 있는 경우에만 featured_media 필드 추가
    if media_id > 0:
        payload["featured_media"] = media_id
    
    try:
        res = session.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30, verify=False)
        if res.status_code in [200, 201]:
            print(f"발행 성공! (확인: {res.json().get('link')})")
        else: print(f"발행 실패: {res.status_code} - {res.text}")
    except Exception as e: print(f"포스팅 예외: {e}")

def main():
    if not all([PERPLEXITY_API_KEY, WP_USERNAME, WP_APP_PASSWORD]):
        print("필수 환경 변수 누락")
        return
    init_session()
    
    recent_titles = get_recent_post_titles()
    news_list = get_rss_news()
    
    selected_news = analyze_news_with_perplexity(news_list, recent_titles)
    
    if not selected_news:
        print("선정된 뉴스가 없습니다.")
        return
        
    for news in selected_news:
        try:
            post_to_wordpress(news, news_list)
            time.sleep(5)
        except Exception as e: print(f"처리 중 오류: {e}")

if __name__ == "__main__":
    main()
