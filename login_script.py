import asyncio
from notebooklm import NotebookLMClient

async def main():
    print("NotebookLM 로그인을 시작합니다. 곧 뜨는 브라우저 창에서 로그인해주세요.")
    # 로그인을 위해 NotebookLMClient 객체 생성 및 login 메서드 호출
    async with await NotebookLMClient.login() as client:
        print("로그인이 성공적으로 완료되었습니다(쿠키 저장됨)!")

if __name__ == "__main__":
    asyncio.run(main())

