import base64, requests
from pathlib import Path

WP_URL = 'https://ajken.mycafe24.com'
WP_USER = 'inhoe.an@gmail.com'
WP_PASS = 'ISPe NJZf FCSb Qwh3 MPf2 ZPds'
PAGE_ID = 2184

def read_file(path):
    with open(path, encoding='utf-8') as f:
        return f.read()

# Read the HTML skeleton (this is small enough to pass the firewall)
html_body = read_file('dashboard/page-content.html')

assets_url = WP_URL + '/wp-content/uploads/dashboard'

# Final HTML with external links
final_content = f'''<!-- 정보보호 통계 대시보드 - sFTP 배포 버전 -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>

<link rel="stylesheet" href="{assets_url}/dashboard.css">

{html_body}

<script src="{assets_url}/dashboard-data.js"></script>
<script src="{assets_url}/dashboard-render.js"></script>
'''

headers = {
    'Authorization': 'Basic ' + base64.b64encode(f'{WP_USER}:{WP_PASS}'.encode()).decode(),
    'Content-Type': 'application/json',
}

print(f"Updating Page {PAGE_ID} at {WP_URL}...")
r = requests.post(
    f'{WP_URL}/wp-json/wp/v2/pages/{PAGE_ID}',
    headers=headers,
    json={'content': final_content, 'status': 'publish'}
)

if r.status_code == 200:
    print('SUCCESS! Dashboard is now live.')
    print(f"URL: {WP_URL}/%ec%8b%9c%ec%9e%a5%ed%98%84%ed%99%a9/")
else:
    print(f'FAILED: {r.status_code}')
    print(r.text)
