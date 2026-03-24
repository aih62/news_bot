import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

load_dotenv()

WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
WP_SITE_URL = os.getenv("WP_SITE_URL")

def deactivate_plugin(plugin_slug):
    print(f"Trying to deactivate plugin: {plugin_slug} on {WP_SITE_URL}...")
    endpoint = f"{WP_SITE_URL.rstrip('/')}/wp-json/wp/v2/plugins/{plugin_slug}"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    try:
        # 플러그인 비활성화 시도 (status를 'inactive'로 변경)
        res = requests.post(endpoint, auth=auth, json={'status': 'inactive'}, verify=False, timeout=20)
        if res.status_code == 200:
            print(f"Success! Plugin '{plugin_slug}' has been DEACTIVATED.")
            return True
        else:
            print(f"Failed! Code: {res.status_code} - {res.text}")
            print(f"Make sure you have administrative privileges and the REST API for plugins is enabled.")
    except Exception as e:
        print(f"Error: {e}")
    return False

if __name__ == "__main__":
    # EWWW Image Optimizer 비활성화 시도
    # 플러그인 슬러그는 ewww-image-optimizer/ewww-image-optimizer 임
    deactivate_plugin("ewww-image-optimizer/ewww-image-optimizer")
