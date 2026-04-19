import feedparser
import requests
import json
import re
from requests.auth import HTTPBasicAuth
import time
import calendar
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
    """워드프레스에서 최근 포스팅된 30개의 제목을 가져옵니다."""
    print("최근 포스팅된 뉴스 제목 확인 중...")
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    params = {"per_page": 30, "status": "publish"}
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

    for source_name, rss_url in direct_feeds.items():
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:20]:
                is_recent = False
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    if now - calendar.timegm(entry.published_parsed) < day_in_seconds:
                        is_recent = True
                
                # 직접 피드에서도 한국어 포함 기사 엄격 제외
                if is_recent and re.search('[가-힣]', entry.title):
                    is_recent = False
                
                # FeedBurner 원본 링크가 있으면 그것을 사용 (매칭 정확도 향상)
                actual_link = getattr(entry, 'feedburner_origlink', entry.link)
                
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

    # 구글 뉴스 검색: 글로벌 설정 강화 및 한국 관련 키워드 배제
    for category_name, keywords in search_categories.items():
        # -site:co.kr 등을 추가하여 한국 도메인 기사 배제 시도
        query = " OR ".join([f'"{k}"' if " " in k else k for k in keywords])
        full_query = f"({query}) -site:co.kr -site:kr when:1d"
        rss_url = f"https://news.google.com/rss/search?q={quote(full_query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:15]:
                # 24시간 이내 기사인지 확인
                is_recent = True
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    entry_time = calendar.timegm(entry.published_parsed)
                    if now - entry_time > day_in_seconds:
                        is_recent = False
                
                # 한국어 포함 여부 체크 (국내 뉴스 제외 원칙)
                if is_recent and re.search('[가-힣]', entry.title):
                    is_recent = False

                if is_recent and entry.link not in seen_links:
                    all_entries.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": getattr(entry, 'published', time.ctime()),
                        "search_category": category_name,
                        "rss_image": extract_image(entry)
                    })
                    seen_links.add(entry.link)
        except: pass
            
    # --- 가치 평가 기반 뉴스 선정 로직 (Scoring System) ---
    def calculate_score(entry):
        score = 0
        title = entry['title'].lower()
        
        # 1. 산업 영향도 및 키워드 가중치
        impact_keywords = {
            'critical': 10, 'zero-day': 15, 'vulnerability': 5, 'exploit': 5, 
            'breach': 8, 'cyberattack': 7, 'ransomware': 7, 'supply chain': 10,
            'openai': 12, 'anthropic': 12, 'microsoft': 8, 'google': 8, 'nvidia': 8,
            'regulation': 10, 'policy': 10, 'standard': 8, 'nist': 10, 'cisa': 10
        }
        for kw, points in impact_keywords.items():
            if kw in title:
                score += points
        
        # 2. 시의성 가중치 (최신일수록 높은 점수)
        try:
            pub_time = calendar.timegm(time.strptime(entry['published'], time.ctime())) if isinstance(entry['published'], str) else entry['published']
            hours_ago = (now - pub_time) / 3600
            if hours_ago < 6: score += 10
            elif hours_ago < 12: score += 5
        except: pass

        if "Expert_" in entry['search_category']:
            score += 5
            
        return score

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

