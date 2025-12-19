from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Holiday, HolidayType, OverlayDescription, Overlay,ProgramCount,PermissionRequest
from django.contrib.auth.models import User, Group
from pro.models import Program
from django.utils.timezone import now
from django.http import HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.core.paginator import Paginator
from collections import OrderedDict
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.contrib import messages
from datetime import datetime
from django.utils.dateparse import parse_date
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods,require_POST
from django.urls import reverse
from .tasks import delete_rejected_holiday,delete_rejected_permission_request
logger = logging.getLogger(__name__)

@login_required(login_url='staff_user:staff_login_process')
def vacation_home(request):
    
    return render (request,'vacation_home.html')

@login_required(login_url='staff_user:staff_login_process')
def holiday_create(request, holiday_id=None):
    user = request.user
    user_groups = set(user.groups.values_list('name', flat=True))

    # Check if user is in Presenter or Production groups
    is_presenter_or_production = 'Radio / TV Presenter' in user_groups or 'Production Manager' in user_groups
    overlay = Overlay.objects.first()

    # Fetch the holiday if holiday_id is provided
    holiday = get_object_or_404(Holiday, id=holiday_id) if holiday_id else None

    # Check if the user has an approved holiday
    has_approved_holiday = Holiday.objects.filter(
        user=user,
        status='approved'
    ).exists()

    if request.method == 'POST':
        # Get form inputs
        address = request.POST.get('address')
        working_holiday = request.POST.get('working_holiday')
        custom_holiday = request.POST.get('custom_holiday')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        my_last_holiday_start = request.POST.get('my_last_holiday_start')
        my_last_holiday_end = request.POST.get('my_last_holiday_end')
        current_address = request.POST.get('current_address')
        delegatee_id = request.POST.get('delegatee')
        my_tasks = request.POST.getlist('my_tasks[]')  # Retrieve "My Tasks"

        # Handle custom holiday type input
        if working_holiday == 'other':
            if not custom_holiday.strip():
                users_in_same_group = User.objects.filter(groups__name__in=user_groups).exclude(id=user.id)
                return render(request, 'holiday/holiday.html', {
                    'error_message': 'Please specify a custom holiday type.',
                    'holiday_type_choices': Holiday.HOLIDAY_TYPE_CHOICES,
                    'is_presenter_or_production': is_presenter_or_production,
                    'users_in_same_group': users_in_same_group,
                    'overlay': overlay,
                    'has_approved_holiday': has_approved_holiday,
                })
            
            custom_holiday_type, created = HolidayType.objects.get_or_create(name=custom_holiday.strip())
            final_holiday_type = custom_holiday_type
        else:
            final_holiday_type = working_holiday

        # Create or update the holiday object
        if holiday is None:
            holiday = Holiday(
                user=user,
                address=address,
                working_holiday=final_holiday_type if isinstance(final_holiday_type, str) else None,
                custom_holiday_type=final_holiday_type if isinstance(final_holiday_type, HolidayType) else None,
                start_date=start_date,
                end_date=end_date,
                my_last_holiday_start=my_last_holiday_start,
                my_last_holiday_end=my_last_holiday_end,
                current_address=current_address,
                delegatee_id=delegatee_id,
                my_tasks=', '.join(task.strip() for task in my_tasks if task.strip())  # Store tasks as comma-separated
            )
        else:
            holiday.address = address
            holiday.working_holiday = final_holiday_type if isinstance(final_holiday_type, str) else holiday.working_holiday
            holiday.custom_holiday_type = final_holiday_type if isinstance(final_holiday_type, HolidayType) else holiday.custom_holiday_type
            holiday.start_date = start_date
            holiday.end_date = end_date
            holiday.my_last_holiday_start = my_last_holiday_start
            holiday.my_last_holiday_end = my_last_holiday_end
            holiday.current_address = current_address
            holiday.delegatee_id = delegatee_id
            holiday.my_tasks = ', '.join(task.strip() for task in my_tasks if task.strip())  # Update tasks

        holiday.save()

        return redirect('vacation:view_holidays')
    else:
        # Prepare context for GET request
        users_in_same_group = User.objects.filter(groups__name__in=user_groups).exclude(id=user.id)

        context = {
            'holiday_type_choices': Holiday.HOLIDAY_TYPE_CHOICES,
            'is_presenter_or_production': is_presenter_or_production,
            'users_in_same_group': users_in_same_group,
            'overlay': overlay,
            'holiday': holiday,
            'has_approved_holiday': has_approved_holiday,
        }
        return render(request, 'holiday/holiday.html', context)



