from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required,permission_required
from django.db.models import Q
from .models import TaskAssignment, AssignmentDetail, Equipment, AssignmentEquipment
from .decorators import role_required,determine_user_role
from django.contrib.auth.models import User,Group
from django.http import HttpResponse,JsonResponse,HttpResponseForbidden
from django.contrib import messages
from datetime import date
from django.core.paginator import Paginator
from django.db.models import Count
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from .models import TaskAssignment
from .tasks import delete_rejected_task

# from finance.utility import determine_user_role  # Import the determine_user_role function from the utils module



from django.utils import timezone
from django.shortcuts import redirect, render
from .models import Equipment

@login_required(login_url='staff_user:staff_login_process')
@role_required('Technical', 'Technical Manager')
@permission_required('auth.add_user', raise_exception=True)
def register_equipment(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        type_model = request.POST.get('type_model')
        equipment_image = request.FILES.get('equipment_image')
        serial_number = request.POST.get('serial_number')

        # Validate required fields
        if not name or not category or not type_model or not serial_number:
            messages.error(request, "Please fill in all required fields.")
            return redirect('equipment:register_equipment')

        # Handle adding new category if 'add_category' is selected
        if category == 'add_category':
            new_category = request.POST.get('new_category')
            if new_category:
                # Save the new category if it doesn't exist
                category_obj, created = Category.objects.get_or_create(name=new_category)
                category = category_obj.name  # Update category variable to the saved category name

        # Handle adding new type model if 'add_type_model' is selected
        if type_model == 'add_type_model':
            new_type_model = request.POST.get('new_type_model')
            if new_type_model:
                # Save the new type model if it doesn't exist
                type_model_obj, created = TypeModel.objects.get_or_create(name=new_type_model)
                type_model = type_model_obj.name  # Update type_model variable to the saved type model name

        # Create a new Equipment instance
        new_equipment = Equipment.objects.create(
            name=name,
            category=category,
            type_model=type_model,
            equipment_image=equipment_image,
            serial_number=serial_number,
        )

        # Display success message and redirect
        messages.success(request, "Equipment registered successfully!")
        return redirect('equipment:equipment_list')  # Replace with actual equipment list URL

    # If request method is GET, render the form template
    category_choices = [choice[0] for choice in Equipment.CATEGORY_CHOICES]
    type_model_choices = [choice[0] for choice in Equipment.TYPE_MODEL_CHOICES]
    context = {
        'category_choices': category_choices,
        'type_model_choices': type_model_choices
    }
    return render(request, 'vifaa/equip_register.html', context)


@login_required(login_url='staff_user:staff_login_process')
def equipment_list(request):
    user_role = determine_user_role(request.user)
    query = request.GET.get('q', '')  # Get the search query
    page = request.GET.get('page', 1)  # Get the current page number
    view = request.GET.get('view', 'grid')  # Get the current view state, default to grid

    # Fetch all equipment if no query is provided
    if not query:  
        equipment_list = Equipment.objects.all()
    else:
        # Filter based on the search query if provided
        equipment_list = Equipment.objects.filter(
            Q(name__icontains=query) | Q(category__icontains=query) | Q(status__icontains=query)
        )

    # Count total items in the filtered list
    total_equipment_count = equipment_list.count()  # Get total count of filtered equipment

    paginator = Paginator(equipment_list, 4)  # Paginate with 4 items per page
    page_obj = paginator.get_page(page)  # Get the current page object

    context = {
        'equipment': page_obj.object_list,
        'total_equipment_count': total_equipment_count,  # Add total count to context
        'categories': Equipment.objects.values_list('category', flat=True).distinct(),
        'page_obj': page_obj,
        'view': view,  # Pass the view state to the template
        'user_role':user_role,
    }

    # Handle AJAX requests
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'vifaa/equipment_list_partial.html', context)

    return render(request, 'vifaa/equip_list.html', context)



