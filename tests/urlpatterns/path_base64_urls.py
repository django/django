from django.urls import path, register_converter

from . import converters, views

register_converter(converters.Base64Converter, 'base64')

urlpatterns = [
    path('base64/<base64:value>/', views.empty_view, name='base64'),
]
