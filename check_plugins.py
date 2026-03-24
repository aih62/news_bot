import requests
from requests.auth import HTTPBasicAuth
import os
import json
from dotenv import load_dotenv

load_dotenv()

WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
WP_SITE_URL = os.getenv("WP_SITE_URL")

def check_active_plugins():
    print(f"Checking plugins on [{WP_SITE_URL}]...")
    endpoint = f"{WP_SITE_URL.rstrip('/')}/wp-json/wp/v2/plugins"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    try:
        res = requests.get(endpoint, auth=auth, verify=False, timeout=20)
        if res.status_code == 200:
            plugins = res.json()
            active_plugins = []
            for p in plugins:
                if p.get('status') == 'active':
                    active_plugins.append(f"{p.get('plugin')} ({p.get('name')})")
            
            print("\nActive Plugins:")
            for p in active_plugins:
                print(f"- {p}")
            return active_plugins
        else:
            print(f"Error: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Exception: {e}")
    return []

if __name__ == "__main__":
    check_active_plugins()
