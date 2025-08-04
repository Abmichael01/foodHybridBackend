from django.urls import path
from .views import *

urlpatterns = [
    path('addproduct/', AdminAddProductView.as_view(), name='add-product'),
    path('products/', ProductWithShopView.as_view(), name='products'),
    path('products/<str:product_id>/', ProductWithShopView.as_view(), name='products'),
    path('product/delete/', DeleteProductView.as_view(), name="delete product"),
    path('products/delete/<str:product_id>/', DeleteProductView.as_view(), name="delete-product"),
    path('products/update/<str:product_id>/', AdminUpdateProductView.as_view(), name="update-product"),
    # path('addshop/', AdminAddShopView.as_view(), name='add-product'),
    # path('shop/', DeleteShopView.as_view(), name="delete shop"),
    # path('shop/', DeleteShopView.as_view(), name="delete shop")
]