from django.utils.html import escape  # for safely displaying tasks
@login_required(login_url='staff_user:staff_login_process')
def view_holidays(request):
    user = request.user
    user_groups = set(user.groups.values_list('name', flat=True))

    # Search query and pagination parameters
    query = request.GET.get('q', '')
    page_number = request.GET.get('page', 1)

    # Fetch holidays based on user role
    holidays_for_approval = get_holidays_based_on_role(user_groups)

    # Fetch user's related holidays
    user_holidays = Holiday.objects.filter(user=user)
    approved_delegated_holidays = Holiday.objects.filter(delegatee=user, status='approved')
    delegated_holidays = Holiday.objects.filter(delegatee=user, status='pending')

    # Add program details (name and count) to holidays using the custom function
    user_holidays = add_program_counts_to_holidays(user_holidays)
    approved_delegated_holidays = add_program_counts_to_holidays(approved_delegated_holidays)
    delegated_holidays = add_program_counts_to_holidays(delegated_holidays)
    holidays_for_approval = add_program_counts_to_holidays(holidays_for_approval)

    # Apply search filter
    user_holidays = filter_holidays_by_query(user_holidays, query)
    approved_delegated_holidays = filter_holidays_by_query(approved_delegated_holidays, query)
    delegated_holidays = filter_holidays_by_query(delegated_holidays, query)
    holidays_for_approval = filter_holidays_by_query(holidays_for_approval, query)

    # Extract tasks from 'my_tasks' field for each holiday
    for holiday in user_holidays:
        holiday.tasks_list = holiday.my_tasks.split(',') if holiday.my_tasks else []

    # Pagination for user_holidays
    paginator = Paginator(user_holidays, 10)  # Show 10 holidays per page
    user_holidays_page = paginator.get_page(page_number)

    # Determine which switches to show based on the user's roles
    visible_switches = determine_visible_switches(user_groups)

    context = {
        'user_holidays': user_holidays_page,
        'approved_delegated_holidays': approved_delegated_holidays,
        'delegated_holidays': delegated_holidays,
        'holidays_for_approval': holidays_for_approval,
        'search_query': query,  # Pass search query to the template for pre-filling search fields
        'visible_switches': visible_switches,
    }

    # Check if the request is AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'holidays': list(user_holidays_page.object_list.values(
                'id', 
                'address', 
                'holiday_type', 
                'delegatee__full_name', 
                'start_date', 
                'end_date', 
                'status', 
                'program_counts_display',
                'my_tasks'  # include my_tasks field
            )),
            'has_previous': user_holidays_page.has_previous(),
            'has_next': user_holidays_page.has_next(),
            'current_page': user_holidays_page.number,
            'previous_page_number': user_holidays_page.previous_page_number() if user_holidays_page.has_previous() else None,
            'next_page_number': user_holidays_page.next_page_number() if user_holidays_page.has_next() else None,
            'total_pages': paginator.num_pages,
        })

    return render(request, 'holiday/new_view_holiday.html', context)


def determine_visible_switches(user_groups):
    switches = {
        'show_delegated_holidays': False,
        'show_approved_delegated_holidays': False,
        'show_holidays_for_approval': False,
        'show_user_holidays': True,  # Ensure this switch is passed in context
    }

    # Toggle visibility based on user roles
    if 'Production Manager' in user_groups or 'Technical Manager' in user_groups:
        switches['show_holidays_for_approval'] = True

    if 'Treasurer' in user_groups or 'Assistant Treasurer' in user_groups:
        switches['show_approved_delegated_holidays'] = True

    if 'Radio / TV Presenter' in user_groups:
        switches['show_delegated_holidays'] = True

    return switches




def get_holidays_based_on_role(user_groups):
    if 'Production Manager' in user_groups:
        return get_holidays_for_production_approval()
    elif 'Technical Manager' in user_groups:
        return get_holidays_for_technical_manager_approval()
    elif 'Treasurer' in user_groups:
        return get_holidays_for_treasurer_approval()
    elif 'Managing Director' in user_groups:
        return get_holidays_for_director_approval()
    return Holiday.objects.none()  # Default to an empty queryset if no roles match

def filter_holidays_by_query(holidays, query):
    if query:
        return holidays.filter(Q(address__icontains=query) | Q(holiday_type__icontains=query))
    return holidays

def get_holidays_for_production_approval():
    return Holiday.objects.filter(
        Q(user__groups__name='Radio / TV Presenter', status='pending', delegatee__isnull=True) |
        Q(delegatee__groups__name='Radio / TV Presenter', status='Under Review', delegatee_approved=True)
    )

def get_holidays_for_technical_manager_approval():
    return Holiday.objects.filter(
        Q(user__groups__name='Technical Manager', status='pending', delegatee__isnull=True) |
        Q(delegatee__groups__name='Technician', status='Under Review', delegatee_approved=True)
    )

