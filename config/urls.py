"""
URL configuration for gestion_personal project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health_check(request):
    """Simple health check endpoint for Render"""
    return JsonResponse({'status': 'ok'})

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('', include('personal.urls')),
    path('api/v1/', include('core.api_urls')),
    path('api/', include('personal.api_urls')),  # backward compat
    path('asistencia/', include('asistencia.urls')),
    path('mi-portal/', include('portal.urls')),
    path('cierre/', include('cierre.urls')),
    path('documentos/', include('documentos.urls')),
    path('sistema/', include('core.urls')),
    # Shortcut: /buscar/ → same views as /sistema/buscar/ (avoids prefix)
    path('buscar/', include(('core.urls_buscar', 'buscar'))),
    path('prestamos/', include('prestamos.urls')),
    path('viaticos/', include('viaticos.urls')),
    path('vacaciones/', include('vacaciones.urls')),
    path('capacitaciones/', include('capacitaciones.urls')),
    path('disciplinaria/', include('disciplinaria.urls')),
    path('salarios/', include('salarios.urls')),
    path('evaluaciones/', include('evaluaciones.urls')),
    path('encuestas/', include('encuestas.urls')),
    path('calendario/', include('calendario.urls')),
    path('onboarding/', include('onboarding.urls')),
    path('reclutamiento/', include('reclutamiento.urls')),
    path('comunicaciones/', include('comunicaciones.urls')),
    path('analytics/', include('analytics.urls')),
    path('integraciones/', include('integraciones.urls')),
    path('nominas/', include('nominas.urls')),
    path('empresas/', include('empresas.urls')),
    path('workflows/', include('workflows.urls')),
]

# Add debug toolbar URLs in development
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
    
    # Serve media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
