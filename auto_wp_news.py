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
    너는 글로벌 보안 인텔리전스 기업의 '수석 분석가'이자 전문 뉴스 편집자야. 
    아래 제공된 뉴스 리스트의 URL에 실시간으로 접속하여 기사 전문을 읽고, 다음 5가지 기준에 따라 총점이 가장 높은 상위 10개 뉴스를 선정해 전문적인 보안 보고서를 작성해줘.
    [평가 기준: 파급력(30), 심각성(25), 시의성(20), 신뢰성(15), 시사점(10)]

    각 뉴스 분석은 워드프레스 포스팅용 HTML 구조를 포함하며, 카테고리는 "News"로 고정하고 다음 형식을 엄격히 준수해야 함:

    1. 분석 가이드라인 (한국어 작성):
       - [제목]: 원문의 핵심(대상, 공격유형, 여파)을 관통하며 통찰이 느껴지는 명사형 문장.
       - [서브 헤드라인]: <h3> 태그 사용. 기사의 시급한 위협과 대상을 100자 이내 요약.
       - [심층 분석 및 세부 요약]: 
         * <h2> 태그로 주제 분류(예: 기술적 메커니즘, 파급 효과).
         * 각 <h2> 아래 <ul>, <li> 태그 사용.
         * 전체 문장 10~15개, 각 문장은 '개조식(~함, ~임)'으로 종결.
         * 각 문장은 기술적 인과관계와 수치/데이터를 포함하여 정보 밀도를 극대화할 것.
       - [전문가 코멘트]: <blockquote> 태그 사용. 원문에 직접 인용구(Direct Quote)와 인물/직함이 있는 경우만 포함(없으면 태그 자체를 삭제).
       - [시사점 및 전략적 제언]: <h2> 태그 사용. 단기/중장기 대응 전략을 포함하여 200자 이내로 정리.
       - [출처]: <p>출처: <a href='URL'>매체명</a></p> 형식.

    결과는 반드시 아래의 순수 JSON 리스트 형식으로만 응답해 (설명 없이 JSON만):
    [
      {{
        "title": "분석된 뉴스 제목",
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

def get_or_create_term(taxonomy, name):
    """카테고리나 태그의 ID를 가져오거나 없으면 생성합니다."""
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/{taxonomy}"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    try:
        res = requests.get(endpoint, auth=auth, params={"search": name}, headers=COMMON_HEADERS, timeout=20)
        if res.status_code == 200 and res.text.strip():
            terms = res.json()
            for term in terms:
                if term['name'] == name:
                    return term['id']
        
        res = requests.post(endpoint, auth=auth, json={"name": name}, headers=COMMON_HEADERS, timeout=20)
        if res.status_code in [200, 201] and res.text.strip():
            return res.json()['id']
        else:
            print(f"Term 생성 응답 이상 ({taxonomy}: {name}): Status {res.status_code}, Body: {res.text[:100]}")
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
        img_res = requests.get(image_url, timeout=20, headers=COMMON_HEADERS)
        if img_res.status_code == 200:
            filename = f"news_img_{int(time.time())}.jpg"
            headers = {
                **COMMON_HEADERS,
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "image/jpeg"
            }
            up_res = requests.post(
                f"{WP_SITE_URL}/wp-json/wp/v2/media",
                auth=auth,
                headers=headers,
                data=img_res.content,
                timeout=30
            )
            if up_res.status_code in [200, 201] and up_res.text.strip():
                return up_res.json()['id']
            else:
                print(f"미디어 업로드 실패 응답: Status {up_res.status_code}, Body: {up_res.text[:100]}")
    except Exception as e:
        print(f"이미지 업로드 중 예외: {e}")
    return None

def post_to_wordpress(news_data):
    """뉴스를 워드프레스에 포스팅합니다."""
    print(f"--- 포스팅 시도: {news_data['title']} ---")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    # 카테고리/태그가 없어도 글은 올라가야 함
    cat_id = get_or_create_term("categories", news_data.get('category', 'News'))
    tag_ids = []
    for t in news_data.get('tags', []):
        tid = get_or_create_term("tags", t)
        if tid: tag_ids.append(tid)
    
    media_id = upload_media_from_url(news_data.get('image_url'))
    
    payload = {
        "title": news_data['title'],
        "content": f"{news_data['content']}<br><br><a href='{news_data['source_url']}' target='_blank'>원문 기사 읽기</a>",
        "status": "publish",
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "featured_media": media_id if media_id else 0
    }
    
    try:
        res = requests.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload, headers=COMMON_HEADERS, timeout=30)
        
        if res.status_code in [200, 201]:
            if res.text.strip():
                try:
                    post_info = res.json()
                    print(f"발행 성공! (ID: {post_info.get('id')})")
                    print(f"글 주소: {post_info.get('link')}")
                except:
                    print(f"발행 성공(200)했으나 JSON 해석 실패. 서버 응답: {res.text[:200]}")
            else:
                print(f"발행 성공(200)했으나 응답 바디가 비어있음. (차단 의심)")
        else:
            print(f"발행 실패 (Status: {res.status_code}): {res.text[:500]}")
            
    except Exception as e:
        print(f"포스팅 요청 중 예외 발생: {e}")

def main():
    if not all([PERPLEXITY_API_KEY, WP_USERNAME, WP_APP_PASSWORD]):
        print("에러: 환경 변수(API Key, WP 로그인 정보)가 설정되지 않았습니다.")
        return

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
