# Generated by Django 5.0.2 on 2024-10-25 06:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vacation', '0019_holiday_my_tasks'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='permissionrequest',
            name='duties',
        ),
        migrations.AddField(
            model_name='permissionrequest',
            name='duties',
            field=models.CharField(default='Not Specified', max_length=500),
        ),
    ]
