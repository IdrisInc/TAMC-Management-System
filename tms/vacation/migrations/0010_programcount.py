# Generated by Django 5.0.2 on 2024-08-19 07:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vacation', '0009_holiday_director_approved_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgramCount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('program_name', models.CharField(max_length=255)),
                ('count', models.PositiveIntegerField(default=0)),
                ('holiday', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='program_counts', to='vacation.holiday')),
            ],
        ),
    ]
