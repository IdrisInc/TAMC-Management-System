# Generated by Django 5.0.2 on 2024-03-31 08:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0006_alter_financialrequest_slug'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='financialrequest',
            name='slug',
        ),
    ]
