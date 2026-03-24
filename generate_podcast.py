import os
import time
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import html
from dotenv import load_dotenv
import asyncio
import re

import sys
sys.path.append(r"C:\Users\inhoe\AppData\Roaming\Python\Python313\site-packages")

# NotebookLM
from notebooklm import NotebookLMClient
from notebooklm.types import (
    AudioLength, 
    AudioFormat, 
    ReportFormat, 
    SlideDeckFormat, 
    SlideDeckLength, 
    ArtifactType
)

# Google Drive API
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv()

# ================= CONFIGURATION =================
WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com").rstrip('/')

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# NotebookLM Audio Settings from .env
AUDIO_INSTRUCTIONS = os.getenv("NOTEBOOKLM_AUDIO_INSTRUCTIONS", "전문적인 뉴스 팟캐스트 스타일로 진행해 주세요.")
AUDIO_FORMAT = os.getenv("NOTEBOOKLM_AUDIO_FORMAT", "deep-dive")
AUDIO_LENGTH = os.getenv("NOTEBOOKLM_AUDIO_LENGTH", "default")

def get_today_posts_content():
    """워드프레스에서 오늘 날짜의 최신 포스트 10개를 가져와 제목과 본문(텍스트) 목록을 반환합니다."""
    print("워드프레스에서 오늘 포스팅 가져오는 중...", flush=True)
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    params = {"per_page": 10, "status": "publish"}
    posts_data = []
    
    try:
        res = requests.get(endpoint, params=params, timeout=20)
        if res.status_code == 200:
            posts = res.json()
            
            for post in posts:
                title = html.unescape(post['title']['rendered'])
                content_html = post['content']['rendered']
                soup = BeautifulSoup(content_html, 'html.parser')
                
                # 텍스트만 추출 (스크립트, 스타일 시트 제외)
                for script_or_style in soup(['script', 'style']):
                    script_or_style.decompose()
                
                clean_text = soup.get_text(separator='\n', strip=True)
                posts_data.append({"title": title, "content": clean_text})
                            
            print(f"-> 총 {len(posts_data)}개의 포스트 내용을 성공적으로 추출했습니다.", flush=True)
            return posts_data
    except Exception as e:
        print(f"포스트 데이터 가져오기 실패: {e}", flush=True)
    return []

