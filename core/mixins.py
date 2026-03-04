"""
Mixins compartidos para vistas del sistema Harmoni.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect

from core.constants import ROL_ADMIN, ROL_RESPONSABLE, ROL_COLABORADOR


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Solo permite acceso a superusuarios (administradores)."""

    def test_func(self):
        return self.request.user.is_superuser


class ResponsableRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Permite acceso a superusuarios y responsables de área."""

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        return hasattr(user, 'personal_data') and user.personal_data and \
            user.personal_data.areas_responsable.exists()


class ColaboradorRequiredMixin(LoginRequiredMixin):
    """Permite acceso a cualquier usuario autenticado con personal vinculado."""

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'personal_data') or not request.user.personal_data:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


def get_user_role(user):
    """Determina el rol del usuario en el sistema."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return ROL_ADMIN
    if not hasattr(user, 'personal_data') or not user.personal_data:
        return None
    if user.personal_data.areas_responsable.exists():
        return ROL_RESPONSABLE
    return ROL_COLABORADOR
