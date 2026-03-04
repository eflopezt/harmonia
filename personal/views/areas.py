"""
Vistas para gestión de áreas (gerencias y subáreas).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
import pandas as pd
from datetime import datetime
import re

from ..models import Area, SubArea, Personal
from ..forms import AreaForm, SubAreaForm, ImportExcelForm
from ..permissions import (
    filtrar_areas, filtrar_subareas, get_context_usuario
)


# ================== ÁREAS ==================

@login_required
def area_list(request):
    """Lista de areas con paginación y totales."""
    areas = filtrar_areas(request.user).annotate(
        total_subareas=Count('subareas', distinct=True),
        total_personal=Count(
            'subareas__personal_asignado',
            filter=Q(subareas__personal_asignado__estado='Activo'),
            distinct=True,
        ),
        total_staff=Count(
            'subareas__personal_asignado',
            filter=Q(
                subareas__personal_asignado__estado='Activo',
                subareas__personal_asignado__grupo_tareo='STAFF',
            ),
            distinct=True,
        ),
        total_rco=Count(
            'subareas__personal_asignado',
            filter=Q(
                subareas__personal_asignado__estado='Activo',
                subareas__personal_asignado__grupo_tareo='RCO',
            ),
            distinct=True,
        ),
    ).select_related('jefe_area').order_by('nombre')

    buscar = request.GET.get('buscar', '')
    solo_activas = request.GET.get('activas', '1')

    if buscar:
        areas = areas.filter(
            Q(nombre__icontains=buscar) |
            Q(responsables__apellidos_nombres__icontains=buscar)
        ).distinct()
    if solo_activas == '1':
        areas = areas.filter(activa=True)

    paginator = Paginator(areas, 20)
    page = request.GET.get('page', 1)
    areas_page = paginator.get_page(page)

    context = {
        'areas': areas_page,
        'buscar': buscar,
        'solo_activas': solo_activas,
        'puede_crear': request.user.is_superuser,
        'total_count': paginator.count,
    }
    context.update(get_context_usuario(request.user))
    return render(request, 'personal/area_list.html', context)


@login_required
def area_detail(request, pk):
    """Detalle de área: subareas, headcount con breakdown completo."""
    from django.db.models import Count, Q

    area = get_object_or_404(Area, pk=pk)

    subareas = area.subareas.annotate(
        total_personal=Count(
            'personal_asignado',
            filter=Q(personal_asignado__estado='Activo')
        ),
        total_staff=Count(
            'personal_asignado',
            filter=Q(personal_asignado__estado='Activo', personal_asignado__grupo_tareo='STAFF')
        ),
        total_rco=Count(
            'personal_asignado',
            filter=Q(personal_asignado__estado='Activo', personal_asignado__grupo_tareo='RCO')
        ),
    ).order_by('nombre')

    from django.utils import timezone
    from datetime import timedelta
    from collections import Counter

    hoy = timezone.localdate()

    empleados = Personal.objects.filter(
        subarea__area=area, estado='Activo'
    ).select_related('subarea').order_by('subarea__nombre', 'apellidos_nombres')

    # ── 1 sola query aggregate en lugar de 11 queries separadas ──────────────
    stats = empleados.aggregate(
        total=Count('id'),
        staff=Count('id', filter=Q(grupo_tareo='STAFF')),
        rco=Count('id', filter=Q(grupo_tareo='RCO')),
        cat_normal=Count('id', filter=Q(categoria='NORMAL')),
        cat_confianza=Count('id', filter=Q(categoria='CONFIANZA')),
        cat_direccion=Count('id', filter=Q(categoria='DIRECCION')),
        reg_afp=Count('id', filter=Q(regimen_pension='AFP')),
        reg_onp=Count('id', filter=Q(regimen_pension='ONP')),
        reg_sin=Count('id', filter=Q(regimen_pension='SIN_PENSION')),
        prox_vencer=Count('id', filter=Q(
            fecha_fin_contrato__isnull=False,
            fecha_fin_contrato__gte=hoy,
            fecha_fin_contrato__lte=hoy + timedelta(days=30),
        )),
        vencidos=Count('id', filter=Q(
            fecha_fin_contrato__isnull=False,
            fecha_fin_contrato__lt=hoy,
        )),
    )
    total_emp          = stats['total']
    total_staff        = stats['staff']
    total_rco          = stats['rco']
    cat_normal         = stats['cat_normal']
    cat_confianza      = stats['cat_confianza']
    cat_direccion      = stats['cat_direccion']
    reg_afp            = stats['reg_afp']
    reg_onp            = stats['reg_onp']
    reg_sin            = stats['reg_sin']
    proximos_vencimientos = stats['prox_vencer']
    contratos_vencidos    = stats['vencidos']

    # ── Distribución por tipo_contrato — 1 query GROUP BY ────────────────────
    contratos_qs = (
        empleados.values('tipo_contrato')
        .annotate(n=Count('id'))
    )
    contratos = Counter()
    contratos_sin_definir = 0
    for row in contratos_qs:
        if row['tipo_contrato']:
            contratos[row['tipo_contrato']] = row['n']
        else:
            contratos_sin_definir += row['n']

    from personal.models import Personal as PersonalModel
    contrato_labels = dict(PersonalModel.TIPO_CONTRATO_CHOICES)
    contratos_display = [
        {'key': k, 'label': contrato_labels.get(k, k), 'count': v}
        for k, v in contratos.most_common(5)
    ]
    if contratos_sin_definir:
        contratos_display.append({'key': '', 'label': 'Sin definir', 'count': contratos_sin_definir})

    context = {
        'area': area,
        'subareas': subareas,
        'empleados': empleados[:50],
        'hay_mas': total_emp > 50,
        'total_personal': total_emp,
        'total_staff': total_staff,
        'total_rco': total_rco,
        # Breakdown categoría
        'cat_normal': cat_normal,
        'cat_confianza': cat_confianza,
        'cat_direccion': cat_direccion,
        # Breakdown pensión
        'reg_afp': reg_afp,
        'reg_onp': reg_onp,
        'reg_sin': reg_sin,
        # Breakdown contrato
        'contratos_display': contratos_display,
        'proximos_vencimientos': proximos_vencimientos,
        'contratos_vencidos': contratos_vencidos,
        # Permisos
        'puede_editar': request.user.is_superuser,
    }
    context.update(get_context_usuario(request.user))
    return render(request, 'personal/area_detail.html', context)


@login_required
def area_create(request):
    """Crear nueva area."""
    # Solo superusuarios pueden crear áreas
    if not request.user.is_superuser:
        messages.error(request, 'Solo los administradores pueden crear áreas.')
        return redirect('area_list')

    if request.method == 'POST':
        form = AreaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Área creada exitosamente.')
            return redirect('area_list')
    else:
        form = AreaForm()

    context = {
        'form': form,
        'area': None  # Para el template que verifica si está editando
    }
    context.update(get_context_usuario(request.user))
    return render(request, 'personal/area_form.html', context)


@login_required
def area_update(request, pk):
    """Actualizar area."""
    if not request.user.is_superuser:
        messages.error(request, 'Solo los administradores pueden editar áreas.')
        return redirect('area_list')

    area = get_object_or_404(Area, pk=pk)

    if request.method == 'POST':
        form = AreaForm(request.POST, instance=area)
        if form.is_valid():
            form.save()
            messages.success(request, 'Área actualizada exitosamente.')
            return redirect('area_detail', pk=area.pk)
    else:
        form = AreaForm(instance=area)

    context = {
        'form': form,
        'area': area
    }
    context.update(get_context_usuario(request.user))
    return render(request, 'personal/area_form.html', context)


@login_required
def area_toggle(request, pk):
    """Activar/desactivar área (POST, solo admin)."""
    if not request.user.is_superuser:
        messages.error(request, 'Acción no permitida.')
        return redirect('area_list')
    if request.method == 'POST':
        area = get_object_or_404(Area, pk=pk)
        area.activa = not area.activa
        area.save(update_fields=['activa'])
        estado = 'activada' if area.activa else 'desactivada'
        messages.success(request, f'Área "{area.nombre}" {estado}.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'activa': area.activa})
    return redirect('area_list')


@login_required
def area_delete(request, pk):
    """Eliminar área (solo si no tiene personal asignado)."""
    if not request.user.is_superuser:
        messages.error(request, 'Acción no permitida.')
        return redirect('area_list')
    if request.method == 'POST':
        area = get_object_or_404(Area, pk=pk)
        total_emp = Personal.objects.filter(subarea__area=area).count()
        if total_emp > 0:
            messages.error(
                request,
                f'No se puede eliminar "{area.nombre}": tiene {total_emp} empleado(s) asignado(s). '
                'Reasígnalos o desactiva el área.'
            )
            return redirect('area_detail', pk=area.pk)
        nombre = area.nombre
        area.delete()
        messages.success(request, f'Área "{nombre}" eliminada.')
    return redirect('area_list')


# ================== SUBAREAS ==================

@login_required
def subarea_list(request):
    """Lista de SubÁreas con paginación."""
    subareas = filtrar_subareas(request.user).select_related('area').annotate(
        total_personal=Count(
            'personal_asignado',
            filter=Q(personal_asignado__estado='Activo')
        )
    ).order_by('area__nombre', 'nombre')

    area_id = request.GET.get('area', '')
    buscar = request.GET.get('buscar', '')
    solo_activas = request.GET.get('activas', '1')

    if area_id:
        subareas = subareas.filter(area_id=area_id)
    if buscar:
        subareas = subareas.filter(
            Q(nombre__icontains=buscar) | Q(area__nombre__icontains=buscar)
        )
    if solo_activas == '1':
        subareas = subareas.filter(activa=True)

    areas = Area.objects.filter(activa=True).order_by('nombre')

    paginator = Paginator(subareas, 25)
    page = request.GET.get('page', 1)
    subareas_page = paginator.get_page(page)

    context = {
        'subareas': subareas_page,
        'areas': areas,
        'buscar': buscar,
        'area_id': area_id,
        'solo_activas': solo_activas,
        'total_count': paginator.count,
    }
    context.update(get_context_usuario(request.user))
    return render(request, 'personal/subarea_list.html', context)


@login_required
def subarea_create(request):
    """Crear nueva SubÁrea."""
    if not request.user.is_superuser:
        messages.error(request, 'Solo los administradores pueden crear SubÁreas.')
        return redirect('subarea_list')

    area_pk = request.GET.get('area') or request.POST.get('area_redirect')

    if request.method == 'POST':
        form = SubAreaForm(request.POST)
        if form.is_valid():
            subarea = form.save()
            messages.success(request, 'SubÁrea creada exitosamente.')
            return redirect('area_detail', pk=subarea.area.pk)
    else:
        initial = {}
        if area_pk:
            initial['area'] = area_pk
        form = SubAreaForm(initial=initial)

    context = {
        'form': form,
        'subarea': None,
        'area_redirect': area_pk,
    }
    context.update(get_context_usuario(request.user))
    return render(request, 'personal/subarea_form.html', context)


@login_required
def subarea_update(request, pk):
    """Actualizar SubÁrea."""
    if not request.user.is_superuser:
        messages.error(request, 'Solo los administradores pueden editar SubÁreas.')
        return redirect('subarea_list')

    subarea = get_object_or_404(SubArea, pk=pk)

    if request.method == 'POST':
        form = SubAreaForm(request.POST, instance=subarea)
        if form.is_valid():
            form.save()
            messages.success(request, 'SubÁrea actualizada exitosamente.')
            return redirect('area_detail', pk=subarea.area.pk)
    else:
        form = SubAreaForm(instance=subarea)

    context = {
        'form': form,
        'subarea': subarea
    }
    context.update(get_context_usuario(request.user))
    return render(request, 'personal/subarea_form.html', context)


@login_required
def subarea_toggle(request, pk):
    """Activar/desactivar subárea (POST, solo admin)."""
    if not request.user.is_superuser:
        messages.error(request, 'Acción no permitida.')
        return redirect('subarea_list')
    if request.method == 'POST':
        subarea = get_object_or_404(SubArea, pk=pk)
        subarea.activa = not subarea.activa
        subarea.save(update_fields=['activa'])
        estado = 'activada' if subarea.activa else 'desactivada'
        messages.success(request, f'SubÁrea "{subarea.nombre}" {estado}.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'activa': subarea.activa})
        return redirect('area_detail', pk=subarea.area.pk)
    return redirect('subarea_list')


@login_required
def subarea_delete(request, pk):
    """Eliminar subárea (solo si no tiene personal asignado)."""
    if not request.user.is_superuser:
        messages.error(request, 'Acción no permitida.')
        return redirect('subarea_list')
    if request.method == 'POST':
        subarea = get_object_or_404(SubArea, pk=pk)
        total_emp = subarea.personal_asignado.count()
        if total_emp > 0:
            messages.error(
                request,
                f'No se puede eliminar "{subarea.nombre}": tiene {total_emp} empleado(s). '
                'Reasígnalos primero.'
            )
            return redirect('area_detail', pk=subarea.area.pk)
        area_pk = subarea.area.pk
        nombre = subarea.nombre
        subarea.delete()
        messages.success(request, f'SubÁrea "{nombre}" eliminada.')
        return redirect('area_detail', pk=area_pk)
    return redirect('subarea_list')


@login_required
def subarea_detail(request, pk):
    """Detalle de una SubÁrea: empleados, stats y acciones."""
    from django.db.models import Count, Q
    from django.utils import timezone
    from datetime import timedelta

    subarea = get_object_or_404(SubArea, pk=pk)

    empleados = Personal.objects.filter(
        subarea=subarea, estado='Activo'
    ).order_by('apellidos_nombres')

    total_emp = empleados.count()
    total_staff = empleados.filter(grupo_tareo='STAFF').count()
    total_rco = empleados.filter(grupo_tareo='RCO').count()
    reg_afp = empleados.filter(regimen_pension='AFP').count()
    reg_onp = empleados.filter(regimen_pension='ONP').count()

    hoy = timezone.localdate()
    proximos_venc = empleados.filter(
        fecha_fin_contrato__isnull=False,
        fecha_fin_contrato__gte=hoy,
        fecha_fin_contrato__lte=hoy + timedelta(days=30),
    ).count()

    # Otras subáreas del mismo área
    otras_subareas = subarea.area.subareas.exclude(pk=pk).annotate(
        total_personal=Count(
            'personal_asignado',
            filter=Q(personal_asignado__estado='Activo')
        )
    ).order_by('nombre')

    context = {
        'subarea': subarea,
        'empleados': empleados,
        'total_personal': total_emp,
        'total_staff': total_staff,
        'total_rco': total_rco,
        'reg_afp': reg_afp,
        'reg_onp': reg_onp,
        'proximos_vencimientos': proximos_venc,
        'otras_subareas': otras_subareas,
        'puede_editar': request.user.is_superuser,
    }
    context.update(get_context_usuario(request.user))
    return render(request, 'personal/subarea_detail.html', context)


# ================== IMPORT/EXPORT ==================

# Importar utilidades de Excel
from ..excel_utils import (
    crear_plantilla_gerencias,
    crear_plantilla_areas,
)

# ===== GERENCIAS =====

@login_required
def area_export(request):
    """Exportar gerencias a Excel con plantilla y catálogos."""
    areas = filtrar_areas(request.user)

    # Crear plantilla con datos actuales
    excel_file = crear_plantilla_gerencias(areas)

    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=gerencias_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    return response


@login_required
def area_import(request):
    """Importar gerencias desde Excel."""
    if request.method == 'POST':
        form = ImportExcelForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']

            try:
                # Forzar DNI como texto para preservar ceros a la izquierda
                df = pd.read_excel(
                    archivo,
                    sheet_name='Gerencias',
                    dtype={'Responsable_DNI': str}
                )

                # Validar columnas
                columnas_requeridas = ['Nombre']
                if not all(col in df.columns for col in columnas_requeridas):
                    messages.error(request, 'El archivo debe contener al menos la columna: Nombre')
                    return redirect('area_import')

                creados = 0
                actualizados = 0
                errores = []

                for idx, row in df.iterrows():
                    try:
                        nombre = str(row['Nombre']).strip()
                        if not nombre or nombre == 'nan':
                            continue

                        responsables_list = None
                        fila_con_error = False
                        if 'Responsable_DNI' in row:
                            responsables_list = []
                            if pd.notna(row['Responsable_DNI']):
                                dni_responsable = row['Responsable_DNI']
                                if isinstance(dni_responsable, (int, float)):
                                    dni_responsable = str(int(dni_responsable)).strip()
                                else:
                                    dni_responsable = str(dni_responsable).strip()

                                dni_list = [d.strip() for d in re.split(r'[;,]', dni_responsable) if d.strip()]
                                for dni in dni_list:
                                    try:
                                        responsables_list.append(Personal.objects.get(nro_doc=dni))
                                    except Personal.DoesNotExist:
                                        errores.append(f"Fila {idx + 2}: Responsable con DNI {dni} no encontrado")
                                        fila_con_error = True

                            if fila_con_error:
                                continue

                        # Determinar si está activa
                        activa = True
                        if 'Activa' in row and pd.notna(row['Activa']):
                            activa = str(row['Activa']).strip().lower() in ['sí', 'si', 'yes', '1', 'true']

                        # Crear o actualizar
                        area, created = Area.objects.update_or_create(
                            nombre=nombre,
                            defaults={
                                'descripcion': row.get('Descripcion', '') if pd.notna(row.get('Descripcion')) else '',
                                'activa': activa,
                            }
                        )
                        if responsables_list is not None:
                            area.responsables.set(responsables_list)

                        if created:
                            creados += 1
                        else:
                            actualizados += 1

                    except Exception as e:
                        errores.append(f"Fila {idx + 2}: {str(e)}")

                if creados > 0:
                    messages.success(request, f'✓ {creados} gerencias creadas')
                if actualizados > 0:
                    messages.info(request, f'ℹ {actualizados} gerencias actualizadas')
                if errores:
                    for error in errores[:10]:
                        messages.warning(request, error)

                return redirect('area_list')

            except Exception as e:
                messages.error(request, f'Error al procesar el archivo: {str(e)}')
                return redirect('area_import')
    else:
        form = ImportExcelForm()

    # Si se solicita plantilla vacía, generarla y descargar
    if request.GET.get('plantilla') == 'vacia':
        excel_file = crear_plantilla_gerencias(None)
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=plantilla_gerencias_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return response

    context = {
        'form': form,
        'titulo': 'Importar Gerencias',
    }
    context.update(get_context_usuario(request.user))
    return render(request, 'personal/import_form.html', context)


# ===== ÁREAS =====

@login_required
def subarea_export(request):
    """Exportar áreas a Excel con plantilla y catálogos."""
    subareas = filtrar_subareas(request.user)

    excel_file = crear_plantilla_areas(subareas)

    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=areas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    return response


@login_required
def subarea_import(request):
    """Importar áreas desde Excel."""
    if request.method == 'POST':
        form = ImportExcelForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']

            try:
                df = pd.read_excel(archivo, sheet_name='Areas')

                columnas_requeridas = ['Nombre', 'Gerencia']
                if not all(col in df.columns for col in columnas_requeridas):
                    messages.error(request, 'El archivo debe contener: Nombre, Area')
                    return redirect('subarea_import')

                creados = 0
                actualizados = 0
                errores = []

                for idx, row in df.iterrows():
                    try:
                        nombre = str(row['Nombre']).strip()
                        area_nombre = str(row['Area']).strip()

                        if not nombre or nombre == 'nan' or not area_nombre or area_nombre == 'nan':
                            continue

                        # Buscar área
                        try:
                            area = Area.objects.get(nombre=area_nombre)
                        except Area.DoesNotExist:
                            errores.append(f"Fila {idx + 2}: Área '{area_nombre}' no encontrada")
                            continue

                        activa = True
                        if 'Activa' in row and pd.notna(row['Activa']):
                            activa = str(row['Activa']).strip().lower() in ['sí', 'si', 'yes', '1', 'true']

                        area, created = SubArea.objects.update_or_create(
                            nombre=nombre,
                            area=area,
                            defaults={
                                'descripcion': row.get('Descripcion', '') if pd.notna(row.get('Descripcion')) else '',
                                'activa': activa,
                            }
                        )

                        if created:
                            creados += 1
                        else:
                            actualizados += 1

                    except Exception as e:
                        errores.append(f"Fila {idx + 2}: {str(e)}")

                if creados > 0:
                    messages.success(request, f'✓ {creados} áreas creadas')
                if actualizados > 0:
                    messages.info(request, f'ℹ {actualizados} áreas actualizadas')
                if errores:
                    for error in errores[:10]:
                        messages.warning(request, error)

                return redirect('subarea_list')

            except Exception as e:
                messages.error(request, f'Error al procesar el archivo: {str(e)}')
                return redirect('subarea_import')
    else:
        form = ImportExcelForm()

    # Si se solicita plantilla vacía, generarla y descargar
    if request.GET.get('plantilla') == 'vacia':
        excel_file = crear_plantilla_areas(None)
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=plantilla_areas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return response

    context = {
        'form': form,
        'titulo': 'Importar Áreas',
    }
    context.update(get_context_usuario(request.user))
    return render(request, 'personal/import_form.html', context)
