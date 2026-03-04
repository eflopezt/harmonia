"""
Middleware del sistema Harmoni.
"""
from core.audit import set_current_request


class AuditMiddleware:
    """Captura el request actual en thread-local storage para uso por el sistema de auditoría.

    Esto permite que signals y servicios accedan al usuario y IP
    sin necesidad de recibir el request explícitamente.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        response = self.get_response(request)
        set_current_request(None)
        return response
