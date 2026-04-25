"""
Helpers compartidos entre el processor (importación) y _recalcular_horas
(edición manual via UI). Garantizan que ambos paths usen la MISMA lógica.

NOTA IMPORTANTE: cualquier regla de cálculo aquí debe ser idéntica en
ambos contextos para evitar divergencias entre lo que se importa y lo
que se edita manualmente.
"""
from __future__ import annotations

from decimal import Decimal

from asistencia.services.processor import (
    redondear_media_hora as _redondear_media_hora,
)

CERO = Decimal('0')
HORAS_MAX_DIA = Decimal('16')  # tope sanitario (D.S. 007-2002-TR jornada legal 12h + buffer)


# Re-export para que callers usen un único path
redondear_media_hora = _redondear_media_hora


def calcular_almuerzo_h(
    horas_marcadas: Decimal,
    jornada_h: Decimal,
    almuerzo_manual: Decimal | None,
) -> Decimal:
    """
    Devuelve la cantidad de horas a descontar por refrigerio/almuerzo.

    Reglas:
      - Si almuerzo_manual fue seteado (override admin), prioridad absoluta.
      - Auto: 1h cuando horas_marcadas > 7 Y jornada_h > 6
        (excluye sábado LOCAL 5.5h y domingos donde el almuerzo no aplica).
    """
    if almuerzo_manual is not None:
        return Decimal(str(almuerzo_manual))
    if horas_marcadas > Decimal('7') and jornada_h > Decimal('6'):
        return Decimal('1')
    return CERO


def cap_horas_dia(horas: Decimal, dni: str | None = None,
                  fecha=None, logger=None) -> Decimal:
    """
    Limita horas marcadas a HORAS_MAX_DIA. Avisa si supera el tope.
    """
    if horas > HORAS_MAX_DIA:
        if logger:
            logger.warning(
                'Horas sospechosas (%sh) para DNI %s en %s. Se usará máximo %sh.',
                horas, dni or '?', fecha or '?', HORAS_MAX_DIA,
            )
        return HORAS_MAX_DIA
    return horas


def fecha_en_periodo_cerrado(fecha) -> bool:
    """
    True si (fecha.year, fecha.month) tiene un PeriodoCierre con estado=CERRADO.
    """
    from cierre.models import PeriodoCierre
    return PeriodoCierre.objects.filter(
        anio=fecha.year, mes=fecha.month, estado='CERRADO',
    ).exists()


def calcular_horas_marcadas_desde_horarios(
    fecha,
    hora_entrada,
    hora_salida,
    horas_marcadas_fallback: Decimal | None = None,
) -> Decimal:
    """
    Calcula horas marcadas desde entrada/salida.

    Reglas:
      - entrada == salida → 0h (caso "limpiar" o sin trabajo).
      - salida < entrada → turno overnight (suma 1 día).
      - Si no hay entrada/salida, usa horas_marcadas_fallback (puede ser None).

    Devuelve siempre Decimal redondeado a 0.5h con gracia de 7 minutos.
    """
    from datetime import datetime, timedelta
    from decimal import ROUND_FLOOR

    if hora_entrada and hora_salida:
        if hora_entrada == hora_salida:
            return CERO
        entrada_dt = datetime.combine(fecha, hora_entrada)
        salida_dt = datetime.combine(fecha, hora_salida)
        if salida_dt < entrada_dt:
            salida_dt += timedelta(days=1)
        diff = Decimal(str((salida_dt - entrada_dt).total_seconds() / 3600))
        # Gracia de 7 min: redondeo "amigable" hacia abajo después de empujar
        gracia = Decimal('7') / 60
        return ((diff + gracia) * 2).to_integral_value(
            rounding=ROUND_FLOOR
        ) / 2
    if horas_marcadas_fallback is not None and horas_marcadas_fallback > CERO:
        return Decimal(str(horas_marcadas_fallback))
    return CERO