def get_holidays_for_treasurer_approval():
    return Holiday.objects.filter(
        Q(user__groups__name__in=['Cashier', 'Accountant'], status='pending', delegatee__isnull=True) |
        Q(delegatee__groups__name__in=['Cashier', 'Accountant'], status='Under Review', delegatee_approved=True)
    )

def get_holidays_for_director_approval():
    return Holiday.objects.filter(
        Q(user__groups__name='Radio / TV Presenter', production_approved=True, status='Under Review') |
        Q(user__groups__name='Technician', technical_manager_approved=True, status='Under Review') |
        Q(user__groups__name__in=['Cashier', 'Accountant'], treasurer_approved=True, status='Under Review')
    )

def add_program_counts_to_holidays(holidays):
    # Create a dictionary to hold program counts for each holiday
    holiday_ids = [holiday.id for holiday in holidays]
    program_counts_dict = {}

    # Fetch all program counts for the holidays in one query to avoid multiple database hits
    program_counts = ProgramCount.objects.filter(holiday__id__in=holiday_ids).select_related('holiday')

    # Populate the dictionary with holiday IDs and their respective program counts
    for program in program_counts:
        if program.holiday.id not in program_counts_dict:
            program_counts_dict[program.holiday.id] = []
        program_counts_dict[program.holiday.id].append(f"{program.program_name} ({program.count})")

    # Loop through holidays to attach program counts
    for holiday in holidays:
        # Join the program counts for the specific holiday
        holiday.program_counts_display = ', '.join(program_counts_dict.get(holiday.id, ["No programs"]))
    
    return holidays




@login_required(login_url='staff_user:staff_login_process')
def edit_holiday(request, id):
    # Fetch the holiday instance for the current user
    holiday = get_object_or_404(Holiday, id=id, user=request.user)

    # Check if the holiday status is 'pending' for editing
    if holiday.status != 'pending':
        return HttpResponseForbidden("You cannot edit this request.")

    # Get the user groups to determine if the user is a Presenter or Production Manager
    user_groups = request.user.groups.values_list('name', flat=True)
    is_presenter_or_production = 'Radio / TV Presenter' in user_groups or 'Production Manager' in user_groups

    if request.method == 'POST':
        # Update holiday fields based on form submission
        holiday.address = request.POST.get('address')
        working_holiday = request.POST.get('working_holiday')
        custom_holiday = request.POST.get('custom_holiday', '')

        if working_holiday == 'other' and custom_holiday:
            holiday.working_holiday = None
            holiday.custom_holiday_type, created = HolidayType.objects.get_or_create(name=custom_holiday)
        else:
            holiday.working_holiday = working_holiday if working_holiday != 'other' else None
            holiday.custom_holiday_type = None

        holiday.start_date = request.POST.get('start_date')
        holiday.end_date = request.POST.get('end_date')
        holiday.my_last_holiday_start = request.POST.get('my_last_holiday_start')
        holiday.my_last_holiday_end = request.POST.get('my_last_holiday_end')
        holiday.current_address = request.POST.get('current_address')

        # Handle task descriptions as a list from the form submission
        tasks_input = request.POST.getlist('my_tasks[]')
        tasks_input = [task.strip() for task in tasks_input if task.strip()]  # Remove empty tasks

        if tasks_input:
            holiday.my_tasks = ', '.join(tasks_input)  # Join the tasks into a comma-separated string
        else:
            holiday.my_tasks = ''  # Clear tasks if input is empty

        delegatee_id = request.POST.get('delegatee')
        if delegatee_id:
            holiday.delegatee = User.objects.get(id=delegatee_id)
        else:
            holiday.delegatee = None

        # Save the updated holiday instance
        holiday.save()

        # Redirect after successful update
        return redirect('vacation:view_holidays')
    else:
        # Prepare context for GET request
        holiday_type_choices = HolidayType.objects.all()
        users_in_same_group = User.objects.filter(groups__name__in=user_groups).exclude(id=request.user.id)

        # Split existing tasks into a list for display in the form
        existing_tasks = holiday.my_tasks.split(', ') if holiday.my_tasks else []

        context = {
            'holiday': holiday,
            'holiday_type_choices': holiday_type_choices,
            'users_in_same_group': users_in_same_group,
            'is_presenter_or_production': is_presenter_or_production,
            'existing_tasks': existing_tasks,  # Pass existing tasks to the context
        }
        return render(request, 'holiday/edit_holiday.html', context)




@login_required(login_url='staff_user:staff_login_process')
def delete_holiday(request, id):
    holiday = get_object_or_404(Holiday, id=id, user=request.user)
    
    # Check if the holiday status is not 'pending'
    if holiday.status != 'pending':
        return HttpResponseForbidden("You cannot delete this request.")
    
    if request.method == 'POST':
        # Delete the holiday and redirect to the user's holiday list
        holiday.delete()
        return redirect('vacation:view_holidays')

    # Render the confirmation template for GET request
    return render(request, 'holiday/confirm_delete.html', {'holiday': holiday})


