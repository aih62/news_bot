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
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

# WP_SITE_URL이 비어있거나 None인 경우를 대비한 처리
WP_SITE_URL = os.getenv("WP_SITE_URL")
if not WP_SITE_URL:
    WP_SITE_URL = "https://ajken.mycafe24.com"
WP_SITE_URL = WP_SITE_URL.rstrip("/")

def get_rss_news():
    """feeds.json에서 키워드를 읽어와 구글 뉴스 RSS에서 최신 기사 목록을 가져옵니다."""
    print(f"현재 작업 디렉토리: {os.getcwd()}")
    print("feeds.json 로드 중...")
    try:
        with open("feeds.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            categories = config.get("keywords", {})
    except Exception as e:
        print(f"feeds.json 로드 실패: {e}")
        return []

    all_entries = []
    seen_links = set()

    for category_name, keywords in categories.items():
        # 키워드들을 OR로 묶어서 검색 쿼리 생성 및 인코딩
        query = " OR ".join([f'"{k}"' if " " in k else k for k in keywords])
        encoded_query = quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
        
        print(f"[{category_name}] RSS 검색 중: {rss_url[:100]}...")
        try:
            feed = feedparser.parse(rss_url)
            count = 0
            for entry in feed.entries[:20]:
                if entry.link not in seen_links:
                    all_entries.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.published,
                        "search_category": category_name
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
        
    # 토큰 제한 및 분석 효율을 위해 최신순 상위 40개로 제한
    limited_news = news_list[:40]
    print(f"Perplexity AI 분석 중 ({len(news_list)}개 중 상위 {len(limited_news)}개 기사 분석)...")
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    너는 글로벌 보안 인텔리전스 기업의 '수석 분석가'이자 친절한 보안 에듀케이터야.
    아래 제공된 뉴스 리스트 중 다음 기준에 따라 **글로벌(해외) 보안 뉴스 상위 10개**를 선정해,
    한국 정부 정책 담당자가 빠르게 동향을 파악할 수 있는 인텔리전스 리포트를 작성해줘.
    **※ 주의: 한국 국내 뉴스나 정책은 선정에서 제외하고, 철저히 글로벌 동향 및 국제 규제 위주로 선정할 것.**

    [선정 기준]
    1. 심각성: 글로벌 보안 사고나 취약점의 기술적 위험 수준
    2. 시급성: 즉각적인 대응이나 패치가 필요한 긴급성
    3. 영향력: 대규모 인프라, 기업, 국가 단위의 글로벌 파급력
    4. 정책성: 해외 주요국(미국, EU 등)의 법규, 규제, 정부 정책 등 제도적 변화 여부
    5. 미래가치: 향후 글로벌 보안 패러다임 변화에 대한 시사점

    [독자 페르소나]
    - 독자는 기술 전문가가 아닌 한국 정부의 사이버보안 정책 담당자야.
    - 독자는 "이 사건이 왜 중요하고, 우리 정책에 어떤 시사점이 있는가"를 알고 싶어해.
    - 따라서 기술 용어는 반드시 쉬운 말로 풀어쓰고, 정책·외교·경제적 맥락을 강조해줘.

    [각 뉴스 작성 형식]

    [제목]
    - 이 사건·동향·정책의 본질과 파급력이 느껴지는 완성형 문장. (~다 / ~하다 체)
    - 단순 사실 전달이 아닌, 통찰과 경고가 담긴 헤드라인으로 작성.

    [서브 헤드라인] (<h3> 태그 사용)
    - 핵심 내용과 파급효과를 100자 이내의 한 문장으로 요약.

    [심층 분석 리포트] (<ul><li> 구조 사용)
    - <ul> 태그 내부에 <li> 태그로 항목을 구성할 것.
    - 전체 분량: 반드시 **4개의 <li> 항목**으로 구성하며, 각 항목은 2~3개의 긴 호흡을 가진 문장으로 이루어진 **하나의 완성된 문단(Paragraph)** 형태여야 함.
    - **중요: 각 항목 시작 부분에 [배경], [핵심 내용] 등의 머리말(Label)을 절대 사용하지 말 것.**
    - 각 <li> 항목은 **최소 150자에서 250자 사이**로 작성하여 정보의 밀도를 높이고 분석적 깊이를 확보할 것.
    - 아래 4단계 스토리 구조를 각 <li>에 하나씩 정밀하게 배분하여 서술할 것:
      1) (배경 및 지정학적 맥락) 단순히 사건 발생을 나열하지 말고, 왜 지금 이 시점에 미국/EU 등 주요국이 이 문제에 집중하는지, 글로벌 기술 패권이나 산업 구조 변화와 연계하여 심도 있게 분석할 것.
      2) (핵심 내용 및 메커니즘) 정책의 세부 조항이나 공격 기법의 핵심 원리를 비전문가인 정책 결정자가 직관적으로 이해할 수 있도록 비유와 상세 설명을 곁들여 풍부하게 서술할 것.
      3) (글로벌 파급력 및 산업 영향) 해당 사안이 단순히 보안 영역을 넘어 글로벌 공급망, 외교 관계, 혹은 국가 간 기술 표준 주도권에 어떤 실질적인 영향을 미치는지 거시적인 관점에서 서술할 것.
      4) (전망 및 한국 정책 시사점) 향후 1~2년 내 전개될 구체적인 시나리오를 제시하고, 한국 정부의 보안 정책(예: 제로 트러스트 도입, 공급망 보안 입법 등)에 즉각적으로 반영해야 할 구체적이고 전략적인 제언을 포함할 것.
    - 모든 문장은 **'~다', '~하다'와 같은 격식 있는 서술형 어미**로 끝맺음할 것.
    - '이러한 맥락에서', '결과적으로', '나아가', '따라서' 등 고급 접속어를 활용하여 논리적 완결성을 확보할 것.
    - 출처 번호([1], [web:1] 등) 및 인용 표시는 절대 포함하지 말 것.

    [전문가 코멘트] (<blockquote> 태그 사용)
    - 형식: "이번 사건은 ~라는 점에서 주목할 필요가 있다. 단기적으로는 ~, 중장기적으로는 ~ 대응이 필요하다."
    - 정책 담당자를 위한 행동 권고를 포함하여 150자 내외로 작성할 것.

    [출처]
    <p>출처: <a href='URL'>매체명</a></p>

    결과는 반드시 아래의 순수 JSON 리스트 형식으로만 응답해 (설명 없이 JSON만):
    [
      {{
        "title": "뉴스 제목",
        "content": "HTML 구조가 포함된 본문 전체 내용",
        "category": "News",
        "tags": ["태그1", "태그2", "태그3"],
        "image_url": "대표 이미지 주소 혹은 null",
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

    # 재시도 로직 추가 (최대 2회)
    for attempt in range(2):
        try:
            print(f"AI 분석 시도 {attempt + 1}/2...")
            response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=300)
            
            if response.status_code != 200:
                print(f"API 에러 발생 (Status: {response.status_code}): {response.text}")
                continue

            resp_json = response.json()
            if 'choices' not in resp_json:
                print(f"응답 구조 이상: {resp_json}")
                continue

            content = resp_json['choices'][0]['message']['content']
            json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(content)
            
        except requests.exceptions.Timeout:
            print(f"AI 분석 시간 초과 (300초). 재시도 중...")
        except Exception as e:
            print(f"AI 분석 중 예외 발생: {e}")
            break
            
    return []

# 공통 헤더 (봇 차단 방지용)
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 전역 세션 객체 생성
session = requests.Session()
session.headers.update(COMMON_HEADERS)

def init_session():
    """Cafe24 스팸 쉴드 우회를 위해 메인 페이지에 접속하여 쿠키를 획득합니다."""
    try:
        print("세션 초기화: 메인 페이지 접속 중...")
        res = session.get(WP_SITE_URL, timeout=10)
        print(f"메인 페이지 접속 결과: {res.status_code}")
        # 쿠키 확인 (디버깅용)
        # print(f"Cookies: {session.cookies.get_dict()}")
    except Exception as e:
        print(f"세션 초기화 실패: {e}")

def get_or_create_term(taxonomy, name):
    """카테고리나 태그의 ID를 가져오거나 없으면 생성합니다."""
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/{taxonomy}"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    try:
        res = session.get(endpoint, auth=auth, params={"search": name}, timeout=20)
        if res.status_code == 200:
            try:
                terms = res.json()
                for term in terms:
                    if term['name'] == name:
                        return term['id']
            except:
                pass # JSON 파싱 실패 시 무시
        
        res = session.post(endpoint, auth=auth, json={"name": name}, timeout=20)
        if res.status_code in [200, 201]:
            try:
                return res.json()['id']
            except:
                pass
    except Exception as e:
        print(f"Term 생성 중 예외 ({taxonomy}: {name}): {e}")
    return None

def upload_media_from_url(image_url):
    """이미지 URL을 워드프레스 미디어 라이브러리에 업로드하고 ID를 반환합니다."""
    if not image_url or not image_url.startswith("http"):
        return None
        
    print(f"이미지 업로드 시도: {image_url[:50]}...")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    try:
        img_res = session.get(image_url, timeout=20)
        if img_res.status_code == 200:
            filename = f"news_img_{int(time.time())}.jpg"
            headers = {
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "image/jpeg"
            }
            # 이미지 업로드 시에는 Content-Type이 덮어씌워지지 않도록 주의
            # requests는 files 파라미터 사용 시 자동으로 헤더 설정하지만, 여기서는 raw data 전송
            # session 헤더와 충돌 방지를 위해 별도 헤더 병합
            upload_headers = session.headers.copy()
            upload_headers.update(headers)
            
            up_res = session.post(
                f"{WP_SITE_URL}/wp-json/wp/v2/media",
                auth=auth,
                headers=upload_headers,
                data=img_res.content,
                timeout=30
            )
            if up_res.status_code in [200, 201]:
                return up_res.json()['id']
    except Exception as e:
        print(f"이미지 업로드 중 예외: {e}")
    return None

def post_to_wordpress(news_data):
    """뉴스를 워드프레스에 포스팅합니다."""
    print(f"--- 포스팅 시도: {news_data['title']} ---")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    cat_id = get_or_create_term("categories", news_data.get('category', 'News'))
    tag_ids = []
    for t in news_data.get('tags', []):
        tid = get_or_create_term("tags", t)
        if tid: tag_ids.append(tid)
    
    # 미디어 업로드 대신 플러그인 연동용 메타데이터 사용
    image_url = news_data.get('image_url')
    
    payload = {
        "title": news_data['title'],
        "content": news_data['content'],
        "status": "publish",
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "meta": {
            "_featured_image_url": image_url if image_url else ""
        }
    }
    
    try:
        res = session.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30)
        
        if res.status_code in [200, 201]:
            if res.text.strip():
                try:
                    post_info = res.json()
                    print(f"발행 성공! (ID: {post_info.get('id')})")
                    print(f"글 주소: {post_info.get('link')}")
                except:
                    print(f"발행 성공(200)했으나 JSON 해석 실패.")
            else:
                print(f"발행 성공(200)했으나 응답 바디가 비어있음.")
        else:
            print(f"발행 실패 (Status: {res.status_code}): {res.text[:500]}")
            
    except Exception as e:
        print(f"포스팅 요청 중 예외 발생: {e}")

def main():
    if not all([PERPLEXITY_API_KEY, WP_USERNAME, WP_APP_PASSWORD]):
        print("에러: 환경 변수(API Key, WP 로그인 정보)가 설정되지 않았습니다.")
        return

    # 세션 초기화 (쿠키 획득)
    init_session()

    news_list = get_rss_news()
    selected_news = analyze_news_with_perplexity(news_list)
    
    if not selected_news:
        print("선정된 뉴스가 없습니다.")
        return

    for news in selected_news:
        try:
            post_to_wordpress(news)
            print("다음 포스팅을 위해 5초 대기...")
            time.sleep(5)
        except Exception as e:
            print(f"처리 중 오류: {e}")

if __name__ == "__main__":
    main()
