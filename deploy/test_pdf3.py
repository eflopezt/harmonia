import io, os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()
from xhtml2pdf import pisa

with open('/tmp/test_report.html') as f:
    html = f.read()

# Strip components one by one to find the culprit
import re

# 1. Only the calendar table
match = re.search(r'(<table>.*?</table>)', html, re.DOTALL)
if match:
    table_html = match.group(1)
    test = f'<html><body>{table_html}</body></html>'
    buf = io.BytesIO()
    try:
        r = pisa.CreatePDF(io.StringIO(test), dest=buf)
        print(f'Table only: {"OK" if not r.err else "FAIL"} size={len(buf.getvalue())}')
    except Exception as e:
        print(f'Table only: ERROR {e}')

# 2. Only the header paragraph
header_match = re.search(r'(<p style="background-color:#0f766e.*?</p>)', html, re.DOTALL)
if header_match:
    test = f'<html><body>{header_match.group(1)}</body></html>'
    buf = io.BytesIO()
    try:
        r = pisa.CreatePDF(io.StringIO(test), dest=buf)
        print(f'Header P only: {"OK" if not r.err else "FAIL"} size={len(buf.getvalue())}')
    except Exception as e:
        print(f'Header P: ERROR {e}')

# 3. Header + info p
info_match = re.search(r'(<p style="font-size:7.5pt.*?</p>)', html, re.DOTALL)
if info_match:
    test = f'<html><body>{header_match.group(1)}{info_match.group(1)}</body></html>'
    buf = io.BytesIO()
    try:
        r = pisa.CreatePDF(io.StringIO(test), dest=buf)
        print(f'Header + Info: {"OK" if not r.err else "FAIL"} size={len(buf.getvalue())}')
    except Exception as e:
        print(f'Header + Info: ERROR {e}')

# 4. All tables
tables = re.findall(r'<table>.*?</table>', html, re.DOTALL)
for i, t in enumerate(tables):
    test = f'<html><body>{t}</body></html>'
    buf = io.BytesIO()
    try:
        r = pisa.CreatePDF(io.StringIO(test), dest=buf)
        print(f'Table {i}: {"OK" if not r.err else "FAIL"} size={len(buf.getvalue())} chars={len(t)}')
    except Exception as e:
        print(f'Table {i}: ERROR {type(e).__name__}')

# 5. Firma
firma = re.search(r'(<br><br>.*Sello y Firma.*?</p>)', html, re.DOTALL)
if firma:
    test = f'<html><body>{firma.group(1)}</body></html>'
    buf = io.BytesIO()
    try:
        r = pisa.CreatePDF(io.StringIO(test), dest=buf)
        print(f'Firma: {"OK" if not r.err else "FAIL"}')
    except Exception as e:
        print(f'Firma: ERROR {e}')
