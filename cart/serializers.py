# serializers.py

from rest_framework import serializers
from .models import CartItem, Cart
from shop.models import Product, Order, OrderItem

class CartItemSerializer(serializers.ModelSerializer):
    product_detail = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'product_detail']

    def get_product_detail(self, obj):
        return {
            "name": obj.product.name,
            "price": obj.product.price
        }

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = '__all__'
