import feedparser
import requests
import json
import re
from requests.auth import HTTPBasicAuth
import time
import os
import urllib.parse
from datetime import datetime, timedelta, timezone

# ================= CONFIGURATION (환경 변수 설정) =================
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com")

def load_feeds_config():
    """feeds.json 파일에서 RSS 피드와 키워드 설정을 불러옵니다."""
    try:
        with open('feeds.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"설정 파일(feeds.json) 로드 실패: {e}")
        return {"direct_feeds": [], "keywords": ["사이버보안"]}

def get_rss_news(config):
    """여러 소스의 RSS 피드를 통합하여 최근 24시간 이내의 기사를 가져옵니다."""
    all_entries = []
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(days=1.5)

    # 1. 직접 매체 RSS 수집
    for url in config.get('direct_feeds', []):
        print(f"매체 직접 수집 중: {url[:50]}...")
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                pub_time = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                
                if not pub_time or pub_time > one_day_ago:
                    all_entries.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.get('published', 'N/A')
                    })
        except Exception as e:
            print(f"피드 읽기 실패 ({url}): {e}")

    # 2. 구글 뉴스 RSS 수집 (백업용)
    keyword_query = urllib.parse.quote(" OR ".join(config.get('keywords', [])))
    google_rss_url = f"https://news.google.com/rss/search?q={keyword_query}+tbs=qdr:d&hl=en-US&gl=US&ceid=US:en"
    
    print("구글 뉴스 백업 수집 중...")
    try:
        google_feed = feedparser.parse(google_rss_url)
        existing_links = {e['link'] for e in all_entries}
        for entry in google_feed.entries:
            if entry.link not in existing_links:
                all_entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.get('published', 'N/A')
                })
    except Exception as e:
        print(f"구글 RSS 읽기 실패: {e}")

    # 중복 제거 및 상위 150개 제한
    unique_entries = list({v['link']: v for v in all_entries}.values())
    print(f"최종 통합 수집 완료: 총 {len(unique_entries)}개 기사 확보")
    return unique_entries[:150]

def analyze_news_with_perplexity(news_list):
    """Perplexity AI를 사용하여 상위 10개 뉴스를 딥다이브 분석합니다."""
    if not news_list:
        return []
        
    print(f"Perplexity AI 딥다이브 분석 중 (대상: {len(news_list)}개)...")
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    너는 글로벌 보안 인텔리전스 기업의 '수석 분석가'이자 전문 뉴스 편집자야. 
    아래 제공된 뉴스 리스트의 URL에 직접 접속하여 기사 전문을 읽고, 다음 5가지 기준에 따라 
    총점이 가장 높은 상위 10개 뉴스를 선정해 전문적인 보안 보고서를 작성해서 워드프레스에 즉시 포스팅 가능한 고품질의 분석 리포트를 작성해줘.
    [평가 기준: 파급력(30), 심각성(25), 시의성(20), 신뢰성(15), 시사점(10)]

    각 뉴스 분석은 다음 구조를 반드시 지켜서 매우 풍부하게 작성해 (한국어로 작성):

    1. 제목: 원문의 의미를 관통하며 전문가의 통찰이 느껴지는 한국어 제목
    
    2. 본문 (HTML 태그를 사용하여 매우 상세하게 작성):
       - [서브 헤드라인]: <h3> 태그를 사용하여 기사의 핵심 요약과 파급력을 한 줄로 명확하게 작성해줘.
       - [심층 분석 (<h2> 중간 제목)]: 내용을 2~3개 주제(예: 공격 메커니즘, 인프라 파급력 등)로 분류하여 구조화.
       - [세부 요약 (<ul>, <li>)]: 각 <h2> 아래 배치하며, 개조식(~함, ~임) 문체 사용.
            * 전체 문장 수 10~15개 유지.
            * 정보 밀도 극대화: 각 문장은 기술적 인과관계(A로 인해 B가 발생함)와 핵심 수치/데이터를 최소 2개 이상 포함할 것.
        [전문가 코멘트 (<blockquote>)]: 조건부 작성: 
            * 원문에 직접적인 인용구(Direct Quote)가 있는 경우에만 작성.
            * 인물의 성함과 직함을 반드시 명시. (없으면 섹션 전체 삭제)      
       - [시사점]: 우리(국가, 기업, 개인)에게 미칠 영향을 고려하여 전략적 제언, 정책적 개선사항, 기술적 대응방안 등 단기 및 중장기적 전략을 도출하고, 핵심적인 시사점과 제언을 명확하고 간결하게 **200자 이내**로 정리해줘.
       - [출처]: <a href='링크'>매체명</a> 형식으로 표기.

    3. 태그: 기사 내용과 관련된 구체적인 기술 키워드(예: APT38, CVE-2024-XXXX, Zero-day 등)를 포함해 10개 이내로 추출.

    응답은 마크다운 없이 오직 순수 JSON 배열만 반환해:
    [
      {{
        "title": "...",
        "content": "...",
        "tags": ["...", "..."],
        "image_url": "..."
      }}
    ]

    대상 뉴스 리스트:
    {json.dumps(news_list, ensure_ascii=False)}
    """

    data = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "보안 뉴스 분석 전문가입니다. 반드시 JSON 배열 형식으로만 답변합니다."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=150)
        content = response.json()['choices'][0]['message']['content'].strip()
        json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
        return json.loads(json_match.group()) if json_match else json.loads(content)
    except Exception as e:
        print(f"AI 분석 실패: {e}")
        return []

def get_category_id(name):
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/categories"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    try:
        res = requests.get(endpoint, auth=auth, params={"search": name})
        categories = res.json()
        for cat in categories:
            if cat['name'].lower() == name.lower(): return cat['id']
    except: pass
    return None

def get_or_create_tag(name):
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/tags"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    try:
        res = requests.get(endpoint, auth=auth, params={"search": name})
        tags = res.json()
        for tag in tags:
            if tag['name'] == name: return tag['id']
        res = requests.post(endpoint, auth=auth, json={"name": name})
        if res.status_code in [200, 201]: return res.json()['id']
    except: pass
    return None

def post_to_wordpress(news_data, category_id):
    print(f"포스팅 중: {news_data['title']}")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    tag_ids = [get_or_create_tag(t) for t in news_data.get('tags', [])]
    tag_ids = [tid for tid in tag_ids if tid]
    
    payload = {
        "title": news_data['title'],
        "content": news_data['content'],
        "status": "publish",
        "categories": [category_id] if category_id else [],
        "tags": tag_ids
    }
    res = requests.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload)
    if res.status_code in [200, 201]: print("발행 성공!")
    else: print(f"발행 실패: {res.text}")

def main():
    if not all([PERPLEXITY_API_KEY, WP_USERNAME, WP_APP_PASSWORD]):
        print("에러: 필수 환경 변수가 설정되지 않았습니다.")
        return

    config = load_feeds_config()
    category_id = get_category_id("News")
    
    news_list = get_rss_news(config)
    if not news_list:
        print("최종적으로 수집된 뉴스가 없습니다.")
        return

    selected_news = analyze_news_with_perplexity(news_list)
    if not selected_news:
        print("AI 분석을 통해 선정된 뉴스가 없습니다.")
        return

    print(f"총 {len(selected_news)}개의 뉴스를 포스팅합니다.")
    for news in selected_news:
        try:
            post_to_wordpress(news, category_id)
            time.sleep(3)
        except Exception as e:
            print(f"처리 중 오류: {e}")

if __name__ == "__main__":
    main()
