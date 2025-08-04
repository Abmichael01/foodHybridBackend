# models.py
from django.db import models
# from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from .utils import generate_order_id
import uuid, random, string
from django.utils.text import slugify
from datetime import timedelta, date

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

class Product(models.Model):
    # shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="products")
    product_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)  # investment amount
    stock_quantity = models.PositiveIntegerField(default=0)
    quantity_per_unit = models.PositiveIntegerField(default=0, null=True, blank=True)
    kg_per_unit = models.PositiveIntegerField(default=0, null=True, blank=True)
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
     super().save(*args, **kwargs)


    def __str__(self):
        return self.name

    def calculate_roi_amount(self):
        return (self.price * self.roi_percentage) / 100

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='product_images/')

class PartnerInvestment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('in_transit', 'In Transit'),
        ('pending_settlement', 'Pending Settlement'),
        ('settled', 'Settled'),
        ('delivered', 'Delivered')
    )
    
    partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="investments")
    product = models.ManyToManyField(Product, related_name="investments")
    amount_invested = models.DecimalField(max_digits=12, decimal_places=2)
    roi_rate = models.DecimalField(max_digits=5, decimal_places=2, default=3.00)  # ROI per payout cycle (e.g., 3%)
    roi_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    order_id = models.CharField(max_length=30, unique=True, default=generate_order_id, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    # def calculate_roi(self):
    #     total_roi = 0
    #     for product in self.product.all():
    #         total_roi += float(self.amount_invested) * float(product.roi_percentage) / 100
    #     return total_roi
    def calculate_roi(self):
        return sum(
        float(self.amount_invested) * float(product.roi_percentage) / 100
        for product in self.product.all()
    )

  
    # def generate_roi_payout_schedule(self):
    #     if self.roi_payouts.exists():
    #         return  # prevent duplicate generation
    
    #     # total_roi = float(self.amount_invested) * float(self.roi_rate) / 100
    #     total_roi = total_roi = self.calculate_roi()
    #     roi_per_cycle = round(total_roi / 3, 2)
    
    #     # Average duration from all associated products
    #     durations = [p.duration_days or 35 for p in self.product.all()]
    #     avg_duration = sum(durations) // len(durations) if durations else 35
    
    #     interval = avg_duration // 3
    #     created = self.created_at.date() if self.pk and self.created_at else date.today()
    #     # created = self.created_at.date() if self.created_at else date.today()

    #     remainder = total_roi - (roi_per_cycle * 3)
    #     amounts = [roi_per_cycle] * 2 + [roi_per_cycle + remainder]
    
    #     payouts = []
    #     for i in range(3):
    #         payout_date = created + timedelta(days=interval * (i + 1))
    #         payouts.append(
    #             ROIPayout(
    #                 investment=self,
    #                 cycle_number=i + 1,
    #                 amount=roi_per_cycle,
    #                 payout_date=payout_date
    #             )
    #         )
    
    #     ROIPayout.objects.bulk_create(payouts)
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

        # payouts = [
        #     ROIPayout(
        #         investment=self,
        #         cycle_number=i + 1,
        #         amount=payout_amounts[i],
        #         payout_date=created + timedelta(days=interval * (i + 1))
        #     )
        #     for i in range(3)
        # ]

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
    # from_date = models.DateField(null=True, blank=True) 
    payout_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('investment', 'cycle_number')
        ordering = ['payout_date']

    def __str__(self):
        return f"Cycle {self.cycle_number} - {self.amount} on {self.payout_date}"
class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

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