def analyze_news_with_perplexity(news_list, recent_titles):
    """Perplexity AI를 사용하여 최상급 품질의 뉴스 분석을 수행합니다."""
    if not news_list: return []
    limited_news = news_list[:40]
    print(f"Perplexity AI 분석 중 ({len(limited_news)}개 기사 분석)...")
    
    headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}

    prompt = f"""
    당신은 글로벌 보안 인텔리전스 기업의 '수석 분석가'이자, 복잡한 기술 이슈를 정책적 가치로 전환하는 '보안 에듀케이터'입니다.
    다음 뉴스 리스트에서 **글로벌 보안 뉴스 상위 10개**를 선정하여, 한국 정부 보안 정책 담당자가 즉각적인 의사결정 참고자료로 활용할 수 있도록 요약 및 분석하십시오.

    **[핵심 분석 타겟: 선정 시 가중치 부여]**
    1. **빅테크 및 보안 리딩 기업(Top-Tier):** Palo Alto Networks(플랫폼화), CrowdStrike(EDR/XDR 주도권), Microsoft(SFI 보안 이니셔티브), Zscaler, Google Cloud(Mandiant), Anthropic/OpenAI(AI 보안 및 안전)의 전략적 행보.
    2. **AI 및 차세대 위협:** AI 모델 취약점(Jailbreak, 탈옥), AI 안전성 프레임워크(Anthropic의 미토스 등), 생성형 AI 기반 사이버 공격 및 방어 전략.
    3. **글로벌 공급망 및 인프라 정책:** 미국의 사이버 보안 행정명령(EO), EU 사이버 복원력 법안(CRA), SEC의 공시 규제 등 국제적 규범 변화.

    **※ 중복 및 필터링 주의사항:**
    - 다음 리스트에 포함된 제목과 유사한 뉴스는 절대 제외할 것: {json.dumps(recent_titles, ensure_ascii=False)}
    - 국내 뉴스는 제외하고, '글로벌 동향'과 '한국 정책에 미칠 영향'에만 집중할 것.

    **[선정 기준 및 가중치]**
    1. 기업 전략 및 시장 지배력 [40%]: M&A, 플랫폼 통합 전략, 기술 로드맵 변화.
    2. AI 보안 및 미래 기술 [25%]: AI 안전성 가이드라인, 양자 내성 암호, 클라우드 네이티브 보안.
    3. 글로벌 규제 및 정책 [20%]: 주요국의 법제화 및 국제 표준화 동향.
    4. 파급력 및 시급성 [15%]: 대규모 취약점 및 공급망 공격에 대한 즉각적 경고.

    **[독자 페르소나: 한국 정부 정책 담당자]**
    - 기술적 디테일보다는 "이 변화가 한국 보안 산업 육성과 국가 안보에 어떤 기회와 위기인가?"를 파악하고자 함.
    - 비전문가도 이해할 수 있도록 IT 전문 용어는 정책적 의미로 치환하여 서술할 것.

    **[작성 가이드라인 - 엄격 준수]**
    - **[제목]**: **뉴스 헤드라인다운 리듬감과 임팩트를 갖춘 전략적 제목 (60자 이내).**
      - **명사 나열 금지:** "A의 B에 따른 C의 D..." 처럼 딱딱한 명사구 나열을 피할 것.
      - **핵심 정보 전면 배치:** 사건의 주체와 핵심 액션을 제목 앞부분에 둘 것.
      - **가독성 기호 활용:** 쉼표(,), 콜론(:), 말줄임표(…)를 적절히 활용하여 문장을 끊어 읽을 수 있게 할 것.
      - **동사적 종결:** '~함', '~강화', '~경고', '~확정' 등 역동적인 느낌으로 마무리할 것.
    - **[서브 헤드라인]**: 파급효과 중심의 한 문장 요약 (`<h3>` 사용).
    - **[핵심 내용 요약]**: `<ul><li>` 구조 사용.
      - **반드시 4개에서 6개 사이의 `<li>` 항목으로 구성하여 리포트의 풍부함을 확보할 것.**
      - **중요: 각 `<li>` 항목은 반드시 중간에 마침표가 없는 '단 하나의 완벽한 문장'으로 구성하되, 정보의 밀도를 위해 최소 120자 이상의 풍부한 내용을 담을 것.**
      - 여러 사실을 연결할 때는 '~하며', '~하고', '~함에 따라', '~인 반면' 등의 연결 어미를 활용하여 문장을 길고 정교하게 구성할 것.
      - **기사에 언급된 핵심 명사(기관명, 인물명, 고유 기술명 등)를 반드시 포함**하여 팩트 위주의 전문적인 내용을 담을 것.
      - 모든 문장은 **'~다', '~하다', '~이다'와 같은 격식 있는 서술형 어미**로 끝맺음할 것.
      - 출처 번호([1], [web:1] 등) 및 인용 표시는 절대 포함하지 말 것.
    - **[전문가 코멘트]**: `<blockquote>` 사용. 정책 담당자를 위한 행동 권고를 포함하여 150자 내외로 작성할 것.
    - **[주요 용어 설명]**: 전문가 코멘트 아래, 출처 바로 위에 별도의 `<p>` 태그로 구성. (형식: `<strong>주요 용어:</strong> 용어(의미), 용어(의미)`)

    **[작성 예시]**
    <h3>NIST, 양자 내성 암호 표준 공식 승인… '국가 안보 암호 체계' 전면 전환 예고</h3>
    <ul>
      <li>미 국립표준기술연구소(NIST)는 수년간의 글로벌 공모를 거쳐 양자 컴퓨터의 연산 공격으로부터 데이터를 안전하게 보호할 수 있는 ML-KEM 등 3종의 양자 내성 암호 알고리즘을 최종 표준으로 공식 승인하며 전 세계 디지털 인프라의 전면적 개편을 선언하였습니다.</li>
      <li>이번 표준 확정은 고성능 양자 컴퓨팅 기술이 기존 RSA 및 ECC 암호 체계를 무력화할 수 있다는 실질적 위협에 대응하기 위한 조치로 전 세계 공공 및 민간 분야의 데이터 보호 체계를 선제적으로 보강하고 글로벌 IT 공급망의 보안 표준을 상향 평준화시키는 결과를 초래할 것입니다.</li>
      <li>(이하 생략 - 실제 작성 시에는 반드시 4~6개의 불렛포인트를 작성할 것)</li>
    </ul>
    <blockquote>이번 사건은 보안이 단순한 기술적 보완재를 넘어 국가의 디지털 주권을 지키는 핵심 생존 요건이 되었음을 시사하며, 한국 정부는 국내 수출 기업의 경쟁력 확보를 위해 국제 표준과의 정합성 확보에 박차를 가해야 합니다.</blockquote>
    <p><strong>주요 용어:</strong> 양자 내성 암호(양자 컴퓨터의 강력한 연산 공격에도 견딜 수 있도록 설계된 차세대 암호 체계), NIST(미국 표준 기술 연구소로 글로벌 IT 표준을 주도하는 기관)</p>
    <p>출처: <a href='URL' target='_blank'>매체명</a></p>

    **[결과물 형식]**
    아래 JSON 리스트 형식으로만 출력하십시오 (설명 생략).
    [
      {{
        "title": "전략적 제목",
        "content": "<h3>서브 헤드라인</h3><ul><li>풍부한 문장 1</li><li>풍부한 문장 2</li>...</ul><blockquote>전문가 코멘트</blockquote><p><strong>주요 용어:</strong> 용어(의미), 용어(의미)</p><p>출처: <a href='URL' target='_blank'>매체명</a></p>",
        "tags": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
        "image_url": "URL",
        "source_url": "URL"
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
                # 제어 문자 제거 및 비표준 이스케이프 수정 시도
                cleaned_json = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
                # 간혹 발생하는 이스케이프되지 않은 큰따옴표 문제 등은 완벽히 해결하기 어려우나 기본 시도
                try:
                    return json.loads(cleaned_json)
                except Exception as e2:
                    print(f"최종 파싱 실패. 응답 길이: {len(content)}")
                    with open("debug_perplexity_error.txt", "w", encoding="utf-8") as df:
                        df.write(content)
                    print(f"디버그 정보가 debug_perplexity_error.txt에 저장되었습니다.")
                    raise e2
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
