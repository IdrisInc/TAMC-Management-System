from celery import shared_task
from django.core.mail import EmailMessage
from your_app.models import Program
import logging

logger = logging.getLogger(__name__)

@shared_task
def scheduled_weekly_report():
    try:
        # Example logic to generate email content
        programs = Program.objects.all()

        # Example of sending email using Django's EmailMessage
        email = EmailMessage(
            subject='Weekly Program Schedule',
            body='Please find attached the weekly program schedule.',
            from_email='allyidrisaally@gmail.com',
            to=['allyidrisaally@gmail.com'],
        )
        
        # Attachments or additional email settings can be added here
        # email.attach(...)

        email.send()

    except Exception as e:
        # Log the exception or handle it appropriately
        print(f"Error sending email: {str(e)}")
