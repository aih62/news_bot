import requests
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import html
from dotenv import load_dotenv

# .env 파일 로드 (로컬 테스트용)
load_dotenv(override=True)

# ================= CONFIGURATION =================
# 환경 변수에서 가져오되, 비어있거나 '/'만 있는 경우 기본값 사용
WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com")
if not WP_SITE_URL or WP_SITE_URL.strip() == "":
    WP_SITE_URL = "https://ajken.mycafe24.com"
WP_SITE_URL = WP_SITE_URL.rstrip('/')
KAKAO_TOKEN_JSON = os.getenv("KAKAO_TOKEN_JSON") # JSON string from GitHub Secrets
REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

# 갱신된 토큰을 GitHub Secret에 되쓰기 위한 설정
GH_PAT = os.getenv("GH_PAT")                          # secrets:write 권한 PAT
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")    # Actions가 자동 주입 (owner/repo)
KAKAO_SECRET_NAME = "KAKAO_TOKEN_JSON"

def get_kst_today():
    """한국 시간(KST) 기준으로 오늘 날짜 문자열(YYYY-MM-DD)을 반환합니다."""
    # UTC+9 설정
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
    """URL 단축 서비스로 단축 URL을 생성합니다. (API 키 불필요, 인터스티셜 없는 즉시 리다이렉트 우선)
    1. TinyURL (즉시 301 리다이렉트, 광고·클릭유도 페이지 없음)
    2. is.gd (깔끔한 리다이렉트, 일시 장애 대비 폴백)
    3. v.gd (is.gd 동일 계열 폴백)
    ※ da.gd는 신규 단축 URL에 클릭 확인 페이지(인터스티셜)를 도입해 제외함.
    """
    # 1. TinyURL 시도 (즉시 리다이렉트, 인터스티셜 없음)
    try:
        res = requests.get("https://tinyurl.com/api-create.php",
                           params={"url": long_url}, timeout=8)
        if res.status_code == 200:
            result = res.text.strip()
            if result.startswith("http") and "error" not in result.lower():
                return result
    except Exception:
        pass

    # 2. is.gd 시도 (깔끔한 리다이렉트)
    try:
        res = requests.get("https://is.gd/create.php",
                           params={"format": "simple", "url": long_url}, timeout=8)
        if res.status_code == 200:
            result = res.text.strip()
            if result.startswith("http") and "Error" not in result:
                return result
    except Exception:
        pass

    # 3. v.gd 시도 (is.gd 동일 계열 폴백)
    try:
        res = requests.get("https://v.gd/create.php",
                           params={"format": "simple", "url": long_url}, timeout=8)
        if res.status_code == 200:
            result = res.text.strip()
            if result.startswith("http") and "Error" not in result:
                return result
    except Exception:
        pass

    return long_url


def wp_shortlink(post):
    """워드프레스 기본 단축링크(?p=글ID)를 반환합니다.
    자기 도메인이라 외부 단축 서비스 없이 광고·인터스티셜 없이 항상 즉시(301) 리다이렉트됩니다."""
    try:
        from urllib.parse import urlparse
        u = urlparse(post.get('link', ''))
        pid = post.get('id')
        if u.scheme and u.netloc and pid:
            return f"{u.scheme}://{u.netloc}/?p={pid}"
    except Exception:
        pass
    return post.get('link', '')


def format_message(posts):
    """포스트 리스트를 간결한 카카오톡 메시지 형식으로 변환합니다."""
    today_str = get_kst_today()
    msg = f"[정보보호 산업 동향 {today_str}]\n\n"
    
    for i, post in enumerate(posts, 1):
        title = html.unescape(post['title']['rendered'])
        content_html = post['content']['rendered']
        soup = BeautifulSoup(content_html, 'html.parser')
        
        # 출처 추출 (p 태그 안의 텍스트)
        source_text = "기타"
        for p in soup.find_all('p'):
            if '출처:' in p.get_text():
                source_text = p.get_text().replace("출처:", "").strip()
                break
            
        # URL 단축: 워드프레스 기본 단축링크(?p=id) 사용 (자기 도메인·광고 없음·즉시 리다이렉트)
        link = wp_shortlink(post)
        
        msg += f"{i}. {title} [{source_text}]\n"
        msg += f"- {link}\n\n"
        
    return msg.strip()

