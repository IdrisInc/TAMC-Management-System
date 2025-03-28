# Generated by Django 5.0.2 on 2024-08-06 11:14

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0007_remove_financialrequest_slug'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='financialrequest',
            name='approved_by',
        ),
        migrations.RemoveField(
            model_name='financialrequest',
            name='approved_by_cashier',
        ),
        migrations.RemoveField(
            model_name='financialrequest',
            name='approved_by_finance',
        ),
        migrations.RemoveField(
            model_name='financialrequest',
            name='approved_by_production',
        ),
        migrations.RemoveField(
            model_name='financialrequest',
            name='approved_by_technical_manager',
        ),
        migrations.RemoveField(
            model_name='financialrequest',
            name='approved_by_treasurer',
        ),
        migrations.AddField(
            model_name='financialrequest',
            name='approved_by_cashier',
            field=models.ManyToManyField(blank=True, related_name='approved_by_cashier', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='financialrequest',
            name='approved_by_finance',
            field=models.ManyToManyField(blank=True, related_name='approved_by_finance', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='financialrequest',
            name='approved_by_production',
            field=models.ManyToManyField(blank=True, related_name='approved_by_production', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='financialrequest',
            name='approved_by_technical_manager',
            field=models.ManyToManyField(blank=True, related_name='approved_by_technical_manager', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='financialrequest',
            name='approved_by_treasurer',
            field=models.ManyToManyField(blank=True, related_name='approved_by_treasurer', to=settings.AUTH_USER_MODEL),
        ),
    ]
