# tasks.py

from celery import shared_task
from .models import FinancialRequest

@shared_task
def delete_rejected_financial_request(request_id):
    try:
        financial_request = FinancialRequest.objects.get(id=request_id)
        financial_request.delete()
        print(f"FinancialRequest with ID {request_id} has been deleted after 24 hours of rejection.")
    except FinancialRequest.DoesNotExist:
        print(f"FinancialRequest with ID {request_id} does not exist.")
