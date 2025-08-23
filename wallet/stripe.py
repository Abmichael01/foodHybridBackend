from decimal import Decimal
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from django.utils.timezone import now

from .models import Wallet, Transaction

# @csrf_exempt
# def stripe_webhook(request):
#     payload = request.body
#     sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
#     endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

#     try:
#         event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=400)

#     if event["type"] == "payment_intent.succeeded":
#         intent = event["data"]["object"]
#         user_id = intent["metadata"].get("user_id")
#         amount = Decimal(intent["metadata"].get("amount"))

#         tx = Transaction.objects.filter(
#             user_id=user_id,
#             amount=amount,
#             status="pending",
#             payment_method="stripe"
#         ).last()

#         if tx:
#             wallet, _ = Wallet.objects.get_or_create(user_id=user_id)
#             wallet.balance += amount
#             wallet.save()

#             tx.status = "success"
#             tx.available_balance_at_time = wallet.balance
#             tx.save()

#     elif event["type"] == "payment_intent.payment_failed":
#         intent = event["data"]["object"]
#         user_id = intent["metadata"].get("user_id")
#         amount = Decimal(intent["metadata"].get("amount"))

#         tx = Transaction.objects.filter(
#             user_id=user_id,
#             amount=amount,
#             status="pending",
#             payment_method="stripe"
#         ).last()

#         if tx:
#             tx.status = "failed"
#             tx.save()


#     return JsonResponse({"status": "ok"})


