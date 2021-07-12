from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='create'),
    path('pastes/<str:key>', views.view, name='view')
]
