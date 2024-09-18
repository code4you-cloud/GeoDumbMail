from django.db import models
from django.utils.html import mark_safe

# Create your models here.
class EmailData(models.Model):
    # Definire le opzioni per il campo 'typo'
    TIPO_SCELTE = [
        ('waste', 'Rifiuti'),
        ('notrunktree', 'Tronchi'),
        ('tree', 'Censimento'),
        ('pianta', 'Piantumazione'),
        ('hole', 'Buche'),
    ]

    latitude = models.CharField(max_length=50, blank=True, null=True)
    longitude = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    image_time = models.DateTimeField(null=True, blank=True)
    image_id = models.CharField(max_length=255, blank=True, null=True)
    image_url = models.CharField(max_length=255,null=True, blank=True)                                   # Mantieni questo se hai bisogno anche dell'URL
    image_file = models.ImageField(upload_to='uploaded_images/', null=True, blank=True)  # Campo per l'immagine salvata
    status = models.CharField(max_length=50, default='Nuovo')                            # Stato della segnalazione
    typo = models.CharField(
        max_length=20,
        choices=TIPO_SCELTE,
        default='rifiuti',  # Opzione predefinita
    )
    show_image = models.BooleanField(default=False)  # Aggiungi questo campo
    show_map = models.BooleanField(default=False)    # Aggiungi questo campo

    def image_preview(self):
        if self.image_file:
            # Costruisci il percorso dell'URL dell'immagine
            return mark_safe(f'<img src="{self.image_file.url}" width="100" height="100" />')
        elif self.image_url:
            return mark_safe(f'<img src="{self.image_url}" width="100" height="100" />')
        return "No image available"

    # Definisci la funzione per mostrare l'immagine originale
    def image_original(self):
        if self.image_url:
            return format_html(
                '<a href="{url}" target="_blank">View Full Image</a>',
                url=self.image_url
            )
        return ""

    def __str__(self):
        return f"Email from {self.city or 'unknown location'}"

