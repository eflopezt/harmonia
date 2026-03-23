import io
from xhtml2pdf import pisa

# Simple test
html = '<html><head><style>@page{size:A4 landscape;margin:5mm}</style></head><body><table><tr><td>TEST</td><td>OK2</td></tr></table></body></html>'
buf = io.BytesIO()
r = pisa.CreatePDF(io.StringIO(html), dest=buf)
print(f'Simple: OK={not r.err}')

# Test with base64 img
from asistencia.membrete_b64 import HEADER_IMG, FOOTER_IMG
html2 = f'<html><head><style>@page{{size:A4 landscape;margin:5mm}}</style></head><body><table><tr><td><img src="{HEADER_IMG}" style="height:25px"></td><td>RUC</td></tr></table></body></html>'
buf2 = io.BytesIO()
try:
    r2 = pisa.CreatePDF(io.StringIO(html2), dest=buf2)
    print(f'With img: OK={not r2.err} size={len(buf2.getvalue())}')
except Exception as e:
    print(f'With img: ERROR {e}')

# Without img - just text header
html3 = '<html><head><style>@page{size:A4 landscape;margin:5mm}</style></head><body><table><tr><td style="background-color:#0f766e;color:white;padding:5px;font-weight:bold">CONSORCIO STILER</td><td style="padding:5px">RUC</td></tr></table></body></html>'
buf3 = io.BytesIO()
r3 = pisa.CreatePDF(io.StringIO(html3), dest=buf3)
print(f'Text header: OK={not r3.err}')
