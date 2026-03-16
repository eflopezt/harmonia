"""
Email backend multi-tenant — envía correo usando la configuración SMTP
de la empresa activa en la sesión del request actual.

Si no hay empresa activa o no tiene SMTP configurado,
cae al backend default de Django (settings.EMAIL_*).

Uso en settings:
    EMAIL_BACKEND = 'empresas.email_backend.EmpresaEmailBackend'
"""
import threading

from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend

# Thread-local storage para pasar la empresa al backend sin request
_current_empresa = threading.local()


def set_current_empresa(empresa):
    """Establece la empresa para el hilo actual (llamar desde middleware o vista)."""
    _current_empresa.value = empresa


def get_current_empresa():
    """Obtiene la empresa del hilo actual."""
    return getattr(_current_empresa, 'value', None)


class EmpresaEmailBackend(SmtpEmailBackend):
    """
    Backend SMTP que usa la configuración de la empresa activa.
    Si la empresa no tiene SMTP, usa los settings globales de Django.
    """

    def __init__(self, **kwargs):
        empresa = get_current_empresa()

        if empresa and empresa.tiene_email_configurado:
            config = empresa.get_smtp_config()
            kwargs.setdefault('host', config['host'])
            kwargs.setdefault('port', config['port'])
            kwargs.setdefault('username', config['username'])
            kwargs.setdefault('password', config['password'])
            kwargs.setdefault('use_tls', config['use_tls'])
            kwargs.setdefault('use_ssl', config['use_ssl'])

        super().__init__(**kwargs)

    def send_messages(self, email_messages):
        empresa = get_current_empresa()

        if empresa and empresa.tiene_email_configurado:
            config = empresa.get_smtp_config()
            from_email = config['from_email']
            reply_to = config.get('reply_to')

            for msg in email_messages:
                if not msg.from_email or msg.from_email == 'webmaster@localhost':
                    msg.from_email = from_email
                if reply_to and not msg.reply_to:
                    msg.reply_to = [reply_to]

        return super().send_messages(email_messages)
