"""
Vistas del módulo de Onboarding y Offboarding.
"""
from datetime import date, timedelta
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Count, Case, When, IntegerField
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.audit import log_create, log_update
from personal.models import Personal, Area
from .models import (
    PlantillaOnboarding, PasoPlantilla,
    ProcesoOnboarding, PasoOnboarding,
    PlantillaOffboarding, PasoPlantillaOff,
    ProcesoOffboarding, PasoOffboarding,
)

solo_admin = user_passes_test(lambda u: u.is_superuser, login_url='login')


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _notificar_onboarding_completado(proceso):
    """
    Envía una notificación in-app al jefe del área cuando el proceso de
    onboarding de un trabajador llega al 100%.
    Falla silenciosamente para no interrumpir el flujo AJAX.
    """
    try:
        from comunicaciones.services import NotificacionService
        trabajador = proceso.personal
        # Intentar notificar al jefe del área
        area = getattr(trabajador, 'area', None)
        jefe = getattr(area, 'jefe', None) if area else None

        destinatario = jefe or trabajador  # fallback: notificar al propio trabajador
        asunto = f'Onboarding completado — {trabajador.apellidos_nombres}'
        cuerpo = (
            f'<p>El proceso de onboarding de <strong>{trabajador.apellidos_nombres}</strong> '
            f'ha sido completado al 100%.</p>'
            f'<p>Plantilla utilizada: {proceso.plantilla.nombre}</p>'
            f'<p>Fecha de ingreso: {proceso.fecha_ingreso.strftime("%d/%m/%Y")}</p>'
        )
        NotificacionService.enviar(destinatario, asunto, cuerpo, tipo='IN_APP')
    except Exception:
        pass  # Notificación no crítica — no propagar el error


# ══════════════════════════════════════════════════════════════
# ONBOARDING — PANEL
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
def onboarding_panel(request):
    """Panel principal de procesos de onboarding."""
    qs = ProcesoOnboarding.objects.select_related('personal', 'plantilla', 'iniciado_por').all()

    estado = request.GET.get('estado', '')
    buscar = request.GET.get('q', '')

    if estado:
        qs = qs.filter(estado=estado)
    if buscar:
        qs = qs.filter(
            Q(personal__apellidos_nombres__icontains=buscar) |
            Q(personal__nro_doc__icontains=buscar)
        )

    # Stats
    en_curso = ProcesoOnboarding.objects.filter(estado='EN_CURSO').count()
    completados = ProcesoOnboarding.objects.filter(estado='COMPLETADO').count()
    cancelados = ProcesoOnboarding.objects.filter(estado='CANCELADO').count()

    # Pasos vencidos
    pasos_vencidos = PasoOnboarding.objects.filter(
        estado__in=['PENDIENTE', 'EN_PROGRESO'],
        fecha_limite__lt=date.today(),
    ).count()

    context = {
        'titulo': 'Onboarding',
        'procesos': qs[:100],
        'total': qs.count(),
        'filtro_estado': estado,
        'buscar': buscar,
        'stats': {
            'en_curso': en_curso,
            'completados': completados,
            'cancelados': cancelados,
            'pasos_vencidos': pasos_vencidos,
        },
    }
    return render(request, 'onboarding/onboarding_panel.html', context)


# ══════════════════════════════════════════════════════════════
# ONBOARDING — CREAR PROCESO
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
def onboarding_crear(request):
    """Crear nuevo proceso de onboarding."""
    if request.method == 'POST':
        try:
            personal = get_object_or_404(Personal, pk=request.POST['personal_id'])
            plantilla = get_object_or_404(PlantillaOnboarding, pk=request.POST['plantilla_id'])
            fecha_ingreso = request.POST.get('fecha_ingreso', '') or date.today().isoformat()

            proceso = ProcesoOnboarding.objects.create(
                personal=personal,
                plantilla=plantilla,
                fecha_ingreso=fecha_ingreso,
                fecha_inicio=date.today(),
                estado='EN_CURSO',
                iniciado_por=request.user,
                notas=request.POST.get('notas', ''),
            )

            # Auto-generar pasos desde la plantilla
            for paso_tpl in plantilla.pasos.all().order_by('orden'):
                PasoOnboarding.objects.create(
                    proceso=proceso,
                    paso_plantilla=paso_tpl,
                    orden=paso_tpl.orden,
                    titulo=paso_tpl.titulo,
                    estado='PENDIENTE',
                    fecha_limite=proceso.fecha_ingreso + timedelta(days=paso_tpl.dias_plazo),
                )

            log_create(request, proceso, f'Onboarding iniciado: {personal.apellidos_nombres}')
            messages.success(request, f'Proceso de onboarding creado para {personal.apellidos_nombres}')
            return redirect('onboarding_detalle', pk=proceso.pk)
        except Exception as e:
            messages.error(request, f'Error: {e}')

    context = {
        'titulo': 'Nuevo Onboarding',
        'personal_list': Personal.objects.filter(estado='Activo').order_by('apellidos_nombres'),
        'plantillas': PlantillaOnboarding.objects.filter(activa=True),
    }
    return render(request, 'onboarding/onboarding_crear.html', context)


