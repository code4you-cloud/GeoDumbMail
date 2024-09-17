from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import EmailData

class EmailDataAdmin(admin.ModelAdmin):
    list_display = ('city', 'address', 'image_time', 'image_id', 'typo', 'image_preview')
    search_fields = ('city', 'address', 'image_id')
    list_filter = ('image_time', 'city')

    # Rendi il campo image_preview selezionabile
    readonly_fields = ('image_preview','image_original',)
    list_display_links = ('city', 'image_preview')

    def image_preview(self, obj):
        return obj.image_preview()

    image_preview.short_description = 'Image Preview'
    image_preview.allow_tags = True

    def image_original(self, obj):
        return obj.image_url

    image_original.short_description = 'Source Image'
    image_original.allow_tags = True


    # Aggiungi il campo per la visualizzazione dell'anteprima
    #fields = ('latitude', 'longitude', 'city', 'address', 'image_time', 'image_id', 'image_url', 'image_file')
    #readonly_fields = ('image_file_preview',)

admin.site.register(EmailData, EmailDataAdmin)