@login_required(login_url='staff_user:staff_login_process')
def finalize_holiday(request, holiday_id):
    holiday = get_object_or_404(Holiday, id=holiday_id)
    
    if holiday.status == 'Under Review':
        if request.user.groups.filter(name='Managing Director').exists():
            holiday.status = 'approved'
            holiday.finalized = True
            holiday.approved_by = request.user
            holiday.save()

            # Keep other holidays under review
            other_holidays = Holiday.objects.filter(status='Under Review')
            for other_holiday in other_holidays:
                other_holiday.status = 'Under Review'
                other_holiday.save()

    return redirect('holiday:view_holidays')


@login_required(login_url='staff_user:staff_login_process')
def approve_delegatee(request, holiday_id):
    holiday = get_object_or_404(Holiday, id=holiday_id, delegatee=request.user)

    if holiday.status == 'pending':
        holiday.delegatee_approved = True
        holiday.status = 'Under Review'
        holiday.save()

    return redirect('vacation:view_holidays')







@login_required(login_url='staff_user:staff_login_process')
def reject_delegatee(request, holiday_id):
    holiday = get_object_or_404(Holiday, id=holiday_id, delegatee=request.user)

    comment = request.POST.get('comment', '')
    if not comment:
        return HttpResponseForbidden("A comment is required for rejection.")

    if holiday.status == 'pending':
        holiday.status = 'rejected'
        holiday.rejected_by = request.user
        holiday.rejection_comment = comment
        holiday.rejected_at = timezone.now()  # Track when the holiday is rejected
        holiday.save()

        # Schedule the task to delete the holiday 24 hours later
        delete_rejected_holiday.apply_async((holiday.id,), countdown=24*60*60)

    return redirect('vacation:view_holidays')

@login_required(login_url='staff_user:staff_login_process')
def approve_holiday(request, holiday_id):
    holiday = get_object_or_404(Holiday, id=holiday_id)
    user = request.user
    user_groups = set(user.groups.values_list('name', flat=True))

    # Handling comments
    comment = request.POST.get('comment', '')

    # General approval for all roles (This function will be used by different roles)
    def handle_approval(role_name, approval_flag, comment_field):
        if holiday.status != 'Under Review' or not holiday.delegatee_approved:
            return HttpResponseForbidden("Delegatee must approve the request before you can approve it.")
        
        holiday.status = 'Under Review'
        holiday.approved_by = user
        setattr(holiday, approval_flag, True)
        setattr(holiday, comment_field, comment)
        holiday.save()
        return redirect('vacation:view_holidays')

    # Approval logic for various roles
    if 'Production Manager' in user_groups and holiday.user.groups.filter(name='Radio / TV Presenter').exists():
        return handle_approval('Production Manager', 'production_manager_approved', 'production_manager_comment')

    elif 'Technical Manager' in user_groups and holiday.user.groups.filter(name='Technical').exists():
        return handle_approval('Technical Manager', 'technical_manager_approved', 'technical_manager_comment')

    elif user_groups.intersection({'Treasurer', 'Assistant Treasurer'}) and holiday.user.groups.filter(name__in=['Cashier', 'Accountant']).exists():
        return handle_approval('Treasurer', 'treasurer_approved', 'treasurer_comment')

    elif 'Marketing Officer' in user_groups and holiday.user.groups.filter(name__in=['Cook', 'Driver', 'Cleaner']).exists():
        return handle_approval('Marketing Officer', 'marketing_officer_approved', 'marketing_officer_comment')

    elif 'Managing Director' in user_groups:
        if all([
            holiday.production_manager_approved,
            holiday.technical_manager_approved,
            holiday.treasurer_approved,
            holiday.marketing_officer_approved
        ]):
            holiday.status = 'Approved'
            holiday.approved_by = user
            holiday.director_approved = True
            # Update start and end dates if provided
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            if start_date:
                holiday.start_date = start_date
            if end_date:
                holiday.end_date = end_date
            holiday.director_comment = comment
            holiday.save()
            return redirect('vacation:view_holidays')
        else:
            return HttpResponseForbidden("The holiday request hasn't been approved by all necessary managers yet.")
    
    raise PermissionDenied


