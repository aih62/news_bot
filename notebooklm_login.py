"""
NotebookLM 자동 로그인 스크립트
Playwright를 사용하여 Google 계정으로 로그인하고 인증 쿠키를 저장합니다.
저장 경로: ~/.notebooklm/storage_state.json
"""

import asyncio
import os
import sys
import pathlib

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

GOOGLE_EMAIL = os.environ.get("GOOGLE_EMAIL", "ken.inhoean@gmail.com")
GOOGLE_PASSWORD = os.environ.get("GOOGLE_PASSWORD", "")

NOTEBOOKLM_URL = "https://notebooklm.google.com/"
STORAGE_DIR = pathlib.Path.home() / ".notebooklm"
STORAGE_PATH = STORAGE_DIR / "storage_state.json"


def save_storage_state_from_env():
    """환경변수 NOTEBOOKLM_STORAGE_STATE가 있으면 파일로 저장합니다."""
    env_state = os.environ.get("NOTEBOOKLM_STORAGE_STATE")
    if env_state:
        print("환경변수 'NOTEBOOKLM_STORAGE_STATE' 감지됨. 세션 정보를 복원합니다.", flush=True)
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        with open(STORAGE_PATH, 'w', encoding='utf-8') as f:
            f.write(env_state)
        print(f"세션 정보 복원 완료: {STORAGE_PATH}", flush=True)
        return True
    return False


async def login_to_notebooklm():
    save_storage_state_from_env()
    
    # 만약 이미 storage_state.json이 유효하다면 로그인을 건너뛸 수도 있지만,
    # 여기서는 환경변수가 있으면 저장만 하고 뒤의 로직은 그대로 두어 
    # 필요시 로그인을 시도하게 합니다. 단 GitHub Action에서는 로그인이 실패할 확률이 높으므로
    # 환경변수로 세션을 주입하는 것이 주 목적입니다.
    
    if not GOOGLE_PASSWORD:
        if STORAGE_PATH.exists():
            print("비밀번호는 없지만 기존 세션 파일이 존재합니다. 로그인을 건너뜁니다.", flush=True)
            return
        print("오류: GOOGLE_PASSWORD 환경변수가 설정되지 않았습니다.", flush=True)
        sys.exit(1)

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        print("Chromium 브라우저 시작 중...", flush=True)
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--window-size=1280,800",
            ]
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        # playwright-stealth으로 자동화 감지 우회
        await Stealth().apply_stealth_async(page)

        try:
            # Step 1: NotebookLM 접속 (Google 로그인 페이지로 리디렉션됨)
            print(f"NotebookLM 접속 중: {NOTEBOOKLM_URL}", flush=True)
            await page.goto(NOTEBOOKLM_URL, wait_until="domcontentloaded", timeout=30000)

            # Step 2: 이메일 입력
            print("Google 로그인 페이지 감지, 이메일 입력 중...", flush=True)
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state="visible", timeout=15000)
            await email_input.fill(GOOGLE_EMAIL)
            await page.keyboard.press("Enter")
            print(f"이메일 입력 완료: {GOOGLE_EMAIL}", flush=True)

            # Step 3: 비밀번호 입력
            print("비밀번호 입력 중...", flush=True)
            password_input = page.locator('input[type="password"]')
            await password_input.wait_for(state="visible", timeout=15000)
            await asyncio.sleep(1)  # 안정화 대기
            await password_input.fill(GOOGLE_PASSWORD)
            await page.keyboard.press("Enter")
            print("비밀번호 입력 완료.", flush=True)

            # Step 4: 로그인 완료 후 NotebookLM으로 리디렉션 대기
            print("로그인 처리 및 NotebookLM으로 리디렉션 대기 중...", flush=True)
            try:
                # "로그인 상태 유지" 프롬프트 처리 (나타날 경우)
                stay_signed_in = page.locator('text="로그인 상태로 유지"')
                if await stay_signed_in.is_visible():
                    await stay_signed_in.click()
                    print("'로그인 상태 유지' 클릭.", flush=True)
            except Exception:
                pass

            # NotebookLM 도메인으로 이동 완료까지 대기
            await page.wait_for_url("**/notebooklm.google.com/**", timeout=60000)
            print("NotebookLM 로그인 성공!", flush=True)

        except PlaywrightTimeoutError as e:
            current_url = page.url
            print(f"타임아웃 오류 발생: {e}", flush=True)
            print(f"현재 URL: {current_url}", flush=True)
            # 스크린샷으로 현재 상태 저장 (디버깅용)
            await page.screenshot(path="login_error.png")
            print("오류 스크린샷 저장: login_error.png", flush=True)
            await browser.close()
            sys.exit(1)
        except Exception as e:
            print(f"로그인 중 예외 발생: {e}", flush=True)
            await page.screenshot(path="login_error.png")
            await browser.close()
            sys.exit(1)

        # Step 5: 쿠키(인증 상태) 저장
        await context.storage_state(path=str(STORAGE_PATH))
        print(f"인증 쿠키 저장 완료: {STORAGE_PATH}", flush=True)

        await browser.close()
        print("브라우저 종료. 로그인 자동화 완료.", flush=True)


if __name__ == "__main__":
    asyncio.run(login_to_notebooklm())
