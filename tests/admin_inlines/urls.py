from django.urls import path

from . import admin

urlpatterns = [
    path('admin/', admin.site.urls),
]
