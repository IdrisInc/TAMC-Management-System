from celery import shared_task
from .models import TaskAssignment
from django.utils import timezone

@shared_task
def delete_rejected_task(task_id):
    try:
        task_assignment = TaskAssignment.objects.get(pk=task_id)
        if task_assignment.status == 'Rejected':
            task_assignment.delete()
            print (f"Task with ID {task_id} has been deleted.")
        else:
            print(f"Task with ID {task_id} is no longer 'Rejected'. No deletion performed.")
    except TaskAssignment.DoesNotExist:
        print(f"Task with ID {task_id} does not exist.")
