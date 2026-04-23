"""
Vistas IA para Reglas Especiales de Asistencia.

Flujo conversacional (similar a contratos/plantillas):
  1. Usuario describe excepción en lenguaje natural
  2. IA pregunta clarificaciones
  3. IA propone regla estructurada [RULE_PROPOSAL]{json}[/RULE_PROPOSAL]
  4. Frontend muestra preview de impacto
  5. Usuario confirma → se crea ReglaEspecialPersonal
"""
import json as _json
import re
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods

from personal.models import Personal
from asistencia.models import ReglaEspecialPersonal, RegistroTareo


CODIGOS_VALIDOS = [
    'T', 'A', 'NOR', 'DL', 'DLA', 'FA', 'DS', 'SS', 'FER',
    'VAC', 'DM', 'LCG', 'LSG', 'LF', 'LP', 'CHE', 'CDT', 'CPF',
    'TR', 'ATM', 'SAI',
]

DIAS_NOMBRE = {
    0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves',
    4: 'Viernes', 5: 'Sábado', 6: 'Domingo',
}

SYSTEM_PROMPT = """Eres el asistente de Reglas de Asistencia de Harmoni ERP.
Tu trabajo es ayudar a consultar, configurar y gestionar reglas especiales de asistencia para empleados.

CAPACIDADES:
- Puedes VER las reglas existentes del empleado (se proporcionan en el contexto)
- Puedes VER la asistencia reciente (últimos 30 días) del empleado
- Puedes CREAR nuevas reglas proponiendo un [RULE_PROPOSAL]
- Puedes RESPONDER preguntas sobre la asistencia, patrones, anomalías del empleado
- Puedes SUGERIR reglas basándote en los patrones que observes en la asistencia

CÓDIGOS DE ASISTENCIA disponibles:
- T / A / NOR = Día trabajado
- DL / DLA = Día libre / Día libre acumulado
- FA = Falta
- DS = Descanso semanal
- SS = Sin salida (marcó entrada pero no salida)
- FER = Feriado no laborado
- VAC = Vacaciones
- DM = Descanso médico
- LCG = Licencia con goce
- LSG = Licencia sin goce
- CHE = Compensación de horas extra
- CDT = Compensación día trabajado
- CPF = Compensación feriado
- TR = Trabajo remoto

CONDICIONES LABORALES:
- LOCAL = Jornada fija en sede (L-V 8.5h, Sáb 5.5h)
- FORÁNEO = Régimen acumulativo (21×7, 14×7, etc.)
- LIMA = Similar a LOCAL

DÍAS DE LA SEMANA (valores numéricos):
0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes, 5=Sábado, 6=Domingo

REGLAS DE NEGOCIO:
- Las reglas se evalúan DESPUÉS de papeletas y ANTES de feriados/biométrico
- Una regla aplica cuando TODAS sus condiciones se cumplen (AND lógico)
- Campos vacíos = acepta cualquier valor (comodín)
- La primera regla que matchea (por prioridad) gana

INSTRUCCIONES:
1. Escucha la descripción del usuario sobre la excepción del empleado
2. Si algo no está claro, pregunta BREVEMENTE (máximo 1 pregunta por turno)
3. Cuando tengas suficiente información, propón la regla usando este formato exacto:

[RULE_PROPOSAL]
{
  "dias_semana": [5],
  "condicion_laboral": "",
  "codigo_reloj_trigger": "",
  "solo_feriados": false,
  "codigo_resultado": "DL",
  "horas_override": null,
  "fecha_desde": "2026-01-01",
  "fecha_hasta": null,
  "descripcion": "Sábados siempre DL por régimen 21×7",
  "aplicar_retroactivamente": false
}
[/RULE_PROPOSAL]

4. Después del JSON, explica brevemente qué hará la regla
5. Responde SIEMPRE en español, sé conciso y profesional
6. Si el usuario pide modificar la propuesta, emite un nuevo [RULE_PROPOSAL] actualizado"""


