"""Empresas — Vistas: CRUD de empresas y selección de empresa activa."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Empresa

solo_admin = user_passes_test(lambda u: u.is_superuser)


@login_required
@solo_admin
def empresas_panel(request):
    """Lista de empresas."""
    empresas = Empresa.objects.all()
    return render(request, 'empresas/panel.html', {
        'titulo': 'Empresas',
        'empresas': empresas,
    })


@login_required
@solo_admin
def empresa_crear(request):
    """Crear nueva empresa."""
    if request.method == 'POST':
        ruc          = request.POST.get('ruc', '').strip()
        razon_social = request.POST.get('razon_social', '').strip()
        nombre_comercial = request.POST.get('nombre_comercial', '').strip()
        es_principal = request.POST.get('es_principal') == '1'

        if not ruc or not razon_social:
            messages.error(request, 'RUC y Razón Social son requeridos.')
            return redirect('empresa_crear')

        if Empresa.objects.filter(ruc=ruc).exists():
            messages.error(request, f'Ya existe una empresa con RUC {ruc}.')
            return redirect('empresa_crear')

        emp = Empresa.objects.create(
            ruc=ruc,
            razon_social=razon_social,
            nombre_comercial=nombre_comercial,
            es_principal=es_principal,
            creado_por=request.user,
        )
        messages.success(request, f'Empresa "{emp}" creada exitosamente.')
        return redirect('empresas_panel')

    return render(request, 'empresas/form.html', {
        'titulo': 'Nueva Empresa',
        'action': 'crear',
        'regimen_choices': Empresa.REGIMEN_CHOICES,
    })


@login_required
@solo_admin
def empresa_editar(request, pk):
    """Editar empresa existente."""
    empresa = get_object_or_404(Empresa, pk=pk)

    if request.method == 'POST':
        empresa.razon_social     = request.POST.get('razon_social', empresa.razon_social).strip()
        empresa.nombre_comercial = request.POST.get('nombre_comercial', '').strip()
        empresa.ruc              = request.POST.get('ruc', empresa.ruc).strip()
        empresa.direccion        = request.POST.get('direccion', '').strip()
        empresa.telefono         = request.POST.get('telefono', '').strip()
        empresa.email_rrhh       = request.POST.get('email_rrhh', '').strip()
        empresa.regimen_laboral  = request.POST.get('regimen_laboral', 'GENERAL')
        empresa.es_principal     = request.POST.get('es_principal') == '1'
        empresa.activa           = request.POST.get('activa') == '1'
        empresa.save()
        messages.success(request, f'Empresa "{empresa}" actualizada.')
        return redirect('empresas_panel')

    return render(request, 'empresas/form.html', {
        'titulo': f'Editar — {empresa.nombre_display}',
        'empresa': empresa,
        'action': 'editar',
        'regimen_choices': Empresa.REGIMEN_CHOICES,
    })


@login_required
@require_POST
def seleccionar_empresa(request):
    """
    Cambia la empresa activa en la sesión.
    Cualquier usuario autenticado puede cambiar su empresa activa.
    """
    empresa_id = request.POST.get('empresa_id')
    next_url   = request.POST.get('next', '/')
    # Prevent open redirect — only allow internal URLs
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = '/'

    if empresa_id:
        try:
            emp = Empresa.objects.get(pk=empresa_id, activa=True)
            request.session['empresa_actual_id']     = emp.pk
            request.session['empresa_actual_nombre'] = emp.nombre_display
            messages.success(request, f'Empresa activa: {emp.nombre_display}')
        except Empresa.DoesNotExist:
            messages.error(request, 'Empresa no encontrada.')
    else:
        # Limpiar selección (vuelve a la empresa principal)
        request.session.pop('empresa_actual_id', None)
        request.session.pop('empresa_actual_nombre', None)
        messages.info(request, 'Empresa activa restablecida.')

    return redirect(next_url)


@login_required
@solo_admin
def configuracion_empresa(request, pk):
    """Configurar identidad visual de la empresa: logo, membrete, firma."""
    empresa = get_object_or_404(Empresa, pk=pk)

    if request.method == 'POST':
        # Campos de texto
        empresa.representante_legal = request.POST.get('representante_legal', '').strip()
        empresa.cargo_representante = request.POST.get('cargo_representante', '').strip()

        # Archivos de imagen
        if 'logo' in request.FILES:
            empresa.logo = request.FILES['logo']
        if 'membrete_header' in request.FILES:
            empresa.membrete_header = request.FILES['membrete_header']
        if 'firma_representante' in request.FILES:
            empresa.firma_representante = request.FILES['firma_representante']

        # Permitir borrar imágenes
        if request.POST.get('borrar_logo') == '1':
            empresa.logo = ''
        if request.POST.get('borrar_membrete') == '1':
            empresa.membrete_header = ''
        if request.POST.get('borrar_firma') == '1':
            empresa.firma_representante = ''

        empresa.save()
        messages.success(request, 'Configuración de empresa actualizada correctamente.')
        return redirect('configuracion_empresa', pk=empresa.pk)

    return render(request, 'empresas/configuracion.html', {
        'titulo': f'Configuración — {empresa.nombre_display}',
        'empresa': empresa,
    })
