import feedparser
import requests
import json
import re
from requests.auth import HTTPBasicAuth
import time
import os

# ================= CONFIGURATION (환경 변수 설정) =================
# GitHub Secrets에 등록한 값을 자동으로 읽어옵니다.
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

# 본인의 워드프레스 주소 (수정 필요 시 여기서 변경)
WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com")

# 뉴스 검색 키워드 및 RSS URL (글로벌 전문 매체 타겟팅)
TARGET_SITES = [
    "thehackernews.com", "darkreading.com", "securityweek.com", "scmagazine.com", 
    "infosecurity-magazine.com", "cyberscoop.com", "therecord.media", "arstechnica.com", 
    "techtarget.com", "wired.com", "krebsonsecurity.com", "csoonline.com", 
    "bleepingcomputer.com", "govinfosecurity.com", "welivesecurity.com", "zdnet.com", 
    "techcrunch.com", "washingtonpost.com", "hackread.com", "politico.com"
]
site_query = " OR ".join([f"site:{site}" for site in TARGET_SITES])
RSS_URL = f"https://news.google.com/rss/search?q=({site_query})+(사이버보안+OR+정보보안+OR+%22Cyber+security%22+OR+%22Information+Security%22)&hl=ko&gl=KR&ceid=KR:ko"
# ========================================================

def get_rss_news():
    """구글 뉴스 RSS에서 최신 기사 목록을 가져옵니다."""
    print("글로벌 전문 매체 RSS 피드 읽는 중...")
    try:
        feed = feedparser.parse(RSS_URL)
        entries = []
        for entry in feed.entries[:80]: # 해외 매체가 많으므로 더 많이 수집
            entries.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published
            })
        return entries
    except Exception as e:
        print(f"RSS 읽기 실패: {e}")
        return []

def analyze_news_with_perplexity(news_list):
    """Perplexity AI를 사용하여 뉴스 선정 및 분석을 수행합니다."""
    if not news_list:
        return []
        
    print(f"Perplexity AI 분석 중 ({len(news_list)}개 기사 중 10개 선정)...")
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    너는 글로벌 사이버 보안 전문가 뉴스 편집자야. 아래 제공된 뉴스 리스트 중 
    기술적 가치, 사회적 파급력, 인용 횟수를 고려하여 가장 중요한 뉴스 10개를 선정해줘.
    
    각 뉴스에 대해 다음 구조로 상세하게 작성해 (반드시 한국어로 작성):

    1. 제목: 영문 뉴스인 경우 원문의 의미를 살려 한국어로 번역하되 전문적인 제목으로 작성해.
    
    2. 본문 내용 (HTML 태그를 사용하여 작성):
       - [서브 헤드라인]: <h3> 태그를 사용하여 기사의 핵심 내용을 한 줄로 요약해줘. (기사 제목보다 구체적이고 깊이 있는 내용을 담아야 함)
       - [주요내용 요약]: 기사의 주요 내용을 10개 이하의 글머리 기호("-" 사용)로 요약해줘.
         * 반드시 '개조식'(문장 끝을 '~함', '~임', '~함' 등으로 간결하게 마무리)으로 작성할 것.
         * 각 문장은 최소 50글자 내외로 상세하게 작성할 것.
         * 문장들 간에는 상호 논리적인 흐름이 있어야 함.
       - [시사점]: 우리나라의 기술, 정책, 산업 현황을 고려했을 때 어떤 부분의 개선이나 반영이 필요한지 3문장 이내로 작성해줘.
       - [출처]: 해당 기사의 '매체명'을 표시하고, 이를 클릭하면 원문 기사 링크로 이동할 수 있도록 <a href='링크'>매체명</a> 형식으로 작성해줘.

    결과는 반드시 아래의 순수 JSON 리스트 형식으로만 응답해 (설명 없이 JSON만):
    [
      {{
        "title": "뉴스 제목",
        "content": "위의 모든 섹션이 포함된 HTML 형식의 본문",
        "category": "카테고리명",
        "tags": ["태그1", "태그2"],
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
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=60)
        res_json = response.json()
        if 'choices' not in res_json:
            print(f"API 응답 에러: {res_json}")
            return []
        content = res_json['choices'][0]['message']['content']
        json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(content)
    except Exception as e:
        print(f"AI 분석 실패: {e}")
        return []

def get_or_create_term(taxonomy, name):
    """카테고리나 태그의 ID를 가져오거나 없으면 생성합니다."""
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/{taxonomy}"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    try:
        res = requests.get(endpoint, auth=auth, params={"search": name})
        terms = res.json()
        for term in terms:
            if term['name'] == name:
                return term['id']
        res = requests.post(endpoint, auth=auth, json={"name": name})
        if res.status_code in [200, 201]:
            return res.json()['id']
    except:
        pass
    return None

def upload_media_from_url(image_url):
    """이미지 URL을 워드프레스 미디어 라이브러리에 업로드하고 ID를 반환합니다."""
    if not image_url or not image_url.startswith("http"):
        return None
        
    print(f"이미지 업로드 시도: {image_url[:50]}...")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    try:
        img_res = requests.get(image_url, timeout=10)
        if img_res.status_code == 200:
            filename = f"news_img_{int(time.time())}.jpg"
            headers = {
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "image/jpeg"
            }
            up_res = requests.post(
                f"{WP_SITE_URL}/wp-json/wp/v2/media",
                auth=auth,
                headers=headers,
                data=img_res.content
            )
            if up_res.status_code in [200, 201]:
                return up_res.json()['id']
    except Exception as e:
        print(f"이미지 업로드 실패: {e}")
    return None

def post_to_wordpress(news_data):
    """뉴스를 워드프레스에 포스팅합니다."""
    print(f"포스팅 중: {news_data['title']}")
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    cat_id = get_or_create_term("categories", news_data['category'])
    tag_ids = [get_or_create_term("tags", t) for t in news_data['tags']]
    tag_ids = [tid for tid in tag_ids if tid]
    
    media_id = upload_media_from_url(news_data['image_url'])
    
    payload = {
        "title": news_data['title'],
        "content": news_data['content'],
        "status": "publish",
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "featured_media": media_id if media_id else 0
    }
    
    res = requests.post(f"{WP_SITE_URL}/wp-json/wp/v2/posts", auth=auth, json=payload)
    if res.status_code in [200, 201]:
        print("발행 성공!")
    else:
        print(f"발행 실패: {res.text}")

def main():
    if not all([PERPLEXITY_API_KEY, WP_USERNAME, WP_APP_PASSWORD]):
        print("에러: 환경 변수(API Key, WP 로그인 정보)가 설정되지 않았습니다.")
        return

    news_list = get_rss_news()
    selected_news = analyze_news_with_perplexity(news_list)
    
    if not selected_news:
        print("선정된 뉴스가 없습니다.")
        return

    # [테스트용] 첫 번째 뉴스 딱 1개만 포스팅하여 형식을 확인합니다.
    test_news = selected_news[:1]
    for news in test_news:
        try:
            post_to_wordpress(news)
            time.sleep(2)
        except Exception as e:
            print(f"처리 중 오류: {e}")

if __name__ == "__main__":
    main()
