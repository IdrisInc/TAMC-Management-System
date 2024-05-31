from django.contrib.auth.models import Group

# Role recognition
def determine_user_role(user):
    # Implement logic to determine user role based on groups or other criteria
    # For example:
    if user.groups.filter(name='Production').exists():
        return 'Production'
    elif user.groups.filter(name='Finance').exists():
        return 'Finance'
    elif user.groups.filter(name='Treasurer').exists():
        return 'Treasurer'
    elif user.groups.filter(name='Cashier').exists():
        return 'Cashier'
    elif user.groups.filter(name='Presenter').exists():
        return 'Presenter'
    elif user.groups.filter(name='Technical').exists():
        return 'Technical'
    elif user.groups.filter(name='Technical Manager').exists():
        return 'Technical Manager'
    elif user.groups.filter(name='Director').exists():
        return 'Director'
    else:
        return 'Unknown'
