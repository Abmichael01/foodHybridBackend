from django.http import JsonResponse
from rest_framework import status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Users, EmailOTP, Driver, OrderDeliveryConfirmation, Notification
from shop.models import Order, PartnerInvestment, ROIPayout, Vendor
from wallet.models import Remittance, Transaction, Wallet
from wallet.serializers import TransactionSerializer 
from drf_yasg.utils import swagger_auto_schema
from .serializers import AdminOrderSerializer, DeliveryConfirmationCreateSerializer, PartnerAdminReportSerializer, PartnerDetailSerializer, PartnerInvestmentListSerializer, PartnerListSerializer, VendorDetailSerializer, VendorOverviewSerializer, VendorSerializer, PartnerInvestmentSerializer, PartnerProfileSerializer, PartnerSignUpSerializer, DriverCreateSerializer, DriverLoginSerializer, OrderDeliveryConfirmationSerializer, CompleteRegistrationSerializer, ResetPasswordOTPSerializer, NotificationSerializer, VendorSignupSerializer
from django.utils import timezone
from datetime import date, datetime
from foodhybrid.utils import send_email
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser,JSONParser
from rest_framework.pagination import PageNumberPagination
from django.db.models import Sum, Q
from .utils import generate_otp, get_tokens_for_user,set_user_pin,retrieve_user_pin
from .permisssion import IsPartner, IsAdmin
from rest_framework.permissions import AllowAny
from django.utils.timezone import now
from django.db.models.functions import TruncDate
from decimal import Decimal
import os
from django.utils import timezone
from rest_framework.generics import UpdateAPIView, DestroyAPIView,ListAPIView
from rest_framework.filters import SearchFilter
from django.db import models
from django.contrib.auth import authenticate


# Create your views here.


def api_root(request):
    return JsonResponse({"message": "Backend API root is working!"})

# Partners SignUp   
# class SignupView(APIView):
#     permission_classes = [AllowAny]
#     def post(self, request):
#         resend = request.data.get('resend', False)
#         serializer = PartnerSignUpSerializer(data=request.data)
#         if resend:
#             otp_code = generate_otp()
#             EmailOTP.objects.create(user=user, otp=otp_code)
#             send_email(user,"code","Your OTP Code", extra_context={"code":otp})
#             return Response({'detail': 'OTP resent to your email.'}, status=status.HTTP_200_OK)
        
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#         email = serializer.validated_data['email']
#         existing_user = Users.objects.filter(email=email).first()

#         if existing_user:
#             if existing_user.is_email_verified:
#                 return Response({'detail': 'Email already verified.'}, status=status.HTTP_400_BAD_REQUEST)
           
#             user = existing_user
#         else:
#             user = serializer.save() 

#         otp = generate_otp()
#         EmailOTP.objects.create(user=user, otp=otp)
#         send_email(user,"code","Your OTP Code", extra_context={"code":otp})

#         return Response({'detail': 'OTP sent to your email.', 'otp': otp}, status=status.HTTP_200_OK)
    
#     def patch(self, request):
#         serializer = CompleteRegistrationSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             email = serializer.validated_data['email']
#             user = Users.objects.filter(email=email).first()
#             send_email(user,"account_created", "Account Created Successfully!")
#             return Response({'detail': 'Registeration Completed, Signin to access your account!.'}, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SignupView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(  
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'user_type': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['email', 'user_type']
        ),
        responses={201: openapi.Response(
            description="Email verified successfully. Go ahead and complete your signup process!",
            schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING),
                'status': openapi.Schema(type=openapi.TYPE_INTEGER),
            })
        )}
    )

    def post(self, request):
        resend = request.data.get('resend', False)
        email = request.data.get('email')

        if resend:
            user = Users.objects.filter(email=email).first()
            if not user:
                return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

            otp_code = generate_otp()
            EmailOTP.objects.create(user=user, otp=otp_code)
            send_email(user, "code", "Your OTP Code", extra_context={"code": otp_code})
            return Response({'detail': 'OTP resent to your email.'}, status=status.HTTP_200_OK)

        # Always use a basic serializer just for validating email/password
        base_serializer = PartnerSignUpSerializer(data=request.data)  
        if not base_serializer.is_valid():
            return Response(base_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = base_serializer.validated_data['email']
        existing_user = Users.objects.filter(email=email).first()

        if existing_user:
            if existing_user.is_email_verified:
                return Response({'detail': 'Email already verified.'}, status=status.HTTP_400_BAD_REQUEST)
            user = existing_user
        else:
            user = base_serializer.save()  # Just creates the base user

        otp = generate_otp()
        EmailOTP.objects.create(user=user, otp=otp)
        send_email(user, "code", "Your OTP Code", extra_context={"code": otp})

        return Response({'detail': 'OTP sent to your email.'}, status=status.HTTP_200_OK)

    def patch(self, request):
        user_type = request.data.get('user_type', 'partner')  # ✅ Now handled here

        if user_type == 'vendor':
            serializer = VendorSignupSerializer(data=request.data)
        else:
            serializer = CompleteRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            email = serializer.validated_data['email']
            user = Users.objects.filter(email=email).first()
            send_email(user, "account_created", "Account Created Successfully!")
            return Response(
                {'detail': 'Registration Completed, Sign in to access your account!'}, 
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    @swagger_auto_schema(  
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'otp': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['email', 'otp']
        ),
        responses={201: openapi.Response(
            description="Email verified successfully. Go ahead and complete your signup process!",
            schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING),
                'status': openapi.Schema(type=openapi.TYPE_INTEGER),
            })
        )}
    )
    def post(self, request):
        email = request.data.get('email')
        otp_input = request.data.get('otp')

        user = Users.objects.filter(email=email).first()
        if not user:
            return Response({'detail': 'Invalid email, Please sign up'}, status=status.HTTP_400_BAD_REQUEST)

        otp_record = EmailOTP.objects.filter(user=user, otp=otp_input).first()
        print(otp_input, user)
        if otp_record:
            user.is_email_verified = True
            user.save()
            EmailOTP.objects.filter(user=user).delete()

            return Response({'detail': 'Email verified successfully. Go ahead and complete your signup process!'}, status=status.HTTP_200_OK)
        
        return Response({'detail': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)

class VendorUpdateView(UpdateAPIView):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [IsAdmin]
    lookup_field = 'vendor_id'
    http_method_names = ['put', 'patch']

class VendorDeleteView(DestroyAPIView):
    queryset = Vendor.objects.all()
    permission_classes = [IsAdmin]
    lookup_field = 'vendor_id'

    def delete(self, request, *args, **kwargs):
        vendor_ids = request.data.get("vendor_ids")  # Expecting a list for multiple delete

        if vendor_ids:
            # Multiple deletion
            deleted_count, _ = Vendor.objects.filter(vendor_id__in=vendor_ids).delete()
            return Response(
                {"message": f"{deleted_count} vendors deleted successfully."},
                status=status.HTTP_200_OK
            )
        else:
            # Single deletion (default DestroyAPIView behavior)
            return super().delete(request, *args, **kwargs)

class VendorPagination(PageNumberPagination):
    page_size = 10  # default per page
    page_size_query_param = 'page_size'  # allow override via query param
    max_page_size = 100

class VendorListView(ListAPIView):
    queryset = Vendor.objects.all().order_by('-created_at')
    serializer_class = VendorSerializer
    pagination_class = VendorPagination
    filter_backends = [SearchFilter]
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'user__phone_number']
    # search_fields = ['name', 'email', 'phone']

class CreateAndSendDeliveryOTPView(APIView):
    def post(self, request):
        serializer = DeliveryConfirmationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Check if already exists
        investment = serializer.validated_data['investment']
        if OrderDeliveryConfirmation.objects.filter(investment=investment).exists():
            return Response({"detail": "Delivery already initiated for this investment"}, status=400)

        # Save and generate OTP
        delivery = serializer.save()
        otp = delivery.generate_otp()

        # Send email
        EmailOTP.objects.create(user=delivery.store_name, otp=otp)
        send_email(delivery,"code","Your OTP Code", extra_context={"code":otp})
        # send_otp_email(delivery.owner_email, otp, delivery.store_name)
        return Response({"detail": "Delivery created and OTP sent"}, status=201)


