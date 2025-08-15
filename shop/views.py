from rest_framework.views import APIView
# from rest_framework.permissions import IsAdminUser, IsAuthenticated
from users.permisssion import IsAdmin, IsAdminOrPartner, IsPartner
from rest_framework.response import Response
from rest_framework import status
from .models import ProductImage, Shop, Product, PartnerInvestment
from .serializers import ShopSerializer, ProductSerializer
from rest_framework.parsers import MultiPartParser, FormParser,JSONParser
from django.shortcuts import get_object_or_404

class AdminAddShopView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = ShopSerializer(data=request.data)

        if serializer.is_valid():
            shop = serializer.save()  # Saves the new shop
            return Response({
                'detail': 'Shop created successfully.',
                'shop': ShopSerializer(shop).data  # Return the created shop data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class AdminAddProductView(APIView):
#     permission_classes = [IsAdmin]
#     parser_classes = [MultiPartParser, FormParser, JSONParser] 

#     def post(self, request):
#         quantity = request.data.get('stock_quantity')

#         serializer = ProductSerializer(data=request.data)
#         if serializer.is_valid():
#             product = serializer.save() 
#             return Response({
#                 'detail': 'Product created successfully.',
#                 'product': ProductSerializer(product).data 
#             }, status=status.HTTP_201_CREATED)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminAddProductView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser] 

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()  # Create the product first

            # Handle uploaded images
            images = request.FILES.getlist('images')  # multiple files
            for img in images:
                ProductImage.objects.create(product=product, image=img)

            return Response({
                'detail': 'Product created successfully.',
                'product': ProductSerializer(product).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUpdateProductView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def put(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)

        serializer = ProductSerializer(product, data=request.data, partial=True)  # use partial=True for partial updates

        if serializer.is_valid():
            product = serializer.save()
            return Response({
                'detail': 'Product updated successfully.',
                'product': ProductSerializer(product).data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# class ProductWithShopView(APIView):
#     def get(self, request, product_id):
#         try:
#             # Retrieve the product by its ID
#             product = Product.objects.get(id=product_id)
#         except Product.DoesNotExist:
#             return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the product and return it with the shop information
        # serializer = ProductSerializer(product)
        # return Response(serializer.data, status=status.HTTP_200_OK)

class ProductWithShopView(APIView):
    permission_classes = [IsAdminOrPartner]
    def get(self, request, product_id=None):
        # product_id = request.query_params.get('product_id')

        if product_id:
            try:
                product = Product.objects.filter(product_id=product_id).first()
                serializer = ProductSerializer(product)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Product.DoesNotExist:
                return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            products = Product.objects.all()
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


class DeleteProductView(APIView):
    permission_classes = [IsAdmin]
    def delete(self, request, product_id=None):
    #    product_id = request.data.get("product_id")
       if product_id:
           try:
               product = Product.objects.get(product_id=product_id)
               product.delete()
               return Response({'detail': 'Product deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
           except Product.DoesNotExist:
               return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
       else:
           Product.objects.all().delete()
           return Response({'detail': 'All products deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)

class DeleteShopView(APIView):
    permission_classes = [IsAdmin]
    def delete(self, request, shop_id):
        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response({'detail': 'Shop not found.'}, status=status.HTTP_404_NOT_FOUND)

        shop.delete()
        return Response({'detail': 'Shop deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)

