# News Bot 프로젝트 설정 및 대화 기록 (2026-03-06)

## 1. 개요
본 문서는 워드프레스 자동 뉴스 포스팅 시스템의 실행 시간 변경 및 카카오톡 알림 서비스 구축 과정을 기록한 문서입니다.

## 2. 주요 변경 사항
### 2.1 워드프레스 포스팅 스케줄 변경
- **기존:** 매일 오전 8:00 (KST)
- **변경:** 매일 오전 7:00 (KST)
- **수정 파일:** `.github/workflows/daily_post.yml` (cron: `0 22 * * *`)

### 2.2 카카오톡 알림 시스템 구축
- **기능:** 매일 오전 8:40에 당일 포스팅된 뉴스 10개를 요약하여 카카오톡 '나에게 보내기'로 전송.
- **신규 파일:** 
  - `kakao_summary.py`: 포스트 수집, 메시지 가공 및 카카오 API 전송 로직.
  - `.github/workflows/kakao_notify.yml`: 오전 8:40 자동 실행 워크플로우.
  - `requirements.txt`: `beautifulsoup4` 라이브러리 추가.

## 3. 카카오톡 API 설정 가이드
1. **카카오 개발자 센터(https://developers.kakao.com/)** 접속.
2. **애플리케이션 생성:** REST API 키 복사.
3. **플랫폼 등록:** [앱 키] 하위의 [Redirect URI]에 `https://localhost` 등록.
4. **카카오 로그인 활성화:** [제품 설정] > [카카오 로그인] > 사용 설정 ON.
5. **동의 항목 설정:** [동의항목] > '카카오톡 메시지 전송(Talk Message)'를 '이용 중 동의'로 설정.

## 4. GitHub Secrets 등록 정보
GitHub 저장소의 **Settings > Secrets and variables > Actions**에 다음 항목을 반드시 등록해야 합니다.

### ① KAKAO_REST_API_KEY
- **Value:** `bc44d4bf7a10ac566503189f9326ef5e`

### ② KAKAO_TOKEN_JSON
- **Value:**
```json
{
  "access_token": "4UU5EkSUbDeTEcg_-mUJd7bATyJfYihpAAAAAQoXIiAAAAGcwTTa586SpOckXrb0",
  "refresh_token": "QhqmDfkzvjE8CFYubDHFwsRirPRvKm1IAAAAAgoXIiAAAAGcwTTa4M6SpOckXrb0"
}
```

### ③ WP_SITE_URL
- **Value:** `https://ajken.mycafe24.com`

## 5. 작업 파일 목록
- `auto_wp_news.py`: 워드프레스 포스팅 메인 스크립트.
- `kakao_summary.py`: 카카오톡 전송 스크립트 (신규).
- `requirements.txt`: 라이브러리 목록.
- `.github/workflows/daily_post.yml`: 포스팅 자동화 (수정).
- `.github/workflows/kakao_notify.yml`: 카카오 알림 자동화 (신규).

---
*본 파일은 Gemini CLI에 의해 자동 생성되었습니다.*
