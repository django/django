from django.urls import path

from . import views

app_name = "app_with_urls"

urlpatterns = [
    path("unnamed", views.view_func),
    path("named", views.view_func, name="named"),
]
