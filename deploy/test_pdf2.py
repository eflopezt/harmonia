import io
import xhtml2pdf
from xhtml2pdf import pisa
import reportlab
print('xhtml2pdf:', xhtml2pdf.__version__)
print('reportlab:', reportlab.Version)

html = """<html><head><meta charset="utf-8"><style>@page{size:A4;margin:1.5cm} body{font-family:Helvetica;font-size:8pt}</style></head><body>
<p style="background-color:#0f766e;color:white;padding:10px">TEST HEADER</p>
<table><tr><th>S</th><th>L</th><th>M</th><th>X</th><th>J</th><th>V</th><th>S</th><th>D</th></tr>
<tr><td>1</td><td style="background-color:#d1fae5">21 A</td><td style="background-color:#d1fae5">22 A</td><td style="background-color:#d1fae5">23 A</td><td style="background-color:#fee2e2">24 F</td><td style="background-color:#d1fae5">25 A</td><td style="background-color:#f3f4f6">26 DL</td><td style="background-color:#f3f4f6">27 DL</td></tr>
<tr><td>2</td><td style="background-color:#d1fae5">28 A</td><td style="background-color:#d1fae5">01 A</td><td style="background-color:#d1fae5">02 A</td><td style="background-color:#d1fae5">03 A</td><td style="background-color:#d1fae5">04 A</td><td style="background-color:#d1fae5">05 A</td><td style="background-color:#dbeafe">06 V</td></tr>
</table>
<p>Firma: _______________</p>
</body></html>"""

buf = io.BytesIO()
r = pisa.CreatePDF(io.StringIO(html), dest=buf)
print('Result:', 'OK' if not r.err else 'FAIL', 'size=', len(buf.getvalue()))
