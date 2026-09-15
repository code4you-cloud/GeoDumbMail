# core/email_backend.py
import ssl
from django.core.mail.backends.smtp import EmailBackend

class CustomEmailBackend(EmailBackend):
    def open(self):
        if self.connection:
            return False
        try:
            # Crea un contesto SSL senza verifica
            ssl_context = ssl._create_unverified_context()
            self.connection = self.connection_class(
                self.host, self.port,
                timeout=self.timeout,
            )
            # Avvia TLS manualmente
            self.connection.starttls(context=ssl_context)
            self.connection.ehlo()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise
            return False
