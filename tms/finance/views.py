from django.db import transaction 
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import Group
from .models import FinancialRequest, Item
from django.urls import reverse
from .utility import determine_user_role
from django.http import HttpResponseForbidden, HttpResponse
from django.db.models import Q
from django.db.models import Sum,F
import datetime
from django.utils import timezone
from django.core.paginator import Paginator
from .tasks import delete_rejected_financial_request

# Role recognition
# def determine_user_role(user):
#     # Implement logic to determine user role based on groups or other criteria
#     # For example:
#     if user.groups.filter(name='Production').exists():
#         return 'Production'
#     elif user.groups.filter(name='Finance').exists():
#         return 'Finance'
#     elif user.groups.filter(name='Treasurer').exists():
#         return 'Treasurer'
#     elif user.groups.filter(name='Cashier').exists():
#         return 'Cashier'
#     elif user.groups.filter(name='Presenter').exists():
#         return 'Presenter'
#     elif user.groups.filter(name='Technical').exists():
#         return 'Technical'
#     elif user.groups.filter(name='Technical Manager').exists():
#         return 'Technical Manager'
#     elif user.groups.filter(name='Director').exists():
#         return 'Director'
#     else:
#         return 'Unknown'






@login_required(login_url='staff_user:staff_login_process')
def money(request):
    if request.method == 'POST':
        # Retrieve data from the POST request
        amount_numeric = request.POST.get('amount_numeric')
        amount_words = request.POST.get('amount_words')
        purpose = request.POST.get('purpose')
        total_request = request.POST.get('total_request')
        items = request.POST.getlist('item[]')
        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('price[]')

        # Validate the data
        if not (amount_numeric and amount_words and purpose and total_request):
            return HttpResponse('Please fill in all required fields.')

        if not all([item and quantity and price for item, quantity, price in zip(items, quantities, prices)]):
            return HttpResponse('Please fill in all item fields.')

        # Convert numeric fields to appropriate data types
        try:
            amount_numeric = float(amount_numeric)
            total_request = float(total_request)
            quantities = [int(quantity) for quantity in quantities]
            prices = [float(price) for price in prices]
        except ValueError:
            return HttpResponse('Invalid numeric input.')

        # Create a financial request and associated items within a transaction
        with transaction.atomic():
            # Save the financial request
            financial_request = FinancialRequest.objects.create(
                amount_numeric=amount_numeric,
                amount_words=amount_words,
                purpose=purpose,
                total_request=total_request,
                user=request.user  # Associate the request with the authenticated user
            )

            # Save items related to the financial request
            for item, quantity, price in zip(items, quantities, prices):
                Item.objects.create(financial_request=financial_request, item_name=item, quantity=quantity, price=price)

        return redirect('finance:request_detail')  # Redirect to a success page
    return render(request, 'financial/money.html')





from django.http import JsonResponse

