# Generated by Django 5.0.2 on 2024-06-16 18:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0006_remove_taskassignment_persons_required'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskassignment',
            name='cashier_approved',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='taskassignment',
            name='production_approved',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='taskassignment',
            name='technical_approved',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='taskassignment',
            name='treasurer_approved',
            field=models.BooleanField(default=False),
        ),
    ]