@login_required(login_url='staff_user:staff_login_process')
@role_required('Technical', 'Technical Manager')
def edit_equipment(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        # Retrieve updated data from the request
        name = request.POST.get('name')
        category = request.POST.get('category')
        type_model = request.POST.get('type_model')
        quantity = request.POST.get('quantity')
        # Update the equipment object
        equipment.name = name
        equipment.category = category
        equipment.type_model = type_model
       
        equipment.save()
        return redirect('equipment:equipment_list')   # Redirect to equipment list after successful edit
    return render(request, 'vifaa/edit_equipment.html', {'equipment': equipment})


# View function to display the delete confirmation form
@login_required(login_url='staff_user:staff_login_process')
def delete_confirmation(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    return render(request, 'vifaa/delete_confirmation.html', {'equipment': equipment})

# View function to handle the delete action
@login_required(login_url='staff_user:staff_login_process')
def delete_equipment(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        equipment.delete()
        return redirect('equipment:equipment_list')
    return redirect('equipment:delete_confirmation', pk=pk)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from .models import TaskAssignment, Equipment, AssignmentEquipment, User
from datetime import date
from .decorators import role_required

@login_required(login_url='staff_user:staff_login_process')
@role_required('Production Manager', 'Radio / TV Presenter', 'Editor')
def task_assignment(request):
    current_user = request.user

    if request.method == 'POST':
        assignment = request.POST.get('assignment')
        location = request.POST.get('location')  # Manual input or selected location
        category = request.POST.get('category')
        submission_date = request.POST.get('submission_date')
        persons_assigned_ids = request.POST.getlist('persons_assigned[]')  # List of assigned persons' IDs
        
        # Get equipment and quantities from the form
        equipment_ids = request.POST.getlist('equipment[]')
        quantities = request.POST.getlist('quantity[]')

        # Ensure assignment data is valid before saving
        if not assignment or not location or not category or not submission_date:
            messages.error(request, 'Please fill out all required fields.')
            return redirect('equipment:task_assignment')

        # Create a new task assignment
        task_assignment = TaskAssignment.objects.create(
            assignment=assignment,
            location=location,
            category=category,
            submission_date=submission_date,
            requested_by=current_user,
            date=date.today(),
        )

        # Assign persons to the task (assuming ManyToManyField for persons_assigned)
        if persons_assigned_ids:
            assigned_persons = User.objects.filter(id__in=persons_assigned_ids)
            task_assignment.persons_assigned.set(assigned_persons)

        # Handle equipment assignments, ensuring valid data
        for equipment_id, quantity in zip(equipment_ids, quantities):
            if equipment_id and quantity:  # Ensure both equipment and quantity are provided
                try:
                    equipment = Equipment.objects.get(id=equipment_id)
                    AssignmentEquipment.objects.create(
                        task_assignment=task_assignment,
                        equipment=equipment,
                        quantity=quantity
                    )
                    # Update equipment status to 'Reserved'
                    equipment.status = 'Reserved'
                    equipment.save()
                except Equipment.DoesNotExist:
                    messages.error(request, 'Some selected equipment does not exist.')
                    return redirect('equipment:task_assignment')

        messages.success(request, 'Task assignment successfully created with equipment reserved.')
        return redirect('equipment:view_assignments')

    # Prepare context for GET request
    context = {
        'available_equipments': Equipment.objects.filter(status='Available'),
        'all_persons': User.objects.filter(
            Q(groups__name='Radio / TV Presenter') | Q(groups__name='Editor')
        ).exclude(id=current_user.id),  # Exclude current user from persons to assign
        'category_choices': TaskAssignment.CATEGORY_CHOICES,
        'assignment_details_choices': AssignmentDetail.objects.all(),
    }

    return render(request, 'vifaa/equipment_request.html', context)

@login_required(login_url='staff_user:staff_login_process')
def view_assignments(request):
    user_role = determine_user_role(request.user)

    # Fetch user's own requests
    user_requests = TaskAssignment.objects.filter(requested_by=request.user)\
        .select_related('production_approver', 'technical_manager_approver', 'treasurer_approver')\
        .prefetch_related('assignmentequipment_set')

    # Fetch requests assigned to the user
    assigned_requests = TaskAssignment.objects.filter(persons_assigned=request.user)\
        .select_related('production_approver', 'technical_manager_approver', 'treasurer_approver')\
        .prefetch_related('assignmentequipment_set')

    # Helper function to fetch approval requests based on user role
    def fetch_approval_requests():
        if user_role == 'Production Manager':
            return TaskAssignment.objects.filter(
                status='Pending',
                production_approved=False
            ).exclude(requested_by=request.user)\
            .select_related('production_approver', 'technical_manager_approver', 'treasurer_approver')\
            .prefetch_related('assignmentequipment_set')

        elif user_role == 'Technical Manager':
            return TaskAssignment.objects.filter(
                status='Under Review',
                production_approved=True,
                technical_manager_approved=False
            ).exclude(requested_by=request.user)\
            .select_related('production_approver', 'technical_manager_approver', 'treasurer_approver')\
            .prefetch_related('assignmentequipment_set')

        elif user_role in ['Treasurer', 'Assistant Treasurer']:
            return TaskAssignment.objects.filter(
                status='Under Review',
                production_approved=True,
                technical_manager_approved=True,
                treasurer_approved=False
            ).exclude(requested_by=request.user)\
            .select_related('production_approver', 'technical_manager_approver', 'treasurer_approver')\
            .prefetch_related('assignmentequipment_set')

        elif user_role == 'Technical':
            return TaskAssignment.objects.filter(
                Q(status='Under Review', production_approved=True, technical_manager_approved=True, treasurer_approved=True, technical_approved=False) |
                Q(status='Approved')
            ).exclude(requested_by=request.user)\
            .select_related('production_approver', 'technical_manager_approver', 'treasurer_approver')\
            .prefetch_related('assignmentequipment_set')

        return TaskAssignment.objects.none()

    # Fetch approval requests
    approval_requests = fetch_approval_requests()

    # Approved requests visible to Technical for return confirmation
    approved_requests = TaskAssignment.objects.filter(
        status='Approved',
        technical_approved=True
    ).exclude(requested_by=request.user)\
    .select_related('production_approver', 'technical_manager_approver', 'treasurer_approver')\
    .prefetch_related('assignmentequipment_set') if user_role == 'Technical' else TaskAssignment.objects.none()

    # Add equipment details and approver names to each request
    def add_equipment_details(request_set):
        for request_item in request_set:
            # Fetch equipment details
            request_item.equipment_details = ", ".join([
                f"{detail.equipment.name} (Quantity: {detail.quantity})"
                for detail in request_item.assignmentequipment_set.all()
            ])

            # Safely handle approver names with a check for None
            request_item.approved_by = {
                'production': request_item.production_approver.get_full_name() if request_item.production_approver else 'Not Approved',
                'technical_manager': request_item.technical_manager_approver.get_full_name() if request_item.technical_manager_approver else 'Not Approved',
                'treasurer': request_item.treasurer_approver.get_full_name() if request_item.treasurer_approver else 'Not Approved',
                'technical': 'Approved' if request_item.technical_approved else 'Not Approved'
            }

            # Safely handle return confirmation details
            request_item.return_confirmation = {
                'return_date': request_item.return_date.strftime('%Y-%m-%d %H:%M') if request_item.return_date else 'Not Returned',
                'confirmed_by': request_item.return_confirmed_by.get_full_name() if request_item.return_confirmed_by else 'Not Confirmed'
            }

    # Add equipment details to all request sets
    add_equipment_details(user_requests)
    add_equipment_details(assigned_requests)
    add_equipment_details(approval_requests)
    add_equipment_details(approved_requests)

    context = {
        'user_role': user_role,
        'user_requests': user_requests,
        'assigned_requests': assigned_requests,
        'approval_requests': approval_requests,
        'approved_requests': approved_requests,
    }

    return render(request, 'vifaa/equip_request_view.html', context)


@login_required(login_url='staff_user:staff_login_process')
def specific_request_view(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, pk=task_id)
    equipment_details = AssignmentEquipment.objects.filter(task_assignment=task_assignment)

    user_role = determine_user_role(request.user)

    # Ensure the user is either the requester or part of the assigned crew
    if request.user != task_assignment.requested_by and request.user not in task_assignment.persons_assigned.all():
        return HttpResponseForbidden("You are not authorized to view this task.")

    if request.method == 'POST':
        action = request.POST.get('action')
        confirm_return = request.POST.get('confirm_return')
        if action == 'approve':
            if user_role == 'Production Manager' and task_assignment.status == 'Pending':
                task_assignment.production_approved = True
                task_assignment.production_approver = request.user
                task_assignment.status = 'Under Review'
                
            elif user_role == 'Technical Manager'  and task_assignment.status == 'Under Review' and task_assignment.production_approved:
                task_assignment.technical_manager_approved = True
                task_assignment.technical_manager_approver = request.user
                task_assignment.status = 'Under Review'
                
            elif user_role == 'Treasurer'or user_role == 'Assistant Treasurer' and task_assignment.status == 'Under Review' and task_assignment.production_approved and task_assignment.technical_manager_approved:
                task_assignment.treasurer_approved = True
                task_assignment.treasurer_approver = request.user or task_assignmnet.assistant_treasurer_approver == request.user
                task_assignment.status = 'Under Review'
            
            
            elif user_role == 'Technical'and task_assignment.status == 'Under Review' and task_assignment.production_approved and task_assignment.technical_manager_approved and task_assignment.treasurer_approved or task_assignment.assistant_treasurer_approved:
                task_assignment.technical_approved == True
                task_assignment.technical_approver == request.user
                task_assignment.status == 'Approved'
            task_assignment.save()
            
        elif action == 'reject':
            task_assignment.status = 'Rejected'
            task_assignment.save()
        elif confirm_return == 'confirm':
            task_assignment.status = 'Return Confirmed'
            task_assignment.save()

    context = {
        'task_assignment': task_assignment,
        'equipment_details': equipment_details,
        'user_role': user_role,
    }
    return render(request, 'vifaa/specific_request.html', context)



@login_required(login_url='staff_user:staff_login_process')
@role_required('Production Manager', 'Radio / TV Presenter')
def edit_task_assignment(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, pk=task_id)
    
    if request.method == 'POST':
        print("POST data received:", request.POST)
        assignment = request.POST.get('assignment')
        location = request.POST.get('location')
        category = request.POST.get('category')
        submission_date = request.POST.get('submission_date')
        agreement = request.POST.get('agreement') == 'on'
        detail_ids = request.POST.getlist('details')
        equipment_ids = request.POST.getlist('equipment[]')
        quantities = request.POST.getlist('quantity[]')
        persons_assigned_ids = request.POST.getlist('persons_assigned[]')  # Corrected to 'persons_assigned[]'
        
        current_date = date.today()

        task_assignment.assignment = assignment
        task_assignment.location = location
        task_assignment.category = category
        task_assignment.submission_date = submission_date
        task_assignment.agreement = agreement
        
        task_assignment.date = current_date
        
        # Save the updated details
        task_assignment.save()
        
        # Update the ManyToMany fields
        task_assignment.details.set(detail_ids)
        
        # Delete existing equipment assignments and create new ones
        task_assignment.assignmentequipment_set.all().delete()
        for equipment_id, quantity in zip(equipment_ids, quantities):
            equipment = Equipment.objects.get(id=equipment_id)
            AssignmentEquipment.objects.create(
                task_assignment=task_assignment,
                equipment=equipment,
                quantity=quantity
            )

        # Update persons assigned
        task_assignment.persons_assigned.set(persons_assigned_ids)
        
        return redirect('equipment:view_assignments')
    
    else:
        # Handle GET request to display the form
        all_equipments = Equipment.objects.all()
        presenter = Group.objects.get(name='Radio / TV Presenter')
        all_persons = User.objects.filter(groups=presenter).exclude(id=request.user.id)
        category_choices = TaskAssignment.CATEGORY_CHOICES
        assignment_details_choices = AssignmentDetail.objects.all()
        
        context = {
            'task_assignment': task_assignment,
            'all_equipments': all_equipments,
            'all_persons': all_persons,
            'assignment_details_choices': assignment_details_choices,
            'category_choices': category_choices,
        }
        
        return render(request, 'vifaa/edit_request.html', context)



@login_required(login_url='staff_user:staff_login_process')
def delete_task_assignment(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, id=task_id)

    if request.method == 'POST':
        # If the request method is POST, it means the user confirmed the deletion
        task_assignment.delete()
        return redirect('equipment:view_assignments')  # Make sure this URL exists in your project
    else:
        # If the request method is not POST, simply render the delete confirmation page
        context = {'task_assignment': task_assignment}
        return render(request, 'vifaa/delete_request.html', context)
    
@login_required(login_url='staff_user:staff_login_process')
@role_required('Production Manager', 'Technical Manager', 'Treasurer', 'Assistant Treasurer', 'Technical')

def approve_request(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, pk=task_id)
    user_role = determine_user_role(request.user)

    if request.method == 'POST':
        try:
            # Approval logic based on user role and previous approvals
            if user_role == 'Production Manager' and task_assignment.status in ['Pending', 'Under Review']:
                task_assignment.status = 'Under Review'
                task_assignment.production_approved = True
                task_assignment.production_approver = request.user
                messages.success(request, 'Task assignment is now under review by the Production Manager.')

            elif user_role == 'Technical Manager' and task_assignment.status == 'Under Review' and task_assignment.production_approved:
                task_assignment.technical_manager_approved = True
                task_assignment.technical_manager_approver = request.user
                messages.success(request, 'Task assignment approved by the Technical Manager.')

            elif user_role in ['Treasurer', 'Assistant Treasurer']:
                if (
                    task_assignment.status == 'Under Review'
                    and task_assignment.production_approved
                    and task_assignment.technical_manager_approved
                ):
                    if user_role == 'Treasurer': 
                        task_assignment.treasurer_approved = True
                        task_assignment.treasurer_approver = request.user
                        messages.success(request, 'Task assignment approved by the Treasurer.')
                    else:
                        task_assignment.assistant_treasurer_approved = True
                        task_assignment.assistant_treasurer_approver = request.user
                        messages.success(request, 'Task assignment approved by the Assistant Treasurer.')

                    task_assignment.status = 'Approved'  # Status change on approval

            elif user_role == 'Technical':
                if (
                    task_assignment.status == 'Under Review'
                    and task_assignment.production_approved
                    and task_assignment.technical_manager_approved
                    and (task_assignment.treasurer_approved or task_assignment.assistant_treasurer_approved)
                ):
                    task_assignment.technical_approved = True
                    task_assignment.status = 'Approved'  # Final approval
                    task_assignment.archive_approved_task()  # Archive task if fully approved
                    messages.success(request, 'Task assignment fully approved and archived.')

            # Return confirmation logic
            elif request.POST.get('confirm_return') and task_assignment.status == 'Approved':
                task_assignment.status = 'Returned'
                for equipment_detail in task_assignment.assignmentequipment_set.all():
                    if equipment_detail.equipment.status == 'Reserved':
                        equipment_detail.equipment.status = 'Available'
                        equipment_detail.equipment.save()
                task_assignment.return_date = timezone.now()
                task_assignment.return_confirmed = True
                task_assignment.return_confirmed_by = request.user
                messages.success(request, 'Task assignment marked as returned successfully.')

            # Save the task assignment changes
            task_assignment.save()

            # Redirect to the view task assignment page after processing
            return redirect('view_assignments')  # Ensure this matches your URL name

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('view_assignments')  # Redirect on error

    messages.error(request, 'Invalid request method.')
    return redirect('view_assignments')  # Redirect for invalid method


@role_required('Production Manager', 'Technical Manager', 'Treasurer', 'Assistant Treasurer', 'Technical')
def reject_request(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, pk=task_id)

    if request.method == 'POST':
        user_role = determine_user_role(request.user)
        if user_role in ['Production Manager', 'Technical Manager', 'Treasurer', 'Assistant Treasurer', 'Technical']:
            task_assignment.status = 'Rejected'
            task_assignment.rejection_reason = request.POST.get('rejection_reason', 'No reason provided')
            task_assignment.save()

            # Handle equipment status update when task is rejected
            assigned_equipments = AssignmentEquipment.objects.filter(task_assignment=task_assignment)
            for assigned_equipment in assigned_equipments:
                equipment = assigned_equipment.equipment
                if equipment.status == 'Reserved':
                    equipment.status = 'Available'
                    equipment.save()

            # Schedule the task deletion to occur 24 hours later
            delete_rejected_task.apply_async((task_assignment.id,), countdown=60)  # 86400 seconds = 24 hours

            return JsonResponse({
                'status': 'success',
                'message': 'Task rejected successfully, and equipment status updated to available.'
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method or you are not authorized to reject this task.'
    }, status=403)
    
    
@login_required(login_url='staff_user:staff_login_process')
@role_required('Technical', 'Technical Manager')
def confirm_return(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, pk=task_id)

    if request.method == 'POST':
        try:
            # Update the TaskAssignment status to 'Returned'
            task_assignment.status = 'Returned'
            task_assignment.save()

            # Assuming you have a way to get the assigned equipment directly
            assigned_equipments = task_assignment.assignmentequipment_set.all()  # Use the related name if defined

            # Change the status of each equipment to 'Available'
            for assignment in assigned_equipments:
                equipment = assignment.equipment  # Get the Equipment instance
                equipment.status = 'Available'  # Update status to Available
                equipment.save()  # Save changes to Equipment

            return JsonResponse({'status': 'success', 'message': 'Return confirmed successfully.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@login_required(login_url='staff_user:staff_login_process')
def view_approved_requests(request):
    approved_requests = TaskAssignment.objects.filter(status='Approved')
    user_role = determine_user_role(request.user)
    
    # Determine if the user has any of the required roles
    can_see_actions = user_role in ['Technical', 'Technical Manager', 'Treasurer']
    
    context = {
        'approved_requests': approved_requests,
        'user_role': user_role,
        'can_see_actions': can_see_actions,
    }
    return render(request, 'vifaa/approved_request.html', context)
