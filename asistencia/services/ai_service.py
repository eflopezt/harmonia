"""
Servicio de IA — Ollama local.

Todas las llamadas a IA pasan por este módulo.
La vista o el importador no sabe qué proveedor se usa internamente.

Decisión arquitectural (MEMORY.md):
  - SOLO Ollama local — sin cloud APIs, sin API keys externas.
  - Datos 100% privados — el LLM corre en el propio servidor del cliente.
  - Modelos: llama3.2, mistral, qwen2.5 (para texto), llava (multimodal / PDF).

API Ollama relevante:
  GET  /api/tags          → lista modelos instalados
  POST /api/generate      → generación single-turn (stream=false)
  POST /api/chat          → chat multi-turn (stream=false)
  POST /api/pull          → descargar modelo (no usado aquí)
"""
from __future__ import annotations

import json
import logging
import re
import time

import requests

logger = logging.getLogger('harmoni.ai')

# Timeouts
TIMEOUT_TEST = 5      # segundos — test de conexión
TIMEOUT_GENERAR = 120 # segundos — inferencia (puede ser lenta en CPU)

# Cache global de resolución de modelo (evita re-queries a /api/tags)
_modelo_cache: dict[str, str] = {}   # {base_modelo: nombre_resuelto}
_modelo_cache_ts: float = 0
_MODELO_CACHE_TTL = 300  # 5 minutos

# Descripciones de campos RRHH para el prompt de mapeo
_CAMPO_DESCRIPCION: dict[str, str] = {
    'dni':           'número de documento de identidad del trabajador (DNI, RUC, CE)',
    'nombre':        'apellidos y nombres completos del trabajador',
    'codigo_s10':    'código interno del trabajador en el sistema S10 de obras',
    'fecha':         'fecha del registro de asistencia (formato DD/MM/AAAA o similar)',
    'entrada':       'hora de entrada o marcación de ingreso',
    'salida':        'hora de salida o marcación de egreso',
    'area':          'área, departamento o sección del trabajador',
    'cargo':         'cargo, puesto o categoría laboral del trabajador',
    'sueldo':        'remuneración, sueldo básico o salario del trabajador',
    'categoria_cod': 'código de categoría laboral',
    'categoria':     'nombre de la categoría o tipo de trabajador',
    'afp':           'nombre de la AFP (fondo de pensiones) del trabajador',
    'regimen_pension': 'régimen previsional (AFP o ONP)',
    'cuspp':         'código único del sistema privado de pensiones',
    'correo':        'correo electrónico del trabajador',
    'celular':       'número de teléfono o celular',
}


# ═══════════════════════════════════════════════════════════════════════════
# OllamaService — cliente principal
# ═══════════════════════════════════════════════════════════════════════════

