from django.apps import AppConfig


class AsistenciaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "asistencia"
    label = "tareo"  # Mantiene compatibilidad con tablas y migraciones existentes
    verbose_name = "Asistencia y Control"

    def ready(self):
        import asistencia.signals  # noqa — registra post_save signals de badge
