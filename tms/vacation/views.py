from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Holiday, HolidayType, OverlayDescription, Overlay,ProgramCount,PermissionRequest,Duty 
from django.contrib.auth.models import User, Group
from pro.models import Program
from django.utils.timezone import now
from django.http import HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from collections import OrderedDict
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.contrib import messages
from datetime import datetime
from django.utils.dateparse import parse_date
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods,require_POST


logger = logging.getLogger(__name__)


@login_required(login_url='staff_user:staff_login_process')
def holiday_create(request, holiday_id=None):
    user = request.user
    user_groups = set(user.groups.values_list('name', flat=True))

    is_presenter_or_production = 'Presenter' in user_groups or 'Production' in user_groups
    overlay = Overlay.objects.first()

    if holiday_id:
        holiday = get_object_or_404(Holiday, id=holiday_id)
    else:
        holiday = None

    # Check if the user has an approved holiday
    has_approved_holiday = Holiday.objects.filter(
        user=user,
        status='approved'
    ).exists()

    if request.method == 'POST':
        address = request.POST.get('address')
        working_holiday = request.POST.get('working_holiday')
        custom_holiday = request.POST.get('custom_holiday')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        my_last_holiday_start = request.POST.get('my_last_holiday_start')
        my_last_holiday_end = request.POST.get('my_last_holiday_end')
        current_address = request.POST.get('current_address')
        delegatee_id = request.POST.get('delegatee')

        if working_holiday == 'other':
            if not custom_holiday.strip():
                programs = Program.objects.values_list('program_name', flat=True).distinct()
                users_in_same_group = User.objects.filter(groups__name__in=user_groups).exclude(id=user.id)
                return render(request, 'holiday/holiday.html', {
                    'error_message': 'Please specify a custom holiday type.',
                    'holiday_type_choices': Holiday.HOLIDAY_TYPE_CHOICES,
                    'is_presenter_or_production': is_presenter_or_production,
                    'users_in_same_group': users_in_same_group,
                    'programs': programs,
                    'overlay': overlay,
                    'has_approved_holiday': has_approved_holiday,
                })
            
            custom_holiday_type, created = HolidayType.objects.get_or_create(name=custom_holiday.strip())
            final_holiday_type = custom_holiday_type
        else:
            final_holiday_type = working_holiday

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

        holiday.save()

        if is_presenter_or_production:
            holiday.program_counts.all().delete()
            
            for program_name in request.POST.getlist('programs'):
                count = request.POST.get(f'count_{program_name}')
                if count:
                    count = int(count)
                    if count > 0:
                        ProgramCount.objects.create(
                            program_name=program_name,
                            count=count,
                            holiday=holiday
                        )

        return redirect('vacation:view_holidays')
    else:
        programs = Program.objects.values_list('program_name', flat=True).distinct()
        users_in_same_group = User.objects.filter(groups__name__in=user_groups).exclude(id=user.id)

        context = {
            'holiday_type_choices': Holiday.HOLIDAY_TYPE_CHOICES,
            'is_presenter_or_production': is_presenter_or_production,
            'users_in_same_group': users_in_same_group,
            'programs': programs,
            'overlay': overlay,
            'holiday': holiday,
            'has_approved_holiday': has_approved_holiday,
        }
        return render(request, 'holiday/holiday.html', context)