@login_required
@require_POST
def chat_regla(request):
    """Chat conversacional con IA para crear/modificar reglas de asistencia."""
    try:
        data = _json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    pregunta = data.get('message', '').strip()
    personal_id = data.get('personal_id')
    historial = data.get('historial', [])

    if not pregunta:
        return JsonResponse({'ok': False, 'error': 'Mensaje vacío'})
    if not personal_id:
        return JsonResponse({'ok': False, 'error': 'personal_id requerido'})

    personal = get_object_or_404(Personal, pk=personal_id)

    # Obtener servicio IA
    from asistencia.services.ai_service import get_service
    svc = get_service()
    if not svc:
        return JsonResponse({
            'ok': False,
            'error': 'No hay servicio de IA configurado. Ir a Configuración > IA.',
        })

    # ── Contexto rico del empleado ──────────────────────
    # 1. Datos personales
    contexto_empleado = (
        f'\nEMPLEADO: {personal.apellidos_nombres}'
        f'\nDNI: {personal.nro_doc}'
        f'\nCargo: {personal.cargo or "—"}'
        f'\nCondición: {personal.condicion or "—"}'
        f'\nGrupo: {personal.grupo_tareo or "—"}'
        f'\nRégimen turno: {personal.regimen_turno or "—"}'
        f'\nEstado: {personal.estado or "—"}'
        f'\nFecha alta: {personal.fecha_alta or "—"}'
    )

    # 2. Reglas existentes (activas e inactivas)
    reglas_all = list(
        ReglaEspecialPersonal.objects
        .filter(personal=personal)
        .order_by('prioridad')
        .values('id', 'descripcion', 'codigo_resultado', 'dias_semana',
                'condicion_laboral', 'activa', 'fecha_desde', 'fecha_hasta',
                'solo_feriados', 'codigo_reloj_trigger', 'prioridad')
    )
    if reglas_all:
        contexto_empleado += '\n\nREGLAS ESPECIALES CONFIGURADAS:'
        for r in reglas_all:
            dias = ', '.join(DIAS_NOMBRE.get(d, '?') for d in (r['dias_semana'] or [])) or 'todos'
            estado = 'ACTIVA' if r['activa'] else 'INACTIVA'
            contexto_empleado += (
                f'\n  [{estado}] ID:{r["id"]} | {r["descripcion"]} '
                f'→ código {r["codigo_resultado"]} (días: {dias}) '
                f'| prioridad: {r["prioridad"]} '
                f'| desde: {r["fecha_desde"]} hasta: {r["fecha_hasta"] or "∞"}'
            )
            if r['condicion_laboral']:
                contexto_empleado += f' | condición: {r["condicion_laboral"]}'
            if r['codigo_reloj_trigger']:
                contexto_empleado += f' | trigger: {r["codigo_reloj_trigger"]}'
            if r['solo_feriados']:
                contexto_empleado += ' | solo feriados'
    else:
        contexto_empleado += '\n\nREGLAS ESPECIALES: Ninguna configurada.'

    # 3. Asistencia reciente (últimos 30 días)
    from datetime import timedelta as _td
    hoy = date.today()
    asistencia_reciente = list(
        RegistroTareo.objects
        .filter(personal=personal, fecha__gte=hoy - _td(days=30), fecha__lte=hoy)
        .order_by('fecha')
        .values('fecha', 'dia_semana', 'codigo_dia', 'condicion',
                'horas_efectivas', 'horas_normales', 'he_100',
                'fuente_codigo', 'es_feriado')
    )
    if asistencia_reciente:
        contexto_empleado += '\n\nASISTENCIA ÚLTIMOS 30 DÍAS:'
        contexto_empleado += '\nFecha       Día  Cód   Cond     HEfec  HNorm  HE100  Fuente'
        for a in asistencia_reciente:
            ds = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
            dia = ds[a['dia_semana']] if a['dia_semana'] is not None else '?'
            fer = ' [FER]' if a['es_feriado'] else ''
            contexto_empleado += (
                f'\n{a["fecha"]} {dia:<3}{fer} '
                f'{(a["codigo_dia"] or "—"):<5} '
                f'{(a["condicion"] or "—"):<8} '
                f'{float(a["horas_efectivas"] or 0):5.1f}  '
                f'{float(a["horas_normales"] or 0):5.1f}  '
                f'{float(a["he_100"] or 0):5.1f}  '
                f'{a["fuente_codigo"] or "—"}'
            )
    else:
        contexto_empleado += '\n\nASISTENCIA: Sin registros en los últimos 30 días.'

    # Construir prompt con historial
    prompt_parts = [contexto_empleado]
    for msg in historial[-6:]:
        role = msg.get('role', 'user')
        content = msg.get('content', '')[:500]
        if role == 'user':
            prompt_parts.append('USUARIO: ' + content)
        else:
            prompt_parts.append('ASISTENTE: ' + content)
    prompt_parts.append('USUARIO: ' + pregunta)
    prompt = '\n\n'.join(prompt_parts)

    try:
        resultado = svc.generate(prompt, system=SYSTEM_PROMPT)
        if not resultado:
            return JsonResponse({'ok': False, 'error': 'La IA no devolvió resultado.'})

        # Extraer regla propuesta si existe
        regla_propuesta = None
        respuesta_limpia = resultado
        match = re.search(
            r'\[RULE_PROPOSAL\]\s*(\{.*?\})\s*\[/RULE_PROPOSAL\]',
            resultado, re.DOTALL
        )
        if match:
            try:
                regla_propuesta = _json.loads(match.group(1))
                # Limpiar la respuesta: quitar el bloque JSON
                respuesta_limpia = resultado[:match.start()].strip()
                texto_despues = resultado[match.end():].strip()
                if texto_despues:
                    respuesta_limpia += '\n\n' + texto_despues
                if not respuesta_limpia:
                    respuesta_limpia = 'He generado una propuesta de regla. Revisa los detalles y confirma.'
            except _json.JSONDecodeError:
                pass  # JSON inválido, ignorar

        response_data = {'ok': True, 'respuesta': respuesta_limpia}
        if regla_propuesta:
            response_data['regla_propuesta'] = regla_propuesta

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error de IA: {str(e)[:200]}'})


