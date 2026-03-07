import os
import time
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import html
from dotenv import load_dotenv
import asyncio

import sys
sys.path.append(r"C:\Users\inhoe\AppData\Roaming\Python\Python313\site-packages")

# NotebookLM
from notebooklm import NotebookLMClient

# Google Drive API
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from notebooklm.rpc.types import AudioLength

load_dotenv()

# ================= CONFIGURATION =================
WP_SITE_URL = os.getenv("WP_SITE_URL", "https://ajken.mycafe24.com").rstrip('/')

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_today_posts_text():
    """워드프레스에서 오늘 날짜의 최신 포스트 10개를 가져와 하나의 텍스트로 결합합니다."""
    print("워드프레스에서 오늘 포스팅 가져오는 중...")
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    params = {"per_page": 10, "status": "publish"}
    combined_text = ""
    
    try:
        res = requests.get(endpoint, params=params, timeout=20)
        if res.status_code == 200:
            posts = res.json()
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            count = 0
            for post in posts:
                # 워드프레스 날짜 형식: "2026-03-06T07:00:00"
                if post['date'].startswith(today_str):
                    title = html.unescape(post['title']['rendered'])
                    content_html = post['content']['rendered']
                    soup = BeautifulSoup(content_html, 'html.parser')
                    text = soup.get_text(separator='\n', strip=True)
                    
                    combined_text += f"제목: {title}\n"
                    combined_text += f"내용:\n{text}\n\n"
                    combined_text += "-" * 50 + "\n\n"
                    count += 1
            print(f"-> 총 {count}개의 포스트를 성공적으로 추출했습니다.")
            return combined_text
    except Exception as e:
        print(f"포스트 가져오기 실패: {e}")
    return combined_text

async def generate_notebooklm_podcast(source_text):
    """NotebookLM-py를 사용하여 텍스트 소스를 기반으로 팟캐스트를 생성하고 다운로드합니다."""
    print("NotebookLM 작업 시작...")
    # NOTE: 먼저 터미널에서 `notebooklm login` 을 실행하여 로그인 세션을 만들어야 합니다.
    async with await NotebookLMClient.from_storage() as client:
    
        try:
            # 1. 새 노트북 생성
            title = f"Daily News Podcast - {datetime.now().strftime('%Y-%m-%d')}"
            notebook = await client.notebooks.create(title=title)
            print(f"새 노트북 생성 완료: {notebook.title}")
            
            # 2. 소스 문서 추가 (텍스트 직접 추가 방식이 클라우드 환경에서 더 안정적일 수 있습니다)
            print("소스 문서 추가 중...")
            source = await client.sources.add_text(notebook.id, f"News_{datetime.now().strftime('%Y%m%d')}", source_text)
            
            # 소스가 인덱싱될 시간을 충분히 확보합니다.
            print("소스 인덱싱 대기 중 (최대 5분)...")
            await client.sources.wait_until_ready(notebook.id, source.id, timeout=300)
            
            # 인덱싱 완료 후 안정성을 위해 추가 대기
            await asyncio.sleep(10)
            
            # 3. 오디오 오버뷰 (팟캐스트) 생성 요청 (실패 시 최대 2회 재시도)
            audio_job = None
            for attempt in range(2):
                try:
                    print(f"팟캐스트(Audio Overview) 생성 요청 중 (시도 {attempt + 1}/2)...")
                    prompt_instructions = (
                        "제공된 10개의 최신 글로벌 보안 뉴스를 바탕으로 단일 팟캐스트 에피소드를 만들어 주세요. "
                        "뉴스 10개를 각각 따로 읽는 것이 아니라, 전체적인 동향과 가장 중요한 이슈들을 하나로 엮어서 "
                        "한국어로 자연스럽게 대화하며 소개해야 합니다. "
                        "전체적인 분량은 20분을 넘지 않도록 간결하게 구성해 주세요."
                    )
                    audio_job = await client.artifacts.generate_audio(
                        notebook.id,
                        language="ko",
                        audio_length=AudioLength.SHORT,
                        instructions=prompt_instructions
                    )
                    break
                except Exception as e:
                    print(f"생성 요청 실패: {e}")
                    if attempt == 0:
                        print("10초 후 다시 시도합니다...")
                        await asyncio.sleep(10)
                    else:
                        raise e

            print("생성 완료를 기다립니다 (약 3~10분 소요됩니다)...")
            # 완료될 때까지 대기
            audio_result = await client.artifacts.wait_for_completion(notebook.id, audio_job.task_id, timeout=900)
            
            # 다운로드 경로
            output_filename = f"podcast_{datetime.now().strftime('%Y%m%d')}.wav"
            
            if audio_result.is_complete and audio_result.url:
                 print(f"팟캐스트 다운로드 중: {output_filename}")
                 res = requests.get(audio_result.url)
                 with open(output_filename, 'wb') as f:
                     f.write(res.content)
                 print("다운로드 완료!")
                 return output_filename
            else:
                if audio_result.is_failed:
                    print(f"오디오 생성 실패: {audio_result.error}")
                else:
                    print("오디오 URL을 찾을 수 없거나 아직 생성되지 않았습니다.")
                return None
                
        except Exception as e:
             print(f"NotebookLM 처리 중 오류 발생: {e}")
        finally:
             if os.path.exists("temp_source.txt"):
                 os.remove("temp_source.txt")
             
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

def upload_to_drive(file_path):
    """다운로드한 팟캐스트 파일을 Google Drive에 업로드합니다."""
    print("Google Drive 업로드 시작...")
    try:
        creds = authenticate_drive()
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {'name': os.path.basename(file_path)}
        media = MediaFileUpload(file_path, mimetype='audio/wav')
        
        file = service.files().create(body=file_metadata, media_body=media,
                                      fields='id, webViewLink').execute()
        print(f"파일 업로드 성공! 파일 ID: {file.get('id')}")
        print(f"웹 보기 링크: {file.get('webViewLink')}")
        return file.get('webViewLink')

    except Exception as error:
        print(f"Google Drive API 에러 발생: {error}")
        return None

async def main():
    # 1. 워드프레스에서 오늘자 뉴스 텍스트 추출
    source_text = get_today_posts_text()
    if not source_text:
        print("추출된 뉴스 데이터가 없습니다. 종료합니다.")
        return
        
    print(f"총 텍스트 길이: {len(source_text)} 자")
    
    # 2. NotebookLM을 통해 팟캐스트 생성
    podcast_file = await generate_notebooklm_podcast(source_text)
    
    if podcast_file and os.path.exists(podcast_file):
        # 3. Google Drive 업로드
        drive_link = upload_to_drive(podcast_file)
        if drive_link:
            print(f"성공! 구글 드라이브 링크: {drive_link}")
        print("모든 작업이 완료되었습니다!")
    else:
        print("팟캐스트 파일 생성에 실패했습니다.")

if __name__ == '__main__':
    asyncio.run(main())
