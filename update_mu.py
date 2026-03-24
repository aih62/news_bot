import os
import io
import ftplib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# FTP/SSH details from .env and script context
FTP_HOST = 'ajken.mycafe24.com'
FTP_USER = 'ajken'
FTP_PASS = os.getenv('GOOGLE_PASSWORD', 'dksdlsghl62@')
PAGE_ID = 2184
ASSET_BASE_URL = 'https://ajken.mycafe24.com/wp-content/uploads/dashboard'

# New version string based on current time
import datetime
VERSION = datetime.datetime.now().strftime('%Y%m%d_%H%M')

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
            ['db-fonts'], '{VERSION}'
        );
        // 대시보드 데이터 (먼저 로드)
        wp_enqueue_script(
            'db-data',
            '{ASSET_BASE_URL}/dashboard-data.js',
            ['chartjs'], '{VERSION}', true
        );
        // 대시보드 렌더링
        wp_enqueue_script(
            'db-render',
            '{ASSET_BASE_URL}/dashboard-render.js',
            ['db-data'], '{VERSION}', true
        );
    }}
}});
"""

mu_plugin_path = 'www/wp-content/mu-plugins/dashboard-assets.php'

print(f'Updating MU plugin with version {VERSION} via FTP...')
try:
    # We'll try FTP as in the original script
    ftp = ftplib.FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.storbinary('STOR ' + mu_plugin_path, io.BytesIO(asset_php.encode()))
    ftp.quit()
    print('MU plugin update successful!')
except Exception as e:
    print(f'FTP failed: {e}. Trying SFTP/SCP...')
    # If FTP fails, we use the SCP command we know works
    with open('temp_mu.php', 'w', encoding='utf-8') as f:
        f.write(asset_php)
    import subprocess
    cmd = f'scp -i C:\\Users\\inhoe\\.ssh\\id_rsa -o StrictHostKeyChecking=no temp_mu.php {FTP_USER}@{FTP_HOST}:{mu_plugin_path}'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print('SCP MU plugin update successful!')
    else:
        print(f'SCP failed: {result.stderr}')
    if os.path.exists('temp_mu.php'):
        os.remove('temp_mu.php')