# ══════════════════════════════════════════════════════════════
# ONBOARDING — DETALLE
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
def onboarding_detalle(request, pk):
    """Detalle de proceso con checklist de pasos."""
    proceso = get_object_or_404(
        ProcesoOnboarding.objects.select_related('personal', 'plantilla', 'iniciado_por'),
        pk=pk
    )
    pasos = proceso.pasos.select_related('responsable', 'completado_por').all()

    context = {
        'titulo': f'Onboarding: {proceso.personal.apellidos_nombres}',
        'proceso': proceso,
        'pasos': pasos,
    }
    return render(request, 'onboarding/onboarding_detalle.html', context)


# ══════════════════════════════════════════════════════════════
# ONBOARDING — ACCIONES AJAX SOBRE PASOS
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
@require_POST
def paso_completar(request, pk):
    """Marca un paso de onboarding como COMPLETADO (AJAX)."""
    paso = get_object_or_404(PasoOnboarding, pk=pk)
    old_estado = paso.estado
    paso.estado = 'COMPLETADO'
    paso.fecha_completado = timezone.now()
    paso.completado_por = request.user
    paso.comentarios = request.POST.get('comentarios', paso.comentarios)
    paso.save()

    log_update(request, paso, cambios={
        'estado': {'old': old_estado, 'new': 'COMPLETADO'}
    })

    # Si todos los pasos estan completados u omitidos, completar el proceso
    proceso = paso.proceso
    pendientes = proceso.pasos.exclude(estado__in=['COMPLETADO', 'OMITIDO']).count()
    proceso_recien_completado = False
    if pendientes == 0 and proceso.estado != 'COMPLETADO':
        proceso.estado = 'COMPLETADO'
        proceso.save(update_fields=['estado', 'actualizado_en'])
        proceso_recien_completado = True
        _notificar_onboarding_completado(proceso)

    return JsonResponse({
        'ok': True,
        'paso_id': paso.pk,
        'estado': 'COMPLETADO',
        'completado_por': request.user.get_full_name() or request.user.username,
        'fecha_completado': paso.fecha_completado.strftime('%d/%m/%Y %H:%M'),
        'proceso_completado': pendientes == 0,
        'proceso_recien_completado': proceso_recien_completado,
        'porcentaje': proceso.porcentaje_avance,
    })


@login_required
@solo_admin
@require_POST
def paso_omitir(request, pk):
    """Marca un paso de onboarding como OMITIDO (AJAX)."""
    paso = get_object_or_404(PasoOnboarding, pk=pk)
    old_estado = paso.estado
    paso.estado = 'OMITIDO'
    paso.comentarios = request.POST.get('comentarios', paso.comentarios)
    paso.save()

    log_update(request, paso, cambios={
        'estado': {'old': old_estado, 'new': 'OMITIDO'}
    })

    # Si todos los pasos estan completados u omitidos, completar el proceso
    proceso = paso.proceso
    pendientes = proceso.pasos.exclude(estado__in=['COMPLETADO', 'OMITIDO']).count()
    proceso_recien_completado = False
    if pendientes == 0 and proceso.estado != 'COMPLETADO':
        proceso.estado = 'COMPLETADO'
        proceso.save(update_fields=['estado', 'actualizado_en'])
        proceso_recien_completado = True
        _notificar_onboarding_completado(proceso)

    return JsonResponse({
        'ok': True,
        'paso_id': paso.pk,
        'estado': 'OMITIDO',
        'proceso_completado': pendientes == 0,
        'proceso_recien_completado': proceso_recien_completado,
        'porcentaje': proceso.porcentaje_avance,
    })


# ══════════════════════════════════════════════════════════════
# PLANTILLAS — PANEL CRUD
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
def plantillas_onboarding(request):
    """Panel con lista de plantillas de onboarding y offboarding."""
    plantillas_on = PlantillaOnboarding.objects.annotate(
        num_pasos=Count('pasos'),
        num_procesos=Count('procesos'),
    )
    plantillas_off = PlantillaOffboarding.objects.annotate(
        num_pasos=Count('pasos'),
        num_procesos=Count('procesos'),
    )

    context = {
        'titulo': 'Plantillas de Onboarding / Offboarding',
        'plantillas_on': plantillas_on,
        'plantillas_off': plantillas_off,
    }
    return render(request, 'onboarding/plantillas_panel.html', context)


