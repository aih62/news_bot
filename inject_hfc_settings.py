"""
inject_hfc_settings.py
CSS/JS를 Head & Footer Code 플러그인 옵션으로 직접 저장
"""
import base64, requests
from pathlib import Path

WP_URL = 'https://ajken.mycafe24.com'
WP_USER = 'inhoe.an@gmail.com'
WP_PASS = 'ISPe NJZf FCSb Qwh3 MPf2 ZPds'

headers = {
    'Authorization': 'Basic ' + base64.b64encode(f'{WP_USER}:{WP_PASS}'.encode()).decode(),
    'Content-Type': 'application/json',
}

SCRIPT_DIR = Path(__file__).parent
DASHBOARD_DIR = SCRIPT_DIR / 'dashboard'

css = (DASHBOARD_DIR / 'dashboard.css').read_text(encoding='utf-8')
data_js = (DASHBOARD_DIR / 'dashboard-data.js').read_text(encoding='utf-8')
render_js = (DASHBOARD_DIR / 'dashboard-render.js').read_text(encoding='utf-8')

# Head & Footer Code 플러그인이 사용하는 option key
# 플러그인 소스 기준: hfc_head (헤드 삽입), hfc_footer_end (body 종료 전)
cdn_head = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>"""

footer_code = f"""<style>
{css}
</style>
<script>
{data_js}
</script>
<script>
{render_js}
</script>"""

print('CSS:', len(css), 'bytes')
print('data_js:', len(data_js), 'bytes')
print('render_js:', len(render_js), 'bytes')
print('footer_code:', len(footer_code), 'bytes')

# WP Settings API 시도
r = requests.post(WP_URL + '/wp-json/wp/v2/settings', headers=headers, json={
    'hfc_head': cdn_head,
    'hfc_footer_end': footer_code,
})
print(f'\nhfc 설정 저장: {r.status_code}')
if r.status_code == 200:
    print('SUCCESS')
else:
    print(r.text[:300])

# 실패 시 대안: wp-json/wp/v2/options 커스텀 엔드포인트 (없으면 실패)
if r.status_code != 200:
    print('\n대안 시도...')
    # WP의 기본 settings API는 명시적으로 register_setting 된 것만 허용
    # head-footer-code 플러그인이 register_setting 하는지 여부에 따라 달라짐
    r2 = requests.get(WP_URL + '/wp-json/wp/v2/settings', headers=headers)
    if r2.status_code == 200:
        all_keys = list(r2.json().keys())
        print('허용된 설정 키:', all_keys)
