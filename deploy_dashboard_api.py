"""
deploy_dashboard_api.py
========================
WP REST API만으로 대시보드를 배포합니다.
(FTP 없이 - CSS/JS를 인라인 포함)

방법: CSS + JS를 <style>/<script> 태그로 페이지 콘텐츠에 직접 포함.
→ Head & Footer Code 플러그인 불필요, 외부 파일 서버 불필요.
→ 데이터 업데이트 시 이 스크립트만 재실행하면 됩니다.
"""

import base64
import requests
import json
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────────────
WP_URL   = 'https://ajken.mycafe24.com'
WP_USER  = 'inhoe.an@gmail.com'
WP_PASS  = 'ISPe NJZf FCSb Qwh3 MPf2 ZPds'
PAGE_ID  = 2184   # 시장현황 페이지

SCRIPT_DIR    = Path(__file__).parent
DASHBOARD_DIR = SCRIPT_DIR / 'dashboard'

API_HEADERS = {
    'Authorization': 'Basic ' + base64.b64encode(f'{WP_USER}:{WP_PASS}'.encode()).decode(),
    'Content-Type': 'application/json',
}


def read_file(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def build_full_page_content():
    """CSS + 데이터 JS + 렌더 JS + HTML 골격을 하나의 페이지 콘텐츠로 조합"""

    css      = read_file(DASHBOARD_DIR / 'dashboard.css')
    data_js  = read_file(DASHBOARD_DIR / 'dashboard-data.js')
    render_js = read_file(DASHBOARD_DIR / 'dashboard-render.js')
    html_body = read_file(DASHBOARD_DIR / 'page-content.html')

    # Chart.js + Google Fonts는 CDN에서 로드
    # 나머지 CSS/JS는 인라인으로 포함
    full_content = f"""<!-- 정보보호 통계 대시보드 시작 -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>

<style>
{css}
</style>

{html_body}

<script>
{data_js}
</script>
<script>
{render_js}
</script>
<!-- 정보보호 통계 대시보드 끝 -->"""

    return full_content


def update_page(content):
    """WordPress 페이지 콘텐츠 업데이트"""
    print(f'\n[1] WordPress 페이지 업데이트 (ID={PAGE_ID})...')
    r = requests.post(
        f'{WP_URL}/wp-json/wp/v2/pages/{PAGE_ID}',
        headers=API_HEADERS,
        json={
            'content': content,
            'status': 'publish',
        },
    )
    if r.status_code == 200:
        data = r.json()
        print(f'  OK 페이지 업데이트 성공')
        print(f'  URL: {data.get("link", "")}')
        return True
    else:
        print(f'  FAIL 업데이트 실패 ({r.status_code}): {r.text[:400]}')
        return False


def activate_plugin(plugin_slug):
    """플러그인 활성화 (Head & Footer Code)"""
    print(f'\n[2] 플러그인 활성화: {plugin_slug}')
    r = requests.put(
        f'{WP_URL}/wp-json/wp/v2/plugins/{plugin_slug}',
        headers=API_HEADERS,
        json={'status': 'active'},
    )
    if r.status_code == 200:
        print(f'  OK 활성화 성공')
        return True
    else:
        print(f'  SKIP ({r.status_code}) - 이미 활성화 상태이거나 권한 없음')
        return False


def check_page():
    """배포된 페이지 간단 확인"""
    print(f'\n[3] 배포 확인...')
    r = requests.get(f'{WP_URL}/wp-json/wp/v2/pages/{PAGE_ID}?_fields=id,title,link,status')
    if r.status_code == 200:
        d = r.json()
        print(f'  페이지: {d["title"]["rendered"]}')
        print(f'  상태:   {d["status"]}')
        print(f'  URL:    {d["link"]}')
    else:
        print(f'  확인 실패: {r.status_code}')


def main():
    print('=' * 60)
    print('  정보보호 통계 대시보드 -> WordPress 배포 (API 방식)')
    print('=' * 60)

    # HTML + CSS + JS 조합
    print('\n[0] 파일 조합 중...')
    content = build_full_page_content()
    print(f'  OK 총 {len(content):,} 문자')

    # 페이지 업데이트
    ok = update_page(content)

    if ok:
        check_page()
        print('\n' + '=' * 60)
        print('  배포 완료!')
        print(f'  확인: {WP_URL}/%EC%8B%9C%EC%9E%A5%ED%98%84%ED%99%A9/')
        print('\n  [데이터 업데이트 방법]')
        print('  1. dashboard/dashboard-data.js 파일의 수치를 수정')
        print('  2. python deploy_dashboard_api.py 재실행')
        print('=' * 60)
    else:
        print('\n  배포 실패. 오류를 확인하세요.')


if __name__ == '__main__':
    main()