@login_required
@solo_admin
def plantilla_crear(request):
    """Crear nueva plantilla de onboarding."""
    tipo = request.GET.get('tipo', 'onboarding')

    if request.method == 'POST':
        try:
            tipo_post = request.POST.get('tipo', 'onboarding')
            if tipo_post == 'offboarding':
                plantilla = PlantillaOffboarding.objects.create(
                    nombre=request.POST['nombre'],
                    descripcion=request.POST.get('descripcion', ''),
                )
            else:
                plantilla = PlantillaOnboarding.objects.create(
                    nombre=request.POST['nombre'],
                    descripcion=request.POST.get('descripcion', ''),
                    aplica_grupo=request.POST.get('aplica_grupo', 'TODOS'),
                )
                # Asignar areas si se seleccionaron
                areas_ids = request.POST.getlist('aplica_areas')
                if areas_ids:
                    plantilla.aplica_areas.set(areas_ids)

            log_create(request, plantilla, f'Plantilla creada: {plantilla.nombre}')
            messages.success(request, f'Plantilla "{plantilla.nombre}" creada.')
            return redirect('plantilla_detalle', tipo=tipo_post, pk=plantilla.pk)
        except Exception as e:
            messages.error(request, f'Error: {e}')

    context = {
        'titulo': 'Nueva Plantilla',
        'tipo': tipo,
        'areas': Area.objects.filter(activa=True),
    }
    return render(request, 'onboarding/plantilla_crear.html', context)


@login_required
@solo_admin
def plantilla_detalle(request, tipo, pk):
    """Detalle de plantilla con pasos ordenados."""
    if tipo == 'offboarding':
        plantilla = get_object_or_404(PlantillaOffboarding, pk=pk)
        pasos = plantilla.pasos.all()
    else:
        plantilla = get_object_or_404(PlantillaOnboarding, pk=pk)
        pasos = plantilla.pasos.all()

    context = {
        'titulo': f'Plantilla: {plantilla.nombre}',
        'plantilla': plantilla,
        'pasos': pasos,
        'tipo': tipo,
    }
    return render(request, 'onboarding/plantilla_detalle.html', context)


# ══════════════════════════════════════════════════════════════
# PLANTILLAS — PASOS AJAX
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
@require_POST
def paso_plantilla_agregar(request, tipo, pk):
    """Agrega un paso a una plantilla (AJAX)."""
    if tipo == 'offboarding':
        plantilla = get_object_or_404(PlantillaOffboarding, pk=pk)
        ultimo_orden = plantilla.pasos.count()
        paso = PasoPlantillaOff.objects.create(
            plantilla=plantilla,
            orden=ultimo_orden + 1,
            titulo=request.POST['titulo'],
            descripcion=request.POST.get('descripcion', ''),
            tipo=request.POST.get('tipo', 'TAREA'),
            responsable_tipo=request.POST.get('responsable_tipo', 'RRHH'),
            dias_plazo=int(request.POST.get('dias_plazo', 1)),
            obligatorio=request.POST.get('obligatorio') == 'on',
        )
    else:
        plantilla = get_object_or_404(PlantillaOnboarding, pk=pk)
        ultimo_orden = plantilla.pasos.count()
        paso = PasoPlantilla.objects.create(
            plantilla=plantilla,
            orden=ultimo_orden + 1,
            titulo=request.POST['titulo'],
            descripcion=request.POST.get('descripcion', ''),
            tipo=request.POST.get('tipo', 'TAREA'),
            responsable_tipo=request.POST.get('responsable_tipo', 'RRHH'),
            dias_plazo=int(request.POST.get('dias_plazo', 1)),
            obligatorio=request.POST.get('obligatorio') == 'on',
        )

    return JsonResponse({
        'ok': True,
        'paso_id': paso.pk,
        'orden': paso.orden,
        'titulo': paso.titulo,
        'tipo': paso.tipo,
        'responsable_tipo': paso.responsable_tipo,
        'dias_plazo': paso.dias_plazo,
        'obligatorio': paso.obligatorio,
    })


@login_required
@solo_admin
@require_POST
def paso_plantilla_eliminar(request, tipo, pk):
    """Elimina un paso de una plantilla (AJAX)."""
    if tipo == 'offboarding':
        paso = get_object_or_404(PasoPlantillaOff, pk=pk)
    else:
        paso = get_object_or_404(PasoPlantilla, pk=pk)

    paso_id = paso.pk
    paso.delete()

    return JsonResponse({'ok': True, 'paso_id': paso_id})


