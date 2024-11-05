from django.core.management.base import BaseCommand
from emails.utils import elimina_immagini_orfane  # Importa la funzione

class Command(BaseCommand):
    help = 'Elimina immagini orfane da temp_image e upload_images'

    def handle(self, *args, **options):
        elimina_immagini_orfane()
        self.stdout.write(self.style.SUCCESS("Immagini orfane eliminate con successo"))

