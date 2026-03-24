import feedparser
import time
import calendar
import json
import os
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import quote
import html
from dotenv import load_dotenv

load_dotenv()

WP_USERNAME = os.getenv("WP_USERNAME") or "inhoe.an@gmail.com"
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
WP_SITE_URL = os.getenv("WP_SITE_URL") or "https://ajken.mycafe24.com"
WP_SITE_URL = WP_SITE_URL.rstrip("/")

def get_recent_post_titles():
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    params = {"per_page": 30, "status": "publish"}
    try:
        res = requests.get(endpoint, auth=auth, params=params, timeout=20, verify=False)
        if res.status_code == 200:
            posts = res.json()
            titles = [html.unescape(post['title']['rendered']) for post in posts]
            return titles
    except Exception as e:
        print(f"Failed to get recent titles: {e}")
    return []

def test_rss_fetch():
    feeds_path = r"C:\Users\inhoe\Desktop\news_bot\news_bot\feeds.json"
    with open(feeds_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        direct_feeds = config.get("direct_feeds", {})
        search_categories = config.get("search_categories", {})

    recent_titles = get_recent_post_titles()
    
    now = time.time()
    day_in_seconds = 24 * 60 * 60
    
    all_entries = []
    seen_links = set()
    
    print(f"Current Time: {time.ctime(now)}")
    
    for source_name, rss_url in direct_feeds.items():
        print(f"Checking {source_name}: {rss_url}...")
        try:
            feed = feedparser.parse(rss_url)
            print(f"  -> Feed has {len(feed.entries)} entries.")
            count = 0
            for entry in feed.entries[:15]:
                is_recent = True
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    entry_time = calendar.timegm(entry.published_parsed)
                    time_diff = now - entry_time
                    if time_diff > day_in_seconds:
                        is_recent = False
                    # print(f"    - Title: {entry.title[:30]}... Recent: {is_recent} (Diff: {time_diff/3600:.1f}h)")
                
                if is_recent:
                    count += 1
                    # Also check for title similarity (simple check)
                    is_duplicate = False
                    for rt in recent_titles:
                        if entry.title.lower() in rt.lower() or rt.lower() in entry.title.lower():
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        all_entries.append(entry.title)
                    else:
                        pass # print(f"    - DUPLICATE: {entry.title[:30]}...")
            print(f"  -> Found {count} recent articles.")
        except Exception as e:
            print(f"  -> Error: {e}")

    # Search categories
    for category_name, keywords in search_categories.items():
        print(f"Checking Category: {category_name}...")
        query = " OR ".join([f'"{k}"' if " " in k else k for k in keywords])
        rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
        print(f"  -> RSS URL: {rss_url}")
        try:
            feed = feedparser.parse(rss_url)
            print(f"  -> Feed has {len(feed.entries)} entries.")
            count = 0
            for entry in feed.entries[:15]:
                is_recent = True
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    entry_time = calendar.timegm(entry.published_parsed)
                    if now - entry_time > day_in_seconds:
                        is_recent = False
                if is_recent:
                    count += 1
                    is_duplicate = False
                    for rt in recent_titles:
                        if entry.title.lower() in rt.lower() or rt.lower() in entry.title.lower():
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        all_entries.append(entry.title)
                        print(f"    - Found: {entry.title[:50]}...")
            print(f"  -> Found {count} recent articles.")
        except Exception as e:
            print(f"  -> Error: {e}")

    print(f"\nTotal potential new news items (after simple title match filter): {len(all_entries)}")
    for title in all_entries[:10]:
        print(f"- {title}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    test_rss_fetch()
