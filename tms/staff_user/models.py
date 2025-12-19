from django.contrib.auth.models import User
from django.db import models

from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    middle_name =models.CharField(max_length=20, blank= True)
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')], blank=True, null=True)
    nida_number = models.CharField(max_length=20, unique=True, blank=True, null=True)

    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True,
        default='default_pics/hope.png'  # Make sure this file exists in media/default_pics/
    )

    def __str__(self):
        return f"{self.user.username}'s profile"

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} at {self.timestamp}: {self.message}"