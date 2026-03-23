import asyncio
import os
import pathlib
import json
from playwright.async_api import async_playwright

STORAGE_DIR = pathlib.Path.home() / ".notebooklm"
STORAGE_PATH = STORAGE_DIR / "storage_state.json"

async def manual_login():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*70)
    print("구글의 강력한 봇 탐지로 인해 직접 브라우저를 실행하여 로그인해야 합니다.")
    print("아래 절차를 천천히 따라해 주세요:")
    print("1. 현재 열려 있는 모든 Chrome 창을 완전히 종료합니다.")
    print("   (작업 표시줄 우측 하단의 Chrome 아이콘 우클릭 -> '종료' 또는 완전히 닫기)")
    print("2. 키보드에서 'Windows 로고 키 + R'을 눌러 '실행' 창을 엽니다.")
    print("3. 열린 창에 아래 명령어를 복사하여 붙여넣고 [확인]을 누릅니다:")
    print(r'   chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chrome-debug"')
    print("4. 새로 열린 빈 Chrome 창 주소창에 아래 주소를 입력하고 이동합니다:")
    print("   https://notebooklm.google.com/")
    print("5. 본인의 구글 계정으로 정상적으로 로그인합니다.")
    print("6. 로그인이 완료되어 NotebookLM 메인 화면이 보이면 이 터미널로 돌아옵니다.")
    print("="*70 + "\n")
    
    input("위 1~6번 단계를 모두 완료했다면 [Enter]를 눌러주세요...")
    
    async with async_playwright() as p:
        try:
            print("Chrome과 연결 시도 중...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            
            # Save state
            await context.storage_state(path=str(STORAGE_PATH))
            print(f"\n✅ 인증 정보가 파일로 성공적으로 추출 및 저장되었습니다: {STORAGE_PATH}")
            
            # Output as JSON string for GitHub Secrets
            with open(STORAGE_PATH, 'r', encoding='utf-8') as f:
                storage_data = json.load(f)
                storage_json_str = json.dumps(storage_data)
                print("\n" + "="*70)
                print("GitHub Secrets에 등록할 'NOTEBOOKLM_STORAGE_STATE' 내용입니다:")
                print("-" * 70)
                print(storage_json_str)
                print("-" * 70)
                print(f"위의 '{{\"cookies\"'로 시작하는 한 줄 문자열 전체를 복사해서")
                print("GitHub Secrets ('NOTEBOOKLM_STORAGE_STATE')에 붙여넣으세요.")
                print("="*70 + "\n")
            
            await browser.close()
            print("세션 추출이 완료되었습니다. 방금 열었던 Chrome 창을 닫아도 됩니다.")
        except Exception as e:
            print(f"\n❌ 오류가 발생했습니다: {e}")
            print("디버깅 모드로 실행된 Chrome 브라우저와 연결할 수 없습니다.")
            print("위의 1~6번 단계를 빠짐없이 진행했는지 다시 한번 확인해 주세요.")

if __name__ == "__main__":
    asyncio.run(manual_login())
