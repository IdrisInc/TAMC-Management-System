# Generated by Django 5.0.2 on 2024-04-11 19:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pro', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='selected_day',
            field=models.CharField(choices=[('sunday', 'Sunday'), ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'), ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday')], default='Sunday', max_length=10),
        ),
    ]
