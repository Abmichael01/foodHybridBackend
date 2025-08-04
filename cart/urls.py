from django.urls import path
from .views import *

urlpatterns = [
    path('addproducttocart/', AddToCartView.as_view(), name='add-product-to-cart'),
    path('viewcart/', ViewCart.as_view(), name='view-cart'),
    path('checkoutcart/', CheckoutView.as_view(), name='checkout-cart'),
    path('remove/', RemoveFromCartView.as_view()),
    # path('update/', UpdateCartQuantityView.as_view()),
]