@login_required(login_url='staff_user:staff_login_process')
def view_holidays(request):
    user = request.user
    user_groups = set(user.groups.values_list('name', flat=True))

    holidays_for_approval = Holiday.objects.none()

    # Determine holidays for approval based on user role
    if 'Production' in user_groups:
        holidays_for_approval = get_holidays_for_production_approval()
    elif 'Technical Manager' in user_groups:
        holidays_for_approval = get_holidays_for_technical_manager_approval()
    elif 'Treasurer' in user_groups:
        holidays_for_approval = get_holidays_for_treasurer_approval()
    elif 'Director' in user_groups:
        holidays_for_approval = get_holidays_for_director_approval()

    # Fetch user's related holidays
    user_holidays = Holiday.objects.filter(user=user)
    approved_delegated_holidays = Holiday.objects.filter(delegatee=user, status='approved')
    delegated_holidays = Holiday.objects.filter(delegatee=user, status='pending')

    # Add program details to holidays
    user_holidays = add_program_counts_to_holidays(user_holidays)
    approved_delegated_holidays = add_program_counts_to_holidays(approved_delegated_holidays)
    delegated_holidays = add_program_counts_to_holidays(delegated_holidays)
    holidays_for_approval = add_program_counts_to_holidays(holidays_for_approval)

    context = {
        'user_holidays': user_holidays,
        'approved_delegated_holidays': approved_delegated_holidays,
        'delegated_holidays': delegated_holidays,
        'holidays_for_approval': holidays_for_approval,
    }

    return render(request, 'holiday/view_holidays.html', context)

def get_holidays_for_production_approval():
    return Holiday.objects.filter(
        Q(user__groups__name='Presenter', status='pending', delegatee__isnull=True) |
        Q(delegatee__groups__name='Presenter', status='Under Review', delegatee_approved=True)
    )

def get_holidays_for_technical_manager_approval():
    return Holiday.objects.filter(
        Q(user__groups__name='Technical', status='pending', delegatee__isnull=True) |
        Q(delegatee__groups__name='Technical', status='Under Review', delegatee_approved=True)
    )

def get_holidays_for_treasurer_approval():
    return Holiday.objects.filter(
        Q(user__groups__name__in=['Cashier', 'Finance'], status='pending', delegatee__isnull=True) |
        Q(delegatee__groups__name__in=['Cashier', 'Finance'], status='Under Review', delegatee_approved=True)
    )

def get_holidays_for_director_approval():
    return Holiday.objects.filter(
        Q(user__groups__name='Presenter', production_approved=True, status='Under Review') |
        Q(user__groups__name='Technical', technical_manager_approved=True, status='Under Review') |
        Q(user__groups__name__in=['Cashier', 'Finance'], treasurer_approved=True, status='Under Review')
    )

def add_program_counts_to_holidays(holidays):
    for holiday in holidays:
        program_counts = ProgramCount.objects.filter(holiday=holiday)
        holiday.program_counts_display = {pc.program_name: pc.count for pc in program_counts}
    return holidays