@login_required
@require_POST
def preview_regla(request):
    """Vista previa: muestra cómo afectaría una regla a los registros existentes."""
    try:
        data = _json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    personal_id = data.get('personal_id')
    regla_json = data.get('regla')
    if not personal_id or not regla_json:
        return JsonResponse({'ok': False, 'error': 'personal_id y regla requeridos'})

    personal = get_object_or_404(Personal, pk=personal_id)

    # Crear regla temporal (sin guardar) para evaluar
    from asistencia.models import ConfiguracionSistema, FeriadoCalendario
    feriados = set(FeriadoCalendario.objects.filter(activo=True).values_list('fecha', flat=True))

    dias_semana = regla_json.get('dias_semana', [])
    condicion_lab = regla_json.get('condicion_laboral', '')
    codigo_trigger = regla_json.get('codigo_reloj_trigger', '')
    solo_fer = regla_json.get('solo_feriados', False)
    fecha_desde_str = regla_json.get('fecha_desde', str(date.today()))
    fecha_hasta_str = regla_json.get('fecha_hasta')
    codigo_res = regla_json.get('codigo_resultado', '')

    try:
        fecha_desde = date.fromisoformat(fecha_desde_str) if fecha_desde_str else date.today()
    except ValueError:
        fecha_desde = date.today()
    try:
        fecha_hasta = date.fromisoformat(fecha_hasta_str) if fecha_hasta_str else None
    except ValueError:
        fecha_hasta = None

    # Rango de evaluación: últimos 90 días (o desde fecha_desde si es más reciente)
    rango_fin = date.today()
    rango_ini = max(fecha_desde, rango_fin - timedelta(days=90))

    registros = RegistroTareo.objects.filter(
        personal=personal,
        fecha__gte=rango_ini,
        fecha__lte=rango_fin,
    ).order_by('fecha').values(
        'fecha', 'dia_semana', 'condicion', 'codigo_dia', 'fuente_codigo', 'es_feriado'
    )

    cambios = []
    for reg in registros:
        # Evaluar si la regla aplica
        f = reg['fecha']
        ds = reg['dia_semana'] if reg['dia_semana'] is not None else f.weekday()
        cond = reg['condicion'] or ''
        cod_actual = reg['codigo_dia'] or ''
        es_fer = reg['es_feriado'] or (f in feriados)

        # Verificar condiciones
        if dias_semana and ds not in dias_semana:
            continue
        if condicion_lab:
            cn = cond.upper().replace('\xc1', 'A')
            rn = condicion_lab.upper().replace('\xc1', 'A')
            if cn != rn:
                continue
        if codigo_trigger and cod_actual.upper() != codigo_trigger.upper():
            continue
        if solo_fer and not es_fer:
            continue
        if fecha_hasta and f > fecha_hasta:
            continue
        if f < fecha_desde:
            continue

        # Solo agregar si realmente cambia algo
        if cod_actual != codigo_res:
            dia_nombre = DIAS_NOMBRE.get(ds, '?')
            cambios.append({
                'fecha': f.isoformat(),
                'dia': dia_nombre,
                'fecha_display': f.strftime('%d/%m/%Y'),
                'codigo_actual': cod_actual,
                'codigo_nuevo': codigo_res,
                'fuente_actual': reg['fuente_codigo'],
            })

    return JsonResponse({
        'ok': True,
        'total_afectados': len(cambios),
        'cambios': cambios[:50],  # Max 50 para no sobrecargar
        'hay_mas': len(cambios) > 50,
    })