@login_required(login_url='staff_user:staff_login_process')
def reject_holiday(request, holiday_id):
    holiday = get_object_or_404(Holiday, id=holiday_id)
    user = request.user

    comment = request.POST.get('comment', '')
    if not comment:
        return HttpResponseForbidden("A comment is required for rejection.")

    if holiday.status in ['pending', 'Under Review']:
        holiday.status = 'rejected'
        holiday.rejected_by = user
        holiday.rejection_comment = comment
        holiday.rejected_at = timezone.now()  # Track when the holiday is rejected
        holiday.save()

        # Schedule the task to delete the holiday 24 hours later
        delete_rejected_holiday.apply_async((holiday.id,), countdown=24*60*60)

    return redirect('vacation:view_holidays')



@login_required(login_url='staff_user:staff_login_process')
def approve_treasurer(request, holiday_id):
    holiday = get_object_or_404(Holiday, id=holiday_id)
    user = request.user

    if holiday.status == 'Under Review':
        if user.groups.filter(name='Treasurer').exists() or user.groups.filter(name= 'Assistant Treasurer' ) and holiday.user.groups.filter(name__in=['Accountant', 'Cashier']).exists():
            holiday.treasurer_approved = True
            holiday.save()
    return redirect('vacation:view_holidays')


@login_required(login_url='staff_user:staff_login_process')
def reject_treasurer(request, holiday_id):
    holiday = get_object_or_404(Holiday, id=holiday_id)
    user = request.user

    if holiday.status == 'Under Review':
        if user.groups.filter(name='Treasurer').exists() and holiday.user.groups.filter(name__in=['Accountant', 'Cashier']).exists():
            holiday.status = 'rejected'
            holiday.rejected_by = user
            holiday.save()
    return redirect('vacation:view_holidays')

@login_required(login_url='staff_user:staff_login_process')
def add_overlay_description(request):
    if request.method == 'POST':
        overlay, created = Overlay.objects.get_or_create(id=1)  # Adjust ID as needed
        
        for key, value in request.POST.items():
            if key.startswith('description-'):
                description_text = value
                if description_text:
                    description = OverlayDescription(
                        description=description_text,
                        added_by=request.user,
                        added_on=now()
                    )
                    description.save()
                    overlay.descriptions.add(description)

        return redirect('vacation:view_holidays')

    return render(request, 'holiday/description.html')

@login_required(login_url='staff_user:staff_login_process')
def overlay_description_view(request):
    # Fetch all OverlayDescription instances
    descriptions = OverlayDescription.objects.all()
    return render(request, 'holiday/description.html', {'descriptions': descriptions})


@login_required(login_url='staff_user:staff_login_process')
def create_permission(request):
    user = request.user
    user_groups = user.groups.all()
    delegatees = User.objects.filter(groups__in=user_groups).exclude(id=user.id).distinct()

    if request.method == 'POST':
        address = request.POST.get('address')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        place = request.POST.get('place')
        description = request.POST.get('description')
        delegatee_id = request.POST.get('delegatee')
        reporting_date = request.POST.get('reporting_date')
        duties = request.POST.getlist('duties[]')  # Retrieve duties as list

        errors = []
        if not all([address, start_date, end_date, place, description, reporting_date]):
            errors.append("All fields are required.")
        
        try:
            start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
            reporting_date_parsed = datetime.strptime(reporting_date, "%Y-%m-%d").date()
        except ValueError:
            errors.append("Invalid date format. Use YYYY-MM-DD.")
            return render(request, 'ruhusa/permission.html', {'delegatees': delegatees})

        if end_date_parsed <= start_date_parsed:
            errors.append("End date must be after start date.")
        if reporting_date_parsed <= end_date_parsed or reporting_date_parsed <= start_date_parsed:
            errors.append("Reporting back date must be after both the start and end dates.")

        if errors:
            messages.error(request, "Error: " + " ".join(errors))
            return render(request, 'ruhusa/permission.html', {'delegatees': delegatees})

        delegatee = User.objects.filter(id=delegatee_id, groups__in=user_groups).first() if delegatee_id else None

        # Create a new PermissionRequest and set duties as a comma-separated string
        permission_request = PermissionRequest.objects.create(
            user=user,
            address=address,
            start_date=start_date_parsed,
            end_date=end_date_parsed,
            place=place,
            description=description,
            delegatee=delegatee,
            reporting_date=reporting_date_parsed,
        )
        permission_request.set_duties(duties)
        permission_request.save()

        messages.success(request, "Permission request created successfully.")
        return redirect('vacation:view_permission_request')

    context = {
        'delegatees': delegatees,
    }
    return render(request, 'ruhusa/permission.html', context)





