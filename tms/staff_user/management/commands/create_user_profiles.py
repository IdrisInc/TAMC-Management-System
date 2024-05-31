from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from staff_user.models import UserProfile

class Command(BaseCommand):
    help = 'Create UserProfile for users without one'

    def handle(self, *args, **kwargs):
        # Find users who don't have a profile
        users_without_profiles = User.objects.filter(profile__isnull=True)
        count = 0
        # Create profiles for these users
        for user in users_without_profiles:
            UserProfile.objects.create(user=user)
            count += 1
        self.stdout.write(self.style.SUCCESS(f'UserProfiles created for {count} users without profiles'))
