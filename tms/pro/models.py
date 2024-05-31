from django.db import models

class Program(models.Model):
    DAY_CHOICES = (
        ('sunday', 'Sunday'),
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
    )
    selected_day = models.CharField(max_length=10, choices=DAY_CHOICES,default='Sunday')  # Add selected_day field
    time_and_date = models.DateTimeField()
    program_name = models.CharField(max_length=255)
    STATUS_CHOICES = (
        ('played', 'Played'),
        ('running', 'Running'),
        ('next', 'Next'),
        ('not_played', 'Not Played'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='not_played')
    IS_NEW_CHOICES = (
        ('new', 'New'),
        ('repeated', 'Repeated'),
        ('live', 'Live'),  # Add 'Live' choice
    )
    is_new = models.CharField(max_length=10, choices=IS_NEW_CHOICES, default='new')

    def __str__(self):
        return f"{self.program_name} ({self.status}) - {self.time_and_date}"


    @classmethod
    def get_programs_for_day(cls, selected_day):
        return cls.objects.filter(selected_day=selected_day.capitalize()).order_by('time_and_date')