from time import timezone
from django.conf import settings
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from users.models import Notification, Users
from users.serializers import RemittanceSerializer
from .models import Remittance, VendorasBeneficiary, Wallet, Transaction, Beneficiary
from shop.models import Order, PartnerInvestment, Vendor
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from .serializers import BeneficiarySerializer, VendorBeneficiarySerializer
from .utils import generate_reference, generate_remmittance_reference
from decimal import Decimal
from users.utils import verify_user_pin
from users.permisssion import IsPartner, IsAdmin, IsAdminOrPartner, IsVendor
from foodhybrid.utils import send_email
from django.utils.timezone import now
import stripe
from django.views.decorators.csrf import csrf_exempt


# class PartnerInvestmentView(APIView):
#     permission_classes = [IsAuthenticated]

#     # def validate_pin(self, user, pin):
#     #        if not user.check_pin(pin):  # Assuming `check_pin` exists on the user model
#     #            return False, Response({'detail': 'Invalid PIN'}, status=400)
#     #        return True, None

#     # create new or update current investment for current user
#     def post(self, request):
#         user = request.user
    
#         if user.user_type != 'partner':
#             return Response({'detail': 'Only partners can invest.'}, status=status.HTTP_403_FORBIDDEN)

#         amount = Decimal(str(request.data.get('amount')))
#         product_id = request.data.get('product_id')
#         investment_id = request.data.get('investment_id')  # Optional: for updating existing investment
#         pin = request.data.get('pin')

        

#         if not amount:
#             return Response({'detail': 'Investment amount is required.'}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             amount = Decimal(str(amount))
#             if amount <= 0:
#                 raise ValueError()
#         except ValueError:
#             return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)

#         wallet = getattr(user, 'wallet', None)
#         if not wallet:
#             return Response({'detail': 'Wallet not found.'}, status=status.HTTP_404_NOT_FOUND)

#         # Check if updating existing investment
#         if investment_id:
#             investment = get_object_or_404(PartnerInvestment, order_id=investment_id, partner=user)

#             # Calculate adjustment (positive = add funds, negative = withdraw)
#             diff = amount - investment.amount_invested
#             if wallet.balance < diff:
#                 return Response({'detail': 'Insufficient balance for adjustment.'}, status=status.HTTP_400_BAD_REQUEST)

#             # Adjust wallet and investment
#             wallet.balance -= diff
#             wallet.save()

#             investment.amount_invested = amount
#             investment.save()

#             print(type(amount),type(investment.amount_invested))

#             Transaction.objects.create(
#             user=user,
#             from_user="wallet",
#             transaction_type="investmentUpdate",
#             amount=amount,
#             status="pending",  # may require admin approval
#             reference=generate_reference(),
#             description="Order Purchased",
#             order_id = investment.order_id
#         )
#             send_email(user,"Investment", f"Your investment with id ${investment.order_id} have successfully been updated")
                 
#             return Response({
#                 'detail': 'Investment updated successfully.',
#                 'investment_id': investment.order_id,
#                 'new_balance': wallet.balance
#             })

#         # For new investments, product_id is required
#         if not product_id:
#             return Response({'detail': 'Product ID is required for new investment.'}, status=status.HTTP_400_BAD_REQUEST)

#         product = get_object_or_404(Product, id=product_id)

#         # is_valid, error_response = self.validate_pin(user, pin)
#         # if not is_valid:
#         #     return error_response

#         if wallet.balance < amount:
#             return Response({'detail': 'Insufficient balance.'}, status=status.HTTP_400_BAD_REQUEST)

#         # Deduct from wallet and create investment
#         print(amount)
#         wallet.balance -= amount
#         wallet.save()

#         investment = PartnerInvestment.objects.create(
#             partner=user,
#             product=product,
#             amount_invested=amount,
#             roi_rate=5.00,  # Default, make dynamic if needed
#             status='pending',
#         )
#         Transaction.objects.create(
#             user=user,
#             from_user="wallet",
#             transaction_type="investment",
#             amount=amount,
#             status="pending",  # may require admin approval
#             reference=generate_reference(),
#             description="Order Purchased",
#             order_id = investment.order_id
#         )

