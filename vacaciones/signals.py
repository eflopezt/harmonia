"""
Signals para el módulo vacaciones.

Responsabilidades:
  - Invalidar caché del badge de superusers cuando cambia el estado de
    SolicitudVacacion o SolicitudPermiso.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


def _invalidar_badge_superusers():
    """Borra el caché del badge de todos los superusers activos."""
    try:
        from django.core.cache import cache
        from django.contrib.auth.models import User
        pks = User.objects.filter(
            is_superuser=True, is_active=True
        ).values_list('pk', flat=True)
        cache.delete_many([f'harmoni_badge_{pk}_v3' for pk in pks])
    except Exception:
        pass


# ── Solicitudes de Vacación ────────────────────────────────────────────────────

@receiver(post_save, sender='vacaciones.SolicitudVacacion')
def badge_solicitud_vacacion(sender, instance, **kwargs):
    """Invalida badge al crear/modificar una solicitud de vacación."""
    _invalidar_badge_superusers()


# ── Solicitudes de Permiso ─────────────────────────────────────────────────────

@receiver(post_save, sender='vacaciones.SolicitudPermiso')
def badge_solicitud_permiso(sender, instance, **kwargs):
    """Invalida badge al crear/modificar una solicitud de permiso."""
    _invalidar_badge_superusers()
