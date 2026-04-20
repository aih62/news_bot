import asyncio
import os
import pathlib
import sys

# Windows 터미널(cp949) 환경 출력 에러(UnicodeEncodeError) 방지
if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr is not None and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

# 기존 generate_podcast.py 임포트 (동일한 폴더 기준)
import generate_podcast

STORAGE_DIR = pathlib.Path.home() / ".notebooklm"
STORAGE_PATH = STORAGE_DIR / "storage_state.json"
PROFILE_DIR = pathlib.Path.home() / ".chrome_podcast_profile"

async def ensure_fresh_session():
    """
    Persistent Chrome 프로필을 열어 구글 로그인을 유지하고, 
    가장 최신의 세션 쿠키를 storage_state.json으로 내보냅니다.
    이후 generate_podcast.py의 NotebookLMClient가 이 JSON을 읽어서 오디오를 생성합니다.
    """
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("🤖 로컬 브라우저 프로필을 시작합니다.")
    print("처음 실행하시거나 로그아웃된 경우, 크롬 창에서 직접 로그인을 해주세요.")
    print("="*60)
    
    async with async_playwright() as p:
        # Persistent Context로 실행 (로그인 정보, 캐시 등을 하드에 저장)
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,  # 직접 로그인이 가능하도록 화면에 표시
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
        
        print("🌍 NotebookLM으로 이동 중...")
        await page.goto("https://notebooklm.google.com/", wait_until="domcontentloaded")
        
        print("⏳ 로딩 대기 중... (만약 로그인 화면이 뜨면 직접 계정으로 로그인해 주세요.)")
        print("   로그인을 진행할 수 있도록 3분간 대기합니다...")
        
        try:
            # NotebookLM 메인 대시보드 구조가 렌더링될 때까지 대기 (또는 3분 한도)
            # 로그인이 이미 되어 있으면 바로 패스됨.
            await page.wait_for_url("**/notebooklm.google.com/**", timeout=180000)
            # 혹시 모를 내부 로그인 팝업 등을 위해 약간 더 대기
            await asyncio.sleep(5) 
            print("✅ NotebookLM 정상 접속 확인 완료.")
        except Exception as e:
            print("\n⚠️ 시간이 초과되었거나 다른 화면에 멈춰 있습니다.")
            print("로그인을 완전히 못 마쳤더라도 임시로 진행합니다.")
            
        print(f"💾 최신 세션(쿠키) 정보를 추출하여 저장합니다: {STORAGE_PATH}")
        await browser_context.storage_state(path=str(STORAGE_PATH))
        
        await browser_context.close()
        print("브라우저 종료 완료. 쿠키 갱신 성공!\n" + "="*60 + "\n")

async def main():
    # 1. 봇 전용 크롬 프로필을 띄워 진짜 사람처럼 쿠키를 갱신합니다.
    await ensure_fresh_session()
    
    # 2. 갱신된 쿠키를 이용해 원래 팟캐스트 코드를 실행합니다.
    print("🚀 기존 팟캐스트 자동화 코드를 실행합니다...")
    await generate_podcast.main()

if __name__ == "__main__":
    asyncio.run(main())
