from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import TaskAssignment, AssignmentDetail, Equipment, AssignmentEquipment
from .decorators import role_required,determine_user_role
from django.contrib.auth.models import User,Group
from django.http import HttpResponse,JsonResponse,HttpResponseForbidden
from django.contrib import messages
from datetime import date


# from finance.utility import determine_user_role  # Import the determine_user_role function from the utils module



@login_required(login_url='staff_user:staff_login_process')
@role_required('Technical','Technical Manager')

def register_equipment(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        type_model = request.POST.get('type_model')
       
        equipment_image = request.FILES.get('equipment_image')
        serial_number = request.POST.get('serial_number')
       
       
        # Handle adding new category or type model if selected
        if category == 'add_category':
            new_category = request.POST.get('new_category')
            if new_category:
                category = new_category 

        if type_model == 'add_type_model':
            new_type_model = request.POST.get('new_type_model')
            if new_type_model:
                type_model = new_type_model

        # Create a new Equipment instance and save it
        new_equipment = Equipment.objects.create(
            name=name,
            category=category,
            type_model=type_model,
           
            equipment_image=equipment_image,
            serial_number=serial_number,
        )

        # Redirect to a success page or display a success message
        return redirect('equipment:equipment_list')  # Replace 'equipment_list' with the URL name of your equipment list page

    # If request method is GET, render the form template
    category_choices = [choice[0] for choice in Equipment.CATEGORY_CHOICES]
    type_model_choices = [choice[0] for choice in Equipment.TYPE_MODEL_CHOICES]
    context = {
        'category_choices': category_choices,
        'type_model_choices': type_model_choices
    }
    return render(request,'vifaa/equip_register.html', context)


@login_required(login_url='staff_user:staff_login_process')
def equipment_list(request):
    query = request.GET.get('q')
    equipment = Equipment.objects.all()
    if query:
        equipment_list = Equipment.objects.filter(
            Q(name__icontains=query) | Q(category__icontains=query)
        )
    else:
        equipment_list = Equipment.objects.all()
    return render(request, 'vifaa/equip_list.html', {'equipment_list': equipment_list,'equipment':equipment})


@login_required(login_url='staff_user:staff_login_process')
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

@login_required(login_url='staff_user:staff_login_process')
@role_required('Production', 'Presenter')
def task_assignment(request):
    current_user = request.user

    if request.method == 'POST':
        # Extract form data and create a new TaskAssignment
        assignment = request.POST.get('assignment')
        location = request.POST.get('location')
        category = request.POST.get('category')
        submission_date = request.POST.get('submission_date')
       
        detail_ids = request.POST.getlist('details')
        equipment_ids = request.POST.getlist('equipment[]')
        quantities = request.POST.getlist('quantity[]')
        
        task_assignment = TaskAssignment.objects.create(
            assignment=assignment,
            location=location,
            category=category,
            submission_date=submission_date,
            requested_by=current_user,
            date=date.today(),
        )
        
        task_assignment.details.set(detail_ids)

        # Create AssignmentEquipment and update the equipment status
        for equipment_id, quantity in zip(equipment_ids, quantities):
            equipment = Equipment.objects.get(id=equipment_id)
            AssignmentEquipment.objects.create(
                task_assignment=task_assignment,
                equipment=equipment,
                quantity=quantity
            )
            # Change the status of the equipment to 'Reserved'
            equipment.status = 'Reserved'
            equipment.save()
        
        # Optionally, save amount required
       
        task_assignment.save()

        return redirect('equipment:view_assignments')  # Redirect to a view or success page

    else:
        # Prepare the context data for the form, only showing available equipment
        available_equipments = Equipment.objects.filter(status='Available')

        presenter = Group.objects.get(name='Presenter')  # Get the group of persons who can be assigned tasks
        all_persons = User.objects.filter(groups=presenter)
        category_choices = TaskAssignment.CATEGORY_CHOICES
        assignment_details_choices = AssignmentDetail.objects.all()

        context = {
            'available_equipments': available_equipments,
            'all_persons': all_persons,
            'assignment_details_choices': assignment_details_choices,
            'category_choices': category_choices,
        }

        return render(request, 'vifaa/equipment_request.html', context)

    
@login_required(login_url='staff_user:staff_login_process')
def view_assignments(request):
    user_role = determine_user_role(request.user)
    
    if user_role == 'Presenter':
        general_requests = TaskAssignment.objects.filter(persons_assigned=request.user)
    elif user_role == 'Technical':
        general_requests = TaskAssignment.objects.filter(
            Q(status='Pending') | 
            Q(persons_assigned=request.user)
        )
    else:
        general_requests = TaskAssignment.objects.filter(
            Q(requested_by=request.user) |
            Q(persons_assigned=request.user)
        )

    # Ensure equipment details are added to all relevant requests
    for user_request in general_requests:
        original_equipment_details = ", ".join([
            f"{assignment_equipment.equipment.name} - Quantity: {assignment_equipment.quantity}" 
            for assignment_equipment in user_request.assignmentequipment_set.all()
        ])
        user_request.equipment_details = original_equipment_details

    context = {
        'user_role': user_role,
        'general_requests': general_requests.distinct(),
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
            if user_role == 'Production' and task_assignment.status == 'Pending':
                task_assignment.production_approved = True
                task_assignment.production_approver = request.user
                task_assignment.status = 'Under Review'
            elif user_role == 'Technical' and task_assignment.status == 'Under Review' and task_assignment.production_approved:
                task_assignment.technical_approved = True
                task_assignment.technical_approver = request.user
                task_assignment.status = 'Under Review'
            elif user_role == 'Treasurer' and task_assignment.status == 'Under Review' and task_assignment.production_approved and task_assignment.technical_approved:
                task_assignment.treasurer_approved = True
                task_assignment.treasurer_approver = request.user
                task_assignment.status = 'Approved'
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
@role_required('Production', 'Presenter')
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
        presenter = Group.objects.get(name='Presenter')
        all_persons = User.objects.filter(groups=presenter)
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
        return redirect('equipment:view_assignments')
    else:
        # If the request method is not POST, simply render the delete confirmation page
        context = {'task_assignment': task_assignment}
        return render(request, 'vifaa/delete_request.html', context)
    

@login_required(login_url='staff_user:staff_login_process')
@role_required('Production', 'Technical', 'Treasurer', 'Cashier')
def approve_request(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, pk=task_id)

    # Determine user role using the determine_user_role function
    user_role = determine_user_role(request.user)
    print(f"User Role: {user_role}")  # Debugging print statement
    
    if task_assignment.status == 'Pending':
        if user_role == 'Production':
            # Only Production can approve when status is Pending
            task_assignment.status = 'Under Review'
            task_assignment.production_approved = True
            task_assignment.save()

            # Redirect to specific request view or another appropriate page
            return redirect('equipment:specific_request', task_id=task_id)

        else:
            return HttpResponseForbidden("You are not authorized to approve this task at this stage.")

    elif task_assignment.status == 'Under Review':
        if user_role == 'Technical':
            if task_assignment.production_approved:
                task_assignment.technical_approved = True
                task_assignment.save()

                # Redirect to specific request view or another appropriate page
                return redirect('equipment:specific_request', task_id=task_id)

            else:
                return HttpResponseForbidden("You are not authorized to approve this task at this stage.")

        elif user_role == 'Treasurer':
            if task_assignment.production_approved and task_assignment.technical_approved:
                task_assignment.treasurer_approved = True
                task_assignment.save()

                # Redirect to specific request view or another appropriate page
                return redirect('equipment:specific_request', task_id=task_id)

            else:
                return HttpResponseForbidden("You are not authorized to approve this task at this stage.")

        elif user_role == 'Cashier':
            if (task_assignment.production_approved or
                task_assignment.technical_approved and 
                task_assignment.treasurer_approved):
                
                task_assignment.cashier_approved = True
                task_assignment.status = 'Approved'
                task_assignment.save()

                # Redirect to specific request view or another appropriate page
                return redirect('equipment:specific_request', task_id=task_id)

            else:
                return HttpResponseForbidden("You are not authorized to approve this task at this stage.")

        else:
            return HttpResponseForbidden("You are not authorized to approve this task.")

    else:
        return HttpResponseForbidden("This task assignment is not pending approval.")


@login_required(login_url='staff_user:staff_login_process')
@role_required('Production', 'Technical', 'Treasurer', 'Cashier')
def reject_request(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, pk=task_id)

    # Check if the user belongs to the appropriate group and update the task status to 'Rejected'
    user_groups = request.user.groups.values_list('name', flat=True)

    if 'Production' in user_groups or 'Technical' in user_groups or 'Treasurer' in user_groups or 'Cashier' in user_groups:
        task_assignment.status = 'Rejected'
        task_assignment.rejection_reason = request.POST.get('rejection_reason', '')
        task_assignment.save()
    else:
        return HttpResponseForbidden('You are not authorized to reject this task.')

    return redirect('specific_request_view', task_id=task_id)


@login_required(login_url='staff_user:staff_login_process')
@role_required('Technical', 'Technical Manager')
def confirm_return(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, pk=task_id)
    
    if task_assignment.status == 'Approved' and task_assignment.treasurer_approved:
        # Update the status of each piece of equipment to 'Available'
        for equipment_detail in task_assignment.assignmentequipment_set.all():
            if equipment_detail.equipment.status == 'Reserved':
                equipment_detail.equipment.status = 'Available'
                equipment_detail.equipment.save()
        
        # Update the task status to 'Returned'
        task_assignment.status = 'Returned'
        task_assignment.save()

        return redirect('equipment:view_approved_requests')

    return HttpResponseForbidden("You are not authorized to perform this action.")


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
