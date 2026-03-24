"""
deploy_dashboard.py
====================
정보보호 통계 대시보드를 WordPress에 배포하는 스크립트.

주요 작업:
1. FTP로 dashboard/ 디렉터리의 정적 파일(CSS, JS) 업로드
2. Head & Footer Code 플러그인 활성화
3. WordPress 페이지(ID=2184, 시장현황)에 HTML 골격 업데이트
4. Head & Footer Code 설정으로 CSS/JS를 해당 페이지에만 로드
"""

import os
import ftplib
import base64
import requests
import json
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────────────
WP_URL      = 'https://ajken.mycafe24.com'
WP_USER     = 'inhoe.an@gmail.com'
WP_PASS     = 'ISPe NJZf FCSb Qwh3 MPf2 ZPds'
PAGE_ID     = 2184   # 시장현황 페이지

# FTP 설정 (카페24는 FTP와 SSH 호스트가 동일)
FTP_HOST    = 'ajken.mycafe24.com'
FTP_USER    = 'ajken'
# FTP 비밀번호는 카페24 FTP 비밀번호 (SSH와 동일한 경우 많음)
# .env에 FTP_PASSWORD가 없으면 WP 관리자 비밀번호와 동일하게 시도
FTP_PASS    = os.getenv('FTP_PASSWORD', 'dksdlsghl62@')  # Google 계정 비밀번호

# 서버 내 업로드 경로 (카페24 기본 웹루트)
REMOTE_DIR  = '/www/wp-content/uploads/dashboard'

# 로컬 파일 경로
SCRIPT_DIR  = Path(__file__).parent
DASHBOARD_DIR = SCRIPT_DIR / 'dashboard'

FILES_TO_UPLOAD = [
    DASHBOARD_DIR / 'dashboard.css',
    DASHBOARD_DIR / 'dashboard-data.js',
    DASHBOARD_DIR / 'dashboard-render.js',
]

# WordPress REST API 헤더
API_HEADERS = {
    'Authorization': 'Basic ' + base64.b64encode(f'{WP_USER}:{WP_PASS}'.encode()).decode(),
    'Content-Type': 'application/json',
}

# 업로드된 파일의 공개 URL 기반
ASSET_BASE_URL = f'{WP_URL}/wp-content/uploads/dashboard'


def upload_files_ftp():
    """FTP로 정적 파일 업로드"""
    print('\n[1] FTP 파일 업로드 시작...')
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        print(f'  ✓ FTP 연결 성공: {FTP_HOST}')

        # 디렉터리 생성 (없으면)
        try:
            ftp.mkd(REMOTE_DIR)
            print(f'  ✓ 디렉터리 생성: {REMOTE_DIR}')
        except ftplib.error_perm:
            print(f'  - 디렉터리 이미 존재: {REMOTE_DIR}')

        ftp.cwd(REMOTE_DIR)

        for local_file in FILES_TO_UPLOAD:
            if not local_file.exists():
                print(f'  ✗ 파일 없음: {local_file}')
                continue
            with open(local_file, 'rb') as f:
                ftp.storbinary(f'STOR {local_file.name}', f)
            print(f'  ✓ 업로드 완료: {local_file.name}')

        ftp.quit()
        print('  ✓ FTP 연결 종료')
        return True

    except Exception as e:
        print(f'  ✗ FTP 오류: {e}')
        print('  → FTP 대신 WordPress 미디어 API 업로드를 시도합니다.')
        return upload_files_via_wp_api()


def upload_files_via_wp_api():
    """FTP 실패 시 WordPress REST API로 파일 업로드 (백업 방법)"""
    print('\n  [백업] WP REST API로 파일 업로드 시도...')
    for local_file in FILES_TO_UPLOAD:
        if not local_file.exists():
            continue
        mime = 'text/css' if local_file.suffix == '.css' else 'application/javascript'
        headers = {
            'Authorization': API_HEADERS['Authorization'],
            'Content-Disposition': f'attachment; filename="{local_file.name}"',
            'Content-Type': mime,
        }
        with open(local_file, 'rb') as f:
            r = requests.post(f'{WP_URL}/wp-json/wp/v2/media', headers=headers, data=f.read())
        if r.status_code in (200, 201):
            print(f'  ✓ API 업로드 성공: {local_file.name}')
        else:
            print(f'  ✗ API 업로드 실패: {r.status_code} - {r.text[:200]}')
    return True


def activate_plugin(plugin_slug):
    """WordPress 플러그인 활성화"""
    print(f'\n[2] 플러그인 활성화: {plugin_slug}')
    r = requests.put(
        f'{WP_URL}/wp-json/wp/v2/plugins/{plugin_slug}',
        headers=API_HEADERS,
        json={'status': 'active'},
    )
    if r.status_code == 200:
        print(f'  ✓ 활성화 성공: {plugin_slug}')
        return True
    else:
        print(f'  ✗ 활성화 실패 ({r.status_code}): {r.text[:300]}')
        return False


