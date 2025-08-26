# wallet/models.py
from datetime import timezone, timedelta
import random
import uuid
from django.conf import settings
from django.db import models
from users.models import Users
from shop.models import Order, Product, Vendor
from django.utils.timezone import now

class Wallet(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    def deposit(self, amount):
        self.balance += amount
        self.save()

    def withdraw(self, amount):
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            return True
        return False

    def __str__(self):
        return f"Wallet of {self.user.email} with balance {self.balance}"

    
class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('fund', 'Fund'),
        ('withdraw', 'Withdraw'),
        ('investment', 'Investment'),
        ('investmentUpdate', 'InvestmentUpdate'),
        ('roi', 'Return On Investment'),
        ('remittance', 'Remittance')
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        # Add more as needed
    )
    vendor = models.ForeignKey(Vendor,
        on_delete=models.CASCADE,
        related_name="transactions",   # ✅ important
        null=True, blank=True
    )
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    available_balance_at_time = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    from_user = models.CharField(max_length=20)
    to = models.CharField(max_length=200)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')  # or pending/failed
    created_at = models.DateTimeField(auto_now_add=True)
    order_id = models.CharField(max_length=30, null=True)
    reference = models.CharField(max_length=30, null=True, blank=True)
    description = models.CharField(max_length=120, null=True, blank=True) 
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.CharField(max_length=30, null=True, blank=True)
    account_name = models.CharField(max_length=100, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)


    

class Beneficiary(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='beneficiaries')
    name = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    account_type = models.CharField(max_length=50, blank=True, null=True)
    sort_code = models.CharField(max_length=50, blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.account_number}"

        
class Remittance(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="remittances")
    order = models.ForeignKey(Order, related_name="remittances", on_delete=models.CASCADE, default=None, null=True, blank=True)  
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    remittance_id = models.CharField(max_length=20, unique=True, default=uuid.uuid4)
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("completed", "Completed"), ("failed", "Failed")],
        default="pending"
    )
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        otp_code = str(random.randint(1000, 9999))  # 4-digit OTP
        self.otp = otp_code
        self.otp_expires_at = now() + timedelta(minutes=5)
        self.save()
        return otp_code
    

class VendorasBeneficiary(models.Model):
    partner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendor_beneficiaries"
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="saved_as_beneficiaries")
    alias = models.CharField(max_length=100, blank=True, null=True)  # optional nickname
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("partner", "vendor")  # prevent duplicates

    def __str__(self):
        return f"{self.partner.username} -> {self.vendor.store_name}"