@login_required(login_url='staff_user:staff_login_process')
def edit_holiday(request, id):
    holiday = get_object_or_404(Holiday, id=id, user=request.user)
    if holiday.status != 'pending':
        return HttpResponseForbidden("You cannot edit this request.")

    user_groups = request.user.groups.values_list('name', flat=True)
    is_presenter_or_production = 'Presenter' in user_groups or 'Production' in user_groups

    if request.method == 'POST':
        holiday.address = request.POST.get('address')
        working_holiday = request.POST.get('working_holiday')
        custom_holiday = request.POST.get('custom_holiday', '')

        if working_holiday == 'other' and custom_holiday:
            # Clear the working_holiday and set the custom_holiday_type
            holiday.working_holiday = None
            holiday.custom_holiday_type, created = HolidayType.objects.get_or_create(name=custom_holiday)
        else:
            holiday.working_holiday = working_holiday
            holiday.custom_holiday_type = None

        holiday.start_date = request.POST.get('start_date')
        holiday.end_date = request.POST.get('end_date')
        holiday.my_last_holiday_start = request.POST.get('my_last_holiday_start')
        holiday.my_last_holiday_end = request.POST.get('my_last_holiday_end')
        holiday.current_address = request.POST.get('current_address')

        delegatee_id = request.POST.get('delegatee')
        if delegatee_id:
            holiday.delegatee = User.objects.get(id=delegatee_id)
        else:
            holiday.delegatee = None

        holiday.save()

        if is_presenter_or_production:
            for key in request.POST:
                if key.startswith('count_'):
                    program_name = key.replace('count_', '')
                    count = int(request.POST.get(key, 0))

                    program_count, created = ProgramCount.objects.get_or_create(
                        holiday=holiday,
                        program_name=program_name,
                        defaults={'count': count}
                    )
                    if not created:
                        program_count.count = count
                        program_count.save()

        return redirect('vacation:view_holidays')

    holiday_type_choices = HolidayType.objects.all()
    programs = Program.objects.all()
    unique_programs = {program.program_name: program for program in programs}

    selected_programs = {pc.program_name: pc.count for pc in holiday.program_counts.all()} if is_presenter_or_production else {}
    users_in_same_group = request.user.groups.first().user_set.exclude(id=request.user.id)

    context = {
        'holiday': holiday,
        'holiday_type_choices': holiday_type_choices,
        'programs': unique_programs.values(),
        'selected_programs': selected_programs,
        'users_in_same_group': users_in_same_group,
        'is_presenter_or_production': is_presenter_or_production,
        'program_counts_list': [(pc.program_name, pc.count) for pc in holiday.program_counts.all()]
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
        if request.user.groups.filter(name='Director').exists():
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
        
        # Set status to 'Under Review' after delegatee approval
        holiday.status = 'Under Review'
        
        # Save the updated holiday record
        holiday.save()

    return redirect('vacation:view_holidays')





@login_required(login_url='staff_user:staff_login_process')
def reject_delegatee(request, holiday_id):
    holiday = get_object_or_404(Holiday, id=holiday_id, delegatee=request.user)

    if holiday.status == 'pending':
        holiday.status = 'rejected'
        holiday.rejected_by = request.user
        holiday.save()

    return redirect('vacation:view_holidays')



@login_required(login_url='staff_user:staff_login_process')
def approve_holiday(request, holiday_id):
    holiday = get_object_or_404(Holiday, id=holiday_id)
    user = request.user
    user_groups = set(user.groups.values_list('name', flat=True))

    # Handling comments
    comment = request.POST.get('comment', '')
    
    if 'Production' in user_groups and holiday.user.groups.filter(name='Presenter').exists():
        if holiday.status == 'Under Review' or holiday.delegatee_approved:
            holiday.status = 'Under Review'
            holiday.approved_by = user
            holiday.production_manager_approved = True
            holiday.production_manager_comment = comment
            holiday.save()
        else:
            return HttpResponseForbidden("Delegatee has not approved yet.")
        return redirect('vacation:view_holidays')

    elif 'Technical Manager' in user_groups and holiday.user.groups.filter(name='Technical').exists():
        if holiday.status == 'Under Review' or holiday.delegatee_approved:
            holiday.status = 'Under Review'
            holiday.approved_by = user
            holiday.technical_manager_approved = True
            holiday.technical_manager_comment = comment
            holiday.save()
        else:
            return HttpResponseForbidden("Delegatee has not approved yet.")
        return redirect('vacation:view_holidays')

    elif 'Treasurer' in user_groups and holiday.user.groups.filter(name__in=['Cashier', 'Finance']).exists():
        if holiday.status == 'Under Review' or holiday.delegatee_approved:
            holiday.status = 'Under Review'
            holiday.approved_by = user
            holiday.treasurer_approved = True
            holiday.treasurer_comment = comment
            holiday.save()
        else:
            return HttpResponseForbidden("Delegatee has not approved yet.")
        return redirect('vacation:view_holidays')

    elif 'Director' in user_groups:
        # Ensure all necessary approvals are done
        if holiday.production_manager_approved or holiday.technical_manager_approved or holiday.treasurer_approved:
            holiday.status = 'approved'
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
        holiday.save()
        
    return redirect('vacation:view_holidays')



@login_required(login_url='staff_user:staff_login_process')
def approve_treasurer(request, holiday_id):
    holiday = get_object_or_404(Holiday, id=holiday_id)
    user = request.user

    if holiday.status == 'Under Review':
        if user.groups.filter(name='Treasurer').exists() and holiday.user.groups.filter(name__in=['Finance', 'Cashier']).exists():
            holiday.treasurer_approved = True
            holiday.save()
    return redirect('vacation:view_holidays')


@login_required(login_url='staff_user:staff_login_process')
def reject_treasurer(request, holiday_id):
    holiday = get_object_or_404(Holiday, id=holiday_id)
    user = request.user

    if holiday.status == 'Under Review':
        if user.groups.filter(name='Treasurer').exists() and holiday.user.groups.filter(name__in=['Finance', 'Cashier']).exists():
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
    overlay = Overlay.objects.get(id=1)
    return render(request, 'holiday/description.html', {'overlay': overlay})








@login_required(login_url='staff_user:staff_login_process')
def create_permission(request):
    user = request.user
    user_groups = user.groups.all()

    # Filter delegatees to ensure they are in the same role (group) as the user
    delegatees = User.objects.filter(groups__in=user_groups).exclude(id=user.id).distinct()

    if request.method == 'POST':
        # Fetching form data
        address = request.POST.get('address')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        place = request.POST.get('place')
        description = request.POST.get('description')
        delegatee_id = request.POST.get('delegatee')
        reporting_date = request.POST.get('reporting_date')
        duties = request.POST.getlist('duties')  # Ensure this matches your form input

        # Ensure all required fields are provided
        if not all([address, start_date, end_date, place, description, reporting_date]):
            messages.error(request, "Error: All fields are required.")
            return render(request, 'ruhusa/permission.html', {'delegatees': delegatees})

        # Validate date relationships
        start_date_parsed = parse_date(start_date)
        end_date_parsed = parse_date(end_date)
        reporting_date_parsed = parse_date(reporting_date)

        if end_date_parsed <= start_date_parsed:
            messages.error(request, "End date must be after start date.")
            return render(request, 'ruhusa/permission.html', {'delegatees': delegatees})

        if reporting_date_parsed <= end_date_parsed or reporting_date_parsed <= start_date_parsed:
            messages.error(request, "Reporting back date must be after both the start and end dates.")
            return render(request, 'ruhusa/permission.html', {'delegatees': delegatees})

        # Fetching the delegatee if provided
        delegatee = User.objects.filter(id=delegatee_id, groups__in=user_groups).first() if delegatee_id else None

        # Create a new PermissionRequest
        permission_request = PermissionRequest.objects.create(
            user=user,
            address=address,
            start_date=start_date,
            end_date=end_date,
            place=place,
            description=description,
            delegatee=delegatee,
            reporting_date=reporting_date
        )

        # Attach duties to the request
        for duty_name in duties:
            duty, created = Duty.objects.get_or_create(name=duty_name)
            permission_request.duties.add(duty)

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
    is_production = user.groups.filter(name='Production').exists()
    is_technical_manager = user.groups.filter(name='Technical Manager').exists()
    is_treasurer = user.groups.filter(name='Treasurer').exists()
    is_director = user.groups.filter(name='Director').exists()

    # Check if the user has permission to view the request
    if not (user_is_delegatee or user_is_requester or is_production or is_technical_manager or is_treasurer or is_director):
        return render(request, '403.html', status=403)

    if request.method == 'POST':
        action = request.POST.get('action')

        # Handle Production approval (after delegatee approval for Presenter requests)
        if is_production and permission_request.delegatee.groups.filter(name='Presenter').exists():
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

        # Handle Treasurer approval (after delegatee approval for Cashier/Finance requests)
        elif is_treasurer and permission_request.delegatee.groups.filter(name__in=['Cashier', 'Finance']).exists():
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

    # Set context for the template
    context = {
        'own_requests': PermissionRequest.objects.filter(user=user),
        'delegated_requests': PermissionRequest.objects.filter(delegatee=user),
        'is_production': is_production,
        'is_technical_manager': is_technical_manager,
        'is_treasurer': is_treasurer,
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

    if request.method == 'POST':
        # Get the form data
        address = request.POST.get('address')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        place = request.POST.get('place')
        description = request.POST.get('description')
        reporting_date = request.POST.get('reporting_date')

        # Parse the dates
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)
        reporting_date = parse_date(reporting_date)

        # Validate if dates are correctly formatted
        if not start_date or not end_date or not reporting_date:
            messages.error(request, 'Please provide valid dates in the format YYYY-MM-DD.')
            return render(request, 'ruhusa/edit_permission_request.html', {'permission_request': permission_request})

        # Update the request object
        permission_request.address = address
        permission_request.start_date = start_date
        permission_request.end_date = end_date
        permission_request.place = place
        permission_request.description = description
        permission_request.reporting_date = reporting_date
        
        permission_request.save()
        messages.success(request, 'Request has been updated.')
        return redirect('vacation:view_permission_request')

    return render(request, 'ruhusa/edit_permission_request.html', {'permission_request': permission_request})


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

    # Add delegatee_name and requester_name to each request for use in the template
    for req in own_requests:
        req.delegatee_name = req.delegatee.get_full_name() if req.delegatee else 'None'
        
    for req in delegated_requests:
        req.delegatee_name = req.delegatee.get_full_name() if req.delegatee else 'None'
        req.requester_name = req.user.get_full_name()

    # Initialize role-based filtering
    role_based_requests = PermissionRequest.objects.none()

    # Check user roles and set role-based requests
    is_production = user.groups.filter(name='Production').exists()
    is_technical_manager = user.groups.filter(name='Technical Manager').exists()
    is_treasurer = user.groups.filter(name='Treasurer').exists()
    is_director = user.groups.filter(name='Director').exists()

    if is_production:
        role_based_requests = PermissionRequest.objects.filter(
            delegatee__groups__name='Presenter',
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
            delegatee__groups__name__in=['Cashier', 'Finance'],
            status='Under Review',
            approved_by_delegatee=True,
            approved_by_treasurer=False
        )
    elif is_director:
        role_based_requests = PermissionRequest.objects.filter(
            status='Under Review',
            approved_by_director=False
        ).filter(
            Q(approved_by_production=True) | 
            Q(approved_by_technical_manager=True) | 
           Q(approved_by_treasurer=True)
        )

    # Update the status based on the user's role and the approval flow
    for req in role_based_requests:
        if is_production:
            if req.approved_by_delegatee:
                req.status = 'Under Review'
        elif is_technical_manager:
            if req.approved_by_delegatee:
                req.status = 'Under Review'
        elif is_treasurer:
            if req.approved_by_delegatee:
                req.status = 'Under Review'
        elif is_director:
            if req.approved_by_production and req.approved_by_technical_manager and req.approved_by_treasurer:
                req.status = 'Approved'
        
        req.delegatee_name = req.delegatee.get_full_name() if req.delegatee else 'None'
        req.requester_name = req.user.get_full_name()

    context = {
        'own_requests': own_requests,
        'delegated_requests': delegated_requests,
        'role_based_requests': role_based_requests,
        'is_production': is_production,
        'is_technical_manager': is_technical_manager,
        'is_treasurer': is_treasurer,
        'is_director': is_director,
    }

    return render(request, 'ruhusa/view_permission_request.html', context)



from django.http import JsonResponse
@login_required
@require_POST
def approve_request(request, request_id):
    permission_request = get_object_or_404(PermissionRequest, id=request_id)
    logger.debug(f"Processing approval for request {request_id} by user {request.user}")

    # Helper function to update approval and status
    def update_approval(field_name, status_condition=None):
        setattr(permission_request, field_name, True)
        if status_condition and status_condition():  # Check if the request is ready for the next approval stage
            permission_request.status = 'Under Review'  # Change status to 'Under Review'
        permission_request.save()

    # Delegatee approval logic
    if request.user == permission_request.delegatee:
        if not permission_request.approved_by_delegatee:
            permission_request.approved_by_delegatee = True
            permission_request.status = 'Under Review'
            permission_request.save()
            return JsonResponse({'success': True, 'message': 'Request approved by delegatee.'})
        else:
            return JsonResponse({'success': False, 'error': 'Request already approved by delegatee.'}, status=400)

    # Check if delegatee has approved before allowing further approvals
    if not permission_request.approved_by_delegatee:
        return JsonResponse({'success': False, 'error': 'Delegatee must approve the request first.'}, status=403)

    # Approval by specific roles
    if permission_request.delegatee.groups.filter(name='Presenter').exists() and \
       request.user.groups.filter(name='Production').exists():
        if not permission_request.approved_by_production:
            update_approval('approved_by_production', permission_request.is_ready_for_director)
            return JsonResponse({'success': True, 'message': 'Request approved by Production.'})
        else:
            return JsonResponse({'success': False, 'error': 'Request already approved by Production.'}, status=400)

    elif permission_request.delegatee.groups.filter(name='Technical').exists() and \
         request.user.groups.filter(name='Technical Manager').exists():
        if not permission_request.approved_by_technical_manager:
            update_approval('approved_by_technical_manager', permission_request.is_ready_for_director)
            return JsonResponse({'success': True, 'message': 'Request approved by Technical Manager.'})
        else:
            return JsonResponse({'success': False, 'error': 'Request already approved by Technical Manager.'}, status=400)

    elif permission_request.delegatee.groups.filter(name__in=['Cashier', 'Finance']).exists() and \
         request.user.groups.filter(name='Treasurer').exists():
        if not permission_request.approved_by_treasurer:
            update_approval('approved_by_treasurer', permission_request.is_ready_for_director)
            return JsonResponse({'success': True, 'message': 'Request approved by Treasurer.'})
        else:
            return JsonResponse({'success': False, 'error': 'Request already approved by Treasurer.'}, status=400)

    elif request.user.groups.filter(name='Director').exists():
        # Check if the request is ready for Director approval
        if permission_request.is_ready_for_director():
            if not permission_request.approved_by_director:
                permission_request.approved_by_director = True
                permission_request.status = 'Approved'
                permission_request.save()
                return JsonResponse({'success': True, 'message': 'Request approved by Director.'})
            else:
                return JsonResponse({'success': False, 'error': 'Request already approved by Director.'}, status=400)
        else:
            return JsonResponse({'success': False, 'error': 'Request is not ready for Director approval.'}, status=403)

    else:
        return JsonResponse({'success': False, 'error': 'You are not authorized to approve this request.'}, status=403)

    # If it's an Ajax request, return a JSON response; otherwise, redirect
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    return redirect('vacation:view_permission_request', request_id=permission_request.id)


@login_required
@require_POST  # Ensure only POST requests are allowed
def reject_request(request, request_id):
    permission_request = get_object_or_404(PermissionRequest, id=request_id)
    
    # Check if the user has the right role to reject the request
    if request.user == permission_request.delegatee or \
       request.user.groups.filter(name__in=['Production', 'Technical Manager', 'Treasurer', 'Director']).exists():
        
        # Get the rejection comment (if provided in the form)
        comment = request.POST.get('comment', '')
        if not comment:
            return JsonResponse({'success': False, 'error': 'Comment is required for rejection.'}, status=400)
        
        permission_request.status = 'rejected'
        permission_request.rejection_comment = comment  # Assuming you have a field for rejection comments
        permission_request.save()

        # Return JSON response if the request is made via AJAX
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        # Redirect for non-AJAX request
        return redirect('vacation:view_permission_request', request_id=permission_request.id)
    
    return JsonResponse({'success': False, 'error': 'You are not authorized to reject this request.'}, status=403)