@login_required(login_url='staff_user:staff_login_process')
def view_permission_request(request, request_id):
    # Fetch the specific permission request
    permission_request = get_object_or_404(PermissionRequest, id=request_id)

    user = request.user
    user_is_delegatee = user == permission_request.delegatee
    user_is_requester = user == permission_request.user

    # Determine if the logged-in user is part of any special groups
    is_production = user.groups.filter(name='Production Manager').exists()
    is_technical_manager = user.groups.filter(name='Technical Manager').exists()
    is_treasurer = user.groups.filter(name='Treasurer').exists()
    is_assistant_treasurer= user.groups.filter(name='Assistant Treasurer').exists()
    is_director = user.groups.filter(name='Managing Director').exists()

    # Check if the user has permission to view the request
    if not (user_is_delegatee or user_is_requester or is_production or is_technical_manager or is_treasurer or is_director):
        return render(request, '403.html', status=403)

    # Handle form submission for approval/rejection
    if request.method == 'POST':
        action = request.POST.get('action')

        # Handle Production approval (after delegatee approval for Presenter requests)
        if is_production and permission_request.delegatee.groups.filter(name='Radio / TV Presenter').exists():
            if action == 'approve':
                permission_request.approved_by_production = True
                if permission_request.is_ready_for_director():
                    permission_request.status = 'Under Review'  # Now ready for Director review
                permission_request.save()
                messages.success(request, 'Request has been approved by Production.')

        # Handle Technical Manager approval (after delegatee approval for Technical requests)
        elif is_technical_manager and permission_request.delegatee.groups.filter(name='Technical').exists():
            if action == 'approve':
                permission_request.approved_by_technical_manager = True
                if permission_request.is_ready_for_director():
                    permission_request.status = 'Under Review'
                permission_request.save()
                messages.success(request, 'Request has been approved by Technical Manager.')

        # Handle Treasurer approval (after delegatee approval for Cashier/Accountant requests)
        elif is_treasurer and permission_request.delegatee.groups.filter(name__in=['Cashier', 'Accountant']).exists():
            if action == 'approve':
                permission_request.approved_by_treasurer = True
                if permission_request.is_ready_for_director():
                    permission_request.status = 'Under Review'
                permission_request.save()
                messages.success(request, 'Request has been approved by Treasurer.')

        # Handle Director approval
        elif is_director:
            if action == 'approve':
                permission_request.approved_by_director = True
                permission_request.status = 'Approved'
                permission_request.save()
                messages.success(request, 'Request has been approved by Director.')

        # Handle rejection by delegatee
        elif action == 'reject' and user_is_delegatee:
            permission_request.status = 'Rejected'
            permission_request.save()
            messages.success(request, 'Request has been rejected by the delegatee.')

        return redirect('vacation:view_permission_request', request_id=permission_request.id)

    # Pass the context to the template
 

    # Set context for the template
    context = {
        'own_requests': PermissionRequest.objects.filter(user=user),
        'delegated_requests': PermissionRequest.objects.filter(delegatee=user),
        'is_production': is_production,
        'is_technical_manager': is_technical_manager,
        'is_treasurer': is_treasurer,
        'is_assistant_treasurer':is_assistant_treasurer,
        'is_director': is_director,
        'user_is_delegatee': user_is_delegatee,
        'user_is_requester': user_is_requester,
        'permission_request': permission_request
    }

    return render(request, 'ruhusa/view_permission_request.html', context)




@login_required(login_url='staff_user:staff_login_process')
def edit_request(request, request_id):
    permission_request = get_object_or_404(PermissionRequest, id=request_id)

    # Check if the user has permission to edit this request
    if not (request.user == permission_request.user or request.user.groups.filter(name='Technical Manager').exists()):
        return HttpResponseForbidden("You do not have permission to edit this request.")
    
    # Get the user's groups to filter delegatees
    user_groups = request.user.groups.all()

    # Filter delegatees to ensure they are in the same role (group) as the user
    delegatees = User.objects.filter(groups__in=user_groups).exclude(id=request.user.id).distinct()
    print(delegatees)

    if request.method == 'POST':
        # Process form data
        address = request.POST.get('address')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        place = request.POST.get('place')
        description = request.POST.get('description')
        reporting_date = request.POST.get('reporting_date')
        duties = request.POST.getlist('duties[]')  # Capture the duties field
        delegatee_id = request.POST.get('delegatee')

        # Parse the dates and validate them
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)
        reporting_date = parse_date(reporting_date)

        if not start_date or not end_date or not reporting_date:
            messages.error(request, 'Please provide valid dates in the format YYYY-MM-DD.')
            return render(request, 'ruhusa/edit_permission_request.html', {
                'permission_request': permission_request,
                'delegatees': delegatees,
                'selected_delegatee_id': delegatee_id
            })

        # Update the permission request with form data
        permission_request.address = address
        permission_request.start_date = start_date
        permission_request.end_date = end_date
        permission_request.place = place
        permission_request.description = description
        permission_request.duties = duties  # Update the duties field
        permission_request.reporting_date = reporting_date

        # Assign delegatee
        if delegatee_id:
            delegatee = User.objects.filter(id=delegatee_id, groups__in=user_groups).first()
            permission_request.delegatee = delegatee if delegatee else None
        else:
            permission_request.delegatee = None

        permission_request.save()
        messages.success(request, 'Request has been updated.')
        return redirect('vacation:view_permission_request')

    # Render form with delegatees passed to template
    return render(request, 'ruhusa/edit_permission_request.html', {
        'permission_request': permission_request,
        'delegatees': delegatees,
        'selected_delegatee_id': permission_request.delegatee_id,  # Pass the selected delegatee's ID
    })




