import os
from django.conf import settings
from .models import EmailData

def elimina_immagini_orfane():
    # Raccogli i nomi dei file delle immagini presenti nel database
    immagini_database = set(email.image_file.name for email in EmailData.objects.exclude(image_file='').only('image_file'))

    # Percorsi delle directory
    temp_image_dir = os.path.join(settings.BASE_DIR, 'temp_images')
    upload_images_dir = os.path.join(settings.MEDIA_ROOT, 'uploaded_images')

    # Elimina immagini orfane in temp_image
    for file_name in os.listdir(temp_image_dir):
        temp_image_path = os.path.join(temp_image_dir, file_name)
        if file_name not in immagini_database:
            os.remove(temp_image_path)
            print(f"Immagine orfana rimossa: {temp_image_path}")

    # Elimina immagini orfane in upload_images
    for file_name in os.listdir(upload_images_dir):
        upload_image_path = os.path.join(upload_images_dir, file_name)
        if file_name not in immagini_database:
            os.remove(upload_image_path)
            print(f"Immagine orfana rimossa: {upload_image_path}")

