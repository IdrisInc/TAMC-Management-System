# Generated by Django 5.0.2 on 2024-10-27 07:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vacation', '0020_remove_permissionrequest_duties_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Duty',
        ),
        migrations.AddField(
            model_name='permissionrequest',
            name='approved_by_assistant_treasurer',
            field=models.BooleanField(default=False),
        ),
    ]
