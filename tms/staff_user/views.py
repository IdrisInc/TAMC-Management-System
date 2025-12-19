import re
from django.shortcuts import get_object_or_404, render,redirect
from django.contrib.auth import authenticate,login,logout,update_session_auth_hash
from django.contrib import messages
# from staff_user.models import MyUser
from django.contrib.auth.models import Group,User
from django.contrib.auth.decorators import permission_required,login_required
from django.utils.http import urlsafe_base64_encode

from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string

from django.core.validators import validate_email
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.contrib.auth import password_validation
from django.db.models import Q
from django.http import JsonResponse
from .models import UserProfile,ChatMessage # Assuming UserProfile is in the same app
from django.db import transaction
from equipment.decorators import determine_user_role

# Create your views here.

# codes toregister user

def index(request):
    
    return render(request,'index.html')

@permission_required('auth.add_user', raise_exception=True)
def user_registration(request):
    roles = Group.objects.all()

    if request.method == 'POST':
        # Collect data
        username = request.POST.get('username','').strip()
        email = request.POST.get('email','').strip()
        password = request.POST.get('password1')
        password_confirm = request.POST.get('password2')
        position = request.POST.get('position')
        first_name = request.POST.get('first_name').strip()
        last_name = request.POST.get('last_name').strip()
        middle_name = request.POST.get('middle_name')
        phone_number = request.POST.get('phone_number')
        gender = request.POST.get('gender')
        nida_number = request.POST.get('nida_number')

        # Validate Password
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return redirect('staff_user:user_registration')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('staff_user:user_registration')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('staff_user:user_registration')

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('staff_user:user_registration')

        if not re.match(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()_+]).{8,}$', password):
            messages.error(request, 'Password must contain at least one digit, one uppercase letter, one lowercase letter, and one special character.')
            return redirect('staff_user:user_registration')

        # Check if Phone Number is Unique
        if UserProfile.objects.filter(phone_number=phone_number).exists():
            messages.error(request, 'Phone number already exists.')
            return redirect('staff_user:user_registration')

        try:
            with transaction.atomic():
                # Create the User object
                user = User.objects.create_user(
                    username=username, 
                    email=email, 
                    password=password,
                    first_name=first_name, 
                    last_name=last_name
                )

                # Assign the user to a group
                group = Group.objects.get(name=position)
                user.groups.add(group)

                # Create the UserProfile with additional fields
                profile = user.profile
                profile.middle_name =middle_name,
                profile.phone_number = phone_number
                profile.gender = gender
                profile.nida_number = nida_number
                profile.save()

            messages.success(request, 'User registered successfully.')
            return redirect('staff_user:registered_users')

        except Exception as e:
            messages.error(request, f'Error registering user: {e}')
            return redirect('staff_user:user_registration')

    context = {'roles': roles}
    return render(request, 'register.html', context)


# registration ends here


#  Codes to login
def login_process(request):
    if request.method== 'POST':
        username= request.POST.get ('username')  
        password= request.POST.get ('password')
      
        user=authenticate(request,username=username,password=password)
        
        if user is not None:
            login(request, user)
            
            # Get full name or fallback to username
            full_name = user.get_full_name() or user.username
            
            messages.success(request, 'Welcome ' + full_name)
            return redirect('staff_user:staff/dashboard')
        else:
            messages.error(request, 'User not found')
            return redirect('staff_user:staff_login_process')

    
    else:
       return render(request,'login.html',{})
#    login ends here
@login_required(login_url='staff_user:staff_login_process')
def view_registered_users(request):
    search_query = request.GET.get('search_query')
    role_id = request.GET.get('role')
    status = request.GET.get('status')
    roles = Group.objects.all()
    users= User.objects.all()
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains='search_query')
        )
    if role_id:
        users = users.filter(groups__id=role_id)
    
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    users = users.distinct()
    paginator = Paginator(users, 10)  # 10 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
     'users': page_obj,
      'roles':roles
        }
    if request.headers.get('HX-Request')== 'true':
        return render(request,'registered_user.html',context)

    return render(request, 
                  'registered_user.html', 
                 context
                  )
    
# dashboard start here
@login_required(login_url='staff_user:staff_login_process') 
def dashboard(request):
  

    return render(request, 'staff/dashboard.html')

# Dashboard ends here

# Password Reset start here

