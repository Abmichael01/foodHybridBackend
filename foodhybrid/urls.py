from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static

schema_view = get_schema_view(
   openapi.Info(
      title="FoodHybrid API",
      default_version='v1',
      description="FoodHybrid API documentation",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="admin@foodhybrid.com"),
      license=openapi.License(name="FoodHybrid License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),  # public access
)


def home(request):
    return HttpResponse("Welcome to FoodHybrid API. Visit /swagger for docs.")

urlpatterns = [
    path('admin/', admin.site.urls), 
    path('', home),
    
    # API routes
    path('api/users/', include('users.urls')),
    path('api/wallet/', include('wallet.urls')),
    path('api/shops/', include('shop.urls')),
    path('api/cart/', include('cart.urls')),

    # Swagger / Redoc
    path('swagger.json/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files in debug
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
