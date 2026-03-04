from django.apps import AppConfig


class WorkflowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workflows'
    verbose_name = 'Flujos de Trabajo'

    def ready(self):
        # Conectar señales usando post_migrate para evitar acceso a BD durante
        # la inicialización (evita RuntimeWarning en Django 5.1+)
        from django.db.models.signals import post_migrate
        from django.dispatch import receiver

        @receiver(post_migrate, sender=self)
        def _conectar_signals_post_migrate(sender, **kwargs):
            try:
                from workflows.signals import conectar_flujos_activos
                conectar_flujos_activos()
            except Exception:
                pass
