from django.core.mail import send_mail
from django.template.loader import render_to_string

def send_order_confirmation_email(user, order):
    subject = f"Order Confirmation - {order.reference}"
    message = render_to_string('order_confirmation.html', {
        'user': user,
        'order': order,
        'items': order.items.all()
    })
    try:
        send_mail(subject, '', None, [user.email], html_message=message, fail_silently=True)
    except Exception as e:
        import logging
        logging.error(f"Order confirmation email sending failed: {e}")
