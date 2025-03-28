# Generated by Django 5.0.2 on 2024-03-31 17:33

import autoslug.fields
import equipment.models
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Equipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Equipment Name')),
                ('category', models.CharField(choices=[('Audio', 'Audio'), ('Lighting', 'Lighting'), ('Power', 'Power'), ('Video', 'Video'), ('Other', 'Other')], max_length=20, verbose_name='Category')),
                ('type_model', models.CharField(choices=[('Tronic', 'Tronic'), ('Sony', 'Sony'), ('USB Capture', 'USB Capture'), ('N/A', 'N/A')], max_length=255, verbose_name='Type/Model')),
                ('serial_number', models.CharField(max_length=100, unique=True, verbose_name='Serial Number')),
                ('quantity', models.PositiveIntegerField(verbose_name='Quantity')),
                ('equipment_image', models.ImageField(upload_to=equipment.models.equipment_image_upload_path, verbose_name='Equipment Image')),
                ('slug', autoslug.fields.AutoSlugField(default='', editable=False, populate_from=equipment.models.generate_slug, unique=True)),
            ],
            options={
                'verbose_name': 'Equipment',
                'verbose_name_plural': 'Equipment',
            },
        ),
    ]