class OllamaService:
    """
    Cliente para el servidor Ollama local.
    Instanciar directamente o usar get_service() para obtener uno
    configurado desde ConfiguracionSistema.
    """

    def __init__(
        self,
        endpoint: str = 'http://localhost:11434',
        modelo: str = 'llama3.2',
    ):
        self.endpoint = endpoint.rstrip('/')
        self.modelo = modelo
        self._modelo_resuelto: str | None = None  # cache del nombre real

    def _resolver_modelo(self) -> str:
        """
        Resuelve el nombre exacto del modelo instalado en Ollama.
        Si el usuario configura 'qwen2.5' pero el instalado es 'qwen2.5:0.5b',
        usa el nombre completo para evitar 404.
        Usa cache global (5min TTL) para evitar re-queries a /api/tags.
        """
        global _modelo_cache, _modelo_cache_ts

        if self._modelo_resuelto:
            return self._modelo_resuelto

        # Verificar cache global
        now = time.time()
        base = self.modelo.split(':')[0].lower()
        if now - _modelo_cache_ts < _MODELO_CACHE_TTL and base in _modelo_cache:
            self._modelo_resuelto = _modelo_cache[base]
            return self._modelo_resuelto

        try:
            resp = requests.get(
                f'{self.endpoint}/api/tags', timeout=TIMEOUT_TEST,
            )
            resp.raise_for_status()
            modelos = [m['name'] for m in resp.json().get('models', [])]

            # Buscar match exacto primero, luego por base
            for m in modelos:
                if m.lower() == self.modelo.lower():
                    self._modelo_resuelto = m
                    _modelo_cache[base] = m
                    _modelo_cache_ts = now
                    return m
            for m in modelos:
                if m.lower().startswith(base):
                    self._modelo_resuelto = m
                    _modelo_cache[base] = m
                    _modelo_cache_ts = now
                    logger.info(f'Modelo resuelto: {self.modelo} → {m}')
                    return m
        except Exception:
            pass

        self._modelo_resuelto = self.modelo
        return self.modelo

    # ── Conectividad ────────────────────────────────────────────────────────

    def test_connection(self) -> dict:
        """
        Verifica que Ollama esté corriendo y lista los modelos instalados.

        Returns:
            {
                'ok': bool,
                'modelos': list[str],        # nombres completos (ej: "llama3.2:latest")
                'modelo_activo': bool,       # si config.ia_modelo está instalado
                'error': str | None,
            }
        """
        try:
            resp = requests.get(
                f'{self.endpoint}/api/tags',
                timeout=TIMEOUT_TEST,
            )
            resp.raise_for_status()
            data = resp.json()
            modelos = [m['name'] for m in data.get('models', [])]
            # Verificar si el modelo configurado está disponible
            base = self.modelo.split(':')[0].lower()
            modelo_activo = any(m.lower().startswith(base) for m in modelos)
            return {
                'ok': True,
                'modelos': modelos,
                'modelo_activo': modelo_activo,
                'error': None,
            }
        except requests.exceptions.ConnectionError:
            return {
                'ok': False,
                'modelos': [],
                'modelo_activo': False,
                'error': (
                    f'No se puede conectar a Ollama en {self.endpoint}. '
                    '¿Está corriendo? Ejecuta: ollama serve'
                ),
            }
        except requests.exceptions.Timeout:
            return {
                'ok': False,
                'modelos': [],
                'modelo_activo': False,
                'error': f'Timeout al conectar con {self.endpoint}.',
            }
        except Exception as e:
            return {
                'ok': False,
                'modelos': [],
                'modelo_activo': False,
                'error': str(e),
            }

    # ── Generación de texto ─────────────────────────────────────────────────

    def generate(self, prompt: str, system: str | None = None) -> str | None:
        """
        Genera texto (single-turn) usando /api/generate.
        No hace streaming — espera la respuesta completa.

        Returns: texto generado, o None si falla.
        """
        modelo = self._resolver_modelo()
        payload: dict = {
            'model': modelo,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.1,   # determinístico para mapeos
                'num_predict': 300,
            },
        }
        if system:
            payload['system'] = system

        try:
            resp = requests.post(
                f'{self.endpoint}/api/generate',
                json=payload,
                timeout=TIMEOUT_GENERAR,
            )
            resp.raise_for_status()
            return resp.json().get('response', '').strip()
        except requests.exceptions.Timeout:
            logger.warning(
                f'Ollama generate timeout (>{TIMEOUT_GENERAR}s) '
                f'en {self.endpoint} modelo={self.modelo}'
            )
            return None
        except Exception as e:
            logger.warning(f'Ollama generate falló: {e}')
            return None

    def chat(self, messages: list, system: str | None = None) -> str | None:
        """
        Chat multi-turno usando /api/chat.
        messages: [{"role": "user"|"assistant", "content": "..."}]

        Returns: texto de la respuesta del asistente, o None si falla.
        """
        modelo = self._resolver_modelo()
        payload: dict = {
            'model': modelo,
            'messages': messages,
            'stream': False,
            'options': {
                'temperature': 0.1,
                'num_predict': 300,
            },
        }
        if system:
            payload['system'] = system

        try:
            resp = requests.post(
                f'{self.endpoint}/api/chat',
                json=payload,
                timeout=TIMEOUT_GENERAR,
            )
            resp.raise_for_status()
            return resp.json().get('message', {}).get('content', '').strip()
        except requests.exceptions.Timeout:
            logger.warning(
                f'Ollama chat timeout (>{TIMEOUT_GENERAR}s) '
                f'en {self.endpoint} modelo={self.modelo}'
            )
            return None
        except Exception as e:
            logger.warning(f'Ollama chat falló: {e}')
            return None

    # ── Streaming ─────────────────────────────────────────────────────────

    def chat_stream(
        self,
        messages: list,
        system: str | None = None,
        temperature: float = 0.3,
        num_predict: int = 500,
    ):
        """
        Chat multi-turno con streaming via /api/chat.
        Yields chunks de texto a medida que llegan de Ollama.
        Raises en caso de error (el caller decide qué hacer).
        """
        modelo = self._resolver_modelo()
        payload: dict = {
            'model': modelo,
            'messages': messages,
            'stream': True,
            'options': {
                'temperature': temperature,
                'num_predict': num_predict,
            },
        }
        if system:
            payload['system'] = system

        try:
            resp = requests.post(
                f'{self.endpoint}/api/chat',
                json=payload,
                timeout=TIMEOUT_GENERAR,
                stream=True,
            )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    content = data.get('message', {}).get('content', '')
                    if content:
                        yield content
                    if data.get('done', False):
                        break
        except Exception as e:
            logger.warning(f'Ollama chat_stream falló: {e}')
            raise ConnectionError(f'Ollama chat_stream: {e}') from e

    def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
        num_predict: int = 500,
    ):
        """
        Generación single-turn con streaming via /api/generate.
        Yields chunks de texto a medida que llegan.
        """
        modelo = self._resolver_modelo()
        payload: dict = {
            'model': modelo,
            'prompt': prompt,
            'stream': True,
            'options': {
                'temperature': temperature,
                'num_predict': num_predict,
            },
        }
        if system:
            payload['system'] = system

        try:
            resp = requests.post(
                f'{self.endpoint}/api/generate',
                json=payload,
                timeout=TIMEOUT_GENERAR,
                stream=True,
            )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    content = data.get('response', '')
                    if content:
                        yield content
                    if data.get('done', False):
                        break
        except Exception as e:
            logger.warning(f'Ollama generate_stream falló: {e}')
            raise ConnectionError(f'Ollama generate_stream: {e}') from e

    # ── Casos de uso RRHH ───────────────────────────────────────────────────

    def mapear_columnas(
        self,
        columnas: list[str],
        campos_target: list[str],
    ) -> dict[str, str]:
        """
        Detecta qué columna del archivo corresponde a cada campo RRHH.

        El LLM analiza los encabezados del Excel y los mapea a los nombres
        canónicos que el sistema entiende (dni, nombre, fecha, etc.).

        Args:
            columnas:      Nombres de columna del archivo (ej: ['Apellidos', 'Nro. Doc.'])
            campos_target: Campos que necesitamos (ej: ['dni', 'nombre'])

        Returns:
            dict campo_canónico → nombre_columna_excel
            Ej: {'dni': 'Nro. Doc.', 'nombre': 'Apellidos'}
        """
        if not columnas or not campos_target:
            return {}

        # Construir descripción legible de los campos objetivo
        descripciones = '\n'.join(
            f'- "{c}": {_CAMPO_DESCRIPCION.get(c, c)}'
            for c in campos_target
        )

        prompt = (
            f'Tengo un archivo Excel con las siguientes columnas:\n'
            f'{json.dumps(columnas, ensure_ascii=False)}\n\n'
            f'Necesito mapear estas columnas a los siguientes campos:\n'
            f'{descripciones}\n\n'
            f'Responde ÚNICAMENTE con un objeto JSON válido, sin ningún texto adicional.\n'
            f'Formato exacto: {{"campo": "nombre_columna_excel"}}\n'
            f'Reglas:\n'
            f'  1. Solo incluye los campos que puedas identificar con certeza.\n'
            f'  2. Los valores deben ser el nombre exacto de la columna del archivo.\n'
            f'  3. Si no encuentras un campo, omítelo del JSON.\n'
            f'  4. No inventes columnas que no estén en la lista.'
        )

        system = (
            'Eres un asistente especializado en datos de RRHH y planillas peruanas. '
            'Tu única función es identificar columnas de archivos Excel. '
            'Respondes ÚNICAMENTE con JSON válido, sin texto adicional, '
            'sin comillas extra, sin explicaciones.'
        )

        respuesta = self.generate(prompt, system=system)
        if not respuesta:
            logger.debug('mapear_columnas: Ollama no devolvió respuesta')
            return {}

        # Extraer JSON de la respuesta (puede venir con texto extra)
        try:
            match = re.search(r'\{[^{}]+\}', respuesta, re.DOTALL)
            if match:
                mapping = json.loads(match.group())
                # Validar: solo devolver los que realmente existen
                valido = {
                    k: v for k, v in mapping.items()
                    if isinstance(k, str)
                    and isinstance(v, str)
                    and k in campos_target
                    and v in columnas
                }
                logger.info(f'IA mapeó columnas: {valido}')
                return valido
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(
                f'Error parseando JSON de IA: {e}\n'
                f'Respuesta recibida: {respuesta[:200]}'
            )

        return {}

    def resumir_texto(self, texto: str, max_palabras: int = 80) -> str | None:
        """
        Resume un texto en español en máximo `max_palabras` palabras.
        Útil para síntesis de feedback en evaluaciones o encuestas.
        """
        prompt = (
            f'Resume el siguiente texto en máximo {max_palabras} palabras, '
            f'en español, conservando los puntos clave:\n\n{texto}'
        )
        return self.generate(prompt)

    def clasificar_falta(self, descripcion: str) -> str | None:
        """
        Sugiere el tipo de falta disciplinaria según la descripción del hecho.
        Returns: nombre del tipo de falta, o None.
        """
        prompt = (
            'Según el DS 003-97-TR (Perú), clasifica la siguiente situación '
            'en uno de estos tipos de falta: ABANDONO_TRABAJO, INCUMPLIMIENTO_TAREAS, '
            'FALTA_HONESTIDAD, HOSTIGAMIENTO, OTRAS_FALTAS, GRAVE_CONDUCTA, INJURIA.\n\n'
            f'Situación: {descripcion}\n\n'
            'Responde ÚNICAMENTE con el nombre del tipo de falta, sin explicaciones.'
        )
        return self.generate(prompt)


