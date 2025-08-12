from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from users.models import Notification, Users
from .models import Wallet, Transaction, Beneficiary
from shop.models import PartnerInvestment
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from .serializers import BeneficiarySerializer
from .utils import generate_reference
from decimal import Decimal
from users.utils import verify_user_pin
from users.permisssion import IsPartner, IsAdmin, IsAdminOrPartner
from foodhybrid.utils import send_email
from django.utils.timezone import now


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

        # Fund the wallet (increase balance)
        print({"type":type(amount)})
        print({"type":type(wallet.balance)})
        wallet.balance += amount
        wallet.save()
        Notification.objects.create(
            user=user,
            title="Account Funded!",
            message=f"You just funded your account with {amount}",
            event_type="fund",
            from_user = payment_method,
            to_user="wallet",
            available_balance_at_time=wallet.balance
        )    
        ref = generate_reference()
        Transaction.objects.create(
            user=user,
            from_user="Available Balance",
            payment_method= payment_method,
            transaction_type="fund",
            amount=amount,
            # status="pending",  # may require admin approval
            reference= ref,
            description="Withdrawal request by partner",
            available_balance_at_time=wallet.balance
        )
        send_email(user,"wallet_funded", "Wallet Funded Successfully", extra_context={"amount":amount,"payment_method":payment_method,"reference": ref, "date": now()})

        return Response({'detail': f'Wallet funded successfully. New balance: {wallet.balance}'})


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



