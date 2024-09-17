from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)  # Optional but unique if provided
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')], blank=True, null=True)
    nida_number = models.CharField(max_length=20, unique=True, blank=True, null=True)  # Required and unique

    def __str__(self):
        return f"{self.user.username}'s profile"

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} at {self.timestamp}: {self.message}"