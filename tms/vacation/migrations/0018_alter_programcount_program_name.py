# Generated by Django 5.0.2 on 2024-10-10 07:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vacation', '0017_alter_holiday_status_alter_permissionrequest_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='programcount',
            name='program_name',
            field=models.CharField(max_length=255, verbose_name='Program Name'),
        ),
    ]