# ══════════════════════════════════════════════════════════════
# OFFBOARDING — PANEL
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
def offboarding_panel(request):
    """Panel principal de procesos de offboarding."""
    qs = ProcesoOffboarding.objects.select_related('personal', 'plantilla', 'iniciado_por').all()

    estado = request.GET.get('estado', '')
    buscar = request.GET.get('q', '')
    motivo = request.GET.get('motivo', '')

    if estado:
        qs = qs.filter(estado=estado)
    if motivo:
        qs = qs.filter(motivo_cese=motivo)
    if buscar:
        qs = qs.filter(
            Q(personal__apellidos_nombres__icontains=buscar) |
            Q(personal__nro_doc__icontains=buscar)
        )

    # Stats
    en_curso = ProcesoOffboarding.objects.filter(estado='EN_CURSO').count()
    completados = ProcesoOffboarding.objects.filter(estado='COMPLETADO').count()

    context = {
        'titulo': 'Offboarding',
        'procesos': qs[:100],
        'total': qs.count(),
        'filtro_estado': estado,
        'filtro_motivo': motivo,
        'buscar': buscar,
        'stats': {
            'en_curso': en_curso,
            'completados': completados,
        },
    }
    return render(request, 'onboarding/offboarding_panel.html', context)


# ══════════════════════════════════════════════════════════════
# OFFBOARDING — CREAR PROCESO
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
def offboarding_crear(request):
    """Crear nuevo proceso de offboarding."""
    if request.method == 'POST':
        try:
            personal = get_object_or_404(Personal, pk=request.POST['personal_id'])
            plantilla = get_object_or_404(PlantillaOffboarding, pk=request.POST['plantilla_id'])
            fecha_cese = request.POST.get('fecha_cese', '') or date.today().isoformat()

            proceso = ProcesoOffboarding.objects.create(
                personal=personal,
                plantilla=plantilla,
                fecha_cese=fecha_cese,
                motivo_cese=request.POST['motivo_cese'],
                estado='EN_CURSO',
                iniciado_por=request.user,
                notas=request.POST.get('notas', ''),
            )

            # Auto-generar pasos desde la plantilla
            for paso_tpl in plantilla.pasos.all().order_by('orden'):
                PasoOffboarding.objects.create(
                    proceso=proceso,
                    paso_plantilla=paso_tpl,
                    orden=paso_tpl.orden,
                    titulo=paso_tpl.titulo,
                    estado='PENDIENTE',
                    fecha_limite=proceso.fecha_cese + timedelta(days=paso_tpl.dias_plazo),
                )

            log_create(request, proceso, f'Offboarding iniciado: {personal.apellidos_nombres}')
            messages.success(request, f'Proceso de offboarding creado para {personal.apellidos_nombres}')
            return redirect('offboarding_detalle', pk=proceso.pk)
        except Exception as e:
            messages.error(request, f'Error: {e}')

    context = {
        'titulo': 'Nuevo Offboarding',
        'personal_list': Personal.objects.filter(estado='Activo').order_by('apellidos_nombres'),
        'plantillas': PlantillaOffboarding.objects.filter(activa=True),
    }
    return render(request, 'onboarding/offboarding_crear.html', context)


# ══════════════════════════════════════════════════════════════
# OFFBOARDING — DETALLE
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
def offboarding_detalle(request, pk):
    """Detalle de proceso de offboarding con checklist."""
    proceso = get_object_or_404(
        ProcesoOffboarding.objects.select_related('personal', 'plantilla', 'iniciado_por'),
        pk=pk
    )
    pasos = proceso.pasos.select_related('responsable', 'completado_por').all()

    context = {
        'titulo': f'Offboarding: {proceso.personal.apellidos_nombres}',
        'proceso': proceso,
        'pasos': pasos,
    }
    return render(request, 'onboarding/offboarding_detalle.html', context)


# ══════════════════════════════════════════════════════════════
# OFFBOARDING — ACCIONES AJAX SOBRE PASOS
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
@require_POST
def paso_off_completar(request, pk):
    """Marca un paso de offboarding como COMPLETADO (AJAX)."""
    paso = get_object_or_404(PasoOffboarding, pk=pk)
    old_estado = paso.estado
    paso.estado = 'COMPLETADO'
    paso.fecha_completado = timezone.now()
    paso.completado_por = request.user
    paso.comentarios = request.POST.get('comentarios', paso.comentarios)
    paso.save()

    log_update(request, paso, cambios={
        'estado': {'old': old_estado, 'new': 'COMPLETADO'}
    })

    proceso = paso.proceso
    pendientes = proceso.pasos.exclude(estado__in=['COMPLETADO', 'OMITIDO']).count()
    if pendientes == 0:
        proceso.estado = 'COMPLETADO'
        proceso.save(update_fields=['estado', 'actualizado_en'])

    return JsonResponse({
        'ok': True,
        'paso_id': paso.pk,
        'estado': 'COMPLETADO',
        'completado_por': request.user.get_full_name() or request.user.username,
        'fecha_completado': paso.fecha_completado.strftime('%d/%m/%Y %H:%M'),
        'proceso_completado': pendientes == 0,
        'porcentaje': proceso.porcentaje_avance,
    })


