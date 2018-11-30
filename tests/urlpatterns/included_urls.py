from django.urls import path

from . import views

urlpatterns = [
    path('extra/<extra>/', views.empty_view, name='inner-extra'),
]
