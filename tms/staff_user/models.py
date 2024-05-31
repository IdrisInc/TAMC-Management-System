from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    # This establishes a one-to-one relationship with the default User model.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Adding custom fields
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # Field for phone number
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')], blank=True, null=True)  # Gender with predefined choices
    nida_number = models.CharField(max_length=20, unique=True, blank=True, null=True)  # National ID number, set to be unique

    def __str__(self):
        return f"{self.user.username}'s profile"


class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} at {self.timestamp}: {self.message}"