@login_required(login_url='staff_user:staff_login_process')
@require_http_methods(["DELETE"])
def delete_request(request, request_id):
    permission_request = get_object_or_404(PermissionRequest, id=request_id)
    
    if request.user == permission_request.user or request.user.is_superuser:
        permission_request.delete()
        return JsonResponse({'message': 'Request deleted successfully.'}, status=200)
    else:
        return JsonResponse({'error': 'Unauthorized'}, status=403)



@login_required(login_url='staff_user:staff_login_process')
def view_requests(request):
    user = request.user

    # Fetch the user's own requests
    own_requests = PermissionRequest.objects.filter(user=user)

    # Fetch requests where the user is the delegatee
    delegated_requests = PermissionRequest.objects.filter(delegatee=user)

    # Adding duties to own requests
    for req in own_requests:
        req.delegatee_name = req.delegatee.get_full_name() if req.delegatee else 'None'
        req.requester_name = req.user.get_full_name()
        req.duties_list = req.duties # Get duties for own requests

    # Adding duties to delegated requests
    for req in delegated_requests:
        req.delegatee_name = req.delegatee.get_full_name() if req.delegatee else 'None'
        req.requester_name = req.user.get_full_name()
        req.duties_list = req.duties # Get duties for delegated requests

    # Initialize role-based filtering
    role_based_requests = PermissionRequest.objects.none()

    # Check user roles and set role-based requests
    is_production = user.groups.filter(name='Production Manager').exists()
    is_technical_manager = user.groups.filter(name='Technical Manager').exists()
    is_treasurer = user.groups.filter(name='Treasurer').exists()
    is_assistant_treasurer = user.groups.filter(name='Assistant Treasurer').exists()
    is_director = user.groups.filter(name='Managing Director').exists()
    

    if is_production:
        role_based_requests = PermissionRequest.objects.filter(
            delegatee__groups__name='Radio / TV Presenter',
            status='Under Review',
            approved_by_delegatee=True,
            approved_by_production=False
        )
    elif is_technical_manager:
        role_based_requests = PermissionRequest.objects.filter(
            delegatee__groups__name='Technical',
            status='Under Review',
            approved_by_delegatee=True,
            approved_by_technical_manager=False
        )
    elif is_treasurer:
        role_based_requests = PermissionRequest.objects.filter(
            delegatee__groups__name__in=['Cashier', 'Accountant'],
            status='Under Review',
            approved_by_delegatee=True,
            approved_by_treasurer=False,
            approved_by_assistant_treasurer= False,
        )
        
    elif is_assistant_treasurer:
             role_based_requests = PermissionRequest.objects.filter(
            delegatee__groups__name__in=['Cashier', 'Accountant','Marketing Officer'],
            status='Under Review',
            approved_by_delegatee=True,
            approved_by_treasurer=False,
             approved_by_assistant_treasurer= False
        )
    elif is_director:
        role_based_requests = PermissionRequest.objects.filter(
            status='Under Review',
            approved_by_director=False
        ).filter(
            Q(approved_by_production=True) | 
            Q(approved_by_technical_manager=True) | 
            Q(approved_by_treasurer=True) |
            Q(approved_by_assistant_treasurer=True)
            
        )

    # Update the status based on the user's role and the approval flow
    for req in role_based_requests:
        if is_production and req.approved_by_delegatee:
            req.status = 'Under Review'
        elif is_technical_manager and req.approved_by_delegatee:
            req.status = 'Under Review'
        elif is_treasurer and req.approved_by_delegatee:
            req.status = 'Under Review'
        elif is_assistant_treasurer and req.approved_by_delegatee:
            req.status = 'Under Review'
        elif is_director and req.approved_by_production and req.approved_by_technical_manager and req.approved_by_treasurer:
            req.status = 'Approved'

        req.delegatee_name = req.delegatee.get_full_name() if req.delegatee else 'None'
        req.requester_name = req.user.get_full_name()
        req.duties_list = req.duties  # Get duties for role-based requests

    context = {
        'own_requests': own_requests,
        'delegated_requests': delegated_requests,
        'role_based_requests': role_based_requests,
        'is_production': is_production,
        'is_technical_manager': is_technical_manager,
        'is_assistant_treasurer':is_assistant_treasurer,
        'is_treasurer': is_treasurer,
        'is_director': is_director,
    }

    return render(request, 'ruhusa/view_permission_request.html', context)



