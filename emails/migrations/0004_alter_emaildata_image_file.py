# Generated by Django 5.1 on 2024-08-27 11:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0003_alter_emaildata_city_alter_emaildata_image_file"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emaildata",
            name="image_file",
            field=models.ImageField(
                blank=True, null=True, upload_to="uploaded_images/"
            ),
        ),
    ]