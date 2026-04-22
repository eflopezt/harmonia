"""
Signals para el módulo asistencia (app label: tareo).

Responsabilidades:
  - Invalidar caché del badge de superusers cuando cambia el estado de
    RegistroPapeleta, SolicitudHE o JustificacionNoMarcaje.
"""
from django.db.models.signals import post_save, post_delete, pre_save
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

@receiver(pre_save, sender='tareo.RegistroPapeleta')
def papeleta_snapshot_previo(sender, instance, **kwargs):
    """Guarda el estado anterior de la papeleta para detectar cambios."""
    if instance.pk:
        try:
            prev = sender.objects.get(pk=instance.pk)
            instance._estado_previo = prev.estado
            instance._rango_previo = (prev.fecha_inicio, prev.fecha_fin)
            instance._tipo_previo = prev.tipo_permiso
        except sender.DoesNotExist:
            instance._estado_previo = None
            instance._rango_previo = None
            instance._tipo_previo = None
    else:
        instance._estado_previo = None
        instance._rango_previo = None
        instance._tipo_previo = None


@receiver(post_save, sender='tareo.RegistroPapeleta')
def badge_papeleta(sender, instance, created, **kwargs):
    """Sincroniza RegistroTareo + invalida badge al crear/modificar papeleta."""
    _invalidar_badge_superusers()

    # Sincronizar automáticamente los RegistroTareo según estado.
    try:
        from asistencia.services.papeletas_sync import (
            aplicar_papeleta, revertir_papeleta,
        )
        estado_previo = getattr(instance, '_estado_previo', None)
        rango_previo = getattr(instance, '_rango_previo', None)
        tipo_previo = getattr(instance, '_tipo_previo', None)

        # Si el rango o tipo cambió, revertir primero los días viejos.
        if not created and rango_previo and (
            rango_previo != (instance.fecha_inicio, instance.fecha_fin)
            or tipo_previo != instance.tipo_permiso
        ):
            # Construir una instancia "fantasma" con los valores previos
            # para revertir los días viejos.
            from copy import copy
            antigua = copy(instance)
            antigua.fecha_inicio, antigua.fecha_fin = rango_previo
            antigua.tipo_permiso = tipo_previo
            revertir_papeleta(antigua)

        if instance.estado in ('APROBADA', 'EJECUTADA'):
            aplicar_papeleta(instance)
        else:
            # PENDIENTE / RECHAZADA / ANULADA → revertir a default
            revertir_papeleta(instance)
    except Exception as exc:
        import logging
        logging.getLogger('personal.business').warning(
            f'papeletas_sync signal error (pap_id={instance.pk}): {exc}'
        )


@receiver(post_delete, sender='tareo.RegistroPapeleta')
def papeleta_eliminada(sender, instance, **kwargs):
    """Restaura RegistroTareo a default cuando se elimina una papeleta."""
    _invalidar_badge_superusers()
    try:
        from asistencia.services.papeletas_sync import revertir_papeleta
        revertir_papeleta(instance)
    except Exception as exc:
        import logging
        logging.getLogger('personal.business').warning(
            f'papeletas_sync post_delete error (pap_id={instance.pk}): {exc}'
        )


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
