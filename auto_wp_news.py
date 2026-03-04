import feedparser
import requests
import json
import re
from requests.auth import HTTPBasicAuth
import time
import os
from urllib.parse import quote, urljoin

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

# 공통 헤더
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
session = requests.Session()
session.headers.update(COMMON_HEADERS)

def get_image_from_webpage(url):
    """기사 원본 주소에서 og:image 태그를 추출합니다."""
    if not url or not url.startswith("http"):
        return None
    print(f"원본 페이지에서 이미지 추출 중: {url[:60]}...")
    try:
        res = requests.get(url, timeout=10, headers=COMMON_HEADERS)
        if res.status_code == 200:
            html = res.text
            match = re.search(r'<meta [^>]*property=["\']og:image["\'] [^>]*content=["\']([^"\']+)["\']', html)
            if not match:
                match = re.search(r'<meta [^>]*content=["\']([^"\']+)["\'] [^>]*property=["\']og:image["\']', html)
            if match:
                img_url = match.group(1)
                if img_url.startswith('/'):
                    img_url = urljoin(url, img_url)
                print(f"  -> 추출 성공: {img_url[:60]}...")
                return img_url
    except Exception as e:
        print(f"  -> 추출 실패: {e}")
    return None

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
        if 'media_content' in entry and entry.media_content:
            return entry.media_content[0]['url']
        if 'media_thumbnail' in entry and entry.media_thumbnail:
            return entry.media_thumbnail[0]['url']
        content = getattr(entry, 'summary', '') + getattr(entry, 'description', '')
        img_match = re.search(r'<img [^>]*src="([^"]+)"', content)
        if img_match:
            return img_match.group(1)
        return None

    # 1. 보안 전문 매체 직접 RSS 파싱
    for source_name, rss_url in direct_feeds.items():
        print(f"[{source_name}] 직접 RSS 수집 중...")
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
        except Exception as e:
            print(f"  -> [{source_name}] 읽기 실패: {e}")

    # 2. 구글 뉴스 키워드 검색
    for category_name, keywords in search_categories.items():
        query = " OR ".join([f'"{k}"' if " " in k else k for k in keywords])
        encoded_query = quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
        print(f"[{category_name}] 구글 뉴스 검색 중...")
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
        except Exception as e:
            print(f"  -> [{category_name}] 읽기 실패: {e}")
            
    print(f"총 {len(all_entries)}개의 고유 기사 수집 완료.")
    return all_entries

def analyze_news_with_perplexity(news_list):
    """Perplexity AI를 사용하여 최상급 품질의 뉴스 분석을 수행합니다 (NIST 예시 포함)."""
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

    다음은 주어진 뉴스 리스트 중에서 **글로벌(해외) 보안 뉴스 상위 10개**를 선정해
    한국 정부 정책 담당자가 빠르게 동향을 파악할 수 있도록 뉴스의 핵심사항을 요약해야 하는 작업이다.

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
        "category": "News",
        "tags": ["태그1", "태그2", "태그3"],
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

    for attempt in range(2):
        try:
            response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=300)
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
                return json.loads(json_match.group()) if json_match else json.loads(content)
        except Exception as e:
            print(f"AI 분석 중 예외 발생: {e}")
    return []

def init_session():
    try:
        res = session.get(WP_SITE_URL, timeout=10)
        print(f"세션 초기화 완료 (Status: {res.status_code})")
    except: pass

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
    if not image_url or not image_url.startswith("http"): return None
    print(f"이미지 업로드 시도: {image_url[:60]}...")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    try:
        img_res = session.get(image_url, timeout=20)
        if img_res.status_code != 200: return None
        content_type = img_res.headers.get('Content-Type', 'image/jpeg')
        filename = f"news_img_{int(time.time())}.{'png' if 'png' in content_type else 'jpg'}"
        headers = {"Content-Disposition": f"attachment; filename={filename}", "Content-Type": content_type}
        up_res = session.post(f"{WP_SITE_URL}/wp-json/wp/v2/media", auth=auth, headers=headers, data=img_res.content, timeout=30)
        if up_res.status_code in [200, 201]: return up_res.json().get('id')
    except: pass
    return None

def post_to_wordpress(news_data, original_news_list):
    """뉴스를 워드프레스에 포스팅합니다."""
    print(f"--- 포스팅 시도: {news_data['title']} ---")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    # 1. 실제 이미지 주소 결정 (RSS -> 웹 스크래핑 -> AI -> 디폴트 순)
    target_image = None
    source_url = news_data.get('source_url')
    for item in original_news_list:
        if item['link'] == source_url and item.get('rss_image'):
            target_image = item['rss_image']
            print("  -> RSS 피드에서 실제 이미지를 찾았습니다.")
            break
    
    if not target_image:
        target_image = get_image_from_webpage(source_url)
    
    if not target_image:
        target_image = news_data.get('image_url')

    # 2. 이미지 업로드 (실패 시 디폴트 이미지 사용)
    media_id = upload_media_from_url(target_image)
    if not media_id:
        print("  -> 이미지 업로드 실패. 기본 이미지를 사용합니다.")
        media_id = upload_media_from_url(DEFAULT_IMAGE_URL)

    cat_id = get_or_create_term("categories", news_data.get('category', 'News'))
    tag_ids = [get_or_create_term("tags", t) for t in news_data.get('tags', [])]
    tag_ids = [tid for tid in tag_ids if tid]
    
    # 3. 포스팅 페이로드 (Ele뉴스 최적화: 본문 이미지 삽입 제거)
    payload = {
        "title": news_data['title'],
        "content": news_data.get('content', '내용 없음'),
        "status": "publish",
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "featured_media": media_id if media_id else 0,
        "meta": {
            "fifu_image_url": target_image or DEFAULT_IMAGE_URL,
            "_featured_image_url": target_image or DEFAULT_IMAGE_URL
        }
    }
    
    try:
        res = session.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30)
        if res.status_code in [200, 201]:
            print(f"발행 성공! (ID: {res.json().get('id')})")
        else: print(f"발행 실패: {res.status_code}")
    except Exception as e: print(f"포스팅 예외: {e}")

def main():
    if not all([PERPLEXITY_API_KEY, WP_USERNAME, WP_APP_PASSWORD]): return
    init_session()
    news_list = get_rss_news()
    selected_news = analyze_news_with_perplexity(news_list)
    if not selected_news: return
    for news in selected_news:
        try:
            post_to_wordpress(news, news_list)
            time.sleep(5)
        except Exception as e: print(f"처리 중 오류: {e}")

if __name__ == "__main__":
    main()
