"""
ZapSign - Servicio de Firma Digital.

Integración con ZapSign REST API v1.
Documentación: https://docs.zapsign.com.br/

API Key se configura en ConfiguracionSistema.zapsign_api_key
"""
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

ZAPSIGN_BASE_URL = 'https://api.zapsign.com.br/api/v1'


def _get_api_token():
    """Obtiene el API token de ZapSign desde la configuración del sistema."""
    try:
        from asistencia.models import ConfiguracionSistema
        cfg = ConfiguracionSistema.objects.first()
        if cfg and cfg.zapsign_api_key:
            return cfg.zapsign_api_key
    except Exception:
        pass
    from django.conf import settings
    return getattr(settings, 'ZAPSIGN_API_KEY', '')


def _request(method, endpoint, data=None, token=None):
    """Realiza una petición a la API de ZapSign."""
    if not token:
        token = _get_api_token()
    if not token:
        raise ValueError(
            'ZapSign API Key no configurado. '
            'Ve a Sistema → Configuración → Firma Digital y configura la API Key.'
        )

    url = f'{ZAPSIGN_BASE_URL}/{endpoint.lstrip("/")}'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method.upper())

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'ZapSign API error {e.code}: {body}')
    except urllib.error.URLError as e:
        raise RuntimeError(f'ZapSign conexión fallida: {e.reason}')


def crear_documento_firma(nombre, url_pdf, firmantes, dias_expiracion=30):
    """
    Crea un documento en ZapSign y lo envía a los firmantes.

    Args:
        nombre (str): Nombre descriptivo del documento
        url_pdf (str): URL pública del PDF (debe ser accesible desde internet)
        firmantes (list): Lista de dicts con claves: name, email
        dias_expiracion (int): Días hasta que expire el link de firma

    Returns:
        dict con: token, open_id, created_at, signers[{token, sign_url, ...}]
    """
    payload = {
        'name': nombre,
        'url_pdf': url_pdf,
        'lang': 'es',
        'disable_signer_emails': False,
        'signed_file_only_finished': True,
        'expiration_date': (
            datetime.now() + timedelta(days=dias_expiracion)
        ).strftime('%Y-%m-%dT%H:%M:%S'),
        'signers': [
            {
                'name': s['name'],
                'email': s['email'],
                'lock_name': True,
                'lock_email': True,
                'send_automatic_email': True,
                'send_automatic_whatsapp': False,
                'auth_mode': 'assinaturaTela',
            }
            for s in firmantes
        ],
    }
    return _request('POST', '/docs/', data=payload)


def obtener_estado_documento(token_doc):
    """
    Consulta el estado actual de un documento en ZapSign.

    Returns:
        dict con status, signed_file (URL del PDF firmado si está listo), signers, etc.
    """
    return _request('GET', f'/docs/{token_doc}/')


def cancelar_documento(token_doc):
    """Cancela un documento en ZapSign (no permite seguir firmando)."""
    return _request('DELETE', f'/docs/{token_doc}/')


def reenviar_email_firmante(token_signer):
    """Reenvía el email de firma a un firmante."""
    return _request('PATCH', f'/signers/{token_signer}/', data={'resend_email': True})


def sincronizar_estado(doc_firma):
    """
    Sincroniza el estado de un DocumentoFirmaDigital con ZapSign.

    Args:
        doc_firma: instancia de DocumentoFirmaDigital

    Returns:
        bool - True si el estado cambió, False si no cambió o hubo error
    """
    from django.utils import timezone

    if not doc_firma.zapsign_token:
        return False

    if doc_firma.estado in ('FIRMADO', 'CANCELADO', 'RECHAZADO'):
        return False  # Ya en estado final, no consultar

    try:
        data = obtener_estado_documento(doc_firma.zapsign_token)
    except Exception as e:
        logger.warning(f'[ZapSign] Error consultando doc {doc_firma.pk}: {e}')
        return False

    # Mapear estado ZapSign → estado Harmoni
    zap_status = data.get('status', '')
    ESTADO_MAP = {
        'pending':  'FIRMANDO',
        'finished': 'FIRMADO',
        'canceled': 'CANCELADO',
    }
    nuevo_estado = ESTADO_MAP.get(zap_status, doc_firma.estado)
    changed = False

    if doc_firma.estado != nuevo_estado:
        doc_firma.estado = nuevo_estado
        changed = True

    if nuevo_estado == 'FIRMADO' and not doc_firma.firmado_en:
        doc_firma.firmado_en = timezone.now()
        pdf_url = data.get('signed_file') or ''
        if pdf_url:
            doc_firma.pdf_firmado_url = pdf_url
        changed = True

    if changed:
        doc_firma.save()

    return changed
