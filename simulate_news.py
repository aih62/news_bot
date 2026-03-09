import feedparser
import requests
import json
import re
from urllib.parse import urljoin
import os

# ================= CONFIGURATION =================
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

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
    except Exception as e:
        print(f"      [Error] 웹페이지 이미지 추출 실패: {e}")
    return None

def simulate_news_fetch():
    print("--- 뉴스 수집 및 이미지 추출 시뮬레이션 시작 ---")
    
    # feeds.json 로드
    try:
        with open("feeds.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            direct_feeds = config.get("direct_feeds", {})
    except Exception as e:
        print(f"feeds.json 로드 실패: {e}")
        return

    results = []
    
    for source_name, rss_url in direct_feeds.items():
        print(f"\n[{source_name}] 수집 중: {rss_url}")
        feed = feedparser.parse(rss_url)
        
        # 각 피드당 최신 3개만 테스트하여 빠른 결과 확인
        for entry in feed.entries[:3]:
            title = entry.get("title", "제목 없음")
            link = entry.get("link", "")
            
            print(f"  - 제목: {title}")
            
            # 1. RSS 내 메타데이터에서 이미지 확인
            img_url = None
            if 'media_content' in entry and entry.media_content:
                try:
                    img_url = entry.media_content[0].get('url')
                    if img_url:
                        print(f"    [RSS] media_content 발견: {img_url}")
                except (IndexError, AttributeError, KeyError):
                    pass
            
            if not img_url and 'media_thumbnail' in entry and entry.media_thumbnail:
                try:
                    img_url = entry.media_thumbnail[0].get('url')
                    if img_url:
                        print(f"    [RSS] media_thumbnail 발견: {img_url}")
                except (IndexError, AttributeError, KeyError):
                    pass
            
            # 2. 본문(description) 내 img 태그 확인
            if not img_url:
                content = entry.get('summary', '') + entry.get('description', '')
                img_match = re.search(r'<img [^>]*src="([^"]+)"', content)
                if img_match:
                    img_url = img_match.group(1)
                    print(f"    [RSS] 본문 내 img 태그 발견: {img_url}")
            
            # 3. 원본 웹페이지 og:image/twitter:image 확인
            if not img_url:
                print(f"    [WEB] 웹페이지에서 이미지 메타 태그 검색 중: {link}")
                img_url = get_image_from_webpage(link)
                if img_url:
                    print(f"    [WEB] 이미지 메타 태그 발견: {img_url}")
                else:
                    print(f"    [FAIL] 이미지를 찾을 수 없음")
            
            results.append({
                "source": source_name,
                "title": title,
                "img_url": img_url
            })

    print("\n" + "="*50)
    print("시뮬레이션 결과 요약")
    print("="*50)
    for r in results:
        status = "✅" if r['img_url'] else "❌"
        print(f"{status} [{r['source']}] {r['title'][:40]}...")
    
    found_count = len([r for r in results if r['img_url']])
    print(f"\n총계: {len(results)}개 중 {found_count}개 이미지 확보 성공")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    simulate_news_fetch()
