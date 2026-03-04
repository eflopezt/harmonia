from django.apps import AppConfig


class VacacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vacaciones'
    verbose_name = 'Vacaciones y Permisos'

    def ready(self):
        import vacaciones.signals  # noqa — registra post_save signals de badge