def save_tokens_to_github_secret(tokens):
    """갱신된 카카오 토큰을 GitHub Actions Secret에 다시 저장합니다.

    카카오 refresh token은 유효기간이 2개월이며, 만료가 임박하면 갱신 시 새 토큰으로
    교체(rotate)됩니다. 회전된 refresh token을 저장하지 않으면 기존 토큰이 결국 만료되어
    KOE322(expired_or_invalid_refresh_token)가 발생하므로, Secret에 되써서 이를 예방합니다.
    """
    if not GH_PAT or not GITHUB_REPOSITORY:
        print("  -> GH_PAT/GITHUB_REPOSITORY 미설정: Secret 자동 저장을 건너뜁니다.")
        return False

    try:
        from nacl import encoding, public
    except ImportError:
        print("  -> PyNaCl 미설치: Secret 자동 저장을 건너뜁니다.")
        return False

    api = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/actions/secrets"
    headers = {
        "Authorization": f"Bearer {GH_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        # 1. 저장소 공개키 조회
        res = requests.get(f"{api}/public-key", headers=headers, timeout=20)
        if res.status_code != 200:
            print(f"  -> 공개키 조회 실패: {res.status_code}, {res.text[:150]}")
            return False
        pk = res.json()

        # 2. libsodium sealed box로 암호화 (GitHub Secret 규격)
        pub_key = public.PublicKey(pk["key"].encode(), encoding.Base64Encoder())
        sealed = public.SealedBox(pub_key).encrypt(
            json.dumps(tokens, ensure_ascii=False).encode("utf-8")
        )
        encrypted_value = encoding.Base64Encoder().encode(sealed).decode("utf-8")

        # 3. Secret 업데이트
        res = requests.put(
            f"{api}/{KAKAO_SECRET_NAME}",
            headers=headers,
            json={"encrypted_value": encrypted_value, "key_id": pk["key_id"]},
            timeout=20,
        )
        if res.status_code in (201, 204):
            print(f"  -> GitHub Secret '{KAKAO_SECRET_NAME}' 자동 갱신 완료.")
            return True
        print(f"  -> Secret 업데이트 실패: {res.status_code}, {res.text[:150]}")
    except Exception as e:
        print(f"  -> Secret 저장 중 예외 발생: {e}")
    return False


def refresh_kakao_token():
    """리프레시 토큰을 사용하여 액세스 토큰을 갱신합니다."""
    if not KAKAO_TOKEN_JSON or not REST_API_KEY:
        return None

    try:
        tokens = json.loads(KAKAO_TOKEN_JSON)
        refresh_token = tokens.get("refresh_token")

        url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": REST_API_KEY,
            "refresh_token": refresh_token
        }

        res = requests.post(url, data=data)
        if res.status_code == 200:
            new_tokens = res.json()
            # 카카오는 refresh token 만료가 1개월 미만으로 남았을 때만 새 토큰을 내려준다.
            rotated = bool(new_tokens.get("refresh_token")) and new_tokens["refresh_token"] != refresh_token

            # 기존 리프레시 토큰이 유지되는 경우가 많으므로 병합
            if 'refresh_token' not in new_tokens:
                new_tokens['refresh_token'] = refresh_token
            print("카카오 토큰 갱신 성공!")

            # refresh token이 회전된 경우에만 Secret에 되써서 만료(KOE322)를 예방
            if rotated:
                print("  -> refresh token이 회전되었습니다. GitHub Secret에 저장합니다.")
                save_tokens_to_github_secret({
                    "access_token": new_tokens.get("access_token"),
                    "refresh_token": new_tokens.get("refresh_token"),
                })

            return new_tokens
        else:
            print(f"카카오 토큰 갱신 실패: {res.status_code}, {res.text}")
            if "KOE322" in res.text or "invalid_grant" in res.text:
                print("  ** refresh token이 만료/폐기되었습니다. kakao_auth_helper.py로 재인증 후 "
                      f"'{KAKAO_SECRET_NAME}' Secret을 갱신하세요. **")
    except Exception as e:
        print(f"토큰 갱신 중 예외 발생: {e}")
    return None