# ═══════════════════════════════════════════════════════════════════════════
# Funciones de conveniencia — usan ConfiguracionSistema automáticamente
# ═══════════════════════════════════════════════════════════════════════════

_service_cache: dict = {'svc': None, 'ts': 0, 'key': ''}
_SERVICE_CACHE_TTL = 60  # re-read config every 60s


def get_service() -> OllamaService | None:
    """
    Devuelve un OllamaService configurado desde ConfiguracionSistema.
    Returns None si ia_provider != 'OLLAMA'.
    Usa cache de 60s para no re-leer config en cada request.
    """
    global _service_cache
    now = time.time()
    if (now - _service_cache['ts'] < _SERVICE_CACHE_TTL
            and _service_cache['svc'] is not None):
        return _service_cache['svc']

    try:
        from asistencia.models import ConfiguracionSistema
        config = ConfiguracionSistema.get()
        if config.ia_provider == 'OLLAMA':
            key = f'{config.ia_endpoint}|{config.ia_modelo}'
            # Re-use existing instance if config unchanged
            if key == _service_cache['key'] and _service_cache['svc']:
                _service_cache['ts'] = now
                return _service_cache['svc']

            svc = OllamaService(
                endpoint=config.ia_endpoint or 'http://localhost:11434',
                modelo=config.ia_modelo or 'llama3.2',
            )
            _service_cache.update(svc=svc, ts=now, key=key)
            return svc
    except Exception as e:
        logger.debug(f'get_service: {e}')

    _service_cache.update(svc=None, ts=now, key='')
    return None


def ia_disponible() -> bool:
    """
    ¿Está la IA habilitada en configuración Y el servidor Ollama responde?
    Hace una llamada de red real (usar con moderación).
    """
    svc = get_service()
    if svc is None:
        return False
    return svc.test_connection()['ok']


def mapear_columnas_ia(
    columnas: list[str],
    campos_target: list[str],
) -> dict[str, str]:
    """
    Wrapper de conveniencia para mapeo de columnas.
    Solo actúa si ia_mapeo_activo=True en configuración.
    Returns {} si la IA no está disponible, no está activa, o falla.
    """
    try:
        from asistencia.models import ConfiguracionSistema
        config = ConfiguracionSistema.get()
        if not config.ia_mapeo_activo:
            return {}
        svc = get_service()
        if svc is None:
            return {}
        return svc.mapear_columnas(columnas, campos_target)
    except Exception as e:
        logger.warning(f'mapear_columnas_ia: {e}')
        return {}
