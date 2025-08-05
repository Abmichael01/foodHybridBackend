from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from shop.serializers import ProductSerializer
from .models import Users, Driver,OrderDeliveryConfirmation, Notification, EmailOTP, Vendor
from shop.models import PartnerInvestment, ROIPayout, OrderItem, Order
from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.db.models import Sum
from datetime import date


class PartnerSignUpSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=False,allow_blank=True)
    last_name = serializers.CharField(required=False,allow_blank=True) 

    class Meta:
        model = Users
        fields = ['email','first_name', 'last_name']
        extra_kwargs = {
            'email': {'validators': []}
        }

    def validate_email(self, value):
        existing_user = Users.objects.filter(email=value).first()
        if existing_user and existing_user.is_email_verified:
            raise serializers.ValidationError("A user with this email is already verified.")
        return value

    def create(self, validated_data):
        user = Users.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            user_type='partner',
            is_email_verified=False
        )
        print("saved")
        return user


# class OrderItemSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = OrderItem
#         fields = ['product_name', 'quantity', 'price']
# serializers.py

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['product_name', 'quantity', 'price']
        
class DeliveryConfirmationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDeliveryConfirmation
        fields = [
            'investment',
            'owner_name',
            'owner_email',
            'store_name',
            'store_email',
            'store_phone',
            'store_address'
        ]

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ['id', 'name', 'email', 'phone', 'profile_picture', 'created_at']

class AdminOrderSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    total_amount = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True)
    order_id = serializers.SerializerMethodField()
    product = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'created_at', 'partner_name', 'vendor_name', 'total_amount', 'items', 'order_id', 'product']

    def get_total_amount(self, obj):
        return sum(item.quantity * item.price for item in obj.items.all())
    
    def get_total_amount(self, obj):
       return sum(item.quantity * item.price for item in obj.items.all())

    def get_order_id(self, obj):
        # Use related_name if defined, else fallback to first related investment
        investment = getattr(obj, 'partnerinvestment', None)
        if investment:
            return investment.order_id
        return None

    def get_product(self, obj):
        investment = getattr(obj, 'partnerinvestment', None)
        if investment and investment.product:
            return investment.product.name  # or .title depending on your model
        return None

    def get_partner_name(self, obj):
         user = getattr(obj, 'partner', None)
         if not user:
             return None
 
         # Prefer company_name if available, fall back to full name
         return (
             getattr(user, 'name', None)
             or f"{user.first_name} {user.last_name}".strip()
             or user.username
         )
        # investment = getattr(obj, 'partnerinvestment', None)
        # if investment and investment.partner.name:
        #     return investment.partner  # or .title depending on your model
        # return None

class CompleteRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True, required=False)

    def validate(self, data):
        try:
            user = Users.objects.get(email=data['email'])
        except Users.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        if not user.is_email_verified:
            raise serializers.ValidationError({"error":"Email is not verified yet."})
        
        if user.username and user.has_usable_password():
            raise serializers.ValidationError({"detail": "Registration is already completed."})

        if 'username' in data:
            if Users.objects.filter(username=data['username']).exclude(pk=user.pk).exists():
                raise serializers.ValidationError("Username already taken.")
            
            
        try:
            validate_password(data['password'], user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        data['user'] = user
        return data

    def save(self):
        user = self.validated_data['user']
        updated_fields = []

        if 'username' in self.validated_data:
            user.username = self.validated_data['username']
            updated_fields.append('username')

        if 'password' in self.validated_data:
            user.set_password(self.validated_data['password'])
            updated_fields.append('password')

        user.save(update_fields=updated_fields)
        return user
    

class PartnerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id','user','title','from_user','to_user','message','event_type','is_read','created_at','available_balance_at_time', 'payment_method', 'bank_name', 'account_number','account_name']
        read_only_fields = ['id', 'created_at', 'user']
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.event_type not in ['fund', 'withdraw']:
            data.pop('from_user', None)
            data.pop('to_user', None)
        if instance.event_type in ['fund', 'withdraw']:
            data.pop('order_id', None)
        if instance.event_type not in ['fund', 'withdraw', 'roi', 'investment']:
            data.pop('available_balance_at_time', None)
        
        # Hide bank details if not a withdrawal
        if instance.event_type != 'withdraw':
            data.pop('bank_name', None)
            data.pop('account_number', None)
            data.pop('account_name', None)
        return data
class ResetPasswordOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(required=False,allow_blank=True)
    new_password = serializers.CharField(write_only=True, required=False,allow_blank=True)

    def validate(self, data):
        email = data.get('email')
        otp = data.get('otp')
        new_password = data.get('new_password')

        # Step 1: Email is always required
        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        data['user'] = user

        # Step 2: If OTP is provided, verify it
        if otp:
            try:
                otp_entry = EmailOTP.objects.filter(user=user, otp=otp).latest('created_at')
            except EmailOTP.DoesNotExist:
                raise serializers.ValidationError({"otp": "Invalid OTP."})

            if timezone.now() - otp_entry.created_at > timedelta(minutes=10):
                raise serializers.ValidationError({"otp": "OTP has expired."})

            data['otp_entry'] = otp_entry

        # Step 3: If new password is provided, ensure OTP is valid and password is strong
        if new_password:
            if not otp:
                raise serializers.ValidationError({"otp": "OTP is required to set a new password."})
            try:
                validate_password(new_password, user=user)
            except DjangoValidationError as e:
                raise serializers.ValidationError({"new_password": list(e.messages)})

        return data

    def save(self):
        user = self.validated_data['user']
        new_password = self.validated_data.get('new_password')
        otp_entry = self.validated_data.get('otp_entry')

        # If password is being reset
        if new_password:
            user.set_password(new_password)
            user.save()

            # Invalidate OTP after use
            if otp_entry:
                otp_entry.delete()

        return user
      
class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()
    password = serializers.CharField(write_only=True)

class DriverCreateSerializer(serializers.ModelSerializer):
    driver_id = serializers.CharField()

    class Meta:
        model = Driver
        fields = ['driver_id', 'phone_number']

    def create(self, validated_data):
        user = self.context['user']
        return Driver.objects.create(user=user, **validated_data)

class DriverLoginSerializer(serializers.Serializer):
    driver_id = serializers.CharField()
    password = serializers.CharField(write_only=True)
    

class RequestPasswordResetOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not Users.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value
    
    # def save(self):
    #     email = self.validated_data['email']
    #     user = Users.objects.get(email=email)

     
class OrderDeliveryConfirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDeliveryConfirmation
        fields = ['order_id', 'owner_name', 'owner_email', 'vendor_location']

class ROIPayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = ROIPayout
        fields = ['cycle_number', 'amount', 'payout_date', 'is_paid']

class PartnerInvestmentSerializer(serializers.ModelSerializer):
    product = ProductSerializer(many=True, read_only=True)
    # roi_payouts = ROIPayoutSerializer(many=True, read_only=True )

    class Meta:
        model = PartnerInvestment
        fields = [
            # 'id', 'order_id', 'amount_invested', 'roi_rate', 'roi_paid',
            # 'status',
              'product', 
            # , 'created_at', 'updated_at' 'roi_payouts'
        ]

class PartnerAdminReportSerializer(serializers.Serializer):
    name = serializers.SerializerMethodField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    address = serializers.CharField()
    username = serializers.CharField()
    total_purchase = serializers.SerializerMethodField()
    total_orders = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    portfolio_balance = serializers.SerializerMethodField()

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_total_purchase(self, obj):
        return PartnerInvestment.objects.filter(partner=obj).aggregate(total=models.Sum('amount'))['total'] or 0

    def get_total_orders(self, obj):
        return PartnerInvestment.objects.filter(partner=obj).count()

    def get_balance(self, obj):
        wallet = getattr(obj, 'wallet', None)
        return wallet.balance if wallet else 0

    def get_portfolio_balance(self, obj):
        wallet = getattr(obj, 'wallet', None)
        return wallet.portfolio_balance if wallet and hasattr(wallet, 'portfolio_balance') else 0


class AllOrdersSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.get_full_name')
    shop_name = serializers.CharField(source='shop.name')

    class Meta:
        model = PartnerInvestment
        fields = ['id', 'partner_name', 'shop_name', 'amount', 'status', 'created_at']

class VendorOverviewSerializer(serializers.ModelSerializer):
    total_remittance = serializers.SerializerMethodField()
    today_remittance = serializers.SerializerMethodField()
    total_orders = serializers.SerializerMethodField()
    orders = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = ['id', 'name', 'email', 'phone', 'address',
                  'total_remittance', 'today_remittance',
                  'total_orders', 'orders']

    def get_total_remittance(self, vendor):
        return PartnerInvestment.objects.filter(
            shop__vendor=vendor
        ).aggregate(total=Sum('amount'))['total'] or 0

    def get_today_remittance(self, vendor):
        return PartnerInvestment.objects.filter(
            shop__vendor=vendor,
            created_at__date=date.today()
        ).aggregate(total=Sum('amount'))['total'] or 0

    def get_total_orders(self, vendor):
        return PartnerInvestment.objects.filter(shop__vendor=vendor).count()

    def get_orders(self, vendor):
        return PartnerInvestment.objects.filter(
            shop__vendor=vendor
        ).values('id', 'amount', 'status', 'created_at', 'partner__email', 'shop__name')
# class NotificationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Notification
#         fields = ['id', 'title', 'message', 'event_type', 'is_read', 'created_at']

# class PartnerInvestmentSerializer(serializers.ModelSerializer):
#     total_roi = serializers.SerializerMethodField()
#     roi_collected = serializers.SerializerMethodField()
#     roi_pending = serializers.SerializerMethodField()
#     current_cycle = serializers.SerializerMethodField()

#     class Meta:
#         model = PartnerInvestment
#         fields = [
#             'id', 'order_id', 'amount_invested', 'roi_rate', 'status',
#             'total_roi', 'roi_collected', 'roi_pending', 'current_cycle',
#         ]

#     def get_total_roi(self, obj):
#         return round(obj.total_roi(), 2)

#     def get_roi_collected(self, obj):
#         return round(obj.roi_collected(), 2)

#     def get_roi_pending(self, obj):
#         return round(obj.roi_pending(), 2)

#     def get_current_cycle(self, obj):
#         return obj.current_cycle()