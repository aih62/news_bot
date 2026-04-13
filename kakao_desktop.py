import win32gui
import win32api
import win32con
import time
import pyperclip
import pyautogui
import requests
import json
import os
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import html
from dotenv import load_dotenv

load_dotenv()

# ================= CONFIGURATION =================
WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com")
if not WP_SITE_URL or WP_SITE_URL.strip() == "":
    WP_SITE_URL = "https://ajken.mycafe24.com"
WP_SITE_URL = WP_SITE_URL.rstrip('/')
# =================================================

def get_kst_today():
    """한국 시간(KST) 기준으로 오늘 날짜 문자열(YYYY-MM-DD)을 반환합니다."""
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime("%Y-%m-%d")

def get_today_posts():
    """워드프레스에서 오늘 날짜의 최신 포스트 10개를 가져옵니다."""
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    params = {"per_page": 10, "status": "publish"}
    try:
        res = requests.get(endpoint, params=params, timeout=20)
        if res.status_code == 200:
            posts = res.json()
            today_str = get_kst_today()
            today_posts = []
            for post in posts:
                # 워드프레스 날짜 형식: "2026-03-06T07:00:00"
                if post['date'].startswith(today_str):
                    today_posts.append(post)
            return today_posts
    except Exception as e:
        print(f"포스트 가져오기 실패: {e}")
    return []

def shorten_url(long_url):
    """is.gd API를 사용하여 단축 URL을 생성합니다. (API 키 불필요)
    is.gd 오류 발생 시 tinyurl.com으로 폴백합니다.
    """
    # 1. is.gd 시도
    try:
        url = "https://is.gd/create.php"
        params = {"format": "simple", "url": long_url}
        res = requests.get(url, params=params, timeout=10)
        
        if res.status_code == 200:
            result = res.text.strip()
            if result.startswith("http"):
                return result
            else:
                print(f"URL 단축 실패 (is.gd 응답 오류): {result}")
        else:
            print(f"URL 단축 실패 (is.gd 상태 코드): {res.status_code}")
    except Exception as e:
        print(f"URL 단축 오류 (is.gd): {e}")

    # 2. tinyurl.com 폴백
    try:
        url = "https://tinyurl.com/api-create.php"
        params = {"url": long_url}
        res = requests.get(url, params=params, timeout=10)
        
        if res.status_code == 200:
            result = res.text.strip()
            if result.startswith("http"):
                return result
        else:
            print(f"URL 단축 실패 (tinyurl 상태 코드): {res.status_code}")
    except Exception as e:
        print(f"URL 단축 오류 (tinyurl): {e}")

    return long_url

def format_message(posts):
    """포스트 리스트를 가독성 좋은 카카오톡 메시지 형식으로 변환합니다."""
    today_str = get_kst_today()
    msg = f"🛡️ *[보안/IT 산업 동향] {today_str}*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, post in enumerate(posts, 1):
        title = html.unescape(post['title']['rendered'])
        content_html = post['content']['rendered']
        soup = BeautifulSoup(content_html, 'html.parser')
        
        # 출처 추출
        source_text = "기타"
        for p in soup.find_all('p'):
            if '출처:' in p.get_text():
                source_text = p.get_text().replace("출처:", "").strip()
                break
            
        # URL 단축 적용
        link = shorten_url(post['link'])
        
        # 숫자 + 제목 + 출처
        msg += f"{i}. *{title}* [{source_text}]\n"
        msg += f"🔗 {link}\n\n"
        
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"💻 뉴스 센터: {WP_SITE_URL}\n"
    msg += "🔔 매일 아침 자동으로 배달됩니다."
        
    return msg.strip()

def find_edit_handle(parent_hwnd):
    """모든 자식 윈도우를 뒤져서 메시지를 입력할 수 있는 에디터 핸들을 찾아냅니다."""
    child_list = []
    def callback(hwnd, extra):
        child_list.append((hwnd, win32gui.GetClassName(hwnd)))
        return True
    win32gui.EnumChildWindows(parent_hwnd, callback, None)
    
    # 카카오톡 업데이트로 인해 'RICHEDIT50W' (대문자) 등으로 변경된 경우를 대비하여 소문자로 변환해서 검사합니다.
    edit_hwnds = [h for h, c in child_list if "richedit" in c.lower() or "chateditor" in c.lower()]
    if edit_hwnds:
        return edit_hwnds[-1] # 보통 마지막에 생성된 RichEdit이 입력창입니다.
    return None

def send_message_to_room(room_name, message):
    """특정 채팅방에 메시지를 전송합니다."""
    hwnd = win32gui.FindWindow(None, room_name)
    
    if not hwnd:
        print(f"[Fail] '{room_name}' 채팅방을 찾을 수 없습니다.")
        return False

    edit_hwnd = find_edit_handle(hwnd)
    
    if not edit_hwnd:
        print(f"[Fail] '{room_name}'의 입력 영역을 찾지 못했습니다.")
        return False

    # 창을 앞으로 가져오기 위한 좀 더 강력한 방법
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        # Windows의 SetForegroundWindow 제약을 피하기 위해 Alt 키를 먼저 한 번 누릅니다.
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        win32gui.SetForegroundWindow(hwnd)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        
        time.sleep(0.5)
        
        # 입력창 위치 재계산 및 클릭 (DPI 대응을 위해 넉넉한 위치 클릭)
        rect = win32gui.GetWindowRect(edit_hwnd)
        # rect = (left, top, right, bottom)
        click_x = rect[0] + 10
        click_y = rect[1] + 10
        pyautogui.click(click_x, click_y)
        time.sleep(0.3)
        
    except Exception as e:
        print(f"[Warn] 창 활성화 보조 로직 시도 중: {e}")

    # 내용을 클립보드에 복사
    pyperclip.copy(message)
    
    # 확실한 붙여넣기 (기존 내용 삭제를 위해 전체선택 후 붙여넣기)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'v')
    
    # 내용이 많으므로 렌더링 대기 시간을 더 늘림
    time.sleep(2.0) 
    
    # 전송 시도: Enter, Ctrl+Enter, 그리고 다시 한번 Enter (확실한 전송을 위해)
    pyautogui.press('enter')
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'enter')
    
    # 마지막 확인 사위로 SendMessage 방식도 섞어서 시도 (보안 패치되지 않은 경우를 대비)
    win32api.PostMessage(edit_hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    win32api.PostMessage(edit_hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
    
    print(f"[Success] '{room_name}' 채팅방에 메시지 전송 완료!")
    return True

if __name__ == "__main__":
    print("오늘의 워드프레스 뉴스를 가져오는 중입니다...")
    posts = get_today_posts()
    
    if not posts:
        print("오늘 발행된 뉴스가 없습니다.")
    else:
        print(f"총 {len(posts)}개의 뉴스를 찾았습니다. 카카오톡 전송을 준비합니다...")
        
        # 뉴스 메시지 생성 (URL 단축 포함)
        news_msg = format_message(posts)
        
        # 발송할 채팅방 이름 지정
        # 실제 여러 방에 동시에 보내려면 이곳의 로직을 리스트 반복문으로 확장하면 됩니다.
        target_room = "안씨네카톡방" 
        send_message_to_room(target_room, news_msg)
