# views.py

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from users.permisssion import IsPartner
from users.models import Notification, Users
from .models import Cart, CartItem
from shop.models import Product, Order, OrderItem, PartnerInvestment, Vendor
from wallet.utils import generate_reference
from wallet.models import Transaction
from foodhybrid.utils import send_email
from datetime import timedelta, date
from decimal import Decimal
from users.utils import verify_user_pin

class AddToCartView(APIView):
   permission_classes = [IsPartner]

   def post(self, request):
        user = request.user
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        if not product_id:
            return Response({"detail": "A product id is required"})
        try:
            quantity = int(quantity)
            if quantity <= 0:
                return Response({"detail": "Quantity must be greater than zero."}, status=400)
        except ValueError:
            return Response({"detail": "Invalid quantity."}, status=400)

        product = get_object_or_404(Product, product_id=product_id)

        cart, _ = Cart.objects.get_or_create(user=user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        # cart_item.product_id = product.product_id 

        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity

        cart_item.save()

        
        cart_items = cart.items.select_related('product')
        total_unique_items = cart_items.count()
        total_quantity = sum(item.quantity for item in cart_items)

        items_summary = [
            {
                "product_id": item.product.product_id,
                "product_name": item.product.name,
                "quantity": item.quantity
            }
            for item in cart_items
        ]

        return Response({
            "detail": "Product added to cart successfully.",
              "cart_summary": {
                "total_unique_items": total_unique_items,
                "total_quantity": total_quantity,
                "items": items_summary
            }
        }, status=200)
   


    #  permission_classes = [IsAuthenticated]

    # def post(self, request):
    #     user = request.user
    #     product_id = request.data.get('product_id')
    #     quantity = int(request.data.get('quantity', 1))

    #     product = Product.objects.filter(id=product_id).first()
    #     if not product:
    #         return Response({"detail": "Product not found."}, status=404)

    #     cart, _ = Cart.objects.get_or_create(user=user)

    #     cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    #     if not created:
    #         cart_item.quantity += quantity
    #     else:
    #         cart_item.quantity = quantity
    #     cart_item.save()

    #     return Response({"detail": "Product added to cart."})

class ViewCart(APIView):
    permission_classes = [IsPartner]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = cart.items.all()

        cart_data = []
        today = date.today()

        for item in items:
            product = item.product
            duration = product.duration_days or 105
            roi_percentage = product.roi_percentage or Decimal('0')
            amount = Decimal(product.price) * item.quantity
            total_roi = (amount * roi_percentage / Decimal('100')).quantize(Decimal('0.01'))
            roi_per_cycle = round(total_roi / 3, 2)
            interval = duration // 3

            cycles = []
            for i in range(3):
                payout_date = today + timedelta(days=interval * (i + 1))
                cycles.append({
                    "cycle": i + 1,
                    "amount": roi_per_cycle,
                    "payout_date": payout_date
                })

            cart_data.append({
                "product_id": product.product_id,
                "product_name": product.name,
                "quantity": item.quantity,
                "price": float(product.price),
                "total_amount": round(amount, 2),
                "roi_percentage": roi_percentage,
                "total_roi": total_roi,
                "roi_cycles": cycles
            })

        return Response({
            "total_items": len(cart_data),
            "items": cart_data
        })

class CheckoutView(APIView):
    permission_classes = [IsPartner]

    def post(self, request):
        user = request.user
        cart = getattr(user, 'cart', None)
        wallet = getattr(user, 'wallet', None)
        pin = request.data.get("transaction_pin")
        vendor_id = request.data.get("vendor_id")

        if not cart or not cart.items.exists():
            return Response({'detail': 'Cart is empty.'}, status=400)
        if not wallet:
            return Response({'detail': 'Wallet not found.'}, status=404)
        if not vendor_id:
            return Response({'detail': 'Vendor ID is required.'}, status=400)

        vendor = get_object_or_404(Vendor, vendor_id=vendor_id)

        items = cart.items.all()
        total = sum(item.product.price * item.quantity for item in items)
        weighted_roi = sum(
            float(item.product.price * item.quantity / total) * float(item.product.roi_percentage)
            for item in items
        )

        if total:
            if not pin:
                return Response({'detail': 'Transaction pin is required!'}, status=400)
            if not user.pin_hash:
                return Response({"detail": "Please kindly set a pin."}, status=403)
            if not verify_user_pin(pin, user.pin_hash):
                return Response({"detail": "Invalid transaction PIN."}, status=403)

        if wallet.balance < total:
            return Response({'detail': 'Insufficient wallet balance.'}, status=400)

        # Deduct from wallet
        wallet.balance -= total
        wallet.save()

        # Create order
        order = Order.objects.create(
            user=user,
            total_amount=total,
            reference=generate_reference(),
            status="completed"
        )

        # Create investment with vendor
        investment = PartnerInvestment.objects.create(
            vendor=vendor,
            partner=user,
            amount_invested=total,
            roi_rate=round(weighted_roi, 2),
            status='pending',
        )
        investment.generate_roi_payout_schedule()

        # Notify
        send_email(user, "investment_created", "Investment Pending Approval",
                   extra_context={"amount": total, "reference": order.reference})
        Notification.objects.create(
            user=user,
            title="You just made an investment!",
            message=f"You just made an investment of {total} with reference {order.reference}",
            event_type="investment",
            available_balance_at_time=wallet.balance
        )
        admins = Users.objects.filter(is_superuser=True)  # Or use is_staff/group filter
        for admin in admins:
            Notification.objects.create(
                user=admin,
                title="New Pending Investment",
                message=f"Partner {user.username} just made an investment of {total} with reference {order.reference}. Pending your approval.",
                event_type="admin",
                from_user=user.username,
                to_user=admin.username
            )
        Transaction.objects.create(
            user=user,
            from_user="Available Balance",
            payment_method="wallet",
            to="investment",
            transaction_type="investment",
            amount=total,
            status="pending",
            reference=generate_reference(),
            order_id=order.reference,
            description="Your investment is pending approval",
            available_balance_at_time=wallet.balance
        )

        for item in cart.items.all():
            investment.product.set([item.product])
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

        cart.items.all().delete()

        return Response({
            'detail': 'Order placed and wallet charged successfully.',
            'reference': order.reference
        })

class RemoveFromCartView(APIView):
    permission_classes = [IsPartner]

    def delete(self, request):
        user = request.user
        product_id = request.data.get('product_id')
        reduce_by = request.data.get('quantity')

        if not product_id:
            return Response({"detail": "Product ID is required."}, status=400)

        cart = getattr(user, 'cart', None)
        if not cart:
            return Response({"detail": "Cart not found."}, status=404)

        item = cart.items.filter(product__product_id=product_id).first()
        if not item:
            return Response({"detail": "Item not in cart."}, status=404)
        
        if reduce_by:
            reduce_by = int(reduce_by)
            if item.quantity > reduce_by:
                item.quantity -= reduce_by
                item.save()
                return Response({"detail": f"Reduced quantity by {reduce_by}."})
            else:
                item.delete()
                return Response({"detail": "Item removed from cart."})
        item.delete()
        return Response({"detail": "Item removed from cart"})

# class UpdateCartQuantityView(APIView):
#     permission_classes = [IsAuthenticated]

#     def put(self, request):
#         user = request.user
#         product_id = request.data.get('product_id')
#         quantity = int(request.data.get('quantity', 1))

#         cart = getattr(user, 'cart', None)
#         if not cart:
#             return Response({"detail": "Cart not found."}, status=404)

#         item = cart.items.filter(product_id=product_id).first()
#         if not item:
#             return Response({"detail": "Item not in cart."}, status=404)

#         if quantity < 1:
#             item.delete()
#         else:
#             item.quantity = quantity
#             item.save()

#         return Response({"detail": "Cart updated successfully."})