def send_kakao_memo(message):
    """카카오톡 '나에게 보내기' API를 호출합니다."""
    # 1. 먼저 토큰 갱신 시도
    new_tokens = refresh_kakao_token()
    if not new_tokens:
        print("토큰 갱신에 실패하여 기존 토큰을 사용합니다.")
        if not KAKAO_TOKEN_JSON: return False
        tokens = json.loads(KAKAO_TOKEN_JSON)
    else:
        tokens = new_tokens
        
    access_token = tokens.get("access_token")
    
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 텍스트 메시지 구성 (카카오톡 텍스트 컴포넌트 제약사항 준수)
    template = {
        "object_type": "text",
        "text": message,
        "link": {
            "web_url": WP_SITE_URL,
            "mobile_web_url": WP_SITE_URL
        },
        "button_title": "뉴스 센터 바로가기"
    }
    
    payload = {"template_object": json.dumps(template)}
    
    res = requests.post(url, headers=headers, data=payload)
    if res.status_code == 200:
        print("카카오톡 메시지 전송 성공!")
        return True
    else:
        print(f"전송 실패: {res.status_code}, {res.text}")
        return False

def verify_secret_save():
    """GH_PAT의 Secret 쓰기 권한을 즉시 검증합니다 (알림 전송 없음).

    자동 저장은 refresh token이 회전할 때(약 1개월 뒤)만 실행되므로, PAT 권한이 잘못돼도
    그때까지 드러나지 않습니다. 이 모드는 현재 토큰을 그대로 다시 저장(멱등)해봄으로써
    쓰기 권한을 지금 확인합니다.
    """
    print("=== GH_PAT Secret 쓰기 권한 검증 모드 (카카오톡 전송 안 함) ===")
    if not GH_PAT:
        print("GH_PAT가 설정되지 않았습니다.")
        sys.exit(1)

    tokens = refresh_kakao_token()
    if not tokens:
        print("토큰 갱신 실패 - KAKAO_TOKEN_JSON을 먼저 확인하세요.")
        sys.exit(1)

    ok = save_tokens_to_github_secret({
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
    })
    if ok:
        print("\n검증 성공: refresh token 회전 시 자동 저장이 정상 동작합니다.")
        sys.exit(0)

    print("\n검증 실패: GH_PAT의 권한(Repository permissions -> Secrets: Read and write)과 "
          "대상 저장소 설정을 확인하세요.")
    sys.exit(1)


def main():
    # 검증 모드: 워크플로에서 verify_secret_save 입력으로 실행 가능
    if "--verify-secret-save" in sys.argv:
        verify_secret_save()
        return

    posts = get_today_posts()
    if not posts:
        # 당일 게시된 뉴스가 없으면 0건 안내 메시지를 전송한다.
        today_str = get_kst_today()
        zero_msg = f"[정보보호 산업 동향 {today_str}]\n\n오늘 게시된 뉴스가 없습니다. (0건)"
        print("오늘 올라온 포스팅이 없습니다 → 0건 안내 전송")
        if not send_kakao_memo(zero_msg):
            sys.exit(1)
        return

    message = format_message(posts)
    print("--- 생성된 메시지 ---")
    print(message)

    # 전송 실패 시 워크플로를 실패 처리하여 GitHub 알림을 받도록 함
    # (refresh token 만료 등 재인증이 필요한 상황을 놓치지 않기 위함)
    if not send_kakao_memo(message):
        sys.exit(1)

if __name__ == "__main__":
    main()
