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
WP_SITE_URL = "https://ajken.mycafe24.com"

# 뉴스 검색 키워드 및 RSS URL
RSS_URL = "https://news.google.com/rss/search?q=사이버보안+OR+정보보안&hl=ko&gl=KR&ceid=KR:ko"
# ========================================================

def get_rss_news():
    """구글 뉴스 RSS에서 최신 기사 목록을 가져옵니다."""
    print("RSS 피드 읽는 중...")
    try:
        feed = feedparser.parse(RSS_URL)
        entries = []
        for entry in feed.entries[:30]:
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
    너는 사이버 보안 전문가 뉴스 편집자야. 아래 제공된 뉴스 리스트 중 
    기술적 가치, 사회적 파급력, 인용 횟수를 고려하여 가장 중요한 뉴스 10개를 선정해줘.
    
    각 뉴스에 대해 다음 작업을 수행해:
    1. 핵심 내용을 3~4문장으로 요약해 (한국어).
    2. 뉴스 내용에 가장 적합한 워드프레스 카테고리 하나를 정해 (예: 기술, 정책, 산업, 보안사고).
    3. 관련 태그 3~5개를 생성해.
    4. 뉴스 원문에서 가장 대표적인 이미지 URL을 찾아줘. (없으면 null로 표시)

    결과는 반드시 아래의 순수 JSON 리스트 형식으로만 응답해 (설명 없이 JSON만):
    [
      {{
        "title": "뉴스 제목",
        "content": "요약된 본문 내용",
        "category": "카테고리명",
        "tags": ["태그1", "태그2"],
        "image_url": "이미지 주소 혹은 null",
        "source_url": "원본 링크"
      }}
    ]

    대상 뉴스 리스트:
    {json.dumps(news_list, ensure_ascii=False)}
    """

    data = {
        "model": "sonar-reasoning",
        "messages": [
            {"role": "system", "content": "보안 뉴스 분석 전문가입니다. 반드시 JSON 형식으로만 답변합니다."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=60)
        content = response.json()['choices'][0]['message']['content']
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
        "content": f"{news_data['content']}<br><br><a href='{news_data['source_url']}' target='_blank'>원문 기사 읽기</a>",
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

    for news in selected_news:
        try:
            post_to_wordpress(news)
            time.sleep(2)
        except Exception as e:
            print(f"처리 중 오류: {e}")

if __name__ == "__main__":
    main()
