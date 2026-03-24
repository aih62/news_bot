import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()
WP_URL = os.getenv('WP_SITE_URL', 'https://ajken.mycafe24.com').rstrip('/')
WP_USER = os.getenv('WP_USERNAME', 'inhoe.an@gmail.com')
WP_PASS = os.getenv('WP_APP_PASSWORD')
if not WP_PASS:
    WP_PASS = 'ISPe NJZf FCSb Qwh3 MPf2 ZPds'

auth = HTTPBasicAuth(WP_USER, WP_PASS)
requests.packages.urllib3.disable_warnings()

res = requests.get(f'{WP_URL}/wp-json/wp/v2/pages?search=브리핑', auth=auth, verify=False)
if res.status_code == 200:
    for page in res.json():
        print(f"ID: {page['id']}, Title: {page['title']['rendered']}")
else:
    print(res.status_code)
