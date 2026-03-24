import base64
import requests
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

WP_URL = os.getenv('WP_SITE_URL', 'https://ajken.mycafe24.com')
WP_USER = os.getenv('WP_USERNAME', 'inhoe.an@gmail.com')
WP_PASS = os.getenv('WP_APP_PASSWORD', 'ISPe NJZf FCSb Qwh3 MPf2 ZPds')
PAGE_ID = 2184

DASHBOARD_DIR = Path('dashboard')
html_file = DASHBOARD_DIR / 'page-content.html'

with open(html_file, encoding='utf-8') as f:
    page_html = f.read()

auth = base64.b64encode(f'{WP_USER}:{WP_PASS}'.encode()).decode()
headers = {
    'Authorization': f'Basic {auth}',
    'Content-Type': 'application/json',
}

print(f'Updating page {PAGE_ID} at {WP_URL}...')
r = requests.post(
    f'{WP_URL}/wp-json/wp/v2/pages/{PAGE_ID}',
    headers=headers,
    json={
        'content': page_html,
        'status': 'publish',
    },
)

if r.status_code == 200:
    print('Update successful!')
    print(f'URL: {r.json().get("link")}')
else:
    print(f'Update failed: {r.status_code}')
    print(r.text)