@login_required
@require_POST
def confirmar_regla(request):
    """Crea la ReglaEspecialPersonal confirmada y opcionalmente aplica retroactivamente."""
    try:
        data = _json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    personal_id = data.get('personal_id')
    regla_json = data.get('regla')
    conversacion = data.get('conversacion', [])
    aplicar_retro = data.get('aplicar_retroactivamente', False)

    if not personal_id or not regla_json:
        return JsonResponse({'ok': False, 'error': 'personal_id y regla requeridos'})

    personal = get_object_or_404(Personal, pk=personal_id)

    # Validar código resultado
    codigo_res = regla_json.get('codigo_resultado', '').upper().strip()
    if not codigo_res:
        return JsonResponse({'ok': False, 'error': 'codigo_resultado es obligatorio'})

    # Parsear fechas
    try:
        fecha_desde = date.fromisoformat(regla_json.get('fecha_desde', str(date.today())))
    except ValueError:
        fecha_desde = date.today()
    try:
        fecha_hasta_str = regla_json.get('fecha_hasta')
        fecha_hasta = date.fromisoformat(fecha_hasta_str) if fecha_hasta_str else None
    except (ValueError, TypeError):
        fecha_hasta = None

    # Horas override
    horas_ov = regla_json.get('horas_override')
    if horas_ov is not None:
        try:
            horas_ov = Decimal(str(horas_ov))
        except Exception:
            horas_ov = None

    # Crear la regla
    regla = ReglaEspecialPersonal.objects.create(
        personal=personal,
        dias_semana=regla_json.get('dias_semana', []),
        condicion_laboral=regla_json.get('condicion_laboral', ''),
        codigo_reloj_trigger=regla_json.get('codigo_reloj_trigger', ''),
        solo_feriados=regla_json.get('solo_feriados', False),
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        codigo_resultado=codigo_res,
        horas_override=horas_ov,
        descripcion=regla_json.get('descripcion', f'Regla: {codigo_res}')[:300],
        descripcion_natural=regla_json.get('descripcion_natural', '')[:2000],
        conversacion_ia=conversacion[-20:] if conversacion else [],
        prioridad=regla_json.get('prioridad', 10),
        activa=True,
        aplicar_retroactivamente=aplicar_retro,
        creado_por=request.user,
    )

    # Aplicar retroactivamente si se solicita
    registros_actualizados = 0
    if aplicar_retro:
        registros_actualizados = _aplicar_regla_retroactiva(regla, personal)

    return JsonResponse({
        'ok': True,
        'regla_id': regla.pk,
        'registros_actualizados': registros_actualizados,
    })


def _aplicar_regla_retroactiva(regla, personal):
    """Aplica la regla a registros existentes que matcheen."""
    from asistencia.models import FeriadoCalendario
    feriados = set(FeriadoCalendario.objects.filter(activo=True).values_list('fecha', flat=True))

    rango_fin = date.today()
    rango_ini = max(regla.fecha_desde, rango_fin - timedelta(days=90))

    registros = RegistroTareo.objects.filter(
        personal=personal,
        fecha__gte=rango_ini,
        fecha__lte=rango_fin,
    ).select_related('personal')

    to_update = []
    for reg in registros:
        ds = reg.dia_semana if reg.dia_semana is not None else reg.fecha.weekday()
        es_fer = reg.es_feriado or (reg.fecha in feriados)
        codigo_reloj = reg.codigo_dia or ''

        if regla.aplica_a(reg.fecha, ds, reg.condicion or '', codigo_reloj, es_fer):
            if reg.codigo_dia != regla.codigo_resultado:
                reg.codigo_dia = regla.codigo_resultado
                reg.fuente_codigo = 'REGLA_ESPECIAL'
                to_update.append(reg)

    if to_update:
        RegistroTareo.objects.bulk_update(
            to_update, ['codigo_dia', 'fuente_codigo'], batch_size=200
        )

    return len(to_update)


@login_required
@require_POST
def toggle_regla(request, pk):
    """Activa/desactiva una regla."""
    regla = get_object_or_404(ReglaEspecialPersonal, pk=pk)
    regla.activa = not regla.activa
    regla.save(update_fields=['activa', 'actualizado_en'])
    return JsonResponse({
        'ok': True,
        'activa': regla.activa,
    })


@login_required
@require_http_methods(['DELETE', 'POST'])
def delete_regla(request, pk):
    """Elimina una regla."""
    regla = get_object_or_404(ReglaEspecialPersonal, pk=pk)
    regla.delete()
    return JsonResponse({'ok': True})
