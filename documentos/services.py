"""
Servicio de generación de constancias/documentos legales en PDF.

Usa xhtml2pdf para convertir HTML (con variables Django template) a PDF.
Soporta membrete corporativo automático con logo, dirección y firma.
"""
import io
from datetime import date

from django.template import Template, Context
from xhtml2pdf import pisa

MESES_ES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre',
}


def _fecha_texto(fecha):
    """Convierte date a texto: '01 de marzo de 2026'."""
    return f'{fecha.day:02d} de {MESES_ES[fecha.month]} de {fecha.year}'


def _calcular_antiguedad(personal):
    """Retorna antigüedad como texto legible."""
    if not personal.fecha_alta:
        return 'N/A'
    hoy = date.today()
    delta = hoy - personal.fecha_alta
    anios = delta.days // 365
    meses = (delta.days % 365) // 30
    dias = (delta.days % 365) % 30

    partes = []
    if anios > 0:
        partes.append(f'{anios} año{"s" if anios != 1 else ""}')
    if meses > 0:
        partes.append(f'{meses} mes{"es" if meses != 1 else ""}')
    if not partes and dias > 0:
        partes.append(f'{dias} día{"s" if dias != 1 else ""}')

    return ', '.join(partes) or 'menos de 1 día'


def _build_membrete_html(empresa_ctx):
    """
    Construye el HTML del membrete corporativo para insertar en PDFs.
    Usa tabla para compatibilidad con xhtml2pdf (no soporta flexbox ni grid).
    """
    color = empresa_ctx.get('membrete_color', '#0f766e')
    nombre = empresa_ctx.get('nombre', '')
    ruc = empresa_ctx.get('ruc', '')
    direccion = empresa_ctx.get('direccion', '')
    telefono = empresa_ctx.get('telefono', '')
    email = empresa_ctx.get('email', '')
    web = empresa_ctx.get('web', '')
    logo_b64 = empresa_ctx.get('logo_base64', '')

    # Construir celda izquierda (logo)
    if logo_b64:
        logo_cell = f'<td style="width:110px; vertical-align:middle; padding-right:14px;"><img src="{logo_b64}" style="max-width:100px; max-height:55px;" /></td>'
    else:
        logo_cell = ''

    # Construir datos de contacto
    contacto_parts = []
    if direccion:
        contacto_parts.append(f'<span>{direccion}</span>')
    if telefono:
        contacto_parts.append(f'<span>Tel: {telefono}</span>')
    if email:
        contacto_parts.append(f'<span>{email}</span>')
    if web:
        contacto_parts.append(f'<span>{web}</span>')
    contacto_html = ' &nbsp;|&nbsp; '.join(contacto_parts) if contacto_parts else ''

    datos_cell = f'''<td style="vertical-align:middle;">
        <div style="font-size:13pt; font-weight:bold; color:{color}; margin-bottom:3px;">{nombre}</div>
        {"<div style='font-size:8pt; color:#888; margin-bottom:2px;'>RUC: " + ruc + "</div>" if ruc else ""}
        {"<div style='font-size:8pt; color:#666;'>" + contacto_html + "</div>" if contacto_html else ""}
    </td>'''

    return f'''<table style="width:100%; border-bottom:2.5px solid {color}; margin-bottom:20pt; padding-bottom:10pt;">
<tr>
{logo_cell}
{datos_cell}
</tr>
</table>'''


def _build_firma_html(empresa_ctx):
    """
    Construye el bloque HTML de firma autorizada.
    Si hay imagen de firma, la inserta encima de la línea.
    """
    firma_nombre = empresa_ctx.get('firma_nombre', '')
    firma_cargo = empresa_ctx.get('firma_cargo', '')
    firma_b64 = empresa_ctx.get('firma_base64', '')
    color = empresa_ctx.get('membrete_color', '#0f766e')

    if not firma_nombre and not firma_b64:
        return ''

    firma_img_html = ''
    if firma_b64:
        firma_img_html = f'<img src="{firma_b64}" style="max-width:160px; max-height:60px; display:block; margin:0 auto 4pt;" />'

    return f'''<div class="firma" style="margin-top:48pt; text-align:center;">
{firma_img_html}
<div class="linea" style="border-top:1px solid #333; width:200px; margin:0 auto; padding-top:4pt;"></div>
{"<div style='font-weight:bold; font-size:10pt;'>" + firma_nombre + "</div>" if firma_nombre else ""}
{"<div style='font-size:9pt; color:#666;'>" + firma_cargo + "</div>" if firma_cargo else ""}
{"<div style='font-size:9pt; color:" + color + ";'>" + empresa_ctx.get('nombre','') + "</div>" if empresa_ctx.get('nombre') else ""}
</div>'''


