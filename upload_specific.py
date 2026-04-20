import os
import sys

# Windows 환경(cp949)에서 이모지 출력 시 발생하는 UnicodeEncodeError 방지
if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr is not None and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import generate_podcast
import requests
from notebooklm import NotebookLMClient
from notebooklm.types import ArtifactType
import asyncio

async def download_and_upload():
    async with await NotebookLMClient.from_storage(timeout=120) as client:
        notebooks = await client.notebooks.list()
        
        target_notebook = None
        for lb in notebooks:
            if "Daily News Podcast - 2026-03-25 13:22" in lb.title:
                target_notebook = lb
                break
                
        if not target_notebook:
            print("❌ 대상 노트북 'Daily News Podcast - 2026-03-25 13:22'을(를) 찾지 못했습니다.")
            return
            
        print(f"✅ 노트북 발견: {target_notebook.title} (ID: {target_notebook.id})")
        
        artifacts = await client.artifacts.list(target_notebook.id)
        files_to_upload = {}
        
        for art in artifacts:
            # ArtifactType.SLIDE_DECK vs SLIDES
            is_slides = (art.kind == getattr(ArtifactType, 'SLIDE_DECK', '') or art.kind == getattr(ArtifactType, 'SLIDES', ''))

            if art.kind == ArtifactType.AUDIO:
                ext = ".wav"
                key = "audio"
            elif art.kind == ArtifactType.REPORT:
                ext = ".txt"
                key = "report"
            elif is_slides:
                ext = ".txt"
                key = "slides"
            else:
                continue

            filename = f"manual_{art.id}{ext}"
            
            if art.kind == ArtifactType.AUDIO and getattr(art, 'url', None):
                print(f"📥 오디오 다운로드 중: {art.title} ({filename})")
                res = requests.get(art.url)
                if res.status_code == 200:
                    with open(filename, 'wb') as f:
                        f.write(res.content)
                    files_to_upload[key] = filename
            else:
                print(f"📥 텍스트 아티팩트 저장 중: {art.title} ({filename})")
                content = getattr(art, 'content', str(getattr(art, 'metadata', '')))
                if not content and getattr(art, 'url', None):
                    try: content = requests.get(art.url).text
                    except: pass
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_to_upload[key] = filename

        print(f"다운로드 완료된 파일 종류: {list(files_to_upload.keys())}")

        uploaded_links = {}
        for key, local_file in files_to_upload.items():
            if key in ['audio', 'slides']: 
                print(f"🚀 Google Drive 업로드 시작: {local_file}")
                link = generate_podcast.upload_to_drive(local_file)
                if link:
                    uploaded_links[key] = link
                    print(f"🔗 링크 완료: {link}")

        if uploaded_links:
            print("🌐 워드프레스 업데이트 중...")
            generate_podcast.update_wordpress_briefing_page(uploaded_links)
            print("✨ 워드프레스 브리핑 페이지 업데이트 완료!")
        else:
            print("❌ 업로드할 링크가 없어 워드프레스 업데이트를 건너뜁니다.")

if __name__ == "__main__":
    asyncio.run(download_and_upload())