@login_required
@solo_admin
@require_POST
def paso_off_omitir(request, pk):
    """Marca un paso de offboarding como OMITIDO (AJAX)."""
    paso = get_object_or_404(PasoOffboarding, pk=pk)
    old_estado = paso.estado
    paso.estado = 'OMITIDO'
    paso.comentarios = request.POST.get('comentarios', paso.comentarios)
    paso.save()

    log_update(request, paso, cambios={
        'estado': {'old': old_estado, 'new': 'OMITIDO'}
    })

    proceso = paso.proceso
    pendientes = proceso.pasos.exclude(estado__in=['COMPLETADO', 'OMITIDO']).count()
    if pendientes == 0:
        proceso.estado = 'COMPLETADO'
        proceso.save(update_fields=['estado', 'actualizado_en'])

    return JsonResponse({
        'ok': True,
        'paso_id': paso.pk,
        'estado': 'OMITIDO',
        'proceso_completado': pendientes == 0,
        'porcentaje': proceso.porcentaje_avance,
    })


# ══════════════════════════════════════════════════════════════
# PORTAL — MI ONBOARDING
# ══════════════════════════════════════════════════════════════

@login_required
def mi_onboarding(request):
    """Vista portal: muestra el proceso de onboarding/offboarding del empleado."""
    from portal.views import _get_empleado
    empleado = _get_empleado(request.user)

    proceso_on = None
    pasos_on = []
    proceso_off = None
    pasos_off = []

    if empleado:
        proceso_on = ProcesoOnboarding.objects.filter(
            personal=empleado, estado='EN_CURSO'
        ).select_related('plantilla').first()
        if proceso_on:
            pasos_on = proceso_on.pasos.all()

        proceso_off = ProcesoOffboarding.objects.filter(
            personal=empleado, estado='EN_CURSO'
        ).select_related('plantilla').first()
        if proceso_off:
            pasos_off = proceso_off.pasos.all()

    context = {
        'titulo': 'Mi Onboarding',
        'empleado': empleado,
        'proceso_on': proceso_on,
        'pasos_on': pasos_on,
        'proceso_off': proceso_off,
        'pasos_off': pasos_off,
    }
    return render(request, 'onboarding/mi_onboarding.html', context)