@login_required(login_url='staff_user:staff_login_process')
def request_detail_view(request):
    user = request.user
    user_role = determine_user_role(user)
    has_permission_to_change = user.has_perm('finance.change_financialrequest')

    # Filter user-specific requests
    user_requests = FinancialRequest.objects.filter(user=user)

    # Initialize general_requests to an empty queryset
    general_requests = FinancialRequest.objects.none()

    # Map roles to queries to avoid redundant if-elif blocks
    role_based_queries = {
        'Technical Manager': Q(user__groups__name='Technical'),
        'Production Manager': Q(user__groups__name='Radio / TV Presenter'),
        'Finance': Q(user__groups__name__in=[
            'Technical Manager', 'Production Manager', 'Marketing Officer', 'Secretary', 'Finance','Managing Director','Editor','Cook','Driver'
        ]) | Q(approved_by_technical_manager__isnull=False) |
        Q(approved_by_production__isnull=False) |
        Q(approved_by_finance__isnull=False),
        'Treasurer': Q(approved_by_finance__isnull=False) |
                     Q(approved_by_assistant_treasurer__isnull=False) |
                     Q(user__groups__name__in=['Finance', 'Cashier','Assistant Treasurer']),
        'Assistant Treasurer': Q(approved_by_finance__isnull=False) |
                            Q(approved_by_treasurer__isnull=False) |
                               Q(user__groups__name__in=['Finance', 'Cashier','Treasurer']),
        'Cashier': Q(approved_by_treasurer__isnull=False) |
                  Q(approved_by_assistant_treasurer__isnull=False),
                #   Q(user__groups__name__in=['Treasurer','Assistant Treasurer']),
    }

    # Get requests based on role, excluding the user's own requests
    if user_role in role_based_queries:
        general_requests = FinancialRequest.objects.filter(role_based_queries[user_role]).exclude(user=user)

    # Create paginator for general requests
    general_requests_paginator = Paginator(general_requests, 5)  # Show 5 requests per page
    page_number_general_requests = request.GET.get('page')
    general_requests_page_obj = general_requests_paginator.get_page(page_number_general_requests)

    # Calculate total amounts for both user and general requests
    def calculate_total_amount(queryset):
        for req in queryset:
            req.total_amount = req.items.aggregate(
                total_amount=Sum(F('quantity') * F('price'))
            )['total_amount'] or 0

    calculate_total_amount(user_requests)
    calculate_total_amount(general_requests_page_obj)

    # Handle AJAX requests
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        requests_data = [{
            'request_from': req.user.get_full_name(),
            'date_requested': req.created_at.strftime('%Y-%m-%d'),
            'status': req.status,
            'detail_url': request.build_absolute_uri(
                reverse('finance:specific_detail', args=[req.id])
            )
        } for req in general_requests_page_obj]

        response_data = {
            'requests': requests_data,
            'has_next': general_requests_page_obj.has_next(),
            'next_page_number': general_requests_page_obj.next_page_number() if general_requests_page_obj.has_next() else None,
            'has_previous': general_requests_page_obj.has_previous(),
            'previous_page_number': general_requests_page_obj.previous_page_number() if general_requests_page_obj.has_previous() else None,
            'current_page_number': general_requests_page_obj.number,
            'total_pages': general_requests_page_obj.paginator.num_pages,
        }
        return JsonResponse(response_data)

    return render(request, 'financial/financial_req_detail.html', {
        'user_requests': user_requests,
        'general_requests': general_requests_page_obj,  # Use the paginated object
        'user_role': user_role,
        'logged_in_user': user,
        'has_permission_to_change': has_permission_to_change,
    })
    
    
def get_request_details(request):
    request_id = request.GET.get('id')
    try:
        financial_request = FinancialRequest.objects.get(id=request_id)
        data = {
            'amount': financial_request.amount_numeric,
            'date': financial_request.created_at.strftime('%Y-%m-%d'),
            'purpose': financial_request.purpose,
            'description': financial_request.description,
            'account': financial_request.account_to_charge if financial_request.approved_by_cashier else "Waiting for Cashier's Approval",
            'status': financial_request.status,
            'approval': financial_request.get_approval_stage()  # Ensure this method is available
        }
        return JsonResponse(data)
    except FinancialRequest.DoesNotExist:
        return JsonResponse({'error': 'Request not found'}, status=404)

    
@login_required(login_url='staff_user:staff_login_process')
def specific_detail_view(request, request_id):
    financial_request = get_object_or_404(FinancialRequest, id=request_id)
    user = request.user
    user_role = determine_user_role(user)
    
    # Calculate total for all items
    total = sum(item.quantity * item.price for item in financial_request.items.all())
    
    # Handle approval/rejection logic
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        if action == 'approve':
            financial_request.comment = comment
            # Update request status based on user role
            if user_role == 'Accountant':
                financial_request.approved_by_finance.add(user)
            elif user_role == 'Treasurer' :
                financial_request.approved_by_treasurer.add(user)
            elif user_role == 'Assistant Treasurer':
                
                financial_request.approved_by_assistant_treasurer.add(user)                
            elif user_role == 'Cashier':
                financial_request.approved_by_cashier.add(user)
            financial_request.update_status()  # Update the status based on approval fields
            financial_request.save()
        elif action == 'reject':
            financial_request.status = 'Rejected'
            financial_request.comment = comment
            financial_request.save()
    
    return render(request, 'financial/specific_detail.html', {
        'financial_request': financial_request,
        'user_role': user_role,
        'total': total,
    })

#Update or delete request

