import requests
from requests.auth import HTTPBasicAuth
import os
import json
from dotenv import load_dotenv

load_dotenv()

WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
WP_SITE_URL = os.getenv("WP_SITE_URL")

def inspect_settings():
    print(f"Inspecting settings on [{WP_SITE_URL}]...")
    # 워드프레스 기본 설정 엔드포인트
    endpoint = f"{WP_SITE_URL.rstrip('/')}/wp-json/wp/v2/settings"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    keywords = ['import', 'save', 'media', 'fifu', 'ewww', 'sideload', 'upload', 'external', 'featured']
    
    try:
        res = requests.get(endpoint, auth=auth, verify=False, timeout=20)
        if res.status_code == 200:
            settings = res.json()
            print("\n--- Found Relevant Settings ---")
            found = False
            for key, value in settings.items():
                if any(kw in key.lower() for kw in keywords):
                    print(f"Setting: {key} = {value}")
                    found = True
            
            if not found:
                print("No obvious auto-upload settings found in standard REST API settings.")
                print("Checking for common plugin-specific options...")
                
        else:
            print(f"Error accessing settings: {res.status_code} - {res.text}")
            print("\nHint: Some settings are only visible if the 'REST API Controller' or similar plugin is configured to expose them.")

    except Exception as e:
        print(f"Exception during inspection: {e}")

if __name__ == "__main__":
    inspect_settings()