# ══════════════════════════════════════════════════════════════
# DASHBOARD OVERVIEW
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
def onboarding_dashboard(request):
    """Dashboard ejecutivo de onboarding y offboarding con KPIs y grafico Chart.js."""
    hoy = date.today()
    hace_7_dias = hoy + timedelta(days=7)
    inicio_mes = hoy.replace(day=1)

    # KPIs base
    activos_onboarding = ProcesoOnboarding.objects.filter(estado='EN_CURSO').count()
    activos_offboarding = ProcesoOffboarding.objects.filter(estado='EN_CURSO').count()

    # ── KPIs nuevos ──────────────────────────────────────────

    # en_proceso: procesos que NO estan completados ni cancelados (ambos modelos)
    en_proceso = 0
    try:
        en_proceso_on = ProcesoOnboarding.objects.exclude(
            estado__in=['COMPLETADO', 'CANCELADO']
        ).count()
        en_proceso_off = ProcesoOffboarding.objects.exclude(
            estado__in=['COMPLETADO', 'CANCELADO']
        ).count()
        en_proceso = en_proceso_on + en_proceso_off
    except Exception:
        en_proceso = 0

    # tasa_completitud: total completados / total procesos * 100 (int)
    tasa_completitud = 0
    try:
        total_on_all = ProcesoOnboarding.objects.count()
        total_off_all = ProcesoOffboarding.objects.count()
        total_all = total_on_all + total_off_all
        comp_on_all = ProcesoOnboarding.objects.filter(estado='COMPLETADO').count()
        comp_off_all = ProcesoOffboarding.objects.filter(estado='COMPLETADO').count()
        comp_all = comp_on_all + comp_off_all
        tasa_completitud = int(comp_all * 100 / total_all) if total_all else 0
    except Exception:
        tasa_completitud = 0

    # promedio_dias_completitud: promedio de dias desde fecha_inicio hasta completado
    # Para onboarding: (actualizado_en.date - fecha_inicio).days solo si completado
    # Para offboarding: (actualizado_en.date - creado_en.date).days solo si completado
    promedio_dias_completitud = 0
    try:
        dias_lista = []
        on_completados = ProcesoOnboarding.objects.filter(
            estado='COMPLETADO'
        ).only('fecha_inicio', 'actualizado_en')
        for p in on_completados:
            delta = p.actualizado_en.date() - p.fecha_inicio
            if delta.days >= 0:
                dias_lista.append(delta.days)

        off_completados = ProcesoOffboarding.objects.filter(
            estado='COMPLETADO'
        ).only('creado_en', 'actualizado_en')
        for p in off_completados:
            delta = p.actualizado_en.date() - p.creado_en.date()
            if delta.days >= 0:
                dias_lista.append(delta.days)

        promedio_dias_completitud = round(sum(dias_lista) / len(dias_lista)) if dias_lista else 0
    except Exception:
        promedio_dias_completitud = 0

    # offboarding_activos: alias de activos_offboarding (offboarding EN_CURSO)
    offboarding_activos = activos_offboarding

    # por_tipo_json: desglose de procesos activos (EN_CURSO) por tipo, para doughnut
    por_tipo_json = '[]'
    try:
        por_tipo_data = [
            {'label': 'Onboarding', 'count': activos_onboarding},
            {'label': 'Offboarding', 'count': activos_offboarding},
        ]
        por_tipo_json = json.dumps(por_tipo_data)
    except Exception:
        por_tipo_json = '[]'

    # ── Métricas adicionales (todas en try/except para no romper el dashboard) ──

    # Conteo por tipo: cuántos procesos EN_CURSO hay de cada clase
    procesos_por_tipo = {'ONBOARDING': activos_onboarding, 'OFFBOARDING': activos_offboarding}

    # Progreso promedio de procesos activos (onboarding + offboarding EN_CURSO)
    progreso_promedio = 0
    try:
        procesos_on_activos_qs = list(
            ProcesoOnboarding.objects.filter(estado='EN_CURSO')
            .prefetch_related('pasos')
        )
        procesos_off_activos_qs = list(
            ProcesoOffboarding.objects.filter(estado='EN_CURSO')
            .prefetch_related('pasos')
        )
        all_activos = procesos_on_activos_qs + procesos_off_activos_qs
        if all_activos:
            progreso_promedio = round(
                sum(p.porcentaje_avance for p in all_activos) / len(all_activos)
            )
    except Exception:
        progreso_promedio = 0

    # Tareas críticas: pasos vencidos (fecha_limite < hoy) y no completadas/omitidas
    tareas_pendientes_criticas = 0
    try:
        criticas_on = PasoOnboarding.objects.filter(
            fecha_limite__lt=hoy,
            estado__in=['PENDIENTE', 'EN_PROGRESO'],
        ).count()
        criticas_off = PasoOffboarding.objects.filter(
            fecha_limite__lt=hoy,
            estado__in=['PENDIENTE', 'EN_PROGRESO'],
        ).count()
        tareas_pendientes_criticas = criticas_on + criticas_off
    except Exception:
        tareas_pendientes_criticas = 0

    # Timeline reciente: últimos 8 procesos (on + off) ordenados por fecha_inicio/-creado_en
    timeline_reciente = []
    try:
        on_recientes = list(
            ProcesoOnboarding.objects.select_related('personal')
            .order_by('-fecha_inicio')[:8]
        )
        off_recientes = list(
            ProcesoOffboarding.objects.select_related('personal')
            .order_by('-creado_en')[:8]
        )
        # Unificar en una lista normalizada y ordenar por fecha desc
        def _normalizar_on(p):
            return {
                'pk': p.pk,
                'tipo': 'ONBOARDING',
                'trabajador': p.personal.apellidos_nombres,
                'fecha_inicio': p.fecha_inicio,
                'porcentaje': p.porcentaje_avance,
                'estado': p.get_estado_display(),
                'estado_raw': p.estado,
                'url': f'/onboarding/{p.pk}/progreso/',
            }

        def _normalizar_off(p):
            return {
                'pk': p.pk,
                'tipo': 'OFFBOARDING',
                'trabajador': p.personal.apellidos_nombres,
                'fecha_inicio': p.creado_en.date(),
                'porcentaje': p.porcentaje_avance,
                'estado': p.get_estado_display(),
                'estado_raw': p.estado,
                'url': f'/onboarding/offboarding/{p.pk}/',
            }

        combinados = [_normalizar_on(p) for p in on_recientes] + \
                     [_normalizar_off(p) for p in off_recientes]
        combinados.sort(key=lambda x: x['fecha_inicio'], reverse=True)
        timeline_reciente = combinados[:8]
    except Exception:
        timeline_reciente = []

    completados_on_mes = ProcesoOnboarding.objects.filter(
        estado='COMPLETADO', actualizado_en__date__gte=inicio_mes
    ).count()
    completados_off_mes = ProcesoOffboarding.objects.filter(
        estado='COMPLETADO', actualizado_en__date__gte=inicio_mes
    ).count()
    completados_mes = completados_on_mes + completados_off_mes

    total_on = ProcesoOnboarding.objects.count()
    total_off = ProcesoOffboarding.objects.count()
    total = total_on + total_off
    total_completados = (
        ProcesoOnboarding.objects.filter(estado='COMPLETADO').count() +
        ProcesoOffboarding.objects.filter(estado='COMPLETADO').count()
    )
    porcentaje_completado = round(total_completados * 100 / total) if total else 0

    # Procesos activos ordenados por dias restantes (fecha_cese / fecha_ingreso - hoy)
    # Onboarding en curso — añadir dias_restantes calculado
    procesos_on_activos = []
    for p in ProcesoOnboarding.objects.filter(estado='EN_CURSO').select_related('personal', 'plantilla'):
        # Usamos el ultimo dia limite de sus pasos como referencia de fin, o +30 dias desde inicio
        ultimo_paso = p.pasos.order_by('-fecha_limite').first()
        fecha_fin = ultimo_paso.fecha_limite if ultimo_paso and ultimo_paso.fecha_limite else (p.fecha_inicio + timedelta(days=30))
        dias_restantes = (fecha_fin - hoy).days
        procesos_on_activos.append({
            'pk': p.pk,
            'tipo': 'ONBOARDING',
            'trabajador': p.personal.apellidos_nombres,
            'doc': p.personal.nro_doc,
            'plantilla': p.plantilla.nombre,
            'fecha_ref': fecha_fin,
            'dias_restantes': dias_restantes,
            'porcentaje': p.porcentaje_avance,
            'pasos_completados': p.pasos_completados,
            'total_pasos': p.total_pasos,
            'en_riesgo': 0 < dias_restantes <= 7,
            'vencido': dias_restantes < 0,
            'url': f'/onboarding/{p.pk}/progreso/',
        })

    procesos_off_activos = []
    for p in ProcesoOffboarding.objects.filter(estado='EN_CURSO').select_related('personal', 'plantilla'):
        ultimo_paso = p.pasos.order_by('-fecha_limite').first()
        fecha_fin = ultimo_paso.fecha_limite if ultimo_paso and ultimo_paso.fecha_limite else p.fecha_cese
        dias_restantes = (fecha_fin - hoy).days
        procesos_off_activos.append({
            'pk': p.pk,
            'tipo': 'OFFBOARDING',
            'trabajador': p.personal.apellidos_nombres,
            'doc': p.personal.nro_doc,
            'plantilla': p.plantilla.nombre,
            'fecha_ref': fecha_fin,
            'dias_restantes': dias_restantes,
            'porcentaje': p.porcentaje_avance,
            'pasos_completados': p.pasos_completados,
            'total_pasos': p.total_pasos,
            'en_riesgo': 0 < dias_restantes <= 7,
            'vencido': dias_restantes < 0,
            'url': f'/onboarding/offboarding/{p.pk}/',
        })

    todos_activos = sorted(
        procesos_on_activos + procesos_off_activos,
        key=lambda x: x['dias_restantes']
    )

    # Procesos en riesgo: fecha_fin en los proximos 7 dias, sin completar
    en_riesgo_count = sum(1 for p in todos_activos if p['en_riesgo'])

    # Gráfico Chart.js: completados últimos 6 meses (onboarding vs offboarding)
    meses_labels = []
    data_on = []
    data_off = []
    for i in range(5, -1, -1):
        # Calcular año/mes hace i meses
        mes = hoy.month - i
        anio = hoy.year
        while mes <= 0:
            mes += 12
            anio -= 1
        meses_labels.append(f"{anio}-{mes:02d}")
        data_on.append(
            ProcesoOnboarding.objects.filter(
                estado='COMPLETADO',
                actualizado_en__year=anio,
                actualizado_en__month=mes,
            ).count()
        )
        data_off.append(
            ProcesoOffboarding.objects.filter(
                estado='COMPLETADO',
                actualizado_en__year=anio,
                actualizado_en__month=mes,
            ).count()
        )

    context = {
        'titulo': 'Dashboard Onboarding & Offboarding',
        'activos_onboarding': activos_onboarding,
        'activos_offboarding': activos_offboarding,
        'completados_mes': completados_mes,
        'porcentaje_completado': porcentaje_completado,
        'en_riesgo_count': en_riesgo_count,
        'todos_activos': todos_activos,
        # Metricas adicionales existentes
        'procesos_por_tipo': procesos_por_tipo,
        'progreso_promedio': progreso_promedio,
        'tareas_pendientes_criticas': tareas_pendientes_criticas,
        'timeline_reciente': timeline_reciente,
        # Nuevos KPIs
        'en_proceso': en_proceso,
        'tasa_completitud': tasa_completitud,
        'promedio_dias_completitud': promedio_dias_completitud,
        'offboarding_activos': offboarding_activos,
        # JSON para Chart.js
        'chart_labels': json.dumps(meses_labels),
        'chart_on': json.dumps(data_on),
        'chart_off': json.dumps(data_off),
        'por_tipo_json': por_tipo_json,
    }
    return render(request, 'onboarding/dashboard.html', context)


