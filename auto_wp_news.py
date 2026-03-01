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

# Ultimate 글로벌 보안 소스 리스트 (32개 정예 사이트)
TARGET_SITES = [
    # Global Security News (Top Tier)
    "thehackernews.com", "bleepingcomputer.com", "therecord.media", "krebsonsecurity.com",
    "darkreading.com", "securityweek.com", "cyberscoop.com", "infosecurity-magazine.com",
    "scmagazine.com", "arstechnica.com", "wired.com", "csoonline.com",
    # Tech Vendor Intelligence (Primary Sources)
    "mandiant.com", "crowdstrike.com", "paloaltonetworks.com", "microsoft.com", 
    "googleblog.com", "cloudflare.com", "trendmicro.com", "sentinelone.com",
    # Vulnerability & Deep Research
    "zerodayinitiative.com", "sans.org", "citizenlab.ca",
    # Cloud-Native & ICS/OT Security
    "wiz.io", "snyk.io", "sysdig.com", "dragos.com",
    # Enterprise & Policy
    "zdnet.com", "techcrunch.com", "politico.com",
    # Domestic Trends
    "boannews.com", "dailysecu.com"
]

KEYWORDS = [
    "사이버보안", "정보보안", "Cybersecurity", "Ransomware", 
    "Vulnerability", "Malware", "Data breach", "Cyber attack"
]

site_query = " OR ".join([f"site:{site}" for site in TARGET_SITES])
keyword_query = " OR ".join([f'"{k}"' for k in KEYWORDS])
search_query = f"({site_query}) ({keyword_query})"
encoded_query = urllib.parse.quote(search_query)

# tbs=qdr:d (최근 1일 필터) 및 글로벌 검색 설정
RSS_URL = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en&tbs=qdr:d"
# ========================================================

def get_rss_news():
    """구글 뉴스 RSS에서 최근 기사 목록을 가져옵니다."""
    print(f"글로벌 보안 소스({len(TARGET_SITES)}개) RSS 피드 읽는 중...")
    try:
        feed = feedparser.parse(RSS_URL)
        all_entries = feed.entries
        print(f"구글 뉴스에서 검색된 총 기사 수: {len(all_entries)}개")
        
        if len(all_entries) == 0:
            print("사이트 제한 검색 결과가 없어 키워드 단독 검색으로 재시도합니다...")
            backup_query = urllib.parse.quote(" OR ".join([f'"{k}"' for k in KEYWORDS]))
            url = f"https://news.google.com/rss/search?q={backup_query}&hl=en-US&gl=US&ceid=US:en&tbs=qdr:d"
            feed = feedparser.parse(url)
            all_entries = feed.entries

        entries = []
        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)

        for entry in all_entries:
            published_time = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            
            if not published_time or published_time > one_day_ago:
                entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.get('published', 'N/A')
                })
            
            if len(entries) >= 100:
                break

        print(f"최종 분석 대상 기사 수: {len(entries)}개")
        return entries
    except Exception as e:
        print(f"RSS 읽기 실패: {e}")
        return []

def analyze_news_with_perplexity(news_list):
    """Perplexity AI를 사용하여 5가지 기준에 따라 점수를 매기고 상위 10개를 분석합니다."""
    if not news_list:
        return []
        
    print(f"Perplexity AI 정량 평가 및 분석 중 (대상 기사 {len(news_list)}개)...")
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    너는 글로벌 사이버 보안 전문가 뉴스 편집자야. 아래 제공된 뉴스 리스트 중 
    다음 5가지 평가 기준을 바탕으로 총점이 가장 높은 상위 10개 뉴스를 선정해줘:
    
    [평가 기준 (총 100점)]
    1. 파급력 및 규모 (Impact): 30점
    2. 기술적 심각성 (Severity): 25점
    3. 시의성 (Timeliness): 20점
    4. 출처 신뢰성 (Credibility): 15점
    5. 전략적 시사점 (Insights): 10점

    각 뉴스에 대해 다음 구조로 상세하게 작성해 (반드시 한국어로 작성):

    1. 제목: 영문 뉴스인 경우 원문의 의미를 살려 한국어로 번역하되 전문적인 제목으로 작성해.
    2. 본문 내용 (HTML 태그 사용):
       - [서브 헤드라인]: <h3> 태그를 사용하여 기사의 핵심 내용을 한 줄로 요약해줘. (제목보다 구체적이어야 함)
       - [주요내용 요약]: <ul> 및 <li> 태그를 사용하여 기사의 주요 내용을 10개 이하의 리스트 형식으로 요약해줘.
         * 반드시 '개조식'(문장 끝을 '~함', '~임', '~함' 등으로 간결하게 마무리)으로 작성할 것.
         * 각 문장은 최소 50글자 내외로 상세하게 작성할 것.
         * 문장들 간에는 상호 논리적인 흐름이 있어야 함.
         * 별도의 글머리 기호는 텍스트에 포함하지 말고 <li> 태그만 사용할 것.
       - [시사점]: 국가, 기업, 개인에게 미칠 영향을 고려하여 전략적 제언, 정책적 개선사항, 기술적 대응방안 등 단기 및 중장기적 전략을 도출하고, 핵심적인 시사점과 제언을 명확하고 간결하게 200자 이내로 정리해줘.
       - [출처]: 매체명을 표시하고 원문 링크를 걸어줘.
    3. 태그: 기사 내용과 관련된 핵심 키워드를 10개 이내로 추출해줘.

    결과는 반드시 아래의 순수 JSON 리스트 형식으로만 응답해:
    [
      {{
        "title": "뉴스 제목",
        "content": "HTML 형식의 상세 본문",
        "tags": ["태그1", "태그2", ...],
        "image_url": "이미지 주소 혹은 null"
      }}
    ]

    대상 뉴스 리스트:
    {json.dumps(news_list, ensure_ascii=False)}
    """

    data = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "보안 뉴스 분석 전문가입니다. 반드시 JSON 형식으로만 답변합니다."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=90)
        res_json = response.json()
        if 'choices' not in res_json:
            print(f"API 응답 에러: {res_json}")
            return []
        content = res_json['choices'][0]['message']['content']
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

    category_id = get_category_id("News")
    news_list = get_rss_news()
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
