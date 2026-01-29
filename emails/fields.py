# emails/fields.py

from django.db.models import ImageField
from custom_storage.backends import CustomRemoteStorage

class RemoteImageField(ImageField):
    def __init__(self, *args, **kwargs):
        kwargs['storage'] = CustomRemoteStorage()
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Rimuovi l'oggetto storage dalle kwargs perché non è serializzabile
        kwargs.pop('storage', None)
        return name, path, args, kwargs

