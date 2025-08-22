from rest_framework import serializers
from .models import Shop, Product, ProductImage

class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'shop_id', 'name', 'description', 'address', 'email']


# class ProductSerializer(serializers.ModelSerializer):
#     # shop = ShopSerializer(read_only=True) 
#     name = serializers.CharField(required=True,allow_blank=False)
#     description = serializers.CharField(required=True,allow_blank=False) 
#     price = serializers.CharField(required=True,allow_blank=False)
#     roi_percentage = serializers.CharField(required=True,allow_blank=False) 
#     quantity_per_unit = serializers.CharField(required=True,allow_blank=False)
#     kg_per_unit = serializers.CharField(required=True,allow_blank=False)
#     image = serializers.ImageField(required=True,allow_null=False)
#     class Meta:
#         model = Product
#         fields = ['id', 'product_id', 'name', 'description', 'price', 'stock_quantity', 'roi_percentage', 'quantity_per_unit', 'kg_per_unit', 'image']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image']

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    bags = serializers.SerializerMethodField(read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        # write_only=True,
        required=False
    )

    class Meta:
        model = Product
        fields = [
            'id', 'product_id', 'name', 'description',
            'price', 'stock_quantity', 'roi_percentage',
            'quantity_per_unit', 'kg_per_unit',
            'images', 'uploaded_images', 'bags'  
        ]

    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        product = Product.objects.create(**validated_data)
        for img in uploaded_images:
            ProductImage.objects.create(product=product, image=img)
        return product

    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if uploaded_images:
            # Optional: clear previous images
            instance.images.all().delete()
            for img in uploaded_images:
                ProductImage.objects.create(product=instance, image=img)

        return instance
    

    def get_bags(self, obj):
        return (obj.quantity_per_unit or 0) * (obj.stock_quantity or 0)