# ══════════════════════════════════════════════════════════════
# PROGRESO DE PROCESO (TIMELINE)
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
def proceso_progreso(request, pk):
    """Vista timeline de pasos de un ProcesoOnboarding con toggle AJAX."""
    proceso = get_object_or_404(
        ProcesoOnboarding.objects.select_related('personal', 'plantilla', 'iniciado_por'),
        pk=pk
    )
    pasos = proceso.pasos.select_related('responsable', 'completado_por', 'paso_plantilla').order_by('orden')

    hoy = date.today()
    ultimo_paso_limite = pasos.filter(fecha_limite__isnull=False).order_by('-fecha_limite').first()
    fecha_fin = ultimo_paso_limite.fecha_limite if ultimo_paso_limite else (proceso.fecha_inicio + timedelta(days=30))
    dias_restantes = (fecha_fin - hoy).days

    context = {
        'titulo': f'Progreso: {proceso.personal.apellidos_nombres}',
        'proceso': proceso,
        'pasos': pasos,
        'hoy': hoy,
        'dias_restantes': dias_restantes,
        'fecha_fin': fecha_fin,
        'alerta_nivel': 'danger' if dias_restantes < 0 else ('warning' if dias_restantes <= 7 else ''),
    }
    return render(request, 'onboarding/proceso_progreso.html', context)