#         return Response({
#             'detail': 'Investment created successfully.',
#             'investment_id': investment.order_id,
#             'amount_invested': amount,
#             'new_balance': wallet.balance,
#             'status': investment.status
#         })
    
#     # get all investments for current user
#     def get(self, request):
#         user = request.user

#         if user.user_type != 'partner':
#             return Response({'detail': 'Only partners can view investments.'}, status=status.HTTP_403_FORBIDDEN)

#         investments = PartnerInvestment.objects.filter(partner=user).select_related('product').order_by('-created_at')

#         data = []
#         for inv in investments:
#             data.append({
#                 'order_id': inv.order_id,
#                 'product': inv.product.name,  
#                 'amount_invested': float(inv.amount_invested),
#                 'roi_rate': float(inv.roi_rate),
#                 'roi_paid': float(inv.roi_paid),
#                 'status': inv.status,
#                 'created_at': inv.created_at,
#                 'updated_at': inv.updated_at,
#             })

#         return Response({'investments': data})
stripe.api_key = settings.STRIPE_SECRET_KEY
class PartnerInvestmentDeleteView(APIView):
    permission_classes = [IsAdminOrPartner]
       # cancel investment for current user
    def delete(self, request, investment_id):
        user = request.user
        if user.user_type != 'partner':
            return Response({'detail': 'Only partners can cancel investments.'}, status=status.HTTP_403_FORBIDDEN)

        if not investment_id:
            return Response({'detail': 'Investment ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        investment = get_object_or_404(PartnerInvestment, order_id=investment_id, partner=user)

        if investment.status not in ['pending', 'approved']:
            return Response({'detail': f'Cannot cancel investment in status: {investment.status}.'},
                            status=status.HTTP_400_BAD_REQUEST)

        wallet = getattr(user, 'wallet', None)
        if wallet:
            wallet.balance += investment.amount_invested
            wallet.save()

        investment.delete()
        Notification.objects.create(
            user=user,
            title="Investment Cancelled",
            message=f"Your {investment.amount_invested} investment has been cancelled and your wallet has been credited!",
            event_type="investment",
            available_balance_at_time = wallet.balance
        )    

        return Response({'detail': 'Investment cancelled and amount refunded.', 'new_balance': wallet.balance})

class ApproveInvestmentView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, investment_id):
        # investment_id = request.data.get('investment_id')
        if not investment_id:
            return Response({'detail': 'Investment ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        investment = get_object_or_404(PartnerInvestment, order_id=investment_id)

        if investment.status != 'pending':
            return Response({'detail': f'Investment is already {investment.status}.'},
                            status=status.HTTP_400_BAD_REQUEST)

        investment.status = 'approved'
        investment.save()
        Notification.objects.create(
            user=investment.user,
            title="Investment Approved!",
            message=f"Your {investment.amount_invested} Investment has been approved",
            event_type="investment"
        )    

        return Response({'detail': 'Investment approved successfully.'})


class FundWalletView(APIView):
    permission_classes = [IsPartner]
    @swagger_auto_schema(
        operation_description="Fund the user's wallet.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='Amount to fund the wallet')
            },
            required=['amount', 'payment_method']
        ),
        responses={200: openapi.Response('Wallet funded successfully')}
    )
    
    def post(self, request):
        user = request.user

        # Restrict to partners
        if user.user_type != 'partner':
            return Response({'detail': 'Only partners can fund their wallets.'}, status=status.HTTP_403_FORBIDDEN)

        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method')
        if not amount:
            return Response({'detail': 'Amount to fund is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount))
        except ValueError:
            return Response({'detail': 'Invalid amount format.'}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({'detail': 'Amount must be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve or create the user's wallet
        wallet, created = Wallet.objects.get_or_create(user=user)

        stripe_amount = int(amount * 100)

        intent = stripe.PaymentIntent.create(
            amount=stripe_amount,
            currency="usd",
            automatic_payment_methods={"enabled": True},
            metadata={"user_id": user.id, "amount": str(amount)},
        )

        # Fund the wallet (increase balance)
        # print({"type":type(amount)})
        # print({"type":type(wallet.balance)})
        # wallet.balance += amount
        # wallet.save()
        # Notification.objects.create(
        #     user=user,
        #     title="Account Funding!",
        #     message=f"You just funded your account with {amount}",
        #     event_type="fund",
        #     from_user = payment_method,
        #     to_user="wallet",
        #     available_balance_at_time=wallet.balance
        # )    
        ref = generate_reference()
        Transaction.objects.create(
            user=user,
            from_user="Available Balance",
            payment_method= payment_method,
            transaction_type="fund",
            amount=amount,
            status="pending",  # may require admin approval
            reference= ref,
            description="Withdrawal request by partner",
            available_balance_at_time=wallet.balance
        )
        # send_email(user,"wallet_funded", "Wallet funding Successfully", extra_context={"amount":amount,"payment_method":payment_method,"reference": ref, "date": now()})

        return Response({'detail': f'Wallet funding initiated. We are confirming your payment.', 'client_secret': intent.client_secret, "reference":ref})


class WithdrawWalletView(APIView):
    permission_classes = [IsPartner]

    @swagger_auto_schema(
        operation_description="Withdraw from the user's wallet.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='Amount to withdraw from wallet')
            },
            required=['amount']
        ),
        responses={200: openapi.Response('Withdrawal successful')}
    )

    def post(self, request):
        user = request.user

        # Restrict to partners
        if user.user_type != 'partner':
            return Response({'detail': 'Only partners can withdraw from their wallets.'}, status=status.HTTP_403_FORBIDDEN)

        amount = request.data.get('amount')
        pin = request.data.get('transaction_pin')
        to = request.data.get('to')
        bank_name = request.data.get("bank_name")
        account_name = request.data.get("account_name")
        account_number = request.data.get("account_number")
        if not amount:
            return Response({'detail': 'Amount to withdraw is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(amount)
        except ValueError:
            return Response({'detail': 'Invalid amount format.'}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({'detail': 'Amount must be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the user's wallet
        wallet = getattr(user, 'wallet', None)
        if not wallet:
            return Response({'detail': 'Wallet not found for this user.'}, status=status.HTTP_404_NOT_FOUND)
        if not to:
            return Response({'detail': 'Please Select a beneficiary'}, status=status.HTTP_404_NOT_FOUND)
        
        
        if not pin:
                return Response({'detail': 'Transaction pin is required!.'}, status=400)
            
        if not user.pin_hash:
            return Response({"detail": "Please kindly set a pin."}, status=403)
        if not verify_user_pin(pin, user.pin_hash):
                return Response({"detail": "Invalid transaction PIN."}, status=403)

        
        # is_valid, error_response = self.validate_pin(user, pin)
        # if not is_valid:
        #     return error_response

        if wallet.balance < amount:
            return Response({'detail': 'Insufficient balance.'}, status=status.HTTP_400_BAD_REQUEST)

        # Withdraw the money (decrease balance)
        wallet.balance -= Decimal(str(amount))
        wallet.save()

        withdrawal_id = generate_reference()
        Transaction.objects.create(
            user=user,
            from_user="Portfolio",
            to = "Wallet",
            transaction_type="withdraw",
            amount=amount,
            status="pending",  # may require admin approval
            reference=withdrawal_id,
            description="Withdrawal request by partner",
            available_balance_at_time=wallet.balance
        )
        Notification.objects.create(
            user=user,
            title="Withdrawal!",
            message=f"Your withdrawal request of {amount} has been sent and is awaiting approval",
            event_type="withdraw",
            from_user="wallet",
            to_user=bank_name,
            available_balance_at_time=wallet.balance
                )   
        # admin_users = Users.objects.filter(is_staff=True)  # or is_superuser=True
        # for admin in admin_users:
        Notification.objects.create(
                user=user,
                title="Withdrawal!",
                message=f"Withdrawal: Request of {amount} from {user.first_name} {user.last_name}",
                event_type="admin",
                from_user="wallet",
                to_user=bank_name,
            )
        send_email(user,"withdrawal", "Withdrawal Successful!", extra_context={"amount":amount, "date": now()})


        return Response({'detail': f'Withdrawal awaiting approval!. New balance: {wallet.balance}',"withdrawal_id":withdrawal_id})
    

class BeneficiaryListCreateView(APIView):
    permission_classes = [IsPartner]

    def get(self, request):
        beneficiaries = Beneficiary.objects.filter(user=request.user)
        serializer = BeneficiarySerializer(beneficiaries, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BeneficiarySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({'detail': 'Beneficiary added successfully.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BeneficiaryDetailView(APIView):
    permission_classes = [IsPartner]

    def put(self, request, pk):
        try:
            beneficiary = Beneficiary.objects.get(pk=pk, user=request.user)
        except Beneficiary.DoesNotExist:
            return Response({'detail': 'Beneficiary not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = BeneficiarySerializer(beneficiary, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'detail': 'Beneficiary updated successfully.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            beneficiary = Beneficiary.objects.get(pk=pk, user=request.user)
            beneficiary.delete()
            return Response({'detail': 'Beneficiary removed.'}, status=status.HTTP_204_NO_CONTENT)
        except Beneficiary.DoesNotExist:
            return Response({'detail': 'Beneficiary not found.'}, status=status.HTTP_404_NOT_FOUND)


# class VendorRemitView(APIView):
#     permission_classes = [IsVendor]

#     def post(self, request):
#         user = request.user
#         if user.user_type != "vendor":
#             return Response({"error": "Only vendors can remit"}, status=status.HTTP_403_FORBIDDEN)

#         amount = request.data.get("amount")
#         if not amount:
#             return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)
        
#         remittance_ref = generate_remmittance_reference()
#         remit = Remittance.objects.create(
#             vendor=user,
#             amount=amount,
#             remittance_id=remittance_ref,
#             status="pending"
#         )

#         return Response({
#             "message": "Remittance awaiting confirmation",
#             "remittance": {
#                 "reference": remit.remittance_id,
#                 "amount": remit.amount,
#                 "status": remit.status,
#                 "created_at": remit.created_at
#             }
#         }, status=status.HTTP_201_CREATED)

# class VendorRemitView(APIView):
#     permission_classes = [IsVendor]

#     def post(self, request):
#         order_id = request.data.get("order_id")
#         amount = request.data.get("amount")

#         if not order_id or not amount:
#             return Response({"error": "Order ID and amount are required"}, status=400)

#         vendor = Vendor.objects.get(user=request.user)
#         order = Order.objects.get(reference=order_id, vendor=vendor)

#         remit = Remittance.objects.create(
#             vendor=vendor,
#             order=order,
#             amount=amount,
#             remittance_id=generate_remmittance_reference(),
#             status="pending"
#         )
#         otp = remit.generate_otp()
#         send_email(vendor.user, "code", "Your OTP Code", extra_context={"code": otp})

#         return Response({
#             "message": "Remittance initiated. Please confirm with OTP.",
#             "remittance": RemittanceSerializer(remit).data
#         }, status=201)


class VendorRemitView(APIView):
    permission_classes = [IsVendor]
    def post(self, request):
        user = request.user
        if user.user_type != "vendor":
            return Response({"error": "Only vendors can remit"}, status=status.HTTP_403_FORBIDDEN)

        amount = request.data.get("amount")
        if not amount:
            return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        remittance_ref = generate_remmittance_reference()
        vendor = Vendor.objects.get(user=request.user)
        remit = Remittance.objects.create(
            vendor=vendor,
            amount=amount,
            remittance_id=remittance_ref,
            status="pending"
        )
        Transaction.objects.create(
            user=user,
            from_user=vendor.user.first_name + " " + vendor.user.last_name,
            transaction_type="remittance",
            amount=amount,
            status="pending",  # may require admin approval
            reference=generate_reference(),
            description="Remittance Initiated",
            # order_id = investment.order_id
        )

        # Generate OTP
        otp = remit.generate_otp()
        user = vendor.user

        # TODO: Send OTP via email/SMS (pseudo)
        # send_sms(user.phone, f"Your remittance OTP is {otp}")
        send_email(user, "code", "Your OTP Code", extra_context={"code": otp})
        print(otp)

        return Response({
            "message": "Remittance initiated. Please confirm with OTP.",
            "remittance": {
                "reference": remit.remittance_id,
                "amount": remit.amount,
                "status": remit.status,
                "created_at": remit.created_at
            }
        }, status=status.HTTP_201_CREATED)

class ConfirmRemittanceView(APIView):
    permission_classes = [IsVendor]

    def post(self, request):
        reference = request.data.get("reference")
        otp = request.data.get("otp")

        try:
            vendor = Vendor.objects.get(user=request.user)
            remit = Remittance.objects.get(remittance_id=reference, vendor=vendor)
        except Remittance.DoesNotExist:
            return Response({"error": "Invalid remittance reference"}, status=status.HTTP_404_NOT_FOUND)

        if remit.status != "pending":
            return Response({"error": "Remittance already processed"}, status=status.HTTP_400_BAD_REQUEST)
        

        if not remit.otp or int(remit.otp) != otp:
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        if remit.otp_expires_at < now():
            return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Mark remittance as completed
        remit.status = "completed"
        remit.otp = None  # clear OTP
        remit.otp_expires_at = None
        remit.save()

        return Response({
            "message": "Remittance confirmed successfully",
            "remittance": {
                "reference": remit.remittance_id,
                "amount": remit.amount,
                "status": remit.status,
                "created_at": remit.created_at
            }
        }, status=status.HTTP_200_OK)

class AdminApproveRemittanceView(APIView):
    permission_classes = [IsAdmin]  # Only admins can approve

    def post(self, request, remittance_id):
        # remittance_id = request.data.get("remittance_id")
        action = request.data.get("action")  # approve | reject

        if not remittance_id or not action:
            return Response({"error": "Reference and action are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            remit = Remittance.objects.get(remittance_id=remittance_id)
        except Remittance.DoesNotExist:
            return Response({"error": "Invalid remittance reference"}, status=status.HTTP_404_NOT_FOUND)

        if remit.status != "completed":
            return Response({"error": "Only completed remittances can be approved/rejected"}, status=status.HTTP_400_BAD_REQUEST)

        if action == "approve":
            remit.status = "approved"
            # remit.admin_approved_at = now()
            # remit.admin_approved_by = request.user  # store which admin approved
        elif action == "reject":
            remit.status = "rejected"
            # remit.admin_rejected_at = now()
            # remit.admin_rejected_by = request.user
        else:
            return Response({"error": "Invalid action. Use 'approve' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        remit.save()

        return Response({
            "message": f"Remittance {action}d successfully",
            "remittance": {
                "remittance_id": remit.remittance_id,
                "amount": remit.amount,
                "status": remit.status,
                "created_at": remit.created_at,
                # "approved_at": getattr(remit, "admin_approved_at", None),
                # "approved_by": getattr(remit, "admin_approved_by", None).id if getattr(remit, "admin_approved_by", None) else None,
            }
        }, status=status.HTTP_200_OK)
    

# class AdminConfirmRemittanceView(APIView):
#     permission_classes = [IsAdmin]

#     def post(self, request, remittance_id):
#         try:
#             remit = Remittance.objects.get(remittance_id=remittance_id)
#         except Remittance.DoesNotExist:
#             return Response({"error": "Remittance not found"}, status=status.HTTP_404_NOT_FOUND)

#         action = request.data.get("action")  # "approve" or "reject"
#         note = request.data.get("note", "")  
#         if action not in ["approve", "reject"]:
#             return Response({"error": "Action must be 'approve' or 'reject'"}, status=status.HTTP_400_BAD_REQUEST)

#         if remit.status != "pending":
#             return Response({"error": f"Remittance already {remit.status}"}, status=status.HTTP_400_BAD_REQUEST)

#         if action == "approve":
#             remit.status = "completed"
#             remit.note = note
#         else:
#             remit.status = "rejected"
#             remit.note = note

#         remit.confirmed_by = request.user
#         remit.confirmed_at = now()
#         remit.save()

#         return Response({
#             "message": f"Remittance {action}d successfully",
#             "remittance": {
#                 "reference": remit.remittance_id,
#                 "vendor": remit.vendor.email,
#                 "amount": remit.amount,
#                 "status": remit.status,
#                 "confirmed_by": remit.confirmed_by.email if remit.confirmed_by else None,
#                 "confirmed_at": remit.confirmed_at
#             }
#         })


# class BeneficiaryListCreateView(generics.ListCreateAPIView):
#     serializer_class = VendorBeneficiarySerializer
#     permission_classes = [IsPartner]

#     def get_queryset(self):
#         return VendorasBeneficiary.objects.filter(partner=self.request.user)

#     def perform_create(self, serializer):
#         serializer.save(partner=self.request.user)

class VendorBeneficiaryView(APIView):
    permission_classes = [IsPartner]

    def post(self, request):
        partner = request.user
        vendor_id = request.data.get("vendor_id")

        if not vendor_id:
            return Response({"error": "vendor_id is required"}, status=400)

        try:
            vendor = Vendor.objects.get(vendor_id=vendor_id)
        except Vendor.DoesNotExist:
            return Response({"error": "Vendor not found"}, status=404)

        # Prevent duplicate
        beneficiary, created = VendorasBeneficiary.objects.get_or_create(
            partner=partner,
            vendor=vendor
        )

        if not created:
            return Response(
                {"message": "Vendor already saved as beneficiary"},
                status=200
            )

        return Response(
            {
                "message": "Vendor saved as beneficiary",
                "beneficiary": {
                    "id": beneficiary.id,
                    "vendor": vendor.store_name,
                    "vendor_id": vendor.vendor_id
                }
            },
            status=201
        )

    def get(self, request):
        partner = request.user
        beneficiaries = VendorasBeneficiary.objects.filter(partner=partner)
        data = [
            {
                "id": b.id,
                "vendor_id": b.vendor.id,
                "vendor_name": b.vendor.store_name,
                "vendor_email": b.vendor.store_email,
                "vendor_phone": b.vendor.store_phone,
            }
            for b in beneficiaries
        ]
        return Response(data, status=200)

class BeneficiaryDeleteView(generics.DestroyAPIView):
    serializer_class = VendorBeneficiarySerializer
    permission_classes = [IsPartner]

    def get_queryset(self):
        return VendorasBeneficiary.objects.filter(partner=self.request.user)


# --------STRIPE WEBHOOK.PY--------
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({"error": "Invalid signature"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    # ---------------- FUND WALLET ----------------
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        user_id = intent["metadata"].get("user_id")
        amount = Decimal(intent["metadata"].get("amount"))

        tx = Transaction.objects.filter(
            user_id=user_id,
            amount=amount,
            status="pending",
            payment_method="stripe",
            transaction_type="fund"
        ).last()

        if tx:
            wallet, _ = Wallet.objects.get_or_create(user_id=user_id)
            wallet.balance += amount
            wallet.save()

            tx.status = "success"
            tx.available_balance_at_time = wallet.balance
            tx.save()

            # Optional: notify user
            # send_notification(user_id, f"Wallet funded successfully: {amount}")

    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        user_id = intent["metadata"].get("user_id")
        amount = Decimal(intent["metadata"].get("amount"))

        tx = Transaction.objects.filter(
            user_id=user_id,
            amount=amount,
            status="pending",
            payment_method="stripe",
            transaction_type="fund"
        ).last()

        if tx:
            tx.status = "failed"
            tx.save()

            # Optional: notify user
            # send_notification(user_id, f"Wallet funding failed: {amount}")

    # ---------------- WITHDRAWALS (Stripe Payouts) ----------------
    elif event["type"] == "payout.paid":
        payout = event["data"]["object"]
        reference = payout.get("metadata", {}).get("reference")
        tx = Transaction.objects.filter(reference=reference, transaction_type="withdraw").last()

        if tx:
            tx.status = "success"
            tx.save()
            # send_notification(tx.user.id, f"Withdrawal successful: {tx.amount}")

    elif event["type"] == "payout.failed":
        payout = event["data"]["object"]
        reference = payout.get("metadata", {}).get("reference")
        tx = Transaction.objects.filter(reference=reference, transaction_type="withdraw").last()

        if tx:
            tx.status = "failed"
            tx.save()
            # send_notification(tx.user.id, f"Withdrawal failed: {tx.amount}")

    return JsonResponse({"status": "ok"})
# --------STRIPE WEBHOOK.PY--------