@login_required(login_url='staff_user:staff_login_process')
def update_request(request, request_id):
    # Retrieve the financial request object
    financial_request = get_object_or_404(FinancialRequest, pk=request_id)

    if request.method == 'POST':
        # Retrieve data from the POST request
        amount_numeric = request.POST.get('amount_numeric')
        amount_words = request.POST.get('amount_words')
        purpose = request.POST.get('purpose')
        total_request = request.POST.get('total_request')
        items = request.POST.getlist('item[]')
        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('price[]')

        # Validate the data
        if not all([amount_numeric, amount_words, purpose, total_request]) or \
           not all([item and quantity and price for item, quantity, price in zip(items, quantities, prices)]):
            return HttpResponseBadRequest('Invalid request data.')

        try:
            amount_numeric = float(amount_numeric)
            total_request = float(total_request)
            quantities = [int(quantity) for quantity in quantities]
            prices = [float(price) for price in prices]
        except ValueError:
            return HttpResponseBadRequest('Invalid numeric input.')

        # Update the financial request and related items within a transaction
        with transaction.atomic():
            financial_request.amount_numeric = amount_numeric
            financial_request.amount_words = amount_words
            financial_request.purpose = purpose
            financial_request.total_request = total_request
            financial_request.save()

            # Update or create items
            Item.objects.filter(financial_request=financial_request).delete()  # Delete existing items
            for item, quantity, price in zip(items, quantities, prices):
                Item.objects.create(financial_request=financial_request, item_name=item, quantity=quantity, price=price)

        return redirect(reverse('finance:request_detail') + f'?request_id={request_id}')  # Redirect to request detail with request_id

    return render(request, 'financial/update_req.html', {'request': financial_request})




@login_required(login_url='staff_user:staff_login_process')
def delete_confirmation(request, request_id):
    financial_request = get_object_or_404(FinancialRequest, pk=request_id)
    approval_status = (financial_request.approved_by_production or financial_request.approved_by_technical_manager)
    return render(request, 'financial/deletereq.html', {'request': financial_request, 'approval_status': approval_status})

@login_required(login_url='staff_user:staff_login_process')
def delete_request(request, request_id):
    # Retrieve the financial request object
    financial_request = get_object_or_404(FinancialRequest, pk=request_id)

    # Check if the user has permission to delete the request
    if request.user != financial_request.user:
        return HttpResponseForbidden("You don't have permission to delete this request.")

    # Check if the request has been approved or rejected by production or technical
    # if (financial_request.approved_by_production or financial_request.approved_by_technical_manager):
    #     return HttpResponse("You cannot delete a request that has been approved or rejected by production or technical.")

    # Delete the financial request
    financial_request.delete()

    # Redirect to the financial request list page
    return redirect('finance:request_detail')


@login_required(login_url='staff_user:staff_login_process')
def approve_request(request, request_id):
    if request.method == 'POST':
        user = request.user
        financial_request = get_object_or_404(FinancialRequest, pk=request_id)
        user_role = determine_user_role(user)

        # Handle approvals for various roles
        if user_role == 'Technical Manager':
            if financial_request.status == 'Pending':
                financial_request.approved_by_technical_manager.add(user)
                messages.success(request, 'Request approved by Technical Manager.')
            else:
                messages.error(request, 'Cannot proceed. Previous review not completed.')

        elif user_role == 'Production Manager':
            if financial_request.status == 'Pending':
                financial_request.approved_by_production.add(user)
                messages.success(request, 'Request approved by Production Manager.')
            else:
                messages.error(request, 'Cannot proceed. Previous review not completed.')

        elif user_role == 'Accountant':
            account_to_charge = request.POST.get("account_to_charge")
            account_code = request.POST.get("account_code")
           
            if not account_to_charge or not account_code:
                messages.error(request, 'Please provide Account to be Charged and Account Code.')
                return HttpResponseBadRequest('Required information missing.')

            if financial_request.status == 'Pending':
                # Update to 'Under Review' status first (or any intermediary status)
                financial_request.status = 'Under Review'
                financial_request.save()
                messages.info(request, 'Request is now under review.')
                
            if financial_request.status == 'Under Review':
                financial_request.approved_by_finance.add(user)
                financial_request.account_to_charge = account_to_charge
                financial_request.account_code = account_code
                
                financial_request.save()
                messages.success(request, 'Request approved by Finance.')
            else:
                messages.error(request, 'Cannot proceed. Previous review not completed.')

        elif user_role in ['Treasurer', 'Assistant Treasurer']:  # Combine Treasurer and Assistant Treasurer roles
            if financial_request.status == 'Under Review':
                if user_role == 'Treasurer':
                    financial_request.approved_by_treasurer.add(user)
                elif user_role == 'Assistant Treasurer':
                    financial_request.approved_by_assistant_treasurer.add(user)
                
                financial_request.save()  # Ensure changes are saved to the database
                messages.success(request, f'Request approved by {user_role}.')
            else:
                messages.error(request, 'Cannot proceed. Previous review not completed.')

        elif user_role == 'Cashier':
            wef = timezone.now()  # Set the WEF date to the current date/time when approved

            if financial_request.status == 'Under Review':
                financial_request.approved_by_cashier.add(user)
                financial_request.status = 'Approved'
                financial_request.wef = wef
                financial_request.save()
                messages.success(request, 'Request approved by Cashier.')
            else:
                messages.error(request, 'Cannot proceed. Previous review not completed.')

        # After approval, update the request status if required
        financial_request.update_status()

        # Redirect after processing
        return redirect('finance:specific_detail', request_id=request_id)

    else:
        messages.error(request, 'Invalid request method.')
        return redirect('finance:request_detail')


