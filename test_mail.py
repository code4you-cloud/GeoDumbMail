import os
import django

# Imposta la variabile d'ambiente per Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GeoDumbMail.settings')
django.setup()

from django.core.mail import send_mail

send_mail(
        'Test Email',
        'Questo è un messaggio di prova.',
        'info@citylog.cloud',  # EMAIL_HOST_USER
        ['report@citylog.cloud'],
        fail_silently=False,

)

