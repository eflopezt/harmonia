"""
Nóminas — Generador de Boletas de Pago PDF.

Usa xhtml2pdf (ya instalado) para generar boletas desde RegistroNomina.
"""
import io
from decimal import Decimal

from django.template.loader import render_to_string
from django.conf import settings


def _monto(value):
    """Formatea monto Decimal como string con 2 decimales."""
    if not value:
        return '0.00'
    try:
        return f'{Decimal(str(value)):.2f}'
    except Exception:
        return '0.00'


def generar_boleta_pdf(registro):
    """
    Genera la boleta de pago en PDF para un RegistroNomina.

    Returns:
        bytes — contenido del PDF
    """
    try:
        from xhtml2pdf import pisa
    except ImportError:
        raise RuntimeError(
            'xhtml2pdf no está instalado. Ejecuta: pip install xhtml2pdf'
        )

    # Construir contexto enriquecido
    lineas_ingresos = []
    lineas_descuentos = []
    lineas_aportes = []
    total_ingresos = Decimal('0')
    total_descuentos = Decimal('0')

    for linea in registro.lineas.select_related('concepto').order_by(
        'concepto__tipo', 'concepto__orden'
    ):
        entry = {
            'nombre': linea.concepto.nombre,
            'monto': linea.monto,
            'monto_str': _monto(linea.monto),
        }
        if linea.concepto.tipo == 'INGRESO':
            lineas_ingresos.append(entry)
            total_ingresos += linea.monto or Decimal('0')
        elif linea.concepto.tipo == 'DESCUENTO':
            lineas_descuentos.append(entry)
            total_descuentos += linea.monto or Decimal('0')
        else:
            lineas_aportes.append(entry)

    # Datos del trabajador snapshot
    personal = registro.personal

    context = {
        'registro': registro,
        'personal': personal,
        'periodo': registro.periodo,
        'lineas_ingresos': lineas_ingresos,
        'lineas_descuentos': lineas_descuentos,
        'lineas_aportes': lineas_aportes,
        'total_ingresos': total_ingresos,
        'total_descuentos': total_descuentos,
        'neto': registro.neto_a_pagar,
        'total_ingresos_str': _monto(total_ingresos),
        'total_descuentos_str': _monto(total_descuentos),
        'neto_str': _monto(registro.neto_a_pagar),
        'essalud_str': _monto(registro.aporte_essalud),
        # Config empresa
        'empresa_nombre': getattr(
            getattr(settings, 'HARMONI_EMPRESA', None), 'nombre', 'Empresa'
        ),
    }

    # Obtener config del sistema para empresa
    try:
        from core.context_processors import _get_config
        cfg = _get_config()
        if cfg:
            context['empresa_nombre'] = cfg.empresa_nombre or 'Empresa'
            context['empresa_ruc'] = cfg.empresa_ruc or ''
    except Exception:
        context.setdefault('empresa_ruc', '')

    html_string = render_to_string('nominas/boleta_pdf.html', context)

    buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        io.StringIO(html_string),
        dest=buffer,
        encoding='utf-8',
    )

    if pisa_status.err:
        raise RuntimeError(f'Error generando PDF: {pisa_status.err}')

    return buffer.getvalue()