@login_required(login_url='staff_user:staff_login_process')
def reject_financial_request(request, request_id):
    if request.method == 'POST':
        user = request.user
        financial_request = get_object_or_404(FinancialRequest, pk=request_id)
        user_role = determine_user_role(user)  # Assuming you have this function to determine the role

        rejection_comment = request.POST.get('rejection_comment', '').strip()  # Get the rejection comment from the form

        # Handle rejection for various roles
        if user_role == 'Technical Manager':
            if financial_request.status in ['Pending', 'Under Review']:
                financial_request.status = 'Rejected'
                financial_request.rejected_by = user
                financial_request.rejection_comment = rejection_comment  # Store rejection comment
                financial_request.save()
                messages.success(request, 'Request rejected by Technical Manager.')

        elif user_role == 'Production Manager':
            if financial_request.status in ['Pending', 'Under Review']:
                financial_request.status = 'Rejected'
                financial_request.rejected_by = user
                financial_request.rejection_comment = rejection_comment  # Store rejection comment
                financial_request.save()
                messages.success(request, 'Request rejected by Production Manager.')

        elif user_role == 'Accountant':
            if financial_request.status in ['Pending', 'Under Review']:
                financial_request.status = 'Rejected'
                financial_request.rejected_by = user
                financial_request.rejection_comment = rejection_comment  # Store rejection comment
                financial_request.save()
                messages.success(request, 'Request rejected by Finance.')

        elif user_role in ['Treasurer', 'Assistant Treasurer']:
            if financial_request.status in ['Under Review']:
                financial_request.status = 'Rejected'
                financial_request.rejected_by = user
                financial_request.rejection_comment = rejection_comment  # Store rejection comment
                financial_request.save()
                messages.success(request, f'Request rejected by {user_role}.')

        elif user_role == 'Cashier':
            if financial_request.status in ['Under Review']:
                financial_request.status = 'Rejected'
                financial_request.rejected_by = user
                financial_request.rejection_comment = rejection_comment  # Store rejection comment
                financial_request.save()
                messages.success(request, 'Request rejected by Cashier.')

        # Trigger Celery task to delete the rejected request after 24 hours (86400 seconds)
        delete_rejected_financial_request.apply_async((request_id,), countdown= 60)

        # Redirect after processing
        return redirect('finance:specific_detail', request_id=request_id)

    else:
        messages.error(request, 'Invalid request method.')
        return redirect('finance:request_detail')

@login_required(login_url='staff_user:staff_login_process')
def financial_requests_view(request):
    all_requests = FinancialRequest.objects.all()

    context = {
        'all_requests': all_requests,
    }
    return render(request, 'financial/all_financial_request.html', context)


# views.py
from django.shortcuts import render
from .models import FinancialRequestArchive

def archived_requests_view(request):
    archived_requests = FinancialRequestArchive.objects.all()
    print(archived_requests)  # Check if this prints archived data

    context = {
        'archived_requests': archived_requests,
    }
    return render(request, 'archived_requests.html', context)
