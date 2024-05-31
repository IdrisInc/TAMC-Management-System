from django.db import transaction 
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import Group
from .models import FinancialRequest, Item
from django.urls import reverse
from .utility import determine_user_role
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.db.models import Sum,F
import datetime



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




@login_required(login_url='staff_user:staff_login_process')
def request_detail_view(request):
    if request.user.is_authenticated:
        user = request.user
        user_role = determine_user_role(user)
        
        # Retrieve all financial requests
        all_user_requests = FinancialRequest.objects.filter(user=user)
        
        # Filter user requests based on user role
        if user_role == 'Technical Manager':
            user_requests = all_user_requests.filter(user__groups__name='Technical')
        elif user_role == 'Production':
            user_requests = all_user_requests.filter(user__groups__name='Presenter')
        elif user_role == 'Finance':
            # For Finance, include requests from Technical Managers and Production users
            user_requests = all_user_requests.filter(user__groups__name__in=['Technical Manager', 'Production'])
        elif user_role == 'Treasurer':
            # For Treasurer, include requests approved by Finance and requests made by Finance
            user_requests = all_user_requests.filter(Q(approved_by_finance=True) | Q(user__groups__name='Finance'))
        elif user_role == 'Cashier':
            # For Cashier, include requests approved by Treasurer and requests made by Cashier
            user_requests = all_user_requests.filter(Q(approved_by_treasurer=True) | Q(user=user))
        else:
            user_requests = all_user_requests
        
        # Fetch associated items for each user request
        for req in user_requests:
            req.user_items = Item.objects.filter(financial_request=req)
        
        # Include the user's own requests in the queryset
        user_requests |= all_user_requests.filter(user=user)
        
        # Filter general requests based on user role
        if user_role == 'Production':
            # Production users can see requests from Presenters in the general part
            general_requests = FinancialRequest.objects.filter(user__groups__name='Presenter')
        elif user_role == 'Technical Manager':
            # Technical Managers can see requests from Technical users in the general part
            general_requests = FinancialRequest.objects.filter(user__groups__name='Technical')
        elif user_role == 'Finance':
            # Finance users can see requests from Technical Managers and Production users in the general part
            general_requests = FinancialRequest.objects.filter(user__groups__name__in=['Technical Manager', 'Production']).exclude(user=user)
            general_requests |=FinancialRequest.objects.filter(approved_by_technical_manager =True)
            general_requests |= FinancialRequest.objects.filter(approved_by_production= True, )
        elif user_role == 'Treasurer':
            # Treasurer can see Presenter and Technical requests approved by Finance and requests made by Finance
            general_requests = FinancialRequest.objects.filter(Q(approved_by_finance=True) | Q(user__groups__name='Finance'))
            # Include requests made by Cashier
            general_requests |=FinancialRequest.objects.filter(user__groups__name='Cashier')
        elif user_role == 'Cashier':
            # Cashier can see requests approved by Treasurer and requests made by Cashier
            general_requests = FinancialRequest.objects.filter(approved_by_treasurer=True)
            # Exclude Cashier's own requests from the general part
            general_requests = general_requests.exclude(user=user)
            # Include requests made by Treasurer in the general part
            general_requests |= FinancialRequest.objects.filter(user__groups__name='Treasurer')
        else:
            # For other roles, fetch all general requests except Finance's own requests
            general_requests = FinancialRequest.objects.exclude(user=user)
        
        # Calculate total amount for each request
        for req in user_requests:
            req.total_amount = req.items.aggregate(total_amount=Sum(F('quantity') * F('price')))['total_amount'] or 0

        
        return render(request, 'financial/financial_req_detail.html', {
            'user_requests': user_requests,
            'general_requests': general_requests,
            'user_role': user_role,
            'logged_in_user': user,  # Pass the logged-in user to the template
        })
    else:
        # Redirect unauthenticated users to the login page with a message
        messages.info(request, 'Please log in to view your financial requests.')
        return redirect('staff_user:staff_login_process')




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
        comment = request.POST.get('comment')
        if action == 'approve':
            financial_request.comment = comment
            # Update request status based on user role
            if user_role == 'Finance':
                financial_request.approved_by_finance = True
            elif user_role == 'Treasurer':
                financial_request.approved_by_treasurer = True
            elif user_role == 'Cashier':
                financial_request.approved_by_cashier = True
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
    if (financial_request.approved_by_production or financial_request.approved_by_technical_manager):
        return HttpResponse("You cannot delete a request that has been approved or rejected by production or technical.")

    # Delete the financial request
    financial_request.delete()

    # Redirect to the financial request list page
    return redirect('finance:request_detail')



@login_required(login_url='staff_user:staff_login_process')
def approve_request(request, request_id):
    if request.method == 'POST':
        user = request.user
        financial_request = FinancialRequest.objects.get(pk=request_id)
        user_role = determine_user_role(user)

        # Handle approvals for various roles
        if user_role == 'Technical Manager':
            if financial_request.status == 'Pending':
                financial_request.approved_by_technical_manager = True
                financial_request.save()
                messages.success(request, 'Request approved by Technical Manager.')
            else:
                messages.error(request, 'Cannot proceed. Previous review not completed.')

        elif user_role == 'Production':
            if financial_request.status == 'Pending':
                financial_request.approved_by_production = True
                financial_request.save()
                messages.success(request, 'Request approved by Production.')
            else:
                messages.error(request, 'Cannot proceed. Previous review not completed.')

        elif user_role == 'Finance':
            if financial_request.status == 'Under Review':
                financial_request.approved_by_finance = True
                financial_request.save()
                messages.success(request, 'Request approved by Finance.')
            else:
                messages.error(request, 'Cannot proceed. Previous review not completed.')

        elif user_role == 'Treasurer':
            if financial_request.status == 'Under Review':
                financial_request.approved_by_treasurer = True
                financial_request.save()
                messages.success(request, 'Request approved by Treasurer.')

        elif user_role == 'Cashier':
            # Account to be Charged and Account Code are required fields
            account_to_charge = request.POST.get("account_to_charge")
            account_code = request.POST.get("account_code")

            if not account_to_charge or not account_code:
                messages.error(request, 'Please provide Account to be Charged and Account Code.')
                return HttpResponseBadRequest('Required information missing.')

            # Set the WEF date to the current date/time when the Cashier approves
            wef = datetime.datetime.now()

            if financial_request.status == 'Under Review':
                financial_request.approved_by_cashier = True
                financial_request.account_to_charge = account_to_charge
                financial_request.account_code = account_code
                financial_request.wef = wef  # Set WEF to the current date
                financial_request.save()

                messages.success(request, 'Request approved by Cashier.')
            else:
                messages.error(request, 'Cannot proceed. Previous review not completed.')

        # After approval, update the request status if required
        financial_request.update_status()

        # Redirect to the appropriate detail view after processing the request
        return redirect('finance:specific_detail', request_id=request_id)

    else:
        messages.error(request, 'Invalid request method.')
        return redirect('finance:request_detail', request_id)





def financial_requests_view(request):
    all_requests = FinancialRequest.objects.all()

    context = {
        'all_requests': all_requests,
    }
    return render(request, 'financial/all_financial_request.html', context)