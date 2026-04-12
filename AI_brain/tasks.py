# Example Celery task for async email sending
from celery import shared_task
from django.core.mail import send_mail

def send_async_email(subject, message, recipient_list):
    send_mail(subject, message, 'noreply@aihealth.com', recipient_list)

@shared_task
def send_email_task(subject, message, recipient_list):
    send_async_email(subject, message, recipient_list)

# Example Celery task for PDF receipt generation
@shared_task
def generate_pdf_receipt(order_id):
    # Stub: Implement PDF generation logic
    pass

# Example Celery task for SMS notification (stub)
@shared_task
def send_sms_task(phone_number, message):
    # Integrate with Africa's Talking/Twilio here
    pass
