# vacation/tasks.py

from celery import shared_task
from django.utils import timezone
from .models import Holiday,PermissionRequest

@shared_task
def delete_rejected_holiday(holiday_id):
    try:
        holiday = Holiday.objects.get(id=holiday_id, status='rejected')
        time_diff = timezone.now() - holiday.updated_at  # Assuming `updated_at` is the last updated timestamp of the holiday
        if time_diff.days >= 1:  # If the holiday has been rejected for 24 hours or more
            holiday.delete()
            print(f"Holiday request with ID {holiday_id} has been deleted.")
        else:
            print(f"Holiday request with ID {holiday_id} has not been rejected for 24 hours yet.")
    except Holiday.DoesNotExist:
        print(f"Holiday with ID {holiday_id} does not exist or is not in 'rejected' status.")


@shared_task
def delete_rejected_permission_request(request_id):
    try:
        permission_request = PermissionRequest.objects.get(id=request_id)
        permission_request.delete()
        print(f"PermissionRequest with ID {request_id} has been deleted after 24 hours.")
    except PermissionRequest.DoesNotExist:
        print(f"PermissionRequest with ID {request_id} does not exist.")