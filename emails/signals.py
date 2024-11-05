# signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import EmailData
from django.conf import settings

@receiver(post_save, sender=EmailData)
def send_notification_email(sender, instance, created, **kwargs):
    if created:
        # Preparare i dati dell'email
        subject = f"Nuova segnalazione email ricevuta: {instance.id}"
        message = (
            f"È stata aggiunta una nuova segnalazione.\n"
            f"Dettagli:\n"
            f"Città: {instance.city}\n"
            f"Indirizzo: {instance.address}\n"
            f"Tipo di segnalazione: {instance.typo}\n"
            f"Status: {instance.status}"
        )
        recipient_list = ['system@code4you.cloud']  # Inserisci il tuo indirizzo di destinazione

        # Inviare l'email
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )

