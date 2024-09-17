from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_verification_email(user, verification_link):
    subject = 'Verify Your Email Address'
    html_message = render_to_string('emails/verification_email.html', {'user': user, 'verification_link': verification_link})
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    to = user.email

    send_mail(subject, plain_message, from_email, [to], html_message=html_message)

def send_password_reset_email(user, reset_link):
    subject = 'Password Reset Request'
    html_message = render_to_string('emails/password_reset_email.html', {'user': user, 'reset_link': reset_link})
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    to = user.email

    send_mail(subject, plain_message, from_email, [to], html_message=html_message)
