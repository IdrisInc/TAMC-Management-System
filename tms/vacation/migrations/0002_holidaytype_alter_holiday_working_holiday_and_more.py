# Generated by Django 5.0.2 on 2024-08-09 09:13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vacation', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HolidayType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.AlterField(
            model_name='holiday',
            name='working_holiday',
            field=models.CharField(blank=True, choices=[('year', 'Mwaka'), ('maternity', 'Uzazi'), ('sick', 'Ugonjwa'), ('Malipo', 'Bila Malipo')], max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='holiday',
            name='custom_holiday_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='vacation.holidaytype'),
        ),
    ]