async def generate_notebooklm_podcast(posts_data):
    """NotebookLM-py를 사용하여 추출된 텍스트를 기반으로 팟캐스트를 생성하고 다운로드합니다."""
    # NotebookLMClient.from_storage()는 인자가 없으면 환경변수 NOTEBOOKLM_AUTH_JSON을 먼저 확인하고, 
    # 없으면 기본 경로(~/.notebooklm/storage_state.json)를 사용합니다.
    async with await NotebookLMClient.from_storage(timeout=120) as client:

        try:
            # 1. 새 노트북 생성
            timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M')
            title = f"Daily News Podcast - {timestamp_str}"
            notebook = await client.notebooks.create(title=title)
            print(f"새 노트북 생성 완료: {notebook.title}", flush=True)
            
            # 2. 소스 문서 추가 (텍스트 기반)
            print(f"소스 텍스트 추가 중 ({len(posts_data)}개)...", flush=True)
            sources = []
            for i, data in enumerate(posts_data):
                try:
                    print(f"[{i+1}/{len(posts_data)}] 소스 추가: {data['title']}", flush=True)
                    source = await client.sources.add_text(notebook.id, data['title'], data['content'])
                    sources.append(source)
                except Exception as err:
                    print(f"소스 추가 실패 ({data['title']}): {err}", flush=True)
            
            if not sources:
                raise Exception("추가된 소스가 하나도 없습니다.")

            # 모든 소스가 인덱싱될 시간을 충분히 확보합니다.
            print("모든 소스 인덱싱 대기 중...", flush=True)
            for source in sources:
                try:
                    await client.sources.wait_until_ready(notebook.id, source.id, timeout=300)
                except Exception as e:
                    print(f"소스 준비 대기 중 오류 (ID: {source.id}): {e}", flush=True)
            
            # 안정적인 생성을 위해 인덱싱 완료 후 30초 추가 대기
            print("인덱싱 후 안정화를 위해 30초간 대기합니다...", flush=True)
            await asyncio.sleep(30)
            
            # 3. 오디오 오버뷰 (팟캐스트) 생성 요청
            print(f"팟캐스트(Audio Overview) 생성 요청 중 (한국어)...", flush=True)
            audio_job = None
            try:
                # 환경변수에서 로드한 설정 사용
                print(f"  -> 프롬프트: {AUDIO_INSTRUCTIONS[:50]}...")
                
                # 문자열 설정을 Enum 타입으로 변환
                final_format = None
                if AUDIO_FORMAT == "deep-dive": final_format = AudioFormat.DEEP_DIVE
                elif AUDIO_FORMAT == "brief": final_format = AudioFormat.BRIEF
                elif AUDIO_FORMAT == "critique": final_format = AudioFormat.CRITIQUE
                elif AUDIO_FORMAT == "debate": final_format = AudioFormat.DEBATE
                
                final_length = None
                if AUDIO_LENGTH == "short": final_length = AudioLength.SHORT
                elif AUDIO_LENGTH == "default": final_length = AudioLength.DEFAULT
                elif AUDIO_LENGTH == "long": final_length = AudioLength.LONG

                print(f"  -> 포맷: {final_format}, 길이: {final_length}")
                
                audio_job = await client.artifacts.generate_audio(
                    notebook.id,
                    language="ko",
                    instructions=AUDIO_INSTRUCTIONS,
                    audio_format=final_format,
                    audio_length=final_length
                )
                print(f"오디오 생성 작업 시작됨 (Task ID: {audio_job.task_id})", flush=True)
            except Exception as e:
                print(f"오디오 생성 요청 실패: {e}", flush=True)

            # 4. 브리핑 문서(Report) 생성 요청
            print("브리핑 문서(Report) 생성 요청 중 (한국어)...", flush=True)
            report_job = None
            try:
                report_job = await client.artifacts.generate_report(
                    notebook.id, 
                    report_format=ReportFormat.BRIEFING_DOC,
                    language="ko"
                )
                print(f"브리핑 문서 생성 작업 시작됨 (Task ID: {report_job.task_id})", flush=True)
            except Exception as report_err:
                print(f"브리핑 문서 생성 요청 실패: {report_err}", flush=True)

            # 5. 슬라이드 덱(Slide Deck) 생성 요청
            print("슬라이드 덱(Slide Deck) 생성 요청 중 (한국어)...", flush=True)
            slides_job = None
            try:
                slides_job = await client.artifacts.generate_slide_deck(
                    notebook.id,
                    language="ko"
                )
                print(f"슬라이드 덱 생성 작업 시작됨 (Task ID: {slides_job.task_id})", flush=True)
            except Exception as slides_err:
                print(f"슬라이드 덱 생성 요청 실패: {slides_err}", flush=True)

            # 폴링 및 다운로드 (최대 40분 대기)
            start_time = asyncio.get_event_loop().time()
            timeout = 2400 
            timestamp_file = datetime.now().strftime('%Y%m%d_%H%M')
            podcast_filename = f"podcast_{timestamp_file}.wav"
            report_filename = f"report_{timestamp_file}.txt"
            slides_filename = f"slides_{timestamp_file}.txt"
            files_downloaded = []

            print("아티팩트 생성 완료 대기 및 다운로드 시도...", flush=True)
            
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    print("대기 시간 초과로 종료합니다.", flush=True)
                    break
                
                try:
                    all_artifacts = await client.artifacts.list(notebook.id)
                    
                    for art in all_artifacts:
                        # 오디오 다운로드
                        if art.kind == ArtifactType.AUDIO and art.url and podcast_filename not in files_downloaded:
                            print(f"오디오 발견! 다운로드 중...", flush=True)
                            res = requests.get(art.url)
                            if res.status_code == 200:
                                with open(podcast_filename, 'wb') as f:
                                    f.write(res.content)
                                files_downloaded.append(podcast_filename)
                        
                        # 리포트/브리핑 문서 저장
                        if art.kind == ArtifactType.REPORT and report_filename not in files_downloaded:
                            content = getattr(art, 'content', None)
                            if not content and art.url:
                                try: content = requests.get(art.url).text
                                except: pass
                            
                            if content:
                                print(f"리포트({art.title}) 발견! 저장 중...", flush=True)
                                with open(report_filename, 'w', encoding='utf-8') as f:
                                    f.write(content)
                                files_downloaded.append(report_filename)

                        # 슬라이드 덱 저장
                        if art.kind == ArtifactType.SLIDE_DECK and slides_filename not in files_downloaded:
                            print(f"슬라이드 덱 발견! 저장 중...", flush=True)
                            content = getattr(art, 'content', str(getattr(art, 'metadata', '')))
                            with open(slides_filename, 'w', encoding='utf-8') as f:
                                f.write(content)
                            files_downloaded.append(slides_filename)

                    # 상태 확인 (이미 다운로드된 파일들 기준)
                    audio_done = (podcast_filename in files_downloaded) or (audio_job is None)
                    report_done = (report_filename in files_downloaded) or (report_job is None)
                    slides_done = (slides_filename in files_downloaded) or (slides_job is None)

                    if audio_done and report_done and slides_done:
                        if files_downloaded:
                            print(f"아티팩트 다운로드 완료: {files_downloaded}", flush=True)
                            break

                    # 중간에 오디오가 여전히 실패 상태면 1회 재시도 (인덱싱 후 시간이 더 필요할 수 있음)
                    if not audio_done and audio_job is None and elapsed > 300:
                         print("오디오 생성을 재시도합니다 (한국어)...", flush=True)
                         try:
                             audio_job = await client.artifacts.generate_audio(
                                 notebook.id,
                                 language="ko",
                                 instructions="한국어로 대화해 주세요."
                             )
                             if audio_job:
                                 print(f"오디오 재시도 작업 시작됨 (Task ID: {audio_job.task_id})", flush=True)
                         except:
                             pass

                    print(f"[{int(elapsed)}초 경과] 대기 중... (Audio: {'O' if podcast_filename in files_downloaded else 'X'}, Report: {'O' if report_filename in files_downloaded else 'X'}, Slides: {'O' if slides_filename in files_downloaded else 'X'})", flush=True)
                    await asyncio.sleep(60)
                    
                except Exception as poll_err:
                    print(f"상태 확인 중 오류 (무시하고 계속): {poll_err}", flush=True)
                    await asyncio.sleep(30)

            return files_downloaded
                
        except Exception as e:
             print(f"NotebookLM 처리 중 오류 발생: {e}")
        finally:
             pass
             
    return None


