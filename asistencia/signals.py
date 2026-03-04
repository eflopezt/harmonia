"""
Signals para el módulo asistencia (app label: tareo).

Responsabilidades:
  - Invalidar caché del badge de superusers cuando cambia el estado de
    RegistroPapeleta, SolicitudHE o JustificacionNoMarcaje.
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
        pass  # No interrumpir flujo principal si la caché no está disponible


# ── Papeletas ──────────────────────────────────────────────────────────────────

@receiver(post_save, sender='tareo.RegistroPapeleta')
def badge_papeleta(sender, instance, **kwargs):
    """Invalida badge al crear/modificar una papeleta."""
    _invalidar_badge_superusers()


# ── Solicitudes HE ─────────────────────────────────────────────────────────────

@receiver(post_save, sender='tareo.SolicitudHE')
def badge_solicitud_he(sender, instance, **kwargs):
    """Invalida badge al crear/modificar una solicitud de HE."""
    _invalidar_badge_superusers()


# ── Justificaciones ────────────────────────────────────────────────────────────

@receiver(post_save, sender='tareo.JustificacionNoMarcaje')
def badge_justificacion(sender, instance, **kwargs):
    """Invalida badge al crear/modificar una justificación de no marcaje."""
    _invalidar_badge_superusers()
