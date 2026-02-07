# A URLconf that doesn't define any error handler view.
from django.urls import path

from .views import bad_view, empty_view

urlpatterns = [
    path("test_view/", empty_view, name="test_view"),
    path("bad_view/", bad_view, name="bad_view"),
]
