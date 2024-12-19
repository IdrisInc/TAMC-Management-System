from django.contrib.auth.models import Group

# Role recognition
from django.contrib.auth.models import Group

def determine_user_role(user):
    # Get all group names
    all_roles = Group.objects.values_list('name', flat=True)

    # Loop through the user's groups and return the first matching role
    user_groups = user.groups.values_list('name', flat=True)  # Get the group names for the user
    for role in all_roles:
        if role in user_groups:
            return role

    return 'Unknown'
