"""
Nóminas — Generador de Boletas de Pago PDF.

Usa xhtml2pdf (ya instalado) para generar boletas desde RegistroNomina.
Diseño: 3 columnas (Remuneraciones | Descuentos | Aportes Empleador).
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

    # ── Clasificar líneas por tipo ───────────────────────────────────────
    lineas_ingresos   = []
    lineas_descuentos = []
    lineas_aportes    = []
    total_ingresos    = Decimal('0')
    total_descuentos  = Decimal('0')
    total_aportes     = Decimal('0')

    for linea in registro.lineas.select_related('concepto').order_by(
        'concepto__tipo', 'concepto__orden'
    ):
        entry = {
            'nombre':    linea.concepto.nombre,
            'monto':     linea.monto,
            'monto_str': _monto(linea.monto),
            'base_str':  _monto(linea.base_calculo) if linea.base_calculo else '',
            'pct':       linea.porcentaje_aplicado,
            'obs':       linea.observacion or '',
        }
        if linea.concepto.tipo == 'INGRESO':
            lineas_ingresos.append(entry)
            total_ingresos += linea.monto or Decimal('0')
        elif linea.concepto.tipo == 'DESCUENTO':
            lineas_descuentos.append(entry)
            total_descuentos += linea.monto or Decimal('0')
        else:  # APORTE
            lineas_aportes.append(entry)
            total_aportes += linea.monto or Decimal('0')

    # EsSalud siempre va en la columna aportes (campo directo del registro)
    essalud = registro.aporte_essalud or Decimal('0')
    # Si no hay una línea de aporte para EsSalud, construir entrada explícita
    essalud_en_lineas = any(
        'essalud' in l['nombre'].lower() or 'seguro' in l['nombre'].lower()
        for l in lineas_aportes
    )
    if not essalud_en_lineas and essalud > 0:
        lineas_aportes.append({
            'nombre':    'EsSalud (9%)',
            'monto':     essalud,
            'monto_str': _monto(essalud),
            'base_str':  _monto(registro.total_ingresos),
            'pct':       Decimal('9'),
            'obs':       'Aporte empleador Ley 29351',
        })
        total_aportes += essalud

    # ── Datos del trabajador ─────────────────────────────────────────────
    personal = registro.personal

    # Fecha ingreso
    try:
        fecha_ingreso = personal.fecha_ingreso
        fecha_ingreso_str = fecha_ingreso.strftime('%d/%m/%Y') if fecha_ingreso else '—'
    except Exception:
        fecha_ingreso_str = '—'

    # Fecha fin contrato
    try:
        fecha_fin = personal.fecha_fin_contrato
        fecha_fin_str = fecha_fin.strftime('%d/%m/%Y') if fecha_fin else 'Indefinido'
    except Exception:
        fecha_fin_str = '—'

    # Días del período
    try:
        dias_periodo = registro.periodo.fecha_fin.day if registro.periodo.fecha_fin else 30
    except Exception:
        dias_periodo = 30

    # Banco / CCI
    try:
        banco_nombre = personal.banco or ''
        cuenta_cci   = personal.cuenta_cci or ''
    except Exception:
        banco_nombre = ''
        cuenta_cci   = ''

    # AFP / CUSPP
    try:
        cuspp = personal.cuspp or ''
    except Exception:
        cuspp = ''

    # Área
    try:
        area_nombre = personal.subarea.area.nombre if personal.subarea else '—'
    except Exception:
        area_nombre = '—'

    context = {
        'registro': registro,
        'personal': personal,
        'periodo':  registro.periodo,

        # Líneas
        'lineas_ingresos':   lineas_ingresos,
        'lineas_descuentos': lineas_descuentos,
        'lineas_aportes':    lineas_aportes,

        # Totales
        'total_ingresos':      total_ingresos,
        'total_descuentos':    total_descuentos,
        'total_aportes':       total_aportes,
        'total_ingresos_str':  _monto(total_ingresos),
        'total_descuentos_str':_monto(total_descuentos),
        'total_aportes_str':   _monto(total_aportes),
        'neto':                registro.neto_a_pagar,
        'neto_str':            _monto(registro.neto_a_pagar),
        'essalud_str':         _monto(essalud),
        'costo_empresa_str':   _monto(registro.costo_total_empresa),

        # Trabajador
        'area_nombre':        area_nombre,
        'cuspp':              cuspp,
        'fecha_ingreso_str':  fecha_ingreso_str,
        'fecha_fin_str':      fecha_fin_str,
        'banco_nombre':       banco_nombre,
        'cuenta_cci':         cuenta_cci,
        'dias_periodo':       dias_periodo,

        # Config empresa (se rellena abajo)
        'empresa_nombre': 'Empresa',
        'empresa_ruc':    '',
        'empresa_dir':    '',
    }

    # Obtener config del sistema para datos de empresa
    try:
        from core.context_processors import _get_config
        cfg = _get_config()
        if cfg:
            context['empresa_nombre'] = cfg.empresa_nombre or 'Empresa'
            context['empresa_ruc']    = cfg.empresa_ruc    or ''
            context['empresa_dir']    = getattr(cfg, 'empresa_direccion', '') or ''
    except Exception:
        pass

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