@login_required
@require_POST
def approve_request(request, request_id):
    permission_request = get_object_or_404(PermissionRequest, id=request_id)

    def safe_approve(field_name):
        """Approve the request field if it hasn't been approved and Director hasn't approved."""
        if not getattr(permission_request, field_name) and not permission_request.approved_by_director:
            setattr(permission_request, field_name, True)
            permission_request.save()
            return True
        return False

    # Delegatee approval
    if request.user == permission_request.delegatee and not permission_request.approved_by_delegatee:
        permission_request.approved_by_delegatee = True
        permission_request.status = 'Under Review'
        permission_request.save()
        return JsonResponse({
            'success': True,
            'message': 'Request approved by delegatee.',
            'redirect_url': reverse('vacation:view_permission_request')
        })

    # Require delegatee approval before other approvals
    if not permission_request.approved_by_delegatee:
        return JsonResponse({'success': False, 'error': 'Delegatee must approve the request first.'}, status=403)

    # Role-based approvals
    if permission_request.delegatee.groups.filter(name__in=['Radio / TV Presenter']).exists() and \
       request.user.groups.filter(name='Production Manager').exists():
        if safe_approve('approved_by_production'):
            return JsonResponse({
                'success': True,
                'message': 'Request approved by Production.',
                'redirect_url': reverse('vacation:view_permission_request')
            })

    elif permission_request.delegatee.groups.filter(name='Technical').exists() and \
         request.user.groups.filter(name='Technical Manager').exists():
        if safe_approve('approved_by_technical_manager'):
            return JsonResponse({
                'success': True,
                'message': 'Request approved by Technical Manager.',
                'redirect_url': reverse('vacation:view_permission_request')
            })

    elif permission_request.delegatee.groups.filter(name__in=['Cashier', 'Accountant', 'Marketing Officer']).exists() and \
        request.user.groups.filter(name='Treasurer').exists():
        if not permission_request.approved_by_treasurer:
            permission_request.approved_by_treasurer = True
            permission_request.save()
            return JsonResponse({
                'success': True,
                'message': 'Request approved by Treasurer.',
                'redirect_url': reverse('vacation:view_permission_request')
            })

    elif permission_request.delegatee.groups.filter(name__in=['Cashier', 'Accountant', 'Marketing Officer']).exists() and \
        request.user.groups.filter(name='Assistant Treasurer').exists():
        if not permission_request.approved_by_assistant_treasurer:
            permission_request.approved_by_assistant_treasurer = True
            permission_request.save()
            return JsonResponse({
                'success': True,
                'message': 'Request approved by Assistant Treasurer.',
                'redirect_url': reverse('vacation:view_permission_request')
            })



    # Director approval
    if request.user.groups.filter(name='Managing Director').exists() and permission_request.is_ready_for_director():
        permission_request.finalize_approval_by_director()  # Use the dedicated method for Director approval
        return JsonResponse({
            'success': True,
            'message': 'Request approved by Director.',
            'redirect_url': reverse('vacation:view_permission_request')
        })

    return JsonResponse({'success': False, 'error': 'You are not authorized to approve this request or it has already been approved.'}, status=403)


@login_required(login_url='staff_user:staff_login_process')
@require_POST  # Ensure only POST requests are allowed
def reject_request(request, request_id):
    permission_request = get_object_or_404(PermissionRequest, id=request_id)
    
    # Check if the user has the right role to reject the request
    if request.user == permission_request.delegatee or \
       request.user.groups.filter(name__in=['Production Manager', 'Technical Manager', 'Treasurer', 'Managing Director']).exists():
        
        # Get the rejection comment (if provided in the form)
        comment = request.POST.get('comment', '')
        if not comment:
            return JsonResponse({'success': False, 'error': 'Comment is required for rejection.'}, status=400)
        
        permission_request.status = 'rejected'
        permission_request.rejection_comment = comment  # Assuming you have a field for rejection comments
        permission_request.save()

        # Schedule the task to delete the permission request 24 hours later
        delete_rejected_permission_request.apply_async((permission_request.id,), countdown=24*60*60)

        # Return JSON response if the request is made via AJAX
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'redirect_url': reverse('vacation:view_permission_request')})  # Include redirect URL
        
        # Redirect for non-AJAX request
        return redirect('vacation:view_permission_request', request_id=permission_request.id)
    
    return JsonResponse({'success': False, 'error': 'You are not authorized to reject this request.'}, status=403)