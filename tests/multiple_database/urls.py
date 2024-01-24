from django.contrib import admin
from django.urls import path

from .views import book


urlpatterns = [
    path("books/<book_id>/", book),
    path("test_multiple_database/admin/", admin.site.urls),
]