def authenticate_drive():
    """Google Drive API 인증을 수행하고 인증 객체를 반환합니다."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def get_or_create_drive_folder(service, folder_name, parent_id=None):
    """Google Drive에서 폴더를 찾거나 없으면 생성하여 폴더 ID를 반환합니다."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    else:
        # 최상단 폴더 검사 (부모가 없어도 검색되도록)
        pass
        
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    # 여러 개가 검색되면 부모 조건 추가 확인
    if parent_id:
        items = [i for i in items if parent_id in service.files().get(fileId=i['id'], fields='parents').execute().get('parents', [])]
    else:
        # root에 있는 항목을 정확하게 가져오려면 이 조건 필요
        items = [i for i in items if 'root' in (service.files().get(fileId=i['id'], fields='parents').execute().get('parents', ['root']))]
        
    # 위 방식은 다소 비효율적이므로 단순화된 쿼리 재구성
    query_exact = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query_exact += f" and '{parent_id}' in parents"
    else:
        query_exact += " and 'root' in parents"
        
    results_exact = service.files().list(q=query_exact, spaces='drive', fields='files(id, name)').execute()
    items_exact = results_exact.get('files', [])

    if items_exact:
        return items_exact[0]['id']
    else:
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            folder_metadata['parents'] = [parent_id]
            
        file = service.files().create(body=folder_metadata, fields='id').execute()
        return file.get('id')

def upload_to_drive(file_path):
    """다운로드한 파일을 Google Drive의 날짜별 폴더에 업로드합니다."""
    print(f"Google Drive 업로드 시작: {os.path.basename(file_path)}")
    try:
        creds = authenticate_drive()
        service = build('drive', 'v3', credentials=creds)

        # 1. 메인 폴더 (NewsBot_Artifacts) ID 확인 혹은 생성
        main_folder_name = "NewsBot_Artifacts"
        main_folder_id = get_or_create_drive_folder(service, main_folder_name)
        
        # 2. 오늘 날짜 하위 폴더 ID 확인 혹은 생성
        today_str = datetime.now().strftime('%Y-%m-%d')
        daily_folder_id = get_or_create_drive_folder(service, today_str, parent_id=main_folder_id)

        # 3. 하위 폴더에 파일 업로드
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [daily_folder_id]
        }
        mimetype = 'audio/wav' if file_path.endswith('.wav') else 'text/plain'
        media = MediaFileUpload(file_path, mimetype=mimetype)
        
        file = service.files().create(body=file_metadata, media_body=media,
                                      fields='id, webViewLink').execute()
        print(f"파일 업로드 성공! 폴더: {today_str}, 파일 ID: {file.get('id')}")
        return file.get('webViewLink')

    except Exception as error:
        print(f"Google Drive API 에러 발생: {error}")
        return None

async def main():
    # 1. 워드프레스에서 오늘자 뉴스 내용 추출 (본문 텍스트 포함)
    posts_data = get_today_posts_content()
    if not posts_data:
        print("추출된 뉴스 데이터가 없습니다. 종료합니다.")
        return
        
    print(f"총 수집된 포스트 개수: {len(posts_data)}")
    
    # 2. NotebookLM을 통해 팟캐스트 및 슬라이드 초안 생성
    generated_files = await generate_notebooklm_podcast(posts_data)
    
    if generated_files:
        print(f"\n총 {len(generated_files)}개의 파일이 생성되었습니다.")
        for fpath in generated_files:
            if os.path.exists(fpath):
                # 3. Google Drive 업로드
                drive_link = upload_to_drive(fpath)
                if drive_link:
                    print(f"-> {os.path.basename(fpath)} 업로드 완료: {drive_link}")
        
        print("\n모든 작업이 성공적으로 완료되었습니다!")
    else:
        print("파일 생성에 실패했습니다.")

if __name__ == '__main__':
    asyncio.run(main())
