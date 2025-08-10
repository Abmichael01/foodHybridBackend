from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from shop.serializers import ProductSerializer
from .models import Users, Driver,OrderDeliveryConfirmation, Notification, EmailOTP
from shop.models import PartnerInvestment, Product, ROIPayout, OrderItem, Order, Vendor
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
        fields = ['id','vendor_id', 'name', 'email', 'phone', 'profile_picture', 'created_at']

class AdminOrderSerializer(serializers.ModelSerializer):
    partner_name = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    total_amount = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    order_id = serializers.SerializerMethodField()
    product = serializers.SerializerMethodField()

    class Meta:
        model = Order  # Still default for Orders
        fields = [
            'id', 'created_at', 'partner_name', 'vendor_name',
            'total_amount', 'items', 'order_id', 'product', 'status'
        ]

    def get_total_amount(self, obj):
        if hasattr(obj, 'items'):  
            # Order case
            return sum(product.price * product.quantity for product in obj.items.all())
        elif hasattr(obj, 'amount_invested'):  
            # PartnerInvestment case
            return obj.amount_invested
        return 0

    def get_order_id(self, obj):
        investment = getattr(obj, 'partnerinvestment', None)
        if investment:
            return getattr(investment, 'order_id', None)
        return None

    def get_product(self, obj):
        investment = getattr(obj, 'partnerinvestment', None)
        if investment and hasattr(investment, 'product'):
            return [p.name for p in investment.product.all()]
        return []

    def get_partner_name(self, obj):
        user = getattr(obj, 'partner', None)
        if not user:
            return None
        return (
            getattr(user, 'name', None)
            or f"{user.first_name} {user.last_name}".strip()
            or user.username
        )


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
        fields = ['order_id', 'owner_name', 'owner_email', 'store_address']

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
    # phone = serializers.CharField()
    # address = serializers.CharField()
    username = serializers.CharField()
    total_purchase = serializers.SerializerMethodField()
    total_orders = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    portfolio_balance = serializers.SerializerMethodField()

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_total_purchase(self, obj):
        return PartnerInvestment.objects.filter(partner=obj).aggregate(total=models.Sum('amount_invested'))['total'] or 0

    def get_total_orders(self, obj):
        return PartnerInvestment.objects.filter(partner=obj).count()

    def get_balance(self, obj):
        wallet = getattr(obj, 'wallet', None)
        return wallet.balance if wallet else 0

    def get_portfolio_balance(self, obj):
        wallet = getattr(obj, 'wallet', None)
        return wallet.portfolio_balance if wallet and hasattr(wallet, 'portfolio_balance') else 0
    

class SimplePartnerSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = Users
        fields = ['id', 'username', 'email', 'full_name']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()



class ProductBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['product_id', 'name', 'description', 'price']

class PartnerInvestmentListSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.get_full_name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    products = ProductBriefSerializer(source='product', many=True)

    class Meta:
        model = PartnerInvestment
        fields = [
            'order_id',
            'partner_name',
            'vendor_name',
            'amount_invested',
            'products',
            'status',
            'created_at'
        ]

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['product_name', 'quantity', 'price']

class VendorOrderSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.full_name', read_only=True)
    total_amount = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_id', 'partner_name', 'total_amount', 'created_at', 'items']

    def get_total_amount(self, obj):
        return sum(item.price * item.quantity for item in obj.items.all())

class VendorDetailSerializer(serializers.ModelSerializer):
    recent_orders = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = ['vendor_id', 'name', 'email', 'phone', 'profile_picture', 'created_at', 'recent_orders']

    def get_recent_orders(self, obj):
        limit = self.context.get('order_limit', 10)  # Default if not provided
        orders = obj.orders.all().order_by('-created_at')[:limit]
        return VendorOrderSerializer(orders, many=True).data

        
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
        vendor=vendor
        ).aggregate(total=Sum('amount_invested'))['total'] or 0

    def get_today_remittance(self, vendor):
        return PartnerInvestment.objects.filter(
            vendor=vendor,
            created_at__date=date.today()
        ).aggregate(total=Sum('amount_invested'))['total'] or 0

    def get_total_orders(self, vendor):
        return PartnerInvestment.objects.filter(vendor=vendor).count()

    def get_orders(self, vendor):
        return PartnerInvestment.objects.filter(
            vendor=vendor
        ).values('id', 'amount_invested', 'status', 'created_at', 'partner__email', 'vendor__name')
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



class InvestmentProductSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source='shop.name', read_only=True)  # if Product.shop exists
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'roi_percentage', 'duration_days', 'shop_name']

class VendorSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ['id', 'name', 'email', 'phone']  # adjust fields on Vendor




class AdminPartnerOrderSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(read_only=True)
    date = serializers.DateTimeField(source='created_at', read_only=True)
    partner = SimplePartnerSerializer(read_only=True)
    vendors = serializers.SerializerMethodField()
    amount_invested = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    investment_details = serializers.SerializerMethodField()

    class Meta:
        model = PartnerInvestment
        fields = [
            'id', 'order_id', 'date', 'partner', 'vendors',
            'amount_invested', 'investment_details', 'status'
        ]

    def get_investment_details(self, obj):
        products = obj.product.all()
        return InvestmentProductSerializer(products, many=True).data

    def get_vendors(self, obj):
        vendors = []
        seen = set()
        for p in obj.product.select_related('shop__vendor').all():
            shop = getattr(p, 'shop', None)
            vendor = getattr(shop, 'vendor', None) if shop else None
            if vendor and vendor.id not in seen:
                seen.add(vendor.id)
                vendors.append(vendor)
        return VendorSmallSerializer(vendors, many=True).data
    
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'roi_percentage', 'duration_days']

class InvestmentSerializer(serializers.ModelSerializer):
    products = ProductSerializer(source='product', many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    total_roi = serializers.SerializerMethodField()
    roi_collected = serializers.SerializerMethodField()
    roi_pending = serializers.SerializerMethodField()
    current_cycle = serializers.SerializerMethodField()

    class Meta:
        model = PartnerInvestment
        fields = [
            'id', 'order_id', 'vendor_name', 'products',
            'amount_invested', 'roi_rate', 'total_roi',
            'roi_collected', 'roi_pending', 'current_cycle',
            'status', 'created_at'
        ]

    def get_total_roi(self, obj):
        return obj.total_roi()

    def get_roi_collected(self, obj):
        return obj.roi_collected()

    def get_roi_pending(self, obj):
        return obj.roi_pending()

    def get_current_cycle(self, obj):
        return obj.current_cycle()

class PartnerDetailSerializer(serializers.ModelSerializer):
    recent_investments = serializers.SerializerMethodField()

    class Meta:
        model = Users  # assuming user_type="partner"
        fields = [
            'id', 'full_name', 'email', 'phone',
            'profile_picture', 'created_at', 'recent_investments'
        ]

    def get_recent_investments(self, obj):
        limit = self.context.get('investment_limit', 10)
        investments = obj.investments.all().select_related('vendor').prefetch_related('product')[:limit]
        return InvestmentSerializer(investments, many=True).data