def password_reset_form(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = User.objects.filter(email=email).first()
        if user:
            # Generate a password reset token
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            # Construct the password reset link
            reset_link = request.build_absolute_uri(f'/reset/{uid}/{token}/')
            # Send the password reset email
            subject = 'Password Reset Request'
            message = render_to_string('pass_email_reset.html', {
                'reset_link': reset_link,
            })
            send_mail(subject, message, 'allyidrisaally@gmail.com.com', [email])
            messages.success(request, 'Password reset instructions have been sent to your email address.')
            return redirect('password_reset_done')
        else:
            messages.error(request, 'User with that email address does not exist.')
            return redirect('password_reset')
    return render(request, 'pass_reset.html')


def password_reset_done(request):
    return render(request, 'emails/email_send.html')


def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            # Handle the password reset form submission
            new_password = request.POST.get('password')
            confirm_password = request.POST.get('password_confirm')
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return redirect('password_reset_confirm', uidb64=uidb64, token=token)
            if len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
                return redirect('password_reset_confirm', uidb64=uidb64, token=token)
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Your password was successfully updated!')
            return redirect('password_reset_complete')
        return render(request, 'password_reset_confirm.html')
    else:
        messages.error(request, 'The password reset link is invalid.')
        return redirect('password_reset_done')


def password_reset_complete(request):
    return render(request, 'password_reset_complete.html')

@login_required(login_url='staff_user:staff_login_process')
def view_user_profile(request):
    try:
        # Get the profile of the logged-in user
        profile = UserProfile.objects.get(user=request.user)

        # Render the profile template
        context = {
            'profile': profile,
        }
        return render(request, 'staff/new_profile.html', context)

    except UserProfile.DoesNotExist:
        # Handle the case when the user doesn't have a profile
        messages.error(request, 'Your profile is missing. Please contact support.')
        return render(request, 'staff_user/profile_missing.html', {})


@login_required(login_url='staff_user:staff_login_process')
def update_profile(request):
    user = request.user

    try:
        profile = UserProfile.objects.get(user=user)

        if request.method == 'POST':
            # User fields
            user.email = request.POST.get('email', '')
            user.first_name = request.POST.get('first_name', '')
            user.middle_name = request.POST.get('middle_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.username = request.POST.get('username', '')

            # Check username uniqueness
            if User.objects.filter(username=user.username).exclude(pk=user.pk).exists():
                messages.error(request, 'Username is already taken.')
                return redirect('staff_user:update_profile')

            # Check email uniqueness
            if User.objects.filter(email=user.email).exclude(pk=user.pk).exists():
                messages.error(request, 'Email is already in use.')
                return redirect('staff_user:update_profile')

            # Profile fields
            profile.phone_number = request.POST.get('phone_number', '')
            profile.nida_number = request.POST.get('nida_number', '')

            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']

            user.save()
            profile.save()

            messages.success(request, 'Profile updated successfully!')
            return redirect('staff_user:my_profile')

        context = {
            'user': user,
            'profile': profile,
        }
        return render(request, 'staff/new_profile_update.html', context)

    except UserProfile.DoesNotExist:
        messages.error(request, 'Your profile is missing. Please contact support.')
        return redirect('staff_user:user_profile')

def view_user_detail(request, user_id):
    profile = get_object_or_404(UserProfile, user__id=user_id)
    
    return render(
        request,
        'staff/new_profile_update.html',
        {
            'profile':profile
        }
    )

@login_required(login_url='staff_user:staff_login_process')
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        new_password_confirm = request.POST.get('new_password_confirm')

        # Validate new password
        if new_password != new_password_confirm:
            messages.error(request, 'New passwords do not match.')
            return redirect('staff_user:change_password')

        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('staff_user:change_password')

        if not re.match(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()_+]).{8,}$', new_password):
            messages.error(request, 'Password must contain at least one digit, one uppercase letter, one lowercase letter, and one special character.')
            return redirect('staff_user:change_password')

        user = request.user

        if not user.check_password(old_password):
            messages.error(request, 'Old password is incorrect.')
            return redirect('staff_user:change_password')

        if old_password == new_password:
            messages.error(request, 'New password cannot be the same as the old password.')
            return redirect('staff_user:change_password')

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)  # Keep the user logged in after password change

        messages.success(request, 'Password changed successfully.')
        return redirect('staff_user:my_profile')  # Ensure this matches the name in your URL patterns

    return render(request, 'change_password.html')

@login_required
def chat_view(request):
    if request.method == "POST":
        message = request.POST.get('message')
        if message:
            ChatMessage.objects.create(user=request.user, message=message)
            return redirect('staff_user:message_success')  # Redirect to success page

    return render(request, 'staff/chat.html')

@login_required
def fetch_messages(request):
    if request.user.is_superuser:
        messages = ChatMessage.objects.all().values('user__username', 'message', 'timestamp')
    else:
        messages = ChatMessage.objects.filter(user=request.user).values('user__username', 'message', 'timestamp')
    return JsonResponse({'messages': list(messages)})


@login_required
def message_success(request):
    return render(request, 'staff/success.html')

# Logout start here
@login_required(login_url='staff_user:staff_login_process')
def logout_user(request):
    logout(request)
    return redirect('staff_user:welcome')

def custom_404_page(request, exception=None):
    return render(request, 'base/404.html', status=404)
