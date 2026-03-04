"""
Vistas de inicio y logout.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, timedelta
from django.db.models import Count, Q, Sum

from ..models import Area, SubArea, Personal, Roster
from ..permissions import (
    filtrar_areas, filtrar_subareas, filtrar_personal,
    get_context_usuario
)


# ── Frase del día ──────────────────────────────────────────────────────────────

def _get_frase_dia(hoy: date) -> dict:
    """
    Retorna una frase contextual según el calendario laboral peruano.
    Prioriza eventos próximos; si no hay ninguno, usa sabiduría RRHH
    rotatoria por día del año.
    """
    # ── 1. Calcular Día de la Madre y Padre (domingos móviles) ────────────
    def _nth_sunday(year, month, n):
        """Retorna el n-ésimo domingo del mes/año (1-based)."""
        d = date(year, month, 1)
        d += timedelta(days=(6 - d.weekday()) % 7)  # primer domingo
        return d + timedelta(weeks=n - 1)

    dia_madre = _nth_sunday(hoy.year, 5, 2)   # 2.° domingo de mayo
    dia_padre = _nth_sunday(hoy.year, 6, 3)   # 3.° domingo de junio

    # ── 2. Catálogo de eventos ────────────────────────────────────────────
    # Cada entrada: (fecha, ventana_antes, ventana_despues, nombre, frases, icono, color)
    EVENTOS = [
        (date(hoy.year, 1, 1), 3, 2,
         "Año Nuevo",
         [f"Año nuevo, mismo gran equipo — con metas aún más altas. ¡Bienvenidos al {hoy.year}!",
          "El inicio del año es el mejor momento para renovar el compromiso con las personas."],
         "fa-star", "#0f766e"),

        (date(hoy.year, 3, 8), 10, 2,
         "Día Internacional de la Mujer",
         ["La equidad de género no se declara, se construye todos los días. Hoy lo celebramos.",
          "Nuestras colaboradoras mueven el mundo. Hoy es el momento perfecto para reconocerlo.",
          "Una organización que valora a sus mujeres, valora su futuro."],
         "fa-venus", "#db2777"),

        (date(hoy.year, 5, 1), 14, 3,
         "Día del Trabajador",
         ["El 1° de mayo nos recuerda que detrás de cada indicador hay una historia humana. ¡Celebremos al equipo!",
          "Se acerca el día más importante del calendario laboral — ¡estoy emocionado de planear la celebración!",
          "El trabajo no solo construye empresas, construye personas. ¡Feliz Día del Trabajador!",
          "El mejor homenaje al Día del Trabajo es escuchar a nuestro equipo. ¿Ya tienes algo planeado?"],
         "fa-hard-hat", "#d97706"),

        (dia_madre, 10, 1,
         "Día de la Madre",
         ["Muchas de nuestras colaboradoras son madres. Hoy es el día de reconocer esa fortaleza doble.",
          "El mejor beneficio que podemos dar es flexibilidad para quienes además son mamás. ¡Feliz día!"],
         "fa-heart", "#ec4899"),

        (dia_padre, 7, 1,
         "Día del Padre",
         ["A todos los papás del equipo: gracias por la entrega doble, en casa y en el trabajo.",
          "Ser padre y colaborador es un acto de balance diario. Hoy los reconocemos."],
         "fa-child", "#0891b2"),

        (date(hoy.year, 6, 29), 5, 1,
         "San Pedro y San Pablo",
         ["Feriado a la vista — el equipo se lo ha ganado. ¡Que recarguen energías!"],
         "fa-church", "#7c3aed"),

        (date(hoy.year, 7, 28), 12, 3,
         "Fiestas Patrias",
         ["¡Tan peruanos como nuestro equipo! Que disfruten el descanso y vuelvan con energía renovada.",
          "El orgullo de ser peruanos se siente también en cómo tratamos a nuestra gente. ¡Viva el Perú!",
          "Fiestas Patrias: el momento ideal para agradecer al equipo por todo el año."],
         "fa-flag", "#dc2626"),

        (date(hoy.year, 8, 30), 5, 1,
         "Santa Rosa de Lima",
         ["Un feriado más para el equipo. La calidad de vida también se mide en días de descanso bien ganados."],
         "fa-sun", "#d97706"),

        (date(hoy.year, 10, 8), 5, 1,
         "Combate de Angamos",
         ["Recordar nuestra historia nos recuerda quiénes somos como equipo y como país."],
         "fa-anchor", "#0f766e"),

        (date(hoy.year, 11, 1), 4, 1,
         "Día de Todos los Santos",
         ["Un momento para reflexionar y agradecer a quienes nos acompañaron en el camino."],
         "fa-candle-holder", "#6366f1"),

        (date(hoy.year, 12, 9), 5, 1,
         "Batalla de Ayacucho",
         ["La libertad también se construye en las organizaciones, con respeto y oportunidades reales."],
         "fa-shield-alt", "#dc2626"),

        (date(hoy.year, 12, 25), 15, 4,
         "Navidad",
         ["La mejor época del año para agradecer a cada persona del equipo por su entrega y dedicación.",
          "Navidad nos recuerda que las grandes organizaciones se construyen con pequeños gestos de humanidad.",
          "Fin de año: el momento más poderoso para reconocer logros y sembrar expectativas positivas."],
         "fa-snowflake", "#0891b2"),

        (date(hoy.year, 12, 31), 5, 1,
         "Fin de Año",
         ["Un año más de logros y aprendizajes juntos. ¡El balance es positivo!",
          "Cada cierre de año es también un comienzo. ¿Qué historia escribiremos juntos el próximo?"],
         "fa-glass-cheers", "#7c3aed"),
    ]

    # ── 3. Buscar evento próximo o en curso ───────────────────────────────
    # Artículo correcto por evento (default "el")
    _ART = {
        "Fiestas Patrias":          "las",
        "Navidad":                  "la",
        "Batalla de Ayacucho":      "la",
        "Día de la Madre":          "el",
        "San Pedro y San Pablo":    "",
        "Santa Rosa de Lima":       "",
    }
    for (fecha_e, antes, despues, nombre, frases, icono, color) in EVENTOS:
        delta = (fecha_e - hoy).days
        if -despues <= delta <= antes:
            art = _ART.get(nombre, "el")
            nombre_con_art = f"{art} {nombre}".strip()
            if delta > 1:
                comentario = f"Faltan {delta} días para {nombre_con_art}"
            elif delta == 1:
                comentario = f"¡Mañana es {nombre_con_art}!"
            elif delta == 0:
                comentario = f"¡Hoy es {nombre_con_art}!"
            else:
                comentario = f"¡{nombre}!"
            frase = frases[hoy.timetuple().tm_yday % len(frases)]
            return {'evento': nombre, 'comentario': comentario,
                    'frase': frase, 'icono': icono, 'color': color}

    # ── 4. Sin evento especial — sabiduría RRHH rotatoria ─────────────────
    FRASES_RRHH = [
        ("Las personas no son recursos — son el propósito.", "fa-heart", "#0f766e"),
        ("Un equipo comprometido supera cualquier estrategia perfecta.", "fa-handshake", "#0891b2"),
        ("El bienestar del colaborador no es un beneficio, es una inversión.", "fa-seedling", "#059669"),
        ("Contratar bien es el acto de gestión más importante que existe.", "fa-user-check", "#7c3aed"),
        ("La cultura no se declara, se vive en cada decisión pequeña.", "fa-building", "#0f766e"),
        ("Un 'gracias' a tiempo vale más que cualquier bono.", "fa-award", "#d97706"),
        ("El mejor indicador de clima laboral es cuando la gente llega sonriendo.", "fa-smile", "#10b981"),
        ("Desarrollar personas es la única ventaja que nadie puede copiar.", "fa-chart-line", "#0891b2"),
        ("El onboarding termina cuando la persona se siente verdaderamente en casa.", "fa-home", "#059669"),
        ("La rotación no es un problema de personas — es un espejo de la organización.", "fa-sync-alt", "#ef4444"),
        ("Medir el desempeño sin retroalimentar es como pesar al paciente sin medicarle.", "fa-balance-scale", "#7c3aed"),
        ("Una conversación honesta a tiempo previene una renuncia inesperada.", "fa-comments", "#0f766e"),
        ("El liderazgo no se ejerce desde el cargo, se ejerce desde la confianza.", "fa-user-shield", "#0891b2"),
        ("Diversidad sin inclusión es decoración. Inclusión sin equidad es teatro.", "fa-users", "#059669"),
        ("El error más caro en RRHH es esperar a que alguien bueno se vaya para valorarlo.", "fa-exclamation-circle", "#d97706"),
        ("Flexibilidad no es sinónimo de caos — es sinónimo de confianza.", "fa-random", "#0f766e"),
        ("El salario emocional es lo que hace que la gente se quede cuando otra empresa paga más.", "fa-brain", "#7c3aed"),
        ("Un proceso de selección justo es el primer mensaje cultural que envías.", "fa-clipboard-check", "#0891b2"),
        ("Las políticas rígidas alejan a los mejores y retienen a los más conformistas.", "fa-file-contract", "#ef4444"),
        ("El propósito no se cuelga en una pared — se siente en el trato diario.", "fa-compass", "#059669"),
    ]

    # Día de semana: comentario motivacional
    MOTS_SEMANA = {
        0: "Lunes — el mejor momento para arrancar con intención.",
        1: "Martes — el día más productivo de la semana según la ciencia.",
        2: "Miércoles — mitad del camino, todo el impulso por delante.",
        3: "Jueves — un día más para hacer algo que importe.",
        4: "Viernes — bien hecho esta semana, equipo.",
        5: "Sábado — algunos trabajan hoy también. ¡Gracias!",
        6: "Domingo — mañana volvemos a construir.",
    }

    frase, icono, color = FRASES_RRHH[hoy.timetuple().tm_yday % len(FRASES_RRHH)]
    return {
        'evento': None,
        'comentario': MOTS_SEMANA[hoy.weekday()],
        'frase': frase,
        'icono': icono,
        'color': color,
    }


@login_required
def home(request):
    """Vista principal del sistema — Dashboard contextual."""
    hoy = date.today()

    # Filtros según rol del usuario
    gerencias_filtradas = filtrar_areas(request.user)
    areas_filtradas = filtrar_subareas(request.user)
    personal_filtrado = filtrar_personal(request.user)
    personal_activo = personal_filtrado.filter(estado='Activo')
    total_activos = personal_activo.count()

    # ── KPIs base ──
    _dist = {d['grupo_tareo']: d['n']
             for d in personal_activo.values('grupo_tareo').annotate(n=Count('id'))}
    context = {
        'total_gerencias': gerencias_filtradas.filter(activa=True).count(),
        'total_areas': areas_filtradas.filter(activa=True).count(),
        'total_personal': total_activos,
        'staff_count': _dist.get('STAFF', 0),
        'rco_count':   _dist.get('RCO',   0),
        'total_roster_hoy': Roster.objects.filter(
            fecha=hoy, personal__in=personal_filtrado,
        ).count(),
    }

    # ── Asistencia HOY (solo admin/responsable) ──
    if request.user.is_superuser or gerencias_filtradas.exists():
        from asistencia.models import RegistroTareo
        tareo_hoy = RegistroTareo.objects.filter(
            fecha=hoy, personal__in=personal_activo,
        )
        asistencia_hoy = tareo_hoy.aggregate(
            total=Count('id'),
            # SS = Sin Salida → persona PRESENTE (llegó pero no marcó salida)
            trabajando=Count('id', filter=Q(codigo_dia__in=['T', 'NOR', 'TR', 'SS'])),
            faltas=Count('id', filter=Q(codigo_dia__in=['FA', 'LSG'])),
            permisos=Count('id', filter=Q(codigo_dia__in=[
                'V', 'DL', 'DLA', 'DM', 'LCG', 'LF', 'LP', 'LM',
                'CAP', 'CT', 'CHE', 'CDT', 'CPF', 'ATM',
            ])),
            ss=Count('id', filter=Q(codigo_dia='SS')),  # sub-conteo para nota
        )
        context['asistencia_hoy'] = asistencia_hoy
        context['sin_registro_hoy'] = total_activos - (asistencia_hoy['total'] or 0)

    # ── Papeletas y Solicitudes HE pendientes (este mes) ──
    if request.user.is_superuser or gerencias_filtradas.exists():
        from asistencia.models import RegistroPapeleta, SolicitudHE, JustificacionNoMarcaje

        inicio_mes = hoy.replace(day=1)

        pap_stats = RegistroPapeleta.objects.filter(
            personal__in=personal_activo,
            creado_en__date__gte=inicio_mes,
        ).aggregate(
            total_mes=Count('id'),
            pendientes=Count('id', filter=Q(estado='PENDIENTE')),
        )

        sol_stats = SolicitudHE.objects.filter(
            personal__in=personal_activo,
            creado_en__date__gte=inicio_mes,
        ).aggregate(
            total_mes=Count('id'),
            pendientes=Count('id', filter=Q(estado='PENDIENTE')),
        )

        just_stats = JustificacionNoMarcaje.objects.filter(
            personal__in=personal_activo,
            creado_en__date__gte=inicio_mes,
        ).aggregate(
            total_mes=Count('id'),
            pendientes=Count('id', filter=Q(estado='PENDIENTE')),
        )

        context['pap_stats'] = pap_stats
        context['sol_stats'] = sol_stats
        context['just_stats'] = just_stats

        # ── Actividad reciente (últimos 7 días) ──
        hace_7d = hoy - timedelta(days=7)

        actividad = []

        # Papeletas recientes
        for p in RegistroPapeleta.objects.filter(
            creado_en__date__gte=hace_7d,
            personal__in=personal_activo,
        ).select_related('personal').order_by('-creado_en')[:5]:
            actividad.append({
                'icono': 'fa-file-alt',
                'color': '#0f766e',
                'texto': f'{p.personal.apellidos_nombres if p.personal else "?"} — {p.get_tipo_permiso_display()}',
                'estado': p.estado,
                'estado_display': p.get_estado_display(),
                'fecha': p.creado_en,
                'tipo': 'papeleta',
            })

        # Solicitudes HE recientes
        for s in SolicitudHE.objects.filter(
            creado_en__date__gte=hace_7d,
            personal__in=personal_activo,
        ).select_related('personal').order_by('-creado_en')[:5]:
            actividad.append({
                'icono': 'fa-clock',
                'color': '#7c3aed',
                'texto': f'{s.personal.apellidos_nombres} — HE {s.horas_estimadas}h ({s.get_tipo_display()})',
                'estado': s.estado,
                'estado_display': s.get_estado_display(),
                'fecha': s.creado_en,
                'tipo': 'solicitud_he',
            })

        # Justificaciones recientes
        for j in JustificacionNoMarcaje.objects.filter(
            creado_en__date__gte=hace_7d,
            personal__in=personal_activo,
        ).select_related('personal').order_by('-creado_en')[:5]:
            actividad.append({
                'icono': 'fa-clipboard-check',
                'color': '#ea580c',
                'texto': f'{j.personal.apellidos_nombres} — {j.get_tipo_display()}',
                'estado': j.estado,
                'estado_display': j.get_estado_display(),
                'fecha': j.creado_en,
                'tipo': 'justificacion',
            })

        # ── Préstamos en actividad reciente ──
        try:
            from prestamos.models import Prestamo
            for pr in Prestamo.objects.filter(
                creado_en__date__gte=hace_7d,
                personal__in=personal_activo,
            ).select_related('personal', 'tipo').order_by('-creado_en')[:5]:
                actividad.append({
                    'icono': 'fa-hand-holding-usd',
                    'color': '#7c3aed',
                    'texto': f'{pr.personal.apellidos_nombres} — {pr.tipo.nombre} S/ {pr.monto_efectivo:,.2f}',
                    'estado': pr.estado,
                    'estado_display': pr.get_estado_display(),
                    'fecha': pr.creado_en,
                    'tipo': 'prestamo',
                })
        except Exception:
            pass

        # Ordenar por fecha descendente y limitar
        actividad.sort(key=lambda x: x['fecha'], reverse=True)
        context['actividad_reciente'] = actividad[:8]

    # ── Préstamos stats (si módulo activo) ──
    if request.user.is_superuser:
        try:
            from prestamos.models import Prestamo
            from asistencia.models import ConfiguracionSistema
            config = ConfiguracionSistema.get()
            if config.mod_prestamos:
                prest_stats = Prestamo.objects.filter(
                    personal__in=personal_activo,
                ).aggregate(
                    total=Count('id'),
                    en_curso=Count('id', filter=Q(estado='EN_CURSO')),
                    pendientes=Count('id', filter=Q(estado='PENDIENTE')),
                    saldo_total=Sum('monto_aprobado', filter=Q(estado='EN_CURSO')),
                )
                context['prest_stats'] = prest_stats
        except Exception:
            pass

    # ── Documentos stats (si módulo activo) ──
    if request.user.is_superuser:
        try:
            from documentos.models import DocumentoTrabajador
            from asistencia.models import ConfiguracionSistema
            config = ConfiguracionSistema.get()
            if config.mod_documentos:
                doc_stats = DocumentoTrabajador.objects.filter(
                    personal__in=personal_activo,
                ).aggregate(
                    total=Count('id'),
                    vigentes=Count('id', filter=Q(estado='VIGENTE')),
                    por_vencer=Count('id', filter=Q(estado='POR_VENCER')),
                )
                context['doc_stats'] = doc_stats
        except Exception:
            pass

    # ── Nóminas: último período ──
    if request.user.is_superuser:
        try:
            from nominas.models import PeriodoNomina
            ultimo_periodo = PeriodoNomina.objects.filter(
                tipo='REGULAR', estado__in=['CALCULADO', 'APROBADO', 'CERRADO']
            ).order_by('-anio', '-mes').first()
            context['nominas_stats'] = {
                'periodo':      ultimo_periodo,
                'neto':         ultimo_periodo.total_neto if ultimo_periodo else None,
                'trabajadores': ultimo_periodo.total_trabajadores if ultimo_periodo else 0,
                'estado':       ultimo_periodo.get_estado_display() if ultimo_periodo else None,
            }
        except Exception:
            pass

    # ── Vacaciones y permisos pendientes ──
    if request.user.is_superuser:
        try:
            from vacaciones.models import SolicitudVacacion, SolicitudPermiso
            vac_pend = SolicitudVacacion.objects.filter(
                estado='PENDIENTE', personal__in=personal_activo).count()
            perm_pend = SolicitudPermiso.objects.filter(
                estado='PENDIENTE', personal__in=personal_activo).count()
            context['vacaciones_stats'] = {
                'vac_pendientes':  vac_pend,
                'perm_pendientes': perm_pend,
                'total':           vac_pend + perm_pend,
            }
        except Exception:
            pass

    # ── Contratos por vencer (próximos 30 días) ──
    if request.user.is_superuser:
        try:
            en_30_dias = hoy + timedelta(days=30)
            context['contratos_vencen'] = personal_activo.filter(
                fecha_fin_contrato__isnull=False,
                fecha_fin_contrato__gte=hoy,
                fecha_fin_contrato__lte=en_30_dias,
            ).count()
        except Exception:
            pass

    # ── Workflows pendientes para este usuario ──
    if request.user.is_authenticated:
        try:
            from workflows.services import get_pendientes_usuario
            pendientes_wf = get_pendientes_usuario(request.user)
            context['workflows_pendientes'] = pendientes_wf.count()
        except Exception:
            pass

    # ── Alertas RRHH activas (admin) ──
    if request.user.is_superuser:
        try:
            from analytics.models import AlertaRRHH
            alertas_activas = AlertaRRHH.objects.filter(activa=True)
            context['alertas_rrhh_total'] = alertas_activas.count()
            context['alertas_rrhh_critical'] = alertas_activas.filter(severidad='CRITICAL').count()
        except Exception:
            pass

    # ── Procesos disciplinarios activos (admin) ──
    if request.user.is_superuser:
        try:
            from disciplinaria.models import MedidaDisciplinaria
            disc_activos = MedidaDisciplinaria.objects.filter(
                estado__in=('BORRADOR', 'EN_DESCARGO', 'EN_RESOLUCION')
            ).count()
            context['disciplinaria_activos'] = disc_activos
        except Exception:
            pass

    # ── Evaluaciones pendientes de completar (admin) ──
    if request.user.is_superuser:
        try:
            from evaluaciones.models import Evaluacion
            eval_pendientes = Evaluacion.objects.filter(
                estado__in=('PENDIENTE', 'EN_PROGRESO')
            ).count()
            context['evaluaciones_pendientes'] = eval_pendientes
        except Exception:
            pass

    # ── Onboarding activos (admin) ──
    if request.user.is_superuser:
        try:
            from onboarding.models import ProcesoOnboarding
            context['onboarding_activos'] = ProcesoOnboarding.objects.filter(
                estado__in=('EN_PROCESO', 'PENDIENTE'), tipo='ONBOARDING'
            ).count()
            context['offboarding_activos'] = ProcesoOnboarding.objects.filter(
                estado__in=('EN_PROCESO', 'PENDIENTE'), tipo='OFFBOARDING'
            ).count()
        except Exception:
            pass

    # ── Encuestas activas (admin) ──
    if request.user.is_superuser:
        try:
            from encuestas.models import Encuesta
            context['encuestas_activas'] = Encuesta.objects.filter(estado='ACTIVA').count()
        except Exception:
            pass

    # ── Reclutamiento: vacantes + candidatos nuevos (admin) ──
    if request.user.is_superuser:
        try:
            from reclutamiento.models import Vacante, Postulacion
            context['reclutamiento_stats'] = {
                'vacantes_activas': Vacante.objects.filter(
                    estado__in=['PUBLICADA', 'ACTIVA']
                ).count(),
                'candidatos_mes': Postulacion.objects.filter(
                    creado_en__date__gte=hoy.replace(day=1)
                ).count(),
            }
        except Exception:
            pass

    # ── Attrition risk: empleados con score alto (admin) ──
    if request.user.is_superuser:
        try:
            en_30_dias = hoy + timedelta(days=30)
            riesgo_count = personal_activo.filter(
                Q(fecha_fin_contrato__isnull=False,
                  fecha_fin_contrato__lte=en_30_dias) |
                Q(sueldo_base__isnull=True) |
                Q(sueldo_base=0)
            ).count()
            context['attrition_riesgo'] = riesgo_count
        except Exception:
            pass

    # ── Viáticos CDT por conciliar (admin) ──
    if request.user.is_superuser:
        try:
            from viaticos.models import ViaticoCDT
            context['viaticos_por_conciliar'] = ViaticoCDT.objects.filter(
                estado__in=['ENTREGADO', 'EN_RENDICION']
            ).count()
        except Exception:
            pass

    # ── Bandas salariales: cobertura (admin) ──
    if request.user.is_superuser:
        try:
            from salarios.models import HistorialSalarial
            con_banda = personal_activo.filter(
                historial_salarial__banda_salarial__isnull=False
            ).distinct().count()
            context['bandas_cobertura'] = {
                'con_banda': con_banda,
                'sin_banda': total_activos - con_banda,
                'pct': round((con_banda / total_activos * 100) if total_activos else 0),
            }
        except Exception:
            pass

    # ── Capacitaciones del mes (admin) ──
    if request.user.is_superuser:
        try:
            from capacitaciones.models import Capacitacion
            inicio_mes = hoy.replace(day=1)
            context['capacitaciones_mes'] = Capacitacion.objects.filter(
                fecha__gte=inicio_mes, fecha__lte=hoy
            ).count()
        except Exception:
            pass

    # ── Headcount tendencia: altas/bajas este mes (admin) ──
    if request.user.is_superuser:
        try:
            inicio_mes = hoy.replace(day=1)
            altas_mes = Personal.objects.filter(
                fecha_alta__gte=inicio_mes, fecha_alta__lte=hoy
            ).count()
            bajas_mes = Personal.objects.filter(
                fecha_baja__gte=inicio_mes, fecha_baja__lte=hoy
            ).count()
            context['headcount_tendencia'] = {
                'altas': altas_mes,
                'bajas': bajas_mes,
                'neto': altas_mes - bajas_mes,
            }
        except Exception:
            pass

    context.update(get_context_usuario(request.user))
    context['frase_dia'] = _get_frase_dia(hoy)
    return render(request, 'home.html', context)


def logout_view(request):
    """Vista personalizada de logout que acepta GET y POST."""
    auth_logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')
