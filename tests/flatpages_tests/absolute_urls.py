from django.contrib.flatpages import views
from django.urls import path

urlpatterns = [
    path('flatpage/', views.flatpage, {'url': '/hardcoded/'}),
]