# ══════════════════════════════════════════════════════════════
# COMPLETAR PASO — AJAX TOGGLE (nuevo endpoint unificado)
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
@require_POST
def onboarding_completar_paso(request, proc_pk, paso_pk):
    """
    Toggle estado de PasoOnboarding: PENDIENTE/EN_PROGRESO <-> COMPLETADO.
    Devuelve JSON {ok, nuevo_estado, progreso_pct}.
    """
    proceso = get_object_or_404(ProcesoOnboarding, pk=proc_pk)
    paso = get_object_or_404(PasoOnboarding, pk=paso_pk, proceso=proceso)

    old_estado = paso.estado

    if paso.estado == 'COMPLETADO':
        # Toggle: revertir a PENDIENTE
        paso.estado = 'PENDIENTE'
        paso.fecha_completado = None
        paso.completado_por = None
        paso.save(update_fields=['estado', 'fecha_completado', 'completado_por'])
        log_update(request, paso, cambios={'estado': {'old': old_estado, 'new': 'PENDIENTE'}})
        # Reabrir proceso si estaba completado
        if proceso.estado == 'COMPLETADO':
            proceso.estado = 'EN_CURSO'
            proceso.save(update_fields=['estado', 'actualizado_en'])
    else:
        # Marcar como completado
        paso.estado = 'COMPLETADO'
        paso.fecha_completado = timezone.now()
        paso.completado_por = request.user
        paso.save(update_fields=['estado', 'fecha_completado', 'completado_por'])
        log_update(request, paso, cambios={'estado': {'old': old_estado, 'new': 'COMPLETADO'}})
        # Auto-completar proceso si todos los pasos terminaron
        pendientes = proceso.pasos.exclude(estado__in=['COMPLETADO', 'OMITIDO']).count()
        if pendientes == 0 and proceso.estado != 'COMPLETADO':
            proceso.estado = 'COMPLETADO'
            proceso.save(update_fields=['estado', 'actualizado_en'])
            _notificar_onboarding_completado(proceso)

    # Recalcular progreso fresco desde DB
    proceso.refresh_from_db()
    total = proceso.pasos.count()
    completados_n = proceso.pasos.filter(estado='COMPLETADO').count()
    progreso_pct = round(completados_n * 100 / total) if total else 0

    return JsonResponse({
        'ok': True,
        'nuevo_estado': paso.estado,
        'progreso_pct': progreso_pct,
        'pasos_completados': completados_n,
        'total_pasos': total,
    })


# ══════════════════════════════════════════════════════════════
# PLANTILLA AJAX — devuelve datos de plantilla para pre-fill
# ══════════════════════════════════════════════════════════════

@login_required
@solo_admin
def plantilla_ajax(request, pk):
    """
    Devuelve JSON con datos de una PlantillaOnboarding para pre-fill en crear proceso.
    GET /onboarding/plantilla-ajax/<pk>/
    """
    plantilla = get_object_or_404(PlantillaOnboarding, pk=pk)
    pasos = list(plantilla.pasos.values(
        'orden', 'titulo', 'tipo', 'responsable_tipo', 'dias_plazo', 'obligatorio'
    ))
    return JsonResponse({
        'ok': True,
        'pk': plantilla.pk,
        'nombre': plantilla.nombre,
        'descripcion': plantilla.descripcion,
        'aplica_grupo': plantilla.aplica_grupo,
        'pasos': pasos,
    })
