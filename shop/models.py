# models.py
from django.db import models
# from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings

from .utils import generate_order_id
import uuid, random, string
from django.utils.text import slugify
from datetime import timedelta, date

def generate_unique_vendor_id():
    return f"VND-{uuid.uuid4().hex[:8].upper()}"

def generate_unique_product_id(name):
    prefix = slugify(name).upper().replace('-', '')[:4]
    random_part = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{random_part}"

class Shop(models.Model):
    shop_id = models.CharField(max_length=225, unique=True, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    address = models.TextField()
    email = models.EmailField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="owned_shops")
   
    def save(self, *args, **kwargs):
     if not self.shop_id:
         for _ in range(10):  # try 10 times max
             candidate_id = generate_unique_product_id(self.name)
             if not Shop.objects.filter(shop_id=candidate_id).exists():
                 self.shop_id = candidate_id
                 break
         else:
             raise ValueError("Could not generate a unique shop_id after 10 attempts.")
     super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Shops"
        ordering = ['name']

    def __str__(self):
        return self.name
    

# def vendor_profile_picture_upload_path(instance, filename):
#     return f'vendor_profiles/{instance.name}_{filename}'

# class Vendor(models.Model):
#     user = models.OneToOneField("Users", on_delete=models.CASCADE, related_name="vendor_profile")
#     vendor_id = models.CharField(max_length=20, unique=True, editable=False)  # ✅ auto-generated
#     store_name = models.CharField(max_length=255)
#     store_email = models.EmailField()
#     store_phone = models.CharField(max_length=20)
#     store_address = models.TextField()
#     # logo = models.ImageField(upload_to="vendors/", null=True, blank=True)

#     def save(self, *args, **kwargs):
#         if not self.vendor_id:
#             last_vendor = Vendor.objects.order_by("id").last()
#             if last_vendor:
#                 last_id = int(last_vendor.vendor_id.split("-")[-1])
#                 new_id = last_id + 1
#             else:
#                 new_id = 1
#             self.vendor_id = f"VEND-{new_id:04d}"  # → VEND-0001, VEND-0002, etc.
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"{self.vendor_id} - {self.store_name}"

class Vendor(models.Model):
    user = models.OneToOneField("Users", on_delete=models.CASCADE, related_name="vendor_profile")
    vendor_id = models.CharField(max_length=20, unique=True, blank=True)

    # store details
    store_name = models.CharField(max_length=255)
    store_email = models.EmailField()
    store_phone = models.CharField(max_length=20)
    store_address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    # logo = models.ImageField(upload_to="vendors/logos/", blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.vendor_id:
            last_id = Vendor.objects.count() + 1
            self.vendor_id = f"VEND-{last_id:04d}"  # e.g. VEND-0001
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vendor_id} - {self.store_name}"

# class Vendor(models.Model):
#     vendor_id = models.CharField(max_length=120, unique=True, editable=False)
#     name = models.CharField(max_length=255,default="")
#     email = models.EmailField(unique=True)
#     phone = models.CharField(max_length=225,default="")
#     address = models.CharField(max_length=225,default="")
#     profile_picture = models.ImageField(upload_to=vendor_profile_picture_upload_path, null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

    
#     def save(self, *args, **kwargs):
#      if not self.vendor_id:
#          for _ in range(10):  # try 10 times max
#              candidate_id = generate_unique_vendor_id()
#              if not Vendor.objects.filter(vendor_id=candidate_id).exists():
#                  self.vendor_id = candidate_id
#                  break
#          else:
#              raise ValueError("Could not generate a unique vendor_id after 10 attempts.")
#      super().save(*args, **kwargs)

#     # def save(self, *args, **kwargs):
#     #     if not self.vendor_id:
#     #         self.vendor_id = generate_unique_vendor_id()
#     #     super().save(*args, **kwargs)

#     def __str__(self):
#         return self.name

class Product(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="products",null=True, blank=True)
    product_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    # bags = models.PositiveIntegerField(default=0, editable=False) 
    price = models.DecimalField(max_digits=12, decimal_places=2)  # investment amount
    stock_quantity = models.PositiveIntegerField(default=0)
    quantity_per_unit = models.PositiveIntegerField(default=0, null=True, blank=True)
    kg_per_unit = models.DecimalField(default=0, null=True, blank=True, decimal_places=2, max_digits=10)
    roi_percentage = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 10.5 for 10.5%
    duration_days = models.PositiveIntegerField(null=True, blank=True, default=105)  # Investment duration in days
    created_at = models.DateTimeField(auto_now_add=True)


    def save(self, *args, **kwargs):
     if not self.product_id:
         for _ in range(10):  # try 10 times max
             candidate_id = generate_unique_product_id(self.name)
             if not Product.objects.filter(product_id=candidate_id).exists():
                 self.product_id = candidate_id
                 break
         else:
             raise ValueError("Could not generate a unique shop_id after 10 attempts.")
        
        # Auto-calculate bags before saving
    #  self.bags = (self.quantity_per_unit or 0) * (self.stock_quantity or 0)
     super().save(*args, **kwargs)


    def __str__(self):
        return self.name

    def calculate_roi_amount(self):
        return (self.price * self.roi_percentage) / 100

    # @property
    # def total_bags(self):
    #     """Calculate total bags = quantity_per_unit * stock_quantity"""
    #     return (self.quantity_per_unit or 0) * (self.stock_quantity or 0)

    # @property
    # def total_weight(self):
    #     """Optional: Calculate total weight in kg = total_bags * kg_per_unit"""
    #     return self.total_bags * (self.kg_per_unit or 0)

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='product_images/')

    
def get_default_vendor_pk():
    vendor = Vendor.objects.first()
    return vendor.pk if vendor else None

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, related_name='orders', on_delete=models.CASCADE, default=get_default_vendor_pk)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

