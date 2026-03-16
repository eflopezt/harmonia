"""
Middleware de multi-empresa para Harmoni.

Inyecta request.empresa_actual con la empresa activa en la sesión.
Si no hay empresa en sesión, usa la empresa principal.
"""


class EmpresaMiddleware:
    """
    Inyecta `request.empresa_actual` (instancia de Empresa o None).
    Disponible en todas las vistas sin importar nada extra.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.empresa_actual = None

        if request.user.is_authenticated:
            empresa_id = request.session.get('empresa_actual_id')
            if empresa_id:
                try:
                    from empresas.models import Empresa
                    request.empresa_actual = Empresa.objects.get(pk=empresa_id, activa=True)
                except Exception:
                    pass

            # Si no hay empresa en sesión, buscar la principal
            if not request.empresa_actual:
                try:
                    from empresas.models import Empresa
                    request.empresa_actual = Empresa.objects.filter(
                        activa=True, es_principal=True
                    ).first()
                    if request.empresa_actual:
                        request.session['empresa_actual_id']     = request.empresa_actual.pk
                        request.session['empresa_actual_nombre'] = request.empresa_actual.nombre_display
                except Exception:
                    pass

        # Setear empresa en thread-local para el email backend
        if request.empresa_actual:
            from empresas.email_backend import set_current_empresa
            set_current_empresa(request.empresa_actual)

        response = self.get_response(request)

        # Limpiar thread-local después del request
        from empresas.email_backend import set_current_empresa
        set_current_empresa(None)

        return response