class ConfirmDeliveryView(APIView):
    def post(self, request):
        investment_id = request.data.get("investment_id")
        otp = request.data.get("otp")

        try:
            delivery = OrderDeliveryConfirmation.objects.get(investment_id=investment_id)
        except OrderDeliveryConfirmation.DoesNotExist:
            return Response({"detail": "No delivery record found"}, status=404)

        if delivery.is_confirmed:
            return Response({"detail": "Delivery already confirmed"}, status=400)

        if delivery.confirm_delivery(otp): 
            partner = delivery.investment.partner 
            Notification.objects.create(
                user=partner.user,
                title="Order Delivered",
                message=f"Order {investment_id} successfully delivered to the vendor.",
                event_type="order",
            )
            admins = Users.objects.filter(is_superuser=True)  # Or use is_staff/group filter
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    title="Order Delivered",
                    message=f"Order {investment_id} successfully delivered to the vendor.",
                    event_type="admin",
                    from_user=request.user.username if request.user else "system",
                    to_user=admin.username
                )
            send_email(partner.user,"order_delivered", "Order {investment_id} successfully delivered!")
            return Response({"detail": "Delivery confirmed successfully"}, status=200)
        return Response({"detail": "Invalid OTP"}, status=400)
    


# class VendorCreateView(APIView):
#     permission_classes = [IsAdmin]
#     parser_classes = [MultiPartParser, FormParser]  # to handle image uploads

#     def post(self, request):
#         serializer = VendorSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"detail": "Vendor created successfully", "data": serializer.data}, status=201)
#         return Response(serializer.errors, status=400)

class VendorCreateView(APIView):
    permission_classes = [AllowAny]  # ✅ anyone can signup
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = VendorSignupSerializer(data=request.data)
        if serializer.is_valid():
            vendor = serializer.save()
            return Response({
                "detail": "Vendor registered successfully",
                "vendor": VendorSignupSerializer(vendor).data
            }, status=201)
        return Response(serializer.errors, status=400)
    

# class ResendOTPView(APIView):
    # @swagger_auto_schema(
    #     request_body=openapi.Schema(
    #         type=openapi.TYPE_OBJECT,
    #         properties={
    #             'email': openapi.Schema(type=openapi.TYPE_STRING),
    #             'otp_input': openapi.Schema(type=openapi.TYPE_STRING),
    #         },
    #         required=['email', 'otp_input']
    #     ),
    #     responses={201: openapi.Response(
    #         description="OTP has been resent!",
    #         schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
    #             'message': openapi.Schema(type=openapi.TYPE_STRING),
    #             'status': openapi.Schema(type=openapi.TYPE_INTEGER),
    #         })
    #     )}
    # )
    # def post(self, request):
        # email = request.data.get('email')
        # if not email:
        #     return Response({"error": "Email is required."}, status=400)

        # try:
        #     user = Users.objects.get(email=email)
        # except Users.DoesNotExist:
        #     return Response({"error": "User not found."}, status=404)

        # # Optional: prevent spamming OTP
        # if user.otp_created_at and timezone.now() < user.otp_created_at + timedelta(minutes=1):
        #     return Response({"error": "You can request a new OTP after 1 minute."}, status=429)

        # user.generate_otp()

        # send_mail(
        #     subject="Your OTP Code",
        #     message=f"Your new OTP is: {user.email_otp}",
        #     from_email="noreply@example.com",
        #     recipient_list=[user.email],
        # )

        # return Response({"message": "OTP has been resent."}, status=200)

# forgot password (request,verify and set new password)
# set resend to 'true' to resend otp
class PasswordResetView(APIView):
        @swagger_auto_schema(
        request_body=ResetPasswordOTPSerializer,
        responses={201: openapi.Response(
            description="Reset OTP has been sent!",
            schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING),
                'status': openapi.Schema(type=openapi.TYPE_INTEGER),
            })
        )}
    )
        def post(self, request):
            resend = request.data.get('resend', False)
            serializer = ResetPasswordOTPSerializer(data=request.data)
            if resend:
                email = request.data.get('email')
                if not email:
                    return Response({"email": "This field is required to resend OTP."}, status=400)
                try:
                    user = Users.objects.get(email=email)
                except Users.DoesNotExist:
                    return Response({"email": "User not found."}, status=400)

                otp_code = generate_otp()
                EmailOTP.objects.create(user=user, otp=otp_code)
                # send_reset_otp_email(user, otp_code)
                send_email(user,"code", "Your OTP Code", extra_context={
                        "code":otp_code}) 
                return Response({"detail": "OTP resent to your email."}, status=200)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                otp = request.data.get('otp')
                new_password = request.data.get('new_password')
                if not otp and not new_password:
                    # Stage 1: Send OTP
                    otp_code = generate_otp()
                    EmailOTP.objects.create(user=user, otp=otp_code)
                    send_email(user, "code", "Your OTP Code", extra_context={
                        "code":otp_code})  # Your email utility
                    return Response({"detail": "OTP sent to your email."}, status=status.HTTP_200_OK)
                elif otp and not new_password:
                    # Stage 2: Verify OTP only
                    return Response({"detail": "OTP is valid. You can now reset your password."}, status=status.HTTP_200_OK)
                elif otp and new_password:
                    # Stage 3: Reset password
                    serializer.save()
                    return Response({"detail": "Password has been reset successfully."}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# class RequestResetPasswordOtp(APIView):
#     @swagger_auto_schema(
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 'email': openapi.Schema(type=openapi.TYPE_STRING),
#             },
#             required=['email']
#         ),
#         responses={201: openapi.Response(
#             description="Reset OTP has been sent!",
#             schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
#                 'message': openapi.Schema(type=openapi.TYPE_STRING),
#                 'status': openapi.Schema(type=openapi.TYPE_INTEGER),
#             })
#         )}
#     )
#     def post(self, request):
#         email = request.data.get('email')

#         if not email:
#             return Response({
#                 "status": "error",
#                 "message": "Email is required."
#             }, status=400)
#         try:
#             user = Users.objects.get(email=email)
#         except Users.DoesNotExist:
#             return Response({
#                 "status": "error",
#                 "message": "No user found with this email."
#             }, status=404)
#         otp = generate_otp()
#         user.reset_otp = otp
#         user.reset_otp_expiry = timezone.now() + timezone.timedelta(minutes=10)
#         user.save()
#         # send_reset_otp_email(user, otp)
#         return Response({
#             "status": "success",
#             "message": "OTP has been sent to your email.",
#             "email": email,
#             "expires_in": 600,  # 10 minutes in seconds
#             "otp": otp
#         }, status=status.HTTP_200_OK)


# class ResetPasswordWithOTPView(APIView):
#     @swagger_auto_schema(
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 'email': openapi.Schema(type=openapi.TYPE_STRING),
#                 'otp': openapi.Schema(type=openapi.TYPE_STRING),
#                 'new_password': openapi.Schema(type=openapi.TYPE_STRING),
#             },
#             # required=['email', 'otp', 'new_password']
#         ),
#         responses={201: openapi.Response(
#             description="Password Reset Successful, you can now login!",
#             schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
#                 'message': openapi.Schema(type=openapi.TYPE_STRING),
#                 'status': openapi.Schema(type=openapi.TYPE_INTEGER),
#                 'email': openapi.Schema(type=openapi.TYPE_INTEGER),
#             })
#         )}
#     )
#     def post(self, request):
#         email = request.data.get("email")
#         otp = request.data.get("otp")
#         new_password = request.data.get("new_password")

#         if not all([email, otp, new_password]):
#             return Response({
#                 "status": "error",
#                 "message": "Email, OTP, and new password are required."
#             }, status=400)

#         try:
#             user = Users.objects.get(email=email)
#         except Users.DoesNotExist:
#             return Response({
#                 "status": "error",
#                 "message": "User not found."
#             }, status=404)

#         if user.reset_otp != otp:
#             return Response({
#                 "status": "error",
#                 "message": "Invalid OTP."
#             }, status=400)

#         if timezone.now() > user.reset_otp_expiry:
#             return Response({
#                 "status": "error",
#                 "message": "OTP has expired."
#             }, status=400)

#         # Set the new password
#         user.set_password(new_password)
#         user.reset_otp = None
#         user.reset_otp_expiry = None
#         user.save()

#         return Response({
#             "status": "success",
#             "message": "Password reset successful. You can now log in.",
#             "email": user.email
#         }, status=200)

# authenticated user reset password
class ChangePasswordView(APIView):
    permission_classes = [IsPartner]
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'old password': openapi.Schema(type=openapi.TYPE_STRING),
                'new password': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['old password', 'new password']
        ),
        responses={201: openapi.Response(
            description="Password changed successfully!",
            schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING),
                'status': openapi.Schema(type=openapi.TYPE_INTEGER),
            })
        )}
    )

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response({
                "status": "error",
                "message": "Old and new password are required."
            }, status=400)

        if not user.check_password(old_password):
            return Response({
                "status": "error",
                "message": "Old password is incorrect."
            }, status=400)

        user.set_password(new_password)
        user.save()
        
        # send_email(user,"Password Changed!", "Your password has been reset!")

        return Response({
            "status": "success",
            "message": "Password changed successfully."
        }, status=200)
    

