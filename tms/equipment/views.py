from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import TaskAssignment, AssignmentDetail, Equipment, AssignmentEquipment
from .decorators import role_required,determine_user_role
from django.contrib.auth.models import User,Group
from django.http import HttpResponse,JsonResponse,HttpResponseForbidden

from datetime import date


# from finance.utility import determine_user_role  # Import the determine_user_role function from the utils module


@login_required(login_url='staff_user:staff_login_process')
@role_required('Technical','Technical Manager')

def register_equipment(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        type_model = request.POST.get('type_model')
        quantity = request.POST.get('quantity')
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
            quantity=quantity,
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
        equipment.quantity = quantity
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
        # Technical users can see all pending requests
        general_requests = TaskAssignment.objects.filter(status='Pending')
    else:
        general_requests = TaskAssignment.objects.all()

    user_requests = TaskAssignment.objects.filter(requested_by=request.user)

    for user_request in user_requests:
        # Fetch original equipment details for each user request
        original_equipment_details = ", ".join([f"{assignment_equipment.equipment.name} - Quantity: {assignment_equipment.quantity}" for assignment_equipment in user_request.assignmentequipment_set.all()])
        # Update equipment details for each user request
        user_request.equipment_details = original_equipment_details
        # Update other fields as needed

    context = {
        'user_role': user_role,
        'general_requests': general_requests,
        'user_requests': user_requests,
    }
    
    return render(request, 'vifaa/equip_request_view.html', context)

@login_required(login_url='staff_user:staff_login_process')
def specific_request_view(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, pk=task_id)
    equipment_details = AssignmentEquipment.objects.filter(task_assignment=task_assignment)
    context = {
        'task_assignment': task_assignment,
        'equipment_details': equipment_details,
    }
    return render(request, 'vifaa/specific_request.html', context)


@role_required('Production', 'Presenter')
@login_required(login_url='staff_user:staff_login_process')
def edit_task_assignment(request, task_id):
    """
    This method allows authorized users (Production or Presenter) to update a specific task assignment.
    """
    
    task_assignment = TaskAssignment.objects.get(pk=task_id)
    
    if request.method == 'POST':
        print(request.POST)
        # Process the update data manually without forms
        assignment = request.POST.get('assignment')
        location = request.POST.get('location')
        category = request.POST.get('category')
        submission_date = request.POST.get('submission_date')
        agreement = request.POST.get('agreement') == 'on'
        detail_ids = request.POST.getlist('details')
        equipment_ids = request.POST.getlist('equipment[]')  # Correctly retrieve equipment IDs as an array
        quantities = request.POST.getlist('quantity[]')  # Correctly retrieve quantities as an array
        persons_assigned_ids = request.POST.getlist('persons_assigned')
        current_date = date.today()
        
        # Update the TaskAssignment object fields
        task_assignment.assignment = assignment
        task_assignment.location = location
        task_assignment.category = category
        task_assignment.submission_date = submission_date
        task_assignment.agreement = agreement
        task_assignment.date = current_date
        
        # Clear existing AssignmentEquipment objects (compatible with Django 5.0.2)
        existing_assignments = task_assignment.assignmentequipment_set.all()
        for assignment in existing_assignments:
            assignment.delete()

        # Update AssignmentEquipment objects (assuming a one-to-many relationship)
        for equipment_id, quantity in zip(equipment_ids, quantities):
            equipment = Equipment.objects.get(id=equipment_id)
            AssignmentEquipment.objects.create(
                task_assignment=task_assignment,
                equipment=equipment,
                quantity=quantity
            )

        # Update assigned persons
        task_assignment.persons_assigned.set(persons_assigned_ids)
        
        # Save the updated task assignment
        task_assignment.save()
        
        # Redirect to a success page or further processing
        return redirect('equipment:view_assignments')  # Replace with actual success URL
    
    else:
        # Prepare context data for rendering the update form (similar to task_assignment)
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
def approve_request(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, id=task_id)
    print(request.user.groups.all())  # Print all groups the user belongs to

    # Check if the current user is in the technical or treasurer group
    if request.user.groups.filter(name='Technical').exists():
        # Technical approves the request
        task_assignment.status = 'Under Review'
        task_assignment.save()
    elif request.user.groups.filter(name='Treasurer').exists():
        # Treasurer approves the request
        task_assignment.status = 'Approved'
        task_assignment.save()
    else:
        # User doesn't have permission to approve
        return HttpResponseForbidden("You don't have permission to approve this request.")

    # Redirect to a success page or another appropriate view
    return redirect('equipment:view_assignments')
    # Redirect to the view assignments page
    return redirect('equipment:view_assignments')

@login_required(login_url='staff_user:staff_login_process')
def reject_request(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, id=task_id)
    
    # Check if the current user is authorized to reject the request
    if request.user.groups.filter(name='Technical').exists() or request.user.groups.filter(name='Treasurer').exists():
        # Update the status to "Rejected"
        task_assignment.status = 'Rejected'
        task_assignment.save()
        
        # Redirect to a success page or another appropriate view
        return redirect('equipment:view_assignments')
    else:
        # User doesn't have permission to reject
        return HttpResponseForbidden("You don't have permission to reject this request.")



@login_required(login_url='staff_user:staff_login_process')
@role_required('Technical', 'Technical Manager')
def confirm_return(request, task_id):
    task_assignment = get_object_or_404(TaskAssignment, id=task_id)
    if task_assignment.status == 'Approved':
        # Update the status of the equipment to 'Available'
        equipment_details = AssignmentEquipment.objects.filter(task_assignment=task_assignment)
        for detail in equipment_details:
            equipment = detail.equipment
            equipment.status = 'Available'
            equipment.save()
        
        # Optionally update the task status or other fields
        task_assignment.status = 'Returned'  # Update task status to 'Returned' if needed
        task_assignment.save()

    return redirect('equipment:view_assignments')  # Update with your redirect URL
def view_approved_requests(request):
    approved_requests = TaskAssignment.objects.filter(status='Approved')
    context = {'approved_requests': approved_requests}
    return render(request, 'vifaa/approved_request.html', context)