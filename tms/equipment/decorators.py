from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .models import Equipment

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

def is_in_role(user, role):
    return determine_user_role(user) == role

def role_required(*roles):
    """
    Decorator for views that checks if the user is in the specified role.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            user_role = determine_user_role(request.user)
            if user_role in roles:
                return view_func(request, *args, **kwargs)
            else:
                # Redirect to a page indicating unauthorized access
                return redirect('staff_user:custom_404_page')
        return wrapped_view
    return decorator