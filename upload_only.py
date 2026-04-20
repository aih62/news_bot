import os
import generate_podcast

from notebooklm import NotebookLMClient
from notebooklm.types import ArtifactType
import asyncio

async def download_and_upload():
    client = NotebookLMClient()
    
    # 1. NotebookLM에서 가장 최근 노트북을 찾습니다.
    notebooks = await client.notebooks.list()
    if not notebooks:
        print("❌ 실행된 노트북을 찾을 수 없습니다.")
        return
    
    # 가장 최근 노트북 선택 (Daily News Podcast로 시작하는)
    target_notebook = None
    for lb in notebooks:
        if "Daily News Podcast" in lb.title:
            target_notebook = lb
            break
            
    if not target_notebook:
        print("❌ 대상 노트북을 찾지 못했습니다.")
        return
        
    print(f"✅ 노트북 발견: {target_notebook.title} (ID: {target_notebook.id})")
    
    # 2. 아티팩트 목록 가져오기 및 다운로드
    artifacts = await client.artifacts.list(target_notebook.id)
    files_to_upload = {}
    
    for art in artifacts:
        if art.url:
            ext = ".wav" if art.kind == ArtifactType.AUDIO else ".txt"
            filename = f"manual_{art.id}{ext}"
            
            if not os.path.exists(filename):
                print(f"📥 다운로드 중: {art.title} ({filename})")
                await client.artifacts.download(art.id, filename)
            
            if art.kind == ArtifactType.AUDIO:
                files_to_upload['audio'] = filename
            elif art.kind == ArtifactType.REPORT:
                files_to_upload['report'] = filename
            elif art.kind == ArtifactType.SLIDES:
                files_to_upload['slides'] = filename

    # 3. Google Drive 업로드
    uploaded_links = {}
    for key, local_file in files_to_upload.items():
        print(f"🚀 Google Drive 업로드 시작: {local_file}")
        link = generate_podcast.upload_to_drive(local_file)
        if link:
            uploaded_links[key] = link
            print(f"🔗 링크 완료: {link}")

    # 4. 워드프레스 업데이트
    if uploaded_links:
        print("🌐 워드프레스 업데이트 중...")
        generate_podcast.update_wordpress_briefing_page(uploaded_links)
        print("✨ 정식 브리핑 페이지 업데이트 완료!")
    else:
        print("❌ 업로드할 링크가 없습니다.")

if __name__ == "__main__":
    asyncio.run(download_and_upload())
