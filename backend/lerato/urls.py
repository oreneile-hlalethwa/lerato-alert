from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    # Everything else (/, /alert/, /vault/pin.html ...) is the frontend, served by WhiteNoise.
]
