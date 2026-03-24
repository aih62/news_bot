"""빌드 스크립트: 전체 페이지 콘텐츠 파일 생성"""
from pathlib import Path

d = Path(__file__).parent

css       = (d / 'dashboard.css').read_text(encoding='utf-8')
data_js   = (d / 'dashboard-data.js').read_text(encoding='utf-8')
render_js = (d / 'dashboard-render.js').read_text(encoding='utf-8')
body      = (d / 'page-content.html').read_text(encoding='utf-8')

full = f"""<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
{css}
</style>

{body}

<script>
{data_js}
</script>
<script>
{render_js}
</script>"""

out = d / 'full_page_content.html'
out.write_text(full, encoding='utf-8')
print(f'빌드 완료: {out}')
print(f'크기: {len(full):,} bytes = {len(full.encode())//1024} KB')
