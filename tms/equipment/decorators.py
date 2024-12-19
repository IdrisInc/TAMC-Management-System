from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib.auth.models import Group

def determine_user_role(user):
    """
    Determine the user's role based on their group memberships.
    Returns the role name as a string or 'Unknown' if not found.
    """
    user_groups = user.groups.values_list('name', flat=True)
    # If using a dynamic list of roles, you can fetch from the Group model
    roles = Group.objects.values_list('name', flat=True)  # Fetch all role names

    return next((group for group in roles if group in user_groups), 'Unknown')

def is_in_role(user, role):
    """
    Check if the user has the specified role.
    """
    return determine_user_role(user) == role

def role_required(*roles, redirect_url='staff_user:custom_404_page'):
    """
    Decorator for views that checks if the user is in the specified role(s).
    Redirects to the specified URL if the user does not have the required role.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='staff_user:staff_login_process')  # Ensure user is logged in
        def wrapped_view(request, *args, **kwargs):
            user_role = determine_user_role(request.user)
            if user_role in roles:
                return view_func(request, *args, **kwargs)
            else:
                # Redirect to a page indicating unauthorized access
                return redirect(redirect_url)
        return wrapped_view
    return decorator