# parners and admin signin
class SigninView(APIView): 
    def post(self, request):
        login_input = request.data.get('username')  # Can be username or email
        password = request.data.get('password')
        expected_user_type = request.data.get('user_type')

        if not login_input or not password or not expected_user_type:
            return Response({'detail': 'Username/email, password and user type required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Find user by email or username
        user = Users.objects.filter(email=login_input).first() or Users.objects.filter(username=login_input).first()

        if user and user.check_password(password):
            if not user.is_email_verified:
                return Response({'detail': 'Email not verified.'}, status=status.HTTP_403_FORBIDDEN)
            
            if user.user_type != expected_user_type:
               return Response({'detail': f'User is not of type {expected_user_type}.'},
                               status=status.HTTP_403_FORBIDDEN)
            tokens = get_tokens_for_user(user)
            return Response({
                'detail': 'Login successful.',
                'tokens': tokens
            })
        else:
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
        
# admin create driver
class DriverCreateView(APIView):
    permission_classes = [IsAdmin]
    @swagger_auto_schema()
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        username = request.data.get('username')
        if not all([email, password, username]):
            return Response({"error": "Missing user info"}, status=400)
        user = Users.objects.create(
            email=email,
            username=username,
            user_type='driver',
            is_email_verified=True  # Admin adds them manually
        )
        user.set_password(password)
        user.save()

        # Step 2: create profile
        serializer = DriverCreateSerializer(data=request.data, context={"user": user})
        if serializer.is_valid():
            serializer.save()
            return Response({"msg": "Driver created successfully"}, status=201)
        return Response(serializer.errors, status=400)
    

class WithdrawalSummaryAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, *args, **kwargs):
        request_time = now()
        user = request.user

        # Get all pending withdrawal transactions for partners
        pending_qs = Transaction.objects.filter(
            transaction_type='withdraw',
            status='pending',
            user__user_type="partner"
        ).select_related('user', 'user__wallet')

        # Prepare response list
        withdrawals_data = []
        for tx in pending_qs:
            partner = tx.user
            partner_name = partner.get_full_name() if hasattr(partner, 'get_full_name') else f"{partner.first_name} {partner.last_name}"
            balance = getattr(partner.wallet, 'balance', 0)
            if user.profile_picture:
                profile_picture_url = user.profile_picture.url
            else:
                profile_picture_url = None

            withdrawals_data.append({
                "partner_name": partner_name,
                "profile_pic": profile_picture_url,
                "amount": tx.amount,
                "balance": balance,
                "from_user": tx.from_user,
                "to": tx.to,  # Or dynamically from transaction if available
                "requested_at": tx.created_at,
                "status": tx.status,
                "withdraw_id": tx.reference
            })

        return Response(withdrawals_data, status=status.HTTP_200_OK)


# class WithdrawalSummaryAPIView(APIView):
#     permission_classes = [IsAdmin]

#     def get(self, request, *args, **kwargs):

#         # Global queries
#         pending_qs = Transaction.objects.filter(transaction_type='withdraw', status='pending')
#         approved_qs = Transaction.objects.filter(transaction_type='withdraw', status='approved')

#         total_pending_amount = pending_qs.aggregate(total=Sum('amount'))['total'] or 0
#         total_pending_count = pending_qs.count()

#         total_approved_amount = approved_qs.aggregate(total=Sum('amount'))['total'] or 0
#         total_approved_count = approved_qs.count()

#         # Per-user summaries
#         user_summaries = []
#         partners = Users.objects.filter(user_type="partner")  # Only partners
#         partner_data_map = {
#             p.id: data
#             for p, data in zip(partners, PartnerAdminReportSerializer(partners, many=True).data)
#         }

#         for user in partners:
#             user_pending = pending_qs.filter(user=user)
#             user_approved = approved_qs.filter(user=user)

#             pending_amount = user_pending.aggregate(total=Sum('amount'))['total'] or 0
#             approved_amount = user_approved.aggregate(total=Sum('amount'))['total'] or 0

#             pending_count = user_pending.count()
#             approved_count = user_approved.count()

#             if pending_amount > 0 or approved_amount > 0:
#                 user_summaries.append({
#                     "partner_details": partner_data_map[user.id],  # Full partner details
#                     "pending_withdrawals_amount": pending_amount,
#                     "pending_withdrawals_count": pending_count,
#                     "requested_at":
#                     # "approved_withdrawals_amount": approved_amount,
#                     # "approved_withdrawals_count": approved_count,
#                 })

#         return Response({
#             # "request_time": request_time.isoformat(),
#             "global_summary": {
#                 "total_pending_amount": total_pending_amount,
#                 "total_pending_count": total_pending_count,
#                 "total_approved_amount": total_approved_amount,
#                 "total_approved_count": total_approved_count
#             },
#             "user_summaries": user_summaries
#         }, status=status.HTTP_200_OK)  

# class AdminRecentOrdersView(APIView):
#     permission_classes = [IsAdmin]

#     def get(self, request):
#         limit = int(request.query_params.get('limit', 10))  # e.g. ?limit=5
#         orders = Order.objects.order_by('-created_at')[:limit]
#         # select_related('partner', 'vendor').prefetch_related('items').

#         serializer = AdminOrderSerializer(orders, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200

class AdminRecentOrdersView(ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminOrderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ['created_at', 'amount_invested', 'status']
    ordering = ['-created_at']
    search_fields = ['order_id', 'partner__username', 'partner__email', 'product__name', 'status']

    def get_queryset(self):
        qs = PartnerInvestment.objects.select_related('partner').prefetch_related('product__vendor').all()
        vendor_id = self.request.query_params.get('vendor')
        if vendor_id:
            pass
            qs = qs.filter(product__shop__vendor__id=vendor_id).distinct()
        return qs

#deliery form


# driver login
class DriverLoginView(APIView):
    @swagger_auto_schema()
    def post(self, request):
        serializer = DriverLoginSerializer(data=request.data)
        if serializer.is_valid():
            driver_id = serializer.validated_data['driver_id']
            password = serializer.validated_data['password']

            try:
                profile = Driver.objects.get(driver_id=driver_id)
                user = profile.user
                if user.check_password(password):
                    tokens = get_tokens_for_user(user)
                    return Response({
                        "message": "Login successful",
                        "tokens": tokens
                    })
                return Response({"error": "Invalid credentials"}, status=401)
            except Driver.DoesNotExist:
                return Response({"error": "Driver not found"}, status=404)
        return Response(serializer.errors, status=400)
    
# partners set pin update pin
class SetPinView(APIView):
    permission_classes = [IsPartner]

    def post(self, request):
        user = request.user
        if user.user_type != 'partner':
            return Response({'detail': 'Only partners can set a PIN.'}, status=status.HTTP_403_FORBIDDEN)

        pin_set = bool(user.pin_hash and user.pin_hash.strip() != "")
        if pin_set:
             email = request.user.email
             otp = request.data.get('otp')
             new_pin = request.data.get('pin')
                 # Step 1: Send OTP
             if email and not otp:
                 raw_otp = generate_otp()
                 request.session['otp'] = raw_otp
                 request.session['email'] = email
                 request.session.modified = True
                 # Send OTP via email here in real use
                 send_email(user,"code","Your OTP Code", extra_context={
                        "code":raw_otp}) 
                 return Response({'detail': f'OTP sent to {email}', 'otp': raw_otp})
                 # Step 2: Verify OTP
             if not otp:
                 return Response({'detail': 'OTP is required.'}, status=status.HTTP_400_BAD_REQUEST)
             if otp != request.session.get('otp'):
                 return Response({'detail': 'Invalid OTP.'}, status=status.HTTP_403_FORBIDDEN)
             if not new_pin:
                 return Response({"detail": 'Enter a new pin'}, status=status.HTTP_400_BAD_REQUEST)
                 # Step 3: Reset PIN
             user = request.user
             user.pin_hash = set_user_pin(new_pin)
             user.save()
                 # Step 4: Clear session
             request.session.pop('otp', None)
             request.session.pop('email', None)
             return Response({'detail': 'Your withdrawal PIN has been successfully reset.'}, status=status.HTTP_200_OK)
     
        pin = request.data.get('transaction_pin')
        if not pin or len(pin) < 4 or not pin.isdigit():
           return Response({'detail': 'PIN must be at least 4 digits.'}, status=status.HTTP_400_BAD_REQUEST)

        encrypted_pin = set_user_pin(pin)
        user.pin_hash = encrypted_pin
        user.save()
    
        return Response({'detail': 'PIN set successfully.'})

class RetrieveWithdrawalPinView(APIView):
    permission_classes = [IsPartner]

    def post(self, request):
            user = request.user
            password = request.data.get('password')

            if not password:
                return Response({'detail': 'Password is required!'})

            # Validate password
            if not user.check_password(password):
                return Response({'detail': 'Invalid password.'}, status=status.HTTP_403_FORBIDDEN)
            hashed_pin= user.pin_hash
            if not hashed_pin:
                return Response({'detail':"You have no pin set"})
            pin = retrieve_user_pin(hashed_pin)

            # Return the withdrawal PIN
            return Response({'Transaction pin': pin})
        
# partner details
class PartnerDetailsView(APIView):
    permission_classes = [IsPartner]

    def get(self, request):
        user = request.user
        today = now().date()

        has_pin = bool(user.pin_hash and user.pin_hash.strip())
        wallet, _ = Wallet.objects.get_or_create(user=user)
        investments = PartnerInvestment.objects.filter(partner=user).prefetch_related('product', 'roi_payouts')
        roi_queryset = ROIPayout.objects.filter(investment__partner=user)

        # Aggregated ROI values
        total_roi = roi_queryset.aggregate(total=Sum('amount'))['total'] or 0
        daily_roi = roi_queryset.filter(payout_date=today).aggregate(total=Sum('amount'))['total'] or 0
        total_roi_paid = roi_queryset.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or 0
        total_roi_expected = roi_queryset.filter(payout_date__lte=today).aggregate(total=Sum('amount'))['total'] or 0
        total_roi_scheduled = roi_queryset.aggregate(total=Sum('amount'))['total'] or 0
        total_invested = investments.aggregate(total=Sum('amount_invested'))['total'] or 0

        # ROI chart data
        roi_chart = (
            roi_queryset
            .annotate(date=TruncDate('payout_date'))
            .values('date')
            .annotate(total=Sum('amount'))
            .order_by('date')
        )

        # Investment breakdown 
        investment_summary = []
        for inv in investments:
            roi_paid = Decimal(
    ROIPayout.objects.filter(investment=inv, is_paid=True).aggregate(total=Sum('amount'))['total'] or 0
)

            roi_expected = Decimal(
    ROIPayout.objects
    .annotate(payout_day=TruncDate('payout_date'))
    .filter(investment=inv, payout_day__lte=today)
    .aggregate(total=Sum('amount'))['total'] or 0
)

            future_roi = Decimal(
    ROIPayout.objects.filter(investment=inv, payout_date__gt=today).aggregate(total=Sum('amount'))['total'] or 0
)

            roi_schedule = ROIPayout.objects.filter(investment=inv).order_by('payout_date').values('payout_date', 'amount')

            roi_pending = max(round(roi_expected - roi_paid, 2), 0)
            roi_progress = float((roi_paid / roi_expected) * 100) if roi_expected else 0


            investment_summary.append({
                "order_id": inv.order_id,
                "amount_invested": inv.amount_invested,
                "roi_rate": inv.roi_rate,
                "status": inv.status,
                "created_at": inv.created_at,
                "roi_expected": round(roi_expected, 2),
                "roi_paid": round(roi_paid, 2),
                "roi_pending": roi_pending,
                "roi_progress": round(roi_progress, 2),
                "future_roi": round(future_roi, 2),
                "is_matured": future_roi == 0,
                "payout_schedule": roi_schedule,
                "product": PartnerInvestmentSerializer(inv).data.get("product")
            })

        profile_image_url = request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None
        serializer = PartnerProfileSerializer(user)

        return Response({
            "has_pin": has_pin,
            "profile_picture": profile_image_url,
            "personal_details": serializer.data,
            "wallet_balance": wallet.balance,
            "total_invested": total_invested,
            "total_roi": round(total_roi, 2),
            "daily_roi": round(daily_roi, 2),
            "total_roi_expected": round(total_roi_expected, 2),
            "total_roi_paid": round(total_roi_paid, 2),
            "roi_pending": round(Decimal(total_roi_expected) - Decimal(total_roi_paid), 2),
            "total_roi_scheduled": round(total_roi_scheduled, 2),
            "roi_over_time": roi_chart,
            "investment_summary": investment_summary
        }, status=status.HTTP_200_OK)
# class ResetPinWithOTPView(APIView):
#     permission_classes = [IsPartner]
#     def post(self, request):
#            email = request.data.get('email')
#            otp = request.data.get('otp')
#            new_pin = request.data.get('pin')
#                # Step 1: Send OTP
#            if email and not otp:
#                raw_otp = generate_otp()
#                request.session['otp'] = raw_otp
#                request.session['email'] = email
#                request.session.modified = True
#                # Send OTP via email here in real use
#                return Response({'detail': f'OTP sent to {email}', 'otp': raw_otp})
#                # Step 2: Verify OTP
#            if not otp:
#                return Response({'detail': 'OTP is required.'}, status=status.HTTP_400_BAD_REQUEST)
#            if otp != request.session.get('otp'):
#                return Response({'detail': 'Invalid OTP.'}, status=status.HTTP_403_FORBIDDEN)
#            if not new_pin:
#                return Response({"detail": 'Enter a new pin'}, status=status.HTTP_400_BAD_REQUEST)
#                # Step 3: Reset PIN
#            user = request.user
#            user.pin_hash = set_user_pin(new_pin)
#            user.save()
#                # Step 4: Clear session
#            request.session.pop('otp', None)
#            request.session.pop('email', None)
#            return Response({'detail': 'Your withdrawal PIN has been successfully reset.'}, status=status.HTTP_200_OK)

class CreateDeliveryConfirmationView(APIView):
    def post(self, request):
        serializer = OrderDeliveryConfirmationSerializer(data=request.data)
        email = request.data.get("email")
        if serializer.is_valid():
            serializer.save()
            otp = generate_otp()
            send_email(email,"code","Your OTP Code", extra_context={
                        "code":otp}) 
            return Response({'detail': 'OTP sent to vendor email.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ConfirmDeliveryOTPView(APIView):
    def post(self, request):
        order_id = request.data.get('order_id')
        otp = request.data.get('otp')

        try:
            confirmation = OrderDeliveryConfirmation.objects.get(order_id=order_id)
        except OrderDeliveryConfirmation.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if confirmation.is_confirmed:
            return Response({'detail': 'Order already confirmed.'}, status=status.HTTP_400_BAD_REQUEST)

        if confirmation.otp != otp:
            return Response({'detail': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        confirmation.is_confirmed = True
        confirmation.confirmed_at = timezone.now()
        confirmation.save()
        return Response({'detail': 'Order delivery confirmed.'}, status=status.HTTP_200_OK)


class UpdateProfileView(APIView):
    permission_classes = [IsPartner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # for handling file uploads

    def patch(self, request):
        user = request.user

        # Update basic fields
        username = request.data.get('username')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        # email = request.data.get('email')
        profile_picture = request.data.get('profile_picture')  # optional

        # Update fields only if they are present
        if username:
            user.username = username
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        # if email and email != user.email:
            # Check if email is already used in either email or unverified_email
            # if Users.objects.filter(
                # Q(email=email) | Q(unverified_email=email)
            # ).exclude(id=user.id).exists():
                # return Response({'detail': 'Email is already in use.'}, status=status.HTTP_400_BAD_REQUEST)

            # Proceed with sending OTP
            # user.unverified_email = email
            # user.is_email_verified = False
            # otp = generate_otp()
            # EmailOTP.objects.create(user=user, otp=otp)
            # send_email(
                # user,
                # subject="Verify Your New Email",
                # message="Use the code below to verify your new email address.",
                # code=otp
            # )
            # user.save()
            # return Response({'detail': 'OTP sent to new email.'}, status=status.HTTP_200_OK)
        if profile_picture:
          if profile_picture.content_type not in ['image/jpeg', 'image/png']:
              return Response({'detail': 'Only JPEG or PNG images are allowed.'}, status=400)
          if profile_picture.size > 2 * 1024 * 1024:
              return Response({'detail': 'Max file size is 2MB.'}, status=400)
          # Delete old image
          if user.profile_picture and hasattr(user.profile_picture, 'path'):
              if os.path.isfile(user.profile_picture.path):
                  user.profile_picture.delete(save=False)
          user.profile_picture = profile_picture
        # if profile_picture and user.profile_picture:
        #     if os.path.isfile(user.profile_picture.path):
        #         user.profile_picture.delete(save=False)
        # if profile_picture:
        #     if profile_picture.content_type not in ['image/jpeg', 'image/png']:
        #         return Response({'detail': 'Only JPEG or PNG images are allowed.'}, status=400)
        #     if profile_picture.size > 2 * 1024 * 1024:
        #         return Response({'detail': 'Max file size is 2MB.'}, status=400)
        #     user.profile_picture = profile_picture  # assuming user model has this field

        user.save()

        # profile_image_url = request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None

        return Response({'detail': 'Profile updated successfully.'}, status=status.HTTP_200_OK)

# GET /vendor-investments/?status=approved
# Authorization: Bearer <token>
# class PartnerInvestmentsView(APIView):
#     permission_classes = [IsPartner]

#     def get(self, request):
#         user = request.user

#         if user.user_type != 'partner':
#             return Response({'detail': 'Only partners can view this resource.'}, status=status.HTTP_403_FORBIDDEN)

#         # Optional filter: status
#         investment_status = request.query_params.get('status', None)

#         investments = PartnerInvestment.objects.filter(partner=user)
#         if investment_status:
#             investments = investments.filter(status=investment_status)

#         # Use set to remove duplicates
#         product = {investment.product for investment in investments}

#         # Paginate shops
#         paginator = PageNumberPagination()
#         paginator.page_size = 10
#         result_page = paginator.paginate_queryset(list(product), request)

#         serializer = InvestmentGetSerializer(result_page, many=True)
#         return paginator.get_paginated_response(serializer.data)
    
class PartnerInvestmentOverview(APIView):
    permission_classes = [IsPartner]
    def get(self, request):
        if request.user.user_type != 'partner':
            return Response({'detail': 'Only partners can access this.'}, status=403)
        
        investments = PartnerInvestment.objects.filter(partner=request.user)
        serializer = PartnerInvestmentSerializer(investments, many=True)
        return Response(serializer.data)
 

class ShopInvestmentPagination(PageNumberPagination):
    page_size = 5

# class PartnerFullInvestmentOverviewView(APIView):
#     permission_classes = [IsPartner]

#     def get(self, request):
#         user = request.user
#         if user.user_type != 'partner':
#             return Response({'detail': 'Only partners can view this data.'}, status=403)

#         status_filter = request.query_params.get('status')
#         product_name_filter = request.query_params.get('product_name')

#         investments = PartnerInvestment.objects.filter(partner=user).select_related('product')
#         if not investments:
#             return Response({"detail":"No Investment at the moment!"})

#         if status_filter:
#             investments = investments.filter(status=status_filter)
#         if product_name_filter:
#             investments = investments.filter(product__name__icontains=product_name_filter)

#         wallet_balance = float(getattr(user.wallet, 'balance', 0.0))

#         global_summary = {
#             'wallet_balance': round(wallet_balance, 2),
#             'total_invested': 0.0,
#             'total_roi_earned': 0.0,
#             'total_daily_roi': 0.0,
#             'expected_total_roi': 0.0,
#             'investment_count': investments.count(),
#             'total_purchase': investments.count(),
#             'status_breakdown': {
#                 'pending': 0.0,
#                 'approved': 0.0,
#                 'in_transit': 0.0,
#                 'pending_settlement': 0.0,
#                 'settled': 0.0,
#                 'delivered': 0.0,
#             }
#         }

#         products = []

#         for investment in investments:
#             amount = float(investment.amount_invested)
#             roi_paid = float(investment.roi_paid)
#             total_expected_roi = float(investment.calculate_roi())
#             expected_roi_remaining = total_expected_roi - roi_paid

#             product = investment.product
#             duration = product.duration_days if product.duration_days else 1
#             daily_roi = total_expected_roi / duration

#             global_summary['total_invested'] += amount
#             global_summary['total_roi_earned'] += roi_paid
#             global_summary['total_daily_roi'] += daily_roi
#             global_summary['expected_total_roi'] += expected_roi_remaining

#             if investment.status in global_summary['status_breakdown']:
#                 global_summary['status_breakdown'][investment.status] += amount

#             products.append({
#                 'investment_id': investment.order_id,
#                 'product_id': product.id,
#                 'product_name': product.name,
#                 'amount_invested': round(amount, 2),
#                 'roi_earned': round(roi_paid, 2),
#                 'expected_roi': round(expected_roi_remaining, 2),
#                 'daily_roi': round(daily_roi, 2),
#                 'roi_percentage_earned': round((roi_paid / amount * 100), 2) if amount else 0.0,
#                 'status': investment.status
#             })

#         global_summary['total_invested'] = round(global_summary['total_invested'], 2)
#         global_summary['total_roi_earned'] = round(global_summary['total_roi_earned'], 2)
#         global_summary['total_daily_roi'] = round(global_summary['total_daily_roi'], 2)
#         global_summary['expected_total_roi'] = round(global_summary['expected_total_roi'], 2)
#         global_summary['status_breakdown'] = {k: round(v, 2) for k, v in global_summary['status_breakdown'].items()}

#         paginator = ShopInvestmentPagination()  # Optionally rename this to ProductInvestmentPagination
#         paginated_products = paginator.paginate_queryset(products, request)

#         return paginator.get_paginated_response({
#             'global_summary': global_summary,
#             'products': paginated_products
#         })

class TransactionPagination(PageNumberPagination):
    page_size = 10

class UserTransactionHistoryView(APIView):
    permission_classes = [IsPartner]

    def get(self, request):
        user = request.user
        
        # Filters
        transaction_type = request.query_params.get('transaction_type')
        status = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        # Base queryset
        transactions = Transaction.objects.filter(user=user).order_by('-created_at')

        # Apply filters
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)

        if status:
            transactions = transactions.filter(status=status)

        if date_from:
            transactions = transactions.filter(created_at__date__gte=date_from)

        if date_to:
            transactions = transactions.filter(created_at__date__lte=date_to)

        # PAGINATION
        paginator = TransactionPagination()
        paginated_transactions = paginator.paginate_queryset(transactions, request)

        serializer = TransactionSerializer(paginated_transactions, many=True)

        # SUMMARY PART
        total_funds = Transaction.objects.filter(user=user, transaction_type='fund', status='completed').aggregate(total=Sum('amount'))['total'] or 0
        total_withdrawals = Transaction.objects.filter(user=user, transaction_type='withdraw', status='completed').aggregate(total=Sum('amount'))['total'] or 0
        total_investments = Transaction.objects.filter(user=user, transaction_type='investment', status='completed').aggregate(total=Sum('amount'))['total'] or 0
        total_roi_earned = Transaction.objects.filter(user=user, transaction_type='roi', status='completed').aggregate(total=Sum('amount'))['total'] or 0

        
        # wallet = getattr(user, 'wallet', None)
        # available_balance = wallet.balance if wallet else 0

        summary = {
            # 'total_funds': total_funds,
            # 'total_withdrawals': total_withdrawals,
            # 'total_investments': total_investments,
            # 'total_roi_earned': total_roi_earned,
            # 'available_balance':available_balance
        }

        return paginator.get_paginated_response({
            'summary': summary,
            'transactions': serializer.data
        })
    

class AllTransactionsPagination(PageNumberPagination):
    page_size = 20

class AllTransactionsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        user = request.user

        transactions = Transaction.objects.all() if user.is_superuser else Transaction.objects.filter(user=user)

        # Admin-only filters
        if user.is_superuser:
            user_id = request.query_params.get('user_id')
            transaction_type = request.query_params.get('transaction_type')
            status_filter = request.query_params.get('status')
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            search = request.query_params.get('search')
            sort_by = request.query_params.get('sort_by')  # <-- NEW

            if user_id:
                transactions = transactions.filter(user__id=user_id)
            if transaction_type:
                transactions = transactions.filter(transaction_type=transaction_type)
            if status_filter:
                transactions = transactions.filter(status=status_filter)
            if from_date:
                try:
                    from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
                    transactions = transactions.filter(created_at__date__gte=from_date_obj)
                except ValueError:
                    return Response({"detail": "Invalid from_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
            if to_date:
                try:
                    to_date_obj = datetime.strptime(to_date, "%Y-%m-%d")
                    transactions = transactions.filter(created_at__date__lte=to_date_obj)
                except ValueError:
                    return Response({"detail": "Invalid to_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
            if search:
                transactions = transactions.filter(
                    Q(order_id__icontains=search) |
                    Q(amount__icontains=search)
                )

            # Handle Sorting
            if sort_by == 'newest':
                transactions = transactions.order_by('-created_at')
            elif sort_by == 'oldest':
                transactions = transactions.order_by('created_at')
            elif sort_by == 'amount_high':
                transactions = transactions.order_by('-amount')
            elif sort_by == 'amount_low':
                transactions = transactions.order_by('amount')
            else:
                transactions = transactions.order_by('-created_at')  # Default

        else:
            transactions = transactions.order_by('-created_at')  # Normal users, default newest first

        # Pagination
        paginator = AllTransactionsPagination()
        paginated_transactions = paginator.paginate_queryset(transactions, request)

        serializer = TransactionSerializer(paginated_transactions, many=True)

        return paginator.get_paginated_response(serializer.data)

class NotificationListView(APIView):
    permission_classes = [IsPartner]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

class NotificationMarkAsReadView(APIView):
    permission_classes = [IsPartner, IsAdmin]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            notification.is_read = True
            notification.save()
            return Response({"detail": "Notification marked as read."})
        except Notification.DoesNotExist:
            return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
        
class ApproveWithdrawalView(APIView):
    permission_classes = [IsAdmin]  # or a custom IsStaff permission

    def post(self, request, transaction_id):
        action = request.data.get('action')  # 'approve' or 'reject'
        note = request.data.get('note')

        try:
            tx = Transaction.objects.get(reference=transaction_id, transaction_type='withdraw', status='pending')
        except Transaction.DoesNotExist:
            return Response({'detail': 'Withdrawal not found or already processed.'}, status=404)

        if action == 'approve':
            tx.status = 'approved'
            tx.save()
            # Trigger payment webhook or internal payout function here
            # e.g. send_to_payment_provider(tx)
            Notification.objects.create(
                user=tx.user,
                title="Withdrawal Approved",
                message=f"Your withdrawal of {tx.amount} was approved.",
                event_type="withdraw",
            )

        elif action == 'reject':
            tx.status = 'rejected'
            tx.admin_note = note
            tx.save()

            # Refund the wallet
            tx.user.wallet.balance += tx.amount
            tx.user.wallet.save()

            Notification.objects.create(
                user=tx.user,
                title="Withdrawal Rejected",
                message=f"Your withdrawal of {tx.amount} was rejected. Reason: {note}",
                event_type="withdraw",
            )
        else:
            return Response({'detail': 'Invalid action.'}, status=400)

        return Response({'detail': f'Withdrawal {action}ed successfully.'})


class AdminComprehensiveReportView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        partners = Users.objects.filter(user_type="partner")
        total_partners = partners.count()
        total_investment = PartnerInvestment.objects.aggregate(total=models.Sum('amount_invested'))['total'] or 0

        partner_data = PartnerAdminReportSerializer(partners, many=True).data
        # all_orders = PartnerInvestment.objects.all()
        # orders_data = AdminOrderSerializer(all_orders, many=True).data

        pending_qs = Transaction.objects.filter(transaction_type='withdraw', status='pending')
        approved_qs = Transaction.objects.filter(transaction_type='withdraw', status='approved')

        total_pending_amount = pending_qs.aggregate(total=Sum('amount'))['total'] or 0
        total_pending_count = pending_qs.count()

        total_approved_amount = approved_qs.aggregate(total=Sum('amount'))['total'] or 0
        total_approved_count = approved_qs.count()



        # print(all_orders)
        return Response({
            'total_partners': total_partners,
            "partners": partner_data,
            'total_investment': total_investment, 
            'pending_withdrawals': total_pending_count,
                # 'approved': {
                #     'count': total_approved_count,
                #     'total_amount': total_approved_amount
                # }
        })
    
class AdminVendorDashboardView(APIView):
    def get(self, request):
        vendors = Vendor.objects.all()
        total_vendors = vendors.count()

        total_remittance = Remittance.objects.aggregate(
            total=Sum('amount')
        )['total'] or 0

        today_remittance = Remittance.objects.filter(
            created_at__date=date.today()
        ).aggregate(total=Sum('amount'))['total'] or 0

        serialized_vendors = VendorOverviewSerializer(vendors, many=True).data

        return Response({
            'total_vendors': total_vendors,
            'total_remittance': total_remittance,
            'today_remittance': today_remittance,
            'vendors': serialized_vendors
        })
    
# class VendorListWithOrdersView(APIView):
#     permission_classes = [IsAdmin]

#     def get(self, request):
#         vendors = Vendor.objects.all().prefetch_related(
#             'orders__items',  # Prefetch orders and order items
#             'orders__items__product',
#         )
#         serializer = VendorDetailSerializer(vendors, many=True)
#         return Response(serializer.data)
# class RecentInvestmentsView(APIView):
#     permission_classes = [IsAdmin]

#     def get(self, request):
#         recent_investments = PartnerInvestment.objects.select_related('partner').prefetch_related('product').order_by('-created_at')[:20]
#         serializer = PartnerInvestmentListSerializer(recent_investments, many=True)
#         return Response(serializer.data)

class VendorDetailWithOrdersView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, vendor_id):
        today = now().date()
        search_query = request.query_params.get('search', '').strip()
        try:
            vendor = Vendor.objects.prefetch_related(
                # 'orders__items',
                # 'orders__items__product',
                #  'product_set__orderitem_set__order'
            ).get(vendor_id=vendor_id)
        except Vendor.DoesNotExist:
            return Response({"error": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get limit from query params, default to 10
        limit = request.query_params.get('limit', 10)
        try:
            limit = int(limit)
        except ValueError:
            return Response({"error": "limit must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
        
# Get all order references for the vendor
        vendor_order_refs = Order.objects.filter(vendor=vendor).values_list('reference', flat=True)

# Filter transactions with those order_ids and remittance type
        # todays_remittance = Transaction.objects.filter(
        #     order_id__in=vendor_order_refs,
        #     transaction_type='remittance',
        #     created_at__date=today
        # ).aggregate(total=Sum('amount'))['total'] or 0

        # total_remittance = Transaction.objects.filter(
        #     order_id__in=vendor_order_refs,
        #     transaction_type='remittance',
        # ).aggregate(total=Sum('amount'))['total'] or 0

        # total_remittance = Remittance.objects.aggregate(
        #     total=Sum('amount')
        # )['total'] or 0

        # todays_remittance = Remittance.objects.filter(
        #     created_at__date=date.today()
        # ).aggregate(total=Sum('amount'))['total'] or 0

        todays_remittance = Remittance.objects.filter(
    created_at__date=date.today()
).values(
    'vendor__id', 'vendor__email', 'vendor__first_name', 'vendor__last_name'
).annotate(
    total_remittance=Sum('amount')
).order_by('-total_remittance')
        
                
        total_remittance = Remittance.objects.values(
            'vendor__id', 'vendor__email', 'vendor__first_name', 'vendor__last_name'
        ).annotate(
            total_remittance=Sum('amount')
        ).order_by('-total_remittance')

        # Transactions list (filtered by "remittance" type)
        transactions_qs = Transaction.objects.filter(
            order_id__in=vendor_order_refs,
            transaction_type='remittance'
        )

        # Apply search filter
        if search_query:
            transactions_qs = transactions_qs.filter(
                Q(order_id__icontains=search_query) |
                Q(reference__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        # Paginate or limit results
        transactions_qs = transactions_qs.order_by('-created_at')[:limit]

        transactions_data = [
            {
                "transaction_id": tx.id,
                "order_id": tx.order_id,
                "amount": tx.amount,
                "status": tx.status,
                "reference": tx.reference,
                "description": tx.description,
                "created_at": tx.created_at,
                "payment_method": tx.payment_method,
                "bank_name": tx.bank_name,
                "account_number": tx.account_number,
                "account_name": tx.account_name,
            }
            for tx in transactions_qs
        ]

        # Pass the limit to serializer context
        serializer = VendorDetailSerializer(vendor, context={'order_limit': limit})
        return Response({
            "today_remittance":todays_remittance,
            "total_remittance":total_remittance,
           "vendor_details": serializer.data,
            "transactions": transactions_data
        })
    

class PartnerDetailWithInvestmentsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, partner_id):
        try:
            partner = Users.objects.prefetch_related(
                'investments__vendor',
                'investments__product',
                'transactions'
            ).get(id=partner_id, user_type='partner')
        except Users.DoesNotExist:
            return Response({"error": "Partner not found"}, status=status.HTTP_404_NOT_FOUND)

        limit = request.query_params.get('limit', 10)
        try:
            limit = int(limit)
        except ValueError:
            return Response({"error": "limit must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        investments = partner.investments.all()
        total_orders = investments.count()
        total_invested = investments.aggregate(total=Sum('amount_invested'))['total'] or 0
        balance = getattr(partner.wallet, 'balance', 0)

        # orders_serializer = InvestmentSerializer(investments.order_by('-created_at')[:limit], many=True)
        transactions_serializer = TransactionSerializer(partner.transactions.all().order_by('-created_at'), many=True)

        profile_picture_url = partner.profile_picture.url if partner.profile_picture else None

        orders_list = []
        for inv in investments.order_by('-created_at')[:limit]:
            orders_list.append({
                "order_id": inv.order_id,
                "created_at": inv.created_at,
                "vendor_name": inv.vendor.name if inv.vendor else None,
                "partner_name":partner.get_full_name(),
                "amount": inv.amount_invested,
                "status": inv.status,
                "products": [p.name for p in inv.product.all()]
            })

        return Response({
            "partner": {
                "id": partner.id,
                "name": partner.get_full_name(),
                "email": partner.email,
                "phone": getattr(partner, "phone", None),
                "address": partner.address,
                "balance": balance,
                "profile_picture": profile_picture_url
            },
            "summary": {
                "total_orders": total_orders,
                "total_invested": total_invested,
                "balance": balance
            },
            "orders": orders_list,
            "transactions": transactions_serializer.data
        }, status=status.HTTP_200_OK)


# class PartnerDetailWithInvestmentsView(APIView):
#     permission_classes = [IsAdmin]

#     def get(self, request, partner_id):
#         try:
#             partner = Users.objects.prefetch_related(
#                 'investments__vendor',
#                 'investments__product',
#                 'transactions'
#             ).get(id=partner_id, user_type='partner')
#         except Users.DoesNotExist:
#             return Response({"error": "Partner not found"}, status=status.HTTP_404_NOT_FOUND)

#         # Limit for orders
#         limit = request.query_params.get('limit', 10)
#         try:
#             limit = int(limit)
#         except ValueError:
#             return Response({"error": "limit must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

#         # Investments summary
#         investments = partner.investments.all()
#         total_orders = investments.count()
#         total_invested = investments.aggregate(total=Sum('amount_invested'))['total'] or 0

#         # Balance (assuming Users model has a balance field)
#         balance = getattr(partner.wallet, 'balance', 0)

#         # Orders list
#         orders_list = []
#         for inv in investments.order_by('-created_at')[:limit]:
#             orders_list.append({
#                 "order_id": inv.order_id,
#                 "date": inv.created_at,
#                 "vendor": inv.vendor.name if inv.vendor else None,
#                 "amount_invested": inv.amount_invested,
#                 "products": [p.name for p in inv.product.all()]
#             })

#         # Transactions list
#         transactions_list = []
#         for tx in partner.transactions.all().order_by('-created_at'):
#             transactions_list.append({
#                 "transaction_id": tx.id,
#                 "transaction_type": tx.transaction_type,
#                 "amount": tx.amount,
#                 "status": tx.status,
#                 "created_at": tx.created_at
#             })
            
#         if partner.profile_picture:
#             profile_picture_url = partner.profile_picture.url
#         else:
#             profile_picture_url = None



#         return Response({
#             "partner": {
#                 "id": partner.id,
#                 "name": partner.get_full_name(),
#                 "email": partner.email,
#                 "phone": partner.phone if hasattr(partner, "phone") else None,
#                 "address": partner.address,
#                 "balance": balance,
#                 "profile_picture":profile_picture_url
#             },
#             "summary": {
#                 "total_orders": total_orders,
#                 "total_invested": total_invested,
#                 "balance": balance
#             },
#             "orders": orders_list,
#             "transactions": transactions_list
#         }, status=status.HTTP_200_OK)
#     psycopg.errors.UndefinedColumn: column shop_vendor.user_id does not exist

# LINE 1: ...tnerinvestment"."updated_at", "shop_vendor"."id", "shop_vend...
class AdminDashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        today = now().date()

        # Get limit from query params, default to 10
        try:
            limit = int(request.query_params.get('limit', 10))
        except ValueError:
            return Response({"error": "limit must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        # Pending withdrawals
        
        pending_qs = Transaction.objects.filter(transaction_type='withdraw', status='pending')
        approved_qs = Transaction.objects.filter(transaction_type='withdraw', status='approved')

        total_pending_amount = pending_qs.aggregate(total=Sum('amount'))['total'] or 0
        total_pending_count = pending_qs.count()

        total_approved_amount = approved_qs.aggregate(total=Sum('amount'))['total'] or 0
        total_approved_count = approved_qs.count()

        # pending_withdrawals_qs = Withdrawal.objects.filter(status='pending')
        # pending_withdrawals_count = pending_withdrawals_qs.count()
        # pending_withdrawals_total = pending_withdrawals_qs.aggregate(
        #     total=Sum('amount')
        # )['total'] or 0

        # Today's remittance (approved withdrawals today)
        # todays_remittance_total = Withdrawal.objects.filter(
        #     status='approved',
        #     created_at__date=today
        # ).aggregate(total=Sum('amount'))['total'] or 0

        # Total balance (total investments - total withdrawals)
        total_investments = PartnerInvestment.objects.aggregate(
            total=Sum('amount_invested')
        )['total'] or 0
        # total_withdrawals = Withdrawal.objects.aggregate(
        #     total=Sum('amount')
        # )['total'] or 0
        total_balance = total_investments - total_approved_amount

        # Recent orders
        recent_orders_qs = PartnerInvestment.objects.select_related(
            'partner', 'vendor'
        ).prefetch_related('product').order_by('-created_at')[:limit]

        recent_orders = [
            {
                "created_at":order.created_at,
                "order_id": order.order_id,
                "partner_name": getattr(order.partner, "get_full_name", lambda: str(order.partner))(),
                "vendor_name": order.vendor.name if order.vendor else None,
                "amount": order.amount_invested,
                "status": order.status,
                "products": [p.name for p in order.product.all()]
            }
            for order in recent_orders_qs
        ]

        
        # Per-user summaries
        user_summaries = []
        users = Users.objects.all()

        for user in users:
            user_pending = Transaction.objects.filter(
                user=user, transaction_type='withdraw', status='pending'
            )
            user_approved = Transaction.objects.filter(
                user=user, transaction_type='withdraw', status='approved'
            )

            pending_amount = user_pending.aggregate(total=Sum('amount'))['total'] or 0
            approved_amount = user_approved.aggregate(total=Sum('amount'))['total'] or 0

            pending_count = user_pending.count()
            approved_count = user_approved.count()

            # if pending_amount > 0 or approved_amount > 0:
            #     user_summaries.append({
            #         "user_id": user.id,
            #         "user_name": user.get_full_name() if hasattr(user, 'get_full_name') else str(user),
            #         "pending_withdrawals_amount": pending_amount,
            #         "pending_withdrawals_count": pending_count,
            #         "approved_withdrawals_amount": approved_amount,
            #         "approved_withdrawals_count": approved_count,
            #     })

        # withdrawals_data = []
        # for tx in pending_qs:
        #     partner = tx.user
        #     partner_name = partner.get_full_name() if hasattr(partner, 'get_full_name') else f"{partner.first_name} {partner.last_name}"
        #     balance = getattr(partner.wallet, 'balance', 0)
        #     if user.profile_picture:
        #         profile_picture_url = user.profile_picture.url
        #     else:
        #         profile_picture_url = None


        #     user_summaries.append({
        #         "partner_name": partner_name,
        #         "profile_pic": profile_picture_url,
        #         "amount": tx.amount,
        #         "balance": balance,
        #         "from_user": tx.from_user,
        #         "to": tx.to,  # Or dynamically from transaction if available
        #         "requested_at": tx.created_at,
        #         "withdraw_id": tx.reference
        #     })
        user_summaries = []
        partner_balances = {}  # To avoid counting a partner's balance multiple times

        for tx in pending_qs:
            partner = tx.user
            partner_name = partner.get_full_name() if hasattr(partner, 'get_full_name') else f"{partner.first_name} {partner.last_name}"
            balance = getattr(partner.wallet, 'balance', 0)

            # Use tx.user.id (or pk) to avoid duplicate balances for same partner
            if partner.id not in partner_balances:
                partner_balances[partner.id] = balance

            profile_picture_url = partner.profile_picture.url if getattr(partner, 'profile_picture', None) else None

            user_summaries.append({
                "partner_name": partner_name,
                "profile_pic": profile_picture_url,
                "amount": tx.amount,
                "balance": balance,
                "from_user": tx.from_user,
                "to": tx.to,
                "requested_at": tx.created_at,
                "withdraw_id": tx.reference
            })

        # Total accumulative balance for all unique partners
        # total_accumulative_balance = sum(partner_balances.values())
        total_accumulative_balance = Users.objects.aggregate(
    total_balance=Sum('wallet__balance')
)['total_balance'] or 0

            # return Response({
            # "global_summary": {
            #     "total_pending_withdrawals_amount": total_pending_amount,
            #     "total_pending_withdrawals_count": total_pending_count,
            #     "total_approved_withdrawals_amount": total_approved_amount,
            #     "total_approved_withdrawals_count": total_approved_count,
            # },
#     "user_summaries": user_summaries
# }, status=status.HTTP_200_OK)

        return Response({
            "pending_withdrawals": total_pending_count,
            "todays_remittance": 0,
            "total_balance": total_accumulative_balance,
            "recent_orders": recent_orders,
            "withdrawal_request": user_summaries
        }, status=status.HTTP_200_OK)

class AdminROICycleBreakdownView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        today_date = now().date()

        # Today's ROI payouts
        todays_remittance = ROIPayout.objects.filter(
            paid_at__date=today_date,
            is_paid=True
        ).aggregate(total=Sum("amount"))["total"] or 0

        # Total ROI payouts
        total_remittance = ROIPayout.objects.filter(
            is_paid=True
        ).aggregate(total=Sum("amount"))["total"] or 0

        # Prefetch related objects (ManyToMany needs prefetch_related)
        investments = PartnerInvestment.objects.select_related(
            "partner", "vendor"
        ).prefetch_related("product", "roi_payouts")

        # Pending remittance stats
        pending_remittance_qs = investments.filter(status="pending")
        pending_remittance_amount = pending_remittance_qs.aggregate(total=Sum("roi_payouts__amount"))["total"] or 0
        pending_remittance_count = pending_remittance_qs.count()

        orders_data = []
        for inv in investments:
            roi_cycles = [
                {
                    "cycle": payout.cycle_number,
                    "payout_date": payout.payout_date,
                    "amount": payout.amount,
                    "status": "paid" if payout.is_paid else "pending"
                }
                for payout in inv.roi_payouts.all().order_by("cycle_number")
            ]

            orders_data.append({
                "order_id": inv.order_id,
                "partner_name": inv.partner.get_full_name() if inv.partner else None,
                "vendor_name": inv.vendor.name if inv.vendor else None,
                "products": [p.name for p in inv.product.all()],
                "amount_invested": inv.amount_invested,
                "total_roi": inv.total_roi(),
                "roi_cycles": roi_cycles,
                "status": inv.status
            })

        return Response({
            "todays_remittance": todays_remittance,
            "total_remittance": total_remittance,
            "pending_remittance": {
                "amount": pending_remittance_amount,
                "count": pending_remittance_count
            },
            "orders": orders_data
        }, status=status.HTTP_200_OK)

class AdminSingleROICycleBreakdownView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, order_id):
        try:
            inv = PartnerInvestment.objects.select_related(
                "partner", "vendor"
            ).prefetch_related(
                "product", "roi_payouts"
            ).get(order_id=order_id)
        except PartnerInvestment.DoesNotExist:
            return Response({"error": "Investment not found"}, status=status.HTTP_404_NOT_FOUND)

        # ROI cycles for this specific investment
        roi_cycles = [
            {
                "cycle": payout.cycle_number,
                "payout_date": payout.payout_date,
                "amount": payout.amount,
                "status": "paid" if payout.is_paid else "pending"
            }
            for payout in inv.roi_payouts.all().order_by("cycle_number")
        ]
        if inv.partner.profile_picture:
            profile_picture_url = inv.partner.profile_picture.url
        else:
            profile_picture_url = None

        
        if inv.vendor.profile_picture:
            vendor_profile_picture_url = inv.vendor.profile_picture.url
        else:
            vendor_profile_picture_url = None



        data = {
            "created_at": inv.created_at,
            "order_id": inv.order_id,
            "partner_name": inv.partner.get_full_name() if inv.partner else None,
            "partner_picture": profile_picture_url,
            "vendor_name": inv.vendor.name if inv.vendor else None,
            "vendor_address": inv.vendor.address if inv.vendor else None,
            "vendor_picture": vendor_profile_picture_url,
            "products": [p.name for p in inv.product.all()],
            "amount_invested": inv.amount_invested,
            "total_roi": inv.total_roi(),
            "roi_rate": inv.roi_rate,
            "roi_cycles": roi_cycles,
            "status": inv.status
        }

        return Response(data, status=status.HTTP_200_OK)

class PartnerListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        partners = Users.objects.all()
        serializer = PartnerListSerializer(partners, many=True, context={'request': request})
        return Response(serializer.data)
    

class AdminNotificationListView(APIView):
    permission_classes = [IsAdmin]  

    def get(self, request):
        notifications = Notification.objects.filter(event_type="admin").order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)


class UpdateStatusView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, *args, **kwargs):
        model_type = request.data.get("model_type")  # 'order' or 'investment'
        obj_id = request.data.get("order_id")
        new_status = request.data.get("status")

        if not model_type or not obj_id or not new_status:
            return Response(
                {"error": "model_type, order_id, and status are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if model_type == "order":
            try:
                obj = Order.objects.get(order_id=obj_id)
            except Order.DoesNotExist:
                return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        elif model_type == "investment":
            try:
                obj = PartnerInvestment.objects.get(order_id=obj_id)
            except PartnerInvestment.DoesNotExist:
                return Response({"error": "Investment not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "Invalid model_type"}, status=status.HTTP_400_BAD_REQUEST)

        obj.status = new_status
        obj.save()

        return Response(
            {"message": f"{model_type.capitalize()} status updated", "id": obj_id, "status": new_status},
            status=status.HTTP_200_OK
        )

class AdminOrderDeliveryListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        confirmations = OrderDeliveryConfirmation.objects.all().order_by("-created_at")
        serializer = OrderDeliveryConfirmationSerializer(confirmations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class AdminOrderDeliveryDetailView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, order_id):
        try:
            confirmation = OrderDeliveryConfirmation.objects.get(investment__order_id=order_id)
        except OrderDeliveryConfirmation.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderDeliveryConfirmationSerializer(confirmation)
        return Response(serializer.data, status=status.HTTP_200_OK)