def generar_constancia_pdf(plantilla, personal, extra_context=None):
    """Genera un PDF a partir de una PlantillaConstancia y datos del empleado.

    Args:
        plantilla: PlantillaConstancia instance
        personal:  Personal instance
        extra_context: dict con variables adicionales

    Returns:
        bytes - contenido del PDF generado
    """
    hoy = date.today()

    # ── Construir contexto ───────────────────────────────────────────────────
    ctx = {
        'personal': personal,
        'hoy': hoy,
        'hoy_texto': _fecha_texto(hoy),
        'antiguedad': _calcular_antiguedad(personal),
        'fecha_alta_texto': _fecha_texto(personal.fecha_alta) if personal.fecha_alta else 'N/A',
        'fecha_cese_texto': _fecha_texto(personal.fecha_cese) if personal.fecha_cese else None,
    }

    # ── Datos de empresa desde ConfiguracionSistema ──────────────────────────
    empresa_ctx = {'nombre': 'EMPRESA S.A.C.', 'ruc': '', 'direccion': ''}
    membrete_mostrar = True

    try:
        from asistencia.models import ConfiguracionSistema
        config = ConfiguracionSistema.get()
        empresa_ctx = {
            'nombre': config.empresa_nombre or 'EMPRESA S.A.C.',
            'ruc': config.ruc or '',
            'direccion': config.empresa_direccion or '',
            'telefono': config.empresa_telefono or '',
            'email': config.empresa_email or '',
            'web': config.empresa_web or '',
            'logo_base64': config.logo_base64,        # property → base64 string o None
            'firma_base64': config.firma_base64,      # property → base64 string o None
            'firma_nombre': config.firma_nombre or '',
            'firma_cargo': config.firma_cargo or '',
            'membrete_color': config.membrete_color or '#0f766e',
            'membrete_mostrar': config.membrete_mostrar,
        }
        membrete_mostrar = config.membrete_mostrar
    except Exception:
        pass

    ctx['empresa'] = empresa_ctx

    if extra_context:
        ctx.update(extra_context)

    # ── Renderizar cuerpo del documento ─────────────────────────────────────
    tpl = Template(plantilla.contenido_html)
    body_html = tpl.render(Context(ctx))

    # ── Construir membrete y firma ───────────────────────────────────────────
    membrete_html = _build_membrete_html(empresa_ctx) if membrete_mostrar else ''
    firma_html = _build_firma_html(empresa_ctx)

    # ── Envolver en página completa si no tiene <html> tag ───────────────────
    if '<html' not in body_html.lower():
        color = empresa_ctx.get('membrete_color', '#0f766e')
        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{ size: A4; margin: 2cm 2cm 2.5cm; }}
body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
}}
h1 {{
    font-size: 13pt;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: {color};
    margin-bottom: 20pt;
    margin-top: 12pt;
}}
h2 {{ font-size: 11pt; text-align: center; margin-bottom: 14pt; }}
.body-text {{ text-align: justify; margin-bottom: 12pt; }}
table {{ width: 100%; border-collapse: collapse; margin: 12pt 0; }}
td, th {{ padding: 4pt 8pt; text-align: left; }}
.label {{ font-weight: bold; width: 35%; color: #444; }}
.footer {{
    position: fixed;
    bottom: 0; left: 0; right: 0;
    text-align: center;
    font-size: 7.5pt;
    color: #bbb;
    border-top: 1px solid #eee;
    padding-top: 4pt;
}}
</style>
</head>
<body>
{membrete_html}
{body_html}
{firma_html}
<div class="footer">
    Documento generado electrónicamente por Harmoni ERP - {hoy.strftime('%d/%m/%Y')}
</div>
</body>
</html>"""
    else:
        # El template ya tiene estructura HTML completa; inyectamos membrete después de <body>
        html_content = body_html
        if membrete_html:
            html_content = html_content.replace('<body>', f'<body>\n{membrete_html}', 1)

    # ── Generar PDF ──────────────────────────────────────────────────────────
    buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        io.StringIO(html_content),
        dest=buffer,
        encoding='utf-8',
    )

    if pisa_status.err:
        raise RuntimeError(f'Error generando PDF: {pisa_status.err} errores')

    return buffer.getvalue()
