from django.urls import path, register_converter

from . import converters, views

register_converter(converters.DynamicConverter, "dynamic")

urlpatterns = [
    path("dynamic/<dynamic:value>/", views.empty_view, name="dynamic"),
]