class PartnerInvestment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('in_transit', 'In Transit'),
        ('pending_settlement', 'Pending Settlement'),
        ('settled', 'Settled'),
        ('delivered', 'Delivered')
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='investments')  
    partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="investments")
    product = models.ManyToManyField(Product, related_name="investments")
    amount_invested = models.DecimalField(max_digits=12, decimal_places=2)
    roi_rate = models.DecimalField(max_digits=5, decimal_places=2, default=3.00)  # ROI per payout cycle (e.g., 3%)
    roi_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    order_id = models.CharField(max_length=30, unique=True, default=generate_order_id, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    def save(self, *args, **kwargs):
        if not self.vendor and self.product and self.product.shop:
            self.vendor = self.product.shop.vendor
        super().save(*args, **kwargs)


    def calculate_roi(self):
        return sum(
        float(self.amount_invested) * float(product.roi_percentage) / 100
        for product in self.product.all()
    )

    def generate_roi_payout_schedule(self):
        if self.roi_payouts.exists() or not self.product:
            return  # prevent duplicate or empty generation

        total_roi = float(self.amount_invested) * float(self.roi_rate) / 100
        roi_per_cycle = round(total_roi / 3, 2)
        remainder = round(total_roi - (roi_per_cycle * 3), 2)
        payout_amounts = [roi_per_cycle, roi_per_cycle, roi_per_cycle + remainder]

        durations = [p.duration_days or 105 for p in self.product.all()]
        avg_duration = sum(durations) // len(durations) if durations else 105
        interval = avg_duration // 3

        created = self.created_at.date() if self.pk and self.created_at else date.today()

        payouts = []
        for i in range(3):
            from_date = created + timedelta(days=interval * i)
            to_date = created + timedelta(days=interval * (i + 1))
            payouts.append(
                ROIPayout(
                    investment=self,
                    cycle_number=i + 1,
                    amount=payout_amounts[i],
                    # from_date=from_date,
                    payout_date=to_date
                )
            )

        ROIPayout.objects.bulk_create(payouts)
        
    def total_roi(self):
        return float(self.amount_invested) * float(self.roi_rate) / 100

    def roi_collected(self):
        return self.roi_payouts.filter(is_paid=True).aggregate(
            total=models.Sum('amount')
        )['total'] or 0

    def roi_pending(self):
        return self.roi_payouts.filter(is_paid=False).aggregate(
            total=models.Sum('amount')
        )['total'] or 0

    def current_cycle(self):
        # Return next unpaid payout's cycle number or "Completed"
        unpaid = self.roi_payouts.filter(is_paid=False).order_by('cycle_number').first()
        return unpaid.cycle_number if unpaid else "Completed"

class Meta:
    ordering = ['-created_at']
    verbose_name = "Partner Investment"

def __str__(self):
    return f"Investment {self.order_id} by {self.partner}"

class ROIPayout(models.Model):
    investment = models.ForeignKey(PartnerInvestment, on_delete=models.CASCADE, related_name="roi_payouts")
    cycle_number = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payout_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('investment', 'cycle_number')
        ordering = ['payout_date']

    def __str__(self):
        return f"Cycle {self.cycle_number} - {self.amount} on {self.payout_date}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    
class ROIPayment(models.Model):
    investment = models.ForeignKey(PartnerInvestment, on_delete=models.CASCADE, related_name="roi_payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)

    def pay_roi(self):
        # Check if the investment is approved and not fully paid yet
        if self.investment.status == 'approved' and self.investment.roi_paid < self.investment.amount_invested:
            # Calculate the ROI for the partner
            roi_amount = self.investment.calculate_roi()
            
            # Ensure the wallet has enough balance to pay the ROI
            if self.investment.partner.wallet.withdraw(roi_amount):
                # Update ROI paid on the investment
                self.investment.roi_paid += roi_amount
                self.investment.save()

                # Record the payout
                self.amount = roi_amount
                self.save()

                # Notify the partner (could be email, push notification, etc.)
                self.notify_partner()

    def notify_partner(self):
        # Notification logic (could be sending an email or push notification)
        pass