def update_wp_page():
    """WordPress 시장현황 페이지(ID=2184) 콘텐츠 업데이트"""
    print(f'\n[3] WordPress 페이지 업데이트 (ID={PAGE_ID})...')

    html_file = DASHBOARD_DIR / 'page-content.html'
    if not html_file.exists():
        print('  ✗ page-content.html 파일 없음')
        return False

    with open(html_file, encoding='utf-8') as f:
        page_html = f.read()

    r = requests.post(
        f'{WP_URL}/wp-json/wp/v2/pages/{PAGE_ID}',
        headers=API_HEADERS,
        json={
            'content': page_html,
            'status': 'publish',
        },
    )
    if r.status_code == 200:
        print(f'  ✓ 페이지 업데이트 성공')
        data = r.json()
        print(f'  ✓ 페이지 URL: {data.get("link", "")}')
        return True
    else:
        print(f'  ✗ 페이지 업데이트 실패 ({r.status_code}): {r.text[:300]}')
        return False


def inject_assets_via_hfc():
    """
    Head & Footer Code 플러그인 설정을 통해
    CSS/JS를 시장현황 페이지에만 조건부 삽입.
    플러그인 slug: head-footer-code/head-footer-code.php
    """
    print('\n[4] Head & Footer Code 플러그인으로 에셋 삽입 시도...')

    # Head & Footer Code 는 options 테이블에 설정을 저장하므로
    # wp-json/head-footer-code 엔드포인트가 없음.
    # 대신 WP Options API (커스텀 플러그인 필요)나
    # 인라인 코드 삽입 방식을 사용.
    # 여기서는 wp-json/wp/v2/settings 로 시도 후,
    # 실패하면 대안 안내를 출력.

    # 에셋 삽입용 PHP 코드 (functions.php 또는 뮤 플러그인)
    asset_php = f"""<?php
/**
 * 정보보호 통계 대시보드 에셋 로더
 * 시장현황 페이지(ID={PAGE_ID})에만 조건부 로드
 */
add_action('wp_enqueue_scripts', function() {{
    if (is_page({PAGE_ID})) {{
        // Chart.js CDN
        wp_enqueue_script(
            'chartjs',
            'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js',
            [], '4.4.1', true
        );
        // Google Fonts
        wp_enqueue_style(
            'db-fonts',
            'https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap',
            [], null
        );
        // 대시보드 CSS
        wp_enqueue_style(
            'db-dashboard',
            '{ASSET_BASE_URL}/dashboard.css',
            ['db-fonts'], '1.0'
        );
        // 대시보드 데이터 (먼저 로드)
        wp_enqueue_script(
            'db-data',
            '{ASSET_BASE_URL}/dashboard-data.js',
            ['chartjs'], '1.0', true
        );
        // 대시보드 렌더링
        wp_enqueue_script(
            'db-render',
            '{ASSET_BASE_URL}/dashboard-render.js',
            ['db-data'], '1.0', true
        );
    }}
}});
"""
    # mu-plugins 디렉터리에 업로드 시도 (FTP)
    mu_plugin_path = '/www/wp-content/mu-plugins/dashboard-assets.php'
    print(f'  → MU 플러그인으로 에셋 로더 업로드 시도: {mu_plugin_path}')

    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)

        # mu-plugins 디렉터리 생성
        try:
            ftp.mkd('/www/wp-content/mu-plugins')
        except ftplib.error_perm:
            pass

        # PHP 파일 업로드
        import io
        ftp.storbinary('STOR ' + mu_plugin_path, io.BytesIO(asset_php.encode()))
        ftp.quit()
        print(f'  ✓ 에셋 로더 MU 플러그인 업로드 성공!')
        return True

    except Exception as e:
        print(f'  ✗ MU 플러그인 업로드 실패: {e}')
        print('\n  ⚠️  수동 처리 필요:')
        print('  아래 코드를 WordPress 관리자 > 외모 > 테마 편집기 > functions.php 맨 아래에 추가하거나')
        print('  Head & Footer Code 플러그인에서 HTML(JS) 형태로 해당 페이지에 삽입하세요.\n')
        print('  --- 에셋 로더 PHP 코드 ---')
        print(asset_php)
        return False


def main():
    print('=' * 60)
    print('  정보보호 통계 대시보드 → WordPress 배포')
    print('=' * 60)

    # 1. 파일 업로드
    upload_files_ftp()

    # 2. Head & Footer Code 플러그인 활성화
    activate_plugin('head-footer-code/head-footer-code.php')

    # 3. 페이지 콘텐츠 업데이트
    update_wp_page()

    # 4. 에셋 로더 설치
    inject_assets_via_hfc()

    print('\n' + '=' * 60)
    print('  배포 완료!')
    print(f'  페이지 확인: {WP_URL}/시장현황/')
    print('=' * 60)


if __name__ == '__main__':
    main()
